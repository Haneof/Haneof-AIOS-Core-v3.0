# CORE-HEADLESS-001 Integration Receipt — 2026-09-24

Status: DONE
Task: CORE-HEADLESS-001 / CORE-HEADLESS-001-CORRECTIVE-001

## Historical chain

- Engineering PR: #181.
- Original tested implementation exact head:
  `a43c2e9408e51ec8812e9f6ec808a71401bc2841`.
- Original evidence-only handoff:
  `12928af4ffa40e70d9ae80124dab388a486f7097`.
- First independent acceptance: PR #185 = ACCEPTANCE_FAIL.
- Historical blocker:
  `CORE-HEADLESS-001-ACCEPT-BLOCKER-001`.
- Historical probe: PR #184 / head
  `f36665541742badde3b7c20e24528668b5ba3f59`, CLOSED / UNMERGED.
- Historical failure: same durable World writer exclusion could be bypassed by choosing an alternate caller-controlled `lock_path`.

The historical FAIL is preserved and is not rewritten as PASS.

## Corrective

Corrective continued on the original PR #181 and branch.

Corrected tested implementation exact head:
`16e983a536b124ddb600981fc16326d9db54358f`.

Corrected evidence-only handoff:
`f25218aac3812c4511351333704055ff90e7dd75`.

The corrective changes only:
- `src/aios_core/headless/core.py`
- `src/aios_core/headless/cli.py`
- `tests/integration/test_core_headless.py`

The writer lease identity is now derived only from the canonical resolved durable World path:
`<canonical-world>.writer.lock`.

Caller-supplied `HeadlessConfig.lock_path`, CLI `--lock`, and `AIOS_LOCK_PATH` are validation-only and cannot select a second writer identity.

The actual exclusion primitive remains the process-held OS advisory lease:
- POSIX `fcntl.flock(... LOCK_EX | LOCK_NB)`
- Windows `msvcrt.locking(... LK_NBLCK ...)`

Lock-file PID/host/text remains diagnostic only and is not liveness or World truth.

## Corrected exact-head verification

All required runs were tied to corrected implementation exact head
`16e983a536b124ddb600981fc16326d9db54358f`:

- core-headless: run `35993796247`, job `107613844756` — SUCCESS
- world-kernel: run `35993796267`, job `107613844605` — SUCCESS
- constitutional-cognition-closure: run `35993796265`, job `107613844757` — SUCCESS
- full P16: run `35993796249`, job `107613844795` — SUCCESS

Environment:
- CPython 3.12.14
- pytest 8.4.2
- pydantic 2.13.5

Headless proof:
- clean non-editable `pip install ".[dev]"`
- installed `aios-core-headless`
- World continuity `world_revision 0 -> 2 -> 2`
- corrected permanent HEADLESS suite 13/13 PASS
- runtime compatibility suite PASS

Full P16:
- direct `pytest -q`
- 100%
- 675 pass markers
- workflow/job SUCCESS

## Fresh final independent acceptance

Review-only PR:
- PR #189
- review head:
  `603f0d9f14e2214c8cd67504efa2b2ae5b25413e`
- report:
  `reviews/CORE_HEADLESS_001_CORRECTIVE_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`
- verdict: ACCEPTANCE_PASS
- blockers: 0

Fresh adversarial probe:
- PR #188 — CLOSED / UNMERGED
- probe head:
  `bf104da474049c3250b081a3d3616f172c4e8a9f`
- core-headless targeted suite: 18/18 PASS
- full P16 probe run: 680 pass markers
- all four probe workflows SUCCESS

Independent probes established:
- historical alternate-lock bypass is closed;
- active same-World competing writer fails closed;
- failed competing startup does not mutate World;
- clean release permits subsequent writer;
- stale lock-file metadata without an OS lease is harmless;
- relative/absolute and supported symlink aliases converge on one lease identity;
- CLI/environment alternate lock input cannot choose another lease.

## Integration

PM merged independent acceptance evidence first:
- PR #189 merge:
  `6a44073880f4a6551a814cde0c94cb480b6502c2`.

Before candidate integration:
- PR #181 head remained exactly
  `f25218aac3812c4511351333704055ff90e7dd75`;
- the tested implementation/evidence boundary remained valid:
  `16e983a5... -> f25218aa...` changed only the completion-evidence file;
- after GitHub recomputation, #181 was `mergeable=true / mergeable_state=clean / rebaseable=true`;
- main drift after final acceptance consisted only of the #189 review report.

PM merged PR #181 with expected-head pin:
- merge:
  `6ccd79d93f8fa8845bf392bd3c1ef0641ad1cde6`.

## Honest post-merge note

At integration writeback time, GitHub returned no automatic workflow runs for merge commit
`6ccd79d93f8fa8845bf392bd3c1ef0641ad1cde6`.

No post-merge green run is claimed.
The authoritative integration evidence is:
- corrected exact-head four-Gate SUCCESS set;
- full P16 675-pass evidence;
- fresh independent acceptance #189;
- fresh adversarial probe #188.

## Release effect

`CORE-HEADLESS-001 = DONE`.
`CORE-HEADLESS-001-CORRECTIVE-001 = DONE`.

The headless Core is now integrated with:
- installable CLI;
- same-World start/stop/restart continuity;
- canonical single-writer exclusion;
- A-F restart matrix;
- preserved FIX-001/002/003 semantics.

This does not mean S2 or AIOS Core is complete.

The next S2 task is:
`CORE-RECOVERY-001`.

CORE-SCALE-001, CORE-RC-FREEZE-001, fresh Resident A/B/C, C16, broad P16 and P17 remain blocked by their own gates.
