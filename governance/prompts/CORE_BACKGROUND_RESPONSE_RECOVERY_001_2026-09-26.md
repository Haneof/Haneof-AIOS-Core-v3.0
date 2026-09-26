# CORE-BACKGROUND-RESPONSE-RECOVERY-001

Repository: `Haneof/Haneof-AIOS-Core-v3.0`

Role: Core Runtime Recovery Engineer.

Start by fetching live `main` and reading:
- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
- `AIOS_v3.0_CURRENT_CHECKPOINT.md`
- `governance/C15_RCC_B_PERSISTENCE_CORE_RECOVERY_ADJUDICATION_2026-09-26.md`
- `src/aios_core/runtime/background_attempt.py`
- `src/aios_core/runtime/cognitive_runtime.py`
- `src/aios_core/runtime/turn_runtime.py`
- `src/aios_core/headless/cli.py`
- existing background-attempt / turn-execution / recovery tests.

Confirm `CORE-BACKGROUND-RESPONSE-RECOVERY-001 = READY`. If not, STOP.

Your only task is to add the minimum crash-safe Core continuation for an exact model response that was durably returned before process death.

Do not run Resident.
Do not touch sealed fixtures or canonical Resident evidence.
Do not implement B persistence/operator journaling in this window.
Do not enter RC re-freeze.
Do not weaken `in_doubt`.
Do not treat an external journal assertion as sufficient unless exact response bytes/directive + provider/model/request identity + durable fingerprint all verify.

Required behavior:
- exact reconciled response can resume the SAME attempt/round without provider re-dispatch;
- recovery uses normal CognitiveRuntime downstream semantics;
- capability/response/silence effects converge exactly once under crash/restart;
- metering remains exactly-once/idempotent;
- ordinary live provider path remains unchanged;
- missing/mismatched response evidence remains fail-closed.

Required adversarial/fault tests:
1. dispatch boundary crossed, no exact response -> in_doubt, no retry;
2. exact reconciled response -> provider call count remains zero on recovery;
3. wrong response fingerprint -> reject;
4. wrong provider/model/request id -> reject;
5. crash after response reconciliation before application;
6. crash during first capability application;
7. crash after capability result before next model round;
8. crash after terminal response/silence before final completion;
9. repeated recovery invocation -> no duplicate side effect/meter/assistant output;
10. existing not_submitted retry + normal model path regressions stay green.

Preserve every red attempt.

When implementation and full targeted + relevant regression evidence are complete, open a candidate PR and stop at:

`REVIEW_READY`

Do not self-accept.
