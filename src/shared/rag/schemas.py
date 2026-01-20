"""RAG schemas for vector storage and retrieval."""

from pydantic import BaseModel


class VectorDocument(BaseModel):
    """Document stored in vector database."""

    arxiv_id: str
    title: str
    abstract: str
    url: str
    authors: list[str] = []
    year: int = 0


class SearchResult(BaseModel):
    """Result from vector similarity search."""

    arxiv_id: str
    title: str
    abstract: str
    url: str
    score: float
