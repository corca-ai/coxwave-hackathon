# Clarifier Agent (OpenAI Agents SDK) 요구사항

## 배경
- 현재 데모는 `main.py`에서 Protocol 기반 인터페이스만 가정하고 있으며, 실제 에이전트 구현은 비어 있다.
- 첫 번째 실제 구현 대상으로 Clarifier 에이전트를 OpenAI Agents SDK로 연결하려고 한다.
- 기존 작업 방식은 “가장 미니멀하게 한 스텝씩” 진행하는 것이다.

## 목표
- OpenAI Agents SDK로 동작하는 Clarifier 에이전트를 추가하고 데모(`main.py`)에 연결한다.
- Clarifier는 구조화된 출력으로 데모 흐름에 바로 사용 가능해야 한다.
- Clarifier를 전체 시나리오와 독립적으로도 실행/검증할 수 있어야 한다.

## 범위 (Requirements)
1. **Clarifier 에이전트 구현**
   - OpenAI Agents SDK를 사용해 LLM 기반 Clarifier를 구현한다.
   - 출력은 `main.py`의 `ClarifyOutput`와 호환되어야 한다.
   - 명확하지 않은 질의에 대해 최대 3개의 clarifying question을 생성한다.
   - 항상 `interpreted_query`와 `assumptions`를 포함한다.

2. **데모와의 연결**
   - `main.py`의 `DemoAgents` 구조에 Clarifier가 연결되어야 한다.
   - `agents_impl.py`에 `build_agents()`를 추가해 Clarifier를 반환하도록 한다.
   - 나머지 에이전트는 아직 mock 또는 기존 placeholder로 유지한다.

3. **단독 실행 (독립 테스트)**
   - Clarifier만 실행 가능한 별도 엔트리/파일을 제공한다.
   - 입력 1개 → 구조화된 출력 1개를 반환하는 단순 CLI 형태면 충분하다.

4. **자동화된 테스트**
   - Clarifier 성공 기준을 검증하는 자동화 테스트를 추가한다.
   - 테스트는 로컬 실행 기준으로 실패/성공이 명확히 구분되어야 한다.
   - 현 시점 테스트 suite는 “데모 E2E + 각 에이전트 단위 테스트”로 구성한다.

5. **오류/경계 처리**
   - API 키가 없을 경우 에러 메시지를 명확히 출력한다.
   - Clarifier 출력이 파싱 실패 시 안전하게 실패 원인을 노출한다.

6. **문서 업데이트**
   - 구현 완료 후 README에 실행 방법과 테스트 방법을 반영한다.

## 비목표 (Non-goals)
- 다른 에이전트(Search/Extractor/Verifier/Writer/Visualizer) 구현
- Search/Extract/Verify 루프 개선
- DSPy 연동, 지식 그래프 연동
- UI/시각화 개선

## 제약 (Constraints)
- OpenAI Agents SDK (Python) 사용
- 최소한의 코드 변경으로 데모에 붙이는 것을 우선
- 기존 데모 흐름(Clarify → Plan → Search → Extract → Verify → Write → Visualize)을 유지

## 성공 기준
- `python3 main.py --query "..."` 실행 시 Clarifier 단계에서 실제 LLM 호출이 수행됨
- Clarifier 출력이 `ClarifyOutput` 구조로 파싱되어 다음 단계로 전달됨
- 모호한 질의(예: 3~4단어 수준)에 대해 clarifying question이 1개 이상 생성됨
- Clarifier 단독 실행에서도 동일한 구조화 출력이 생성됨
- 자동화 테스트가 통과함

## 참고
- `openai-agents-python-docs/quickstart.md`
- `openai-agents-python-docs/agents.md`
- `openai-agents-python-docs/running_agents.md`
