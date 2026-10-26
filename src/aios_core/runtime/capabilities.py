"""Auditable capability registry for the AIOS Executive Plane.

The registry is intentionally dumb about cognition. It tells the model what it can
ask the system to do, validates call shape, executes the registered handler, and
returns structured evidence/errors. It does not decide which capability is relevant.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable, Mapping


class CapabilityKind(StrEnum):
    READ = "read"
    WRITE = "write"
    ACTION = "action"
    RESPONSE = "response"


# Writes whose silent failure costs continuity. Every one of them has to be called
# with the right argument names the first time: the turn ends, so there is no
# second attempt, and a rejected write leaves nothing durable behind.
#
# This set lives next to the registry rather than next to the prompt renderer
# because it classifies capabilities, not presentation. Both catalog copies (the
# full one a provider renders and the compact one in the cockpit) read it from
# here, so they cannot drift apart again — the drift was the bug: the compact copy
# carried `required_args` while the rendered copy did not, and the prompt showed
# names with no signatures at all.
CONTINUITY_WRITE_CAPABILITIES = frozenset(
    {
        "commit_ai_world_claim",
        "commit_claim",
        "revise_claim",
        "retract_claim",
        "record_ai_promise",
        "propose_goal",
        "create_task",
    }
)

_ARGUMENT_TYPE_SHORTHANDS = {
    "array[{object_id:string,revision:integer}]": "[{object_id,revision}]",
    "{object_id:string,revision:integer}": "{object_id,revision}",
}


def required_arguments(input_schema: Any) -> dict[str, str]:
    """Return ``{name: short_type}`` for required arguments only.

    Optional arguments are omitted on purpose: they can be left out and the call
    still succeeds. Required ones cannot, and an unknown required name is exactly
    what makes a write fail.
    """

    if not isinstance(input_schema, Mapping):
        return {}
    required: dict[str, str] = {}
    for name, type_text in input_schema.items():
        # Some schemas append guidance after a semicolon ("object?; use mode=...").
        # The type is the part before it; the rest is instruction, not a type.
        text = str(type_text).split(";")[0].strip()
        if text.endswith("?"):
            continue
        short = _ARGUMENT_TYPE_SHORTHANDS.get(text)
        if short is None:
            short = text if len(text) <= 24 else text[:21] + "..."
        required[str(name)] = short
    return required


_JSON_SCHEMA_SCALARS: dict[str, dict[str, Any]] = {
    "string": {"type": "string"},
    "integer": {"type": "integer"},
    "number": {"type": "number"},
    "boolean": {"type": "boolean"},
    "object": {"type": "object"},
    "array": {"type": "array"},
}


def _split_top_level(text: str) -> list[str]:
    """Split on commas that sit outside any brace or bracket.

    ``{object_id:string,path:array[string]?}`` uses a comma both to separate
    members and inside a member's own type, so a plain split would cut a type in
    half and invent a member named ``path:array[string``.
    """

    parts: list[str] = []
    current: list[str] = []
    depth = 0
    for char in text:
        if char in "{[":
            depth += 1
        elif char in "}]":
            depth -= 1
        if char == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
    tail = "".join(current)
    if tail.strip():
        parts.append(tail)
    return [part.strip() for part in parts if part.strip()]


def _strip_optional(text: str) -> tuple[str, bool]:
    """Split a declared type from its trailing ``?`` marker."""

    stripped = text.strip()
    if stripped.endswith("?"):
        return stripped[:-1].strip(), True
    return stripped, False


def _parse_object_members(members: str) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []
    for member in _split_top_level(members):
        key, _, value = member.partition(":")
        if not key.strip() or not value.strip():
            continue
        name = key.strip()
        inner, optional = _strip_optional(value)
        properties[name] = _parse_type_text(inner)
        if not optional:
            required.append(name)
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _parse_type_text(text: str) -> dict[str, Any]:
    """Translate one mini-language type string into a JSON Schema fragment.

    The kernel declares argument types in a language meant for a human reading a
    prompt — ``string``, ``integer?``, ``array[string]``, ``number[0,1]``,
    ``a|b|c``, ``{object_id:string,revision:integer}``. A ``tools`` array needs
    real JSON Schema instead, and every constraint has to survive that
    translation: if the schema says ``number`` where the kernel meant ``number
    between 0 and 1``, the model supplies something legal that the turn then
    rejects.

    Unknown spellings degrade to ``string`` rather than raising. A crash would be
    loud and obvious; a quietly wrong parameter shape teaches the model the wrong
    contract, which is the failure we are trying to end.
    """

    declared, _ = _strip_optional(text)
    if not declared:
        return {}
    lowered = declared.lower()

    if lowered.startswith("iso-8601"):
        return {"type": "string", "format": "date-time", "description": declared}
    if lowered.startswith("string starting "):
        prefix = declared[len("string starting ") :].strip()
        return {"type": "string", "pattern": f"^{re.escape(prefix)}", "description": declared}
    if "json value" in lowered:
        # Deliberately unconstrained: every JSON value is acceptable here.
        return {"description": declared}
    if "temporalextent" in lowered:
        return {"type": "object", "description": declared}

    bounded = re.fullmatch(r"number\s*\[\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\]", declared)
    if bounded:
        return {
            "type": "number",
            "minimum": float(bounded.group(1)),
            "maximum": float(bounded.group(2)),
        }

    map_of = re.fullmatch(r"object\s*\[\s*([A-Za-z]+)\s*\]", declared)
    if map_of:
        return {"type": "object", "additionalProperties": _parse_type_text(map_of.group(1))}

    if declared.startswith("array[") and declared.endswith("]"):
        return {"type": "array", "items": _parse_type_text(declared[6:-1])}

    if declared.startswith("{") and declared.endswith("}"):
        return _parse_object_members(declared[1:-1])

    if "|" in declared:
        return {
            "type": "string",
            "enum": [part.strip() for part in declared.split("|") if part.strip()],
        }

    scalar = _JSON_SCHEMA_SCALARS.get(lowered)
    if scalar is not None:
        return dict(scalar)

    return {"type": "string", "description": f"declared as {declared}"}


def json_schema_for_arguments(input_schema: Any) -> dict[str, Any]:
    """Convert a kernel ``input_schema`` into the JSON Schema a tools array needs.

    This sits next to ``required_arguments`` deliberately. Both answer "what must
    the caller supply"; if they disagree, the prompt text and the tools array
    advertise two different contracts for one call, which is exactly the class of
    drift that already cost us once. ``required`` here matches
    ``required_arguments`` by construction — same semicolon rule for appended
    guidance, same trailing-``?`` rule for optionality.
    """

    if not isinstance(input_schema, Mapping):
        return {"type": "object", "properties": {}, "required": []}
    properties: dict[str, Any] = {}
    required: list[str] = []
    for name, type_text in input_schema.items():
        declared = str(type_text).split(";")[0].strip()
        inner, optional = _strip_optional(declared)
        properties[str(name)] = _parse_type_text(inner)
        if not optional:
            required.append(str(name))
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


@dataclass(frozen=True)
class CapabilitySpec:
    name: str
    description: str
    kind: CapabilityKind = CapabilityKind.READ
    input_schema: Mapping[str, Any] = field(default_factory=dict)
    hard_boundary: bool = False
    side_effecting: bool = False

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("capability name must be non-blank")
        if not self.description or not self.description.strip():
            raise ValueError("capability description must be non-blank")
        if self.kind in {CapabilityKind.WRITE, CapabilityKind.ACTION} and not self.side_effecting:
            object.__setattr__(self, "side_effecting", True)


@dataclass(frozen=True)
class CapabilityCall:
    name: str
    arguments: Mapping[str, Any] = field(default_factory=dict)
    call_id: str | None = None

    def normalized_signature(self) -> tuple[str, tuple[tuple[str, str], ...]]:
        # A conservative loop signature. repr() is only used for duplicate-call
        # detection inside one transient turn; it is not a durable identity format.
        return (
            self.name,
            tuple(sorted((str(k), repr(v)) for k, v in self.arguments.items())),
        )


@dataclass(frozen=True)
class CapabilityResult:
    name: str
    ok: bool
    data: Any = None
    error_code: str | None = None
    error_message: str | None = None
    call_id: str | None = None


@dataclass(frozen=True)
class _RegisteredCapability:
    spec: CapabilitySpec
    handler: Callable[..., Any]


def _argument_error_message(
    call: CapabilityCall,
    spec: CapabilitySpec,
    exc: TypeError,
) -> str:
    """Explain an argument mismatch in terms the model can act on.

    ``got an unexpected keyword argument 'claim'`` is true and useless: it says
    what was rejected, never what is accepted. A live model called
    ``commit_ai_world_claim`` with ``claim`` instead of ``statement`` three rounds
    in a row, because each rejection told it nothing it could correct. The schema
    was available the whole time; this puts it where the model is actually looking
    — the error it just received.
    """

    schema = spec.input_schema or {}
    required: list[str] = []
    optional: list[str] = []
    for name, type_text in schema.items():
        (optional if str(type_text).endswith("?") else required).append(str(name))

    unexpected = sorted(key for key in call.arguments if key not in schema)

    parts = [str(exc)]
    if unexpected:
        parts.append(f"unrecognized argument(s): {', '.join(unexpected)}")
    if required:
        parts.append(f"required arguments: {', '.join(required)}")
    if optional:
        parts.append(f"optional arguments: {', '.join(optional)}")
    return ". ".join(parts)


class CapabilityRegistry:
    """Registry + execution boundary for model-callable capabilities."""

    def __init__(self) -> None:
        self._items: dict[str, _RegisteredCapability] = {}

    def register(self, spec: CapabilitySpec, handler: Callable[..., Any]) -> None:
        if spec.name in self._items:
            raise ValueError(f"capability already registered: {spec.name}")
        if not callable(handler):
            raise TypeError("capability handler must be callable")
        self._items[spec.name] = _RegisteredCapability(spec=spec, handler=handler)

    def unregister(self, name: str) -> None:
        self._items.pop(name, None)

    def get_spec(self, name: str) -> CapabilitySpec:
        try:
            return self._items[name].spec
        except KeyError:
            raise KeyError(f"unknown capability: {name}") from None

    def catalog(self) -> list[dict[str, Any]]:
        """Return model-facing capability metadata without leaking Python handlers.

        Continuity writes also carry ``required_args``. The prompt renderer only has
        this catalog, so a signature computed anywhere else never reaches the model.
        """

        entries: list[dict[str, Any]] = []
        for _, item in sorted(self._items.items()):
            entry = {
                "name": item.spec.name,
                "description": item.spec.description,
                "kind": item.spec.kind.value,
                "input_schema": dict(item.spec.input_schema),
                "hard_boundary": item.spec.hard_boundary,
                "side_effecting": item.spec.side_effecting,
            }
            if item.spec.name in CONTINUITY_WRITE_CAPABILITIES:
                entry["required_args"] = required_arguments(item.spec.input_schema)
            entries.append(entry)
        return entries

    def invoke(self, call: CapabilityCall) -> CapabilityResult:
        item = self._items.get(call.name)
        if item is None:
            return CapabilityResult(
                name=call.name,
                ok=False,
                error_code="CAPABILITY_NOT_FOUND",
                error_message=f"unknown capability: {call.name}",
                call_id=call.call_id,
            )

        try:
            value = item.handler(**dict(call.arguments))
        except TypeError as exc:
            return CapabilityResult(
                name=call.name,
                ok=False,
                error_code="CAPABILITY_ARGUMENT_ERROR",
                error_message=_argument_error_message(call, item.spec, exc),
                call_id=call.call_id,
            )
        except Exception as exc:  # handler errors become structured tool evidence
            return CapabilityResult(
                name=call.name,
                ok=False,
                error_code="CAPABILITY_EXECUTION_ERROR",
                error_message=f"{type(exc).__name__}: {exc}",
                call_id=call.call_id,
            )

        return CapabilityResult(
            name=call.name,
            ok=True,
            data=value,
            call_id=call.call_id,
        )
