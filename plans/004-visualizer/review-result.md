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
- `src/agent/search/clients/arxiv_client.py`
- `README.md`
- `tests/test_tools_search.py`
- `tests/test_tools_rag.py`

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
- Search tool에서 네트워크/외부 API 오류가 발생해도 `SearchResult.errors`에 반영되지 않음(현재 tool 반환 타입이 `list[Candidate]`라 구조적으로 기록 불가).
- Search Agent의 loop 제어는 LLM 지침에만 의존하며, `constraints.loop_budget`를 코드로 강제하지 않음.
- `main.py`의 `--show-inputs`는 효과가 없지만, 현재 정책(입력 payload 항상 출력)에는 부합함.

## Tests Run
- Not run (review-only changes).
