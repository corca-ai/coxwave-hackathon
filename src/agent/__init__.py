"""Local agent package - re-exports from openai-agents SDK."""

# Direct import from openai-agents SDK (no conflict now that we're named 'agent')
from agents import function_tool, Agent, Runner, FunctionTool

__all__ = ["function_tool", "Agent", "Runner", "FunctionTool"]
