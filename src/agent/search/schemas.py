"""Pydantic schemas for Search Agent request/response models."""

from pydantic import BaseModel, Field
from typing import Literal


class IngestPolicy(BaseModel):
    """Policy for document ingestion into the vector store."""

    mode: Literal["abstract_only"] = "abstract_only"
    chunk_size: int = 512
    chunk_overlap: int = 50


class Constraints(BaseModel):
    """Search constraints and limits."""

    target_new_docs: int = 12
    max_candidates: int = 80
    max_selected: int = 20
    time_range_years: int = 7
    loop_budget: int = 2
    categories: list[str] | None = None
    ingest_policy: IngestPolicy = Field(default_factory=IngestPolicy)
    preview_top_k: int = 5


class SearchRequest(BaseModel):
    """Request model for initiating a paper search."""

    goal: str
    namespace: str = "default"
    constraints: Constraints = Field(default_factory=Constraints)


class Candidate(BaseModel):
    """A candidate paper from arXiv search results."""

    arxiv_id: str
    title: str
    year: int
    authors: list[str]
    abstract: str
    url: str
    pdf_url: str | None = None
    categories: list[str] = []
    score: float = 0.0
    why_selected: str = ""


class LoopDecision(BaseModel):
    """Record of a decision made during search iteration."""

    iteration: int
    action: str
    reason: str


class QueryPlan(BaseModel):
    """Plan for executing search queries."""

    queries: list[str]
    time_range: str
    categories: list[str]
    loop_decisions: list[LoopDecision] = []


class IngestSummary(BaseModel):
    """Summary of document ingestion results."""

    new_docs_added: int
    duplicates_skipped: int
    chunks_added: int = 0
    index_size: int = 0


class PreviewSnippet(BaseModel):
    """A preview snippet from indexed document chunks."""

    arxiv_id: str
    chunk_id: str
    score: float
    snippet: str


class SearchError(BaseModel):
    """Error information from search operations."""

    code: str
    message: str
    retryable: bool = False


class SearchResult(BaseModel):
    """Complete result from a search operation."""

    query_plan: QueryPlan
    selected_papers: list[Candidate]
    ingest_summary: IngestSummary
    preview_snippets: list[PreviewSnippet] = []
    errors: list[SearchError] = []
