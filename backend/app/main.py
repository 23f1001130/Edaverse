import os
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from app.routers import upload, datasets, eda, ai, cleaning, demo, features
from app.services.store import cleanup_expired_datasets

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
    except Exception:
        pass

app = FastAPI(title="edaverse API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api")
app.include_router(datasets.router, prefix="/api")
app.include_router(eda.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(cleaning.router, prefix="/api")
app.include_router(demo.router, prefix="/api")
app.include_router(features.router, prefix="/api")


@app.on_event("startup")
def cleanup_anonymous_datasets_on_startup():
    cleanup_expired_datasets()

@app.get("/")
def root():
    return {"status": "ok", "message": "edaverse API is running"}

@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)
