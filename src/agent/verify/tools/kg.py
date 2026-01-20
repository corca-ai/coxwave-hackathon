from agents import function_tool


def _kg_query_impl(sparql: str) -> list[dict]:
    """실제 구현 로직 (테스트 가능)"""
    # TODO: GraphDB 연동 시 활성화
    return []


@function_tool
def kg_query(sparql: str) -> list[dict]:
    """
    GraphDB에 SPARQL 쿼리를 실행합니다.
    v1.0: 모킹 - 빈 리스트 반환.

    Args:
        sparql: SPARQL 쿼리 문자열

    Returns:
        쿼리 결과 rows (v1.0에서는 빈 리스트)
    """
    return _kg_query_impl(sparql)
