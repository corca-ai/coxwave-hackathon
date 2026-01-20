# RAG Implementation Design

## Overview

Research Navigator에 Qdrant 기반 RAG (Retrieval-Augmented Generation) 시스템 구현.

## 결정 사항

| 항목 | 결정 | 이유 |
|------|------|------|
| 벡터 DB | Qdrant v1.12.1 | Docker Compose에 이미 설정됨 |
| Embedding | OpenAI text-embedding-3-small | 1536차원, 비용 효율적 |
| 검색 단위 | Paper (abstract 전체) | 해커톤에 적합, 간단 |
| 검색 전략 | source_id 우선 + semantic fallback | 정확도 + 유연성 |

## 인프라 설정

```yaml
# docker-compose.yml (기존)
qdrant:
  image: qdrant/qdrant:v1.12.1
  ports:
    - "6333:6333"  # HTTP
    - "6334:6334"  # gRPC
```

```bash
# Collection 생성
curl -X PUT http://localhost:6333/collections/papers \
  -H "Content-Type: application/json" \
  -d '{"vectors": {"size": 1536, "distance": "Cosine"}}'
```

## 에이전트별 RAG 도구

### Search Agent

| 도구 | 변경 |
|------|------|
| `rag_ingest_candidates` | JSON 저장 + Qdrant upsert (embedding 생성) |
| `rag_preview` | Qdrant semantic search 구현 |

### Verifier Agent

| 도구 | 설명 |
|------|------|
| `rag_get_evidence` (신규) | source_id로 조회 → 없으면 semantic search fallback |

## 데이터 흐름

```
[Search Agent]
    ↓ rag_ingest_candidates
    ↓ (1) JSON 저장
    ↓ (2) OpenAI embedding 생성
    ↓ (3) Qdrant upsert

[Verifier Agent]
    ↓ rag_get_evidence(claim, source_ids)
    ↓ (1) Qdrant get_by_ids(source_ids)
    ↓ (2) 부족하면: semantic search(claim)
    ↓ → evidence snippets 반환

[Orchestrator]
    ↓ accumulated_sources → Writer context에 추가

[Writer]
    ↓ sources 활용하여 citation 포함 리포트 생성
```

## Writer Context 수정

**Before**:
```python
writer_context = {
    "supported_claims": [...],
    "weak_claims": [...],
    "total_sources": 5,  # 개수만
}
```

**After**:
```python
writer_context = {
    "supported_claims": [...],
    "weak_claims": [...],
    "sources": [asdict(s) for s in accumulated_sources],  # 전체 내용
}
```

## 파일 구조

```
src/
├── shared/
│   └── rag/                    # 신규
│       ├── __init__.py
│       ├── client.py           # QdrantRAG 클래스
│       ├── embeddings.py       # get_embedding()
│       └── schemas.py          # VectorDocument
├── agent/
│   ├── search/
│   │   └── tools/
│       │   └── rag.py          # 수정: Qdrant 연동
│   └── verify/
│       └── tools/
│           ├── kg.py           # 기존 유지
│           └── rag.py          # 신규: rag_get_evidence
main.py                         # 수정: writer_context
```

## 구현 순서

### Phase 1: 인프라
1. `src/shared/rag/client.py` - Qdrant 클라이언트
2. `src/shared/rag/embeddings.py` - OpenAI embedding
3. `src/shared/rag/schemas.py` - 스키마
4. Collection 초기화

### Phase 2: Search Agent
5. `rag_ingest_candidates` 수정
6. `rag_preview` 구현

### Phase 3: Verifier Agent
7. `rag_get_evidence` 신규
8. Agent 도구 등록

### Phase 4: Orchestrator
9. Writer context 수정

### Phase 5: 테스트
10. 단위 테스트
11. 통합 테스트 (Docker)
12. E2E 검증

## 의존성

```
qdrant-client>=1.12.0
```

## 환경변수

```bash
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=papers
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=sk-...
```
