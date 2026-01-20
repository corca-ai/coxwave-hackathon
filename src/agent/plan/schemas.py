"""Pydantic schemas for Plan Agent request/response models."""

from pydantic import BaseModel, Field


class PlannerConstraints(BaseModel):
    """Constraints for research planning."""

    max_steps: int = 5
    max_search_loops: int = 3
    require_success_criteria: bool = True
    min_data_needs: int = 1


class PlannerRequest(BaseModel):
    """Request model for initiating research planning."""

    goal: str
    namespace: str = "default"
    constraints: PlannerConstraints = Field(default_factory=PlannerConstraints)
    context: str | None = None  # Additional context from clarifier


class ResearchStep(BaseModel):
    """A single step in the research plan."""

    step_number: int
    description: str
    agent: str  # Which agent handles this: search, extract, verify, write
    inputs: list[str] = []
    outputs: list[str] = []


class PlannerResult(BaseModel):
    """Complete result from planning operation.

    Matches main.py PlanOutput interface for compatibility.
    """

    plan_summary: str
    steps: list[str]
    success_criteria: list[str]
    data_needs: list[str]

    # Extended fields for agent coordination
    search_keywords: list[str] = []
    estimated_loops: int = 1
    focus_areas: list[str] = []

    # Detailed step breakdown (optional)
    detailed_steps: list[ResearchStep] = []
