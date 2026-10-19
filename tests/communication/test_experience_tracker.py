from datetime import datetime, timedelta, timezone
import pytest

from aios_core.contracts.enums import SourceClass, UserReaction
from aios_core.contracts.models import ObjectRef, Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent
from aios_core.communication.experience_tracker import (
    ExperienceTracker,
    ToneStyle,
)
from aios_core.storage.sqlite_store import SQLiteWorldStore

NOW = datetime(2026, 10, 19, 10, 0, tzinfo=timezone.utc)


def _seed_user_feedback_obs(store: SQLiteWorldStore, obs_id: str, text: str) -> ObjectRef:
    obs = Observation(
        object_id=obs_id,
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="user_chat_ingest",
        source_kind="user_input",
        modality="text",
        value=text,
        metadata={"role": "user"},
    )
    op = OperationRequest(
        operation_name="test.seed_feedback",
        expected_world_revision=store.current_world_revision(),
        reason="seed user feedback observation",
        idempotency_key=f"seed_obs_{obs_id}_{store.current_world_revision()}",
        source_class=SourceClass.USER,
    )
    store.commit([obs], op)
    return ObjectRef(object_id=obs_id, revision=1)


def test_record_communication_experience_and_stats(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    tracker = ExperienceTracker(store=store)

    ev1 = _seed_user_feedback_obs(store, "obs_fb_1", "好，收到")
    ev2 = _seed_user_feedback_obs(store, "obs_fb_2", "可以，继续")
    ev3 = _seed_user_feedback_obs(store, "obs_fb_3", "太啰嗦了，烦")

    # Record 2 ACCEPTED for DIRECT style
    tracker.record_interaction_experience(
        scenario="task_status_report",
        style=ToneStyle.DIRECT.value,
        tone="concise",
        user_reaction=UserReaction.ACCEPTED,
        evidence_refs=[ev1],
        recorded_at=NOW,
    )
    tracker.record_interaction_experience(
        scenario="task_status_report",
        style=ToneStyle.DIRECT.value,
        tone="concise",
        user_reaction=UserReaction.ACCEPTED,
        evidence_refs=[ev2],
        recorded_at=NOW,
    )

    # Record 1 RESISTED for HUMOROUS style
    tracker.record_interaction_experience(
        scenario="task_status_report",
        style=ToneStyle.HUMOROUS.value,
        tone="playful",
        user_reaction=UserReaction.RESISTED,
        evidence_refs=[ev3],
        recorded_at=NOW,
    )

    stats = tracker.get_style_stats("task_status_report")
    assert len(stats) == 2

    direct_stat = next(s for s in stats if s.style == ToneStyle.DIRECT.value)
    assert direct_stat.accepted_count == 2
    assert direct_stat.resisted_count == 0
    # (2 + 1) / (2 + 2) = 3/4 = 0.75
    assert direct_stat.posterior_acceptance == 0.75

    humor_stat = next(s for s in stats if s.style == ToneStyle.HUMOROUS.value)
    assert humor_stat.accepted_count == 0
    assert humor_stat.resisted_count == 1
    # (0 + 1) / (1 + 2) = 1/3 ~ 0.333
    assert pytest.approx(humor_stat.posterior_acceptance, rel=1e-2) == 0.333


def test_get_effective_style_recommendation(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    tracker = ExperienceTracker(store=store)

    ev_ok = _seed_user_feedback_obs(store, "obs_ok", "很棒")
    ev_no = _seed_user_feedback_obs(store, "obs_no", "不要这样说")

    # Seed 3 distinct positive interactions with GENTLE
    for i in range(3):
        tracker.record_interaction_experience(
            scenario="health_reminder",
            style=ToneStyle.GENTLE.value,
            tone="caring",
            user_reaction=UserReaction.ACCEPTED,
            evidence_refs=[ev_ok],
            recorded_at=NOW + timedelta(minutes=i * 10),
        )

    # Seed 2 distinct negative interactions with FORMAL
    for i in range(2):
        tracker.record_interaction_experience(
            scenario="health_reminder",
            style=ToneStyle.FORMAL.value,
            tone="bureaucratic",
            user_reaction=UserReaction.RESISTED,
            evidence_refs=[ev_no],
            recorded_at=NOW + timedelta(hours=1, minutes=i * 10),
        )

    rec = tracker.get_effective_style("health_reminder")
    assert rec.recommended_style == ToneStyle.GENTLE.value
    assert rec.recommended_tone == "caring"
    assert rec.confidence > 0.5
    assert rec.posterior_score > 0.7

    # Cold start for unknown scenario returns defaults
    cold = tracker.get_effective_style(
        "emergency_dispatch",
        default_style=ToneStyle.DIRECT.value,
        use_fallback_priors=False,
    )
    assert cold.sample_count == 0
    assert cold.recommended_style == ToneStyle.DIRECT.value
    assert cold.is_scenario_specific is False


def test_avoidance_list_blacklisting(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    tracker = ExperienceTracker(store=store)

    ev_annoyed = _seed_user_feedback_obs(store, "obs_annoyed", "闭嘴，别烦我")

    # 2 distinct consecutive resisted events for TEASING
    for i in range(2):
        tracker.record_interaction_experience(
            scenario="focus_session",
            style=ToneStyle.TEASING.value,
            tone="ironic",
            user_reaction=UserReaction.RESISTED,
            evidence_refs=[ev_annoyed],
            recorded_at=NOW + timedelta(minutes=i * 15),
        )

    avoidance = tracker.get_avoidance_list("focus_session", min_resistance_rate=0.5, min_samples=2)
    assert len(avoidance) == 1
    assert avoidance[0].style == ToneStyle.TEASING.value
    assert avoidance[0].resistance_rate == 1.0
    assert "blacklisted" in avoidance[0].reason

    # Recommendation for focus_session will not recommend TEASING
    rec = tracker.get_effective_style("focus_session")
    assert rec.recommended_style != ToneStyle.TEASING.value


def test_assistant_output_alone_is_not_feedback(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    tracker = ExperienceTracker(store=store)

    # Seed an assistant output observation (NOT real user feedback)
    obs = Observation(
        object_id="obs_ai_output",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="conversation_ingest:assistant",
        source_kind="ai_response",
        modality="text",
        value="你好，今天天气很好",
        metadata={"role": "assistant"},
    )
    op = OperationRequest(
        operation_name="test.seed_ai_obs",
        expected_world_revision=0,
        reason="seed ai observation",
        idempotency_key="seed_ai_1",
        source_class=SourceClass.AI_COGNITION,
    )
    store.commit([obs], op)

    ai_ref = ObjectRef(object_id=obs.object_id, revision=1)
    with pytest.raises(ValueError, match="communication experience requires real user/world feedback evidence"):
        tracker.record_interaction_experience(
            scenario="greeting",
            style="gentle",
            user_reaction=UserReaction.ACCEPTED,
            evidence_refs=[ai_ref],
        )
