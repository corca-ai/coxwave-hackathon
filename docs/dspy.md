# DSPy in This Repo

This document explains how we use DSPy here, how to run it, and how to extend it.

## What DSPy is used for

We use DSPy to **optimize agent prompts/modules with measurable metrics**, not to replace the full agent stack. The current targets are:

- **Clarifier**: improve clarification decisions and question quality.
- **Visualizer**: improve JSON component specs from report JSON.

DSPy runs are evaluated via the same local eval harness (JSONL datasets + metrics) used by the rest of the repo.

## Install (dev-only)

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

`requirements-dev.txt` includes `dspy` so the base install stays lightweight.

## Environment variables

Required:
- `OPENAI_API_KEY`

Optional DSPy settings:
- `DSPY_MODEL` (defaults to `OPENAI_MODEL` or `gpt-4o-mini`)
- `DSPY_TEMPERATURE` (defaults to `OPENAI_TEMPERATURE` or `0.2`)
- `DSPY_MAX_TOKENS` (defaults to `1024`)

Optimization loop bounds:
- `DSPY_TRAIN_SAMPLES` (default: 4)
- `DSPY_EVAL_SAMPLES` (default: 6)
- `DSPY_OPT_MAX_ROUNDS` (default: 3)
- `DSPY_OPT_MAX_LABELED_DEMOS` (default: 4)
- `DSPY_OPT_MAX_BOOTSTRAPPED_DEMOS` (default: 4)

## Run DSPy agents (standalone)

Clarifier:
```bash
python3 -m dspy_integration.clarifier_cli --query "AI alignment"
```

Visualizer (input must be report JSON):
```bash
python3 -m dspy_integration.visualizer_cli --report-json '{"title":"Demo","executive_summary":"...","key_findings":["A"],"limitations":["L"],"citations":["https://example.com"]}'
```

## Run evals with DSPy engine

Clarifier:
```bash
python3 evals_cli.py --agent clarifier --engine dspy --dataset evals/datasets/clarifier.jsonl
```

Visualizer:
```bash
python3 evals_cli.py --agent visualizer --engine dspy --dataset evals/datasets/visualizer.jsonl
```

## Run DSPy optimization (Phase 2 loop)

This compiles an optimized DSPy module using the dataset and reports baseline vs optimized scores.

Clarifier:
```bash
python3 -m dspy_integration.optimize_cli --agent clarifier --dataset evals/datasets/clarifier.jsonl
```

Visualizer:
```bash
python3 -m dspy_integration.optimize_cli --agent visualizer --dataset evals/datasets/visualizer.jsonl
```

Artifacts are written to `evals/_artifacts/` by default (override with `EVAL_ARTIFACT_DIR`).

## Extending DSPy to a new agent

1. Add a DSPy module in `dspy_integration/<agent>.py` with a `run()` that returns the dataclass output.
2. Add a JSONL dataset in `evals/datasets/<agent>.jsonl`.
3. Add an eval spec in `evals/<agent>_eval.py` and register it in `evals/registry.py`.
4. Update `dspy_integration/agents.py` and `dspy_integration/optimize_cli.py` to route the new agent.
5. Add a unit test in `tests/` to validate the eval harness for the new agent.
