# Docker Infrastructure

Research Navigator의 인프라 구성요소를 관리합니다.

## 구성요소

| 서비스 | 이미지 | 포트 | 용도 |
|--------|--------|------|------|
| GraphDB | ontotext/graphdb:10.6.0 | 7200 | Knowledge Graph (RDF/SPARQL) |
| Qdrant | qdrant/qdrant:v1.12.1 | 6333, 6334 | Vector DB (RAG) |

## Quick Start

```bash
# 인프라 시작
docker compose up -d

# 상태 확인
docker compose ps

# 로그 확인
docker compose logs -f

# 종료
docker compose down
```

## 서비스 접속

### GraphDB Workbench
- URL: http://localhost:7200
- Repository: `researcher` (수동 생성 필요)

### Qdrant Dashboard
- URL: http://localhost:6333/dashboard

## Repository 초기 설정

### 1. GraphDB Repository 생성

GraphDB Workbench (http://localhost:7200) 접속 후:

1. **Setup** → **Repositories** → **Create new repository**
2. **GraphDB Repository** 선택
3. 설정:
   - Repository ID: `researcher`
   - Ruleset: `RDFS-Plus (Optimized)`
   - Enable OWL sameAs: `true`
4. **Create** 클릭

또는 설정 파일 사용:
```bash
# 설정 파일 위치
docker/graphdb/init/researcher-repo-config.ttl
```

### 2. Ontology 로드

Repository 생성 후:

1. **Import** → **RDF** → **Upload RDF files**
2. `docker/graphdb/init/ontology.ttl` 업로드
3. **Import** 클릭

### 3. Qdrant Collection 생성

**방법 1: 스크립트 사용 (권장)**
```bash
PYTHONPATH=src python scripts/init_qdrant.py
```

**방법 2: curl 사용**
```bash
curl -X PUT http://localhost:6333/collections/papers \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 1536,
      "distance": "Cosine"
    }
  }'
```

### 4. Collection 확인

```bash
curl http://localhost:6333/collections/papers
```

## 데이터 영속성

볼륨 위치:
- `researcher-graphdb-data`: GraphDB 데이터
- `researcher-qdrant-data`: Qdrant 벡터 데이터

데이터 완전 삭제:
```bash
docker compose down -v
```

## 환경변수

`.env.docker` 파일 참조:

```bash
# 복사 후 수정
cp .env.docker .env
```

주요 변수:
- `GRAPHDB_SPARQL_ENDPOINT`: SPARQL 쿼리 엔드포인트
- `QDRANT_URL`: Qdrant HTTP API URL
- `QDRANT_COLLECTION_NAME`: 벡터 컬렉션 이름

## 트러블슈팅

### GraphDB가 시작되지 않음
```bash
# 로그 확인
docker compose logs graphdb

# 메모리 부족 시 docker-compose.yml에서 GDB_JAVA_OPTS 조정
# -Xms512m -Xmx1g (최소 설정)
```

### Qdrant 연결 실패
```bash
# 헬스체크
curl http://localhost:6333/healthz

# 컬렉션 목록
curl http://localhost:6333/collections
```

### 포트 충돌
다른 포트 사용 시 `docker-compose.yml` 수정:
```yaml
ports:
  - "17200:7200"  # GraphDB
  - "16333:6333"  # Qdrant
```
