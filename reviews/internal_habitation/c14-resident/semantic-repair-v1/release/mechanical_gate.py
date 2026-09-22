#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from contextlib import redirect_stdout
from datetime import datetime
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory

RELEASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(RELEASE_DIR))

from bindings import FIXTURE_SHA256, load_canonical_adapter, load_mechanical_adapter, load_release_operator


def _call(fn, **kwargs):
    out = StringIO()
    with redirect_stdout(out):
        fn(SimpleNamespace(**kwargs))
    text = out.getvalue().strip()
    return json.loads(text.splitlines()[-1]) if text else None


def _expect_fail(label, fn, exc_type, checks):
    try:
        fn()
    except exc_type:
        checks.append(label)
        return
    raise AssertionError(f"{label}: expected fail-closed rejection")


def _read_state(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _ack(op, *, phase, state, world, event, ingest_ref, session_id=None, turn_index=None):
    return _call(
        op.cmd_ack,
        phase=phase,
        state=str(state),
        world_db=str(world),
        sequence=event["sequence"],
        event_id=event["event_id"],
        ingest_ref=ingest_ref,
        conversation_session_id=session_id,
        conversation_turn_index=turn_index,
    )


def main() -> int:
    op = load_release_operator()
    mechanical = load_mechanical_adapter()
    canonical = load_canonical_adapter()
    fixture, manifest, events = op._load_bundle()
    checks = []

    fixture_path = op.FIXTURE_PATH
    digest = "sha256:" + hashlib.sha256(fixture_path.read_bytes()).hexdigest()
    assert digest == FIXTURE_SHA256 == manifest["fixture_sha256"]
    checks.append("fixture-sha256-fixed")

    assert len(events) == 15
    assert manifest["event_count"] == 15
    assert manifest["phase_a_count"] == 6
    assert manifest["phase_b_count"] == 9
    checks.append("event-count-fixed")

    assert [event["sequence"] for event in events] == list(range(1, 16))
    assert len({event["event_id"] for event in events}) == 15
    checks.append("cursor-contiguous")

    times = [datetime.fromisoformat(event["occurred_at"]) for event in events]
    assert all(right > left for left, right in zip(times, times[1:]))
    checks.append("time-strictly-monotonic")

    assert all(event["phase"] == "A" for event in events[:6])
    assert all(event["phase"] == "B" for event in events[6:])
    assert manifest["handoff"]["phase_a_final_cursor"] == 6
    assert manifest["handoff"]["phase_b_first_cursor"] == 7
    checks.append("phase-boundary-6-7")

    forbidden = (
        "positive case",
        "negative case",
        "contradiction",
        "planned-vs-observed test",
        "expected cognition",
        "expected claim",
        "should revise",
        "confidence should increase",
        "evaluator note",
        "hidden truth",
        "应该 revise",
    )
    visible_blob = "\n".join(event["resident_visible_payload"].lower() for event in events)
    assert not any(term.lower() in visible_blob for term in forbidden)
    checks.append("resident-visible-no-oracle-labels")

    assert "evaluator" not in str(op.FIXTURE_PATH).lower()
    assert "evaluator" not in str(op.MANIFEST_PATH).lower()
    checks.append("evaluator-not-in-release-source")

    with TemporaryDirectory(prefix="c14-sem-repair-gate-") as tmp:
        tmp_path = Path(tmp)
        state = tmp_path / "release_state.json"
        world = tmp_path / "world.db"

        init_a = _call(op.cmd_init, phase="A", state=str(state))
        assert init_a["next_sequence"] == 1
        checks.append("phase-a-init")

        _expect_fail(
            "phase-b-before-handoff-fails",
            lambda: _call(op.cmd_init, phase="B", state=str(state)),
            op.ReleaseError,
            checks,
        )
        _expect_fail(
            "ack-before-reveal-fails",
            lambda: _ack(
                op,
                phase="A",
                state=state,
                world=world,
                event=events[0],
                ingest_ref="missing_object@1",
            ),
            op.ReleaseError,
            checks,
        )

        first = _call(op.cmd_reveal, phase="A", state=str(state))
        again = _call(op.cmd_reveal, phase="A", state=str(state))
        assert first == again
        assert set(first) == set(op.VISIBLE_KEYS)
        assert "phase" not in first
        assert _read_state(state)["next_sequence"] == 1
        checks.append("reveal-current-only-no-advance")

        first_receipt = mechanical.ingest_projection(world, first)
        _expect_fail(
            "wrong-cursor-fails",
            lambda: _call(
                op.cmd_ack,
                phase="A",
                state=str(state),
                world_db=str(world),
                sequence=2,
                event_id=first["event_id"],
                ingest_ref=first_receipt["ingest_ref"],
                conversation_session_id=None,
                conversation_turn_index=None,
            ),
            op.ReleaseError,
            checks,
        )
        _expect_fail(
            "nonexistent-ref-fails",
            lambda: _ack(
                op,
                phase="A",
                state=state,
                world=world,
                event=events[0],
                ingest_ref="missing_object@1",
            ),
            op.ReleaseError,
            checks,
        )
        _ack(
            op,
            phase="A",
            state=state,
            world=world,
            event=events[0],
            ingest_ref=first_receipt["ingest_ref"],
        )
        checks.append("durable-ack-advances")

        _expect_fail(
            "duplicate-ack-fails",
            lambda: _ack(
                op,
                phase="A",
                state=state,
                world=world,
                event=events[0],
                ingest_ref=first_receipt["ingest_ref"],
            ),
            op.ReleaseError,
            checks,
        )

        for index in range(1, 6):
            event = _call(op.cmd_reveal, phase="A", state=str(state))
            receipt = mechanical.ingest_projection(world, event)
            if event["sequence"] == 2:
                wrong_event = dict(event)
                wrong_event["event_id"] = events[2]["event_id"]
                _expect_fail(
                    "reorder-event-id-fails",
                    lambda e=wrong_event, r=receipt: _call(
                        op.cmd_ack,
                        phase="A",
                        state=str(state),
                        world_db=str(world),
                        sequence=e["sequence"],
                        event_id=e["event_id"],
                        ingest_ref=r["ingest_ref"],
                        conversation_session_id=None,
                        conversation_turn_index=None,
                    ),
                    op.ReleaseError,
                    checks,
                )
            _ack(
                op,
                phase="A",
                state=state,
                world=world,
                event=event,
                ingest_ref=receipt["ingest_ref"],
            )

        assert _read_state(state)["next_sequence"] == 7
        _expect_fail(
            "phase-a-future-cursor-7-fails",
            lambda: _call(op.cmd_reveal, phase="A", state=str(state)),
            op.ReleaseError,
            checks,
        )

        init_b = _call(op.cmd_init, phase="B", state=str(state))
        assert init_b["next_sequence"] == 7
        checks.append("phase-b-init-at-exact-boundary")

        _expect_fail(
            "phase-b-cannot-request-phase-a",
            lambda: _call(op.cmd_reveal, phase="A", state=str(state)),
            op.ReleaseError,
            checks,
        )

        canonical_seen = False
        generic_seen = False
        for _ in range(7, 16):
            event = _call(op.cmd_reveal, phase="B", state=str(state))
            if event["sequence"] == 12:
                _expect_fail(
                    "generic-user-conversation-ingest-fails",
                    lambda e=event: mechanical.ingest_projection(world, e),
                    mechanical.IngestAdapterError,
                    checks,
                )
                receipt = canonical.ingest_canonical_conversation(
                    world,
                    event,
                    session_id="c14-sem-repair-gate",
                    turn_index=1,
                )
                _expect_fail(
                    "wrong-canonical-session-ack-fails",
                    lambda e=event, r=receipt: _ack(
                        op,
                        phase="B",
                        state=state,
                        world=world,
                        event=e,
                        ingest_ref=r["ingest_ref"],
                        session_id="wrong-session",
                        turn_index=1,
                    ),
                    op.ReleaseError,
                    checks,
                )
                _ack(
                    op,
                    phase="B",
                    state=state,
                    world=world,
                    event=event,
                    ingest_ref=receipt["ingest_ref"],
                    session_id="c14-sem-repair-gate",
                    turn_index=1,
                )
                canonical_seen = True
            else:
                receipt = mechanical.ingest_projection(world, event)
                _ack(
                    op,
                    phase="B",
                    state=state,
                    world=world,
                    event=event,
                    ingest_ref=receipt["ingest_ref"],
                )
                generic_seen = True

        final_state = _read_state(state)
        assert final_state["last_acked_sequence"] == 15
        assert final_state["next_sequence"] == 16
        assert len(final_state["receipts"]) == 15
        checks.append("all-15-events-durable-acked")
        assert canonical_seen and generic_seen
        checks.append("canonical-and-generic-paths-exercised")

        _expect_fail(
            "release-after-final-cursor-fails",
            lambda: _call(op.cmd_reveal, phase="B", state=str(state)),
            op.ReleaseError,
            checks,
        )

        # Re-read the entire receipt chain from the supplied World.
        op._verify_prior_receipt_chain_in_world(
            world_db=str(world),
            state=final_state,
            events=events,
            fixture=fixture,
            manifest=manifest,
        )
        checks.append("receipt-chain-world-reverified")

    print(
        "C14 semantic-repair mechanical gate: PASS "
        f"({len(checks)} checks)\n- " + "\n- ".join(checks)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
