"""Gate B — frozen Core contract tests.

Real frozen Core classes are constructed directly; nothing is guessed.

B1 ``RuntimeSnapshot`` with an empty ``capability_history``
B2 successful ``CapabilityResult(ok=True, data=...)``
B3 failed ``CapabilityResult(ok=False, error_code=..., error_message=...)``
B4 multiple ``CapabilityResult`` entries with different name/call_id/data/error
B5 no nonexistent field is ever referenced (``arguments``, ``result``, ``error``,
   ``duration_seconds``), and the runner serializer raises no ``AttributeError``
B6 the frozen field surface is exactly the six legal fields
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import json
import pathlib

import pytest

from aios_core.runtime.capabilities import CapabilityResult
from aios_core.runtime.cognitive_runtime import RuntimeSnapshot

from aios_exchange import verify
from aios_exchange.schema import (
    CAPABILITY_RESULT_EXPECTED_FIELDS,
    CAPABILITY_RESULT_FORBIDDEN_FIELDS,
    SchemaContractError,
    assert_capability_result_contract,
    capability_result_field_names,
    capability_result_from_mapping,
    capability_result_to_mapping,
    model_directive_to_mapping,
    parse_model_directive,
    serialize_runtime_snapshot,
)
from synthetic.gate_env import PACKAGE_ROOT, evidence_dir


def build_snapshot(history: tuple[CapabilityResult, ...]) -> RuntimeSnapshot:
    return RuntimeSnapshot(
        user_input="SYNTHETIC operator-prep contract probe",
        wake_reason="synthetic_operator_prep",
        cockpit={"synthetic": True, "note": "operator-prep synthetic cockpit"},
        capability_catalog=({"name": "synthetic_probe", "kind": "read"},),
        capability_history=history,
        round_index=0,
        remaining_tool_rounds=1,
    )


def test_b1_runtime_snapshot_with_empty_capability_history() -> None:
    snapshot = build_snapshot(())
    assert snapshot.capability_history == ()
    serialized = serialize_runtime_snapshot(snapshot)
    assert serialized["capability_history"] == []
    assert serialized["serialized_fields"] == [
        "user_input",
        "wake_reason",
        "cockpit",
        "capability_catalog",
        "capability_history",
        "round_index",
        "remaining_tool_rounds",
    ]
    assert json.loads(json.dumps(serialized)) == serialized

    # Contract probe: the frozen type has no defaults, so capability_history
    # alone is not a legal construction. Recorded, not guessed.
    signature = inspect.signature(RuntimeSnapshot)
    with pytest.raises(TypeError):
        RuntimeSnapshot(capability_history=())  # type: ignore[call-arg]
    evidence = evidence_dir("gate_b")
    (evidence / "runtime_snapshot_signature.json").write_text(
        json.dumps(
            {
                "signature": str(signature),
                "fields": [field.name for field in dataclasses.fields(RuntimeSnapshot)],
                "capability_history_alone_raises_type_error": True,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_b2_successful_capability_result_serializes() -> None:
    result = CapabilityResult(
        name="synthetic_probe",
        ok=True,
        data={"synthetic": "value", "items": [1, 2, 3]},
        call_id="synthetic-call-0001",
    )
    mapping = capability_result_to_mapping(result)
    assert set(mapping) == set(CAPABILITY_RESULT_EXPECTED_FIELDS)
    assert mapping["ok"] is True
    assert mapping["data"] == {"synthetic": "value", "items": [1, 2, 3]}
    assert mapping["error_code"] is None and mapping["error_message"] is None
    assert mapping["call_id"] == "synthetic-call-0001"
    roundtrip = capability_result_from_mapping(mapping)
    assert roundtrip == result


def test_b3_failed_capability_result_serializes() -> None:
    result = CapabilityResult(
        name="synthetic_probe_failure",
        ok=False,
        error_code="SYNTHETIC_ERROR_CODE",
        error_message="synthetic failure message",
        call_id="synthetic-call-0002",
    )
    mapping = capability_result_to_mapping(result)
    assert set(mapping) == set(CAPABILITY_RESULT_EXPECTED_FIELDS)
    assert mapping["ok"] is False and mapping["data"] is None
    assert mapping["error_code"] == "SYNTHETIC_ERROR_CODE"
    assert mapping["error_message"] == "synthetic failure message"
    assert capability_result_from_mapping(mapping) == result


def test_b4_multiple_capability_results_distinct_fields() -> None:
    results = (
        CapabilityResult(name="alpha", ok=True, data={"v": 1}, call_id="call-a"),
        CapabilityResult(
            name="beta",
            ok=False,
            error_code="SYNTHETIC_BETA_ERROR",
            error_message="beta failed",
            call_id="call-b",
        ),
        CapabilityResult(name="gamma", ok=True, data=[1, 2, 3], call_id=None),
        CapabilityResult(name="delta", ok=False, error_code="DELTA", error_message="d", call_id="call-d"),
    )
    snapshot = build_snapshot(results)
    serialized = serialize_runtime_snapshot(snapshot)
    history = serialized["capability_history"]
    assert len(history) == 4
    for entry in history:
        assert set(entry) == set(CAPABILITY_RESULT_EXPECTED_FIELDS)
        for forbidden in CAPABILITY_RESULT_FORBIDDEN_FIELDS:
            assert forbidden not in entry
    assert [entry["name"] for entry in history] == ["alpha", "beta", "gamma", "delta"]
    assert [entry["call_id"] for entry in history] == ["call-a", "call-b", None, "call-d"]
    assert history[1]["error_code"] == "SYNTHETIC_BETA_ERROR"
    assert history[3]["ok"] is False
    assert json.loads(json.dumps(serialized)) == serialized


def test_b5_no_nonexistent_fields_are_referenced() -> None:
    probe = CapabilityResult(name="probe", ok=True, data=None)
    for name in CAPABILITY_RESULT_EXPECTED_FIELDS:
        assert hasattr(probe, name)
    for name in CAPABILITY_RESULT_FORBIDDEN_FIELDS:
        assert not hasattr(probe, name), f"{name} unexpectedly exists on CapabilityResult"

    payload = {name: getattr(probe, name) for name in CAPABILITY_RESULT_EXPECTED_FIELDS}
    for forbidden in CAPABILITY_RESULT_FORBIDDEN_FIELDS:
        broken = dict(payload)
        broken[forbidden] = "synthetic"
        with pytest.raises(SchemaContractError):
            capability_result_from_mapping(broken)

    # No *code* in the run package may access a field that does not exist on the
    # frozen type. Attribute nodes are inspected AST-wise, so documentation that
    # lists the forbidden names is not mistaken for a reference.
    offenders: list[str] = []
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in {"duration_seconds", "result"}:
                offenders.append(f"{path.name}:{node.lineno}: .{node.attr}")
            if isinstance(node, ast.Attribute) and node.attr == "error":
                offenders.append(f"{path.name}:{node.lineno}: .error")
    assert offenders == [], offenders


def test_b6_frozen_capability_result_surface_is_exactly_six_fields() -> None:
    report = assert_capability_result_contract()
    assert tuple(report["fields"]) == CAPABILITY_RESULT_EXPECTED_FIELDS
    assert tuple(capability_result_field_names()) == CAPABILITY_RESULT_EXPECTED_FIELDS
    assert verify.capability_result_surface_report()["legal_fields"] == list(CAPABILITY_RESULT_EXPECTED_FIELDS)
    evidence = evidence_dir("gate_b")
    (evidence / "capability_result_surface.json").write_text(
        json.dumps(verify.capability_result_surface_report(), indent=2) + "\n", encoding="utf-8"
    )


def test_b7_runner_serializer_round_trips_real_directive() -> None:
    directive = parse_model_directive(
        {
            "response_version": 1,
            "request_id": "req-0001-model_directive-synthetic1",
            "request_sha256": "0" * 64,
            "authored_by": "EXTERNAL_CURRENT_RESIDENT_SESSION",
            "directive": {
                "capability_calls": [
                    {"name": "synthetic_probe", "arguments": {"a": 1}, "call_id": "synthetic-call-0009"}
                ],
                "response": None,
                "silence": False,
            },
        }
    )
    assert directive.capability_calls[0].name == "synthetic_probe"
    assert dict(directive.capability_calls[0].arguments) == {"a": 1}
    assert directive.response is None and directive.silence is False

    # Round trip through the projection the Resident would author.
    projected = model_directive_to_mapping(directive)
    assert projected["capability_calls"][0]["name"] == "synthetic_probe"
    reparsed = parse_model_directive(
        {
            "response_version": 1,
            "request_id": "req-0001-model_directive-synthetic1",
            "request_sha256": "0" * 64,
            "authored_by": "EXTERNAL_CURRENT_RESIDENT_SESSION",
            "directive": projected,
        }
    )
    assert reparsed == directive
