# Research Navigator - Search Agent

> 연구자를 위한 자율형 리서치 에이전트

## Quick Start

```bash
# 환경 설정
cp .env.example .env
# OPENAI_API_KEY 입력

# 의존성 설치
pip install -e ".[dev]"

# 실행
python -m src.runner --goal "Graph RAG for scientific papers"
```

## CLI 옵션

```bash
python -m src.runner \
  --goal "LLM agents for code generation" \
  --namespace demo \
  --target-docs 20 \
  --artifacts-dir artifacts
```

## 테스트

```bash
pytest tests/ -v
```

## 프로젝트 구조

```
src/
├── agents/search/     # Search Agent 모듈
│   ├── agent.py       # Agent 정의
│   ├── schemas.py     # Pydantic 모델
│   ├── tools/         # function_tools
│   └── clients/       # API 클라이언트
├── shared/            # 공유 모듈
└── runner.py          # CLI 진입점
```

## 문서

- [설계 문서](docs/plans/2026-01-20-search-agent-design.md)
- [구현 계획](docs/plans/2026-01-20-search-agent-impl.md)
