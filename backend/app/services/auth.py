import base64
import json
from fastapi import Request


def _decode_jwt_payload(token: str) -> dict:
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return {}
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        return json.loads(base64.urlsafe_b64decode(payload.encode("utf-8")))
    except Exception:
        return {}


def get_request_user_id(request: Request) -> str | None:
    """Best-effort Clerk/user identity extraction.

    Production Clerk verification can sit in middleware or an API gateway. This helper
    keeps the app backward-compatible while preserving ownership metadata when the
    request already carries a trusted user id or JWT.
    """
    for header in ("x-user-id", "x-clerk-user-id", "x-auth-user-id"):
        value = request.headers.get(header)
        if value:
            return value.strip()

    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        claims = _decode_jwt_payload(auth.split(" ", 1)[1].strip())
        return claims.get("sub") or claims.get("user_id")
    return None
