# DSPy in This Repo

This document explains how we use DSPy here, how to run it, and how to extend it.

## What DSPy is used for

DSPy is the **primary runtime for all agents** in this repo (Clarifier → Visualizer).
The OpenAI Agent SDK path remains available, but DSPy can be enabled per-agent or
for the entire pipeline via environment flags.

DSPy runs are evaluated via the same local eval harness (JSONL datasets + metrics)
used by the rest of the repo.

## Install (DSPy optional)

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

`requirements-dev.txt` includes `dspy` so the base install stays lightweight.

## Environment variables

Required:
- `OPENAI_API_KEY`

DSPy enablement:
- `USE_DSPY_ALL` (set to `1/true/yes` to run the full pipeline on DSPy)
- `USE_DSPY_CLARIFIER`
- `USE_DSPY_PLANNER`
- `USE_DSPY_SEARCHER`
- `USE_DSPY_EXTRACTOR`
- `USE_DSPY_VERIFIER`
- `USE_DSPY_WRITER`
- `USE_DSPY_VISUALIZER`

DSPy settings (global defaults):
- `DSPY_MODEL` (defaults to `OPENAI_MODEL` or `gpt-4o-mini`)
- `DSPY_TEMPERATURE` (defaults to `OPENAI_TEMPERATURE` or `0.2`)
- `DSPY_MAX_TOKENS` (defaults to `1024`)

Per-agent overrides (optional):
- `DSPY_<AGENT>_MODEL`
- `DSPY_<AGENT>_TEMPERATURE`
- `DSPY_<AGENT>_MAX_TOKENS`

Optimization loop bounds:
- `DSPY_TRAIN_SAMPLES` (default: 4)
- `DSPY_EVAL_SAMPLES` (default: 6)
- `DSPY_OPT_MAX_ROUNDS` (default: 2)
- `DSPY_OPT_MAX_LABELED_DEMOS` (default: 4)
- `DSPY_OPT_MAX_BOOTSTRAPPED_DEMOS` (default: 4)
- `DSPY_SHUFFLE_SEED` (default: 42)

## Run DSPy agents (standalone)

Clarifier:
```bash
python3 -m dspy_integration.clarifier_cli --query "AI alignment"
```

Planner (input is clarifier context JSON):
```bash
python3 -m dspy_integration.planner_cli --input path/to/clarifier_context.json
```

Searcher:
```bash
python3 -m dspy_integration.searcher_cli --input path/to/search_context.json
```

Extractor:
```bash
python3 -m dspy_integration.extractor_cli --input path/to/search_output.json
```

Verifier:
```bash
python3 -m dspy_integration.verifier_cli --input path/to/extract_output.json
```

Writer:
```bash
python3 -m dspy_integration.writer_cli --input path/to/writer_input.json
```

Visualizer (input must be report JSON):
```bash
python3 -m dspy_integration.visualizer_cli --report-json '{"title":"Demo","executive_summary":"...","key_findings":["A"],"limitations":["L"],"citations":["https://example.com"]}'
```

## Run full pipeline with DSPy

```bash
export USE_DSPY_ALL=1
python3 main.py --query "Investigate RAG and hallucination in legal QA"
```

## Run evals with DSPy engine

```bash
python3 evals_cli.py --agent clarifier --engine dspy --dataset evals/datasets/clarifier.jsonl
python3 evals_cli.py --agent planner --engine dspy --dataset evals/datasets/planner.jsonl
python3 evals_cli.py --agent searcher --engine dspy --dataset evals/datasets/searcher.jsonl
python3 evals_cli.py --agent extractor --engine dspy --dataset evals/datasets/extractor.jsonl
python3 evals_cli.py --agent verifier --engine dspy --dataset evals/datasets/verifier.jsonl
python3 evals_cli.py --agent writer --engine dspy --dataset evals/datasets/writer.jsonl
python3 evals_cli.py --agent visualizer --engine dspy --dataset evals/datasets/visualizer.jsonl
```

## Run DSPy optimization (Phase 2 loop)

This compiles an optimized DSPy module using the dataset and reports baseline vs optimized scores.

```bash
python3 -m dspy_integration.optimize_cli --agent clarifier --dataset evals/datasets/clarifier.jsonl
python3 -m dspy_integration.optimize_cli --agent visualizer --dataset evals/datasets/visualizer.jsonl
```

Artifacts are written to `evals/_artifacts/` by default (override with `EVAL_ARTIFACT_DIR`).

## DSPy report template

Use `docs/dspy-report-template.md` to record baseline/optimized deltas and action items.

## Visualizer dataset variant

`evals/datasets/visualizer_components.jsonl` focuses on component ordering and prop normalization.

## Extending DSPy to a new agent

1. Add a DSPy module in `dspy_integration/<agent>.py` with a `run()` that returns the dataclass output.
2. Add a JSONL dataset in `evals/datasets/<agent>.jsonl`.
3. Add an eval spec in `evals/<agent>_eval.py` and register it in `evals/registry.py`.
4. Update `dspy_integration/agents.py` to route the new agent.
5. Add a unit test in `tests/` to validate the eval harness for the new agent.
