# 004 Visualizer Review

## Scope
- `main.py`
- `agents_impl.py`
- `src/runner.py`
- `src/agent/verify/runner.py`
- `src/agent/search/tools/search.py`
- `src/agent/search/tools/rag.py`
- `src/agent/search/clients/arxiv_client.py`
- `src/agent/search/clients/local_store.py`
- `src/agent/search/ranking.py`
- `README.md`
- `tests/*`

## Findings (fixed)
1. **High**: Search/Verify CLIs did not load `.env` or check `OPENAI_API_KEY`, and did not print input/output payloads → violates observability + reliability expectations.
   - Fix: load `.env`, validate key, and always emit JSON payloads in `src/runner.py` and `src/agent/verify/runner.py`.
2. **High**: `time_range_years` constraint in `ArxivClient` was ignored, allowing out-of-range papers.
   - Fix: filter results by cutoff year in `src/agent/search/clients/arxiv_client.py` with tests.
3. **Medium**: Duplicate arXiv IDs in a single ingest batch could be saved multiple times; duplicate counts were under-reported.
   - Fix: dedupe in `src/agent/search/tools/rag.py` and `src/agent/search/clients/local_store.py` with tests.
4. **Medium**: Recency scoring could exceed 1.0 for future-dated papers.
   - Fix: clamp recency score in `src/agent/search/ranking.py` with tests.
5. **Medium**: Demo pipeline lacked step-level exception handling after clarifier, risking hard crashes.
   - Fix: wrap planner/search/extract/verify/write/visualize calls in `main.py` and return non-zero on failures.
6. **Low**: README status did not reflect actual agent availability (Search/Verifier exist but not wired) and OpenAI usage.
   - Fix: update `README.md` status and notes.

## Remaining Risks / Notes
- Search tool errors are swallowed and surface only as empty results; `SearchResult.errors` is not populated by tools.
- E2E demo still uses mock Planner/Searcher/Extractor/Verifier/Writer, so real multi-agent orchestration is not exercised.

## Tests Run
- `pytest tests/ -v`
