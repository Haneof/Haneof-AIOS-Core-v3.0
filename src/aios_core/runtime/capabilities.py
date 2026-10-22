"""Auditable capability registry for the AIOS Executive Plane.

The registry is intentionally dumb about cognition. It tells the model what it can
ask the system to do, validates call shape, executes the registered handler, and
returns structured evidence/errors. It does not decide which capability is relevant.
"""

from __future__ import annotations

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
