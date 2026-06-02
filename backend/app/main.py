from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import upload, datasets, eda, ai, cleaning

app = FastAPI(title="Dataflow API", version="0.1.0")

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

@app.get("/")
def root():
    return {"status": "ok", "message": "Dataflow API is running"}
