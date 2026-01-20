# Visualizer Agent (OpenAI Agents SDK) 요구사항

## 배경
- 데모 시나리오의 마지막 단계가 Visualizer이며, 현재는 mock 출력만 존재한다.
- 현 시점 UI는 CLI지만, 향후 GUI 확장을 고려해야 한다.
- Visualizer의 핵심은 **렌더링이 아니라 JSON 스펙 출력**이며, 실제 시각화는 프론트엔드 책임이다.
- 잠재적 렌더러로 `json-render`를 염두에 두되, 구현은 특정 프론트엔드에 종속되지 않아야 한다.

## 목표
- OpenAI Agents SDK 기반 Visualizer 에이전트를 추가하고 데모(`main.py`)에 연결한다.
- Writer 출력(ReportOutput)을 입력으로 받아 **GUI에서 바로 렌더 가능한 JSON 컴포넌트 스펙**을 생성한다.
- Visualizer를 전체 시나리오와 독립적으로 실행/검증할 수 있어야 한다.

## 범위 (Requirements)
1. **Visualizer 에이전트 구현**
   - OpenAI Agents SDK를 사용해 LLM 기반 Visualizer를 구현한다.
   - 입력은 `main.py`의 `ReportOutput` JSON이며, 출력은 `VisualOutput` 구조를 따른다.
   - `components[]`는 `type`과 `props`로 구성된 JSON-serializable 객체만 포함한다.
   - 출력은 ASCII-safe JSON을 기본으로 유지한다.

2. **컴포넌트 스펙 최소 집합**
   - 최소한 아래 정보가 시각화 스펙으로 변환되어야 한다.
     - `title` → heading/text
     - `executive_summary` → paragraph
     - `key_findings` → bullets
     - `limitations` → callout/notes
     - `citations` → list
   - 컴포넌트 `type`은 고정된 소규모 셋으로 시작하되, 확장 가능하게 설계한다.
   - 필요 시 `schema_version` 등 메타 정보는 `props` 안에 포함한다.

3. **데모 연결**
   - `agents_impl.py`의 `build_agents()`에서 Visualizer를 반환한다.
   - `main.py`의 Visualize 단계 입력/출력 payload가 기본 출력되도록 유지한다.
   - Writer 출력 → Visualizer 입력 연결이 명확히 보이도록 한다.

4. **단독 실행 (독립 테스트)**
   - Visualizer만 실행 가능한 별도 CLI 엔트리를 제공한다. (예: `visualizer_cli.py`)
   - 입력 1개(JSON) → 출력 1개(JSON) 형태의 단순한 실행 경로면 충분하다.

5. **자동화된 테스트**
   - Visualizer 단위 테스트를 추가한다. (스키마 준수, 필수 컴포넌트 생성 여부)
   - 데모 E2E 테스트에서 Visualize 단계까지 포함되어야 한다.
   - 테스트 로그는 입력/출력 payload를 기본으로 남긴다.

6. **오류/경계 처리**
   - API 키가 없을 경우 명확한 오류 메시지를 출력한다.
   - Visualizer 출력이 파싱 실패 또는 스키마 불일치 시 원인을 노출한다.

7. **루프/반복 제약**
   - Visualizer 내부에 반복 개선 루프가 있다면 상한을 둔다.
   - 기본값은 env로 설정하고 CLI 옵션으로 오버라이드 가능해야 한다.

8. **환경 로드**
   - 실행/테스트에서 `.env`를 기본 로드해 API 키가 자동 반영되도록 한다.

## 비목표 (Non-goals)
- CLI에서의 고급 시각화/렌더링 구현
- 프론트엔드 UI/UX 개발
- json-render에 종속된 전용 스펙 설계
- 다른 에이전트(Search/Extractor/Verifier/Writer) 개선

## 제약 (Constraints)
- OpenAI Agents SDK (Python) 사용
- 기존 데모 흐름(Clarify → Plan → Search → Extract → Verify → Write → Visualize) 유지
- `VisualOutput`/`VisualComponent` 구조와의 호환성 유지

## 성공 기준
- `python3 main.py --query "..."` 실행 시 Visualize 단계에서 실제 LLM 호출이 수행됨
- Visualizer 출력이 `VisualOutput` 구조로 파싱되어 JSON으로 정상 출력됨
- Writer 출력의 핵심 필드가 컴포넌트 스펙으로 매핑되어 있음
- Visualizer 단독 실행에서도 동일한 구조화 출력이 생성됨
- 단위 테스트 + 데모 E2E 테스트가 통과함

## 참고
- `docs/demo-scenario.md`
- `docs/implementation.md`
- `main.py` (`VisualOutput`, `VisualComponent`)
- `plans/004-visualizer/_req_req.md`
