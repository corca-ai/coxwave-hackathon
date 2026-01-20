# Research Navigator

> 연구자를 위한 자율형 리서치 및 동적 시각화 에이전트

## 데모

(데모 URL 또는 영상 링크 - 구현 후 추가)

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

## 조건 충족 여부

- [ ] OpenAI API 사용
- [ ] 멀티에이전트 구현
- [ ] 실행 가능한 데모

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

| Agent | 역할 | 입력 | 출력 |
|-------|------|------|------|
| Clarifier | 질의 명확화 | 사용자 질의 | 명확화된 질의 + 연구 범위 |
| Search | 논문 검색 및 필터링 | 검색 쿼리 | 관련 논문 목록 |
| Extractor | 구조화된 정보 추출 | 논문 텍스트 | Claim, Concept, 메타데이터 |
| Verifier | 품질 검증 | Claim + Evidence | 검증 결과 + 신뢰도 |
| Writer | 리포트 합성 | 검증된 Claim들 | 구조화된 리포트 |

## 기술 스택

- **LLM**: OpenAI GPT-4o / GPT-4o-mini
- **에이전트 프레임워크**: [OpenAI Agent SDK (Python)](https://github.com/openai/openai-agents-python/)
- **파이프라인 최적화**: [DSPy](https://dspy.ai/) - metric 기반 자동 최적화
- **지식 그래프**: GraphDB (OWL 추론 + SHACL 검증)
- **스키마**: RDF/OWL + SPARQL
- **Frontend**: (TBD)

## 설치 및 실행

```bash
# 환경 설정
cp .env.example .env
# API 키 입력: OPENAI_API_KEY, GRAPHDB_ENDPOINT

# 의존성 설치
pip install -r requirements.txt

# 실행
python main.py
```

## 문서

- [concepts.md](./concepts.md) - 지식 그래프/온톨로지 핵심 개념
- [implementation.md](./implementation.md) - 구현 도구 및 기술 스택
- [demo-scenario.md](./demo-scenario.md) - 데모 시나리오 상세
- [meta-strategy.md](./meta-strategy.md) - 개발 전략
- [retrospective.md](./retrospective.md) - 기존 시스템 구축 회고
- [kg2 스킬 문서](../.claude/skills/kg2/SKILL.md) - 그래프 운영 규칙/스키마 정본

## 향후 계획

- [ ] 지식 그래프 스키마 확정 및 초기 데이터 수집
- [ ] DSPy 기반 추출/검증 파이프라인 구축
- [ ] Agent SDK로 워크플로우 통합
- [ ] UI 구현 및 Observability 추가
- [ ] Self-Healing 파이프라인 자동화

## 팀원

| 이름 | 역할 |
| ---- | ---- |
|      |      |
|      |      |
|      |      |
