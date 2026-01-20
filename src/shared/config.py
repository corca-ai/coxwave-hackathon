from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openai_api_key: str
    openai_model: str = "gpt-5-mini"
    artifacts_dir: str = "artifacts"

    # RAG settings
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "papers"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536


def get_settings() -> Settings:
    return Settings()
