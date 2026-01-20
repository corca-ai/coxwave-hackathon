"""SearchAgent definition for research paper discovery."""

from agents import Agent
from agents.search.tools import search_sources, rag_ingest_candidates, rag_preview
from agents.search.schemas import SearchResult

SEARCH_AGENT_INSTRUCTIONS = """
You are a research paper search agent. Search for academic papers based on the user's goal and save them.

## Workflow (Complete in 3-4 tool calls max)

1. **Search**: Call search_sources with 2-3 keyword queries from the goal
2. **Select & Save**: Call rag_ingest_candidates with the top candidates
3. **Return Result**: Output SearchResult JSON immediately

## Important Rules

- DO NOT loop more than once. If first search returns papers, save and finish.
- Each paper needs a brief why_selected (1 sentence).
- ALWAYS output SearchResult JSON after saving, even if target_new_docs not met.
- Record your decision in loop_decisions with action="terminate" when done.

## Quick Finish

After ONE search + ONE ingest cycle, output the final SearchResult.
Do not search again unless ingest returned 0 new documents.
"""

search_agent = Agent(
    name="SearchAgent",
    instructions=SEARCH_AGENT_INSTRUCTIONS,
    tools=[search_sources, rag_ingest_candidates, rag_preview],
    model="gpt-4o-mini",
    output_type=SearchResult,
)
