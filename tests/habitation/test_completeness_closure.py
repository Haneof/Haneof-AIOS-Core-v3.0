from datetime import datetime, timedelta, timezone

from aios_core.runtime.cognitive_runtime import ModelDirective

from .current_core import CurrentCoreHabitationTarget
from .harness import ResidentEvent


UTC = timezone.utc
START = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)


def test_current_core_habitation_runs_dimension_summary_clock(tmp_path):
    summary_calls = []

    def resident(_snapshot):
        return ModelDirective(response="ok")

    def summarize(request):
        summary_calls.append(request)
        return "durable dimension summary"

    target = CurrentCoreHabitationTarget(
        model_id="fake:model",
        subject_id="synthetic-user",
        db_path=tmp_path / "world.sqlite",
        model_handler=resident,
        round_summary_handler=summarize,
        require_fresh=True,
    )
    assert target.runtime.dimension_summary_scheduler is not None

    target.advance_to(START)
    target.handle_event(
        ResidentEvent(
            event_id="note-1",
            occurred_at=START,
            channel="note",
            payload="first durable note",
            metadata={"source": "notes"},
        )
    )
    result = target.advance_to(START + timedelta(days=2))

    assert result["dimension_summaries"]["invoked"] is True
    assert result["dimension_summaries"]["commits"]
    assert summary_calls

    summaries = target.store.list_payloads(
        subject_id="synthetic-user",
    )
    assert any(item.get("object_type") == "summary" for item in summaries)


def test_current_core_catalog_exposes_new_cognition_closure_capabilities(tmp_path):
    def resident(_snapshot):
        return ModelDirective(response="ok")

    target = CurrentCoreHabitationTarget(
        model_id="fake:model",
        subject_id="synthetic-user",
        db_path=tmp_path / "world.sqlite",
        model_handler=resident,
        require_fresh=True,
    )
    names = {item["name"] for item in target.runtime.registry.catalog()}
    for required in {
        "propose_entity",
        "revise_entity",
        "upsert_relation",
        "propose_cognitive_policy",
        "update_cognitive_policy",
        "rollback_cognitive_policy",
    }:
        assert required in names
