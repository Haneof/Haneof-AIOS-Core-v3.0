# WINDOW 28 — DUPLICATE PARALLEL EXECUTION — BLOCKED / PM_ADJUDICATION_REQUIRED

Date: 2026-10-05
Window: 28 (this session)
Task: `CORE-RC-REFREEZE-004-CORRECTIVE-002`
Role of the author of this file: RC Freeze Gate Corrective Engineer
Session branch: `arena/01a10c51-haneof-aios-core-v3-0` (this file's tip; non-canonical)

State: `BLOCKED / PM_ADJUDICATION_REQUIRED / DO_NOT_MERGE`

No competing canonical candidate was created, nothing was pushed to any
`release/*` candidate branch, PR #330 / #332 / #333 were not modified, no
Independent Acceptance was performed and nothing was merged.

## 1. Fresh ground truth confirmed

- live main at entry: `5927d7917112819c53593149ee8fab1eebdcfda6`
  ("Merge PR #334 governance: adjudicate Window 27 and release Window 28")
- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`: `WINDOW 28 RELEASED`
- `AIOS_v3.0_CURRENT_CHECKPOINT.md`: Window 27 FAIL / Window 28 READY
- `governance/CORE_RC_REFREEZE_004_CORRECTIVE_001_WINDOW27_ACCEPTANCE_FAILURE_ADJUDICATION_2026-10-05.md`
- `governance/prompts/CORE_RC_REFREEZE_004_CORRECTIVE_002_2026-10-05.md`
- PM binding blocker: `IA27-BLK-002 = BINDING / CRITICAL` (whole-run candidate
  identity / inter-job TOCTOU)

## 2. Blocking discovery: Window 28 is already being executed in parallel

Fresh remote inventory (read-only, this session) shows an existing, complete and
still-active Window 28 execution that occupies the exact branch name required by
the Window 28 task:

| item | identity |
| --- | --- |
| pull request | **#336** `[DO NOT MERGE] CORE-RC-REFREEZE-004-CORRECTIVE-002 — Window 28` |
| branch | `release/core-rc-refreeze-004-corrective-002-window28` |
| head at observation | `5a5d384f16798bfff46ffe03f87310b0eafb2321` |
| parent | `091ccc95e3e0d67ee7e01bdc576f821868cc98dc` |
| tree | `6976a82af383f89bce196e1d8ef766e24f6ed6c8` |
| PR created | `2026-10-05T09:57:36Z` |
| PR updated | `2026-10-05T13:54:07Z` |
| construction | append-only from failed `#330` head `2380121639865b1bd29176cf944f5a20afe4112d`, 23 commits ahead / 0 behind |
| protected-path drift vs failed candidate | NONE (`src/`, `tests/`, `tools/`, `pyproject.toml` untouched) |
| changed paths | `.github/workflows/core-rc-refreeze-004-formal-gate.yml` + `reviews/CORE_RC_REFREEZE_004_CORRECTIVE_002/**` |

The candidate workflow already implements the Window 28 closure that this
session was asked to build: `cancel-in-progress: true`, a provisional exact pin
(`PROVISIONAL_PENDING_FINAL_IDENTITY_SEAL`), and a final
`rc004-whole-run-identity-seal` job with fresh canonical-branch equality and
`FINAL_SEAL_REMOTE_HEAD_MISMATCH` fail-closed handling.

Parallel control/evidence refs already pushed by that execution:

- `control/w28-toctou-red-window28` (`dabf9c98d0736869ec95e7d0a34ebbe42213e3ee`, RED)
- `control/w28-toctou-green-window28` (`4db5841fe734a425e0e08429dec4d4f5477cd819`, GREEN)
- `control/w28-carry-forward-window28` (`f640cc2157604dddc3a3216f1b88381f0b7584f2`)
- `review/w28-red-toctou-control` (`9bc143c38d7be560af929bbd75ee949458d66b35`)
- `review/w28-toctou-red-control` (`e77e2d1de3bcbdee7f6bee813bd19901e677b4a6`)

Parallel hosted runs observed fresh (newest first, all in the last hours):

```
37320392029 core-rc-refreeze-004-formal-gate release/...window28 5a5d384f16 in_progress  2026-10-05T13:54:08Z
37319946562 core-rc-refreeze-004-formal-gate release/...window28 74f4117164 failure      2026-10-05T13:50:42Z
37318896125 w28-red-toctou-control            review/w28-red-toctou-control 9bc143c38d success 2026-10-05T13:42:34Z
37318820411 w28-red-toctou-control            review/w28-red-toctou-control d57db0abd0 success 2026-10-05T13:41:59Z
37292484209 core-rc-refreeze-004-formal-gate release/...window28 5a5d384f16 success     2026-10-05T09:48:40Z
37291221473 w28-carry-forward-controls        control/w28-carry-forward-window28 success 2026-10-05T09:37:01Z
37289888964 w28-toctou-green-control          control/w28-toctou-green-window28 success 2026-10-05T09:25:07Z
37289340609 w28-toctou-red-control            control/w28-toctou-red-window28 success   2026-10-05T09:20:05Z
```

The parallel execution was demonstrably **live while this session was preparing
its own corrective**: it pushed `review/w28-red-toctou-control` at
`13:41:59Z`/`13:42:34Z`, a commit `74f4117164…` at `13:50:42Z`, and re-pointed
the canonical branch back to `5a5d384f16…` at `13:54:08Z`.

## 3. Additional material observation (for PM attention, not an acceptance)

Run `37319946562` (`head_sha 74f4117164…`, `push`, completed `13:51:06Z` after
~24 s) **failed**, and commit `74f4117164…` is no longer reachable from the
canonical branch: the tip is again `5a5d384f16…`, which itself is the head that
already had a successful formal run at `09:48:40Z` (`37292484209`) and now has a
new run `37320392029` (created `13:54:08Z`, still in progress at observation).

That means the canonical Window 28 branch tip moved away from, and was then
restored to, the claimed frozen candidate after its claimed final CI. Under the
Window 28 prompt (§23/§24: exact freeze, no evidence commits after the final
hosted CI, and `local HEAD = remote branch HEAD = PR head = formal run head`),
the parallel candidate's freeze discipline needs PM adjudication before any
Independent Acceptance is commissioned on `5a5d384f16…`.

This file does not judge the technical quality of the parallel candidate; its
scope, controls and mechanics are consistent with the Window 28 task as far as
this session verified read-only.

## 4. Why this session stopped instead of publishing a second candidate

The Window 28 task mandates a **single** canonical corrective candidate from the
exact failed `#330` head, with a **new** canonical PR, and forbids reusing or
merging `#330`. The parallel execution already occupies:

- the exact recommended branch name `release/core-rc-refreeze-004-corrective-002-window28`,
- the append-only chain from the exact failed head,
- the RED/GREEN/carry-forward hosted controls,
- the canonical evidence path `reviews/CORE_RC_REFREEZE_004_CORRECTIVE_002/**`.

Publishing a second, competing corrective candidate at the same time would
create two divergent "canonical" Window 28 candidates and break the
single-candidate discipline that the fresh Independent Acceptance depends on.
It would also pollute the parallel candidate's open-PR contamination inventory
and could interfere with its in-flight runs (the corrected workflow cancels
stale runs on new pushes to its own branch).

Therefore this session reports
`BLOCKED / PM_ADJUDICATION_REQUIRED` and stops, per
`governance/prompts/CORE_RC_REFREEZE_004_CORRECTIVE_002_2026-10-05.md` §11.

## 5. Work preserved by this session (unpublished as a candidate)

Prepared but **not** published as a candidate branch and **not** pushed to any
`release/*` ref:

- one corrective commit on the session branch
  (`fix(rc004): close whole-run inter-job TOCTOU false-green`) with a whole-run
  identity closure that is mechanically comparable to the parallel candidate:
  `cancel-in-progress: true`; publisher-side fresh canonical equality before and
  after the commit-comment POST with pin invalidation on drift; a final
  `rc004-whole-run-identity-seal` job validating the publisher result,
  re-verifying identity around a bounded settle hold, sealing the pin and
  re-verifying after the seal write; a provisional pin
  (`PROVISIONAL_PENDING_IDENTITY_SEAL`) that can never remain authoritative after
  drift;
- two new mechanical probes under
  `reviews/CORE_RC_REFREEZE_004_CORRECTIVE_002/probes/`:
  - `whole_run_identity_static_probe.py` — 26 checks, `WHOLE_RUN_IDENTITY_STATIC=PASS`;
  - `publisher_identity_fault_matrix.py` — 40 fault cases executed against the
    *extracted bytes* of the two write-capable job scripts,
    `PUBLISHER_IDENTITY_FAULT_MATRIX=PASS`;
- a disposable RED/GREEN control builder
  (`build_control_refs.sh`) that derives controls from a workflow blob by a
  single branch-literal substitution.

No hosted control run of this session's variant was executed because the
disposable control branch name and the canonical branch name are both already
occupied by the parallel execution, and running further controls in parallel
would add conflicting evidence.

## 6. Requested PM disposition

One of the following is required before this session continues:

1. **Stand down (duplicate).** The parallel Window 28 execution is canonical;
   this session stops and publishes nothing further. (Default safe outcome.)
2. **Supersede / rerun (fresh window 28).** The PM rules the parallel candidate
   non-canonical (e.g. because of the post-freeze branch rewriting above), and
   authorizes this session to publish its own candidate under an explicit
   alternative canonical branch name.
3. **Freeze-and-revalidate.** The PM requires the parallel candidate to be
   re-frozen at an exact head with fresh post-freeze CI before acceptance.

Until that disposition arrives, this session publishes no candidate, performs no
Independent Acceptance, performs no merge, and does not touch `#330`, `#332`,
`#333` or `release/core-rc-refreeze-004-corrective-002-window28`.

`IA27-BLK-002` closure is **not** claimed by this file.
