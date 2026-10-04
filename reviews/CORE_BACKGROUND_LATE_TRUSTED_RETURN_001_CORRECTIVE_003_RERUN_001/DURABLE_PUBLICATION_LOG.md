# DURABLE_PUBLICATION_LOG — section 22 staged durable pushes

Branch: `arena/01a101e0-haneof-aios-core-v3-0` (the single engineering branch for this window)
Remote: `https://github.com/Haneof/Haneof-AIOS-Core-v3.0.git`
Base: live main `1541b1ec1a8b40bdc67debd52af986c2869ee00e`

Every stage below was pushed to the remote **before** the next stage began, so no window of work
existed only in the sandbox. That discipline is what made the interruption recorded in §3
recoverable with zero loss.

---

## 1. Push chain (11 commits before the final evidence batch)

| # | SHA | subject | stage |
|---|---|---|---|
| 0 | `1541b1ec` | live main (branch base) | — |
| 1 | `f858057` | evidence(rerun-001): fresh ground truth + GitHub publication capability preflight PASS | §22 stage: ground truth + publication capability proven **before** any source edit |
| 2 | `50a3e1f` | carry-forward(core): `BYTE_EXACT_CARRY_FORWARD_BASE` from `fec30bd1` onto fresh main | 21 code-bearing paths materialized byte-exact; `ALL_MATCH=YES` |
| 3 | `8e68674` | fix(core)!: Route B — remove caller-manufacturable live provider-return trust authority | Phase E source + `BASELINE_RED.md` + `PROBE_MANIFEST.md` + probe raw evidence |
| 4 | `66c3600` | fix(core): external proof supersedes unverified local provenance; TIGHTEN_ONLY rewrite of 3 historical suites | Option S refinement + `raw/GREEN_*_v2.txt` |
| 5 | `99b519c` | test(core): TIGHTEN_ONLY Route B rewrite of R5 exactly-once durable-effect suites | r5_001 + r5_conflicts_001 |
| 6 | `17cf57e` | test(core): TIGHTEN_ONLY Route B rewrite of the response-recovery fault matrix family | response_recovery_001 + corrective_001 + corrective_002_recovery |
| 7 | `2e67ec8` | test(core): TIGHTEN_ONLY Route B rewrite of the last five historical suites | full Core gate 900 passed / 0 failed / 0 errors |
| 8 | `1c85e15` | test(core): add C3 author attack matrix — 27 enumerated cases, RED 17/27 on `fec30bd1` | §16 matrix |
| 9 | `e6a6c31` | ci(core): replace the Window 16 formal gate with the Window 22-RERUN-001 Route B gate (12 jobs) | §17 workflow |
| 10 | `d07f980` | fix(ci,test): make the C3 matrix suite-isolation-safe and the Route B identity guard semantic | first formal-CI defect pair |
| 11 | `30022b0` | fix(ci): make the Route B semantic identity guard dependency-free | second formal-CI defect |

No commit was ever force-pushed, rebased, squashed or amended. History is linear on top of live
main, so `REMOTE_PUBLICATION_IDENTITY_CONFLICT` was never reachable.

## 2. Formal CI runs against these heads

| run id | head SHA | outcome | note |
|---|---|---|---|
| `37145194272` | `e6a6c31` | failure (2 of 12 jobs) | first ever run of the new gate; found two defects in **this window's own new material**, none in Core |
| `37147715445` | `d07f980` | failure (1 of 12 jobs) | `full-core-gate` now green at **928 passed in 129.79s**; only the scope guard's semantic step failed |
| `37147989026` | `30022b0` | failure (1 of 12 jobs) | 11 of 12 green; only `formal-environment-report-and-exact-head` failed, on a version-comparison bug in the workflow itself |
| final | this evidence batch's head | see `FORMAL_CI_RESULTS.md` | the workflow-only fix for the version comparison, plus the evidence batch |

Details, job-by-job verdicts and the environment report are in `FORMAL_CI_RESULTS.md`.

## 3. Sandbox interruption and recovery (disclosed)

Between two turns of this window the sandbox workspace was **rolled back**: the local clone's
`HEAD` was reset to the original branch point `054d15cd6ac52718c39ec34d388dd3186d6f7929`, the
local `preflight` virtualenv and `/home/user/.tooling` were removed, and `/tmp` (frozen probe
extractions, the `fec30bd1` worktree and all raw preflight outputs) was wiped.

**No work was lost**, because §22 staged durable pushes had already put every commit on the
remote. Recovery, in order:

1. `git ls-remote origin refs/heads/arena/01a101e0-haneof-aios-core-v3-0` →
   `30022b06e2795d20790dd4532bf6987146c1b432`, i.e. exactly the last pushed commit. The remote
   was confirmed to be the source of truth.
2. The four evidence documents written after that push were copied to `/tmp` first (untracked files
   survive `git reset --hard`, but they were backed up regardless).
3. `git fetch origin --prune` then
   `git reset --hard origin/arena/01a101e0-haneof-aios-core-v3-0` → `HEAD` back at `30022b06`,
   working tree clean apart from the four uncommitted documents.
4. The `preflight` virtualenv was rebuilt (`python3 -m venv`, `pytest==8.4.2`,
   `pydantic==2.13.5`) → CPython 3.11.2, pydantic 2.13.5, pytest 8.4.2, sqlite 3.40.1.
5. The three frozen probes were re-fetched by pinned ref and re-extracted from their git blobs;
   all three blob ids and SHA-256 values re-verified. `2203117…` was fetched directly by SHA,
   confirming server-side SHA-want support.
6. The `fec30bd1…` detached worktree was recreated at `/tmp/wt-fec`.
7. **Post-recovery re-verification**: Suite A `probes=4 failures=0`, Suite B `probes=7
   failures=0`, W17 `probes=14 failures=0`, and all three outputs are **byte-identical** to the
   archived `raw/GREEN_*_ON_CANDIDATE_v2.txt` evidence. The rollback therefore altered nothing in
   the candidate.

Classification: an infrastructure interruption, **not** `GROUND_TRUTH_DRIFT`, **not**
`FAILED_CANDIDATE_DRIFT` and **not** `REMOTE_PUBLICATION_IDENTITY_CONFLICT`. No stop condition was
reachable, because the remote identity was intact and verified at every step.

Consequence for the reviewer: the durable record on GitHub was never dependent on the sandbox.
Anything that existed only in `/tmp` was re-derived from pinned git objects, never from memory.

## 4. Post-formal-CI evidence channel

Section 22 forbids an evidence-only commit after the final formal CI run. Therefore:

* the final exact-head run id, its job-by-job verdicts and the environment report are recorded in
  the **PR body** and in **PR / commit comments**, not in a later commit;
* the formal workflow itself publishes each job's verdict and diagnostics tail as a **commit
  comment** (`if: always()`), which is the same channel and makes every job result readable
  through `api.github.com` without needing the Actions log or artifact blob hosts;
* `FORMAL_CI_RESULTS.md` in this batch documents runs `37145194272`, `37147715445` and
  `37147989026` in full and states exactly where the final run's identifiers are published.

The workflow's `permissions` were widened from `contents: read` to `contents: write` **solely** to
allow those commit comments. It performs no branch protection change, no merge, no tag, no release
and no write to any other repository object.

## 5. Branch-name deviation (disclosed)

The suggested engineering branch name for this task was
`core-background-late-trusted-return-corrective-003-window22-rerun-001`. The execution platform
for this window hard-binds the session to the branch
`arena/01a101e0-haneof-aios-core-v3-0` and cannot create, switch to or push any other branch name.

That bound branch **is** the new durable engineering branch required by the task: it is new, it is
remote, it is linear on fresh live main, it carries all work, and it is the head of the new PR.
The deviation is a naming difference only, with no effect on durability, identity or reviewability.
It is disclosed here and in `FINAL_HANDOFF.md`.
