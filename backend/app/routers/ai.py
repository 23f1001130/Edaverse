import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.ollama import get_ollama_status, generate_insight
from app.services.ai_providers import stream_ai, humanize_error
from app.services.store import get_dataset, save_insight

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
            line += f" — range [{c['min']}–{c['max']}], mean {c['mean']}"
        if c.get('unique') is not None:
            line += f" — {c['unique']} unique, top: {c.get('top')} ({c.get('freq_pct')}%)"
        col_lines.append(line)

    return f"""You are a data analyst assistant. The user is working with this dataset:

File: {filename}
Shape: {shape.get('rows','?')} rows × {shape.get('columns','?')} columns

Columns:
{chr(10).join(col_lines)}

Top columns by missing values: {null_summary}

RULES:
- Answer factual questions directly from the schema above. Never write code for things you already know.
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


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/ai/status")
async def ollama_status():
    return await get_ollama_status()


@router.post("/datasets/{dataset_id}/insight")
async def generate_dataset_insight(dataset_id: str, req: InsightRequest = InsightRequest()):
    dataset = get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if req.provider == "local" and dataset.get("insight"):
        return {"insight": dataset["insight"], "model": dataset.get("insight_model")}

    if req.provider == "local":
        status = await get_ollama_status()
        if not status["running"]:
            raise HTTPException(status_code=503, detail="Ollama is not running")
        model = req.model or status["active_model"]
        if not model:
            raise HTTPException(status_code=503, detail="No Ollama model available")
        try:
            insight = await generate_insight(
                schema=dataset.get("schema", []), shape=dataset.get("shape", {}),
                filename=dataset.get("filename", ""), model=model,
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=humanize_error(e, "local"))
        save_insight(dataset_id, insight, model)
        return {"insight": insight, "model": model}

    system = _full_system(dataset)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": "Write a concise 3-paragraph data quality and insight report. Cover what the dataset contains, quality issues, and key recommendations."},
    ]
    try:
        out = ""
        async for tok in stream_ai(messages, req.provider, req.model, req.api_key):
            out += tok
        return {"insight": out, "model": req.model or req.provider}
    except Exception as e:
        raise HTTPException(status_code=502, detail=humanize_error(e, req.provider))


@router.post("/datasets/{dataset_id}/chat")
async def chat_with_dataset(dataset_id: str, req: ChatRequest):
    dataset = get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

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

    async def token_stream():
        try:
            async for token in stream_ai(messages, req.provider, model, req.api_key):
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            msg = humanize_error(e, req.provider)
            yield f"data: {json.dumps({'error': msg})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(token_stream(), media_type="text/event-stream")
