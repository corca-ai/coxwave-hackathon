이제 모든 에이전트가 완성된 상태로 이해하고 있다. 우선 전체 repo 구조를 읽어보고, 구현과 일치하지 않는 문서 찾아서 업데이트해줘.

---

우선 제안한 대로 모든 문서를 업데이트하라.

모든 에이전트 구현이 완성됐으므로, 다음 작업을 하는 게 이번 브랜치의 목적이다.
1. CLI로 e2e 데모 전체가 의도대로 동작하는지 쭉 확인한다. 자동화 테스트 + 수동 테스트로. 
  - 내가 확신 수준을 가지려면 어떤 시나리오로 수동 테스트를 해야 하고, 하면서 뭘 관찰해야 하지?
2. 프론트엔드에서도 동일하게 모든 게 의도대로 연결되었고 동작하는지 확인해야 한다. 자동화 테스트 + 수동 테스트를 수행한다.
  - 내가 확신 수준을 가지려면 어떤 시나리오로 수동 테스트를 해야 하고, 수동 테스트를 하면서 뭘 관찰해야 하지?

이걸 하기 위한 계획을 007/check-e2e/_req.md 에 작성해줘.

---

수동 테스트는 시나리오대로 내가 하겠다. 나머지는 네가 해줘.

---

잠깐. 방금 main 브랜치를 머지했다. 변경된 것을 찾아보고 필요시 _req.md를 업데이트하라. 그다음 다시 진행.

---

그런데 왜 아직 `--mock` 으로 테스트하라고 나와있지? 모두 구현된 거 아닌가?

---

.env 는 내가 세팅해뒀음. Integration test 실행해도 됨.

---

스킵된 테스트 둘 다 key not set이네. .env가 있는데도 왜 그런거지?

---

어 그것도 하고, 방금 서버를 띄울 수 있게 됐다. 이걸 고려해서 _req.md 업데이트하고 전체 테스트 다시 수행해줘.

---

현재 프론트엔드와 서버가 잘 연결되어있는지 확인해줘. -> 연결해줘.

---

서버 연결은 잘 됐음. 이제 demo 관련된 UI들은 지저분하니까 `/demo` 로 다 빼자.

그리고 메인 URL에서, 유저가 질의하면 CLI에서처럼 대화 나누며 clarify 하는 게 되어야 하는데 이거 지금 안되는 거 맞지?

---

버튼이 "Start Clarifier" 가 아님. Clarifier는 구현 디테일이잖아. 

이것도 마찬가지.
```
Conversation flow (CLI-style)
```

원래 CLI로 만들어졌다는 걸 유저가 알 필요가 없음. 그리고 당연히 핑퐁 끝나면 다음 게 알아서 실행되어야 함.

내가 어떤 철학에 의해 얘기하는지 알겠지?

---

CORS 에러도 같이 해결.

---

이 문제도 있음.

  File "/Users/ted/codes/corca/007-check-e2e/.venv/lib/python3.13/site-packages/agents/run.py", line 867, in run_sync
    raise RuntimeError(
        "AgentRunner.run_sync() cannot be called when an event loop is already running."
    )
RuntimeError: AgentRunner.run_sync() cannot be called when an event loop is already running.