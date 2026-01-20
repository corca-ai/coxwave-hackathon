"""Local JSON file storage for Search Agent."""

import json
from pathlib import Path

from agent.search.schemas import Candidate, SearchResult


class LocalStore:
    """Search Agent용 로컬 JSON 저장소"""

    def __init__(self, artifacts_dir: Path | str = Path("artifacts")):
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def save_result(self, namespace: str, result: SearchResult) -> Path:
        """검색 결과를 JSON으로 저장"""
        path = self.artifacts_dir / f"{namespace}_search_result.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, ensure_ascii=False, indent=2)
        return path

    def load_existing_ids(self, namespace: str) -> set[str]:
        """기존 저장된 arxiv_id 목록 로드"""
        path = self.artifacts_dir / f"{namespace}_papers.json"
        if not path.exists():
            return set()
        try:
            with open(path, encoding="utf-8") as f:
                papers = json.load(f)
        except (OSError, json.JSONDecodeError):
            return set()
        return {p["arxiv_id"] for p in papers if isinstance(p, dict) and p.get("arxiv_id")}

    def append_papers(self, namespace: str, candidates: list[Candidate]) -> int:
        """신규 논문을 로컬 JSON에 누적"""
        path = self.artifacts_dir / f"{namespace}_papers.json"
        existing: list[dict] = []
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    existing = json.load(f)
            except (OSError, json.JSONDecodeError):
                existing = []
        existing_ids = {
            p["arxiv_id"] for p in existing if isinstance(p, dict) and p.get("arxiv_id")
        }
        seen = set(existing_ids)
        new_papers: list[dict] = []
        for c in candidates:
            if c.arxiv_id in seen:
                continue
            seen.add(c.arxiv_id)
            new_papers.append(c.model_dump())
        if new_papers:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(existing + new_papers, f, ensure_ascii=False, indent=2)
        return len(new_papers)

    def count_papers(self, namespace: str) -> int:
        """저장된 논문 수 반환"""
        path = self.artifacts_dir / f"{namespace}_papers.json"
        if not path.exists():
            return 0
        try:
            with open(path, encoding="utf-8") as f:
                papers = json.load(f)
        except (OSError, json.JSONDecodeError):
            return 0
        return len(papers) if isinstance(papers, list) else 0
