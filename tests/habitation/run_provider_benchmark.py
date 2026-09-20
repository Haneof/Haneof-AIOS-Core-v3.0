"""Run one real provider-backed resident against one sealed resident-visible life.

Usage example (requires the corresponding API key environment variable):

  python -m tests.habitation.run_provider_benchmark \
    --fixture-root tests/habitation/fixtures \
    --manifest cognition_revision_v1.manifest.json \
    --provider openai \
    --model YOUR_MODEL_ID \
    --output-dir artifacts/p16/openai-cognition-revision

This runner intentionally loads only the resident stream. Evaluator oracle bytes are
never opened by this process.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import json
import sys
from typing import Any

from .current_core import CurrentCoreHabitationTarget
from .harness import HabitationRunner
from .io import (
    load_resident_fixture,
    run_artifact,
    scenario_public_fingerprint,
)
from .provider_runtime import ProviderConfig, make_provider_handlers


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one provider-backed AIOS P16 resident."
    )
    parser.add_argument("--fixture-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument(
        "--provider",
        required=True,
        choices=("openai", "anthropic", "gemini"),
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-output-tokens", type=int, default=2048)
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--endpoint", default=None)
    parser.add_argument("--api-key-env", default=None)
    parser.add_argument("--api-version", default=None)
    return parser


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )


def run(args: argparse.Namespace) -> Path:
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    loaded = load_resident_fixture(args.fixture_root, args.manifest)
    scenario = loaded.scenario
    config = ProviderConfig(
        provider=args.provider,
        model=args.model,
        endpoint=args.endpoint,
        api_key_env=args.api_key_env,
        api_version=args.api_version,
        max_output_tokens=args.max_output_tokens,
        timeout_seconds=args.timeout_seconds,
        temperature=args.temperature,
        store=True,
    )
    resident_handler, summary_handler = make_provider_handlers(config)

    target = CurrentCoreHabitationTarget(
        model_id=config.model_id,
        subject_id=scenario.subject_id,
        db_path=output_dir / "world.sqlite",
        model_handler=resident_handler,
        round_summary_handler=summary_handler,
        require_fresh=True,
    )
    runner = HabitationRunner()

    launch = {
        "artifact_schema": "aios.p16.provider-run-launch.v1",
        "scenario_id": scenario.scenario_id,
        "scenario_version": scenario.scenario_version,
        "scenario_public_fingerprint": scenario_public_fingerprint(scenario),
        "subject_id": scenario.subject_id,
        "provider": config.provider,
        "model": config.model,
        "model_id": config.model_id,
        "config_fingerprint": config.config_fingerprint,
        "manifest_name": args.manifest,
        "resident_stream": loaded.manifest.resident_stream,
        "oracle_loaded": False,
    }
    _write_json(output_dir / "launch.json", launch)

    try:
        run_result = runner.run(
            scenario=scenario,
            model_id=config.model_id,
            target=target,
        )
        artifact = run_artifact(
            scenario=scenario,
            run=run_result,
        )
        artifact["oracle_loaded"] = False
        artifact_path = output_dir / "run.json"
        _write_json(artifact_path, artifact)
        return artifact_path
    except Exception as exc:
        failure = {
            "artifact_schema": "aios.p16.provider-run-failure.v1",
            **launch,
            "error_type": type(exc).__name__,
            "error_message": str(exc)[:4000],
            "provider_provenance": resident_handler.provenance_snapshot(),
        }
        _write_json(output_dir / "failure.json", failure)
        raise


def main() -> int:
    args = _parser().parse_args()
    try:
        artifact_path = run(args)
    except Exception as exc:
        print(
            f"P16 provider run failed: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1
    print(str(artifact_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
