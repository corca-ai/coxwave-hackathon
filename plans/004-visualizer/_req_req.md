plans/003-clarifier/_req_req.md 는 clarifier 에이전트 구현 작업을 위해 내가 요청한 일련의 프롬프트다. 이걸 통해 plans/003-clarifier/_req.md 가 생겨서 실제로 구현이 되었다. (commit bb1f246)

이와 유사하게, 이번에는 데모 시나리오상 가장 끝에 있는 visualizer 에이전트를 추가하려고 한다. 

현재는 CLI지만 나중에 GUI로 확장할 것을 염두에 두고 있다. 그러니 visualizer라고 해서 CLI에서 시각화를 예쁘게 하는 것이 중요한 게 아니라 JSON output을 내뱉는 게 중요하다. 

이 JSON output을 이용해 그걸 실제로 GUI로 시각화하는 것은 프론트엔드의 책임이다. 나중에는 프론트엔드가 동적인 UI를 만들게 하고도 싶다. 일단은 https://github.com/vercel-labs/json-render 를 염두에 두고 있음. 어쨌든 이런 맥락을 고려하여, 향후 확장될 것을 생각하며, 네가 이해한 내 작업 스타일을 참고해서 우선 004-visualizer/_req.md 에 요구사항 문서를 만들어줘.

---

.venv에서 테스트 (python3 -m unittest tests/test_visualizer.py) 실행해보니 에러 남. 이걸 비롯해 모든 테스트가 성공하게 해줘. fixture도 테스트 실행을 통해 생긴 걸로 알아서 추가해주는 게 가능한가?

---

README visualizer 수동 테스트에서 fixture 쓰는 방법도 같이 넣어줘.