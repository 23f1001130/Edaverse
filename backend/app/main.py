import os
import uuid
import logging
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.routers import upload, datasets, eda, ai, cleaning, demo, features
from app.services.limiter import limiter
from app.services.store import cleanup_expired_datasets, _anonymous_ttl_hours

logger = logging.getLogger(__name__)

SENTRY_DSN = os.getenv("SENTRY_DSN") or os.getenv("BACKEND_SENTRY_DSN")
if SENTRY_DSN:
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            environment=os.getenv("SENTRY_ENVIRONMENT", os.getenv("APP_ENV", "production")),
            release=os.getenv("SENTRY_RELEASE"),
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            send_default_pii=False,
        )
    except (ImportError, ValueError, RuntimeError) as exc:
        logger.warning("Sentry initialization skipped: %s: %s", type(exc).__name__, exc)

class _RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


app = FastAPI(title="edaverse API", version="0.3.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(_RequestIDMiddleware)


def _csv_env(*names: str) -> list[str]:
    values: list[str] = []
    for name in names:
        raw = os.getenv(name, "")
        values.extend(v.strip() for v in raw.split(",") if v.strip())
    return values


def _cors_origins() -> list[str]:
    configured = _csv_env("CORS_ALLOWED_ORIGINS", "ALLOWED_ORIGINS")
    if configured:
        return configured
    app_url = os.getenv("DATAFLOW_APP_URL") or os.getenv("VITE_APP_URL")
    if app_url:
        return [app_url.rstrip("/")]
    if (os.getenv("APP_ENV") or os.getenv("ENVIRONMENT") or "development").lower() in {"dev", "development", "local", "test"}:
        return ["http://localhost:5173", "http://127.0.0.1:5173"]
    return []


cors_origins = _cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=bool(cors_origins),
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

app.include_router(upload.router, prefix="/api")
app.include_router(datasets.router, prefix="/api")
app.include_router(eda.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(cleaning.router, prefix="/api")
app.include_router(demo.router, prefix="/api")
app.include_router(features.router, prefix="/api")


@app.on_event("startup")
async def cleanup_anonymous_datasets_on_startup():
    import asyncio
    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, cleanup_expired_datasets)

@app.get("/health")
def health():
    from app.services.store import storage_info
    try:
        info = storage_info()
    except (OSError, RuntimeError, ValueError) as exc:
        logger.warning("Health storage check failed: %s: %s", type(exc).__name__, exc)
        info = {"storage": "local", "datasets_count": 0}
    return {"status": "ok", **info}

@app.get("/api/config")
def get_app_config():
    return {
        "ai_provider": os.getenv("AI_PROVIDER", "ollama"),
        "max_upload_mb": int(os.getenv("MAX_UPLOAD_MB", "100")),
        "large_file_threshold_mb": int(os.getenv("LARGE_FILE_THRESHOLD_MB", "50")),
        "anonymous_ttl_hours": _anonymous_ttl_hours(),
    }

@app.get("/")
def root():
    return {"status": "ok", "message": "edaverse API is running"}

@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)
