"""OpenAI embedding utilities."""

from openai import OpenAI

from shared.config import get_settings

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """Get or create OpenAI client."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def get_embedding(
    text: str,
    model: str | None = None,
) -> list[float]:
    """Get embedding vector for text.

    Args:
        text: Text to embed
        model: Embedding model (default: from settings)

    Returns:
        Embedding vector
    """
    settings = get_settings()
    client = _get_client()
    response = client.embeddings.create(
        input=text,
        model=model or settings.embedding_model,
    )
    return response.data[0].embedding


def get_embeddings(
    texts: list[str],
    model: str | None = None,
) -> list[list[float]]:
    """Get embeddings for multiple texts (batch).

    Args:
        texts: Texts to embed
        model: Embedding model (default: from settings)

    Returns:
        List of embedding vectors
    """
    settings = get_settings()
    client = _get_client()
    response = client.embeddings.create(
        input=texts,
        model=model or settings.embedding_model,
    )
    return [d.embedding for d in response.data]
