# WINDOW 17 Reviewer Probe Revision Log (`PROBE_REVISION_LOG.md`)

## Revision 1 (Initial Pre-Execution Freeze — `v1`)

- **Revision:** `v1` (preserved verbatim at `reviewer_probes/window17_independent_attack_v1.py`, `reviewer_probes/SHA256SUMS.v1`, and `raw/candidate_w17_independent_probes_v1.txt`)
- **SHA-256 (`window17_independent_attack_v1.py`):** `c950d158ed0582fce2c1610f8dab9507cd3e90296ae43f98cb514c9e904fb09f`
- **Reason:** Initial pre-execution freeze of 14 reviewer-owned independent acceptance probes (`IA17-MINT-001` through `IA17-SIGKILL-001`).

## Revision 2 (Import-Path Harness Fix — `v2`)

- **Revision:** `v2` (preserved verbatim at `reviewer_probes/window17_independent_attack_v2.py`, `reviewer_probes/SHA256SUMS.v2`, and `raw/candidate_w17_independent_probes_v2.txt`)
- **Old SHA-256 (`v1`):** `c950d158ed0582fce2c1610f8dab9507cd3e90296ae43f98cb514c9e904fb09f`
- **New SHA-256 (`v2`):** `fdefecd8edf20a3b9ede4e0432cac0864e51bb82c098c4d8568fbd08651a4900`
- **Classification:** `HARNESS_FIX_ONLY` (zero expected-outcome changes)
- **Why Harness Fix Was Required:** `v1` line 28 contained `from aios_core.models import CapabilityDescriptor`, raising `ModuleNotFoundError` at import time before any probe ran.

## Revision 3 (Attempt-Admission Precondition Setup Harness Fix — `v3`)

- **Revision:** `v3` (current `reviewer_probes/window17_independent_attack.py`)
- **Old SHA-256 (`v2`):** `fdefecd8edf20a3b9ede4e0432cac0864e51bb82c098c4d8568fbd08651a4900`
- **New SHA-256 (`v3`):** `a6db33956bb7bc1e8af19cddd7cebdd320604bba98b6a2b906fd1eb363fba0c3`
- **Classification:** `HARNESS_FIX_ONLY` (zero expected-outcome changes)
- **Why Harness Fix Was Required:** In `v2`, `probe_ia17_mint_001` and `probe_ia17_mint_002` called `recovery.run_turn(...)` expecting it to transition the background attempt row from `dispatching` to `in_doubt`; however, `FusedTurnRuntime.run_turn` calls `turn_executions.claim(...)` first, which raises `TurnExecutionInDoubt` before reaching `background_model_attempts.admit(...)` (recorded in `raw/candidate_w17_independent_probes_v2.txt`). `v3` calls `recovery.background_model_attempts.admit(...)` (matching Window 14 `reopen_as_recovery`) to transition `attempt.state` from `dispatching` to `in_doubt` before testing the attack. All 14 probe IDs and all expected outcomes in `PROBE_CONTRACT.md` are unchanged.
