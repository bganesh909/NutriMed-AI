from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "NutriMed AI"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # MongoDB
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "nutrimed_ai"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # RabbitMQ
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672//"

    # Celery broker. Defaults to Redis (already running locally and avoids the
    # RabbitMQ 4.x transient-queue restriction). Override via env for other brokers.
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"

    # JWT
    JWT_SECRET: str = "change-me-in-production-use-a-strong-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 30

    # Ollama (local LLM)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "mistral:7b"
    # Generous by default: a 7B model on CPU can take several minutes for the
    # longer diet/workout prompts. Raise further on slower hardware.
    LLM_TIMEOUT_SECONDS: float = 300.0

    # OCR microservice
    OCR_SERVICE_URL: str = "http://localhost:8001"

    # AES encryption for reports
    AES_KEY: str = "change-me-32-byte-base64-key-here"

    # CORS
    ALLOWED_ORIGINS: list[str] = Field(default=["http://localhost:3000", "http://localhost:5173"])

    # Public URL of the web app, used to build links in emails (password reset).
    # A request's Origin header wins when it is one of ALLOWED_ORIGINS.
    FRONTEND_URL: str = "http://localhost:3000"
    PASSWORD_RESET_EXPIRY_MINUTES: int = 30

    # How long request audit logs are kept before MongoDB expires them.
    AUDIT_LOG_RETENTION_DAYS: int = 365

    # Outgoing email. With SMTP_HOST unset, emails are written to the log
    # instead of being sent (local development).
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "NutriMed AI <no-reply@nutrimed.ai>"
    SMTP_USE_TLS: bool = True

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        # The .env file is shared with docker-compose and the frontend
        # (NEXT_PUBLIC_API_URL, ...); keys this class does not define are not errors.
        "extra": "ignore",
    }


settings = Settings()
