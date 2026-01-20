# Research Navigator

> 연구자를 위한 자율형 리서치 및 동적 시각화 에이전트

## 데모

CLI 데모 (Mock / Live):

```bash
# Mock 모드
python3 main.py --mock --query "Which techniques improve long-context reliability?"

# 실제 에이전트 모드 (OPENAI_API_KEY 필요)
python3 main.py --query "Which techniques improve long-context reliability?"
```

실제 에이전트 연결은 `agents_impl.py`의 `build_agents()`에서 구성되어 있다.

### Clarifier 단독 실행

```bash
python3 clarifier_cli.py --query "Ambiguous short query"
```

### Writer 단독 실행

```bash
python3 writer_cli.py --input path/to/writer_input.json
```

### Visualizer 단독 실행

```bash
python3 visualizer_cli.py --input path/to/report.json
```

### Search Agent

Search Agent를 단독으로 실행할 수 있다:

```bash
# 환경 설정
cp .env.example .env
# OPENAI_API_KEY 입력

# 의존성 설치
pip install -e ".[dev]"

# Search Agent 실행
python -m src.runner --goal "Graph RAG for scientific papers"

# 옵션 지정
python -m src.runner \
  --goal "LLM agents for code generation" \
  --namespace demo \
  --target-docs 20 \
  --artifacts-dir artifacts
```

### Frontend UI (Local)

```bash
cd frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:3000`을 열면 된다. 기본 데모 데이터는 `frontend/public/demo/`를 사용하며, Run Bundle JSON과 stream NDJSON을 업로드해서 교체할 수 있다.
Vercel 배포 시 Root Directory는 `frontend/`, Build Command는 `npm run build`, Output Directory는 `.next` 기본값을 사용한다.

## 문제 정의

새로운 분야를 탐구할 때 연구자들은:

- 방대한 자료를 수집하고 파편화된 지식을 연결하는 데 많은 시간을 소비
- 수집된 문서들 간의 맥락과 관계를 파악하기 어려움
- 인사이트를 효과적으로 시각화하고 전달하는 데 추가 노력 필요

**타겟 유저**: 진지한 연구자, 사내 변호사, 신사업 PM 등 - 초반에 시간이 걸려도 깊이 있는 결과를 원하는 사용자

## 솔루션

자료 수집부터 시각화까지 스스로 수행하는 **End-to-End Multi-Agent Workflow**:

1. **Clarify**: 사용자의 의도를 파악하고 명확화 질문
2. **Plan**: 연구 계획 수립 및 사용자 승인
3. **Search & Extract**: 심층적인 자료 조사 및 구조화된 정보 추출
4. **Verify**: Claim/Evidence 평가 및 품질 검증
5. **Synthesize**: 리포트 합성 및 시각화

핵심 차별점:

- **지식 그래프 기반**: 단순 검색이 아닌, 문서 간 관계(인용, 확장, 반박)를 구조화
- **Self-Healing 데이터**: 품질 지표 기반 자동 개선 (고립 노드 탐지, 연결성 강화)
- **Observability**: 에이전트 동작 과정을 사용자에게 투명하게 공개

## 데모 시나리오

- 사용자가 질의를 입력
- Clarifier가 의도 파악 및 필요한 질문
- 충분히 명확해지면 “이 방식으로 연구할까요?” 확인
- 승인 시 Orchestrator가 자동 진행하며 Verifier가 증거 충분성을 판단
- 부족하면 Search → Extract → Verify 루프를 수행
- Writer가 최종 JSON 리포트를 생성
- (Optional) Visualizer가 사전 컴포넌트를 조합
- 최종 결과 출력

## 성공 기준 (Demo)

- **End-to-end completion**: 벤치마크 3개 질의에서 모든 단계 완료 및 종료 코드 0
- **Clarification quality**: 모호한 질의 1개 이상에서 clarifying question ≥1개, 답변이 Planner 컨텍스트에 반영
- **Plan approval**: 각 질의에서 1회 이내 수정으로 계획 승인
- **Evidence sufficiency**: Verifier가 `is_enough = true` 및 supported claim ≥2개(각각 `source_id`+evidence 포함)
- **Report completeness**: executive summary 포함, key findings는 가능하면 ≥3(부족 시 limitations에 명시), citations가 sources와 정합
- **Observability**: 모든 단계 JSON 출력, 데모 환경에서 질의당 3분 내 완료
- **Automated E2E**: mock 모드 end-to-end 테스트가 무인으로 통과

## 조건 충족 여부

- [x] OpenAI API 사용 (Clarifier/Planner/Search/Extract/Verify/Writer/Visualizer: Agent SDK)
- [x] 멀티에이전트 구현 (상태 기반 오케스트레이션, mock 모드 지원)
- [x] 실행 가능한 데모 (Mock + Live)
- [x] Frontend UI (Graph/Trace/Streaming)

## 에이전트 구현 현황

| Agent | Status | Notes |
| --- | --- | --- |
| Orchestrator | Implemented (state-based) | `main.py`의 Orchestrator loop (live 모드에서 실제 에이전트 호출) |
| Clarifier | Implemented (OpenAI Agents SDK) | 단독 CLI + 단위 테스트 |
| Planner | Implemented (OpenAI Agents SDK) | `src/agent/plan` (Orchestrator에서 호출) |
| Searcher | Implemented (OpenAI Agents SDK) | `src/runner.py`로 단독 실행 가능 |
| Extractor | Implemented (OpenAI Agents SDK) | `src/agent/extract/runner.py`로 단독 실행 |
| Verifier | Implemented (Standalone CLI) | `src/agent/verify/runner.py`로 단독 실행 |
| Writer | Implemented (OpenAI Agents SDK) | 단독 CLI + 단위 테스트 |
| Visualizer | Implemented (OpenAI Agents SDK) | 단독 CLI + 단위 테스트 |

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
- **파이프라인 최적화**: [DSPy](https://dspy.ai/) - metric 기반 자동 최적화
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

# Clarifier 단독 실행
python3 clarifier_cli.py --query "Your research question"

# Frontend UI
cd frontend
npm install
npm run dev

# Writer 단독 실행
python3 writer_cli.py --input path/to/writer_input.json
```

`.env` 파일에 `OPENAI_API_KEY`를 넣어두면 자동으로 로드된다.
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

## 향후 계획

- [ ] 지식 그래프 스키마 확정 및 초기 데이터 수집
- [ ] DSPy 기반 추출/검증 파이프라인 구축
- [ ] Agent SDK로 워크플로우 통합
- [x] UI 구현 및 Observability 추가 (Graph/Trace/Streaming, local demo)
- [ ] Vercel 배포 (Frontend)
- [ ] Self-Healing 파이프라인 자동화

## 팀원

| 이름 | 역할 |
| ---- | ---- |
|      |      |
|      |      |
|      |      |


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