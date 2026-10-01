#!/usr/bin/env python3
"""WINDOW 14 S3 — stale capability across a legal typed not_submitted retry with
binding rotation (task item 21 special attack).

Frozen before first execution.  Expected contract (recorded now, not revised):

S3a  a proof made under the pre-retry capability scope must NOT authenticate a
     return for the rotated binding (stale proof must fail closed);
S3b  the capability handed to the observer at the RETRIED dispatch must be able
     to authenticate that dispatch's own late return (class-A recovery must stay
     alive for legal retries).  If the capability row is never re-scoped with
     the replaced binding, the legitimate return is permanently unattachable —
     FAIL (silent recovery dead-end, no rotation/invalidation contract).
S3c  the stale capability must not mint a proof that attaches under the new
     binding either (no signing oracle across the rotation).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile

from aios_core.runtime import ModelCallProvenance, ModelDirective, ModelDispatchNotSubmitted, ModelUsage
from aios_core.runtime.background_attempt import (
    BackgroundModelAttemptStore,
    BackgroundModelResponseConflict,
    encode_model_directive,
)
from aios_core.storage.sqlite_store import SQLiteWorldStore

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)


class Observer:
    def __init__(self):
        self.handed = []

    def accept_return_capability(self, snapshot, capability):
        self.handed.append(capability)


def directive(request_id: str) -> ModelDirective:
    return ModelDirective(
        response=f"return for {request_id}",
        capability_calls=(),
        usage=ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2,
                         provider="p", model="m", request_id=request_id),
        provenance=ModelCallProvenance(provider="p", model="m", request_id=request_id),
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="w14-s3-") as d:
        db = Path(d) / "s3.db"
        store = SQLiteWorldStore(db)
        attempts = BackgroundModelAttemptStore(store)
        observer = Observer()

        # dispatch #1: request req-1, capability issued to the observer.
        att = attempts.admit(subject_id="user_1", work_kind="user_turn", work_id="s3",
                             wake_reason="user_interaction", model_round_index=0,
                             world_revision=int(store.current_world_revision()),
                             admitted_at=NOW)
        attempts.mark_dispatching(att.attempt_id, dispatched_at=NOW,
                                  outbound_request_fingerprint="req-1")
        cap1 = attempts._issue_external_return_capability(att.attempt_id, issued_at=NOW)
        observer.accept_return_capability(None, cap1)

        # accepted typed not_submitted contract (provider adapter knows req-1 never left).
        r = attempts.mark_failure(att.attempt_id, failed_at=NOW + timedelta(minutes=1),
                                  definitely_not_submitted=True,
                                  error=ModelDispatchNotSubmitted("never wrote req-1"))
        assert r.state == "not_submitted", r.state

        # legal retry of the SAME logical attempt; the new outbound request differs.
        att2 = attempts.admit(subject_id="user_1", work_kind="user_turn", work_id="s3",
                              wake_reason="user_interaction", model_round_index=0,
                              world_revision=int(store.current_world_revision()),
                              admitted_at=NOW + timedelta(minutes=2))
        attempts.mark_dispatching(att2.attempt_id, dispatched_at=NOW + timedelta(minutes=2),
                                  outbound_request_fingerprint="req-2")
        cap2 = attempts._issue_external_return_capability(att2.attempt_id,
                                                          issued_at=NOW + timedelta(minutes=2))
        observer.accept_return_capability(None, cap2)

        problems = []
        new_return = directive("req-2")

        # S3b: the retried dispatch's own real late return must attach.
        try:
            attempts.attach_late_trusted_return(
                att2.attempt_id,
                attached_at=NOW + timedelta(minutes=5),
                directive_payload=encode_model_directive(new_return),
                late_return_proof=cap2.prove_external_return(new_return),
                evidence="legitimate late return for the rotated request",
            )
            s3b = "attached"
        except Exception as exc:
            s3b = f"REFUSED: {type(exc).__name__}: {exc}"
            problems.append("S3b: retried dispatch's own return is unattachable")

        # S3c: the stale pre-retry capability must not sign anything under the
        # new binding (checked on a fresh attempt so consumption above cannot
        # mask it).
        att3 = attempts.admit(subject_id="user_1", work_kind="user_turn", work_id="s3b",
                              wake_reason="user_interaction", model_round_index=0,
                              world_revision=int(store.current_world_revision()),
                              admitted_at=NOW)
        attempts.mark_dispatching(att3.attempt_id, dispatched_at=NOW,
                                  outbound_request_fingerprint="req-A")
        stale = attempts._issue_external_return_capability(att3.attempt_id, issued_at=NOW)
        attempts.mark_failure(att3.attempt_id, failed_at=NOW,
                              definitely_not_submitted=True,
                              error=ModelDispatchNotSubmitted("never wrote req-A"))
        attempts.admit(subject_id="user_1", work_kind="user_turn", work_id="s3b",
                       wake_reason="user_interaction", model_round_index=0,
                       world_revision=int(store.current_world_revision()),
                       admitted_at=NOW + timedelta(minutes=1))
        attempts.mark_dispatching(att3.attempt_id, dispatched_at=NOW + timedelta(minutes=1),
                                  outbound_request_fingerprint="req-B")
        rotated = attempts._issue_external_return_capability(att3.attempt_id,
                                                             issued_at=NOW + timedelta(minutes=1))
        shifted = directive("req-B")
        s3a_ok = True
        try:
            attempts.attach_late_trusted_return(
                att3.attempt_id,
                attached_at=NOW + timedelta(minutes=2),
                directive_payload=encode_model_directive(shifted),
                late_return_proof=stale.prove_external_return(shifted),
                evidence="stale capability signs rotated binding",
            )
            s3a_ok = False
            problems.append("S3c: stale capability authenticated the rotated binding return")
        except (BackgroundModelResponseConflict, ValueError):
            pass
        # The rotated capability for the same attempt must also be refusable-or-attachable
        # consistently; if it is refused too, class-A is dead for this retry.
        try:
            attempts.attach_late_trusted_return(
                att3.attempt_id,
                attached_at=NOW + timedelta(minutes=3),
                directive_payload=encode_model_directive(shifted),
                late_return_proof=rotated.prove_external_return(shifted),
                evidence="current capability after rotation",
            )
            s3_rotated_current = "attached"
        except Exception as exc:
            s3_rotated_current = f"REFUSED: {type(exc).__name__}: {exc}"
            problems.append("S3: rotated-binding dispatch cannot attach its own return at all")

        print("S3 | stale capability across legal not_submitted retry with rotation")
        print("  S3a stale proof rejected:", s3a_ok)
        print("  S3b retried return outcome:", s3b)
        print("  rotated-capability outcome:", s3_rotated_current)
        print("  cap1 scope fp:", cap1.outbound_request_fingerprint,
              "cap2 scope fp:", cap2.outbound_request_fingerprint,
              "cap2 is cap1 nonce:", cap1._capability_nonce == cap2._capability_nonce)
        print("  problems:", problems)
        print("SUMMARY | failures=", len(problems))
        return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
