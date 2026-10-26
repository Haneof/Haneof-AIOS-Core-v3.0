"""A rejected capability call must tell the model how to fix it.

Observed live: a local model called ``commit_ai_world_claim`` with ``claim``
instead of ``statement``. The kernel rejected it with "got an unexpected keyword
argument 'claim'", which is true and useless — the model repeated the same call
three rounds running, and nothing was ever persisted. The registry knew the
schema the whole time; the error just never said it.
"""

from __future__ import annotations

from aios_core.runtime.capabilities import (
    CapabilityCall,
    CapabilityKind,
    CapabilityRegistry,
    CapabilitySpec,
)


def _registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()
    registry.register(
        CapabilitySpec(
            name="commit_ai_world_claim",
            description="persist a claim",
            kind=CapabilityKind.WRITE,
            input_schema={
                "domain": "user_understanding|relationship|self",
                "statement": "string",
                "evidence_refs": "array[{object_id:string,revision:integer}]",
                "confidence": "number[0,1]",
                "tags": "array[string]?",
            },
        ),
        lambda domain, statement, evidence_refs, confidence, tags=(): {"ok": True},
    )
    return registry


def test_argument_error_names_the_accepted_arguments() -> None:
    result = _registry().invoke(
        CapabilityCall(
            name="commit_ai_world_claim",
            arguments={
                "domain": "user_understanding",
                "claim": "老王",
                "evidence": "obs_1",
            },
        )
    )

    assert result.ok is False
    assert result.error_code == "CAPABILITY_ARGUMENT_ERROR"
    message = result.error_message or ""
    for required in ("domain", "statement", "evidence_refs", "confidence"):
        assert required in message, f"{required} must be named so the retry can succeed"
    assert "tags" in message  # optional, still worth naming
    assert "claim" in message  # the key that was actually rejected


def test_argument_error_separates_required_from_optional() -> None:
    result = _registry().invoke(CapabilityCall(name="commit_ai_world_claim", arguments={}))
    message = result.error_message or ""

    required_part = message.split("required arguments:")[1].split("optional arguments:")[0]
    assert "statement" in required_part
    assert "tags" not in required_part


def test_successful_invocation_is_unaffected() -> None:
    result = _registry().invoke(
        CapabilityCall(
            name="commit_ai_world_claim",
            arguments={
                "domain": "user_understanding",
                "statement": "老王在东莞做 23cm 手环",
                "evidence_refs": [{"object_id": "obs_1", "revision": 1}],
                "confidence": 0.9,
                "tags": ["core_context"],
            },
        )
    )
    assert result.ok is True
    assert result.error_message is None


def test_unknown_capability_is_unchanged() -> None:
    result = _registry().invoke(CapabilityCall(name="no_such_capability"))
    assert result.error_code == "CAPABILITY_NOT_FOUND"
