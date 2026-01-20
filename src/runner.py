"""CLI runner for Search Agent."""

import click
from pathlib import Path
from agents import Runner
from agent.search.agent import search_agent
from agent.search.schemas import SearchRequest, Constraints
from agent.search.tools.rag import set_artifacts_dir
from agent.search.clients.local_store import LocalStore


@click.command()
@click.option("--goal", required=True, help="연구 목표")
@click.option("--namespace", default="default", help="저장소 네임스페이스")
@click.option("--target-docs", default=12, help="목표 신규 문서 수")
@click.option("--artifacts-dir", default="artifacts", help="아티팩트 저장 디렉토리")
def search(goal: str, namespace: str, target_docs: int, artifacts_dir: str):
    """Search Agent 실행"""
    artifacts_path = Path(artifacts_dir)
    set_artifacts_dir(artifacts_path)

    request = SearchRequest(
        goal=goal,
        namespace=namespace,
        constraints=Constraints(target_new_docs=target_docs),
    )

    click.echo(f"Searching: {goal}")
    result = Runner.run_sync(search_agent, request.model_dump_json())

    output = result.final_output.model_dump()
    click.echo(f"Found: {len(output['selected_papers'])} papers")
    click.echo(f"New: {output['ingest_summary']['new_docs_added']}")

    store = LocalStore(artifacts_dir=artifacts_path)
    path = store.save_result(namespace, result.final_output)
    click.echo(f"Saved: {path}")


if __name__ == "__main__":
    search()
