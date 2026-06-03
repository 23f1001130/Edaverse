from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from app.routers import upload, datasets, eda, ai, cleaning, demo

app = FastAPI(title="edaverse API", version="0.2.0")

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

@app.get("/")
def root():
    return {"status": "ok", "message": "edaverse API is running"}

@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)
