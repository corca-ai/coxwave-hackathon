# [팀명 입력] - Research Navigator

> 연구자, 기업 전략가, 전문직을 위한 자율형 리서치 및 동적 시각화 에이전트

## 🎥 데모

- **시연 영상**: [여기에 YouTube 또는 Loom 영상 링크를 넣어주세요]
- **라이브 데모**: [여기에 배포된 URL이 있다면 넣어주세요]

**(스크린샷이나 GIF가 있다면 여기에 추가하여 시각적 효과를 높이세요)**

## 문제 정의

기업의 R&D 부서, 전략 기획실, 법무팀 등에서는 새로운 분야를 조사하는 데 막대한 시간과 인력을 소모합니다.

- **비효율적인 정보 수집**: 수천 건의 문서를 일일이 검색하고 읽는 데 수십 시간이 소요됩니다.
- **파편화된 지식**: 수집된 정보가 연결되지 않아 전체적인 맥락(Context)을 놓치기 쉽습니다.
- **낮은 신뢰성**: LLM의 환각(Hallucination) 현상으로 인해 전문적인 업무에 바로 적용하기 어렵습니다.

**타겟 유저 (B2B/Enterprise)**:
- **R&D 연구원**: 선행 기술 조사 시간을 5일 -> 1시간으로 단축
- **사내 변호사**: 판례 및 법률 리서치 자동화로 업무 효율 50% 증대
- **신사업 PM**: 시장 동향 및 경쟁사 분석 보고서 즉시 생성

## 솔루션

자료 수집부터 검증, 시각화까지 스스로 수행하는 **End-to-End Multi-Agent Workflow**:

1. **Clarify**: 모호한 업무 지시를 구체적인 리서치 주제로 명확화
2. **Plan**: 기업 환경에 맞는 단계별 리서치 계획 수립 및 승인
3. **Search & Extract**: Arxiv 등 신뢰할 수 있는 소스에서 심층 조사 및 정보 추출
4. **Verify**: 추출된 정보의 출처와 사실 관계를 교차 검증 (Cross-Check)
5. **Synthesize**: 경영진 보고용 리포트 자동 생성 및 시각화

핵심 차별점:

- **Self-Healing Knowledge Graph**: 단순 검색이 아닌, 정보 간의 인과 관계와 모순을 그래프로 구조화하여 분석
- **Enterprise-Grade Safety**: 입력 데이터 보호 및 출력 결과의 신뢰성 보장 (Guardrails 적용)
- **Full Observability**: 에이전트의 모든 사고 과정과 데이터 흐름을 실시간으로 추적 가능

## 데모 시나리오

- 사용자가 질의를 입력 (예: "RAG 시스템의 최신 트렌드 조사해줘")
- **Clarifier**가 의도 파악 및 필요한 질문 (PII/비윤리적 주제 필터링)
- 충분히 명확해지면 “이 방식으로 연구할까요?” 확인
- 승인 시 **Orchestrator**가 자동 진행하며 **Verifier**가 증거 충분성을 판단
- 부족하면 Search → Extract → Verify 루프를 수행 (Self-Healing)
- **Writer**가 최종 JSON 리포트를 생성 (Hallucination 검사)
- (Optional) **Visualizer**가 사전 컴포넌트를 조합하여 시각화
- 최종 결과 출력

## 🛡️ Safety & Reliability (가드레일)

기업 환경 도입을 위해 `guardrails.py`를 통한 강력한 안전 장치를 적용했습니다.

- **Input Guardrails**:
  - **Off-topic**: 업무와 무관한 잡담, 코딩 요청 차단
  - **Unethical**: 무기, 마약, 해킹 등 비윤리적 연구 주제 원천 봉쇄
  - **PII Protection**: API Key, 개인정보 등이 포함된 질의 자동 마스킹
- **Output Guardrails**:
  - **Hallucination Check**: 근거(Reference)가 없는 주장은 사용자에게 전달되지 않음
  - **Overconfidence Check**: 불확실한 정보를 "확실하다"고 표현하는 과장된 언어 탐지

## 조건 충족 여부

- [x] **OpenAI API / SDK 사용** (Clarifier, Planner, Searcher 등 전 에이전트 적용)
- [x] **멀티에이전트 협업** (상태 기반 오케스트레이션 및 Loop 구조)
- [x] **실행 가능한 데모** (CLI 및 Frontend UI 제공)
- [x] **기업용 시나리오** (B2B 리서치 자동화 및 ROI 명시)
- [x] **Safety & Guardrails** (입출력 필터링 및 할루시네이션 방지)
- [x] **Observability** (실시간 추적 및 DSPy 최적화 리포트)

## 성공 기준 (Demo)

## 에이전트 구현 현황

| Agent | Status | Notes |
| --- | --- | --- |
| Orchestrator | Implemented (state-based) | `main.py`의 Orchestrator loop (live 모드에서 실제 에이전트 호출) |
| Clarifier | Implemented (Agent SDK + DSPy) | 단독 CLI + 단위 테스트 + DSPy CLI |
| Planner | Implemented (Agent SDK + DSPy) | `src/agent/plan` + DSPy CLI |
| Searcher | Implemented (Agent SDK + DSPy) | `src/agent/search` + DSPy CLI |
| Extractor | Implemented (Agent SDK + DSPy) | `src/agent/extract/runner.py` + DSPy CLI |
| Verifier | Implemented (Standalone CLI + DSPy) | `src/agent/verify/runner.py` + DSPy CLI |
| Writer | Implemented (Agent SDK + DSPy) | 단독 CLI + DSPy CLI |
| Visualizer | Implemented (Agent SDK + DSPy) | 단독 CLI + DSPy CLI |

## 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                        User Interface                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator Agent                        │
│              (상태 기반 라우팅, 재시도/중단 판단)              │
└─────────────────────────────────────────────────────────────┘
          │           │           │           │           │
          ▼           ▼           ▼           ▼           ▼
     ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
     │Clarifier│ │ Search │ │Extractor│ │Verifier│ │ Writer │
     │ Agent  │ │ Agent  │ │ Agent  │ │ Agent  │ │ Agent  │
     └────────┘ └────────┘ └────────┘ └────────┘ └────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Knowledge Graph                          │
│                                                              │
│  ┌────────┐    cites    ┌────────┐                          │
│  │ Paper  │◄───────────►│ Paper  │                          │
│  └────┬───┘             └────┬───┘                          │
│       │ hasClaim             │ about                        │
│       ▼                      ▼                              │
│  ┌────────┐   extends   ┌────────┐   broader   ┌────────┐  │
│  │ Claim  │────────────►│ Claim  │   ┌────────►│Concept │  │
│  └────────┘             └────────┘   │         └────────┘  │
│                              │regarding                     │
│                              └───────┘                      │
└─────────────────────────────────────────────────────────────┘
```

### 에이전트 역할

| Agent     | 역할                | 입력             | 출력                       |
| --------- | ------------------- | ---------------- | -------------------------- |
| Clarifier | 질의 명확화         | 사용자 질의      | 명확화된 질의 + 연구 범위  |
| Search    | 논문 검색 및 필터링 | 검색 쿼리        | 관련 논문 목록             |
| Extractor | 구조화된 정보 추출  | 논문 텍스트      | Claim, Concept, 메타데이터 |
| Verifier  | 품질 검증           | Claim + Evidence | 검증 결과 + 신뢰도         |
| Writer    | 리포트 합성         | 검증된 Claim들   | 구조화된 리포트            |

## 기술 스택

- **LLM**: OpenAI GPT-4o-mini / GPT-5-mini (에이전트별 기본값, `OPENAI_MODEL`로 일부 구성 가능)
- **에이전트 프레임워크**: [OpenAI Agent SDK (Python)](https://github.com/openai/openai-agents-python/)
- **DSPy**: 전 에이전트 모듈 + metric 기반 자동 최적화
- **지식 그래프**: GraphDB (Docker 설정 포함, `kg_query`는 v1 mock)
- **스키마**: RDF/OWL + SPARQL
- **Frontend**: Next.js App Router + @xyflow/react (React Flow)

## 설치 및 실행

```bash
# 의존성 설치 (Clarifier 실사용 시 필요)
pip install -r requirements.txt

# DSPy 개발용 의존성 (선택)
pip install -r requirements-dev.txt

# API 키 설정 (환경변수 또는 .env 파일)
export OPENAI_API_KEY=sk-...

# Mock 실행 (API 키 불필요)
python3 main.py --mock --query "Your research question"

# 실제 에이전트 연결 후 실행
python3 main.py --query "Your research question"

# DSPy 전체 전환 (옵션)
export USE_DSPY_ALL=1
python3 main.py --query "Your research question"

# Clarifier 단독 실행
python3 clarifier_cli.py --query "Your research question"

# Frontend UI
cd frontend
npm install
npm run dev

# Writer 단독 실행
python3 writer_cli.py --input path/to/writer_input.json

# DSPy 단독 실행
python3 -m dspy_integration.clarifier_cli --query "AI alignment"
python3 -m dspy_integration.planner_cli --input path/to/clarifier_context.json
python3 -m dspy_integration.searcher_cli --input path/to/search_context.json
python3 -m dspy_integration.extractor_cli --input path/to/search_output.json
python3 -m dspy_integration.verifier_cli --input path/to/extract_output.json
python3 -m dspy_integration.writer_cli --input path/to/writer_input.json
python3 -m dspy_integration.visualizer_cli --report-json '{"title":"Demo","executive_summary":"...","key_findings":["A"],"limitations":["L"],"citations":["https://example.com"]}'
```

`.env` 파일에 `OPENAI_API_KEY`를 넣어두면 자동으로 로드된다.
DSPy 전환은 `USE_DSPY_ALL` 또는 `USE_DSPY_<AGENT>` 플래그로 제어한다.
Clarifier 반복 횟수는 `DEMO_MAX_CLARIFY_ROUNDS`로 지정하고, `--clarify-rounds`로 오버라이드할 수 있다. 기본값은 2이다.
각 단계 입력 payload는 기본으로 출력되며, 추가 설정 없이도 전달 경로를 확인할 수 있다.
Frontend에서는 `NEXT_PUBLIC_STREAM_MAX_EVENTS`로 스트림 재생 상한을 설정하고, `?maxEvents=` 쿼리로 오버라이드할 수 있다.

### agents_impl.py 인터페이스

`agents_impl.py`에 아래 형태로 에이전트를 구성한다. (예시는 요약)

```python
from main import DemoAgents

def build_agents() -> DemoAgents:
    # 각 에이전트는 run(context: str) -> OutputType 를 구현
    ...
```

## 문서

- [concepts.md](./docs/concepts.md) - 지식 그래프/온톨로지 핵심 개념
- [implementation.md](./docs/implementation.md) - 구현 도구 및 기술 스택
- [dspy.md](./docs/dspy.md) - DSPy 사용/최적화 가이드
- [dspy-report-template.md](./docs/dspy-report-template.md) - DSPy 최적화 리포트 템플릿
- [demo-scenario.md](./docs/demo-scenario.md) - 데모 시나리오 상세
- [meta-strategy.md](./docs/meta-strategy.md) - 개발 전략
- [problem-1pager-demo.md](./plans/002-demo/problem-1pager.md) - 데모 성공 기준/측정
- [visual-output.schema.json](./docs/schemas/visual-output.schema.json) - Visualizer JSON 스키마
- [run-bundle.schema.json](./docs/schemas/run-bundle.schema.json) - Run Bundle 스키마
- [stream-events.schema.json](./docs/schemas/stream-events.schema.json) - 스트리밍 이벤트 스키마
- [retrospective.md](./docs/retrospective.md) - 기존 시스템 구축 회고
- [kg2 스킬 문서](./.claude/skills/kg2/SKILL.md) - 그래프 운영 규칙/스키마 정본
- [Search Agent 설계 문서](docs/plans/2026-01-20-search-agent-design.md)
- [Search Agent 구현 계획](docs/plans/2026-01-20-search-agent-impl.md)

## 테스트

현재 테스트 suite는 **데모 E2E 테스트 + 각 에이전트 단위 테스트**로 구성한다.

```bash
# Search Agent 테스트
pytest tests/ -v

# OPENAI_API_KEY가 없으면 자동으로 skip
python3 -m unittest tests/test_clarifier.py

# Visualizer 단위 테스트 (OPENAI_API_KEY가 없으면 자동으로 skip)
python3 -m unittest tests/test_visualizer.py

# Writer 단위 테스트 (OPENAI_API_KEY가 없으면 자동으로 skip)
python3 -m unittest tests/test_writer.py

# Demo E2E (mock)
python3 -m unittest tests/test_demo_e2e.py
```

### Frontend 테스트

```bash
cd frontend
npm run test:unit
npm run test:e2e
```

### 전체 테스트 스위트 (pytest, integration 제외)

```bash
.venv/bin/python -m pytest -m "not integration"
```

### 통합 테스트 (실제 API 호출 포함)

```bash
.venv/bin/python -m pytest -m integration
```

### 수동 테스트

```bash
# Clarifier 단독 확인
python3 clarifier_cli.py --query "AI alignment"

# Writer 단독 확인 (Writer input JSON 필요)
python3 writer_cli.py --input path/to/writer_input.json

# Writer 단독 확인 (테스트 fixture 사용)
python3 writer_cli.py --input tests/fixtures/writer_input.json

# Visualizer 단독 확인 (ReportOutput JSON 필요)
python3 visualizer_cli.py --input path/to/report.json

# Visualizer 단독 확인 (테스트 fixture 사용)
python3 visualizer_cli.py --input tests/fixtures/visualizer_report.json

# 데모 시나리오 전체 (mock)
python3 main.py --mock --query "Investigate RAG and hallucination in legal QA"

# DSPy Clarifier 단독 확인 (DSPy 설치 필요)
python3 -m dspy_integration.clarifier_cli --query "AI alignment"
```

테스트 실행 로그는 `tests/_artifacts/`에 저장된다.
E2E 테스트는 콘솔에도 전체 로그를 출력한다.
프론트엔드 테스트 로그/아티팩트는 `frontend/tests/_artifacts/`에 저장된다.
실제 실행 환경: 2026-01-20, node v22.17.0, npm 10.9.2.

## 평가(Evals)

로컬 평가 하네스는 에이전트별 JSONL 데이터셋을 사용한다. 입력/출력 payload는 항상 출력된다.

```bash
# Clarifier 평가 (실제 API 사용)
python3 evals_cli.py --agent clarifier --dataset evals/datasets/clarifier.jsonl

# Mock 에이전트로 평가 (API 키 불필요)
python3 evals_cli.py --agent clarifier --dataset evals/datasets/clarifier.jsonl --mock

# DSPy 엔진으로 평가 (DSPy 설치 필요)
python3 evals_cli.py --agent clarifier --engine dspy --dataset evals/datasets/clarifier.jsonl
```

- `EVAL_MAX_SAMPLES`로 평가 샘플 상한을 설정할 수 있으며, `--max-samples`로 오버라이드한다.
- 결과 로그는 기본적으로 `evals/_artifacts/`에 저장되며, `EVAL_ARTIFACT_DIR`로 변경 가능하다.
- 다른 에이전트 평가/최적화 경로는 `docs/dspy.md` 참고.

## 향후 계획

- [ ] 지식 그래프 스키마 확정 및 초기 데이터 수집
- [x] DSPy 기반 추출/검증 파이프라인 구축
- [ ] Agent SDK로 워크플로우 통합
- [x] UI 구현 및 Observability 추가 (Graph/Trace/Streaming, local demo)
- [ ] Vercel 배포 (Frontend)
- [ ] Self-Healing 파이프라인 자동화

## 팀원

| 이름 | 역할 | Github |
| ---- | ---- | ------ |
| [팀원1 이름] | PM / Backend | @github_id |
| [팀원2 이름] | Frontend / Design | @github_id |
| [팀원3 이름] | AI Research / Modeling | @github_id |

---
&copy; 2026 Research Navigator Team. All Rights Reserved.


## 서버 띄우기

### 의존성 설치
```bash
pip install fastapi uvicorn[standard] sse-starlette
```

### 서버 실행
```bash
python server.py
```
또는
```bash
uvicorn server:app --reload --port 8000
```

### 프론트엔드 연동
프론트에서 서버를 직접 호출하려면 `NEXT_PUBLIC_API_BASE`를 설정한다.

```bash
# frontend/.env 또는 환경변수로 지정
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

간단 스모크 테스트:
```bash
python scripts/server_smoke.py
```
