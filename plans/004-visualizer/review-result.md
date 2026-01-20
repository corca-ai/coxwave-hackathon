# 004 Visualizer Review

## Scope
- `agents_impl.py`
- `main.py`
- `visualizer_cli.py`
- `tests/test_visualizer.py`
- `tests/test_demo_e2e.py`
- `docs/schemas/visual-output.schema.json`
- `README.md`

## Findings (fixed)
1. **High**: Agents SDK strict schema rejected `VisualOutput` because `props` allows arbitrary keys, causing runtime failure.
   - Fix: `AgentOutputSchema(VisualOutput, strict_json_schema=False)` in `agents_impl.py`.
2. **Medium**: Mock Visualizer output lacked required component types used by schema/tests.
   - Fix: expanded `MockVisualizer` components in `main.py`.
3. **Low**: No deterministic fixture for Visualizer manual run/tests.
   - Fix: auto-generated fixture in `tests/test_visualizer.py` and documented in `README.md`.
4. **Low**: `visualizer_cli.py` crashed on missing input file instead of returning a clear error.
   - Fix: added file-not-found handling with user-friendly messages.

## Remaining Risks / Notes
- JSON schema is permissive by design; no strict schema validation is enforced at runtime.
- (Resolved) `visualizer_cli.py` input file-not-found errors are now handled.

## Tests Run
- `.venv/bin/python -m unittest tests/test_clarifier.py tests/test_visualizer.py tests/test_demo_e2e.py`

---

# 2026-01-20 Repo-Wide Review

## Scope
- `clarifier_cli.py`
- `src/runner.py`
- `src/agent/verify/runner.py`
- `README.md`

## Findings (fixed)
1. **High**: Search/Verifier standalone CLI did not load `.env` or enforce `OPENAI_API_KEY`, risking silent failures.
   - Fix: Added `.env` loading + key checks in `src/runner.py` and `src/agent/verify/runner.py`.
2. **High**: Observability default violated in Search/Verifier/Clarifier CLI (input/output payloads not always printed).
   - Fix: Added input/output payload printing in `src/runner.py`, `src/agent/verify/runner.py`, and input echo in `clarifier_cli.py`.
3. **Medium**: README agent status out of sync with actual implementation (Search/Verifier standalone CLIs exist).
   - Fix: Updated agent status table and OpenAI API usage checkbox in `README.md`.
4. **Medium**: Verifier CLI crashed on missing/invalid extractor JSON; no graceful error handling.
   - Fix: Added explicit file/JSON error handling in `src/agent/verify/runner.py`.
5. **Medium**: `time_range_years` constraint ignored in arXiv search.
   - Fix: Filtered results by published year in `src/agent/search/clients/arxiv_client.py`.
6. **Low**: Unit tests didn't print input/output payloads by default.
   - Fix: Added payload logs in `tests/test_tools_search.py` and `tests/test_tools_rag.py`.

## Remaining Risks / Notes
- Some unit tests do not log input/output payloads by default (observability guideline); consider standardizing via shared helpers.
- Verifier/Search CLI lack structured error handling for missing/invalid input files beyond Click exceptions.

## Tests Run
- Not run (review-only changes).
