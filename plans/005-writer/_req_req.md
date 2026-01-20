plans/003-clarifier/_req_req.md 는 clarifier 에이전트 구현 작업을 위해 내가 요청한 일련의 프롬프트다. 이걸 통해 plans/003-clarifier/_req.md 가 생겨서 실제로 구현이 되었다. (commit bb1f246)

마찬가지로 004-visualizer는 3c18311 에서 구현이 되었다.

이와 유사하게, 이번에는 visualizer와 연결된 writer 에이전트를 추가하려고 한다. 관련된 문서를 모두 꼼꼼히 읽고, 네가 이해한 내 작업 스타일을 참고해서 우선 005-writer/_req.md 에 요구사항 문서를 만들어줘.

---

네 가정이 옳다. _req.md 에 적절히 업데이트 후 구현 진행.

---

테스트 다 돌려보고 수정할 거 수정해줘.

---

code-review 하고, 필요한 부분 (README 포함해서) 모두 적절히 수정해줘.

---

code-review.md 에, "리뷰해서 코드 수정 후에는 항상 전체 테스트를 모두 돌린 다음 재확인"하자는 얘기를 추가해야겠다.

그리고 git worktree라서 .env 가 복사되지 않았었음. git worktree 관련 내용을 추가하고, 그 외에도 update-agents-md.md 참고해서 추가할 걸 추가하자. 

한편, AGENTS.md 가 너무 비대해지는 건 경계한다. 압축할 거 압축하고, 너무 자명한 건 빼는 걸 검토해보자.

---

writer -> visualizer 연결을 수동 테스트하고 싶은데 가능한가?

-> 그냥 데모 직접 돌리는 것으로. `python3 main.py --query "Investigate RAG and hallucination in legal QA"`
