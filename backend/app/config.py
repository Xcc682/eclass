from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "思政情景工坊 API"
    VERSION: str = "1.0.0"
    ENV: str = "development"

    # Database
    DATABASE_URL: str = "sqlite:///./dev.db"
    DATABASE_URL_SYNC: str = "sqlite:///./dev.db"
    VECTOR_DATABASE_URL: Optional[str] = None

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # LLM
    LLM_API_KEY: Optional[str] = None
    LLM_API_BASE: str = "https://api.deepseek.com"
    LLM_MODEL: str = "deepseek-chat"
    EMBEDDING_MODEL: str = "BAAI/bge-small-zh-v1.5"
    EMBEDDING_DIMENSION: int = 512
    VECTOR_MAX_COSINE_DISTANCE: float = 0.55
    KNOWLEDGE_RETRIEVAL_TIMEOUT_SECONDS: float = 12.0
    KNOWLEDGE_KEYWORD_FALLBACK_TIMEOUT_SECONDS: float = 5.0
    KNOWLEDGE_LLM_TIMEOUT_SECONDS: float = 45.0

    # Knowledge base
    KNOWLEDGE_STORAGE_DIR: str = "storage/knowledge"
    KNOWLEDGE_MAX_UPLOAD_MB: int = 20
    ADMIN_PHONES: str = ""
    TEACHER_PHONES: str = ""

    # Immersive media.  Local files remain supported; production may point the
    # same S3-compatible settings at MinIO, OSS or COS.
    IMMERSIVE_MEDIA_DIR: str = "storage/immersive"
    MEDIA_BASE_URL: str = ""
    S3_ENDPOINT: Optional[str] = None
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None
    S3_BUCKET: str = "immersive-media"
    S3_REGION: str = "us-east-1"

    # Development authentication. Production deployments must configure an
    # SMS provider and set ENV=production; the code is never returned there.
    DEV_SMS_CODE: str = "123456"

    # Yiban
    YIBAN_APP_ID: Optional[str] = None
    YIBAN_APP_SECRET: Optional[str] = None
    YIBAN_REDIRECT_URI: Optional[str] = None

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5667,http://127.0.0.1:5667"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
