from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    SERVICE_NAME: str = "pdf-service"
    SERVICE_VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8006

    OUTPUT_DIR: str = "/tmp/nutrimed-reports"

    LOG_LEVEL: str = "INFO"

    model_config = {"env_prefix": "PDF_", "env_file": ".env", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
