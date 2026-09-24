# CORE-HEADLESS-001-CORRECTIVE-001 INDEPENDENT ACCEPTANCE

Repository:
`Haneof/Haneof-AIOS-Core-v3.0`

Role:
Independent Headless Core / Single-Writer Corrective Acceptance Reviewer

Candidate:
- original engineering PR #181
- branch: `core-headless-001-20260924-sol`
- historical implementation exact head: `a43c2e9408e51ec8812e9f6ec808a71401bc2841`
- historical evidence-only handoff: `12928af4ffa40e70d9ae80124dab388a486f7097`
- historical independent review #185: `ACCEPTANCE_FAIL`
- historical blocker: `CORE-HEADLESS-001-ACCEPT-BLOCKER-001`
- historical probe #184 head: `f36665541742badde3b7c20e24528668b5ba3f59`
- new corrective tested implementation exact head: `16e983a536b124ddb600981fc16326d9db54358f`
- new evidence-only handoff: `f25218aac3812c4511351333704055ff90e7dd75`

Your only task is to independently decide whether the corrected #181 closes the writer-identity blocker without regressing the already-passing HEADLESS / FIX-001 / FIX-002 / FIX-003 semantics.

You are not:
- PR #181 author
- corrective engineer
- PR #185 reviewer repairing their own finding
- AIOS total PM
- Resident
- UI/hardware engineer

This window:
- acceptance only
- no candidate repair
- no merge
- no CORE-RECOVERY-001
- no Resident
- no UI/hardware

## Start

1. Fetch current live `main`.
2. Read:
   - `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
   - `AIOS_v3.0_CURRENT_CHECKPOINT.md`
   - `PROJECT_MASTER_MAP.md`
   - `governance/prompts/CORE_HEADLESS_001_2026-09-24.md`
   - `governance/prompts/CORE_HEADLESS_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`
   - `governance/prompts/CORE_HEADLESS_001_CORRECTIVE_001_2026-09-24.md`
   - `reviews/CORE_HEADLESS_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`
   - `reviews/CORE_HEADLESS_001_COMPLETION_EVIDENCE_2026-09-24.md`
   - PR #181 current body/diff.
3. Confirm:
   `CORE-HEADLESS-001-CORRECTIVE-001 = GATE / REVIEW_READY`.
4. Pin #181 and confirm the tested corrective exact head remains:
   `16e983a536b124ddb600981fc16326d9db54358f`.
5. Confirm the handoff head remains:
   `f25218aac3812c4511351333704055ff90e7dd75`
   and that `16e983a5... -> f25218aa...` changes only
   `reviews/CORE_HEADLESS_001_COMPLETION_EVIDENCE_2026-09-24.md`.

If the implementation head changes, do not inherit this exact-head evidence.

## Preserve historical FAIL

Do not overwrite or rewrite PR #185 / the historical report as PASS.

Historical failure remains valid:
same canonical World could use two caller-selected lock paths and therefore two independent OS lock-file inodes.

First re-establish that the old design was genuinely bypassable from #185/#184 evidence before judging the corrective.

## Corrective scope

Independently confirm the corrective delta after historical handoff `12928af4...` changes only:
- `src/aios_core/headless/core.py`
- `src/aios_core/headless/cli.py`
- `tests/integration/test_core_headless.py`

No `src/aios_core/runtime/**` changes are allowed.

## Core invariant to accept

For a single canonical durable World identity there must be exactly one writer-exclusion identity.

The corrected code claims:
- `world_path` is canonicalized through resolved path identity;
- actual lease path is derived only as:
  `<canonical-world>.writer.lock`;
- `HeadlessConfig.lock_path` is validation-only;
- CLI `--lock` is validation-only;
- `AIOS_LOCK_PATH` is validation-only;
- any noncanonical supplied lock path raises `HeadlessConfigurationError`;
- caller input cannot select a second lease inode for the same canonical World.

Independently inspect implementation, not just tests.

## OS lease semantics

Verify the repair preserves:
- POSIX: process-held `flock(LOCK_EX | LOCK_NB)`;
- Windows path remains process-held `msvcrt.locking(... LK_NBLCK ...)`;
- lock-file metadata is diagnostic only;
- PID/host/text is not consulted as liveness truth;
- stale file contents alone do not block startup;
- release occurs on clean stop and failure cleanup.

Fail if the repair converts writer ownership into PID-file/content logic or an in-process registry.

## Required blocker probes

Perform fresh independent probes against corrected exact head.

At minimum:

### Probe A — alternate path rejection
Same canonical World + arbitrary alternate `lock_path` must not yield a second lease identity.
It must fail explicitly at configuration/start boundary.

### Probe B — active same-World competition
Writer A holds the canonical lease.
Writer B using valid canonical configuration must fail with `HeadlessWriterBusy`.
Failed B startup must not mutate World revision/state.
After A stops, B must acquire and open the same World.

### Probe C — stale artifact
Leave/recreate stale canonical lock-file contents with no active OS lease.
A new writer must open successfully.
This proves file contents are not liveness truth.

### Probe D — canonicalization alias
Verify relative vs absolute World paths map to the same canonical World and lease identity.

Also perform the symlink test where supported by the CI OS:
an existing World reached by a symlink resolving to the same target must map to the same canonical identity.

## CLI / env acceptance

Freshly verify:
- `--lock <alternate>` cannot choose a second writer lease;
- `AIOS_LOCK_PATH=<alternate>` cannot choose a second writer lease;
- both fail as configuration errors rather than silently using another lock;
- canonical explicit path, if accepted, maps to the exact derived canonical path.

## Regression boundary

The corrective must not regress any previously accepted HEADLESS behavior:

- clean non-editable install;
- installed `aios-core-headless`;
- same-World restart continuity;
- world_revision/index continuity;
- A-F restart matrix;
- pending Wake restart;
- FIX-001 temporal read cut;
- FIX-002 background IN_DOUBT no blind reinvocation;
- FIX-003 pre-admission explicit recovery;
- Wake/Review/assistant/metering no duplicate;
- provider-neutral ModelHandler;
- no second World/runtime/scheduler/recovery ledger.

## Exact-head Gates

All evidence below must be independently re-read and tied to corrected exact head
`16e983a536b124ddb600981fc16326d9db54358f`:

- core-headless — run `35993796247`, job `107613844756`
- world-kernel — run `35993796267`, job `107613844605`
- constitutional-cognition-closure — run `35993796265`, job `107613844757`
- full P16 — run `35993796249`, job `107613844795`

PM pre-check observed:
- CPython 3.12.14
- pytest 8.4.2
- pydantic 2.13.5
- direct P16 `pytest -q`
- 100%
- 675 pass markers
- workflow SUCCESS

Headless PM pre-check observed:
- clean non-editable `pip install ".[dev]"`
- installed CLI smoke
- world revision `0 -> 2 -> 2`
- 13 corrective/headless tests `............. [100%]`
- runtime compatibility suite `[100%]`.

Re-read raw logs yourself.

## Fresh adversarial evidence

Do not simply rely on author tests.

Create fresh probes from the corrected exact head or from its PR merge-ref context.

At least one fresh probe should specifically attempt to recreate the historical bypass using a path that differs textually but refers to the same canonical World configuration space.

If you create a probe PR:
- probe-only;
- do not modify #181;
- close it unmerged after evidence capture.

## Live-main drift

If main advanced after corrective construction:
- governance/review-only drift does not require mechanical rebase;
- any relevant semantic `src/**`, packaging contract, HEADLESS test-contract, or workflow change requires explicit revalidation and may yield `REBASE_REVALIDATION_REQUIRED`.

## Verdict

### ACCEPTANCE_PASS
Only if:
- old blocker is understood/reproduced from historical evidence;
- canonical World -> one lease identity is mechanically true;
- alternate lock path cannot bypass it;
- active competition fails closed;
- failed competitor does not mutate World;
- stale lock artifact is harmless without OS lease;
- relative/absolute and supported symlink aliases converge;
- CLI/env override cannot create a second identity;
- A-F/FIX-001/002/003 regression surface remains PASS;
- four exact-head Gates PASS;
- full P16 PASS;
- fresh adversarial probes PASS;
- no semantic live-main drift invalidates candidate;
- blockers = 0.

### ACCEPTANCE_FAIL
Any real implementation blocker.

### REBASE_REVALIDATION_REQUIRED
Only for a new relevant semantic main change that materially invalidates the pinned corrected candidate.

## Report

Do not modify:
`reviews/CORE_HEADLESS_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`

Create a new report:
`reviews/CORE_HEADLESS_001_CORRECTIVE_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`

Create one review-only PR from review-time live main.

Report:
- review-time main
- PR #181
- old implementation/evidence heads
- old blocker and historical reproduction
- corrected exact implementation head
- corrected evidence-only handoff
- corrective scope
- writer identity verdict
- OS lease verdict
- alternate-path / competing-writer / stale-artifact / alias probes
- CLI/env verdict
- A-F + FIX-001/002/003 compatibility
- exact-head CI
- full P16
- live-main drift
- blocker count
- final verdict

Do not merge #181.

If PASS, state:

`PR #181 CORE-HEADLESS-001-CORRECTIVE-001 tested exact implementation head 16e983a536b124ddb600981fc16326d9db54358f with evidence-only handoff f25218aac3812c4511351333704055ff90e7dd75 is independently accepted for PM integration.`
