from datetime import datetime, timedelta, timezone
import pytest

from aios_core.context.active_window import ActiveRollingWindow
from aios_core.contracts.models import ObjectRef

NOW = datetime(2026, 10, 19, 10, 0, tzinfo=timezone.utc)


def test_record_turn_within_bound():
    win = ActiveRollingWindow(max_active_turns=6, max_token_budget=1500)

    for i in range(1, 4):
        turn, slid_out = win.record_turn(
            turn_index=i,
            user_text=f"用户第 {i} 句话",
            user_observation_ref=ObjectRef(object_id=f"obs_user_{i}", revision=1),
            assistant_text=f"助手第 {i} 句回复",
            assistant_observation_ref=ObjectRef(object_id=f"obs_asst_{i}", revision=1),
            occurred_at=NOW + timedelta(minutes=i),
        )
        assert turn.turn_index == i
        assert len(slid_out) == 0

    assert len(win.active_turns) == 3
    assert len(win.pending_extract_turns) == 0

    context_slice = win.get_context_slice()
    assert len(context_slice) == 3
    assert context_slice[0]["user_text"] == "用户第 1 句话"


def test_slide_out_when_turn_limit_exceeded():
    win = ActiveRollingWindow(max_active_turns=6, max_token_budget=1500)

    # Record 8 turns
    all_slid_out = []
    for i in range(1, 9):
        _, slid = win.record_turn(
            turn_index=i,
            user_text=f"问题 {i}",
            user_observation_ref=ObjectRef(object_id=f"obs_u_{i}", revision=1),
            assistant_text=f"答案 {i}",
            assistant_observation_ref=ObjectRef(object_id=f"obs_a_{i}", revision=1),
            occurred_at=NOW + timedelta(minutes=i),
        )
        all_slid_out.extend(slid)

    # Max turns is 6, so turns 1 and 2 must have slid out
    assert len(win.active_turns) == 6
    assert win.active_turns[0].turn_index == 3
    assert win.active_turns[-1].turn_index == 8

    assert len(all_slid_out) == 2
    assert all_slid_out[0].turn_index == 1
    assert all_slid_out[1].turn_index == 2

    assert len(win.pending_extract_turns) == 2

    # Acknowledge extraction
    acked = win.ack_extracted([1])
    assert acked == 1
    assert len(win.pending_extract_turns) == 1
    assert win.pending_extract_turns[0].turn_index == 2

    acked2 = win.ack_extracted([2])
    assert acked2 == 1
    assert len(win.pending_extract_turns) == 0


def test_token_budget_overflow_eviction():
    # Strict 300 token budget
    win = ActiveRollingWindow(max_active_turns=6, max_token_budget=300)

    # Turn 1: 50 tokens
    win.record_turn(
        turn_index=1,
        user_text="短问题",
        user_observation_ref=ObjectRef(object_id="obs_u_1", revision=1),
        occurred_at=NOW,
    )

    # Turn 2: Very long text (1400 chars ~ 350 tokens)
    long_text = "这是一段非常冗长的回复内容。" * 100
    _, slid_out = win.record_turn(
        turn_index=2,
        user_text="长问题",
        user_observation_ref=ObjectRef(object_id="obs_u_2", revision=1),
        assistant_text=long_text,
        assistant_observation_ref=ObjectRef(object_id="obs_a_2", revision=1),
        occurred_at=NOW + timedelta(minutes=1),
    )

    # Turn 1 must be evicted to prevent exceeding budget
    assert len(slid_out) >= 1
    assert slid_out[0].turn_index == 1
    assert len(win.active_turns) == 1
    assert win.active_turns[0].turn_index == 2


def test_pinned_revision_enforcement():
    win = ActiveRollingWindow()

    # Unpinned user observation ref raises ValueError
    with pytest.raises(ValueError, match="user_observation_ref requires pinned revision"):
        win.record_turn(
            turn_index=1,
            user_text="你好",
            user_observation_ref=ObjectRef(object_id="obs_u_1"),  # unpinned
            occurred_at=NOW,
        )
