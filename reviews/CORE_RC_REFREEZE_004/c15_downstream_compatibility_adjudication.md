# CORE-RC-REFREEZE-004 - C15 downstream compatibility adjudication

Historical broad evidence on the accepted Corrective-003 candidate reported `45 failed / 1092 passed`, concentrated in `tests/c15_persistence/**` / `tools/c15_persistence/**`.

The RC004 final exact-head gate freshly runs `tests/c15_persistence/**` separately from the Core gate and records every failure path. The adjudication rule is frozen:

- if Core gates are green and failures remain only in downstream C15 persistence/operator surfaces, record:
  - `CORE_FREEZE_NOT_BLOCKED_BY_DOWNSTREAM_OPERATOR_DEBT`
  - `C15_OPERATOR_ADAPTATION_REQUIRED_BEFORE_RESIDENT`
- if the C15 run mechanically demonstrates an accepted Core contract regression, RC004 is `BLOCKED`.

Window 24 will not change `tools/c15_persistence/**`, `tests/c15_persistence/**`, or restore the rejected local self-trust path merely to make the legacy harness green.

The final exact-head CI comment/artifact supplies the fresh count and binding classification.
