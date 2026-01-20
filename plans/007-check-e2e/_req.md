# 007-check-e2e 실행/검증 계획

## 1) CLI 데모 E2E (자동화 + 수동)

### 자동화 테스트
- 단위/통합 스모크: `.venv/bin/python -m pytest tests/ -v`
- Demo E2E (mock, 결정적/무API키): `.venv/bin/python -m unittest tests/test_demo_e2e.py`
- (API 키 있을 때) Integration 마커: `.venv/bin/python -m pytest -m integration`

관찰 포인트
- stdout에 모든 단계 입력/출력 payload가 출력되는지
- `tests/_artifacts/`에 로그가 생성되는지
- Demo E2E에서 섹션 헤더(Clarify/Plan/Search/Extract/Verify/Write/Visualize)가 모두 포함되는지

### 수동 테스트 시나리오
1. **모호한 질의 (Clarifier 루프 확인)**
   - `python3 main.py --query "RAG"`
   - 관찰: Clarifier 질문 출력, 응답/스킵 흐름, Clarifier context JSON 구조
2. **명확한 질의 (바로 진행)**
   - `python3 main.py --query "Evaluate long-context reliability techniques"`
   - 관찰: Clarifier가 즉시 is_clear_enough=true, Orchestrator가 Plan→Search→Extract→Verify→Write 순서로 진행
3. **결정적 재현 필요 시 (옵션)**
   - `python3 main.py --mock --query "Evaluate long-context reliability techniques"`
   - 관찰: mock 모드에서도 동일한 섹션/출력 구조 유지

확신을 위한 체크리스트
- 각 단계 payload가 콘솔에 출력
- Orchestrator 루프 상한이 지켜짐
- Verify 결과에 is_enough/next_actions가 포함됨
- Writer 결과가 ReportOutput 스키마를 준수

## 2) Frontend 연결 (자동화 + 수동)

### 자동화 테스트
- Unit: `cd frontend && npm run test:unit`
- E2E: `cd frontend && npm run test:e2e`

관찰 포인트
- `frontend/tests/_artifacts/`에 테스트 로그/아티팩트가 생성되는지
- stream-events/run-bundle 스키마 테스트가 통과하는지

### 수동 테스트 시나리오
1. **로컬 데모 데이터 로드**
   - `cd frontend && npm install && npm run dev`
   - 브라우저에서 `http://localhost:3000`
   - 관찰: Graph/Trace/Stream 패널이 정상 렌더링되고 초기 데모 데이터가 표시되는지
2. **Run Bundle 업로드/교체**
   - UI에서 `frontend/public/demo/run-bundle.json` 업로드
   - 관찰: 시각화가 입력 데이터로 갱신되는지
3. **Stream NDJSON 업로드/재생**
   - `frontend/public/demo/stream-events.ndjson` 업로드
   - 관찰: 이벤트 재생, maxEvents 제어(`?maxEvents=50`) 반영 여부
4. **Payload 확인**
   - Observability 패널에서 입력/출력 payload가 표시되는지

확신을 위한 체크리스트
- UI 로딩/렌더링 오류 없음
- 그래프/트레이스/스트림 패널 간 상태 동기화
- 업로드/재생 시각화 갱신
- maxEvents 제한이 실제로 적용됨

## 3) API 서버 (Streaming)

### 자동화 테스트 (스모크)
- 서버 실행: `python3 server.py`
- 헬스 체크: `curl -s http://localhost:8000/health`
- 간단 스트림 확인 (SSE):
  - `curl -N -X POST http://localhost:8000/api/run/stream -H "Content-Type: application/json" -d '{"query":"Graph RAG for scientific papers"}'`
 - 프론트 연동: `NEXT_PUBLIC_API_BASE`로 서버 주소 오버라이드 가능 (기본: `http://localhost:8000`)

### 수동 테스트 시나리오
1. **/health 확인**
   - 관찰: `{"status":"ok","agents_loaded":true}` 응답
2. **Clarify 스트림**
   - `/api/clarify/stream` 호출 시 event stream이 순서대로 수신되는지
3. **Full pipeline 스트림**
   - `/api/run/stream` 호출 시 pipeline_start → agent events → pipeline_complete 흐름 확인

확신을 위한 체크리스트
- SSE 이벤트가 `data: {json}\n\n` 형태로 연속 수신됨
- 에러 시 `StreamEventTypes.ERROR`가 반환됨
- 클라이언트 중단 시 서버가 예외 없이 종료
