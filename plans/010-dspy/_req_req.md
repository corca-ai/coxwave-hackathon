일단 전체 repo 구조를 파악하라.

전반적으로 https://dspy.ai/ 를 도입하여 각 에이전트 프롬프트가 의도대로 동작하는지 테스트하고, 개선하는 루프를 (어드민?) 만들고 싶다. https://platform.openai.com/docs/guides/evals 이 문서도 좋아 보인다.

그런데 내가 dspy도, eval도 제대로 안 해봤다. 어떻게 하면 좋을지 계획을 문서로 만들어서 010-dspy/_req.md 에 작성해줘.

---

문서는 좋다. 다른 세션에서 다른 작업이 진행 중이니 git worktree로 010-dspy 폴더를 포함해서 집어넣고 작업 진행해줘.

---

1, 2. Do everything. 알아서 잘 하겠지만, 향후 다른 에이전트로 확장하기 쉬운 구조로 해줘

---

적절히 단위 나눠서 커밋하고, 유닛 테스트도 추가 후 커밋하고, phase 2 시작해줘

---

잠시만. main에 visualizer 에이전트 작업한 브랜치가 머지되었다. 내가 worktree 잘 몰라서, 이제 worktree 안 쓰는 것처럼 변경하고, main 기준으로 rebase하고 싶다. 해줘.

---

해당 worktree는 삭제하고 일반적인 브랜치로 온 거 맞나? (외부 git app인 fork에서 에러가 나고 있음) 워크트리 포함해서, 현재 이 브랜치의 구현 상황이 어떤 상태인지 알려줘.

참고로 에러는 Unexpected error:
read head in '/Users/ted/codes/corca/coxwave-hackathon/.git/worktrees/coxwave-hackathon-010-dspy'
No such file or directory (os error 2)

---

dspy는 requirements.txt 에 없는거야? dev dependencies 같은 걸로라도 추가해야 하는 거 아닌가? -> dev로 추가

---

phase 2에서 어떤 작업이 남았지? visualizer에 대해서도 추가됐으면 좋겠는데.