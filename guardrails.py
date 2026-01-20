"""Guardrails for the research navigator agents.

Implements input and output guardrails following OpenAI Agent SDK patterns:
- Input guardrails: Check user input before agent execution
- Output guardrails: Check agent output before returning to user
"""

from pydantic import BaseModel
from src.shared.config import MODEL_LIGHT
from agents import (
    Agent,
    GuardrailFunctionOutput,
    RunContextWrapper,
    Runner,
    TResponseInputItem,
    input_guardrail,
    output_guardrail,
)

from main import VisualOutput


# =============================================================================
# Guardrail Output Types
# =============================================================================


class OffTopicCheck(BaseModel):
    """Output type for off-topic detection."""

    is_off_topic: bool
    reasoning: str
    detected_category: str  # "research", "homework", "chat", "coding", "other"


class UnethicalResearchCheck(BaseModel):
    """Output type for unethical research detection."""

    is_unethical: bool
    reasoning: str
    concern_type: str  # "weapons", "drugs", "hacking", "harm", "none"


class PIICheck(BaseModel):
    """Output type for PII/sensitive data detection."""

    contains_pii: bool
    reasoning: str
    pii_types: list[str]  # ["api_key", "password", "ssn", "email", etc.]


class HallucinationCheck(BaseModel):
    """Output type for hallucination detection in output."""

    has_unsupported_claims: bool
    reasoning: str
    flagged_statements: list[str]


class OverconfidenceCheck(BaseModel):
    """Output type for overconfidence detection."""

    is_overconfident: bool
    reasoning: str
    flagged_phrases: list[str]


# =============================================================================
# Guardrail Agents (lightweight models for fast checking)
# =============================================================================

off_topic_agent = Agent(
    name="OffTopicGuardrail",
    model=MODEL_LIGHT,
    output_type=OffTopicCheck,
    instructions="""You are a guardrail that checks if a user query is appropriate for a research assistant.

APPROPRIATE (is_off_topic=false):
- Academic research questions
- Literature review requests
- Scientific topic exploration
- Paper summarization requests
- Research methodology questions

NOT APPROPRIATE (is_off_topic=true):
- Homework or assignment completion requests (detected_category="homework")
- General chat or small talk (detected_category="chat")
- Code writing requests (detected_category="coding")
- Non-research tasks (detected_category="other")

Be lenient - if it could reasonably be research-related, allow it.""",
)

unethical_research_agent = Agent(
    name="UnethicalResearchGuardrail",
    model=MODEL_LIGHT,
    output_type=UnethicalResearchCheck,
    instructions="""You are a guardrail that checks if a research query involves unethical topics.

BLOCK (is_unethical=true) queries about:
- Weapons development or manufacturing (concern_type="weapons")
- Drug synthesis or illegal substances (concern_type="drugs")
- Hacking, malware, or cyberattacks (concern_type="hacking")
- Causing harm to individuals or groups (concern_type="harm")

ALLOW (is_unethical=false):
- Legitimate security research
- Historical analysis of conflicts
- Medical/pharmaceutical research
- Defensive cybersecurity

Set concern_type="none" if the query is ethical.
Be balanced - don't block legitimate academic research.""",
)

pii_agent = Agent(
    name="PIIGuardrail",
    model=MODEL_LIGHT,
    output_type=PIICheck,
    instructions="""You detect if user input contains sensitive personal information.

CHECK FOR:
- API keys or tokens (patterns like sk-*, pk_*, etc.)
- Passwords or secrets
- Social security numbers
- Credit card numbers
- Personal email addresses in sensitive contexts
- Private keys or certificates

DO NOT flag:
- Public email domains in academic contexts
- Example/placeholder data
- General names or affiliations""",
)

hallucination_agent = Agent(
    name="HallucinationGuardrail",
    model=MODEL_LIGHT,
    output_type=HallucinationCheck,
    instructions="""You check if research output contains unsupported claims.

FLAG (has_unsupported_claims=true) if:
- Claims are made without citing sources
- Statistics are presented without references
- Strong conclusions lack supporting evidence
- Statements like "studies show" without specific citations

ALLOW (has_unsupported_claims=false) if:
- Claims reference specific papers or sources
- Statements are clearly marked as interpretations
- Limitations are acknowledged
- Uncertainty is expressed appropriately

Add flagged statements to the list for transparency.""",
)

overconfidence_agent = Agent(
    name="OverconfidenceGuardrail",
    model=MODEL_LIGHT,
    output_type=OverconfidenceCheck,
    instructions="""You detect overconfident language in research output.

FLAG (is_overconfident=true) phrases like:
- "definitely", "certainly", "absolutely"
- "proves conclusively", "without doubt"
- "100%", "always", "never" (in absolute contexts)
- "the only way", "must be"

ALLOW (is_overconfident=false):
- Hedged language: "suggests", "indicates", "may"
- Qualified statements: "based on available evidence"
- Acknowledged uncertainty: "further research needed"

Research should express appropriate uncertainty.""",
)


# =============================================================================
# Input Guardrails
# =============================================================================


@input_guardrail
async def off_topic_guardrail(
    ctx: RunContextWrapper[None],
    agent: Agent,
    input: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    """Block off-topic requests that aren't research-related."""
    input_text = input if isinstance(input, str) else str(input)
    result = await Runner.run(off_topic_agent, input_text, context=ctx.context)

    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=result.final_output.is_off_topic,
    )


@input_guardrail
async def unethical_research_guardrail(
    ctx: RunContextWrapper[None],
    agent: Agent,
    input: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    """Block unethical research requests."""
    input_text = input if isinstance(input, str) else str(input)
    result = await Runner.run(unethical_research_agent, input_text, context=ctx.context)

    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=result.final_output.is_unethical,
    )


@input_guardrail
async def pii_guardrail(
    ctx: RunContextWrapper[None],
    agent: Agent,
    input: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    """Block inputs containing sensitive personal information."""
    input_text = input if isinstance(input, str) else str(input)
    result = await Runner.run(pii_agent, input_text, context=ctx.context)

    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=result.final_output.contains_pii,
    )


# =============================================================================
# Output Guardrails
# =============================================================================


@output_guardrail
async def hallucination_guardrail(
    ctx: RunContextWrapper,
    agent: Agent,
    output: VisualOutput,
) -> GuardrailFunctionOutput:
    """Check for unsupported claims in the output."""
    # Convert output to string for checking
    output_text = output.rationale if hasattr(output, "rationale") else str(output)
    result = await Runner.run(hallucination_agent, output_text, context=ctx.context)

    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=result.final_output.has_unsupported_claims,
    )


@output_guardrail
async def overconfidence_guardrail(
    ctx: RunContextWrapper,
    agent: Agent,
    output: VisualOutput,
) -> GuardrailFunctionOutput:
    """Check for overconfident language in the output."""
    output_text = output.rationale if hasattr(output, "rationale") else str(output)
    result = await Runner.run(overconfidence_agent, output_text, context=ctx.context)

    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=result.final_output.is_overconfident,
    )


# =============================================================================
# Exported guardrail lists for easy import
# =============================================================================

# Input guardrails for the first agent (Clarifier)
INPUT_GUARDRAILS = [
    off_topic_guardrail,
    unethical_research_guardrail,
    pii_guardrail,
]

# Output guardrails for the last agent (Visualizer)
OUTPUT_GUARDRAILS = [
    hallucination_guardrail,
    overconfidence_guardrail,
]
