from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime


# --- Input Schemas ---

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


class VerifierConstraints(BaseModel):
    evidence_min: int = 10
    unsupported_ratio_max: float = 0.25
    min_concept_coverage: float = 0.7
    max_loops: int = 3
    loops_done: int = 0
    evidence_check_limit: int = 20


class VerifierRequest(BaseModel):
    goal: str
    namespace: str = "default"
    extractor_result: ExtractorResult
    constraints: VerifierConstraints = Field(default_factory=VerifierConstraints)


# --- Output Schemas ---

class QualityGate(BaseModel):
    passed: bool
    reasons: list[str] = []


class QualityMetrics(BaseModel):
    evidence_coverage: float = 0.0
    unsupported_ratio: float = 0.0
    concept_coverage: float = 0.0
    conflicts_count: int = 0
    isolated_nodes_ratio: float = 0.0
    total_claims: int = 0
    verified_claims: int = 0
    weak_claims: int = 0
    unsupported_claims: int = 0


class ClaimJudgement(BaseModel):
    claim_id: str
    status: Literal["supported", "weak", "unsupported", "conflicting"]
    evidence_valid: bool | None = None
    reason: str


class NextAction(BaseModel):
    type: Literal[
        "search_expand",
        "search_more_papers",
        "reextract",
        "human_review",
        "stop"
    ]
    priority: int = 1
    why: str
    suggested_queries: list[str] = []
    target_concepts: list[str] = []


class ToolCallLog(BaseModel):
    tool: str
    latency_ms: int = 0
    success: bool = True
    error: str | None = None


class ObservabilitySummary(BaseModel):
    run_id: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    decision_trace: list[str] = []
    tool_calls: list[ToolCallLog] = []
    duration_ms: int = 0


class VerifierResult(BaseModel):
    quality_gate: QualityGate
    metrics: QualityMetrics
    claim_judgements: list[ClaimJudgement] = []
    next_actions: list[NextAction] = []
    observability_summary: ObservabilitySummary = Field(
        default_factory=ObservabilitySummary
    )
