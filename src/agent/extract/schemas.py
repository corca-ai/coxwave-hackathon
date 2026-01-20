"""Pydantic schemas for Extractor Agent."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from agent.search.schemas import SearchResult


class Evidence(BaseModel):
    chunk_id: str
    quote: str
    page: int | None = None


class Claim(BaseModel):
    claim_id: str
    doc_id: str  # arxiv_id
    text: str
    evidence: Evidence | None = None
    concept_tags: list[str] = []
    confidence: float = 0.0


class Concept(BaseModel):
    concept_id: str
    name: str
    description: str = ""


class PaperCard(BaseModel):
    arxiv_id: str
    title: str
    year: int
    authors: list[str]
    abstract: str


class GraphNode(BaseModel):
    id: str
    type: Literal["paper", "claim", "concept", "author"]
    label: str


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str


class GraphData(BaseModel):
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []


class ExtractorResult(BaseModel):
    paper_cards: list[PaperCard] = []
    claims: list[Claim] = []
    concepts: list[Concept] = []
    graph: GraphData | None = None


class ExtractorConstraints(BaseModel):
    max_claims: int = 8
    min_evidence_chars: int = 20
    allow_weak_claims: bool = True
    include_concepts: bool = False


class ExtractorRequest(BaseModel):
    goal: str
    namespace: str = "default"
    search_result: SearchResult
    constraints: ExtractorConstraints = Field(default_factory=ExtractorConstraints)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
