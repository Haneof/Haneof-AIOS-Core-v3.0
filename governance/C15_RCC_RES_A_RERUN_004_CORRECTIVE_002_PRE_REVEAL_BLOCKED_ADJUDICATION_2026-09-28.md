# C15-RCC-RES-A-RERUN-004-CORRECTIVE-002 Pre-Reveal Blocked Adjudication — 2026-09-28

## Status

```text
C15-RCC-RES-A-RERUN-004-CORRECTIVE-002
= BLOCKED / CONTAMINATED_BEFORE_RUN / PRE-REVEAL
= HISTORICAL_BLOCKED_EXACT / IMMUTABLE

C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP
= READY

C15-RCC-RES-A-RERUN-004-CORRECTIVE-003
= BLOCKED_ON_OPERATOR_PREP
```

This is a PM governance adjudication.

No Resident run occurred.
No Independent Acceptance is required for this blocked pre-reveal attempt.
No Core change is authorized.

## Exact blocked evidence

Evidence PR:

- PR #279
- exact head: `8e5c1ec76ea973c849c33923ccc818fe1dad49e8`
- direct parent: `aa13733ae393ec70e0cfc923ad3fb59a4e1ad97a`
- tree: `af5f7dd273e98f8502ea70556fe80f71e542f37c`
- classification: `HISTORICAL_BLOCKED_EXACT / IMMUTABLE`

The PR contains only:

- `BLOCKED_REPORT.md`
- `SHA256SUMS`

under the Corrective-002 blocked-run evidence directory.

No World, index, release-state, runtime checkpoint, Resident session, exchange ledger, or cursor was created.

## Finding CORR002-BLK-001 — Resident context contaminated by required control-plane reads

The Corrective-002 prompt required the fresh Resident window to read:

- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
- `AIOS_v3.0_CURRENT_CHECKPOINT.md`
- historical failure adjudications

Those files are PM/operator control-plane records and intentionally preserve historical acceptance findings, prior run status, recovery facts, and other Resident-lineage summaries.

They are not Resident-safe inputs.

This conflicts with the binding Resident safe-run contract, which forbids:

- completion evidence / PM/evaluator reports for the test;
- other Resident run artifacts;
- PR descriptions / history that can expose prior or unreleased material.

PM adjudication:

`CORR002-BLK-001 = VALID_DISPATCH_DESIGN_DEFECT`

The Resident correctly stopped immediately.

The defect is in task dispatch design, not in Core and not in Resident behavior.

### Binding correction

A fresh Resident must never be instructed to read:

- task board;
- global checkpoint;
- PM adjudications;
- prior Resident PRs;
- review PRs;
- historical evidence;
- Git history/search for this task.

A Resident launch must be based only on a separately reviewed **Resident-safe launch packet** plus the existing safe Resident A run contract.

## Finding CORR002-BLK-002 — qualified runtime was not pre-provisioned

The blocked window had:

- CPython 3.11.2 only;
- no qualified Pydantic environment;
- required CPython 3.12.14 / Pydantic 2.13.5 was not established.

Provisioning attempts failed before any binding harness tests.

PM adjudication:

`CORR002-BLK-002 = VALID_OPERATOR_PRECONDITION_FAILURE`

This must be solved before the next Resident window is exposed to any task material.

The Resident should not be responsible for discovering historical control-plane material while simultaneously engineering its own launch environment.

## Architecture of the next attempt

The next attempt is split into two role-separated stages.

### Stage 1 — non-Resident operator prep

Task:

`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP`

Role:

`Resident Launch / Test Infrastructure Operator`

This role may read PM governance and historical mechanical failure evidence.

It may not make Resident semantic decisions or reveal the real C15 fixture.

It must:

1. prepare a reproducible CPython 3.12.14 / Pydantic 2.13.5 environment bootstrap;
2. build the run-local mechanical exchange harness;
3. run/freeze Layer A/B/C/D gates against frozen Core;
4. prove real-run mode contains no semantic callback/router;
5. generate a minimal Resident-safe launch packet;
6. publish operator-prep evidence only;
7. stop at `REVIEW_READY`.

### Stage 2 — fresh Resident

Task:

`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003`

This remains BLOCKED until:

- operator-prep evidence is independently accepted;
- PM integrates the prep;
- the exact Resident-safe launch packet is frozen.

The fresh Resident may read only:

1. `reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_A_RUN_CONTRACT.md`;
2. the exact accepted Resident-safe launch packet;
3. current legal event projection / RuntimeSnapshot / capability results generated during its own run.

It must not read global governance/control-plane material.

## Resident-safe launch packet requirements

The launch packet must contain only mechanical information:

- task identifier;
- `READY_FOR_RESIDENT` status;
- exact frozen software/Core/tests pins;
- exact CPython/Pydantic requirement;
- environment bootstrap path + SHA-256;
- harness package path + SHA-256 manifest;
- pre-run gate evidence hashes;
- allowed cursor range `1..13`;
- response mode = external/current Resident session;
- safe run contract path + SHA-256;
- explicit forbidden control-plane paths/categories;
- exact operator-prep evidence head.

It must contain **no**:

- prior user text;
- prior Resident responses;
- Claims;
- summaries;
- cognition descriptions;
- expected answers;
- prior cursor-specific semantic outcomes;
- evaluator findings about what the Resident should learn.

## Historical preservation

Preserve unchanged:

- PR #273 failed A-004;
- PR #275 failed IA;
- PR #277 blocked Corrective-001;
- PR #279 blocked pre-reveal Corrective-002.

No hash-swap or retroactive repair.

## Downstream state

Until Operator Prep → fresh Independent Acceptance → PM integration → fresh Corrective-003 Resident → fresh Independent Acceptance → PM integration:

- persistence Corrective-003 = BLOCKED;
- Resident B = BLOCKED;
- Resident C = BLOCKED;
- evaluator / C15 close = BLOCKED.
