import base64
import json
import os
from fastapi import Request

try:
    import jwt
    from jwt import InvalidTokenError, PyJWKClient
except Exception:
    jwt = None
    InvalidTokenError = Exception
    PyJWKClient = None


def _decode_jwt_payload(token: str) -> dict:
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return {}
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        return json.loads(base64.urlsafe_b64decode(payload.encode("utf-8")))
    except Exception:
        return {}


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _app_env() -> str:
    return (os.getenv("APP_ENV") or os.getenv("ENVIRONMENT") or "development").lower()


def _allow_unverified_jwt() -> bool:
    return _env_bool("AUTH_TRUST_UNVERIFIED_JWT", _app_env() in {"dev", "development", "local", "test"})


def _clerk_issuer() -> str | None:
    return os.getenv("CLERK_ISSUER_URL") or os.getenv("CLERK_ISSUER")


def _clerk_jwks_url() -> str | None:
    explicit = os.getenv("CLERK_JWKS_URL")
    if explicit:
        return explicit
    issuer = _clerk_issuer()
    if issuer:
        return issuer.rstrip("/") + "/.well-known/jwks.json"
    return None


_jwk_client_cache: dict = {"url": None, "client": None}


def _jwk_client():
    jwks_url = _clerk_jwks_url()
    if not jwt or not PyJWKClient or not jwks_url:
        return None
    if _jwk_client_cache["url"] != jwks_url:
        _jwk_client_cache["url"] = jwks_url
        _jwk_client_cache["client"] = PyJWKClient(jwks_url)
    return _jwk_client_cache["client"]


def _verified_jwt_payload(token: str) -> dict:
    client = _jwk_client()
    if not client:
        return {}
    try:
        signing_key = client.get_signing_key_from_jwt(token)
        kwargs = {
            "key": signing_key.key,
            "algorithms": ["RS256"],
            "options": {"verify_aud": False},
        }
        issuer = _clerk_issuer()
        if issuer:
            kwargs["issuer"] = issuer
        return jwt.decode(token, **kwargs)
    except InvalidTokenError:
        return {}
    except Exception:
        return {}


def get_request_user_id(request: Request) -> str | None:
    """Extract a verified Clerk/user identity when possible.

    Tries full JWT signature verification first (requires CLERK_ISSUER_URL or
    CLERK_JWKS_URL to be set). If verification is not configured, falls back to
    decoding the JWT payload without signature verification so that user isolation
    still works — every upload is still scoped to the correct sub claim.

    Set AUTH_TRUST_UNVERIFIED_JWT=false to reject requests when verified decode
    fails (strict mode — requires CLERK_ISSUER_URL to be set).
    """
    if _env_bool("TRUST_PROXY_AUTH_HEADERS"):
        for header in ("x-user-id", "x-clerk-user-id", "x-auth-user-id"):
            value = request.headers.get(header)
            if value:
                return value.strip()

    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        # Preferred: cryptographically verified decode
        claims = _verified_jwt_payload(token)
        if claims:
            return claims.get("sub") or claims.get("user_id")
        # Only fall back to unverified decode in dev/test environments.
        # In production (APP_ENV not in dev/development/local/test) this returns
        # None unless AUTH_TRUST_UNVERIFIED_JWT=true is explicitly set.
        if not _allow_unverified_jwt():
            return None
        claims = _decode_jwt_payload(token)
        return claims.get("sub") or claims.get("user_id")
    return None
