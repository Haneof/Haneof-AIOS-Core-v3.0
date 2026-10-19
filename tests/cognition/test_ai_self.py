from datetime import datetime, timedelta, timezone
import pytest

from aios_core.cognition.ai_self import (
    AISelfMindTracker,
    PromiseStatus,
    SymbioticPosture,
)
from aios_core.contracts.models import ObjectRef
from aios_core.storage.sqlite_store import SQLiteWorldStore

NOW = datetime(2026, 10, 19, 10, 0, tzinfo=timezone.utc)


def test_record_promise_and_active_liabilities(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    tracker = AISelfMindTracker(store=store)

    receipt = tracker.record_promise(
        description="明天早上7点提醒您空腹服药",
        due_time=NOW + timedelta(hours=21),
        committed_at=NOW,
    )

    assert receipt.revision == 1
    assert receipt.status == PromiseStatus.PROMISED
    assert "空腹服药" in receipt.description

    active = tracker.get_active_promises()
    assert len(active) == 1
    assert active[0].status == PromiseStatus.PROMISED
    assert active[0].red_line_offset_receipt == "DEBIT_LIABILITY"


def test_fulfill_promise_with_red_line_offset(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    tracker = AISelfMindTracker(store=store)

    p = tracker.record_promise(
        description="下午3点整理好项目周报",
        due_time=NOW + timedelta(hours=5),
        committed_at=NOW,
    )

    # Fulfill with red-line credit offset
    fulfilled = tracker.fulfill_promise(
        promise_id=p.promise_id,
        fulfilment_note="已于 14:50 提前交付周报",
        fulfilled_at=NOW + timedelta(hours=4, minutes=50),
    )

    assert fulfilled.revision == 2
    assert fulfilled.status == PromiseStatus.FULFILLED

    # Active liabilities cleared
    active = tracker.get_active_promises()
    assert len(active) == 0

    all_p = tracker.get_all_promises()
    assert len(all_p) == 1
    assert all_p[0].status == PromiseStatus.FULFILLED
    assert all_p[0].red_line_offset_receipt == "CREDIT_RED_LINE_OFFSET"


def test_cancel_promise_offset(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    tracker = AISelfMindTracker(store=store)

    p = tracker.record_promise(
        description="今晚预约羽毛球馆",
        committed_at=NOW,
    )

    cancelled = tracker.cancel_promise(
        promise_id=p.promise_id,
        cancellation_reason="用户临时出差，取消预订要求",
        cancelled_at=NOW + timedelta(hours=2),
    )

    assert cancelled.revision == 2
    assert cancelled.status == PromiseStatus.CANCELLED

    active = tracker.get_active_promises()
    assert len(active) == 0


def test_rapport_and_posture_evaluation(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    tracker = AISelfMindTracker(store=store)

    # Initial state: no promises
    initial_rapport = tracker.evaluate_rapport()
    assert initial_rapport.rapport_score == 0.5
    assert initial_rapport.current_posture == SymbioticPosture.OLD_FRIEND

    # Fulfill 3 promises sequentially
    for i in range(1, 4):
        rec = tracker.record_promise(
            description=f"承诺事项 {i}",
            committed_at=NOW + timedelta(hours=i),
        )
        tracker.fulfill_promise(
            promise_id=rec.promise_id,
            fulfilled_at=NOW + timedelta(hours=i, minutes=30),
        )

    high_rapport = tracker.evaluate_rapport()
    # 0.5 + 3 * 0.1 = 0.8 >= 0.75 -> COMRADE
    assert high_rapport.rapport_score >= 0.75
    assert high_rapport.current_posture == SymbioticPosture.COMRADE
    assert "平等战友" in high_rapport.summary

    # Export mind summary for ModelContextBundle
    summary = tracker.get_mind_summary()
    assert summary["posture"] == SymbioticPosture.COMRADE.value
    assert summary["rapport_score"] >= 0.75
    assert len(summary["ethical_invariants"]) == 4
    assert "铁律二" in summary["ethical_invariants"][1]
