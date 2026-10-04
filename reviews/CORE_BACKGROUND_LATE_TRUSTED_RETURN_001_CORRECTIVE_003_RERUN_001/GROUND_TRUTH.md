# GROUND_TRUTH — Window 22-RERUN-001

Formal task: `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-003`
Window: `22-RERUN-001`
Role: Core Runtime Corrective Engineer (author-side only; NOT Independent Acceptance, NOT merge owner)
Repository: `Haneof/Haneof-AIOS-Core-v3.0`
Verification method: `git fetch --all --prune` + `git fetch --deepen` + GitHub REST API (`gh api`), all fresh at window start.
Verification timestamp (UTC): 2026-10-03T13:3x (see per-row raw evidence below)

---

## 1. Live main (fresh, not the prompt's quoted baseline)

| item | value | source |
|---|---|---|
| live `origin/main` | `1541b1ec1a8b40bdc67debd52af986c2869ee00e` | `git rev-parse origin/main` after `git fetch --all --prune` |
| main commit subject | `Merge PR #317 governance: reopen Corrective-003 as Window 22 rerun` | `git log -1 --pretty=%s origin/main` |
| main commit author / date | `Haneof` / `Sat Oct 3 21:09:28 2026 +0800` | `git log -1` |
| PR #317 state | `MERGED` at `2026-10-03T13:09:28Z` | `gh pr view 317 --json state,mergedAt` |

**Result: MATCHES the PM-stated live main exactly. No drift.**

The pre-window local checkout was at `054d15cd6ac52718c39ec34d388dd3186d6f7929`
("Merge PR #316 governance correction: restore publication recovery to Window 23A").
The fetch advanced `origin/main` `054d15c..1541b1e`. All construction in this window is
based on the **fresh live main `1541b1e`**, never on the stale pre-window checkout.

---

## 2. Governance release artifact present in live main

`governance/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_003_WINDOW22_RERUN_RELEASE_2026-10-03.md`
— present in `origin/main` tree (verified with `git ls-tree -r origin/main --name-only`).

Related governance identities also present in live main and **left untouched** by this window:
- `governance/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_003_PUBLICATION_RECOVERY_RELEASE_2026-10-03.md`
- `governance/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_003_SCOPE_PUBLICATION_CLARIFICATION_2026-10-03.md`

---

## 3. PR #310 — frozen failed Corrective-002 candidate

| item | value |
|---|---|
| number | `310` |
| state | `OPEN` (unmerged) |
| isDraft | `false` |
| base | `main` |
| head ref | `arena/01a10010-haneof-aios-core-v3-0` |
| head oid | `fec30bd1495017bf13f08b0ef5b1e241dfb0e247` |
| title | `[IA_FAIL / blocker=1 / FROZEN / DO NOT MERGE] CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-002 — PM adjudicated; Corrective-003 READY` |

**MATCHES the PM-stated exact failed Corrective-002 candidate `fec30bd1495017bf13f08b0ef5b1e241dfb0e247`.**

Commit identity of `fec30bd`:
- subject: `docs(reviews): publish Corrective-002 evidence package at the CI-validated code head`
- parent: `7db79da54b26266c5ec519f3e70dd25dff4a95fb`
  (`fix(core): close Window 17 trust-mint, downgrade/migration and RSA blockers (Corrective-002)`)
- `fec30bd` itself changes **no source or test byte** relative to `7db79da` — confirmed by blob
  comparison of every carried path (`BASE` blob == `FEC` blob for all 21 paths).

PM reset comment on PR #310: id `5969477812`, author `Haneof`, created `2026-10-03T13:09:42Z`,
body begins `## PM reset — previous Window 22 candidate was local-only; WINDOW 22-RERUN-001 is READY`.
**MATCHES the PM-stated comment id `5969477812`.**

This window does **not** commit to, push to, force-push, rebase, squash or amend PR #310 or its
head branch `arena/01a10010-haneof-aios-core-v3-0`. It is read-only historical material.

---

## 4. PR #311 — frozen review-only / evidence-only branch

| item | value |
|---|---|
| number | `311` |
| state | `OPEN` (unmerged) |
| isDraft | `false` |
| base | `main` |
| head ref | `arena/01a1006b-haneof-aios-core-v3-0` |
| head oid (current remote review tip) | `fd52ea8243970187b439208d7061c04c68b6b8ea` |
| title | `[REVIEW-ONLY / EVIDENCE-ONLY / DO NOT MERGE] WINDOW 20 Fresh IA of PR #310 fec30bd — ACCEPTANCE_FAIL / blocker=1` |

**MATCHES the PM-stated current remote review tip `fd52ea8243970187b439208d7061c04c68b6b8ea`.**

This window does **not** commit to, push to, modify, or merge PR #311 or its head branch.

---

## 5. Canonical review commits

| identity | value | verified present in GitHub object graph | subject |
|---|---|---|---|
| canonical Window 20 review | `220311759e88fb3948ad3f4dba655058e0f392a8` | YES (`git cat-file -e`) | Window 20 Fresh IA review evidence for PR #310 |
| canonical Window 17 review | `e4161dd0ad0a2f825461311a1c8c5ff8234a07f8` | YES (fetched by explicit SHA; also `refs/heads/arena/01a0fd4d-haneof-aios-core-v3-0`) | `docs(reviews): publish Window 17 Fresh IA review evidence for PR #308 (ACCEPTANCE_FAIL / blocker=3 / DO NOT MERGE)` |

**Both MATCH the PM-stated identities. No `WINDOW20_REVIEW_IDENTITY_MISMATCH`.**

Retrieval note (disclosed, not drift): the sandbox clone is **shallow**. `fec30bd`,
`2203117` and `fd52ea8` became available after `git fetch origin pull/310/head` and
`git fetch origin pull/311/head`; `e4161dd` required an explicit
`git fetch origin e4161dd0ad0a2f825461311a1c8c5ff8234a07f8`. All four are genuinely
present server-side — this is a local clone-depth artifact, not remote absence.

---

## 6. Prior Window 22 local-only candidate — confirmed NON-DURABLE

| item | value |
|---|---|
| prior reported Corrective-003 head | `39917591f07c2ed1aa679f9098c1fc368c3af42e` |
| present in GitHub object graph? | **NO** — `git cat-file -e` fails locally after full fetch of `main`, `pull/310/head`, `pull/311/head`, and `e4161dd`; no remote ref points at it (`git ls-remote origin` full ref dump contains no such sha) |
| prior Window 22 classification (PM) | `HISTORICAL_LOCAL_ONLY` / `NON_DURABLE` / `NOT_ACCEPTANCE_EVIDENCE` |

Consequences honoured by this window:
- `39917591f07c2ed1aa679f9098c1fc368c3af42e` is **not** used as a source candidate.
- No attempt is made to reconstruct it.
- Its reported candidate SHA / local test counts / local evidence / local bundle hash / local C3
  results are used for **navigation and claims-to-re-prove only**, never as acceptance evidence.
- Everything asserted in this window is re-proved from scratch on durable remote objects.

---

## 7. Frozen blocker (unchanged, sole binding blocker)

- id: `BLK-W20-001`
- full name: `RECOVERY_CALLER_TRUSTED_RETURN_MINT_ORACLE_VIA_SELF_ISSUED_EPHEMERAL_WINDOW`
- root cause: `TRUST_AUTHORITY_ISSUANCE_REMAINS_CALLER_MANUFACTURABLE`

Public/ordinary-process-reachable surface confirmed present at `fec30bd` (this is the oracle):
- `src/aios_core/runtime/live_return.py:156` `open_live_provider_return_window(...)` (exported in `__all__`)
- `src/aios_core/runtime/live_return.py:191` `register_handler_return(...)` (exported in `__all__`)
- `src/aios_core/runtime/background_attempt.py:2416` `BackgroundModelAttemptStore.record_live_provider_return(...)`
- consumed by `src/aios_core/runtime/cognitive_runtime.py:210` and `:407`
- consumed by `src/aios_core/runtime/turn_runtime.py:1362`

---

## 8. Construction base and merge-base facts

| item | value |
|---|---|
| fresh construction base | `1541b1ec1a8b40bdc67debd52af986c2869ee00e` (live `origin/main`) |
| carry-forward source | `fec30bd1495017bf13f08b0ef5b1e241dfb0e247` (frozen failed Corrective-002 candidate) |
| `git merge-base(main, fec30bd)` | `ca47087fb68c90d6ac380c11143a0e36e80fc04a` — `Merge PR #309 governance adjudication: Corrective-001 ACCEPTANCE_FAIL / Corrective-002 READY` |
| main-side changes since merge-base in `src/aios_core/runtime/**`, `tests/**`, `.github/workflows/**` | **NONE** (`git diff --name-status ca47087 1541b1e -- src/aios_core/runtime tests .github/workflows` is empty) |

Therefore byte-exact carry-forward of the `fec30bd` engineering content onto fresh main is
**lossless**: no main-side change to any carried path can be clobbered. Per-path proof is in
`CARRY_FORWARD_MANIFEST.md`.

The branch base is **fresh live main**, not `fec30bd`; `fec30bd` is used only as a byte source.

---

## 9. Ground-truth verdict

No semantic drift detected in any key identity:

`GROUND_TRUTH_VERIFIED — NO GROUND_TRUTH_DRIFT — NO FAILED_CANDIDATE_DRIFT — NO WINDOW20_REVIEW_IDENTITY_MISMATCH`

Proceed to hard gate 2 (`PUBLICATION_CAPABILITY_PREFLIGHT.md`).
