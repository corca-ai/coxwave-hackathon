# Writer Agent (OpenAI Agents SDK) 요구사항

## 배경
- 데모 시나리오에서 Writer는 최종 리포트를 합성하는 핵심 단계지만, 현재는 mock 출력만 존재한다.
- Visualizer는 Writer의 `ReportOutput`을 입력으로 사용하므로, 실제 Writer 구현이 있어야 end-to-end 흐름이 완성된다.
- 기존 작업 방식은 “가장 미니멀하게 한 스텝씩” 진행하며, 입력/출력 payload를 항상 관측 가능하게 유지한다.

## 목표
- OpenAI Agents SDK 기반 Writer 에이전트를 추가하고 데모(`main.py`)에 연결한다.
- Writer는 검증된 claim과 소스 정보를 바탕으로 **구조화된 리포트(JSON)** 를 생성한다.
- Writer를 전체 시나리오와 독립적으로 실행/검증할 수 있어야 한다.

## 범위 (Requirements)
1. **Writer 에이전트 구현**
   - OpenAI Agents SDK를 사용해 LLM 기반 Writer를 구현한다.
   - 입력은 `main.py`의 Writer input(JSON 문자열)이며, 출력은 `ReportOutput` 구조를 따른다.
   - 필수 필드: `title`, `executive_summary`, `key_findings`, `limitations`, `citations`, `suggested_visuals`.
   - 출력은 JSON-serializable이며 ASCII-safe JSON을 기본으로 유지한다.

## 합의 사항 (세션 기준)
- citations는 가능한 경우 URL을 우선 사용하고, URL이 없을 때는 `source_id`를 허용한다.
- `key_findings`는 가능하면 ≥3을 목표로 하되, 근거가 부족한 경우 `limitations`에 명시한다.
- Writer는 기본적으로 단일 패스(리비전 루프 없음)로 구현한다.

2. **리포트 합성 규칙**
   - `supported_claims`와 `sources`를 근거로 핵심 결과를 요약한다.
   - `citations`에는 실제 `sources`의 `url` 또는 `source_id`를 기반으로 한 항목만 포함한다. (환각 인용 금지)
   - 근거가 부족하거나 `supported_claims`가 비어있을 경우 `limitations`에 명시적으로 기록한다.
   - `suggested_visuals`는 Visualizer가 참고할 수 있는 간단한 시각화 아이디어(예: “Key findings bullet list”)를 제공한다.

3. **데모 연결**
   - `agents_impl.py`의 `build_agents()`에서 Writer를 반환한다.
   - `main.py`의 Write 단계 입력/출력 payload가 기본 출력되도록 유지한다.
   - Writer 입력(payload)이 `clarifier`, `plan`, `sources`, `supported_claims`를 포함함을 명확히 보여준다.

4. **단독 실행 (독립 테스트)**
   - Writer만 실행 가능한 별도 CLI 엔트리를 제공한다. (예: `writer_cli.py`)
   - 입력 1개(JSON) → 출력 1개(JSON) 형태의 단순한 실행 경로면 충분하다.
   - CLI는 입력/출력 payload를 항상 출력한다.

5. **자동화된 테스트**
   - Writer 단위 테스트를 추가한다. (스키마 준수, 필수 필드 생성 여부, citations 정합성 최소 검증)
   - 데모 E2E 테스트는 Writer 단계까지 포함되어야 한다.
   - 테스트 로그는 입력/출력 payload를 기본으로 남긴다. (`tests/_artifacts/` 활용)

6. **오류/경계 처리**
   - API 키가 없을 경우 명확한 오류 메시지를 출력한다.
   - Writer 입력이 JSON 파싱 실패 또는 스키마 불일치 시 원인을 노출한다.
   - LLM 출력이 `ReportOutput` 파싱 실패 시 안전하게 실패 원인을 노출한다.

7. **루프/반복 제약**
   - Writer 내부에 개선/재작성 루프가 있다면 상한을 둔다.
   - 기본값은 env로 설정하고 CLI 옵션으로 오버라이드 가능해야 한다.

8. **환경 로드**
   - 실행/테스트에서 `.env`를 기본 로드해 API 키가 자동 반영되도록 한다.

## 비목표 (Non-goals)
- 다른 에이전트(Search/Extractor/Verifier/Visualizer) 구현/개선
- 리포트 렌더링(UI/GUI) 구현
- 고급 스타일링(표/차트 렌더러) 설계
- DSPy 최적화 파이프라인 구축

## 제약 (Constraints)
- OpenAI Agents SDK (Python) 사용
- 기존 데모 흐름(Clarify → Plan → Search → Extract → Verify → Write → Visualize) 유지
- `ReportOutput` 구조와의 호환성 유지
- 관측 가능성 기본값(입력/출력 payload 출력) 유지

## 성공 기준
- `python3 main.py --query "..."` 실행 시 Write 단계에서 실제 LLM 호출이 수행됨
- Writer 출력이 `ReportOutput` 구조로 파싱되어 JSON으로 정상 출력됨
- `executive_summary`, `key_findings`, `limitations`, `citations`가 비어있지 않거나 근거 부족이 명시됨
- citations가 `sources`에 존재하는 URL 또는 source_id 기반으로 구성됨
- Writer 단독 실행에서도 동일한 구조화 출력이 생성됨
- 단위 테스트 + 데모 E2E 테스트가 통과함

## 참고
- `docs/demo-scenario.md`
- `docs/implementation.md`
- `main.py` (`ReportOutput`, Writer input payload 구성)
- `plans/002-demo/problem-1pager.md` (Report completeness 기준)
- `openai-agents-python-docs/agents.md`
