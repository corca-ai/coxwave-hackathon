# 지식 그래프와 온톨로지: 핵심 개념 가이드

이 문서는 연구자를 위한 자율형 리서치 시스템 구축에 필요한 지식 그래프 및 온톨로지 관련 용어와 개념을 정리한다. 기존 kg2 시스템의 설계 결정과 회고를 바탕으로 실용적인 관점에서 설명한다.
운영 절차, 엔드포인트, 스크립트, 상세 스키마는 `../.claude/skills/kg2/SKILL.md` 및 연결 문서를 정본으로 삼는다. 이 문서는 개념과 설계 판단 기준에 집중한다. 비범위/비목표 역시 `../.claude/skills/kg2/SKILL.md`의 Non-Goals를 참고한다.

## 목차

1. [기본 용어](#기본-용어)
2. [핵심 기술 스택](#핵심-기술-스택)
3. [온톨로지 설계 원칙](#온톨로지-설계-원칙)
4. [지식 그래프 품질 지표](#지식-그래프-품질-지표)
5. [Self-Healing 전략](#self-healing-전략)
6. [실용적 교훈](#실용적-교훈)

---

## 기본 용어

### 지식 그래프 (Knowledge Graph)

**정의**: 엔티티(노드)와 관계(엣지)로 구성된 그래프 구조의 데이터베이스. 실세계의 개념들과 그 관계를 표현한다.

**구성 요소**:
- **노드 (Node)**: 개별 엔티티 (예: 논문, 저자, 개념)
- **엣지 (Edge)**: 엔티티 간 관계 (예: "저술함", "인용함", "확장함")
- **트리플 (Triple)**: 주어-술어-목적어 형태의 기본 단위 (예: `Paper A` - `cites` - `Paper B`)

**kg2 예시**:
```
paper:pa_r1s2t3u4 paper:cites paper:pa_v5w6x7y8 .
```
→ "Foundations of Example Research" 논문이 "Advances in Example Methods"를 인용한다.

### 온톨로지 (Ontology)

**정의**: 특정 도메인의 개념들과 그 관계를 정형화한 명세. 지식 그래프의 "스키마" 역할을 한다.

**구성 요소**:
- **클래스 (Class)**: 엔티티의 유형 (예: Paper, Author, Claim, Concept, Venue)
- **프로퍼티 (Property)**: 클래스 간 관계 또는 속성
  - **ObjectProperty**: 엔티티 간 관계 (예: `cites`, `author`)
  - **DatatypeProperty**: 엔티티의 속성값 (예: `year`, `doi`)
- **제약조건 (Constraint)**: 데이터 무결성 규칙

**kg2의 온톨로지 복잡도** (회고에서 언급된 기준):
- 노드 종류: 5개 (Paper, Author, Claim, Concept, Venue)
- 링크 종류: ~15개 (cites, author, primaryAuthor, about, hasClaim, broader, partOf, dependsOn, extends, refutes, supports, regarding, publishedIn 등)

### 트리플 스토어 (Triple Store)

지식 그래프를 저장하는 전문 데이터베이스. RDF 트리플을 저장하고 SPARQL로 쿼리한다.

**kg2에서 사용**: GraphDB

---

## 핵심 기술 스택

### RDF (Resource Description Framework)

**정의**: W3C 표준 데이터 모델. 모든 정보를 "주어-술어-목적어" 트리플로 표현한다.

**특징**:
- URI로 모든 것을 식별 (예: `https://kg.corca.ai/paper#pa_a3f2k9x1`)
- 분산 환경에서 데이터 통합 가능
- 스키마 없이도 데이터 추가 가능 (유연성)

**Turtle 문법** (kg2에서 사용):
```turtle
@prefix paper: <https://kg.corca.ai/paper#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

paper:pa_r1s2t3u4 a paper:Paper ;
    rdfs:label "Foundations of Example Research" ;
    paper:year 2023 ;
    paper:doi "10.1234/example.2023.001" ;
    paper:primaryAuthor paper:au_a1b2c3d4 .
```

### OWL (Web Ontology Language)

**정의**: RDF 위에서 동작하는 온톨로지 언어. 클래스/프로퍼티 정의와 논리적 추론을 지원한다.

**kg2에서 사용하는 주요 기능**:

| OWL 기능 | 설명 | kg2 적용 예시 |
|---------|------|-------------|
| `FunctionalProperty` | 값이 최대 1개 | `doi`, `year`, `publishedIn` |
| `TransitiveProperty` | 추이적 관계 (A→B, B→C면 A→C) | `broader`, `partOf`, `extends` |
| `AsymmetricProperty` | 비대칭 (A→B면 B→A 불가) | `broader`, `extends`, `refutes` |
| `IrreflexiveProperty` | 자기참조 불가 (A→A 불가) | `cites`, `extends`, `broader` |
| `subPropertyOf` | 프로퍼티 계층 | `primaryAuthor`는 `author`의 하위 프로퍼티 |
| `AllDisjointClasses` | 클래스 간 배타성 | Paper, Author, Claim, Concept, Venue는 서로 겹치지 않음 |

**추론 (Reasoning)**: OWL Reasoner가 활성화되면:
- `primaryAuthor`로 연결하면 `author` 관계도 자동 추론
- `A broader B`, `B broader C`면 `A broader C` 자동 추론

**Reasoner 의존성 주의**:
- Reasoner on/off에 따라 `primaryAuthor → author`, `broader/partOf/extends` 등의 결과가 달라진다.
- 쿼리와 품질 지표 정의 시 Reasoner 사용 여부를 명시하고 고정하는 것이 안전하다.

### SPARQL

**정의**: RDF 데이터를 위한 쿼리 언어. SQL과 유사하지만 그래프 패턴 매칭에 특화.

**기본 구조**:
```sparql
PREFIX paper: <https://kg.corca.ai/paper#>

SELECT ?paper ?title WHERE {
  ?paper a paper:Paper ;
         rdfs:label ?title ;
         paper:about ?concept .
  ?concept paper:broader* paper:co_transformer .
}
LIMIT 100
```

**주요 연산자**:
- `*`: 0회 이상 반복 (예: `broader*`는 직접 또는 간접적으로 연결된 모든 상위 개념)
- `+`: 1회 이상 반복
- `OPTIONAL`: 있으면 가져오고 없어도 결과에서 제외하지 않음
- `FILTER`: 조건 필터링
- `UNION`: 여러 패턴 중 하나라도 매칭

**자주 쓰는 패턴** (query.md에서 확장):
```sparql
# partOf 계층 구성 요소 찾기
PREFIX paper: <https://kg.corca.ai/paper#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?component ?label WHERE {
  ?component paper:partOf+ paper:co_transformer ;
             rdfs:label ?label .
}
LIMIT 100
```

```sparql
# extends 체인 추적
PREFIX paper: <https://kg.corca.ai/paper#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?claim ?text ?ancestorText WHERE {
  ?claim a paper:Claim ; rdfs:label ?text ;
         paper:extends+ ?ancestor .
  ?ancestor rdfs:label ?ancestorText .
}
LIMIT 100
```

**성능 고려사항** (query.md에서):
- 항상 `LIMIT` 사용
- 추이적 프로퍼티(`broader*`, `extends+`)는 데이터 증가에 따라 비용 급증
- 추이적 깊이를 제한해 비용을 제어 (예: 1~2 hop)
  ```sparql
  { ?x paper:broader ?root } UNION { ?x paper:broader/paper:broader ?root }
  ```
- 제한적인 패턴을 WHERE 절 앞에 배치

### SHACL (Shapes Constraint Language)

**정의**: RDF 데이터 검증을 위한 W3C 표준. "데이터가 이 모양이어야 한다"는 규칙을 정의한다.

**OWL vs SHACL 역할 분담** (kg2 설계):
- **OWL**: 추론 (Functional/Transitive 등 논리적 제약)
- **SHACL**: 검증 (필수 필드, 데이터 타입, 고유성)

**kg2 SHACL 예시**:
```turtle
shapes:PaperShape a sh:NodeShape ;
    sh:targetClass paper:Paper ;
    sh:property [
        sh:path rdfs:label ;
        sh:minCount 1 ;      # 필수
        sh:maxCount 1 ;      # 1개만
        sh:datatype xsd:string ;
    ] ;
    sh:property [
        sh:path paper:primaryAuthor ;
        sh:minCount 1 ;      # 최소 1명의 주저자 필수
        sh:class paper:Author ;
    ] ;
    sh:sparql [
        sh:message "Duplicate DOI" ;
        sh:select """
            SELECT $this WHERE {
                $this paper:doi ?doi .
                ?other paper:doi ?doi .
                FILTER($this != ?other)
            }
        """ ;
    ] .
```

**검증 시점**: 데이터 삽입 시 SHACL 규칙 위반하면 HTTP 500 반환.

**삽입 전제** (curation.md 기준):
- Author/Claim/Venue/Concept는 Paper와 연결되어야 SHACL을 통과한다.
- 관련 엔티티는 Paper와 함께 한 요청으로 삽입하는 것이 안전하다.
- 새 엔티티 생성 전 외부 식별자 기반 중복 체크를 권장한다.

### 스키마 제약 요약 (schema.ttl/shacl.ttl)

- **Paper**: `rdfs:label` 1개 필수, `primaryAuthor` 최소 1명, `year` 범위(1400~2100), DOI/arXiv/Semantic Scholar ID 중복 금지
- **Author**: `rdfs:label` 1개 필수, ORCID/Semantic Scholar Author ID 중복 금지
- **Claim**: `rdfs:label` 1개 필수, claim 관계는 비대칭/비자기참조
- **Concept**: `rdfs:label` 1개 필수, `broader/partOf`는 추이적, Wikidata ID 중복 금지
- **Venue**: `rdfs:label` 1개 필수, `venueType`는 `conference/journal/preprint/workshop` 중 하나, Semantic Scholar Venue ID 중복 금지

---

## 온톨로지 설계 원칙

### kg2의 설계 철학

> "온톨로지 복잡하게 설계하다가 산으로 가는 경우를 많이 봤는데요, LLM 시대엔 특히 온톨로지를 좀 더 심플하게 설계하고 comments나 label을 LLM and/or vector search가 잘 도와줄걸로 기대하며 약간 느슨하게 설계해도 충분히 가치가 있는 것 같아요."

### 핵심 원칙

#### 1. 단순성 (Simplicity)
- 최소한의 클래스와 프로퍼티만 정의
- 복잡한 계층 구조보다 평평한 구조 선호
- LLM이 `rdfs:comment`와 `rdfs:label`을 이용해 맥락 파악

#### 2. Split by Default (분리 기본 원칙)
검증된 식별자(DOI, ORCID, arXiv ID 등) 없이는 엔티티를 별개로 취급.

**이유**: 잘못 합친 데이터를 분리하는 것보다 별개였던 데이터를 나중에 합치는 것이 훨씬 쉬움.

**적용 예시**:
- "Bae Hwidong", "Hwidong Bae", "배휘동"은 ORCID 없으면 각각 별도 Author로 생성
- 나중에 동일인 확인되면 merge

**동일성 판단 보강**:
- label 일치는 힌트일 뿐이며, 동일성 판단은 외부 식별자(DOI, ORCID, arXiv ID, Semantic Scholar ID) 기준을 우선한다.
- 삽입 전 중복 체크 쿼리를 먼저 실행한다. ([curation.md](../.claude/skills/kg2/curation.md))
- 병합은 증거 기반으로만 수행한다. ([merging.md](../.claude/skills/kg2/merging.md))
- URI 생성 규칙은 [curation.md](../.claude/skills/kg2/curation.md)를 정본으로 둔다.

#### 3. No Inverse Properties
역방향 프로퍼티(예: `claimOf`를 `hasClaim`의 역으로)를 정의하지 않음.

**이유**: SPARQL은 양방향 탐색 가능하므로 불필요한 복잡성만 증가.

```sparql
# hasClaim의 역방향도 쿼리 가능
SELECT ?paper WHERE { ?paper paper:hasClaim ?claim }
SELECT ?claim WHERE { ?paper paper:hasClaim ?claim }
```

#### 4. Claim의 원자성 (Atomic Claims)

- `extends/refutes/supports`는 비교 가능한 주장 단위를 전제로 하므로 Claim을 단문/검증 가능한 수준으로 쪼갠다.
- 조건이나 실험 설정이 다른 주장은 별도 Claim으로 분리한다.
- 모호한 요약형 Claim은 후속 연결과 평가(검증/반박)를 어렵게 만든다.

#### 5. 의미적 구분의 명확화

**paper:about vs paper:regarding vs paper:hasClaim**:
| 관계 | 방향 | 의미 |
|-----|------|------|
| `about` | Paper → Concept | 논문이 다루는 개념 |
| `hasClaim` | Paper → Claim | 논문에 포함된 주장 |
| `regarding` | Claim → Concept | 주장이 다루는 개념(선택) |

**primaryAuthor vs author**:
- `primaryAuthor`는 `author`의 하위 프로퍼티이며 Reasoner가 켜져 있으면 `author`로 자동 추론된다.
- 공동 1저자는 `primaryAuthor`, 일반 공동저자는 `author`로 연결한다.

**cites vs claim relations**:
| 관계 | 수준 | 의미 |
|-----|------|-----|
| `cites` | Paper → Paper | 서지적 참조 (참고문헌에 나열) |
| `extends` | Claim → Claim | 주장의 확장 |
| `supports` | Claim → Claim | 증거 제공 |
| `refutes` | Claim → Claim | 반박 |

**concept relations**:
| 관계 | 추이성 | 의미 | 예시 |
|-----|-------|-----|------|
| `broader` | 추이적 | 분류학적 계층 (is-a) | CNN broader 신경망 |
| `partOf` | 추이적 | 구성 관계 (has-a) | 어텐션 메커니즘 partOf 트랜스포머 |
| `dependsOn` | 비추이적 | 선행 개념 (requires) | 파인튜닝 dependsOn 사전학습 모델 |

---

## 지식 그래프 품질 지표

### 구조적 지표

#### 1. 고립 노드 (Isolated Nodes)
연결이 거의 없는 노드. 적을수록 좋다.

**kg2 쿼리** (enrichment.md):
```sparql
SELECT ?paper ?title (COUNT(DISTINCT ?conn) AS ?connections) WHERE {
  ?paper a paper:Paper ; rdfs:label ?title .
  OPTIONAL {
    { ?paper paper:hasClaim ?conn }
    UNION { ?paper paper:about ?conn }
    UNION { ?paper paper:author ?conn }
    UNION { ?paper paper:cites ?conn }
  }
}
GROUP BY ?paper ?title
HAVING (COUNT(DISTINCT ?conn) < 2)
```

#### 2. 분리된 컴포넌트 (Disconnected Components)
서로 연결되지 않은 그래프 조각들. 적을수록 좋다.

**탐지 방법**: 루트 개념 간 claim 연결이 없는 쌍 찾기
```sparql
# Isolated Field Pairs (enrichment.md)
SELECT ?root1 ?label1 ?root2 ?label2 WHERE {
  ?root1 a paper:Concept ; rdfs:label ?label1 .
  ?root2 a paper:Concept ; rdfs:label ?label2 .
  FILTER(?root1 < ?root2)
  FILTER NOT EXISTS { ?root1 paper:broader ?p1 }
  FILTER NOT EXISTS { ?root2 paper:broader ?p2 }
  # ... claim 연결 없는 경우
}
```

#### 3. 그래프 지름 (Graph Diameter)
임의의 두 노드 사이 최단 경로의 최대 길이. 작을수록 좋다.

**GraphDB 최단 경로 쿼리**:
```sparql
PREFIX path: <http://www.ontotext.com/path#>

SELECT ?pathIndex ?edgeIndex ?edge WHERE {
    VALUES (?src ?dst) { ( <paper:pa_abc> <paper:pa_xyz> ) }
    SERVICE path:search {
        [] path:findPath path:shortestPath ;
           path:sourceNode ?src ;
           path:destinationNode ?dst ;
           path:pathIndex ?pathIndex ;
           path:resultBinding ?edge .
    }
}
```

**이식성 주의**: `path:search`는 GraphDB 확장 기능이다. 다른 트리플 스토어에서는 별도 확장 기능이나 애플리케이션 레벨 경로 계산이 필요하다.

#### 4. Bridge Papers
여러 분야를 연결하는 논문. 많을수록 그래프 연결성 향상.

```sparql
SELECT ?paper ?title (COUNT(DISTINCT ?root) AS ?fieldCount) WHERE {
  ?paper a paper:Paper ; rdfs:label ?title ; paper:about ?concept .
  ?concept paper:broader* ?root .
  FILTER NOT EXISTS { ?root paper:broader ?parent }
}
GROUP BY ?paper ?title
HAVING (COUNT(DISTINCT ?root) > 1)
```

### 데이터 완결성 지표

#### 1. 식별자 커버리지
외부 식별자(DOI, ORCID, Wikidata ID)가 있는 엔티티 비율.

```sparql
SELECT ?type (COUNT(?entity) AS ?total)
       (SUM(IF(BOUND(?id), 1, 0)) AS ?withId)
WHERE {
  VALUES (?type ?class ?idProp) {
    ("Paper" paper:Paper paper:doi)
    ("Author" paper:Author paper:orcidId)
    ("Concept" paper:Concept paper:wikidataId)
  }
  ?entity a ?class .
  OPTIONAL { ?entity ?idProp ?id }
}
GROUP BY ?type
```

#### 2. 고립된 Claim
다른 claim과 연결되지 않은 주장들.

```sparql
SELECT ?claim ?label WHERE {
  ?claim a paper:Claim ; rdfs:label ?label .
  FILTER NOT EXISTS { ?claim paper:extends|paper:refutes|paper:supports ?other }
  FILTER NOT EXISTS { ?other paper:extends|paper:refutes|paper:supports ?claim }
}
```

---

## Self-Healing 전략

### 개념

시스템이 스스로 데이터 품질을 평가하고 개선하는 능력. "갈수록 가치있는 데이터를 만들어내는" 것이 목표.

### 구체적 전략

#### 1. 자동 Enrichment 발견

**kg2 접근법** (enrichment.md):
- 연결이 적은 논문 탐지 → claim, concept, citation 추가 기회
- 인용 없는 논문 탐지 → 참고문헌 수집 기회
- venue 없는 논문 탐지 → 출판 정보 수집 기회

**자동화 가능 포인트**:
```
1. 품질 지표 쿼리 실행
2. 개선 기회 목록 생성
3. 에이전트가 웹 검색으로 정보 수집
4. 수집된 정보 삽입
5. 1번으로 돌아가 반복
```

**신호 → 액션 매핑**:
| 신호 | 해석 | 우선 액션 |
|-----|------|----------|
| 고립 노드/연결 부족 | 메타데이터가 최소치만 존재 | claim/concept/citation 추가 |
| 분리된 컴포넌트 | 분야 간 연결 부족 | bridge papers 추가, 교차 claim 연결 |
| 외부 식별자 누락 | 동일성 검증/병합 어려움 | DOI/ORCID/Wikidata/Semantic Scholar ID 보강 |
| venue/citation 누락 | 출처/맥락 약함 | 출판 정보, 참고문헌 수집 |
| 고립된 claim | 의미 네트워크 약함 | extends/refutes/supports 연결 탐색 |

#### 2. 자동 Merge 후보 탐지

**kg2 접근법** (merging.md):
- 같은 이름의 Author 탐지 (같은 분야면 merge 확률 높음)
- 같은 label의 Concept 탐지
- 같은 title의 Paper 탐지

**주의**: "Be very conservative when merging. You must be absolutely sure."

**병합 절차 요약** (merging.md):
1. 외부 식별자/소속/공동저자/분야 등 증거 수집
2. canonical 엔티티 선정
3. 참조를 canonical로 옮기고 중복 엔티티 삭제
4. 확신이 없으면 병합하지 않기

#### 3. 품질 게이트

SHACL을 이용한 삽입 시점 검증:
- 필수 필드 누락 방지
- 중복 식별자 방지
- 데이터 타입 검증

### 평가 자동화 (retrospective.md에서 강조)

> "자동화된 평가 기준을 만들지 않은 게 가장 큰 이유라고 생각합니다... 다음엔 반드시 평가 기준을 먼저 만들어야겠습니다."

**제안하는 자동 평가 파이프라인**:
```
1. 핵심 품질 지표 정의 (위 지표들)
2. 정기적 측정 스크립트 작성
3. 임계값 설정 (예: 고립 노드 < 5%)
4. 임계값 위반 시 경고/자동 수정 트리거
```

**구현 도구**: [DSPy](https://dspy.ai/)를 활용하면 metric 기반 자동 최적화가 가능하다. 평가 함수를 정의하고 예시 데이터를 제공하면 추출/검증 파이프라인을 자동으로 튜닝한다. 자세한 내용은 [implementation.md](./implementation.md)를 참고.

---

## 실용적 교훈

### kg2 회고에서 배운 것

#### 성공 요인

1. **"코드는 버리고 명세서만 취하기"**: 문서가 소스코드, 생성물이 바이너리
2. **기술적 리스크 먼저 공략**: 온톨로지 설계 + 데이터 수집을 가장 먼저
3. **UI 없이 유용성 테스트**: Claude Code + SPARQL 스킬로 인터페이스 대체
4. **빠른 피드백 루프**: 실제 사용자 1명이라도 빨리 확보

#### 실패/개선 포인트

1. **데이터 품질 미흡**: 자동화된 평가 기준 없이 5일 투자
2. **응답 지연**: 서버 위치(미국-서울) 미고려로 수백 ms 추가 지연

### 해커톤 적용 권장사항

#### 온톨로지 설계

```
1. 클래스는 5개 이하로 시작
2. 필수 프로퍼티만 정의 (나머지는 rdfs:comment로)
3. TransitiveProperty는 신중하게 (쿼리 비용 증가)
4. Split by Default 원칙 유지
```

#### 데이터 파이프라인

```
1. 수집 → 검증(SHACL) → 저장 플로우 구축
2. 품질 지표 쿼리 5개 이상 미리 작성
3. Enrichment 쿼리로 개선 기회 자동 탐지
```

#### 에이전트 연동

LLM이 지식 그래프를 효과적으로 활용하려면:
- `rdfs:label`과 `rdfs:comment`를 풍부하게 작성
- SPARQL 쿼리 예시를 스킬 문서에 포함
- 트랜지티브 프로퍼티 활용법 명시

---

## 참고 자료

### 관련 문서
- [implementation.md](./implementation.md): 구현 도구 및 기술 스택 (DSPy, OpenAI Agent SDK 등)

### kg2 시스템 문서
- [SKILL.md](../.claude/skills/kg2/SKILL.md): 스킬 개요
- [query.md](../.claude/skills/kg2/query.md): SPARQL 쿼리 패턴
- [curation.md](../.claude/skills/kg2/curation.md): 데이터 수집 및 삽입
- [enrichment.md](../.claude/skills/kg2/enrichment.md): 연결성 개선 기회 탐지
- [merging.md](../.claude/skills/kg2/merging.md): 중복 엔티티 병합
- [admin.md](../.claude/skills/kg2/admin.md): 저장소 관리 (SHACL 로딩, export/clear 등)
- [data/schema.ttl](../.claude/skills/kg2/data/schema.ttl): OWL 스키마 정의
- [data/shacl.ttl](../.claude/skills/kg2/data/shacl.ttl): SHACL 검증 규칙
- [data/examples.ttl](../.claude/skills/kg2/data/examples.ttl): Turtle 예시
- [data/repo-config.ttl](../.claude/skills/kg2/data/repo-config.ttl): 저장소 설정

### 외부 자료
- [RDF 1.1 Primer](https://www.w3.org/TR/rdf11-primer/)
- [OWL 2 Primer](https://www.w3.org/TR/owl2-primer/)
- [SPARQL 1.1 Query Language](https://www.w3.org/TR/sparql11-query/)
- [SHACL Specification](https://www.w3.org/TR/shacl/)
