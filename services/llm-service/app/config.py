from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    SERVICE_NAME: str = "llm-service"
    SERVICE_VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8003

    OLLAMA_BASE_URL: str = "http://ollama:11434"
    DEFAULT_MODEL: str = "mistral"
    DEFAULT_TEMPERATURE: float = 0.3
    DEFAULT_MAX_TOKENS: int = 4096
    REQUEST_TIMEOUT: float = 120.0
    MAX_RETRIES: int = 3
    RETRY_BASE_DELAY: float = 1.0

    PROMPT_TEMPLATES_DIR: str = "/app/shared/prompt_templates"

    LOG_LEVEL: str = "INFO"

    model_config = {"env_prefix": "LLM_", "env_file": ".env", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
