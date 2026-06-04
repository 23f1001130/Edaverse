"""Unified AI provider layer — local Ollama or user's own cloud key."""
import json
import re
import httpx
from typing import AsyncGenerator

OLLAMA_BASE = "http://localhost:11434"


async def stream_ollama(messages: list, model: str) -> AsyncGenerator[str, None]:
    payload = {"model": model, "messages": messages, "stream": True}
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


async def stream_openai(messages: list, model: str, api_key: str, base_url: str) -> AsyncGenerator[str, None]:
    """Works for OpenAI and Groq (OpenAI-compatible)."""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "stream": True}
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", f"{base_url}/chat/completions", headers=headers, json=payload) as r:
            if r.status_code != 200:
                body = await r.aread()
                raise ValueError(f"Provider error {r.status_code}: {body.decode()[:200]}")
            async for line in r.aiter_lines():
                if not line.startswith("data: "):
                    continue
                chunk = line[6:]
                if chunk.strip() == "[DONE]":
                    break
                try:
                    data = json.loads(chunk)
                    token = data["choices"][0]["delta"].get("content", "")
                    if token:
                        yield token
                except Exception:
                    continue


async def stream_anthropic(messages: list, model: str, api_key: str) -> AsyncGenerator[str, None]:
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    # Anthropic uses a separate system param. Cache the large dataset context
    # so multi-turn chat pays the full schema prompt cost only once per cache window.
    system_parts = []
    conv = []
    for m in messages:
        if m["role"] == "system":
            system_parts.append({
                "type": "text",
                "text": m["content"],
                "cache_control": {"type": "ephemeral"},
            })
        else:
            conv.append(m)
    system = system_parts or "You are a helpful data analyst."
    payload = {
        "model": model, "max_tokens": 1024, "stream": True,
        "system": system,
        "messages": conv,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", "https://api.anthropic.com/v1/messages", headers=headers, json=payload) as r:
            if r.status_code != 200:
                body = await r.aread()
                raise ValueError(f"Anthropic error {r.status_code}: {body.decode()[:200]}")
            async for line in r.aiter_lines():
                if not line.startswith("data: "):
                    continue
                try:
                    data = json.loads(line[6:])
                    if data.get("type") == "content_block_delta":
                        token = data["delta"].get("text", "")
                        if token:
                            yield token
                except Exception:
                    continue


# Default models per provider
DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "groq": "llama-3.3-70b-versatile",
    # Cheap cloud default. Sonnet/Opus remain selectable from the UI for opt-in escalation.
    "anthropic": "claude-haiku-4-5",
}
BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "groq": "https://api.groq.com/openai/v1",
}


def humanize_error(err: Exception, provider: str) -> str:
    msg = str(err).strip() or err.__class__.__name__

    if "requires an API key" in msg:
        return f"{provider} API key is required."
    if "Unknown provider" in msg:
        return msg

    if isinstance(err, (httpx.ConnectError, httpx.ConnectTimeout)):
        if provider == "local":
            return "Ollama is not reachable. Make sure it is running on http://localhost:11434."
        return f"Could not connect to {provider} API. Check your network and base URL."
    if isinstance(err, (httpx.ReadTimeout, httpx.TimeoutException)):
        return f"{provider} request timed out. Please try again."

    if isinstance(err, ValueError) and ("Provider error" in msg or "Anthropic error" in msg):
        match = re.search(r"(?:Provider|Anthropic) error (\d{3})", msg)
        if match:
            code = int(match.group(1))
            if code in (401, 403):
                return f"{provider} rejected the API key. Check credentials and permissions."
            if code == 429:
                return f"{provider} rate limit reached. Please try again later."
            if code == 400:
                return f"{provider} request was invalid. Check the model name and parameters."
            if code >= 500:
                return f"{provider} is currently unavailable (error {code})."
        return f"{provider} API error. Please try again."

    return f"{provider} error: {msg[:200]}"


async def stream_ai(messages: list, provider: str, model: str | None,
                    api_key: str | None) -> AsyncGenerator[str, None]:
    """Route to the right provider."""
    if provider == "local":
        async for t in stream_ollama(messages, model or "llama3.2:3b"):
            yield t
    elif provider in ("openai", "groq"):
        if not api_key:
            raise ValueError(f"{provider} requires an API key")
        m = model or DEFAULT_MODELS[provider]
        async for t in stream_openai(messages, m, api_key, BASE_URLS[provider]):
            yield t
    elif provider == "anthropic":
        if not api_key:
            raise ValueError("anthropic requires an API key")
        m = model or DEFAULT_MODELS["anthropic"]
        async for t in stream_anthropic(messages, m, api_key):
            yield t
    else:
        raise ValueError(f"Unknown provider: {provider}")
