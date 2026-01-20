import pytest
import json
from pathlib import Path
from agent.verify.tools.rag import rag_get_chunk, set_artifacts_dir


@pytest.fixture
def setup_papers(tmp_path):
    papers = [
        {
            "arxiv_id": "2401.00001",
            "abstract": "This is the abstract text with important findings.",
            "title": "Test Paper"
        }
    ]
    papers_file = tmp_path / "test_papers.json"
    with open(papers_file, "w") as f:
        json.dump(papers, f)

    set_artifacts_dir(tmp_path)
    return tmp_path


def test_get_chunk_abstract(setup_papers):
    # rag_get_chunk는 FunctionTool이므로 내부 함수 직접 호출
    from agent.verify.tools.rag import _rag_get_chunk_impl
    result = _rag_get_chunk_impl("test", "2401.00001", "abstract")
    assert result is not None
    assert "important findings" in result


def test_get_chunk_not_found(setup_papers):
    from agent.verify.tools.rag import _rag_get_chunk_impl
    result = _rag_get_chunk_impl("test", "9999.99999", "abstract")
    assert result is None
