"""T05: the kernel's argument mini-language has to translate without losing anything.

Every capability is advertised to the model twice — argument names rendered into
the prompt text, and a JSON Schema in a ``tools`` array once T06 lands. Two views
of one contract. The prompt renderer already drifted once: it showed names with
no signatures while required arguments existed in another copy of the catalog, and
a live model invented ``claim``/``evidence`` instead of ``statement``/
``evidence_refs``. The write was rejected and nothing durable survived the turn.

So this file asserts the two views cannot disagree, for every single capability —
not a sample. It also asserts each schema is satisfiable, and that nothing silently
fell back to a looser type than the kernel enforces.
"""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import pytest
from jsonschema import Draft202012Validator

from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.capabilities import (
    json_schema_for_arguments,
    required_arguments,
)
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore

_FALLBACK_MARKER = "declared as "


def _real_catalog(root: Path) -> tuple[dict, ...]:
    """The catalog the provider renders, not the cockpit's slimmer budget copy."""

    captured: dict[str, Any] = {}

    def handler(snapshot):  # type: ignore[no-untyped-def]
        captured["snapshot"] = snapshot
        return ModelDirective(response="ok")

    store = SQLiteWorldStore(str(root / "world.sqlite"))
    index = WorldSearchIndex(str(root / "index.sqlite"), store=store)
    index.rebuild()
    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=handler,
        subject_id="user_1",
        recent_turn_limit=3,
    )
    runtime.run_turn(
        session_id="s",
        turn_index=1,
        user_input="hi",
        occurred_at=datetime(2026, 10, 22, 10, tzinfo=timezone.utc),
    )
    return captured["snapshot"].capability_catalog


def _build_catalog() -> tuple[dict, ...]:
    root = Path(tempfile.mkdtemp(prefix="aios-schema-catalog-"))
    return _real_catalog(root)


_ALL_CAPABILITIES: tuple[dict, ...] = _build_catalog()

_NAMED: dict[str, Mapping[str, Any]] = {
    str(cap.get("name")): cap.get("input_schema") or {}
    for cap in _ALL_CAPABILITIES
    if isinstance(cap, Mapping) and cap.get("name")
}

_SCHEMAS: dict[str, dict[str, Any]] = {
    name: json_schema_for_arguments(schema) for name, schema in _NAMED.items()
}


def _conforming_value(schema: Mapping[str, Any]) -> Any:
    """One value the given schema accepts.

    Only used to prove a schema is *satisfiable*. A schema that cannot be met by
    any value would reject every well-formed call the model could produce, which
    looks identical to "the model refused to write".
    """

    if not isinstance(schema, Mapping) or not schema:
        return "<anything>"
    kind = schema.get("type")
    if kind == "string":
        if "enum" in schema:
            return schema["enum"][0]
        if "pattern" in schema:
            # ^dim: -> "dim:<text>", which satisfies the anchor we generated.
            return str(schema["pattern"]).lstrip("^").replace("\\", "") + "<text>"
        return "<text>"
    if kind == "integer":
        return 1
    if kind == "number":
        low, high = schema.get("minimum"), schema.get("maximum")
        if low is not None and high is not None:
            return (low + high) / 2
        return 1.0
    if kind == "boolean":
        return True
    if kind == "array":
        return [_conforming_value(schema.get("items") or {})]
    if kind == "object":
        value = {
            name: _conforming_value(sub) for name, sub in (schema.get("properties") or {}).items()
        }
        extra = schema.get("additionalProperties")
        if isinstance(extra, Mapping) and not value:
            value["any_key"] = _conforming_value(extra)
        return value
    return "<anything>"


def test_catalog_is_not_vacuous() -> None:
    """Guard the suite itself: a collapsed catalog makes every assertion below pass."""

    assert len(_NAMED) >= 40, (
        f"only {len(_NAMED)} capabilities reached the catalog; the assertions below "
        "would pass while asserting almost nothing"
    )
    assert "commit_ai_world_claim" in _NAMED, (
        "the continuity write vanished from the catalog — exactly the drift this file exists to catch"
    )


@pytest.mark.parametrize("name", sorted(_NAMED))
def test_required_matches_the_prompt_contract(name: str) -> None:
    """The tools array and the rendered prompt must demand the same arguments."""

    schema = _SCHEMAS[name]
    declared = set(required_arguments(_NAMED[name]))
    advertised = set(schema.get("required", []))

    assert advertised == declared, (
        f"{name}: tools array requires {sorted(advertised)} but the prompt contract "
        f"requires {sorted(declared)}; the model is being given two contracts for one call"
    )


@pytest.mark.parametrize("name", sorted(_NAMED))
def test_schema_is_a_valid_json_schema(name: str) -> None:
    Draft202012Validator.check_schema(_SCHEMAS[name])


@pytest.mark.parametrize("name", sorted(_NAMED))
def test_required_arguments_are_satisfiable(name: str) -> None:
    """A call that supplies every required argument must validate.

    Every property name in the schema has to be one the kernel actually accepts,
    otherwise the model fills in a name that does not exist and the call is
    rejected for inventing it.
    """

    schema = _SCHEMAS[name]
    properties = schema.get("properties", {})
    call = {key: _conforming_value(properties[key]) for key in schema.get("required", [])}

    Draft202012Validator(schema).validate(call)

    unknown = set(call) - set(_NAMED[name])
    assert not unknown, f"{name}: schema advertises argument(s) the kernel does not declare: {sorted(unknown)}"


def test_no_argument_type_silently_degrades() -> None:
    """Falling back to ``string`` hands the model a looser contract than the kernel enforces.

    A fallback does not crash, so nothing red would show up elsewhere. It just
    means the model is told "any string" where the turn will later reject the
    value — the same silent failure class we are getting away from.
    """

    degraded: list[str] = []
    for name, schema in _SCHEMAS.items():
        for argument, fragment in (schema.get("properties") or {}).items():
            if str(fragment.get("description", "")).startswith(_FALLBACK_MARKER):
                degraded.append(f"{name}.{argument}: {fragment['description'][len(_FALLBACK_MARKER):]}")

    assert not degraded, (
        "these argument types were not recognised by the converter and degraded to string:\n"
        + "\n".join(sorted(degraded))
    )


@pytest.mark.parametrize(
    ("declared", "expected"),
    [
        ("string", {"type": "string"}),
        ("integer", {"type": "integer"}),
        ("number", {"type": "number"}),
        ("boolean", {"type": "boolean"}),
        ("integer?", {"type": "integer"}),
        ("number[0,1]", {"type": "number", "minimum": 0.0, "maximum": 1.0}),
        ("array[string]", {"type": "array", "items": {"type": "string"}}),
        ("a|b|c", {"type": "string", "enum": ["a", "b", "c"]}),
        (
            "{object_id:string,revision:integer}",
            {
                "type": "object",
                "properties": {"object_id": {"type": "string"}, "revision": {"type": "integer"}},
                "required": ["object_id", "revision"],
            },
        ),
        (
            "array[{object_id:string,revision:integer}]",
            {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"object_id": {"type": "string"}, "revision": {"type": "integer"}},
                    "required": ["object_id", "revision"],
                },
            },
        ),
        ("ISO-8601 datetime", {"type": "string", "format": "date-time"}),
        ("object[number]", {"type": "object", "additionalProperties": {"type": "number"}}),
    ],
)
def test_single_type_translation(declared: str, expected: dict[str, Any]) -> None:
    produced = json_schema_for_arguments({"probe": declared})["properties"]["probe"]
    for key, value in expected.items():
        assert produced.get(key) == value, f"{declared}: expected {key}={value!r}, got {produced.get(key)!r}"


def test_trailing_semicolon_guidance_is_not_a_type() -> None:
    """``object?; use mode=...`` — the instruction after the semicolon is not a type."""

    schema = json_schema_for_arguments({"probe": "object?; use mode=append"})
    assert schema["properties"]["probe"] == {"type": "object"}
    assert "required" not in schema


def test_empty_schema_is_still_a_usable_object_schema() -> None:
    assert json_schema_for_arguments({})["type"] == "object"
    assert json_schema_for_arguments(None)["properties"] == {}
