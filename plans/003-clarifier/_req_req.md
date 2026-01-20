이제 실제로 OpenAI Python AGENTS SDK로 동작하는 clarifer 에이전 트를 실제로 추가해서 데모에 연결하려고 한다. 네가 이해한 내 작업 스타일을 참고해서 우선 003-clarifier/_req.md 에 요구사항 문서를 만들어줘.

---

좋은데, 꼭 전체 시나리오로만 하는 게 아니라 clarifier 에이전트를 독립적으로도 테스 트하고 싶다. (즉 별도 파일 겸 에이전트로도 가치가 있음) 그리고 전체 시나리오의 success criteria뿐 아니라 clarifier를 비롯한 각 에이전트가 모두 자기만의 success criteria를 가지고, 통과해야 한다.

---

이 문서에는 clarifier에 대한 성공 기준만 있으면 됨. 그 기준을 평가하는 자동화된 테스트도 필요. 그리고 구현 후 README를 업데이트하라는 내용도 추가. 그다음 구현 시작.

---

생각해보니 전체 데모도 자동화된 테스트를 추가하면 좋겠는데. 이것도 같이 하자. demo 폴더와 README에 기술된 success criteria도 같이 수정.

---

즉 현 시점에서는 테스트 suite = 데모에 대한 e2e 테스트 + 각 에이전트에 대한 테스트 라고 보면 될 것 같다.

---

.env 에는 내가 OPENAI_API_KEY 넣어뒀어.

---

_req_req.md 는 내가 일부러 넣어둔 것이다. 앞으로도 이렇게 프롬프트 전체를 기록할 예정.

---

네가 직접 모두 테스트해보고, 관찰되는 문제도 수정해줘.

---

앞으로 내가 새로 직접 만드는 파일들은 모두 내 의도에 대한 것임을 기억해.

---

자동화 테스트 돌려봤더니 통과하긴 하는데, 왜 통과하는지 모르겠다. observability를 추가해줘. 그리고 자동화 테스트 말고 직접 테스트하는 방법도 READEM에 업데이트.

---

직접 해보니 몇 가지 의문이 있다. 네 의견이 궁금하다.
- 자동화 테스트: observability가 부족. 어떤 쿼리가 들어가서 어떻게 됐는지 안 보임. 수동 테스트처럼 보여야 하지 않을까?
- clarifier 동작: 나는 ambiguity가 충분히 해소되지 않았으면 계속해서 루프를 돌기를 기대했는데 현재 그렇게 되어 있는가? (아닌 것 같다)
- 데모에서 clarifier 와 다음의 연결: clarifier의 아웃풋이 다음 에이전트로 연결되어 있는지 모르겠다. 데모 실행시에는 아닌 것으로 보였다.

---

루프 최대 횟수는 환경변수로 지정하되, CLI option으로 오버라이드 가능하도록. 전달은 JSON payload로 충분.

---

직접 실행해봤는데, plan으로 내 응답이 넘어가는지 여전히 모르겠음. mock이랑 똑같이 뜨는 것 같은데?

Plan:
{
  "plan_summary": "Define scope, gather sources, extract claims, verify, summarize.",
  "steps": [
    "Clarify scope and key terms",
    "Collect primary sources",
    "Extract claims and evidence",
    "Verify and synthesize"
  ],
  "success_criteria": [
    "At least 3 supported claims",
    "Clear limitations"
  ],
  "data_needs": [
    "Primary sources",
    "Recent surveys"
  ]
}

---

show-inputs 할 필요 없이 항상 observable하게 해줘.

---

이번 세션에서 너와 내가 작업 스타일을 맞추기 위해 많은 대화를 했는데, 내가 네게 처음부터 어떻게 얘기했으면 이런 핑퐁이 줄었을까? 를 고민중이다. 생각해보고 AGENTS.md 에 넣을 만한 내용을 정리해서 추가해줘.

---

모든 반복 루프는 적절한 상한이 있어야 한다, 그걸 env로 설정하고 cli에서 오버라이드 가능. 이것도 적절히 추가해줘.