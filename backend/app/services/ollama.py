import httpx
import json
from typing import AsyncGenerator

OLLAMA_BASE = "http://localhost:11434"
PREFERRED_MODELS = ["llama3.2:3b", "llama3.2", "llama3", "mistral", "phi3"]


async def get_ollama_status() -> dict:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{OLLAMA_BASE}/api/tags")
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
                active = next((m for m in PREFERRED_MODELS if any(m in x for x in models)), None)
                if not active and models:
                    active = models[0]
                return {"running": True, "models": models, "active_model": active}
    except Exception:
        pass
    return {"running": False, "models": [], "active_model": None}


async def stream_chat(messages: list, model: str) -> AsyncGenerator[str, None]:
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", f"{OLLAMA_BASE}/api/chat", json=payload) as r:
            async for line in r.aiter_lines():
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    token = data.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if data.get("done"):
                        break
                except Exception:
                    continue


async def generate_insight(schema: list, shape: dict, filename: str, model: str) -> str:
    """Single-shot insight generation — called once on upload."""
    
    col_summary = []
    for c in schema:
        s = f"- {c['name']} ({c['type']})"
        if c.get('null_pct', 0) > 0:
            s += f", {c['null_pct']}% missing"
        if c.get('min') is not None:
            s += f", range [{c['min']} – {c['max']}], mean {c['mean']}"
        if c.get('top_values'):
            s += f", top values: {', '.join(str(v) for v in c['top_values'][:3])}"
        col_summary.append(s)

    prompt = f"""You are a data analyst. A user uploaded a dataset called "{filename}".

Dataset overview:
- {shape['rows']} rows, {shape['columns']} columns

Columns:
{chr(10).join(col_summary)}

Write a concise data quality and insight report (3-4 short paragraphs). Cover:
1. What this dataset appears to contain
2. Data quality issues (missing values, suspicious columns, type issues)
3. Interesting patterns or relationships worth investigating
4. Specific recommendations for analysis

Be direct and specific. No fluff. Reference actual column names and numbers."""

    messages = [{"role": "user", "content": prompt}]
    result = ""
    async for token in stream_chat(messages, model):
        result += token
    return result
