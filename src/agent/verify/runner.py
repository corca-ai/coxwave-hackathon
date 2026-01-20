import json
import click
from pathlib import Path
from agents import Runner
from agent.verify.agent import verifier_agent
from agent.verify.schemas import VerifierRequest, ExtractorResult
from agent.verify.tools.rag import set_artifacts_dir


@click.command()
@click.option("--extractor-result", required=True, help="Extractor 결과 JSON 파일 경로")
@click.option("--goal", required=True, help="연구 목표")
@click.option("--namespace", default="default", help="RAG 네임스페이스")
@click.option("--output", default=None, help="결과 저장 경로")
@click.option("--artifacts-dir", default="artifacts", help="아티팩트 디렉토리")
def verify(
    extractor_result: str,
    goal: str,
    namespace: str,
    output: str | None,
    artifacts_dir: str
):
    """Verifier Agent 실행: Extractor 결과 검증"""

    # 아티팩트 디렉토리 설정
    artifacts_path = Path(artifacts_dir)
    set_artifacts_dir(artifacts_path)

    # Extractor 결과 로드
    with open(extractor_result, encoding="utf-8") as f:
        extractor_data = json.load(f)

    request = VerifierRequest(
        goal=goal,
        namespace=namespace,
        extractor_result=ExtractorResult(**extractor_data)
    )

    click.echo(f"Verifying: {goal}")
    click.echo(f"Claims: {len(request.extractor_result.claims)}")

    # Agent 실행 - JSON을 user message로 전달
    result = Runner.run_sync(verifier_agent, request.model_dump_json())

    # 결과 출력
    output_data = result.final_output.model_dump()
    click.echo("\n=== Verification Result ===")
    click.echo(f"Quality Gate: {'PASS' if output_data['quality_gate']['passed'] else 'FAIL'}")
    click.echo(f"Evidence Coverage: {output_data['metrics']['evidence_coverage']:.2%}")
    click.echo(f"Unsupported Ratio: {output_data['metrics']['unsupported_ratio']:.2%}")
    click.echo(f"Concept Coverage: {output_data['metrics']['concept_coverage']:.2%}")
    click.echo(f"Conflicts: {output_data['metrics']['conflicts_count']}")

    if not output_data['quality_gate']['passed']:
        click.echo(f"\nReasons: {output_data['quality_gate']['reasons']}")
        click.echo(f"Next Actions: {[a['type'] for a in output_data['next_actions']]}")

    # 결과 저장
    output_path = Path(output) if output else artifacts_path / f"{namespace}_verify_result.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    click.echo(f"\nResult saved to: {output_path}")


def main():
    verify()


if __name__ == "__main__":
    main()
