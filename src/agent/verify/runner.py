import json
import os
from pathlib import Path

import click
from agents import Runner

from agent.verify.agent import verifier_agent
from agent.verify.schemas import ExtractorResult, VerifierRequest
from agent.verify.tools.rag import set_artifacts_dir
from env_loader import load_env


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
    load_env(keys=["OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_TEMPERATURE"])
    if not os.getenv("OPENAI_API_KEY"):
        raise click.ClickException("OPENAI_API_KEY is not set.")

    # 아티팩트 디렉토리 설정
    artifacts_path = Path(artifacts_dir)
    set_artifacts_dir(artifacts_path)

    # Extractor 결과 로드
    try:
        with open(extractor_result, encoding="utf-8") as f:
            extractor_data = json.load(f)
    except FileNotFoundError as exc:
        raise click.ClickException(f"Extractor result file not found: {extractor_result}") from exc
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"Extractor result must be valid JSON: {exc}") from exc
    except OSError as exc:
        raise click.ClickException(f"Failed to read extractor result: {exc}") from exc

    request = VerifierRequest(
        goal=goal,
        namespace=namespace,
        extractor_result=ExtractorResult(**extractor_data)
    )

    click.echo("Verifier input:")
    click.echo(
        json.dumps(request.model_dump(), indent=2, ensure_ascii=True)
    )
    click.echo(f"Verifying: {goal}")
    click.echo(f"Claims: {len(request.extractor_result.claims)}")

    # Agent 실행 - JSON을 user message로 전달
    result = Runner.run_sync(verifier_agent, request.model_dump_json())

    # 결과 출력
    output_data = result.final_output.model_dump()
    click.echo("Verifier output:")
    click.echo(json.dumps(output_data, indent=2, ensure_ascii=True))
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
