# DSPy Track: Next Work 정리

## Problem 1-Pager

### Background
- Clarifier/Visualizer 포함 다수 에이전트가 실제 구현되어 DSPy 최적화·평가를 바로 돌릴 수 있는 상태다.
- 기존 계획(010-dspy) 이후, 실제 실행/아티팩트/메트릭 보강이 필요하다.
- 데이터셋 규모와 메트릭 엄격도가 부족해 개선 여부 판단이 불안정하다.
- 이제 “전체 에이전트 DSPy 전환”을 포함한 통합 로드맵이 필요하다.

### Problem
- DSPy 최적화를 실제 키로 end-to-end 실행하고 결과 아티팩트를 남기는 루프가 미완성이다.
- 데이터셋 샘플 수·엣지 케이스·시각화 품질 메트릭이 충분히 엄격하지 않다.
- 실행 경로(특히 `python3 dspy_*` 단독 실행)와 설정 분리가 불명확하다.
- 일부 에이전트만 DSPy 전환되어 있어 전체 플로우 품질 최적화가 단절되어 있다.

### Goal
- 전체 에이전트를 DSPy 기반으로 전환하고, 에이전트별 평가·최적화 루프를 갖춘다.
- Clarifier/Visualizer에 대해 DSPy 최적화를 실제 키로 실행하고 결과 아티팩트를 `evals/_artifacts/`에 저장한다.
- 데이터셋을 10–20 샘플 이상으로 확장하고, Visualizer 엣지 케이스/메트릭을 강화한다.
- `dspy_integration/optimize_cli.py`에 deterministic shuffle/seed를 추가해 평가 편향을 줄인다.
- DSPy 실행 경로(모듈 호출/CLI 도움말)와 필요 시 에이전트별 설정 분리를 정리한다.
- README에 DSPy 결과 요약/리포트 템플릿 방향을 반영한다.
- DSPy 전환 작업은 에이전트별로 병렬 추진(spawn 기반 분할)한다.

### Non-goals
- 대규모 데이터셋 구축(10–20 샘플 규모를 넘는 장기 수집)
- 프로덕션급 UI/대시보드 구축
- 장기 모델 튜닝/파인튜닝

### Constraints
- 데모/테스트는 입력·출력 payload를 항상 출력한다.
- 에이전트 간 연결은 입력 payload로 전달됨을 확인한다.
- 테스트 suite는 “데모 E2E + 각 에이전트 단위 테스트” 구조를 유지한다.
- 반복 루프는 상한을 두며 env 기본 + CLI override 가능해야 한다.
- 실행/테스트는 `.env`를 기본 로드한다.
- `*_req_req.md` 등 프롬프트 로그 파일은 유지한다.
- 비용/빈도 상한은 기본 env 값(합리적 기본값)으로 설정하고 CLI로 오버라이드 가능하게 한다.

---

## 작업 범위 (Next Work)

### Immediate follow-ups
- 전 에이전트 DSPy 전환 계획 수립(병렬화 가능한 작업 묶음 정의).
- Clarifier/Visualizer DSPy 최적화를 실제 API 키로 end-to-end 실행하고 `evals/_artifacts/`에 아티팩트를 저장.
- 최적화 전/후 deltas 리뷰 후 점수 개선이 없거나 회귀 시 데이터셋/메트릭 보정.
- `dspy_integration/optimize_cli.py`에 deterministic shuffle/seed 추가.

### Quality & evaluation
- Clarifier/Visualizer 데이터셋을 10–20 샘플 이상으로 확장.
- Visualizer 엣지 케이스(빈 필드, 긴 요약, 누락 citation 등) 추가.
- Visualizer 메트릭 강화: 최소 bullet 길이, callout title 존재, URL/링크 검증 등.
- DSPy optimizer의 mock 모드 또는 dry-run 경로 회귀 테스트 추가.

### DSPy integration improvements
- 전 에이전트에 대해 DSPy Signature/Module 정의 및 기존 출력 스키마와 호환 유지.
- 에이전트별 DSPy 실행 경로(단독 실행/통합 실행)를 제공.
- `python3 dspy_*` 단독 실행 호환을 위한 wrapper 추가 또는 CLI 도움말에서 `-m` 사용을 명시.
- 필요 시 에이전트별 DSPy 설정(`DSPY_<AGENT>_MODEL` 등) 추가.
- README에 DSPy 결과 요약 또는 `docs/` 하위 리포트 템플릿 추가.

### Visualizer-specific extensions
- Visualizer 전용 DSPy dataset variant(컴포넌트 순서/prop 정규화 중심) 정의.
- 누락 required component/빈 props에 페널티를 부여하는 메트릭 추가.
- DSPy 파이프라인에 `VisualOutput` schema validation 단계 추가.

---

## 산출물 (Deliverables)
- 전 에이전트 DSPy 전환(시그니처/모듈/실행 경로/스키마 호환)
- Clarifier/Visualizer DSPy 최적화 실행 로그 및 아티팩트 (`evals/_artifacts/`)
- 확장된 데이터셋(10–20 샘플 이상) + 엣지 케이스 포함
- 강화된 Visualizer 메트릭 및 (가능 시) dry-run 회귀 테스트
- README 또는 `docs/`의 DSPy 결과 요약/리포트 템플릿

---

## 성공 기준 (Definition of Done)
- 전 에이전트가 DSPy 기반으로 실행 가능하며 기존 출력 스키마를 유지한다.
- Clarifier/Visualizer 최적화 결과가 baseline 대비 개선 또는 개선 실패 원인이 문서화된다.
- 데이터셋 확장과 메트릭 강화가 반영되어 품질 회귀를 탐지할 수 있다.
- DSPy 실행 경로가 명확하며, 단독 실행/테스트 경로가 재현 가능하다.
- 모든 루프는 상한을 가지며 env/CLI에서 제어 가능하다.

---

## 합의된 기본값 (현재 결정)
1. 병렬화: 에이전트별 DSPy 전환/데이터셋/메트릭 작업을 spawn로 병렬 수행.
2. 비용/빈도 상한: 기본 env 상한을 유지하되(예: rounds 2~3), CLI로 조정.
3. Visualizer 품질 기준: required component/props 누락, 링크 형식 위반, 최소 아이템/문자수 미달을 실패로 간주.
4. 결과 정리: README와 별도로 `docs/` 하위 리포트 템플릿에 기록.
