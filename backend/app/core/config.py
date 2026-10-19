import re

from pydantic import Field, field_validator
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

    # Language model (app/services/llm_client.py). "ollama" uses the local
    # Ollama server below; "openai" uses any OpenAI-compatible API (Groq,
    # OpenRouter, ...) at LLM_BASE_URL -- for Groq,
    # https://api.groq.com/openai/v1 with a model such as llama-3.3-70b-versatile.
    LLM_PROVIDER: str = "ollama"
    LLM_BASE_URL: str = ""
    LLM_API_KEY: str = ""
    LLM_MODEL: str = ""

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
    # Optional pattern for further origins, such as Vercel preview deployments:
    # ^https://nutrimed-[a-z0-9-]+-your-team\.vercel\.app$
    ALLOWED_ORIGIN_REGEX: str = ""

    # Public URL of the web app, used to build links in emails (password reset).
    # A request's Origin header wins when it is one of ALLOWED_ORIGINS.
    FRONTEND_URL: str = "http://localhost:3000"
    PASSWORD_RESET_EXPIRY_MINUTES: int = 30

    # How long request audit logs are kept before MongoDB expires them.
    AUDIT_LOG_RETENTION_DAYS: int = 365

    # Where the visitor's IP address comes from, for rate limiting and the
    # audit log (app/middleware/client_ip.py). Empty: the connecting address,
    # which is right behind our nginx. Behind a hosting proxy such as Render's,
    # the header that proxy sets; the address is read CLIENT_IP_HOPS entries
    # from the right of it, so whatever a client sends in it is ignored.
    CLIENT_IP_HEADER: str = ""
    CLIENT_IP_HOPS: int = Field(default=1, ge=1)

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

    @field_validator("OCR_SERVICE_URL")
    @classmethod
    def _default_ocr_scheme(cls, value: str) -> str:
        # Render gives a private service's address as host:port, without a scheme.
        value = value.strip().rstrip("/")
        return value if "://" in value else f"http://{value}"

    @field_validator("ALLOWED_ORIGIN_REGEX")
    @classmethod
    def _valid_origin_regex(cls, value: str) -> str:
        try:
            re.compile(value)
        except re.error as exc:
            raise ValueError(f"not a valid regular expression: {exc}") from exc
        return value


settings = Settings()
