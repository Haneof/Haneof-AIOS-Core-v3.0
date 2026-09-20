"""Offline comparison of completed P16 evaluation artifacts.

This tool aligns findings across resident models. It intentionally does not rank,
score or choose a winning model.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .evaluation import comparison_matrix
from .evaluation_io import load_evaluation_artifact


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Align multiple completed P16 evaluation artifacts."
    )
    parser.add_argument(
        "evaluations",
        nargs="+",
        help="Two or more evaluation.json files",
    )
    parser.add_argument("--output", required=True)
    return parser


def compare(paths: list[str]) -> dict[str, Any]:
    if len(paths) < 2:
        raise ValueError("at least two evaluation artifacts are required")

    loaded = [load_evaluation_artifact(path) for path in paths]
    matrix = comparison_matrix(
        tuple(item.report for item in loaded)
    )
    return {
        "artifact_schema": "aios.p16.evaluation-comparison.v1",
        "scenario_id": matrix["scenario_id"],
        "scenario_version": matrix["scenario_version"],
        "scenario_public_fingerprint": matrix[
            "scenario_public_fingerprint"
        ],
        "evaluator_id": matrix["evaluator_id"],
        "evaluator_provenance": matrix["evaluator_provenance"],
        "source_evaluations": [
            {
                "path": str(Path(path).expanduser().resolve()),
                "resident_model_id": item.resident_model_id,
            }
            for path, item in zip(paths, loaded)
        ],
        "comparison": matrix,
    }


def main() -> int:
    args = _parser().parse_args()
    payload = compare(list(args.evaluations))
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
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
    print(str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
