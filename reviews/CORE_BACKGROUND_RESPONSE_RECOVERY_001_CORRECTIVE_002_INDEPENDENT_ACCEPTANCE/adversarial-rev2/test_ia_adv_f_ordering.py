"""IA-ADV-F: trusted-return authentication must gate every downstream effect."""

from __future__ import annotations

import pytest

from ia_helpers import (
    IAProcessDeath,
    NOW,
    capture_return,
    crash_wake,
    directive,
    effect_snapshot,
    emit_wake,
    stage,
    wake_ref,
    world,
)

from aios_core.runtime.background_attempt import BackgroundModelResponseConflict
from aios_core.runtime.turn_runtime import FusedTurnRuntime


def test_adv_f1_failed_staging_leaves_no_partial_mutation(tmp_path):
    store, index, _db = world(tmp_path)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal, attempt = crash_wake(runtime, key="f1")
    genuine = directive("provider-request-f1", response="ordering bytes")
    receipt = capture_return(runtime, attempt.attempt_id, genuine)

    before = effect_snapshot(runtime, attempt)
    with pytest.raises((BackgroundModelResponseConflict, ValueError)):
        stage(
            runtime,
            work_kind="wake",
            work_id=signal.wake_id,
            round_index=0,
            d=genuine,
            authenticity_proof="bgresponse_v1_" + "9" * 64,  # invalid proof
        )
    after = effect_snapshot(runtime, attempt)
    assert after == before, "failed staging left partial durable mutation"


def test_adv_f2_authentication_failure_blocks_recorder_metering_output_and_world(tmp_path):
    """Production ordering: authenticator raises -> nothing downstream runs."""

    store, index, _db = world(tmp_path)
    genuine = directive("provider-request-f2", response="must never be output")

    def handler(_snapshot):
        return genuine

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=handler)
    signal = emit_wake(runtime, key="f2")

    def die_conflict(snapshot, d):
        raise AssertionError("response recorder must not run after auth failure")

    def meter_conflict(snapshot, d):
        raise AssertionError("metering must not run after auth failure")

    def hostile_authenticator(snapshot, d):
        # Snapshot at the authentication-failure boundary: only mutations AFTER
        # this point may count against the fail-closed ordering invariant. The
        # pre-dispatch wake->running bookkeeping commit happens before the
        # provider boundary and is out of scope for response-derived effects.
        hostile_authenticator.revision_at_failure = int(store.current_world_revision())
        attempt_row = runtime.background_model_attempts.get(snapshot.model_attempt_id)
        assert attempt_row is not None
        raise BackgroundModelResponseConflict(
            attempt_row, "ia injected authentication failure"
        )

    runtime.cognitive_runtime.model_response_authenticator = hostile_authenticator
    runtime.cognitive_runtime.model_response_recorder = die_conflict
    runtime.cognitive_runtime.model_usage_recorder = meter_conflict

    revision_before = int(store.current_world_revision())
    with pytest.raises(BackgroundModelResponseConflict):
        runtime.run_wake(wake_ref=wake_ref(signal), now=NOW)

    attempt = runtime.background_model_attempts.inspect(
        subject_id=runtime.subject_id,
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
    )
    assert attempt is not None, "attempt admission must not be undone by auth failure"
    assert attempt.state in {"admitted", "dispatching"}, attempt
    assert attempt.provider is None and attempt.response_fingerprint is None, (
        "provenance was mutated despite authentication failure"
    )
    assert runtime.background_model_attempts.response_authenticity_receipt(
        attempt.attempt_id
    ) is None
    assert runtime.background_model_attempts.staged_response(attempt.attempt_id) is None
    from ia_helpers import sql_rows

    assert sql_rows(_db_path(store), "SELECT 1 FROM metering_records") == []
    assert int(store.current_world_revision()) == (
        hostile_authenticator.revision_at_failure
    ), "World revision moved after the authentication-failure boundary"
    from ia_helpers import assistant_outputs

    assert assistant_outputs(store, value="must never be output") == []


def test_adv_f3_receipt_is_durable_before_any_downstream_mutation(tmp_path):
    """Crash between receipt and provenance: only the receipt row may exist."""

    store, index, _db = world(tmp_path)
    exact = directive("provider-request-f3", response="ordered bytes")

    def handler(_snapshot):
        return exact

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=handler)
    signal = emit_wake(runtime, key="f3")

    def die_before_provenance(snapshot, d):
        raise IAProcessDeath("death after authenticator, before recorder")

    runtime.cognitive_runtime.model_response_recorder = die_before_provenance
    with pytest.raises(IAProcessDeath):
        runtime.run_wake(wake_ref=wake_ref(signal), now=NOW)

    attempt = runtime.background_model_attempts.inspect(
        subject_id=runtime.subject_id,
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
    )
    assert attempt.state == "dispatching", attempt
    assert attempt.provider is None and attempt.response_fingerprint is None, (
        "provenance was mutated before/despite crash-before-recorder"
    )
    receipt = runtime.background_model_attempts.response_authenticity_receipt(
        attempt.attempt_id
    )
    assert receipt is not None, "receipt must be durable before provenance recording"
    assert runtime.background_model_attempts.staged_response(attempt.attempt_id) is None
    from ia_helpers import sql_rows

    meters = sql_rows(_db_path(store), "SELECT * FROM metering_records")
    assert meters == [], f"metering ran before provenance: {meters!r}"


def _db_path(store):
    return store.db_path
