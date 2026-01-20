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
- `visualizer_cli.py` does not catch file-not-found errors for the input path.

## Tests Run
- `.venv/bin/python -m unittest tests/test_clarifier.py tests/test_visualizer.py tests/test_demo_e2e.py`

---

# Project-Wide Review (2026-01-20)

## Scope
- `src/runner.py`
- `src/agent/verify/runner.py`
- `src/agent/search/clients/arxiv_client.py`
- `README.md`

## Findings (fixed)
1. **High**: Search/Verifier CLI가 입력 payload를 출력하지 않아 observability 기본값(입·출력 payload 상시 출력)과 불일치.
   - Fix: `src/runner.py`, `src/agent/verify/runner.py`에서 입력/출력 payload를 항상 출력.
2. **High**: Search/Verifier CLI가 `.env`를 로드하지 않아 API 키가 있어도 누락될 수 있음.
   - Fix: 두 CLI에서 `load_env` 호출 및 `OPENAI_API_KEY` 확인 추가.
3. **Medium**: `time_range_years` 제약이 arXiv 검색에 적용되지 않아 최신 범위 제약 무시됨.
   - Fix: `src/agent/search/clients/arxiv_client.py`에서 연도 필터 적용.
4. **Medium**: Verifier CLI가 입력 파일 누락/JSON 오류 시 예외 처리 없이 종료.
   - Fix: 파일/JSON/OSError 예외 처리 및 명확한 에러 메시지 추가.

## Remaining Risks / Notes
- Search tool에서 네트워크/외부 API 오류가 발생해도 `SearchResult.errors`에 반영되지 않음(현재 tool 반환 타입이 `list[Candidate]`라 구조적으로 기록 불가).
- Search Agent의 loop 제어는 LLM 지침에만 의존하며, `constraints.loop_budget`를 코드로 강제하지 않음.
- `main.py`의 `--show-inputs`는 효과가 없지만, 현재 정책(입력 payload 항상 출력)에는 부합함.

## Tests Run
- Not run (review only).
