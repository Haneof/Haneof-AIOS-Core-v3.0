# CORE-RC-REFREEZE-003 — Focused Fresh Regression Evidence

Status: **FORMAL GATE PASS** on exact software `f20f2edfa7af00d0286493fd15196ca9503bc315`, CPython 3.12.14, Pydantic 2.13.5 and pytest 8.4.2. Run [36436264055](https://github.com/Haneof/Haneof-AIOS-Core-v3.0/actions/runs/36436264055), job/check `108974868566`.

The focused invocations supplement (and are not added to) the complete 919-test repository run.

## Trusted-return / replay / authenticity / process-loss / recovery

**248 tests; 0 failures; 0 errors; 0 skipped; JUnit testcase-time sum 23.220 s.** The exact selected files were:

- `tests/integration/test_core_background_trusted_return_recovery_001.py`
- `tests/integration/test_core_background_trusted_return_adversarial_001.py`
- `tests/integration/test_core_background_trusted_return_r5_001.py`
- `tests/integration/test_core_background_trusted_return_r5_conflicts_001.py`
- `tests/integration/test_core_background_trusted_return_corrective_001_capability_replay.py`
- `tests/integration/test_core_background_trusted_return_corrective_001_store_fail_closed.py`
- `tests/integration/test_core_background_trusted_return_corrective_001_process_loss.py`
- `tests/integration/test_core_background_response_recovery_001.py`
- `tests/integration/test_core_background_response_recovery_001_corrective_001.py`
- `tests/integration/test_core_background_response_recovery_001_corrective_002_authenticity.py`
- `tests/integration/test_core_background_response_recovery_001_corrective_002_recovery.py`
- `tests/integration/test_core_gap_fix_002_background_attempts.py`
- `tests/runtime/test_background_model_attempt.py`
- `tests/runtime/test_cognitive_runtime_trusted_return.py`
- `tests/runtime/test_turn_execution_recovery.py`

This fresh group covers R1–R5, exact replay and conflict behavior, authenticity/transplant/corruption, process loss, recovery and the prior corrective recovery suites. It is not historical reviewer evidence.

The separate runtime-registry probe returned **`REGISTRY_MATRIX_PASS`**: 43 total reachable capabilities, 22 side-effecting capabilities, 22 matrix rows, exact registry/matrix match, and no provider dispatch. The exact side-effecting names were:

`commit_ai_world_claim`, `commit_claim`, `commit_operation_experience`, `create_attention_watch`, `create_task`, `form_event`, `propose_action`, `propose_cognitive_policy`, `propose_dimension`, `propose_entity`, `propose_goal`, `record_communication_experience`, `retract_claim`, `revise_claim`, `revise_entity`, `rollback_cognitive_policy`, `transition_dimension`, `transition_event`, `transition_goal`, `transition_task`, `update_cognitive_policy`, `upsert_relation`.

- Trusted-return JUnit SHA-256: `df0ca41dee7db87fcce248dce1ace81a350dfb5d8040d32b99bcc11ba5faf4a0`
- Trusted-return raw output SHA-256: `cfecb09eb205b283e78c3043b770079384883b1b25c24c7a8484ff8dedae8229`
- Registry inventory output SHA-256: `f6a676ba174cd12a0f1ae63e5df8c7db20ad71b317ee0a998308ca419a9c5ae6`

## World / index / Wake / Review / C14 / cognition / headless / recovery / SCALE

**356 tests; 0 failures; 0 errors; 0 skipped; JUnit testcase-time sum 34.539 s.** The passing focused group explicitly selected store/World atomicity, M0 store-delta/search, World map/index, C09 Wake/attention/budget, execution, P15 Review, fused-turn/current-time, cognition revision/writeback/policy/runtime, C14 derivation runtime and scheduler, dimension/summary hierarchy, long-context and memory recommendation, headless, recovery, metering, T28 boundary, SCALE and the deterministic habitation harness.

- Core-systems JUnit SHA-256: `7b8d088b36970e64e5dbc574cf70668e949762bab077ef2781994718e03f0d2a`
- Core-systems raw output SHA-256: `d2293de89da7302e7d86cfb60c71c32e6e0d6aab59a779b5e2dcaca9142abdc8`

The full raw test commands, JUnit files, exact target identity and runner inventory are in the hosted Actions artifact documented by `formal_gate_run.json` and `environment_manifest.txt`.
