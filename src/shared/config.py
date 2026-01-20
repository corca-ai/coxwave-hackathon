from pydantic_settings import BaseSettings, SettingsConfigDict


# =============================================================================
# Model Configuration
# =============================================================================
# Light model: For simple/fast tasks (guardrails, simple classification)
# Heavy model: For detailed/complex tasks (reasoning, analysis, generation)

MODEL_LIGHT = "gpt-5-mini"  # Fast, efficient for simple tasks
MODEL_HEAVY = "gpt-5.2"     # Powerful for complex reasoning


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openai_api_key: str
    openai_model: str = MODEL_HEAVY  # Default to heavy for main agents
    openai_model_light: str = MODEL_LIGHT  # For guardrails and simple tasks
    artifacts_dir: str = "artifacts"

    # RAG settings
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "papers"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536


def get_settings() -> Settings:
    return Settings()
