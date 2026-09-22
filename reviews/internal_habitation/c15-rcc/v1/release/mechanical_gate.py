#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from contextlib import redirect_stdout
from datetime import datetime
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

RELEASE_DIR = Path(__file__).resolve().parent
ROOT = RELEASE_DIR.parent
sys.path.insert(0, str(RELEASE_DIR))

from bindings import FIXTURE_SHA256, PHASE_RANGES, load_canonical_adapter, load_mechanical_adapter, load_release_operator


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


def _state(path: Path):
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


def _is_user_conversation(event):
    return (
        event["dimension"] == "dim:conversation"
        and event["source_kind"] == "conversation"
        and event["source_class"] == "USER"
        and event["modality"] == "text"
    )


def _schema_contract_valid(schema, fixture):
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["type"] == "object" and schema["additionalProperties"] is False
    required = set(schema["required"])
    assert required == {
        "fixture_version",
        "schema_version",
        "release_contract_version",
        "timezone",
        "subject_id",
        "events",
    }
    props = schema["properties"]
    for key in ("fixture_version", "schema_version", "release_contract_version", "timezone", "subject_id"):
        assert fixture[key] == props[key]["const"]
    events_schema = props["events"]
    assert events_schema["minItems"] <= len(fixture["events"]) <= events_schema["maxItems"]
    item = events_schema["items"]
    allowed_keys = set(item["properties"])
    required_event = set(item["required"])
    for event in fixture["events"]:
        assert set(event) == allowed_keys == required_event
        assert event["phase"] in item["properties"]["phase"]["enum"]
        assert event["sequence"] >= item["properties"]["sequence"]["minimum"]
        assert event["event_id"].startswith("c15rcc-") and len(event["event_id"]) == len("c15rcc-000")
        datetime.fromisoformat(event["occurred_at"])
        assert event["dimension"].startswith("dim:")
        assert event["source_class"] in item["properties"]["source_class"]["enum"]
        for key in ("source_kind", "modality", "resident_visible_payload"):
            assert isinstance(event[key], str) and event[key].strip()


def _ingest_current(mechanical, canonical, world, event, *, session_id, turn_index):
    if _is_user_conversation(event):
        return canonical.ingest_canonical_conversation(
            world,
            event,
            session_id=session_id,
            turn_index=turn_index,
        )
    return mechanical.ingest_projection(world, event)


def main() -> int:
    op = load_release_operator()
    mechanical = load_mechanical_adapter()
    canonical = load_canonical_adapter()
    fixture, manifest, events = op._load_bundle()
    checks = []

    schema = json.loads((RELEASE_DIR / "event_schema.json").read_text(encoding="utf-8"))
    _schema_contract_valid(schema, fixture)
    checks.append("fixture-json-schema-contract-valid")

    digest = "sha256:" + hashlib.sha256(op.FIXTURE_PATH.read_bytes()).hexdigest()
    assert digest == FIXTURE_SHA256 == manifest["fixture_sha256"]
    checks.append("fixture-sha256-fixed")

    assert len(events) == manifest["event_count"] == 30
    assert (manifest["phase_a_count"], manifest["phase_b_count"], manifest["phase_c_count"]) == (13, 9, 8)
    checks.append("event-count-fixed")

    assert [event["sequence"] for event in events] == list(range(1, 31))
    assert len({event["event_id"] for event in events}) == 30
    checks.append("cursor-strictly-monotonic")

    times = [datetime.fromisoformat(event["occurred_at"]) for event in events]
    assert all(right > left for left, right in zip(times, times[1:]))
    checks.append("timestamps-strictly-monotonic")

    assert all(event["phase"] == "A" for event in events[:13])
    assert all(event["phase"] == "B" for event in events[13:22])
    assert all(event["phase"] == "C" for event in events[22:])
    assert manifest["handoffs"]["a_to_b"]["phase_a_final_cursor"] == 13
    assert manifest["handoffs"]["a_to_b"]["phase_b_first_cursor"] == 14
    assert manifest["handoffs"]["b_to_c"]["phase_b_final_cursor"] == 22
    assert manifest["handoffs"]["b_to_c"]["phase_c_first_cursor"] == 23
    checks.append("abc-boundaries-valid")

    visible_blob = "\n".join(event["resident_visible_payload"].lower() for event in events)
    forbidden_visible = (
        "expected claim",
        "expected domain",
        "expected capability",
        "expected confidence",
        "expected revision",
        "evaluator label",
        "user understanding test",
        "calibration test",
        "should revise",
        "negative control",
        "semantic_goal",
        "expected_axis",
        "r1",
        "r2",
        "r3",
        "r4",
        "r5",
        "r6",
        "r7",
        "r8",
        "r9",
    )
    assert not any(token in visible_blob for token in forbidden_visible)
    checks.append("resident-visible-no-oracle-labels")

    attest = manifest["replacement_model_attestation"]
    assert attest["required_for_r6"] is True
    assert attest["execution_attestation_ref"] is None
    assert attest["trusted_model_identity_artifact"] is None
    assert attest["resident_may_write"] is False
    assert attest["fixture_may_assert_verified"] is False
    checks.append("absent-model-attestation-not-verified")

    a_contract = (ROOT / "resident" / "RESIDENT_A_RUN_CONTRACT.md").read_text(encoding="utf-8")
    b_contract = (ROOT / "resident" / "RESIDENT_B_RUN_CONTRACT.md").read_text(encoding="utf-8")
    c_contract = (ROOT / "resident" / "RESIDENT_C_RUN_CONTRACT.md").read_text(encoding="utf-8")
    notes = (ROOT / "evaluator" / "EVALUATOR_ONLY_design_notes.md").read_text(encoding="utf-8")
    assert notes.startswith("# EVALUATOR ONLY")
    assert "Phase B" not in a_contract and "Phase C" not in a_contract
    assert "cursor 14" not in a_contract and "cursor 23" not in a_contract
    assert "beyond 13" in a_contract
    checks.append("resident-a-contract-cannot-reveal-later-phases")

    assert "transcript" in b_contract.lower()
    assert "must not receive" in b_contract.lower()
    assert "Phase C" not in b_contract and "cursor 23" not in b_contract
    assert "beyond 22" in b_contract
    checks.append("resident-b-no-prior-transcript-or-future-phase")

    assert "Resident A/B chat transcripts" in c_contract
    assert "trusted execution platform" in c_contract
    assert "do not write, edit, fabricate, infer, or self-report" in c_contract.lower()
    checks.append("resident-c-no-transcript-and-external-attestation-only")

    for contract in (a_contract, b_contract, c_contract):
        assert "reviews/internal_habitation/c15-rcc/v1/evaluator/**" in contract
        assert "Do not open" in contract
    checks.append("evaluator-only-not-resident-accessible")

    with TemporaryDirectory(prefix="c15-rcc-gate-") as tmp:
        tmp_path = Path(tmp)
        state = tmp_path / "release_state.json"
        world = tmp_path / "world.db"

        init_a = _call(op.cmd_init, phase="A", state=str(state))
        assert init_a["next_sequence"] == 1
        checks.append("phase-a-init")

        _expect_fail(
            "wrong-phase-b-init-before-a-handoff-fails",
            lambda: _call(op.cmd_init, phase="B", state=str(state)),
            op.ReleaseError,
            checks,
        )
        _expect_fail(
            "wrong-phase-c-init-before-b-handoff-fails",
            lambda: _call(op.cmd_init, phase="C", state=str(state)),
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
        assert set(first) == set(op.VISIBLE_KEYS)
        assert "phase" not in first
        assert _state(state)["next_sequence"] == 1
        _expect_fail(
            "duplicate-reveal-fails-closed",
            lambda: _call(op.cmd_reveal, phase="A", state=str(state)),
            op.ReleaseError,
            checks,
        )
        assert _state(state)["next_sequence"] == 1

        _expect_fail(
            "generic-user-conversation-ingest-fails",
            lambda: mechanical.ingest_projection(world, first),
            mechanical.IngestAdapterError,
            checks,
        )
        first_receipt = canonical.ingest_canonical_conversation(
            world,
            first,
            session_id="c15-gate-a",
            turn_index=1,
        )

        _expect_fail(
            "wrong-cursor-ack-fails",
            lambda: _call(
                op.cmd_ack,
                phase="A",
                state=str(state),
                world_db=str(world),
                sequence=2,
                event_id=first["event_id"],
                ingest_ref=first_receipt["ingest_ref"],
                conversation_session_id="c15-gate-a",
                conversation_turn_index=1,
            ),
            op.ReleaseError,
            checks,
        )
        _expect_fail(
            "wrong-canonical-session-ack-fails",
            lambda: _ack(
                op,
                phase="A",
                state=state,
                world=world,
                event=events[0],
                ingest_ref=first_receipt["ingest_ref"],
                session_id="wrong-session",
                turn_index=1,
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
                session_id="c15-gate-a",
                turn_index=1,
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
            session_id="c15-gate-a",
            turn_index=1,
        )
        checks.append("durable-ack-required-and-advances")

        _expect_fail(
            "duplicate-ack-fails",
            lambda: _ack(
                op,
                phase="A",
                state=state,
                world=world,
                event=events[0],
                ingest_ref=first_receipt["ingest_ref"],
                session_id="c15-gate-a",
                turn_index=1,
            ),
            op.ReleaseError,
            checks,
        )

        turn_by_phase = {"A": 2, "B": 1, "C": 1}

        while _state(state)["next_sequence"] <= 13:
            event = _call(op.cmd_reveal, phase="A", state=str(state))
            phase = "A"
            if event["sequence"] == 2:
                receipt = _ingest_current(
                    mechanical, canonical, world, event,
                    session_id="c15-gate-a", turn_index=turn_by_phase[phase],
                )
                wrong_id = events[2]["event_id"]
                _expect_fail(
                    "skip-reorder-event-id-fails",
                    lambda e=event, r=receipt, wid=wrong_id: _call(
                        op.cmd_ack,
                        phase="A",
                        state=str(state),
                        world_db=str(world),
                        sequence=e["sequence"],
                        event_id=wid,
                        ingest_ref=r["ingest_ref"],
                        conversation_session_id=None,
                        conversation_turn_index=None,
                    ),
                    op.ReleaseError,
                    checks,
                )
            else:
                receipt = _ingest_current(
                    mechanical, canonical, world, event,
                    session_id="c15-gate-a", turn_index=turn_by_phase[phase],
                )
            if _is_user_conversation(event):
                _ack(
                    op, phase=phase, state=state, world=world, event=event,
                    ingest_ref=receipt["ingest_ref"], session_id="c15-gate-a",
                    turn_index=turn_by_phase[phase],
                )
                turn_by_phase[phase] += 1
            else:
                _ack(op, phase=phase, state=state, world=world, event=event, ingest_ref=receipt["ingest_ref"])

        assert _state(state)["next_sequence"] == 14
        _expect_fail(
            "phase-a-future-reveal-fails",
            lambda: _call(op.cmd_reveal, phase="A", state=str(state)),
            op.ReleaseError,
            checks,
        )
        _expect_fail(
            "phase-c-init-at-a-b-boundary-fails",
            lambda: _call(op.cmd_init, phase="C", state=str(state)),
            op.ReleaseError,
            checks,
        )

        init_b = _call(op.cmd_init, phase="B", state=str(state))
        assert init_b["next_sequence"] == 14
        checks.append("phase-b-init-exact-boundary")

        _expect_fail(
            "phase-b-cannot-request-a-fails",
            lambda: _call(op.cmd_reveal, phase="A", state=str(state)),
            op.ReleaseError,
            checks,
        )

        while _state(state)["next_sequence"] <= 22:
            event = _call(op.cmd_reveal, phase="B", state=str(state))
            receipt = _ingest_current(
                mechanical, canonical, world, event,
                session_id="c15-gate-b", turn_index=turn_by_phase["B"],
            )
            if _is_user_conversation(event):
                _ack(
                    op, phase="B", state=state, world=world, event=event,
                    ingest_ref=receipt["ingest_ref"], session_id="c15-gate-b",
                    turn_index=turn_by_phase["B"],
                )
                turn_by_phase["B"] += 1
            else:
                _ack(op, phase="B", state=state, world=world, event=event, ingest_ref=receipt["ingest_ref"])

        assert _state(state)["next_sequence"] == 23
        _expect_fail(
            "phase-b-future-reveal-fails",
            lambda: _call(op.cmd_reveal, phase="B", state=str(state)),
            op.ReleaseError,
            checks,
        )

        init_c = _call(op.cmd_init, phase="C", state=str(state))
        assert init_c["next_sequence"] == 23
        checks.append("phase-c-init-exact-boundary")

        _expect_fail(
            "phase-c-cannot-request-b-fails",
            lambda: _call(op.cmd_reveal, phase="B", state=str(state)),
            op.ReleaseError,
            checks,
        )

        while _state(state)["next_sequence"] <= 30:
            event = _call(op.cmd_reveal, phase="C", state=str(state))
            receipt = _ingest_current(
                mechanical, canonical, world, event,
                session_id="c15-gate-c", turn_index=turn_by_phase["C"],
            )
            if _is_user_conversation(event):
                _ack(
                    op, phase="C", state=state, world=world, event=event,
                    ingest_ref=receipt["ingest_ref"], session_id="c15-gate-c",
                    turn_index=turn_by_phase["C"],
                )
                turn_by_phase["C"] += 1
            else:
                _ack(op, phase="C", state=state, world=world, event=event, ingest_ref=receipt["ingest_ref"])

        final_state = _state(state)
        assert final_state["last_acked_sequence"] == 30
        assert final_state["next_sequence"] == 31
        assert len(final_state["receipts"]) == 30
        checks.append("all-30-events-durable-acked")

        op._verify_prior_receipt_chain_in_world(
            world_db=str(world),
            state=final_state,
            events=events,
            fixture=fixture,
            manifest=manifest,
        )
        checks.append("full-receipt-chain-world-reverified")

        _expect_fail(
            "release-after-final-cursor-fails",
            lambda: _call(op.cmd_reveal, phase="C", state=str(state)),
            op.ReleaseError,
            checks,
        )

    assert PHASE_RANGES == {"A": (1, 13), "B": (14, 22), "C": (23, 30)}
    checks.append("fixed-phase-ranges")

    print(
        "C15 RCC fixture mechanical gate: PASS "
        f"({len(checks)} checks)\n- " + "\n- ".join(checks)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
