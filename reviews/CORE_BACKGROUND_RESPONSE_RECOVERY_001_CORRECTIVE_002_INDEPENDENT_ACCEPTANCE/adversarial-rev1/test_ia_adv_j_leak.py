"""IA-ADV-J: authority-secret leakage scan + private-mint trust-root boundary.

The store-private HMAC key must not appear through any public API output,
serialization, repr, exception, evidence, log, or model input surface.  The
in-process return-boundary callback is the documented trust root; this file
records its exact reachability so the acceptance report states the boundary
precisely rather than hiding it.
"""

from __future__ import annotations

from ia_helpers import (
    NOW,
    authority_secret,
    capture_return,
    crash_wake,
    directive,
    emit_wake,
    effect_snapshot,
    sql_rows,
    stage,
    wake_ref,
    world,
)

from aios_core.runtime.background_attempt import encode_model_directive
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from datetime import timedelta


def test_adv_j1_secret_never_leaks_through_public_api_or_exception_surfaces(tmp_path):
    store, index, db = world(tmp_path, "j1.db")
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal, attempt = crash_wake(runtime, key="j1")
    genuine = directive("provider-request-j1", response="secret scan bytes")
    receipt = capture_return(runtime, attempt.attempt_id, genuine)
    staged = stage(
        runtime,
        work_kind="wake",
        work_id=signal.wake_id,
        round_index=0,
        d=genuine,
        authenticity_proof=receipt.authenticity_proof,
    )
    binding = runtime.background_model_attempts.outbound_request_binding(attempt.attempt_id)

    secret = authority_secret(db)
    assert secret and len(bytes.fromhex(secret)) == 32

    surfaces = {
        "receipt-repr": repr(receipt),
        "receipt-dump": repr(receipt.model_dump()),
        "staged-repr": repr(staged),
        "staged-dump": repr(staged.model_dump()),
        "attempt-repr": repr(runtime.background_model_attempts.get(attempt.attempt_id)),
        "binding-repr": repr(binding),
        "list-work": repr(runtime.background_model_attempts.list_for_work(
            subject_id=runtime.subject_id, work_kind="wake", work_id=signal.wake_id
        )),
    }

    # Exception surfaces on tampered verification.
    try:
        stage(
            runtime,
            work_kind="wake",
            work_id=signal.wake_id,
            round_index=0,
            d=genuine,
            authenticity_proof="bgresponse_v1_" + "7" * 64,
        )
    except BaseException as exc:
        surfaces["tamper-exception"] = repr(exc) + str(exc)

    # World payload surfaces.
    from aios_core.contracts.enums import ObjectType

    world_payloads = []
    for ot in (ObjectType.WAKE, ObjectType.TASK, ObjectType.OBSERVATION):
        world_payloads.extend(store.list_payloads(object_type=ot, subject_id="user_1"))
    surfaces["world-payloads"] = repr(world_payloads)
    # Metering record surfaces.
    surfaces["metering"] = repr(runtime.metering.list_model_calls(subject_id="user_1"))
    # Model input surfaces: what the handler-visible snapshot carries.
    seen: list[str] = []

    def scanning_handler(snapshot):
        seen.append(repr(snapshot))
        try:
            seen.append(repr(snapshot.model_dump()))
        except Exception:
            pass
        return identityless_directive("scan complete")

    from ia_helpers import bind_handler, identityless_directive

    bind_handler(runtime, scanning_handler)
    signal2 = emit_wake(runtime, key="j1-scan")
    runtime.run_wake(wake_ref=wake_ref(signal2), now=NOW + timedelta(minutes=9))
    surfaces["snapshot"] = " ".join(seen)
    assert seen, "scan handler never ran; snapshot surface unverified"

    leaks = {name: body for name, body in surfaces.items() if secret in body}
    assert leaks == {}, f"authority secret leaked through: {sorted(leaks)}"


def test_adv_j2_private_mint_reachability_is_confined_to_in_process_trust_root(tmp_path):
    """Boundary documentation probe.

    The return-boundary callback is the documented trust root: in-process code
    holding the store object can mint receipts (exactly as the production
    authenticator does).  The PUBLIC staging/recovery surface cannot.  This
    probe pins the boundary statement so the acceptance report is explicit.
    """

    store, index, _db = world(tmp_path, "j2.db")
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal, attempt = crash_wake(runtime, key="j2")

    # (1) In-process private mint works (trust root) -- expected to succeed.
    fabricated = directive("provider-request-j2", response="in-process mint")
    receipt = capture_return(runtime, attempt.attempt_id, fabricated)
    assert receipt is not None and receipt.authenticity_proof.startswith(
        "bgresponse_v1_"
    )

    # (2) Public staging surface accepts ONLY that real receipt; every other
    # caller-computable proof string is rejected (asserted across A/B probes).
    staged = stage(
        runtime,
        work_kind="wake",
        work_id=signal.wake_id,
        round_index=0,
        d=fabricated,
        authenticity_proof=receipt.authenticity_proof,
    )
    assert staged.authenticity_proof == receipt.authenticity_proof

    # (3) The public receipt reader exposes the proof (journal copying) but no
    # getter exposes the key; the key exists only in the store table.
    assert (
        runtime.background_model_attempts.response_authenticity_receipt(
            attempt.attempt_id
        ).authenticity_proof
        == receipt.authenticity_proof
    )
    assert not hasattr(runtime.background_model_attempts, "authority_key")
    assert not hasattr(type(runtime.background_model_attempts), "authority_key")


def test_adv_j3_no_signing_helper_is_reachable_without_store_connection(tmp_path):
    """A caller without a live store connection object cannot obtain any proof."""

    store, index, _db = world(tmp_path, "j3.db")
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal, attempt = crash_wake(runtime, key="j3")

    # Public methods that hand out state:
    public = {
        name
        for name in dir(runtime.background_model_attempts)
        if not name.startswith("_")
    }
    # None of them may accept proof material as a signing request.
    import inspect

    from aios_core.runtime.background_attempt import BackgroundModelAttemptStore

    for name in public:
        member = getattr(BackgroundModelAttemptStore, name)
        if callable(member):
            params = inspect.signature(member).parameters
            assert "secret" not in params and "key" not in params, (
                f"public API {name} accepts key material"
            )
