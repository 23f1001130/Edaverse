import json
import hashlib
import math
import re
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.ollama import get_ollama_status, generate_insight
from app.services.ai_providers import stream_ai, humanize_error, DEFAULT_MODELS
from app.services.store import get_dataset, save_insight, get_cached_insight
from app.services.eda import _load_df as _load_eda_df
from app.services.ai_dataframe_exec import execute_pandas_code, is_dataframe_question

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    provider: str = "local"
    model: str | None = None
    api_key: str | None = None
    is_first_message: bool = True   # frontend tells us if schema is needed
    switched_provider: bool = False  # frontend tells us if provider just changed

class InsightRequest(BaseModel):
    provider: str = "local"
    model: str | None = None
    api_key: str | None = None


# ── Context builders ──────────────────────────────────────────────────────────

def _full_system(dataset: dict) -> str:
    """Full schema + stats — sent only on first message of a session."""
    schema = dataset.get("schema", [])
    shape = dataset.get("shape", {})
    filename = dataset.get("filename", "")
    sample_rows = dataset.get("sample_rows", [])[:5]

    null_ranked = sorted(schema, key=lambda c: c.get('null_pct', 0), reverse=True)
    null_summary = ', '.join(
        f"{c['name']} ({c.get('null_pct', 0)}%)"
        for c in null_ranked[:5] if c.get('null_pct', 0) > 0
    ) or "none"

    col_lines = []
    for c in schema:
        line = f"  - {c['name']} ({c['type']})"
        if c.get('null_pct', 0) > 0:
            line += f" — {c['null_pct']}% missing"
        if c.get('min') is not None:
            line += f" — range [{c['min']}–{c['max']}], mean {c['mean']}, std {c.get('std', '?')}"
        if c.get('skewness') is not None:
            line += f", skew {c['skewness']}"
        if c.get('unique') is not None:
            line += f" — {c['unique']} unique, top: {c.get('top')} ({c.get('freq_pct')}%)"
        col_lines.append(line)

    return f"""You are a data analyst assistant. The user is working with this dataset:

File: {filename}
Shape: {shape.get('rows','?')} rows × {shape.get('columns','?')} columns

Columns:
{chr(10).join(col_lines)}

Top columns by missing values: {null_summary}

Small row preview (for examples only, not full-dataset conclusions):
{json.dumps(sample_rows, ensure_ascii=False, default=str)}

RULES:
- Answer factual questions directly from the schema above. Never write code for things you already know.
- Treat the preview as a bounded sample only; use schema stats for dataset-level claims.
- Only write Python/pandas code when explicitly asked.
- Keep answers short and direct. Reference real column names and numbers."""


def _workspace_summary(dataset: dict) -> str:
    """Compressed workspace context — sent when switching providers.
    Contains only the key facts, not the full per-column detail.
    Costs ~10x fewer tokens than _full_system for large datasets."""
    schema = dataset.get("schema", [])
    shape = dataset.get("shape", {})
    filename = dataset.get("filename", "")

    numeric = [c for c in schema if c['type'] in ('integer', 'float')]
    categorical = [c for c in schema if c['type'] in ('categorical', 'text', 'boolean')]
    high_null = sorted(
        [c for c in schema if c.get('null_pct', 0) >= 5],
        key=lambda c: c['null_pct'], reverse=True
    )[:5]

    lines = [
        f"Dataset: {filename}",
        f"Shape: {shape.get('rows','?')} rows × {shape.get('columns','?')} columns",
        f"Numeric columns ({len(numeric)}): {', '.join(c['name'] for c in numeric[:10])}{'...' if len(numeric)>10 else ''}",
        f"Categorical columns ({len(categorical)}): {', '.join(c['name'] for c in categorical[:10])}{'...' if len(categorical)>10 else ''}",
    ]
    if high_null:
        lines.append("Columns with significant nulls: " + ', '.join(
            f"{c['name']} ({c['null_pct']}%)" for c in high_null
        ))

    # Include any cleaning decisions or insight if they exist
    if dataset.get("insight"):
        # Take just the first sentence of the insight as a hint
        first_sentence = dataset["insight"].split('.')[0][:200]
        lines.append(f"Previous analysis note: {first_sentence}.")

    return "You are a data analyst assistant. Context from the previous session:\n\n" + \
           '\n'.join(lines) + \
           "\n\nAnswer questions about this dataset directly and concisely."


def _provider_model(provider: str, requested: str | None, local_model: str | None = None) -> str:
    if requested:
        return requested
    if provider == "local":
        return local_model or "llama3.2:3b"
    return DEFAULT_MODELS.get(provider, provider)


def _data_hash(dataset: dict) -> str:
    """Hash the bounded dataset facts that change when cleaning/engineering changes."""
    payload = {
        "shape": dataset.get("shape", {}),
        "schema": dataset.get("schema", []),
        "sample_rows": dataset.get("sample_rows", []),
        "workflow": dataset.get("workflow", {}),
    }
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _safe_value(value):
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    try:
        import numpy as np
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating,)):
            f = float(value)
            return None if (math.isnan(f) or math.isinf(f)) else round(f, 4)
    except Exception:
        pass
    return value


def _find_column(schema: list[dict], question: str) -> dict | None:
    q = question.lower()
    quoted = re.findall(r"[\"'`]([^\"'`]+)[\"'`]", question)
    for name in quoted:
        for col in schema:
            if col.get("name", "").lower() == name.lower():
                return col
    for col in sorted(schema, key=lambda c: len(c.get("name", "")), reverse=True):
        name = col.get("name", "")
        if not name:
            continue
        pattern = r"(?<!\w)" + re.escape(name.lower()) + r"(?!\w)"
        if re.search(pattern, q):
            return col
    return None


def _column_list(schema: list[dict], col_type: str | None = None) -> list[str]:
    if not col_type:
        return [c["name"] for c in schema if c.get("name")]
    if col_type == "numeric":
        return [c["name"] for c in schema if c.get("type") in ("integer", "float")]
    if col_type == "categorical":
        return [c["name"] for c in schema if c.get("type") in ("categorical", "text", "boolean")]
    return [c["name"] for c in schema if c.get("type") == col_type]


def _series_stat(dataset: dict, col_name: str, stat: str):
    df = _load_eda_df(dataset)
    if df is None or col_name not in df.columns:
        return None
    import pandas as pd
    series = df[col_name]
    if stat in ("mean", "median", "min", "max", "std", "sum"):
        numeric = pd.to_numeric(series, errors="coerce").replace([float("inf"), float("-inf")], pd.NA).dropna()
        if numeric.empty:
            return None
        return _safe_value(getattr(numeric, stat)())
    if stat == "mode":
        vc = series.dropna().astype(str).value_counts()
        if vc.empty:
            return None
        return {"value": vc.index[0], "count": int(vc.iloc[0]), "pct": round(float(vc.iloc[0]) / max(len(series), 1) * 100, 2)}
    if stat == "unique":
        return int(series.nunique(dropna=True))
    return None


def _deterministic_answer(dataset: dict, question: str) -> str | None:
    """Answer cheap factual questions without spending an LLM call."""
    q = question.strip().lower()
    schema = dataset.get("schema", [])
    shape = dataset.get("shape", {})
    if not q or not schema:
        return None

    if re.search(r"\b(shape|size)\b", q):
        return f"The dataset has {shape.get('rows', '?')} rows and {shape.get('columns', '?')} columns."
    if re.search(r"\b(how many|number of|count)\s+rows?\b|\brow count\b", q):
        return f"The dataset has {shape.get('rows', '?')} rows."
    if re.search(r"\b(how many|number of|count)\s+columns?\b|\bcolumn count\b", q):
        return f"The dataset has {shape.get('columns', len(schema))} columns."

    if re.search(r"\b(list|show|what are|which are).*\bcolumns?\b", q) or re.search(r"\bwhat columns\b", q) or q in {"columns", "what columns"}:
        names = _column_list(schema)
        return f"Columns ({len(names)}): " + ", ".join(names)
    if re.search(r"\b(numeric|number)\s+columns?\b", q):
        names = _column_list(schema, "numeric")
        return f"Numeric columns ({len(names)}): " + (", ".join(names) or "none")
    if re.search(r"\b(categorical|category|text)\s+columns?\b", q):
        names = _column_list(schema, "categorical")
        return f"Categorical/text columns ({len(names)}): " + (", ".join(names) or "none")

    if re.search(r"\b(group by|by|breakdown|compare)\b", q) and re.search(
        r"\b(mean|average|median|sum|total|count|top|highest|lowest|correlation|relationship)\b", q
    ):
        return None

    col = _find_column(schema, question)
    if not col:
        return None
    col_name = col.get("name", "")

    if re.search(r"\b(dtype|data type|type)\b", q):
        return f"{col_name} is typed as {col.get('type', 'unknown')}."
    if re.search(r"\b(null|missing|nan|na)\b", q):
        pct = col.get("null_pct", 0)
        count = col.get("nulls")
        suffix = f" ({count} values)" if count is not None else ""
        return f"{col_name} has {pct}% missing values{suffix}."
    if re.search(r"\b(unique|cardinality|distinct)\b", q):
        unique = col.get("unique")
        if unique is None:
            unique = _series_stat(dataset, col_name, "unique")
        return f"{col_name} has {unique} unique non-null values." if unique is not None else None
    if re.search(r"\b(most common|top value|mode|frequent|frequency)\b", q):
        if col.get("top") is not None:
            freq = col.get("freq")
            pct = col.get("freq_pct")
            bits = [f"The most common value in {col_name} is {col.get('top')}"]
            if freq is not None:
                bits.append(f"with {freq} rows")
            if pct is not None:
                bits.append(f"({pct}%)")
            return " ".join(bits) + "."
        mode = _series_stat(dataset, col_name, "mode")
        if mode:
            return f"The most common value in {col_name} is {mode['value']} with {mode['count']} rows ({mode['pct']}%)."
        return None

    stat_terms = {
        "mean": "mean",
        "average": "mean",
        "median": "median",
        "minimum": "min",
        "min": "min",
        "maximum": "max",
        "max": "max",
        "standard deviation": "std",
        "std": "std",
        "sum": "sum",
    }
    for term, stat in stat_terms.items():
        if re.search(rf"\b{re.escape(term)}\b", q):
            value = col.get(stat)
            if value is None:
                value = _series_stat(dataset, col_name, stat)
            return f"The {term} of {col_name} is {value}." if value is not None else None

    return None


async def _collect_ai(messages: list[dict], provider: str, model: str | None, api_key: str | None) -> str:
    out = ""
    async for token in stream_ai(messages, provider, model, api_key):
        out += token
    return out


def _extract_json_object(text: str) -> dict | None:
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def _schema_brief(dataset: dict) -> str:
    lines = []
    for col in dataset.get("schema", []):
        bits = [col.get("name", ""), col.get("type", "unknown")]
        if col.get("null_pct", 0):
            bits.append(f"{col.get('null_pct')}% missing")
        if col.get("unique") is not None:
            bits.append(f"{col.get('unique')} unique")
        lines.append(" - " + " | ".join(str(b) for b in bits if b != ""))
    return "\n".join(lines)


async def _dataframe_tool_answer(
    dataset: dict,
    question: str,
    provider: str,
    model: str | None,
    api_key: str | None,
) -> str | None:
    if not is_dataframe_question(question):
        return None

    code_messages = [
        {
            "role": "system",
            "content": f"""You convert data questions into one safe pandas expression.

Dataset shape: {dataset.get('shape', {})}
Columns:
{_schema_brief(dataset)}

Return strict JSON only:
{{"code":"result = ..."}}

Rules:
- Use the existing dataframe variable df.
- The code must assign to result.
- Do not import anything.
- Do not use direct functions like len().
- Prefer groupby/value_counts/corr/describe/head/sort_values.
- Cap large outputs with .head(20).""",
        },
        {"role": "user", "content": question},
    ]
    try:
        raw = await _collect_ai(code_messages, provider, model, api_key)
        parsed = _extract_json_object(raw)
        code = (parsed or {}).get("code", "")
        if not code.strip().startswith("result"):
            return None
        result = execute_pandas_code(dataset["id"], code)
    except Exception:
        return None

    explain_messages = [
        {
            "role": "system",
            "content": "You are a concise data analyst. Explain the computed pandas result in plain English. Do not mention implementation details unless useful.",
        },
        {
            "role": "user",
            "content": f"Question: {question}\nComputed result JSON: {json.dumps(result, ensure_ascii=False, default=str)[:6000]}",
        },
    ]
    try:
        return await _collect_ai(explain_messages, provider, model, api_key)
    except Exception:
        return f"Computed result: {json.dumps(result.get('result'), ensure_ascii=False, default=str)[:2000]}"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/ai/status")
async def ollama_status():
    return await get_ollama_status()


@router.post("/datasets/{dataset_id}/insight")
async def generate_dataset_insight(dataset_id: str, req: InsightRequest = InsightRequest()):
    dataset = get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    local_model = None
    status = None
    if req.provider == "local":
        status = await get_ollama_status()
        local_model = status.get("active_model")
    model = _provider_model(req.provider, req.model, local_model)
    data_hash = _data_hash(dataset)

    cached = get_cached_insight(dataset, req.provider, model, data_hash)
    if cached:
        return cached

    if req.provider == "local":
        if not status["running"]:
            raise HTTPException(status_code=503, detail="Ollama is not running")
        if not model:
            raise HTTPException(status_code=503, detail="No Ollama model available")
        try:
            insight = await generate_insight(
                schema=dataset.get("schema", []), shape=dataset.get("shape", {}),
                filename=dataset.get("filename", ""), model=model,
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=humanize_error(e, "local"))
        save_insight(dataset_id, insight, model, req.provider, data_hash)
        return {"insight": insight, "model": model}

    system = _full_system(dataset)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": "Write a concise 3-paragraph data quality and insight report. Cover what the dataset contains, quality issues, and key recommendations."},
    ]
    try:
        out = ""
        async for tok in stream_ai(messages, req.provider, model, req.api_key):
            out += tok
        save_insight(dataset_id, out, model, req.provider, data_hash)
        return {"insight": out, "model": model}
    except Exception as e:
        raise HTTPException(status_code=502, detail=humanize_error(e, req.provider))


@router.post("/datasets/{dataset_id}/chat")
async def chat_with_dataset(dataset_id: str, req: ChatRequest):
    dataset = get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    latest_user = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
    deterministic = _deterministic_answer(dataset, latest_user)
    if deterministic:
        async def deterministic_stream():
            yield f"data: {json.dumps({'token': deterministic, 'source': 'deterministic'})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(deterministic_stream(), media_type="text/event-stream")

    if req.provider == "local":
        status = await get_ollama_status()
        if not status["running"]:
            raise HTTPException(status_code=503, detail="Ollama is not running")

    # ── Smart context compression ──────────────────────────────────────────
    # First message: send full schema so model knows the dataset
    # Provider switch: send compressed workspace summary (10x cheaper)
    # Subsequent messages: no system re-injection, just the conversation
    if req.switched_provider:
        system = _workspace_summary(dataset)
    elif req.is_first_message:
        system = _full_system(dataset)
    else:
        system = None  # model already has context from earlier in this session

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages += [{"role": m.role, "content": m.content} for m in req.messages]

    model = req.model
    if req.provider == "local" and not model:
        status = await get_ollama_status()
        model = status.get("active_model")
    model = _provider_model(req.provider, model)

    dataframe_answer = await _dataframe_tool_answer(dataset, latest_user, req.provider, model, req.api_key)
    if dataframe_answer:
        async def dataframe_stream():
            yield f"data: {json.dumps({'token': dataframe_answer, 'source': 'dataframe_tool'})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(dataframe_stream(), media_type="text/event-stream")

    async def token_stream():
        try:
            async for token in stream_ai(messages, req.provider, model, req.api_key):
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            msg = humanize_error(e, req.provider)
            yield f"data: {json.dumps({'error': msg})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(token_stream(), media_type="text/event-stream")
