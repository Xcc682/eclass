"""应用配置：所有可调参数集中在此，通过 .env 或环境变量覆盖。"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    APP_NAME: str = "思政情景工坊 API"
    VERSION: str = "1.0.0"
    ENV: str = "development"

    # Database
    DATABASE_URL: str = "sqlite:///./dev.db"
    DATABASE_URL_SYNC: str = "sqlite:///./dev.db"
    VECTOR_DATABASE_URL: str | None = None

    # Redis
    REDIS_URL: str = "redis://127.0.0.1:6379/0"

    # JWT
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # LLM
    LLM_API_KEY: str | None = None
    LLM_API_BASE: str = "https://api.deepseek.com"
    LLM_MODEL: str = "deepseek-v4-flash"
    EMBEDDING_MODEL: str = "BAAI/bge-small-zh-v1.5"
    EMBEDDING_DIMENSION: int = 512
    VECTOR_MAX_COSINE_DISTANCE: float = 0.55
    KNOWLEDGE_RETRIEVAL_TIMEOUT_SECONDS: float = 12.0
    KNOWLEDGE_KEYWORD_FALLBACK_TIMEOUT_SECONDS: float = 5.0
    KNOWLEDGE_LLM_TIMEOUT_SECONDS: float = 45.0
    # Debate turns can contain a long transcript. Bound the prompt independently
    # from the stored session and allow slightly more time to generate a reply.
    DEBATE_LLM_TIMEOUT_SECONDS: float = 60.0
    DEBATE_HISTORY_MAX_CHARS: int = 12000
    DEBATE_HISTORY_MESSAGE_MAX_CHARS: int = 1400
    DEBATE_ARGUMENT_MAX_CHARS: int = 6000
    DEBATE_EVIDENCE_MAX_ITEMS: int = 4
    DEBATE_EVIDENCE_ITEM_MAX_CHARS: int = 600
    DEBATE_REPORT_HISTORY_MAX_CHARS: int = 24000

    # Knowledge base
    KNOWLEDGE_STORAGE_DIR: str = "storage/knowledge"
    KNOWLEDGE_MAX_UPLOAD_MB: int = 20
    COMMUNITY_STORAGE_DIR: str = "storage/community"
    COMMUNITY_SENSITIVE_TERMS: str = ""
    ADMIN_PHONES: str = ""
    TEACHER_PHONES: str = ""

    # Immersive media.  Local files remain supported; production may point the
    # same S3-compatible settings at MinIO, OSS or COS.
    IMMERSIVE_MEDIA_DIR: str = "storage/immersive"
    MEDIA_BASE_URL: str = ""
    S3_ENDPOINT: str | None = None
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None
    S3_BUCKET: str = "immersive-media"
    S3_REGION: str = "us-east-1"

    # Development authentication. Production deployments must configure an
    # SMS provider and set ENV=production; the code is never returned there.
    DEV_SMS_CODE: str = "123456"

    # Yiban
    YIBAN_APP_ID: str | None = None
    YIBAN_APP_SECRET: str | None = None
    YIBAN_REDIRECT_URI: str | None = None

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: str = "http://127.0.0.1:5667,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
