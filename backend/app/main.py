"""Sixiang Qingjing Gongfang - FastAPI Backend"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.config import settings
from app.database import SessionLocal, init_db
from sqlalchemy import text
from app.seed import seed_data
from app.services.knowledge_service import start_embedding_warmup
from app.routers import (
    auth_router, users_router, interviews_router,
    history_router, tours_router, debates_router, knowledge_router, community_router, immersive_router
)

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION, docs_url="/docs", redoc_url="/redoc")
Path(settings.IMMERSIVE_MEDIA_DIR).mkdir(parents=True, exist_ok=True)
app.mount("/media/immersive/images", StaticFiles(directory="app/static/immersive/images", check_dir=False), name="immersive-images")
app.mount("/media", StaticFiles(directory=str(Path(settings.IMMERSIVE_MEDIA_DIR).parent), check_dir=False), name="media")

cors_origins = [item.strip() for item in settings.CORS_ORIGINS.split(",") if item.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or [],
    allow_credentials="*" not in cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(interviews_router)
app.include_router(history_router)
app.include_router(tours_router)
app.include_router(debates_router)
app.include_router(knowledge_router)
app.include_router(community_router)
app.include_router(immersive_router)

@app.on_event("startup")
def on_startup():
    import os
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if not settings.JWT_SECRET_KEY or (settings.ENV == "production" and len(settings.JWT_SECRET_KEY) < 32):
        raise RuntimeError("JWT_SECRET_KEY 未配置或强度不足")
    if settings.ENV in {"development", "test"}:
        init_db()
    seed_data()
    start_embedding_warmup()
    print(f"[OK] {settings.APP_NAME} started on port {settings.PORT}")

@app.get("/")
def root():
    return {"name": settings.APP_NAME, "version": settings.VERSION, "status": "running"}

@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/health/live")
def health_live():
    return {"status": "alive"}


@app.get("/health/ready")
def health_ready():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"status": "not_ready", "database": "unavailable", "error": exc.__class__.__name__}) from exc
    return {"status": "ready", "database": "available"}
