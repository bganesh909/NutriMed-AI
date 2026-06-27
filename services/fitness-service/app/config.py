from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    SERVICE_NAME: str = "fitness-service"
    SERVICE_VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8005

    LLM_SERVICE_URL: str = "http://llm-service:8003"
    LLM_REQUEST_TIMEOUT: float = 60.0

    LOG_LEVEL: str = "INFO"

    model_config = {"env_prefix": "FITNESS_", "env_file": ".env", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
