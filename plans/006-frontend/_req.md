# Frontend UI (Graph + Observability + Streaming) 요구사항

## 배경
- 현재 데모는 CLI 중심이며, 결과와 에이전트 동작 과정이 텍스트로만 노출된다.
- Visualizer가 출력한 JSON 스펙과 각 에이전트의 중간 결과를 **시각적으로 연결**해 보여줄 UI가 필요하다.
- 기존에 구현했던 UI 스크린샷(`sample-1~4.png`)이 있으며, 이를 참고해 프론트엔드를 정식화하려 한다.

## 문제
- 결과물의 출처/근거/연결 관계를 한눈에 파악하기 어렵다.
- 에이전트가 어떤 순서와 근거로 움직였는지(Observability/Trace)가 텍스트 로그에만 남아 있어 이해가 느리다.
- Streaming 응답이 실제로 어떻게 진행되는지 사용자 경험이 부족하다.

## 목표
- 결과물에 연결된 자료/근거를 **그래프로 시각화**한다.
- 에이전트 동작 과정을 **그래프/타임라인 기반 Trace**로 시각화한다.
- Streaming 응답이 **실시간으로 보이고**, 중간 상태가 자연스럽게 갱신된다.
- CLI에서 출력되던 입력/출력 payload가 UI에서도 기본 노출되어 디버깅이 쉽다.
- 로컬 전용 데모를 우선하되, **Vercel 배포 가능한 구조**를 유지한다. (가산점)

## 범위 (Requirements)
1. **입력/데이터 계약 정의**
   - Visualizer 출력은 `docs/schemas/visual-output.schema.json` 기준으로 렌더링한다.
   - 데모 1회 실행의 결과를 **단일 Run Bundle(JSON)**로 받아 처리한다.
     - 최소 포함: Clarify/Plan/Search/Extract/Verify/Write/Visualize 단계별 input/output payload
   - Run Bundle 스키마는 `docs/schemas/run-bundle.schema.json`로 관리한다.
   - Streaming 로그 스키마는 `docs/schemas/stream-events.schema.json`로 관리한다.
   - Run Bundle은 파일 로드(드래그앤드롭/파일 선택)로도 읽을 수 있어야 한다. (백엔드 없이도 단독 실행 가능)

2. **결과물 그래프 시각화**
   - 그래프 라이브러리는 `@xyflow/react`(React Flow) 기반으로 구현한다.
   - 노드 최소 집합: Query, Source(SearchOutput.sources), Claim(ExtractOutput.claims), Verification(VerifyOutput.verdicts), Report 섹션(ReportOutput 주요 필드), Visual Components(VisualOutput.components)
   - 엣지 최소 규칙:
     - Claim → Source (`source_id` 기반)
     - Verification → Claim (텍스트 매칭 또는 별도 매핑 규칙)
     - Report → Citation (ReportOutput.citations)
     - Visual Component → Report 섹션 (컴포넌트 생성 근거 매핑)
   - 그래프에서 각 노드를 클릭하면 **해당 단계의 원본 payload(JSON)**가 항상 보인다.

3. **에이전트 Trace/Observability 시각화**
   - 단계별 흐름(Clarify → Plan → Search → Extract → Verify → Write → Visualize)을 **타임라인/그래프**로 표시한다.
   - 각 단계는 “입력 payload → 출력 payload”가 기본 노출된다. (숨김 옵션은 제공 가능하되 기본은 항상 노출)
   - 단계 간 연결이 실제로 전달되었음을 보여주기 위해, **전달된 입력 payload를 그대로 표시**한다.

4. **Streaming UX**
   - Streaming 이벤트를 시간순으로 표시하고, 텍스트/결과가 **점진적으로 업데이트**된다.
   - 이벤트 원문(payload)을 별도 패널에서 항상 확인할 수 있어야 한다.
   - 백엔드가 없을 경우에도 **스트림 이벤트 로그(NDJSON 등) 재생 모드**로 데모 가능해야 한다.

5. **단독 실행 우선**
   - 백엔드 없이도 샘플 Run Bundle/스트림 로그만으로 UI가 동작해야 한다.
   - 데모 데이터를 repo 내 고정 경로에 포함하거나, 실행 시 자동 다운로드/생성할 수 있어야 한다.

6. **배포 고려 (Vercel 가산점)**
   - Next.js App Router 기준으로 구성하며, 배포 시에도 동일한 기능이 동작해야 한다.
   - 로컬 전용을 기본으로 하되, Vercel 배포가 가능한 형태(정적/서버리스 모두 허용)로 유지한다.

7. **성능 및 구현 원칙 (vercel-react-best-practices 준수)**
   - 무거운 그래프 라이브러리는 **dynamic import**로 분리한다. (`bundle-dynamic-imports`)
   - 데이터 로딩은 병렬화하고(Suspense/Promise.all), 불필요한 waterfall을 제거한다. (`async-parallel`, `async-suspense-boundaries`)
   - 불필요한 리렌더를 피하도록 그래프 노드/엣지 계산은 memoization한다. (`rerender-memo`)
   - barrel import를 피하고 직접 import한다. (`bundle-barrel-imports`)

8. **테스트 구성**
   - **Demo E2E + 프론트엔드 단위 테스트**로 구성한다.
   - 테스트는 입력/출력 payload를 기본으로 출력하고, 테스트 로그/아티팩트를 남긴다.
   - 실행한 테스트 명령과 환경(`node`, `pnpm`, `npm` 등)을 문서에 기록한다.

9. **루프 상한/환경 로드**
   - Streaming 폴링/재생 루프에는 반드시 상한을 둔다. 기본값은 env로, CLI 옵션으로 오버라이드 가능해야 한다.
   - 실행/테스트는 `.env`를 기본 로드하여 필요한 키가 자동 반영되도록 한다.

10. **문서 업데이트**
   - README에 실행 방법, 테스트 방법, 현재 구현 상태를 반영한다.
   - “조건 충족 여부/에이전트 구현 현황” 섹션은 실제 상태와 동기화한다.

## 비목표 (Non-goals)
- 백엔드/에이전트 로직 변경
- 사용자 인증, 멀티유저, 복잡한 배포 인프라 구축
- 완전한 프로덕션급 디자인 시스템 구축
- Visualizer 스키마의 근본적 재설계

## 제약 (Constraints)
- Next.js App Router 기반 프론트엔드로 구현한다.
- 데이터 계약은 `main.py`와 `docs/schemas/visual-output.schema.json`과 호환되어야 한다.
- 출력 JSON은 ASCII-safe를 기본으로 유지한다.
- 새로 생성된 파일은 사용자 의도로 간주한다.
- `_req_req.md` 등 프롬프트 로그 파일은 삭제하지 않는다.

## 성공 기준
- 샘플 Run Bundle로 실행 시 그래프/타임라인/리포트 렌더링이 모두 보인다.
- Streaming 이벤트가 실시간/재생 모드 모두에서 정상 표시된다.
- 각 단계의 입력/출력 payload가 기본 노출되며, 연결 관계가 시각적으로 확인된다.
- E2E + 단위 테스트가 통과하고, 테스트 로그/아티팩트가 남는다.
- (가산점) Vercel 배포 URL에서 동일하게 동작한다.

## 참고
- `docs/demo-scenario.md`
- `docs/schemas/visual-output.schema.json`
- `main.py` (출력 구조)
- `plans/006-frontend/sample-1.png` ~ `sample-4.png`
