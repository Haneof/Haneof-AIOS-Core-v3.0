# CORE-RC-REFREEZE-004 — Real Process-Loss Evidence

Status: **PASS — real SIGKILL / fresh-process recovery proven on the frozen target.**

## Real SIGKILL selection (9 passed, `raw/local/real_process_loss.txt`)

- `tests/integration/test_core_background_trusted_return_corrective_001_process_loss.py`
- `tests/integration/test_core_background_late_trusted_return_corrective_002.py::test_ca2_004_real_sigkill_leaves_no_live_authority_in_the_fresh_process`
- `tests/integration/test_core_background_response_recovery_001_corrective_002_recovery.py::test_actual_sigkill_after_receipt_commit_recovers_without_provider_redispatch`
- `tests/integration/test_core_background_late_trusted_return_sigkill_001.py`
- `tests/integration/test_core_background_response_recovery_001_corrective_001.py::test_process_sigkill_after_exact_response_staged_recovers_with_zero_provider_calls`
- `tests/integration/test_core_background_response_recovery_001_corrective_001.py::test_process_sigkill_after_capability_side_effect_replays_exactly_once`
- `tests/integration/test_core_background_trusted_return_adversarial_001.py::test_real_sigkill_after_later_round_trusted_handoff`

These kill a real child process with `SIGKILL` (no ordinary-exception substitution) and recover in a fresh process; they assert zero provider redispatch, exactly-once metering and exactly-once capability effect.

## Reviewer probe

Window 17 `IA17-SIGKILL-001` (Suite in `raw/local/window17-probe.txt`): child exit code `-9`, recovered response after real SIGKILL, `provider_calls=[]`, `meters=1`, `state=metered`, `replay_blocked=True`.

## Boundary

Durable work either converges to one metered, one-effect completion through the genuine external proof path, or stays fail-closed (`dispatching` / `in_doubt`) without a second dispatch. No distributed multi-host claim is made.
