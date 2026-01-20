# Next Work: DSPy Track

## Immediate follow-ups
- Run DSPy optimization end-to-end for Clarifier and Visualizer using real API keys and capture artifacts in `evals/_artifacts/`.
- Review optimization deltas and update the dataset/metrics if scores do not improve or regress.
- Add a deterministic shuffle/seed before train/eval splitting in `dspy_integration/optimize_cli.py` to reduce ordering bias.

## Quality & evaluation
- Expand datasets for Clarifier and Visualizer to at least 10–20 samples each.
- Add edge-case samples (empty fields, long summaries, missing citations) for Visualizer.
- Add stricter Visualizer metrics (e.g., minimum bullets length, callout title presence, list URL validation).
- Add a small regression test that runs the DSPy optimizer in mock mode (if possible) or a dry-run path.

## DSPy integration improvements
- Add a light wrapper so `python3 dspy_*` style invocations still work (or update CLI help to require `-m`).
- Consider adding per-agent DSPy config (`DSPY_<AGENT>_MODEL`, etc.) if different models are desired.
- Add a DSPy result summary in README or a short report template in `docs/`.

## Visualizer-specific extensions
- Define a Visualizer-only DSPy dataset variant that focuses on component ordering and prop normalization.
- Add a metric that penalizes missing required components or empty props more aggressively.
- Add a small schema validation pass for `VisualOutput` components in the DSPy pipeline.
