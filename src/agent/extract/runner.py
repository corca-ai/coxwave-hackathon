"""CLI runner for Extractor Agent."""

import json
import click
from pathlib import Path
from agents import Runner

from agent.extract.agent import extract_agent
from agent.extract.schemas import ExtractorRequest
from agent.search.schemas import SearchResult


@click.command()
@click.option("--search-result", required=True, help="Search 결과 JSON 파일 경로")
@click.option("--goal", required=True, help="연구 목표")
@click.option("--namespace", default="default", help="RAG 네임스페이스")
@click.option("--output", default=None, help="결과 저장 경로")
def extract(search_result: str, goal: str, namespace: str, output: str | None):
    """Extractor Agent 실행"""

    with open(search_result, encoding="utf-8") as f:
        search_data = json.load(f)

    request = ExtractorRequest(
        goal=goal,
        namespace=namespace,
        search_result=SearchResult(**search_data),
    )

    click.echo(f"Extracting claims for: {goal}")
    click.echo(f"Papers: {len(request.search_result.selected_papers)}")

    result = Runner.run_sync(extract_agent, request.model_dump_json())

    output_data = result.final_output.model_dump()
    click.echo("\n=== Extractor Result ===")
    click.echo(f"Claims: {len(output_data['claims'])}")
    click.echo(f"Concepts: {len(output_data['concepts'])}")

    output_path = Path(output) if output else Path("artifacts") / f"{namespace}_extract_result.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    click.echo(f"\nResult saved to: {output_path}")


if __name__ == "__main__":
    extract()
