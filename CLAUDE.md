# Research Navigator

연구자를 위한 자율형 리서치 및 동적 시각화 에이전트

## 핵심 문서

- `docs/README.md` - 프로젝트 비전 & 아키텍처
- `docs/concepts.md` - 지식그래프/온톨로지 개념
- `docs/implementation.md` - 기술 스택 (DSPy, OpenAI SDK)
- `docs/hackathon.md` - 해커톤 심사 기준 전문
- `.claude/skills/kg2/SKILL.md` - KG2 시스템 레퍼런스
- `openai-agents-python-docs/` - OpenAI Agent SDK 문서

## 해커톤 심사 기준 요약

**필수**: OpenAI API/SDK 사용 + 실행 가능한 데모 (README에 명시)

| 항목 | 배점 | 핵심 |
|------|------|------|
| 아이디어 | 30% | B2B Pain Point 해결, AI 필수성 |
| 기술 구현 | 40% | 멀티에이전트 협업, 에러 복구, Function Calling 견고성 |
| 완성도 | 20% | Edge Case 대응, 응답속도/비용 효율 (오버엔지니어링 지양) |
| 문서화 | 10% | README/아키텍처 문서 명확성 |

**가산점**: Safety(가드레일), Advanced UX(Human-in-the-loop), Observability(로그/디버깅)

## 아키텍처

```
User → Clarifier → Orchestrator → [Planner|Search|Extractor|Verifier|Writer|Visualizer] → KG
```

**Knowledge Graph**: Paper ↔ Claim ↔ Concept (extends/refutes/supports 관계)

## 기술 스택

- **Backend**: GraphDB (RDF/SPARQL), OWL/SHACL
- **API**: Semantic Scholar, arXiv, OpenAlex, OpenAI
- **Framework**: OpenAI Agent SDK (멀티에이전트)
