# CORE-BACKGROUND-RESPONSE-RECOVERY-001 — Execution Prompt

Repository: `Haneof/Haneof-AIOS-Core-v3.0`

Role: Core Runtime Recovery Engineer.

Start by fetching live `main`, then read:
- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
- `AIOS_v3.0_CURRENT_CHECKPOINT.md`
- `governance/C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_001_GATE_INTEGRITY_CORRECTION_2026-09-26.md`
- `governance/C15_RCC_RES_B_RERUN_002_STATE_LOSS_ADJUDICATION_2026-09-26.md`
- `src/aios_core/runtime/background_attempt.py`
- `src/aios_core/runtime/cognitive_runtime.py`
- `src/aios_core/runtime/turn_runtime.py`
- `src/aios_core/headless/cli.py`
- existing background-attempt, turn-execution, headless and recovery tests.

Confirm:

`CORE-BACKGROUND-RESPONSE-RECOVERY-001 = READY`

If not READY, STOP.

Your only task is the smallest Core mechanism that lets an exact, externally durably preserved provider response resume the SAME background model attempt/round after process death without another provider call.

Hard requirements:

- no provider re-dispatch on exact-response recovery;
- no semantic reconstruction/default/fallback;
- exact provider/model/request_id + response fingerprint/directive verification;
- missing or mismatched exact reply remains fail-closed;
- downstream response/silence/capability application must use the normal CognitiveRuntime path;
- capability side effects, assistant output and metering must converge exactly once across restart;
- existing not_submitted safe retry semantics remain unchanged;
- existing ambiguous no-response in_doubt protection remains unchanged;
- ordinary uninterrupted provider path remains behavior-compatible;
- no second World/cognition store;
- no operator-owned semantic engine.

Fault-injection matrix must include:

1. crash after dispatch, exact response unavailable -> in_doubt and no retry;
2. exact response durably reconciled -> recovery provider call count remains zero;
3. wrong fingerprint -> reject;
4. wrong provider/model/request_id -> reject;
5. crash after response reconciliation before application;
6. crash during capability application;
7. crash after capability result before next model round;
8. crash after terminal response/silence before completion marker;
9. repeated recovery invocation -> no duplicate capability/output/metering;
10. normal model path + not_submitted retry regressions remain green.

Preserve all red attempts.

Do not run Resident.
Do not modify sealed fixture or historical Resident evidence.
Do not work on operator persistence in this task.
Do not enter RC-REFREEZE-002.

When complete, open a candidate PR and stop at:

`REVIEW_READY`

Do not self-accept.
