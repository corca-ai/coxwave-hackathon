"""Local agents package re-exports from openai-agents SDK."""

# Re-export from openai-agents SDK
# Use absolute import from the installed package by manipulating module cache
import sys

# Store our partially initialized module
_our_module = sys.modules.get("agents")

# Temporarily remove ourselves from the module cache
if "agents" in sys.modules:
    del sys.modules["agents"]

# Also temporarily filter out src paths
_src_paths = [p for p in sys.path if p.endswith("/src") or "search-agent" in p]
for p in _src_paths:
    if p in sys.path:
        sys.path.remove(p)

try:
    # Now import from the installed openai-agents package
    import agents as _openai_agents

    # Re-export commonly used items
    _function_tool = _openai_agents.function_tool
    _Agent = _openai_agents.Agent
    _Runner = _openai_agents.Runner
    _FunctionTool = _openai_agents.FunctionTool
finally:
    # Restore paths
    for p in _src_paths:
        sys.path.insert(0, p)

    # Restore our module in the cache
    if _our_module is not None:
        sys.modules["agents"] = _our_module

# Expose the imported items
function_tool = _function_tool
Agent = _Agent
Runner = _Runner
FunctionTool = _FunctionTool

__all__ = ["function_tool", "Agent", "Runner", "FunctionTool"]
