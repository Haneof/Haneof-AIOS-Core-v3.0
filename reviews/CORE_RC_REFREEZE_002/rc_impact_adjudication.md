# CORE-RC-REFREEZE-002 RC impact adjudication

## Verdict

**FRESH_A_REQUIRED**

**A-RERUN-002 = HISTORICAL_FOR_PRIOR_RC_ONLY**

**FRESH_A-RERUN-003_REQUIRED**

Do **not** hash-swap PR #205 / A-002 evidence onto this RC.

## Basis (independent Core semantic diff)

Old RC frozen Core tree (`CORE-RC-FREEZE-001`):

`fe77f8a0706acfaf369041d0882b6d0e6de39f22` at software `773876f92d5f8e53422f8f5a68cc651953d93052`

New RC frozen Core tree:

`a9618abe0b3d4ac3b08bd23dbd58f3e3f97e05d6` at software `27a21db5b656d441248b9240020910b66a223830`

`git diff 773876f9... origin/main -- src/aios_core` (6 files, +1868/−78):

- `src/aios_core/runtime/__init__.py`
- `src/aios_core/runtime/background_attempt.py` (trusted return receipts, HMAC authority, staging/recovery)
- `src/aios_core/runtime/cognitive_runtime.py`
- `src/aios_core/runtime/metering.py`
- `src/aios_core/runtime/turn_execution.py`
- `src/aios_core/runtime/turn_runtime.py`

These paths are exactly the Resident-visible background execution / durability / response-recovery surface.

Corrective-002 changes:

- exact provider-return authenticity
- receipt binding to payload / provider / model / request / work / subject / round / attempt
- crash staging recovery without redispatch
- metering exactly-once on recovered exact response

A Resident run on the old Core therefore exercised a **different** recovery/authenticity semantic than this RC. A-002 remains canonical evidence **for the prior RC only**.

## B persistence

`C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001` stays **FROZEN_WIP**. Resume only after:

1. CORE-RC-REFREEZE-002 independent acceptance PASS
2. FRESH A-RERUN-003
3. A independent acceptance

This freeze window did not modify PR #216.
