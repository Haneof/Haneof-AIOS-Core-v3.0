# CORE-RC-REFREEZE-004 — C15 Downstream Compatibility Debt Adjudication

Status: **`CORE_FREEZE_NOT_BLOCKED_BY_DOWNSTREAM_OPERATOR_DEBT`** + **`C15_OPERATOR_ADAPTATION_REQUIRED_BEFORE_RESIDENT`**.
RED preserved. Nothing repaired in this window.

## Fresh classification

Full-repository run on the frozen target (`raw/local/full-repo-junit.xml`): **1137 tests, 45 failed, 0 errors, 0 skipped**. Every failing test is under `tests/c15_persistence/**` and exercises `tools/c15_persistence/**`:

| Module | Failures |
|---|---:|
| `tests/c15_persistence/test_corrective_003_binding_blockers.py` | 20 |
| `tests/c15_persistence/test_corrective_002_remote_durability.py` | 9 |
| `tests/c15_persistence/killpoints/test_killpoints.py` | 5 |
| `tests/c15_persistence/test_corrective_003_regressions.py` | 4 |
| `tests/c15_persistence/test_environment_reattach.py` | 3 |
| `tests/c15_persistence/test_operator_wiring.py` | 3 |
| `tests/c15_persistence/test_resident_surface.py` | 1 |

Non-downstream failures = **0**. Core gate (`tests/unit tests/integration tests/runtime tests/habitation`) is fully green in the same window (928 passed).

## Failure signatures (local evidence)

- 21× `tools.c15_persistence.backend.BackendError: ack requires a durable application` (the operator's relay `mark_acked` requires `state == "applied"`, which the operator's own pre-Route-B flow never reached);
- 5× child probe `AssertionError: probe command failed` (the child exits 1 with the same `ack requires a durable application`, or exits 42 with `FAIL_CLOSED_HARD_STOP ... attempt is neither safely dispatchable nor recovery-eligible`);
- `tools.c15_persistence.operator_session.DurableTrustedReturnMissing: no durable trusted provider return for attempt ... (state=metered ...)`;
- several `remote-only recovery failed` / `trusted-return handoff missing` assertions in the operator's durability matrix.

## Why this is downstream adaptation debt, not an accepted-Core contract violation

1. All 45 failures are in the operator/persistence layer's own suites; no Core-owned test and no Core contract assertion fails, and the entire 928-test Core gate is green.
2. The operator code itself documents the new boundary — `tools/c15_persistence/operator_session.py` (class `DurableTrustedReturnMissing`): *"Accepted Core deliberately has no legal path that lets a recovery caller turn externally supplied bytes into a trusted provider return. The operator therefore stops fail-closed instead of redispatching, inventing evidence or making non-authoritative progress."* The failing suites are the ones whose expectations still assume a Core-owned durable trusted return on the ordinary local path — exactly the authority the accepted Corrective-003 removed (BLK-W20-001).
3. The failures that reach Core fail **closed** (`FAIL_CLOSED_HARD_STOP`, `in_doubt`) rather than producing a wrong effect — the designed, safe Core behavior.
4. Restoring the rejected local self-trust path to make these suites green is forbidden; the correct downstream remedy is a C15 operator/persistence compatibility adaptation against the frozen RC, to be independently accepted and integrated in a later, separately authorized window.

## Ruling

- `CORE_FREEZE_NOT_BLOCKED_BY_DOWNSTREAM_OPERATOR_DEBT`
- `C15_OPERATOR_ADAPTATION_REQUIRED_BEFORE_RESIDENT`
- No C15 corrective engineering, evaluator/close, or Resident work was performed in this window. The RED tests are preserved unmodified.
