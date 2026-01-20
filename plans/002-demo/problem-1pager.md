# Problem 1-Pager: Demo Scenario MVP (Step-by-step)

## Background
We need a runnable demo that follows the multi-agent scenario in `docs/demo-scenario.md`, but the real agents are not built yet. The fastest path is a minimal, step-by-step orchestrator that assumes agent interfaces exist and focuses on the user-visible flow.

## Problem
We cannot show the Clarify → Plan → Search → Extract → Verify → Write → (Optional) Visualize flow end-to-end. This blocks validation of the concept, UX, and success criteria during the hackathon.

## Goal
Deliver a minimal CLI demo that:
- Wires the agent interfaces in the exact demo order
- Runs one step at a time (no loops unless explicitly added later)
- Collects user inputs for clarifications and plan approval
- Prints structured JSON outputs for observability at each step

## Success Criteria (Measurement)
- **End-to-end completion**: For a small benchmark set (e.g., 3 queries), the demo completes all steps and exits with code 0.
- **Clarification quality**: For at least 1 ambiguous query, the Clarifier returns ≥1 clarifying question and the user’s answers are captured in the context passed to the Planner.
- **Plan approval**: The plan is approved within ≤1 revision for each benchmark query.
- **Evidence sufficiency**: The Verifier returns `is_enough = true` with ≥2 supported claims, each having `source_id` and evidence.
- **Report completeness**: The Writer output includes an executive summary, ≥3 key findings, and citations matching the sources used.
- **Observability**: The CLI prints JSON for every step; manual timing shows the run completes in <3 minutes per query in demo conditions.

## Non-goals
- Full knowledge graph integration
- DSPy optimization pipeline
- Search/Extract/Verify looping logic
- Production UI, persistence, or automated evals

## Constraints
- Assume all agents are implemented elsewhere; the demo only depends on their interfaces
- Keep implementation minimal and easy to run locally
- Follow the scenario flow described in `docs/demo-scenario.md`
