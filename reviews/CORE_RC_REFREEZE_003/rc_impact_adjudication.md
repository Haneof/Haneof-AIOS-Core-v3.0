# CORE-RC-REFREEZE-003 — RC Impact Adjudication

## Verdict

**`FRESH_A_REQUIRED`**

- **A-003 = `HISTORICAL_FOR_PRIOR_RC_ONLY`**.
- **A-003 must not be hash-swapped onto this RC.**
- No Resident A/B/C run was performed in this task. No A-004 was run.

## Mechanical semantic-delta basis

Prior RC-002 frozen software: `27a21db5b656d441248b9240020910b66a223830`
Prior RC-002 Core tree: `a9618abe0b3d4ac3b08bd23dbd58f3e3f97e05d6`

Current RC-003 frozen software: `f20f2edfa7af00d0286493fd15196ca9503bc315`
Current RC-003 Core tree: `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623`

`git diff 27a21db5...f20f2ed... -- src/aios_core` is **11 files, +1,022 / −176**. It changes the accepted trusted-return/recovery/idempotency surface across:

- `src/aios_core/runtime/background_attempt.py`
- `src/aios_core/runtime/turn_runtime.py`
- `src/aios_core/storage/sqlite_store.py`
- `src/aios_core/storage/idempotency.py`
- `src/aios_core/execution/service.py`
- `src/aios_core/world_graph.py`
- `src/aios_core/policy/service.py`
- `src/aios_core/revision/service.py`
- `src/aios_core/events/service.py`
- `src/aios_core/dimensions/registry.py`
- `src/aios_core/communication/service.py`

These are execution-visible recovery/replay and durable capability-effect semantics. The accepted Corrective-001 receipt records that the trusted-return exact-replay correction expanded exact recovery convergence over the **22 reachable side-effecting capabilities**. A prior Resident run therefore exercised a materially different Core recovery/replay boundary.

The software delta is not limited to governance or evidence; reuse has not been proven semantically identical. The burden for overturning the default is unmet, so `FRESH_A_REQUIRED` stands.

## Legal downstream sequence

Only after this candidate receives independent acceptance and separate PM integration may a new `C15-RCC-RES-A-RERUN-004` be authorized in a later task window. Its own independent acceptance and the governance re-release of frozen persistence work are later gates. This task does not start those windows.

**Not authorized here:** A-004, resuming persistence Corrective-003, B release/run, Resident C, C15 evaluator, or C15 close.
