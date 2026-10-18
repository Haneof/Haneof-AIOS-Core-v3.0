"""Frozen-Core contract binding and strict (de)serialization.

Types are imported from the frozen RC; nothing here is guessed or redefined.
The module fails closed whenever the frozen contract is not exactly what the
harness was frozen against.

``CapabilityResult`` legal fields are read from the class itself and must be
exactly ``name, ok, data, error_code, error_message, call_id``. Attributes that
have never existed on the frozen type (``arguments``, ``result``, ``error``,
``duration_seconds``) must never be referenced and are rejected as input keys.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Mapping

from aios_core.runtime.capabilities import (
    CapabilityCall,
    CapabilityResult,
)
from aios_core.runtime.cognitive_runtime import (
    ModelCallProvenance,
    ModelDirective,
    ModelUsage,
    RuntimeSnapshot,
)

__all__ = [
    "CAPABILITY_RESULT_EXPECTED_FIELDS",
    "CAPABILITY_RESULT_FORBIDDEN_FIELDS",
    "MODEL_DIRECTIVE_ALLOWED_KEYS",
    "MODEL_USAGE_ALLOWED_KEYS",
    "MODEL_PROVENANCE_ALLOWED_KEYS",
    "RESPONSE_ENVELOPE_KEYS",
    "SchemaContractError",
    "assert_capability_result_contract",
    "capability_result_field_names",
    "capability_result_to_mapping",
    "capability_result_from_mapping",
    "runtime_snapshot_field_names",
    "serialize_runtime_snapshot",
    "response_envelope_contract",
    "capability_history_contract",
    "parse_response_envelope",
    "parse_model_directive",
    "model_directive_to_mapping",
]

CAPABILITY_RESULT_EXPECTED_FIELDS: tuple[str, ...] = (
    "name",
    "ok",
    "data",
    "error_code",
    "error_message",
    "call_id",
)

#: Attribute names from the historical runner defect. They are not part of the
#: frozen type and must never be read or accepted as input keys.
CAPABILITY_RESULT_FORBIDDEN_FIELDS: tuple[str, ...] = (
    "arguments",
    "result",
    "error",
    "duration_seconds",
)

MODEL_DIRECTIVE_ALLOWED_KEYS: tuple[str, ...] = (
    "capability_calls",
    "response",
    "silence",
    "usage",
    "provenance",
)

MODEL_USAGE_ALLOWED_KEYS: tuple[str, ...] = (
    "total_tokens",
    "input_tokens",
    "output_tokens",
    "provider",
    "model",
    "request_id",
)

MODEL_PROVENANCE_ALLOWED_KEYS: tuple[str, ...] = ("provider", "model", "request_id")

RESPONSE_ENVELOPE_KEYS: tuple[str, ...] = (
    "response_version",
    "request_id",
    "request_sha256",
    "authored_by",
    "directive",
)

RESPONSE_VERSION = 1
REQUEST_VERSION = 1


class SchemaContractError(RuntimeError):
    """A payload or a frozen-Core type violates the frozen contract."""


# ---------------------------------------------------------------------------
# CapabilityResult contract
# ---------------------------------------------------------------------------
def capability_result_field_names() -> tuple[str, ...]:
    """Legal field names, read from the frozen class (never guessed)."""

    return tuple(field.name for field in dataclasses.fields(CapabilityResult))


def assert_capability_result_contract() -> dict[str, Any]:
    """Fail closed unless the frozen ``CapabilityResult`` is exactly as frozen."""

    observed = capability_result_field_names()
    if observed != CAPABILITY_RESULT_EXPECTED_FIELDS:
        raise SchemaContractError(
            "frozen CapabilityResult field drift: "
            f"expected {CAPABILITY_RESULT_EXPECTED_FIELDS!r} observed {observed!r}"
        )
    present_forbidden = [name for name in CAPABILITY_RESULT_FORBIDDEN_FIELDS if hasattr(CapabilityResult, name)]
    if present_forbidden:
        raise SchemaContractError(
            f"CapabilityResult unexpectedly exposes {present_forbidden!r}"
        )
    probe = CapabilityResult(name="contract-probe", ok=True, data=None)
    for name in CAPABILITY_RESULT_EXPECTED_FIELDS:
        getattr(probe, name)
    for name in CAPABILITY_RESULT_FORBIDDEN_FIELDS:
        if hasattr(probe, name):
            raise SchemaContractError(f"probe result exposes forbidden attribute {name!r}")
    return {
        "fields": list(observed),
        "forbidden_fields_absent": list(CAPABILITY_RESULT_FORBIDDEN_FIELDS),
        "signature": str(dataclasses.fields(CapabilityResult)),
    }


def capability_result_to_mapping(result: CapabilityResult) -> dict[str, Any]:
    """Project a real result to its six legal fields (unknown fields impossible)."""

    if not isinstance(result, CapabilityResult):
        raise SchemaContractError(
            f"expected CapabilityResult, got {type(result).__name__}"
        )
    assert_capability_result_contract()
    return {name: getattr(result, name) for name in CAPABILITY_RESULT_EXPECTED_FIELDS}


def capability_result_from_mapping(mapping: Mapping[str, Any]) -> CapabilityResult:
    """Build a real result from a mapping containing only legal fields."""

    if not isinstance(mapping, Mapping):
        raise SchemaContractError("capability result payload must be a mapping")
    keys = set(mapping)
    unknown = keys - set(CAPABILITY_RESULT_EXPECTED_FIELDS)
    if unknown:
        raise SchemaContractError(f"unknown capability result fields: {sorted(unknown)}")
    missing = set(CAPABILITY_RESULT_EXPECTED_FIELDS) - keys
    if missing:
        raise SchemaContractError(f"missing capability result fields: {sorted(missing)}")
    if not isinstance(mapping["name"], str) or not mapping["name"].strip():
        raise SchemaContractError("capability result name must be non-blank text")
    if not isinstance(mapping["ok"], bool):
        raise SchemaContractError("capability result ok must be a boolean")
    return CapabilityResult(
        name=mapping["name"],
        ok=mapping["ok"],
        data=mapping["data"],
        error_code=mapping["error_code"],
        error_message=mapping["error_message"],
        call_id=mapping["call_id"],
    )


def capability_history_contract() -> dict[str, Any]:
    return {
        "allowed_fields": list(CAPABILITY_RESULT_EXPECTED_FIELDS),
        "forbidden_fields": list(CAPABILITY_RESULT_FORBIDDEN_FIELDS),
        "note": (
            "capability_history entries are CapabilityResult values; only the "
            "listed fields exist on the frozen type"
        ),
    }


# ---------------------------------------------------------------------------
# RuntimeSnapshot serialization
# ---------------------------------------------------------------------------
def runtime_snapshot_field_names() -> tuple[str, ...]:
    return tuple(field.name for field in dataclasses.fields(RuntimeSnapshot))


def serialize_runtime_snapshot(snapshot: RuntimeSnapshot) -> dict[str, Any]:
    """Serialize a real RuntimeSnapshot for durable publication.

    Runtime-private correlation attributes (``_model_attempt_id``,
    ``_outbound_relay_id``) are deliberately not published: they are not part of
    the serialized Resident snapshot contract.
    """

    if not isinstance(snapshot, RuntimeSnapshot):
        raise SchemaContractError(
            f"expected RuntimeSnapshot, got {type(snapshot).__name__}"
        )
    history = []
    for item in snapshot.capability_history:
        history.append(capability_result_to_mapping(item))
    return {
        "serialized_fields": list(runtime_snapshot_field_names()),
        "user_input": snapshot.user_input,
        "wake_reason": snapshot.wake_reason,
        "cockpit": dict(snapshot.cockpit),
        "capability_catalog": [
            dict(entry) for entry in snapshot.capability_catalog
        ],
        "capability_history": history,
        "round_index": int(snapshot.round_index),
        "remaining_tool_rounds": int(snapshot.remaining_tool_rounds),
        "capability_history_contract": capability_history_contract(),
    }


# ---------------------------------------------------------------------------
# Response envelope parsing (bytes authored elsewhere; never generated here)
# ---------------------------------------------------------------------------
def response_envelope_contract() -> dict[str, Any]:
    return {
        "response_version": RESPONSE_VERSION,
        "envelope_keys": list(RESPONSE_ENVELOPE_KEYS),
        "directive_allowed_keys": list(MODEL_DIRECTIVE_ALLOWED_KEYS),
        "usage_allowed_keys": list(MODEL_USAGE_ALLOWED_KEYS),
        "provenance_allowed_keys": list(MODEL_PROVENANCE_ALLOWED_KEYS),
        "capability_call_keys": ["name", "arguments", "call_id"],
        "must_echo_request_id": True,
        "must_echo_request_sha256": True,
        "authored_by": "EXTERNAL_CURRENT_RESIDENT_SESSION",
    }


def _require_mapping(value: Any, what: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SchemaContractError(f"{what} must be a JSON object")
    return value


def _require_exact_keys(mapping: Mapping[str, Any], allowed: tuple[str, ...], what: str) -> None:
    unknown = set(mapping) - set(allowed)
    if unknown:
        raise SchemaContractError(f"{what} has unknown keys: {sorted(unknown)}")


def _optional_text(value: Any, what: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise SchemaContractError(f"{what} must be non-blank text when provided")
    return value


def parse_response_envelope(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the mechanical response envelope and return it unchanged."""

    envelope = _require_mapping(payload, "response envelope")
    missing = set(RESPONSE_ENVELOPE_KEYS) - set(envelope)
    if missing:
        raise SchemaContractError(f"response envelope missing keys: {sorted(missing)}")
    _require_exact_keys(envelope, RESPONSE_ENVELOPE_KEYS, "response envelope")
    if envelope["response_version"] != RESPONSE_VERSION:
        raise SchemaContractError(
            f"unsupported response_version: {envelope['response_version']!r}"
        )
    request_id = envelope["request_id"]
    if not isinstance(request_id, str) or not request_id.strip():
        raise SchemaContractError("response envelope request_id must be non-blank text")
    request_sha256 = envelope["request_sha256"]
    if not isinstance(request_sha256, str) or len(request_sha256) != 64:
        raise SchemaContractError("response envelope request_sha256 must be a sha256 digest")
    if envelope["authored_by"] != "EXTERNAL_CURRENT_RESIDENT_SESSION":
        raise SchemaContractError(
            "response envelope authored_by must be EXTERNAL_CURRENT_RESIDENT_SESSION"
        )
    _require_mapping(envelope["directive"], "response directive")
    return dict(envelope)


def parse_model_directive(payload: Mapping[str, Any]) -> ModelDirective:
    """Build a real ``ModelDirective`` from externally authored response bytes.

    The returned object is constructed from the payload only; no default,
    fallback or inferred content is ever added.
    """

    envelope = parse_response_envelope(payload)
    raw = _require_mapping(envelope["directive"], "response directive")
    _require_exact_keys(raw, MODEL_DIRECTIVE_ALLOWED_KEYS, "directive")

    calls_raw = raw.get("capability_calls", [])
    if not isinstance(calls_raw, (list, tuple)):
        raise SchemaContractError("directive capability_calls must be a list")
    calls: list[CapabilityCall] = []
    for index, item in enumerate(calls_raw):
        entry = _require_mapping(item, f"capability_calls[{index}]")
        _require_exact_keys(entry, ("name", "arguments", "call_id"), f"capability_calls[{index}]")
        name = entry.get("name")
        if not isinstance(name, str) or not name.strip():
            raise SchemaContractError(f"capability_calls[{index}].name must be non-blank text")
        arguments = entry.get("arguments", {})
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, Mapping):
            raise SchemaContractError(f"capability_calls[{index}].arguments must be an object")
        call_id = _optional_text(entry.get("call_id"), f"capability_calls[{index}].call_id")
        calls.append(CapabilityCall(name=name, arguments=dict(arguments), call_id=call_id))

    response_text = _optional_text(raw.get("response"), "directive response")
    silence = raw.get("silence", False)
    if not isinstance(silence, bool):
        raise SchemaContractError("directive silence must be a boolean")

    usage = None
    if raw.get("usage") is not None:
        usage_raw = _require_mapping(raw["usage"], "directive usage")
        _require_exact_keys(usage_raw, MODEL_USAGE_ALLOWED_KEYS, "directive usage")
        total = usage_raw.get("total_tokens")
        if isinstance(total, bool) or not isinstance(total, int) or total < 0:
            raise SchemaContractError("directive usage.total_tokens must be a non-negative integer")
        usage = ModelUsage(
            total_tokens=total,
            input_tokens=usage_raw.get("input_tokens"),
            output_tokens=usage_raw.get("output_tokens"),
            provider=_optional_text(usage_raw.get("provider"), "usage.provider"),
            model=_optional_text(usage_raw.get("model"), "usage.model"),
            request_id=_optional_text(usage_raw.get("request_id"), "usage.request_id"),
        )

    provenance = None
    if raw.get("provenance") is not None:
        provenance_raw = _require_mapping(raw["provenance"], "directive provenance")
        _require_exact_keys(provenance_raw, MODEL_PROVENANCE_ALLOWED_KEYS, "directive provenance")
        for key in MODEL_PROVENANCE_ALLOWED_KEYS:
            value = provenance_raw.get(key)
            if not isinstance(value, str) or not value.strip():
                raise SchemaContractError(f"directive provenance.{key} must be non-blank text")
        provenance = ModelCallProvenance(
            provider=provenance_raw["provider"],
            model=provenance_raw["model"],
            request_id=provenance_raw["request_id"],
        )

    # Construction validates the frozen invariants (round/terminal exclusivity).
    return ModelDirective(
        capability_calls=tuple(calls),
        response=response_text,
        silence=silence,
        usage=usage,
        provenance=provenance,
    )


def model_directive_to_mapping(directive: ModelDirective) -> dict[str, Any]:
    """Project a real directive to the JSON shape a Resident would author."""

    if not isinstance(directive, ModelDirective):
        raise SchemaContractError(
            f"expected ModelDirective, got {type(directive).__name__}"
        )
    payload: dict[str, Any] = {
        "capability_calls": [
            {
                "name": call.name,
                "arguments": dict(call.arguments),
                "call_id": call.call_id,
            }
            for call in directive.capability_calls
        ],
        "response": directive.response,
        "silence": bool(directive.silence),
    }
    if directive.usage is not None:
        payload["usage"] = {
            "total_tokens": directive.usage.total_tokens,
            "input_tokens": directive.usage.input_tokens,
            "output_tokens": directive.usage.output_tokens,
            "provider": directive.usage.provider,
            "model": directive.usage.model,
            "request_id": directive.usage.request_id,
        }
    if directive.provenance is not None:
        payload["provenance"] = {
            "provider": directive.provenance.provider,
            "model": directive.provenance.model,
            "request_id": directive.provenance.request_id,
        }
    return payload
