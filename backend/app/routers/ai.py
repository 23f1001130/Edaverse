import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.ollama import get_ollama_status, stream_chat, generate_insight
from app.services.store import get_dataset, save_insight

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    model: str | None = None


@router.get("/ai/status")
async def ollama_status():
    return await get_ollama_status()


@router.post("/datasets/{dataset_id}/insight")
async def generate_dataset_insight(dataset_id: str):
    dataset = get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    status = await get_ollama_status()
    if not status["running"]:
        raise HTTPException(status_code=503, detail="Ollama is not running")
    if not status["active_model"]:
        raise HTTPException(status_code=503, detail="No model available")

    # Return cached insight if exists
    if dataset.get("insight"):
        return {"insight": dataset["insight"], "model": dataset.get("insight_model")}

    insight = await generate_insight(
        schema=dataset.get("schema", []),
        shape=dataset.get("shape", {}),
        filename=dataset.get("filename", ""),
        model=status["active_model"],
    )

    save_insight(dataset_id, insight, status["active_model"])
    return {"insight": insight, "model": status["active_model"]}


@router.post("/datasets/{dataset_id}/chat")
async def chat_with_dataset(dataset_id: str, req: ChatRequest):
    dataset = get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    status = await get_ollama_status()
    if not status["running"]:
        raise HTTPException(status_code=503, detail="Ollama is not running")

    model = req.model or status["active_model"]
    if not model:
        raise HTTPException(status_code=503, detail="No model available")

    # Build system context from dataset schema
    schema = dataset.get("schema", [])
    shape = dataset.get("shape", {})
    filename = dataset.get("filename", "")

    col_lines = []
    for c in schema:
        line = f"  - {c['name']} ({c['type']})"
        if c.get('null_pct', 0) > 0:
            line += f" — {c['null_pct']}% missing"
        if c.get('min') is not None:
            line += f" — range [{c['min']}–{c['max']}], mean {c['mean']}"
        if c.get('top_values'):
            line += f" — values: {', '.join(str(v) for v in c['top_values'][:5])}"
        col_lines.append(line)

    # Pre-compute null rankings from schema so model doesn't need to guess
    null_ranked = sorted(schema, key=lambda c: c.get('null_pct', 0), reverse=True)
    null_summary = ', '.join(
        f"{c['name']} ({c.get('null_pct', 0)}%)"
        for c in null_ranked[:5] if c.get('null_pct', 0) > 0
    ) or "none"

    system = f"""You are a data analyst assistant. The user is working with this dataset:

File: {filename}
Shape: {shape.get('rows', '?')} rows × {shape.get('columns', '?')} columns

Columns:
{chr(10).join(col_lines)}

Top columns by missing values: {null_summary}

RULES:
- Answer factual questions directly using the stats above. Do NOT write code to answer things you already know from the schema.
- Example: "which column has most nulls?" → answer directly from the null stats above.
- Only write Python/pandas code when the user explicitly asks for code or says "write", "generate", "give me code".
- Keep answers short and direct. Use bullet points for lists.
- Always reference actual column names and real numbers from the schema."""

    messages = [{"role": "system", "content": system}]
    messages += [{"role": m.role, "content": m.content} for m in req.messages]

    async def token_stream():
        async for token in stream_chat(messages, model):
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(token_stream(), media_type="text/event-stream")
