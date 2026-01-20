import json
from pathlib import Path
from agents import function_tool

_artifacts_dir: Path = Path("artifacts")


def set_artifacts_dir(path: Path) -> None:
    """테스트용: artifacts 디렉토리 설정"""
    global _artifacts_dir
    _artifacts_dir = path


def get_artifacts_dir() -> Path:
    return _artifacts_dir


def _rag_get_chunk_impl(
    namespace: str,
    arxiv_id: str,
    chunk_id: str
) -> str | None:
    """실제 구현 로직 (테스트 가능)"""
    papers_file = get_artifacts_dir() / f"{namespace}_papers.json"

    if not papers_file.exists():
        return None

    try:
        with open(papers_file, encoding="utf-8") as f:
            papers = json.load(f)
    except Exception:
        return None

    paper = next((p for p in papers if p.get("arxiv_id") == arxiv_id), None)
    if paper is None:
        return None

    # v1.0: abstract만 지원
    if chunk_id == "abstract":
        return paper.get("abstract")

    return paper.get("abstract")  # fallback


@function_tool
def rag_get_chunk(
    namespace: str,
    arxiv_id: str,
    chunk_id: str
) -> str | None:
    """
    특정 chunk의 원본 텍스트를 가져옵니다.
    Evidence quote가 실제로 존재하는지 검증하는 데 사용합니다.

    Args:
        namespace: RAG 저장소 네임스페이스
        arxiv_id: 논문 ID (예: "2401.00001")
        chunk_id: 청크 ID ("abstract" 또는 "chunk_N")

    Returns:
        청크 텍스트. 찾을 수 없으면 None.
    """
    return _rag_get_chunk_impl(namespace, arxiv_id, chunk_id)
