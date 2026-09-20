"""Evaluate one completed P16 resident run in a separate oracle-aware process.

This process is intentionally distinct from run_provider_benchmark.py. The resident
run must already exist on disk. Only this post-run process loads evaluator oracle.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from typing import Any

from .evaluation import evaluate_with_oracle
from .io import (
    load_fixture_bundle,
    load_run_artifact,
    scenario_public_fingerprint,
)
from .provider_evaluator import ProviderOracleEvaluator
from .provider_runtime import ProviderClient, ProviderConfig


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate one completed AIOS P16 provider run."
    )
    parser.add_argument("--fixture-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--run-artifact", required=True)
    parser.add_argument(
        "--provider",
        required=True,
        choices=("openai", "anthropic", "gemini"),
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--evaluator-id", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-output-tokens", type=int, default=4096)
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

    loaded_fixture = load_fixture_bundle(args.fixture_root, args.manifest)
    scenario = loaded_fixture.scenario
    loaded_run = load_run_artifact(args.run_artifact)

    expected_fingerprint = scenario_public_fingerprint(scenario)
    if loaded_run.scenario_id != scenario.scenario_id:
        raise ValueError("resident run scenario_id does not match evaluator fixture")
    if loaded_run.scenario_version != scenario.scenario_version:
        raise ValueError(
            "resident run scenario_version does not match evaluator fixture"
        )
    if loaded_run.scenario_public_fingerprint != expected_fingerprint:
        raise ValueError(
            "resident run visible-life fingerprint does not match evaluator fixture"
        )

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
    client = ProviderClient(config)
    evaluator = ProviderOracleEvaluator(
        client,
        evaluator_id=args.evaluator_id,
    )

    launch = {
        "artifact_schema": "aios.p16.provider-evaluation-launch.v1",
        "scenario_id": scenario.scenario_id,
        "scenario_version": scenario.scenario_version,
        "scenario_public_fingerprint": expected_fingerprint,
        "resident_model_id": loaded_run.model_id,
        "resident_run_artifact": str(
            Path(args.run_artifact).expanduser().resolve()
        ),
        "evaluator_id": args.evaluator_id,
        "evaluator_provider": config.provider,
        "evaluator_model": config.model,
        "evaluator_config_fingerprint": config.config_fingerprint,
        "oracle_loaded": True,
    }
    _write_json(output_dir / "evaluation_launch.json", launch)

    try:
        report = evaluate_with_oracle(
            scenario=scenario,
            run=loaded_run.run,
            evaluator_provenance=evaluator.provenance,
            handler=evaluator,
        )
        payload = {
            **launch,
            "report": asdict(report),
            "provider_request_provenance": (
                evaluator.provider_provenance_snapshot()
            ),
        }
        path = output_dir / "evaluation.json"
        _write_json(path, payload)
        return path
    except Exception as exc:
        _write_json(
            output_dir / "evaluation_failure.json",
            {
                **launch,
                "error_type": type(exc).__name__,
                "error_message": str(exc)[:4000],
                "provider_request_provenance": (
                    evaluator.provider_provenance_snapshot()
                ),
            },
        )
        raise


def main() -> int:
    args = _parser().parse_args()
    try:
        path = run(args)
    except Exception as exc:
        print(
            f"P16 provider evaluation failed: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1
    print(str(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
