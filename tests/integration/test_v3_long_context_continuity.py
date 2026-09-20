from datetime import datetime, timedelta, timezone

import pytest

from aios_core.context.continuity import ConversationContinuityService
from aios_core.contracts.enums import ObjectType
from aios_core.ingest.conversation import ConversationIngestor
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore


NOW = datetime(2026, 9, 20, 16, 0, tzinfo=timezone.utc)


def _world(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index


def _seed_turns(store, *, session_id: str, count: int, prefix: str = "s"):
    ingest = ConversationIngestor(store)
    for turn in range(1, count + 1):
        ingest.commit_turn(
            session_id=session_id,
            turn_index=turn,
            user_text=f"{prefix}-user-{turn}",
            assistant_text=f"{prefix}-assistant-{turn}",
            occurred_at=NOW + timedelta(minutes=turn),
        )


def test_world_rebuilds_recent_turns_and_schedules_contiguous_round_summary(tmp_path):
    store, index = _world(tmp_path)
    _seed_turns(store, session_id="long", count=3, prefix="long")
    _seed_turns(store, session_id="other", count=1, prefix="other")
    service = ConversationContinuityService(store=store, index=index)

    snapshot = service.snapshot(
        session_id="long",
        before_turn=4,
        recent_turn_limit=1,
        summary_chunk_turns=2,
    )

    assert [turn["turn_index"] for turn in snapshot.recent_turns] == [3]
    assert snapshot.round_summaries == ()
    assert snapshot.pending_summary is not None
    assert snapshot.pending_summary.turn_start == 1
    assert snapshot.pending_summary.turn_end == 2
    assert [m.role for m in snapshot.pending_summary.sources] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert all(m.session_id == "long" for m in snapshot.pending_summary.sources)


def test_round_summary_pins_raw_dialogue_and_drills_down_without_deleting_truth(tmp_path):
    store, index = _world(tmp_path)
    _seed_turns(store, session_id="long", count=3, prefix="raw")
    service = ConversationContinuityService(store=store, index=index)

    request = service.prepare_next_round_summary(
        session_id="long",
        before_turn=4,
        recent_turn_limit=1,
        summary_chunk_turns=2,
    )
    assert request is not None

    receipt = service.commit_round_summary(
        request,
        content="前两轮围绕 raw-user-1 和 raw-user-2 展开。",
        generated_at=NOW + timedelta(hours=1),
    )

    summary = store.get_payload(receipt.object_id)
    assert summary["object_type"] == ObjectType.SUMMARY.value
    assert summary["metadata"]["summary_kind"] == "conversation_round"
    assert summary["metadata"]["session_id"] == "long"
    assert summary["metadata"]["turn_start"] == 1
    assert summary["metadata"]["turn_end"] == 2
    assert len(summary["source_refs"]) == 4

    raw = service.drill_down_summary(receipt.object_id)
    assert [(item["turn_index"], item["role"], item["text"]) for item in raw] == [
        (1, "user", "raw-user-1"),
        (1, "assistant", "raw-assistant-1"),
        (2, "user", "raw-user-2"),
        (2, "assistant", "raw-assistant-2"),
    ]

    # Summary is an index only. All raw dialogue facts remain durable.
    observations = store.list_payloads(object_type=ObjectType.OBSERVATION)
    assert len(observations) == 6


def test_summary_retry_is_idempotent_but_changed_summary_fails_closed(tmp_path):
    store, index = _world(tmp_path)
    _seed_turns(store, session_id="long", count=3)
    service = ConversationContinuityService(store=store, index=index)
    request = service.prepare_next_round_summary(
        session_id="long",
        before_turn=4,
        recent_turn_limit=1,
        summary_chunk_turns=2,
    )
    assert request is not None

    first = service.commit_round_summary(
        request,
        content="稳定摘要",
        generated_at=NOW + timedelta(hours=1),
    )
    replay = service.commit_round_summary(
        request,
        content="稳定摘要",
        generated_at=NOW + timedelta(hours=1),
    )
    assert replay.object_id == first.object_id
    assert replay.reused_existing is True

    with pytest.raises(ValueError, match="different content"):
        service.commit_round_summary(
            request,
            content="偷偷改写摘要",
            generated_at=NOW + timedelta(hours=2),
        )


def test_same_session_id_is_isolated_between_subjects(tmp_path):
    store, index = _world(tmp_path)
    user_one = ConversationIngestor(store, subject_id="user_1")
    user_two = ConversationIngestor(store, subject_id="user_2")

    first = user_one.commit_turn(
        session_id="shared",
        turn_index=1,
        user_text="user one",
        assistant_text="one reply",
        occurred_at=NOW,
    )
    second = user_two.commit_turn(
        session_id="shared",
        turn_index=1,
        user_text="user two",
        assistant_text="two reply",
        occurred_at=NOW,
    )

    assert first.user_observation_id != second.user_observation_id
    one = ConversationContinuityService(
        store=store,
        index=index,
        subject_id="user_1",
    )
    two = ConversationContinuityService(
        store=store,
        index=index,
        subject_id="user_2",
    )
    assert one.recent_turns(
        session_id="shared",
        before_turn=2,
        limit=5,
    )[0]["user"]["text"] == "user one"
    assert two.recent_turns(
        session_id="shared",
        before_turn=2,
        limit=5,
    )[0]["user"]["text"] == "user two"


def test_runtime_generates_round_summary_then_restart_restores_it_from_world(tmp_path):
    store, index = _world(tmp_path)
    model_cockpits = []

    def model(snapshot):
        model_cockpits.append(snapshot.cockpit)
        return ModelDirective(response="ok")

    summary_requests = []

    def summarize(request):
        summary_requests.append(request)
        texts = [item.text for item in request.sources if item.role == "user"]
        return " | ".join(texts)

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
        round_summary_handler=summarize,
        recent_turn_limit=1,
        summary_chunk_turns=2,
    )
    for turn in range(1, 4):
        result = runtime.run_turn(
            session_id="restartable",
            turn_index=turn,
            user_input=f"question-{turn}",
            current_topic=None,
            occurred_at=NOW + timedelta(minutes=turn),
        )

    assert len(result.continuity_summary_commits) == 1
    assert result.continuity_summary_error is None
    assert len(summary_requests) == 1
    assert summary_requests[0].turn_start == 1
    assert summary_requests[0].turn_end == 2

    # New runtime instance: no in-memory rolling state is carried over.
    restarted_cockpits = []

    def restarted_model(snapshot):
        restarted_cockpits.append(snapshot.cockpit)
        return ModelDirective(response="after restart")

    restarted = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=restarted_model,
        round_summary_handler=summarize,
        recent_turn_limit=1,
        summary_chunk_turns=2,
    )
    restarted.run_turn(
        session_id="restartable",
        turn_index=4,
        user_input="what did we discuss?",
        current_topic=None,
        occurred_at=NOW + timedelta(minutes=4),
    )

    cockpit = restarted_cockpits[-1]
    assert [turn["turn_index"] for turn in cockpit["recent_turns"]] == [3]
    assert len(cockpit["conversation_summaries"]) == 1
    summary = cockpit["conversation_summaries"][0]
    assert summary["turn_start"] == 1
    assert summary["turn_end"] == 2
    assert summary["raw_drill_down_available"] is True


def test_runtime_model_can_drill_from_summary_to_exact_raw_dialogue(tmp_path):
    store, index = _world(tmp_path)

    def simple_model(snapshot):
        return ModelDirective(response="seed")

    def summarize(request):
        return "older discussion summary"

    seed_runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=simple_model,
        round_summary_handler=summarize,
        recent_turn_limit=1,
        summary_chunk_turns=2,
    )
    for turn in range(1, 4):
        seed_runtime.run_turn(
            session_id="drill",
            turn_index=turn,
            user_input=f"detail-{turn}",
            current_topic=None,
            occurred_at=NOW + timedelta(minutes=turn),
        )

    def drill_model(snapshot):
        history = snapshot.capability_history
        summaries = snapshot.cockpit["conversation_summaries"]
        assert len(summaries) == 1
        if not history:
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="drill_down_conversation",
                        arguments={
                            "summary_id": summaries[0]["object_ref"]["object_id"],
                            "revision": summaries[0]["object_ref"]["revision"],
                        },
                    ),
                )
            )
        data = history[-1].data
        assert [(x["turn_index"], x["role"], x["text"]) for x in data] == [
            (1, "user", "detail-1"),
            (1, "assistant", "seed"),
            (2, "user", "detail-2"),
            (2, "assistant", "seed"),
        ]
        return ModelDirective(response="I checked the exact raw dialogue.")

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=drill_model,
        round_summary_handler=summarize,
        recent_turn_limit=1,
        summary_chunk_turns=2,
    )
    result = runtime.run_turn(
        session_id="drill",
        turn_index=4,
        user_input="quote the exact older detail",
        current_topic=None,
        occurred_at=NOW + timedelta(minutes=4),
    )

    assert [item.name for item in result.runtime.capability_history] == [
        "drill_down_conversation"
    ]
    assert result.runtime.response == "I checked the exact raw dialogue."


def test_runtime_rejects_external_recent_turn_injection(tmp_path):
    store, index = _world(tmp_path)

    def model(snapshot):
        return ModelDirective(response="unused")

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
    )
    with pytest.raises(ValueError, match="derives recent_turns from WorldStore"):
        runtime.run_turn(
            session_id="s1",
            turn_index=1,
            user_input="hello",
            current_topic=None,
            occurred_at=NOW,
            recent_turns=({"role": "user", "text": "forged history"},),
        )


def test_new_session_does_not_auto_load_other_session_round_summaries(tmp_path):
    store, index = _world(tmp_path)
    _seed_turns(store, session_id="old", count=3, prefix="old")
    service = ConversationContinuityService(store=store, index=index)
    request = service.prepare_next_round_summary(
        session_id="old",
        before_turn=4,
        recent_turn_limit=1,
        summary_chunk_turns=2,
    )
    assert request is not None
    service.commit_round_summary(
        request,
        content="old session summary",
        generated_at=NOW + timedelta(hours=1),
    )

    new_snapshot = service.snapshot(
        session_id="new",
        before_turn=1,
        recent_turn_limit=4,
        summary_chunk_turns=2,
    )
    assert new_snapshot.recent_turns == ()
    assert new_snapshot.round_summaries == ()
    assert new_snapshot.pending_summary is None
