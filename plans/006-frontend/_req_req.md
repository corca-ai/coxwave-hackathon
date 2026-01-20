plans/003-clarifier/_req_req.md 는 clarifier 에이전트 구현 작업을 위해 내가 요청한 일련의 프롬프트다. 이걸 통해 plans/003-clarifier/_req.md 가 생겨서 실제로 구현이 되었다. (commit bb1f246)

마찬가지로 004-visualizer는 3c18311 에서 구현이 되었다.

지금까지는 CLI로만 구성되었었는데, 프론트엔드를 추가하려고 한다. 006-frontend/sample-<1~4>.png가 이전에 구현해본 버전의 스크린샷들이다.

현재 프론트엔드 구현에서 신경쓰는 것들은 다음과 같다.
- 결과물에 연결된 자료들을 그래프로 시각화
- 에이전트가 움직이는 과정도 그래프로 시각화 (observability, trace)
- streaming 응답이 잘 보여야 함

vercel-react-best-pratices skill을 이용해서 구현할 것인데, 네가 이해한 내 작업 스타일을 참고해서 우선 _req.md 에 요구사항 문서를 만들어줘.

---

Next.js App Router. 그래프 라이브러리는 가장 적절한 걸로 (vercel-react-best-pratices 참고). UI는 일단 로컬 전용(데모 보여주기가 목적)이나 Vercel 배포 고려(동작하는 URL을 전달하면 가산점). 로그 스키마 저장소는 가장 적합한 장소에 알아서. -> _req.md 업데이트해줘.