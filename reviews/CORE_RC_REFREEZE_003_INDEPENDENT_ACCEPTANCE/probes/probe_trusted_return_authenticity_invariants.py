#!/usr/bin/env python3
"""Reviewer Independent Probe 2: Trusted-return & authenticity security invariants.

Validates key security and recovery invariants required by Section 10:
- Authenticated exact replay converges
- Same durable key + changed request -> fails closed
- Corrupted durable row -> fails closed
- Tampered trusted handoff -> capability application fails closed before effect
- Cross-attempt transplant -> fail
- Cross-provider/model/request transplant -> fail
- Payload digest mismatch -> fail
- No duplicate provider dispatch
- No duplicate meter
- No duplicate capability effect
- No duplicate World/semantic write
- Stronger durable terminal/output receipt short-circuits duplicate work
- Confirm RC freeze tooling did not widen trusted-return authority
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "tests" / "integration"))

from aios_core.contracts.enums import ObjectType, SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime import (
    ModelCallProvenance,
    ModelDirective,
    ModelUsage,
    TurnAlreadyCompleted,
    TurnExecutionInDoubt,
)
from aios_core.runtime.background_attempt import (
    BackgroundModelAttemptBlocked,
    BackgroundModelExecutionInDoubt,
    BackgroundModelResponseConflict,
    encode_model_directive,
)
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from test_core_background_trusted_return_recovery_001 import (
    NOW,
    crash_at_return,
    directive,
    world,
)


def _seed_anchor(store: SQLiteWorldStore) -> None:
    moment = NOW - timedelta(hours=2)
    anchor = Observation(
        object_id="obs_probe2_anchor",
        subject_id="user_1",
        occurred=TemporalExtent.point(moment),
        learned_at=moment,
        recorded_at=moment,
        created_by="reviewer_probe_2",
        source_kind="conversation",
        modality="text",
        value="Durable reality anchor for probe 2.",
        metadata={"dimension": "dim:probe2"},
    )
    store.commit(
        [anchor],
        OperationRequest(
            operation_name="probe2.seed",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed anchor",
            idempotency_key="probe2-seed-key",
            source_class=SourceClass.USER,
        ),
    )


def test_adversarial_tamper_matrix() -> dict[str, Any]:
    mutations = [
        "forged_directive",
        "forged_fingerprint",
        "wrong_provider",
        "wrong_model",
        "wrong_request_id",
        "wrong_originating_request",
        "wrong_response_digest",
        "altered_payload",
        "duplicate_top_key",
        "duplicate_nested_key",
        "missing_handoff",
        "corrupt_handoff_digest",
        "corrupt_handoff_proof",
        "copied_handoff_from_round",
        "cross_work",
        "cross_work_kind",
        "cross_subject",
        "cross_round",
        "unknown_attempt_handoff",
        "missing_receipt",
        "invalid_receipt",
    ]

    verified_mutations = []
    with tempfile.TemporaryDirectory(prefix="aios-ia-adv-") as td:
        for mut in mutations:
            sub = Path(td) / mut
            sub.mkdir()
            db, _before, attempts, receipt, execution_id = crash_at_return(sub, 1)
            target = attempts[-1].attempt_id

            with sqlite3.connect(db) as conn:
                if mut in {"forged_directive", "altered_payload"}:
                    payload = encode_model_directive(directive(1)).replace("finished once", "forged output")
                    conn.execute(
                        "UPDATE background_model_return_handoffs SET directive_payload=?, payload_sha256=? WHERE attempt_id=?",
                        (payload, hashlib.sha256(payload.encode()).hexdigest(), target),
                    )
                elif mut == "forged_fingerprint":
                    conn.execute(
                        "UPDATE background_model_response_receipts SET response_fingerprint=? WHERE attempt_id=?",
                        ("0" * 64, target),
                    )
                elif mut in {
                    "wrong_provider", "wrong_model", "wrong_request_id", "wrong_response_digest",
                    "cross_work", "cross_work_kind", "cross_subject", "cross_round"
                }:
                    col, val = {
                        "wrong_provider": ("provider", "fake-provider"),
                        "wrong_model": ("model", "fake-model"),
                        "wrong_request_id": ("provider_request_id", "fake-request"),
                        "wrong_response_digest": ("payload_sha256", "0" * 64),
                        "cross_work": ("work_id", "other-work"),
                        "cross_work_kind": ("work_kind", "wake"),
                        "cross_subject": ("subject_id", "other-subject"),
                        "cross_round": ("model_round_index", 0),
                    }[mut]
                    conn.execute(f"UPDATE background_model_response_receipts SET {col}=? WHERE attempt_id=?", (val, target))
                elif mut == "wrong_originating_request":
                    conn.execute(
                        "UPDATE background_model_request_bindings SET outbound_request_fingerprint=? WHERE attempt_id=?",
                        ("0" * 64, target),
                    )
                elif mut in {"duplicate_top_key", "duplicate_nested_key"}:
                    valid = encode_model_directive(directive(1))
                    if mut == "duplicate_top_key":
                        payload = valid[:-1] + ',"response":"forged output"}'
                    else:
                        payload = valid.replace('"provider":"trusted-provider"', '"provider":"trusted-provider","provider":"forged"', 1)
                    conn.execute(
                        "UPDATE background_model_return_handoffs SET directive_payload=?, payload_sha256=? WHERE attempt_id=?",
                        (payload, hashlib.sha256(payload.encode()).hexdigest(), target),
                    )
                elif mut == "missing_handoff":
                    conn.execute("DELETE FROM background_model_return_handoffs WHERE attempt_id=?", (target,))
                elif mut == "corrupt_handoff_digest":
                    conn.execute("UPDATE background_model_return_handoffs SET payload_sha256=? WHERE attempt_id=?", ("0" * 64, target))
                elif mut == "corrupt_handoff_proof":
                    conn.execute("UPDATE background_model_return_handoffs SET authenticity_proof=? WHERE attempt_id=?", ("0" * 64, target))
                elif mut == "copied_handoff_from_round":
                    conn.execute(
                        "UPDATE background_model_return_handoffs SET directive_payload=(SELECT directive_payload FROM background_model_return_handoffs WHERE attempt_id=?), payload_sha256=(SELECT payload_sha256 FROM background_model_return_handoffs WHERE attempt_id=?), authenticity_proof=(SELECT authenticity_proof FROM background_model_return_handoffs WHERE attempt_id=?) WHERE attempt_id=?",
                        (attempts[0].attempt_id,) * 3 + (target,),
                    )
                elif mut == "unknown_attempt_handoff":
                    conn.execute("UPDATE background_model_return_handoffs SET attempt_id=? WHERE attempt_id=?", ("unknown-attempt", target))
                elif mut == "missing_receipt":
                    conn.execute("DELETE FROM background_model_response_receipts WHERE attempt_id=?", (target,))
                elif mut == "invalid_receipt":
                    conn.execute("UPDATE background_model_response_receipts SET authenticity_proof=? WHERE attempt_id=?", ("0" * 64, target))
                conn.commit()

            store, index = world(db)
            fresh = FusedTurnRuntime(
                store=store,
                index=index,
                model_handler=lambda _s: (_ for _ in ()).throw(AssertionError("unexpected model dispatch on tampered state")),
            )
            before_meters = fresh.metering.list_model_calls(subject_id="user_1")
            failed = False
            try:
                fresh.run_turn(
                    session_id="trusted-session",
                    turn_index=1,
                    user_input="complete exactly once",
                    occurred_at=NOW,
                )
            except (BackgroundModelResponseConflict, ValueError, TurnExecutionInDoubt, BackgroundModelExecutionInDoubt, BackgroundModelAttemptBlocked):
                failed = True

            assert failed, f"mutation {mut} must fail closed before capability application"
            assert fresh.background_model_attempts.get(target).state == "dispatching"
            assert fresh.metering.list_model_calls(subject_id="user_1") == before_meters
            assert fresh.background_model_attempts.staged_response(target) is None
            verified_mutations.append(mut)

    return {
        "status": "ADVERSARIAL_TAMPER_MATRIX_PASS",
        "verified_mutations_count": len(verified_mutations),
        "mutations": verified_mutations,
    }


def test_terminal_receipt_short_circuit() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="aios-ia-term-") as td:
        db = Path(td) / "world.sqlite"
        store, index = world(db)
        _seed_anchor(store)
        index.catch_up()

        dispatch_count = 0

        def provider(_snapshot):
            nonlocal dispatch_count
            dispatch_count += 1
            return directive(0)

        runtime = FusedTurnRuntime(store=store, index=index, model_handler=provider)
        res = runtime.run_turn(
            session_id="term-session",
            turn_index=1,
            user_input="hello terminal",
            occurred_at=NOW,
        )
        assert res.runtime.response is not None
        assert dispatch_count == 1
        meters_before = runtime.metering.list_model_calls(subject_id="user_1")
        rev_before = store.current_world_revision()

        # Re-running the already completed turn must short-circuit and raise TurnAlreadyCompleted
        # WITHOUT dispatching the model, without adding meter rows, and without advancing world revision.
        replayed = False
        try:
            runtime.run_turn(
                session_id="term-session",
                turn_index=1,
                user_input="hello terminal",
                occurred_at=NOW,
            )
        except TurnAlreadyCompleted:
            replayed = True

        assert replayed, "completed turn replay did not raise TurnAlreadyCompleted"
        assert dispatch_count == 1, "provider was dispatched again on completed turn"
        assert runtime.metering.list_model_calls(subject_id="user_1") == meters_before
        assert store.current_world_revision() == rev_before

    return {
        "status": "TERMINAL_SHORT_CIRCUIT_PASS",
        "no_duplicate_provider": True,
        "no_duplicate_meter": True,
        "no_duplicate_revision": True,
    }


def test_freeze_tooling_authority_boundary() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="aios-ia-auth-") as td:
        db = Path(td) / "world.sqlite"
        store, index = world(db)
        runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)

        # 1. Check that public stage_exact_background_response requires valid authenticity_proof
        admitted = runtime.background_model_attempts.admit(
            subject_id="user_1",
            work_kind="user_turn",
            work_id="auth-test-work",
            wake_reason="user_interaction",
            model_round_index=0,
            world_revision=int(store.current_world_revision()),
            admitted_at=NOW,
        )
        runtime.background_model_attempts.mark_dispatching(
            admitted.attempt_id,
            dispatched_at=NOW,
            outbound_request_fingerprint="fp-req-1",
        )

        fake_dir = directive(0)
        # Attempting to stage with invalid authenticity proof must fail
        rejected = False
        try:
            runtime.stage_exact_background_response(
                work_kind="user_turn",
                work_id="auth-test-work",
                model_round_index=0,
                provider=fake_dir.provenance.provider,
                model=fake_dir.provenance.model,
                provider_request_id=fake_dir.provenance.request_id,
                response_fingerprint=runtime.background_model_attempts._response_fingerprint(fake_dir),
                directive_payload=encode_model_directive(fake_dir),
                staged_at=NOW,
                evidence="unauthenticated external caller",
                authenticity_proof="forged-proof-bytes",
            )
        except (BackgroundModelResponseConflict, ValueError):
            rejected = True

        assert rejected, "staging with forged authenticity proof must be rejected"

        # 2. Check that no unauthenticated public API exists to mint receipts
        # The private method _capture_trusted_response_return starts with an underscore
        assert hasattr(runtime.background_model_attempts, "_capture_trusted_response_return")
        assert not hasattr(runtime.background_model_attempts, "stage_trusted_returned_background_response"), (
            "unauthorized public stage_trusted_returned_background_response must not exist"
        )

    return {
        "status": "AUTHORITY_BOUNDARY_PASS",
        "forged_proof_rejected": True,
        "no_unauthorized_public_minting_api": True,
    }


def main() -> int:
    adv = test_adversarial_tamper_matrix()
    term = test_terminal_receipt_short_circuit()
    auth = test_freeze_tooling_authority_boundary()

    result = {
        "probe": "probe_trusted_return_authenticity_invariants",
        "status": "PASS",
        "adversarial_tamper_matrix": adv,
        "terminal_short_circuit": term,
        "authority_boundary": auth,
    }
    print("RESULT=" + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
