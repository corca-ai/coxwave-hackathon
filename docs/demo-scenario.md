# 데모 시나리오 초안
- 유저가 어떤 질의를 날린다. (타겟 유저: 진지한 연구자, 사내 변호사, 신사업 PM 등 - 즉 초반에 오래 걸려도 괜찮다고 가정)
- Clarifier 에이전트가 생각하면서 이거는 이런 뜻이냐, 이런 거 알려달라 물어봄
    - (optional) 여기서 ‘빨리 응답받기’ 누르면 바로 시작
    - 또는, 충분히 명확한 질의라고 생각하면 clarify 없이 바로 가게 할 수도 있음
- 유저가 응답
- 충분히 핑퐁하고 나면 이런 식으로 연구하겠냐고 물어봄
- 승인하면 시작
    - 여기부터는 거의 유저 개입 없지만
    - observability는 있음. 어떤 식으로 동작하고 있는지 보이고, 중간 결과 보이고 등
- 이후는 오케스트레이터가 아래를 알아서 한다.
    - 질의에 응답하기에 충분한 데이터가 있는지 Verifier가 있나?
    - 있으면 응답, 없으면 Search + Extract + Verify 루프
    - 응답할 때는 Writer가 json을 줌
    - (Optional) Visualizer가 사전에 만들어둔 컴포넌트를 알아서 조합해서 시각화해줌
- 최종 결과가 나옴

## 멀티 에이전트 구성

- Clarifier Agent
- Orchestrator: 상태 기반 라우팅, 재시도/재분배/중단 판단
    - Planner Agent: 실험 계획
- Search/Select Agent: 검색 + 초기 필터
- Extractor Agent: 구조적 추출 + 인용 근거 포함
- Verifier Agent: Claim/Evidence 평가 + Quality Gate
- Writer Agent: 리포트 합성
- Visualizer Agent: 시각화 ([json-render](https://github.com/vercel-labs/json-render)?)