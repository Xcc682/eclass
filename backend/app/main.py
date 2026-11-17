"""Sixiang Qingjing Gongfang - FastAPI Backend"""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.config import settings
from app.database import SessionLocal, init_db
from app.routers import (
    ai_ops_router,
    auth_router,
    community_router,
    debates_router,
    history_router,
    immersive_router,
    interviews_router,
    knowledge_router,
    tours_router,
    tts_router,
    users_router,
)
from app.seed import seed_data
from app.services.knowledge_service import start_embedding_warmup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """应用启动与关闭钩子：校验配置、初始化数据库、灌入种子数据。"""
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if not settings.JWT_SECRET_KEY or (settings.ENV == "production" and len(settings.JWT_SECRET_KEY) < 32):
        raise RuntimeError("JWT_SECRET_KEY 未配置或强度不足")
    if settings.ENV in {"development", "test"}:
        init_db()
    seed_data()
    start_embedding_warmup()
    logger.info("%s started on port %s", settings.APP_NAME, settings.PORT)
    yield
    logger.info("%s shutting down", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)
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
app.include_router(tts_router)
app.include_router(ai_ops_router)

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
