from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    SERVICE_NAME: str = "rag-service"
    SERVICE_VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8004

    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    VECTOR_INDEX_PATH: str = "/app/data/vector_index"
    KNOWLEDGE_BASE_DIR: str = "/app/shared/knowledge_base"
    DEFAULT_TOP_K: int = 5
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50

    LOG_LEVEL: str = "INFO"

    model_config = {"env_prefix": "RAG_", "env_file": ".env", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
