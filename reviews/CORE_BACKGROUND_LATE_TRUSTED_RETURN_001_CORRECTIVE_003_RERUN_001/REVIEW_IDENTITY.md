# REVIEW_IDENTITY — Window 22-RERUN-001

Canonical reviewer evidence identities that this window is bound to. Both were verified present
in the GitHub object graph before any source edit, and both are re-verified mechanically by the
formal workflow.

## 1. Window 20 Independent Acceptance review

| item | value |
|---|---|
| full SHA | `220311759e88fb3948ad3f4dba655058e0f392a8` |
| short SHA | `2203117` |
| reachability | ancestor of `refs/pull/311/head` (`fd52ea8243970187b439208d7061c04c68b6b8ea`, PR #311 **OPEN, UNMERGED**) |
| evidence directory at that commit | `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_002_IA_WINDOW_20/` |
| verdict recorded there | Window 20 Independent Acceptance — the source of `BLK-W20-001` |
| frozen probe directory | `…/reviewer_probes/` |

Drift guard: the workflow asserts
`git merge-base --is-ancestor 2203117… refs/pull/311/head` and fails with
`WINDOW20_REVIEW_IDENTITY_MISMATCH` otherwise.

## 2. Window 17 Independent Acceptance review

| item | value |
|---|---|
| full SHA | `e4161dd0ad0a2f825461311a1c8c5ff8234a07f8` |
| short SHA | `e4161dd0` |
| reachability | tip of `refs/heads/arena/01a0fd4d-haneof-aios-core-v3-0` |
| commit message | `docs(reviews): publish Window 17 Fresh IA review evidence for PR #308 (ACCEPTANCE_FAIL / blocker=3 / DO NOT MERGE)` |
| committed | `2026-10-02T16:35:39Z` |
| evidence directory at that commit | `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_001_IA_WINDOW_17/` |
| frozen probe directory | `…/reviewer_probes/` |

Drift guard: the workflow asserts the branch tip still equals `e4161dd0…` and fails with
`WINDOW17_REVIEW_IDENTITY_MISMATCH` otherwise.

Retrieval disclosure (also recorded in `PROBE_MANIFEST.md`): `e4161dd0…` was not reachable from
the shallow sandbox clone until an explicit `git fetch origin e4161dd0…`. GitHub confirmed the
commit server-side. This was a local clone-depth artifact, **not** remote absence and **not**
identity drift.

## 3. Frozen reviewer probe identities

All three are verified twice — git **blob id** and **SHA-256 of the extracted bytes** — before
every execution, in a dedicated `probe-identity-verification` job and again inside each job that
runs a probe.

| suite | canonical review commit | path at that commit | git blob | SHA-256 | probes |
|---|---|---|---|---|---|
| Suite A | `2203117…` | `…_IA_WINDOW_20/reviewer_probes/window20_independent_attack.py` | `527edd8d92243cabc417f176c0f7c4f6c358e65c` | `ec1dc5c2c5406d5d9e74825f62e0a17fb80f8ebd6dc250817fa048511ce292b5` | 4 |
| Suite B | `2203117…` | `…_IA_WINDOW_20/reviewer_probes/window20_migration_rsa_attack.py` | `867f0ee993595c2d334a3940ad66308166693c97` | `769242465817f31734661ba7ba9c3d5f7d06b8d3f5235d72d2026956d9b98eb1` | 7 |
| W17 | `e4161dd0…` | `…_IA_WINDOW_17/reviewer_probes/window17_independent_attack.py` | `bb25d184a5cb813ae4058de9a75fa23d9591b041` | `a6db33956bb7bc1e8af19cddd7cebdd320604bba98b6a2b906fd1eb363fba0c3` | 14 |

Mismatch raises `WINDOW20_PROBE_HASH_MISMATCH` / `WINDOW17_PROBE_HASH_MISMATCH` and fails the run.

Superseded sibling drafts at the same paths that were deliberately **not** used (recorded so the
choice is auditable): `window20_independent_attack_v1.py`
(`b1ad43619eea38c5b5b14bb09161f4950c7ace4f`),
`window20_independent_attack_v2_defective.py` (`224135e373dfa0ca106dbb5b17d0fc17d2249872`),
`window20_migration_rsa_attack_v1_defective.py` (`22c8455bc81054d71eaef1dda6f7bc4c9db59d46`),
`window20_migration_rsa_attack_v2.py` (`5ad3530733293f8c12842a4f01bf932f899e8739`),
`window17_independent_attack_v1.py` (`0dc5546f12d2d4f88657ad2a7767a2f4bda7b8d6`),
`window17_independent_attack_v2.py` (`9a7105aa613ef57a7612918311ff9d5024ff6a9b`).

## 4. Constraint compliance

* Reviewer probe bytes are **never** modified, copied into the tracked tree, edited, wrapped or
  re-ordered (contract `C3-6`). The `probe-identity-verification` job fails the run if any
  `window1[7]_*attack*.py` / `window20_*attack*.py` path appears in this branch's tracked tree.
* Window 17 and Window 20 reviewer evidence directories are on the forbidden-path list enforced
  by `scope-discipline-and-identity-guard`; they are untouched
  (`out_of_scope = 0`, `forbidden_paths = 0`).
* PR #310 and PR #311 branches were never committed to, force-pushed, rebased, squashed or
  amended.
* This window performs **no** Independent Acceptance. It stops at
  `REVIEW_READY / READY_FOR_FRESH_INDEPENDENT_ACCEPTANCE / DO NOT MERGE`.

## 5. PM reset context

`WINDOW 22-RERUN-001` was declared READY by PM issue comment `5969477812` after governance PR
#317 merged (`2026-10-03T13:09:28Z`) and live main moved to
`1541b1ec1a8b40bdc67debd52af986c2869ee00e`. The prior Window 22 result was classified
`HISTORICAL_LOCAL_ONLY / NON_DURABLE / NOT_ACCEPTANCE_EVIDENCE`, Window 23A Publication Recovery
was `BLOCKED / ARTIFACT_UNAVAILABLE`, and Window 23 Fresh IA was `BLOCKED`. See
`GROUND_TRUTH.md` for the full verification transcript.
