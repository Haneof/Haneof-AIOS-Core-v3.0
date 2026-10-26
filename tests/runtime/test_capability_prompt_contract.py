"""The prompt must not instruct the model to call something it cannot see.

A live local model reproduced the failure this file guards against: told to
"persist it with commit_ai_world_claim", it emitted

    {"call": "commit_ai_world_claim", "arguments": {
        "domain": "user_understanding", "claim_text": "...", "evidence": [...]}}

The kernel expects ``statement`` / ``evidence_refs`` / ``confidence``, so the
write was rejected, no claim existed, and the continuity anchor stayed empty for
the rest of the conversation. The model was not unwilling; it had never been
told the argument names.
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.grok_provider import (
    GrokProviderConfig,
    GrokStreamingProvider,
    _render_capabilities,
    _render_capability_result,
)
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore


def _snapshot(tmp_path: Path):
    captured: dict = {}

    def handler(snapshot):  # type: ignore[no-untyped-def]
        captured.setdefault("snapshot", snapshot)
        captured.update(snapshot.cockpit)
        return ModelDirective(response="ok")

    store = SQLiteWorldStore(str(tmp_path / "world.sqlite"))
    index = WorldSearchIndex(str(tmp_path / "index.sqlite"), store=store)
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
    return captured["snapshot"]


def _real_catalog(tmp_path: Path) -> tuple[dict, ...]:
    """The catalog the provider actually renders.

    Not ``snapshot.cockpit["capability_catalog"]``: that is a separate, slimmer copy
    built for budgeting. An earlier fix computed ``required_args`` into the cockpit
    copy while the renderer read this one, so every assertion below passed against a
    catalog no model ever saw, and the live prompt still showed names with no
    signatures.
    """

    return _snapshot(tmp_path).capability_catalog


def test_every_capability_is_named_not_just_the_first_ten(tmp_path: Path) -> None:
    catalog = _real_catalog(tmp_path)
    rendered = _render_capabilities(catalog)

    assert len(catalog) > 10, "catalog must be larger than the old renderer's cap for this to mean anything"
    missing = [cap["name"] for cap in catalog if cap["name"] not in rendered]
    assert missing == []


def test_continuity_write_arguments_are_stated(tmp_path: Path) -> None:
    catalog = _real_catalog(tmp_path)
    rendered = _render_capabilities(catalog)

    commit_line = next(
        line for line in rendered.splitlines() if line.startswith("- commit_ai_world_claim(")
    )
    for required in ("domain", "statement", "evidence_refs", "confidence"):
        assert required in commit_line, f"{required} must be stated or the model will invent it"


def test_optional_arguments_are_not_advertised_as_required(tmp_path: Path) -> None:
    catalog = _real_catalog(tmp_path)
    commit = next(cap for cap in catalog if cap["name"] == "commit_ai_world_claim")

    # tags is optional in the kernel schema; the standing instructions explain the
    # one value that matters (core_context), so it does not belong in a signature.
    assert "tags" not in commit["required_args"]
    assert "claim_type" not in commit["required_args"]


def test_worked_example_uses_the_same_argument_names(tmp_path: Path) -> None:
    """Prose names alone were not enough; a local model needed the shape itself."""

    catalog = _real_catalog(tmp_path)
    rendered = _render_capabilities(catalog)

    assert "example (copy this shape):" in rendered
    example_line = rendered.split("example (copy this shape):")[1].strip().splitlines()[0]
    example = json.loads(example_line)

    assert example["call"] == "commit_ai_world_claim"
    assert set(example["arguments"]) == {"domain", "statement", "evidence_refs", "confidence"}
    # The shape of evidence matters as much as the name: a bare id string is rejected.
    assert example["arguments"]["evidence_refs"] == [
        {"object_id": "<observation object_id>", "revision": 1}
    ]


def test_guidance_appended_to_a_type_is_not_mistaken_for_a_type() -> None:
    from aios_core.runtime.turn_runtime import _required_arguments

    required = _required_arguments(
        {
            "title": "string",
            "completion_condition": "object?; use mode=world_evidence|action_evidence",
            "mode": "world_evidence|action_evidence",
        }
    )
    assert "completion_condition" not in required
    # Long types are abbreviated for display; the kernel still validates in full.
    assert required["mode"].startswith("world_evidence|")


def test_required_arguments_match_the_registered_schema(tmp_path: Path) -> None:
    catalog = _real_catalog(tmp_path)
    by_name = {cap["name"]: cap for cap in catalog}

    # A capability with no required arguments must not claim any.
    assert "required_args" not in by_name["list_dimensions"]

    # The write path carries them; the read path does not pay for them.
    assert "required_args" in by_name["commit_claim"]
    assert "required_args" in by_name["create_task"]


def test_renderer_tolerates_missing_or_malformed_catalog() -> None:
    assert _render_capabilities(None) == ""
    assert _render_capabilities([]) == ""
    assert _render_capabilities([{"kind": "read"}]) == ""
    assert _render_capabilities(["not-a-mapping"]) == ""


def test_renderer_keeps_names_when_no_signatures_exist() -> None:
    rendered = _render_capabilities([{"name": "search_world", "kind": "read"}])
    assert "search_world" in rendered
    assert "write path" not in rendered


@pytest.mark.parametrize("name", ["commit_ai_world_claim", "commit_claim", "revise_claim", "retract_claim"])
def test_every_continuity_write_is_covered(name: str, tmp_path: Path) -> None:
    catalog = _real_catalog(tmp_path)
    rendered = _render_capabilities(catalog)
    assert any(line.startswith(f"- {name}(") for line in rendered.splitlines())


def test_rejected_call_reports_why_it_was_rejected() -> None:
    """A bare ok=False teaches the model nothing; its next attempt repeats the mistake."""

    from aios_core.runtime.capabilities import CapabilityResult

    rejected = CapabilityResult(
        name="commit_ai_world_claim",
        ok=False,
        error_code="INVALID_ARGUMENTS",
        error_message="missing required argument: statement",
    )
    rendered = _render_capability_result(rejected)

    assert "ok=False" in rendered
    assert "INVALID_ARGUMENTS" in rendered
    assert "missing required argument: statement" in rendered


def test_rejected_call_without_detail_still_invites_a_correction() -> None:
    from aios_core.runtime.capabilities import CapabilityResult

    rendered = _render_capability_result(
        CapabilityResult(name="search_world", ok=False)
    )
    assert "ok=False" in rendered
    assert "call again" in rendered


def test_successful_call_reports_its_data() -> None:
    from aios_core.runtime.capabilities import CapabilityResult

    rendered = _render_capability_result(
        CapabilityResult(name="list_dimensions", ok=True, data={"count": 3})
    )
    assert "ok=True" in rendered
    assert '"count": 3' in rendered


def test_the_prompt_a_provider_sends_states_write_arguments(tmp_path: Path) -> None:
    """The composition is what matters, not the renderer in isolation.

    Everything above renders a catalog by hand. This one builds the actual system
    message a provider would POST, because the defect being guarded against was a
    wiring mistake: the signatures existed, in the wrong catalog.
    """

    snapshot = _snapshot(tmp_path)
    provider = GrokStreamingProvider(
        GrokProviderConfig(base_url="http://127.0.0.1:9/v1", api_key="k", default_model="m")
    )
    sent: dict = {}

    def fake_stream_chat(messages, model=None, **kwargs):  # type: ignore[no-untyped-def]
        sent["messages"] = messages
        return "ok", None, None

    provider.stream_chat = fake_stream_chat  # type: ignore[method-assign]
    provider.as_model_handler(model="m")(snapshot)

    system = sent["messages"][0]["content"]
    assert "commit_ai_world_claim(domain:" in system
    assert "evidence_refs:[{object_id,revision}]" in system
    assert "example (copy this shape)" in system
