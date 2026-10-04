# CORE-RC-REFREEZE-004 — RC Impact Adjudication

## Verdict

**`FRESH_A_REQUIRED`** and **`FRESH_OPERATOR_PREP_REQUIRED`**.

- A-003 and A-004 are **prior-RC historical evidence only**; earlier Resident A runs likewise. **No hash-swap onto this RC.**
- No Resident A/B/C was run in this window; no evaluator/close; no public release.

## Mechanical semantic-delta basis

| | Frozen software | `src/aios_core` tree | `tests` tree |
|---|---|---|---|
| Prior RC-003 | `f20f2edfa7af00d0286493fd15196ca9503bc315` | `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623` | `7e33b5ef8432370234965d3ccd61248c703c4019` |
| This RC-004 | `1cee3c5ad12f4b9098232bae11b51df786c5eb2f` | `16f1487e291b009c55bee402abfd79fdacbae960` | `9db1bfa08143bc99fe03836e2752ee6e05694eb6` |

`git diff f20f2ed… 1cee3c5a… -- src/aios_core`: **6 files, +1733 / −215** — execution-visible, accepted Corrective-003 change to the trusted-return/recovery boundary (`runtime/background_attempt.py`, `runtime/late_return.py`, `runtime/live_return.py`, `runtime/turn_runtime.py`, `runtime/cognitive_runtime.py`, `runtime/__init__.py`).

The software delta is not governance-only and has not been proven semantically identical to any previously Resident-exercised boundary. The default therefore stands: a fresh Resident A (and fresh operator preparation) is required after this RC's independent acceptance and PM integration.

## Legal downstream sequence (later, separately authorized windows only)

1. `CORE-RC-REFREEZE-004` (this window) → 2. Fresh Independent RC Acceptance → 3. PM Integration → 4. C15 operator/persistence compatibility corrective **against the frozen RC** → 5. Fresh IA of that corrective → 6. Fresh Resident A only on explicit PM release.

**Forbidden in Window 24** (and not performed): steps 2–6, B release/run, Resident C, C15 evaluator/close, public release/tag, UI/hardware, restoring the rejected local self-trust path.

## This window's evidence does not change the ruling

The frozen identity, drift audit, fresh 928-test Core gate, reviewer probes Suites A/B/W17 (4/7/14, all zero failures), Corrective-003 security spot checks, real-SIGKILL set (9 passed), clean headless install, backup/restore/rebuild and writer/restart probes all pass. That is a technical freeze-candidate packet for independent acceptance — it is **not** independent acceptance and does not waive `FRESH_A_REQUIRED` / `FRESH_OPERATOR_PREP_REQUIRED`.
