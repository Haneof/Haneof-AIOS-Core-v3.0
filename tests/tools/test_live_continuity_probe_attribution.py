"""Failure attribution decides who has to act, so it must not blur the line.

The local model is a test rig. When it cannot fill in a capability schema, the
right response is a stronger model — not a looser kernel. This module keeps that
judgement mechanical instead of a matter of mood.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_TOOL = Path(__file__).resolve().parents[2] / "tools" / "live_continuity_probe.py"


def _load_probe():
    spec = importlib.util.spec_from_file_location("live_continuity_probe_under_test", _TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


probe = _load_probe()


def test_bad_arguments_are_the_model_side() -> None:
    buckets = probe._attribute_failures(
        [
            {"name": "commit_ai_world_claim", "ok": False, "error_code": "CAPABILITY_ARGUMENT_ERROR"},
            {"name": "commit_ai_world_claim", "ok": False, "error_code": "CAPABILITY_ARGUMENT_ERROR"},
        ]
    )
    assert len(buckets["model_side"]) == 2
    assert buckets["kernel_side"] == []


def test_a_raise_inside_the_kernel_is_the_kernel_side() -> None:
    buckets = probe._attribute_failures(
        [{"name": "commit_ai_world_claim", "ok": False, "error_code": "CAPABILITY_EXECUTION_ERROR"}]
    )
    assert len(buckets["kernel_side"]) == 1
    assert buckets["model_side"] == []


def test_successes_are_not_counted_as_failures() -> None:
    buckets = probe._attribute_failures(
        [
            {"name": "search_world", "ok": True, "error_code": None},
            {"name": "commit_ai_world_claim", "ok": False, "error_code": "CAPABILITY_ARGUMENT_ERROR"},
        ]
    )
    assert len(buckets["succeeded"]) == 1
    assert len(buckets["model_side"]) == 1
    assert buckets["kernel_side"] == []


def test_mixed_failures_land_in_both_buckets() -> None:
    buckets = probe._attribute_failures(
        [
            {"name": "a", "ok": False, "error_code": "CAPABILITY_ARGUMENT_ERROR"},
            {"name": "b", "ok": False, "error_code": "CAPABILITY_EXECUTION_ERROR"},
        ]
    )
    assert [o["name"] for o in buckets["model_side"]] == ["a"]
    assert [o["name"] for o in buckets["kernel_side"]] == ["b"]


class _Result:
    def __init__(self, name: str, ok: bool, code: str | None = None, message: str = "") -> None:
        self.name = name
        self.ok = ok
        self.error_code = code
        self.error_message = message


def test_cumulative_history_is_not_double_counted() -> None:
    """Each round re-delivers every earlier result; counting them again inflates the verdict."""

    first = _Result("commit_ai_world_claim", False, "CAPABILITY_ARGUMENT_ERROR", "bad")
    second = _Result("commit_ai_world_claim", False, "CAPABILITY_ARGUMENT_ERROR", "bad again")

    # Round 1: history has one result.
    assert len(probe._new_outcomes((first,), 0)) == 1
    # Round 2: history is cumulative — only the new one counts.
    assert len(probe._new_outcomes((first, second), 1)) == 1
    # Round 3: nothing new.
    assert probe._new_outcomes((first, second), 2) == []


def test_outcome_shape_matches_what_attribution_reads() -> None:
    recorded = probe._new_outcomes((_Result("x", False, "CAPABILITY_EXECUTION_ERROR", "boom"),), 0)
    assert recorded == [
        {
            "name": "x",
            "ok": False,
            "error_code": "CAPABILITY_EXECUTION_ERROR",
            "error_message": "boom",
        }
    ]
