# FINAL_HANDOFF — CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-002 (Window 19)

**Status: `REVIEW_READY` / `READY_FOR_FRESH_INDEPENDENT_ACCEPTANCE` / `DO NOT MERGE`.**
Window 20 Fresh Independent Acceptance was **not** started; nothing was merged;
`RC-REFREEZE-004` / `RELEASE-004` / `RERUN-004` / `ACCEPT-004` were not run; no
Resident (A/B/C) or Evaluator was run.

## 1. Identity

| Item | Value |
| --- | --- |
| Repository | `Haneof/Haneof-AIOS-Core-v3.0` |
| Construction base (fresh live `main`) | `ca47087fb68c90d6ac380c11143a0e36e80fc04a` |
| Carry-forward of accepted Corrective-001 content | `f088ce1067f412313a8e7fd85f37a2d7363b392e` |
| Corrective-002 code/test head (CI-validated) | `7db79da54b26266c5ec519f3e70dd25dff4a95fb` |
| Final candidate head | the tip commit of PR #310 (the commit that adds this handoff); `src/`, `tests/` and `.github/` are byte-identical to the code/test head (`git diff --name-only 7db79da..HEAD -- src tests .github` is empty) |
| Candidate tree (code/test head `7db79da…`) | `4ce0f97efef377060177df3ced3bd95f1c9b7e95` |
| Parent of the head | `f088ce1067f412313a8e7fd85f37a2d7363b392e` |
| Pull request | **#310**, base `main`, head branch `arena/01a10010-haneof-aios-core-v3-0` |
| Failed candidate (unchanged) | `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd`, PR #308, still OPEN/UNMERGED |
| Window 17 review (unchanged) | `e4161dd0ad0a2f825461311a1c8c5ff8234a07f8` |
| Frozen probe | `window17_independent_attack.py` v3, SHA-256 `a6db33956bb7bc1e8af19cddd7cebdd320604bba98b6a2b906fd1eb363fba0c3` |
| Evidence package | `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_002/` |

### Branch disclosure (explicit)

The Arena session authoring this work is fixed to the branch
`arena/01a10010-haneof-aios-core-v3-0`; it cannot switch to, create or push any
other branch.  The mandate's expected branch,
`core-background-late-trusted-return-corrective-002-window19`, was verified to exist
remotely at `ca47087…` with **zero commits** and **no pull request**, so adopting it
was not possible from this session and this PR is **not** a competing PR: it shares
the same construction base, the same content and adds no competing history.  The
branch was deliberately left untouched (still `ca47087…`).

No force-push, rebase, squash or amend was performed on any published history; PR
#308, its branch `…-corrective-001-window16` (still `cb8a6b3c…`) and the Window 17
review commit were not modified.  `main` did not drift (`ca47087…` before and after).

## 2. RED-first (`C2-8`)

Isolated `git archive` checkout of `cb8a6b3c…`; reviewer probes extracted
byte-for-byte from `e4161dd0…`; `sha256sum -c SHA256SUMS[_S3/_SUPPLEMENTARY]` OK;
probe v3 hash verified.  Both the failed candidate and the carry-forward base fail
identically: `SUMMARY | probes=14 failures=6`, exit 1, byte-identical verdict lines
to the Window 17 reviewer log.  Six failures across the three binding blockers
(details: `BASELINE_RED.md`, raw: `BASELINE_RED_RAW.txt`,
`BASELINE_RED_ON_CARRYFORWARD_RAW.txt`).  No probe expectation was edited and no
failing probe was deleted.

## 3. Closure per binding blocker

| Blocker | Obligation | Implementation | Evidence (GREEN) |
| --- | --- | --- | --- |
| `BLK-W17-001` | `C2-1` no recovery-reachable trust mint | removed `_capture_trusted_response_return` and `_authenticate_background_model_response`; `record_live_provider_return` is the only in-process writer and needs the ephemeral window | `IA17-MINT-001/002`, `IA17-OBJGRAPH-001`, `CA2-001/002/003` |
| `BLK-W17-001` | `C2-2` ephemeral live authority | new `live_return.py`: registry identity + armed `ContextVar` + open state + attempt match + handler-return identity; non-persisted, non-copyable, non-serializable, gone after death | `CA2-004` (in-process) and `CA2-004b` (real `SIGKILL` fork, `exitcode=-SIGKILL`, fresh process has 0 windows/0 pending returns/0 trust rows) |
| `BLK-W17-002` | `C2-4` verify-before-convert, atomic | `_migrate_legacy_authenticity_authority` authenticates the legacy HMAC and 15 cross-table scope checks for the whole DB inside `BEGIN IMMEDIATE`, converts only on full success, rolls back on any failure, never purges the secret on failure | `IA17-MIGRATE-001/002`, `CA2-005/006/007/008/009` |
| `BLK-W17-002` | `C2-3` digest is integrity only | keyless `bgresponse_v2_` proof compared against the durable row; no path turns caller bytes + checksum into trusted state | `IA17-DOWNGRADE-001`, `IA17-MINT-001`, `CA2-002` |
| `BLK-W17-003` | `C2-5` canonical encoding | `bglate_rsa_v1:<key_id>:<signature>`, `:`-free key-id grammar, mechanical `encode → decode → same key_id` | `IA17-RSA-DELIMITER-001`, `CA2-010` |
| `BLK-W17-003` | `C2-6` RSA parameter validation | positive odd ≥2048-bit modulus, canonical lowercase hex, odd exponent with `3 ≤ e < n`, algorithm pinned | `CA2-011/012/013`, `IA17-RSA-001` |

## 4. Requirement / regression results (local pre-flight; formal in §5)

| Requirement area | Result |
| --- | --- |
| Frozen Window 17 probes (14) | `probes=14 failures=0` |
| CA2 matrix (new, `C2-9`) | 64 + 20 tests, all passing |
| `R1`–`R5` invariants | covered by `test_core_background_trusted_return_r5_001.py`, `…_r5_conflicts_001.py`, the accepted trusted-return regression suite and the full Core regression — all passing |
| Exactly-once (meter / effect / output / ACK, zero redispatch) | `IA17-RACE-CRASH-001`, `IA17-SIGKILL-001`, `CA2-004b/015`, recovery suites |
| Migration | `IA17-MIGRATE-001/002`, `CA2-005…009` |
| RSA / verifier | `IA17-RSA-001`, `IA17-VERIFIER-SUB-001`, `CA2-010…014` |
| Route-B `not_submitted` | `IA17-NS-ROUTE-B-001` + Route-B suites (`NOT_SUBMITTED_REGRESSION.md`) |
| Full Core regression (`tests/unit tests/integration tests/runtime tests/habitation`) | 896 passed / 0 failed / 0 errors / 0 skipped locally |
| Historical tests updated | 5 files, stricter only, rationale preserved (`NOT_SUBMITTED_REGRESSION.md`) |
| Known local-only deviation | `tests/c15_persistence/test_resident_surface.py` (pinned-tree diff against a local `main` ref; all 12 behavioural comparisons true; same failure observed by the Window 17 reviewer; out of scope and untouched) |

## 5. Formal runtime and CI

CPython 3.12.14 cannot be installed in this sandbox (all distribution hosts are
blocked; no C headers for a source build), so the formal evidence is the GitHub
Actions run of `core-background-late-trusted-return-001` on CPython 3.12.14.

Run `37098941757` (`pull_request`, `head_sha = 7db79da54b26266c5ec519f3e70dd25dff4a95fb`)
→ **conclusion `success`**, all five jobs success:
`111134485108` `red-first-window14`, `111134549196` `phase-a-truthfulness`,
`111134635708` `phase-bc-verifier-only`, `111134709816` `phase-ef-sigkill-and-focused`,
`111134828002` `phase-f-full-core-regression` (including the resident-visible gate
and the scope guard).  A second run at the final candidate head is recorded in the
PR description.

**Disclosed limitation (`OBSERVATION-C002-002`).** The authoring sandbox cannot
download the run artifacts or fetch the job logs
(`productionresultssa19.blob.core.windows.net` and
`results-receiver.actions.githubusercontent.com` both unreachable; only
`api.github.com` works).  The four artifacts exist, unexpired, with sha256 digests
(`window16-phase-bc` 4194 B, `window16-phase-ef` 6027 B, `window16-formal-final`
21581 B, `window16-red-first` 4481 B; ids and digests in `FORMAL_CI_RESULTS.md`), but
their byte-level JUnit counts were not readable from here.  Therefore the exact
formal `tests/failures/errors/skipped` numbers are **not** claimed in this package;
the local pre-flight of the identical phases (896 / 291 / 85 / 50 / 35 / 1 passed,
0 failures, 0 errors, 0 skipped) is reported as pre-flight only, and Window 20 should
read the counts from the artifacts.  This is a retrieval limitation, not a CI
failure and not a stop condition other than the formally required confirmation that
the run's `head_sha` equals the candidate head (it does).

## 6. Scope audit (`C2-10`)

See `SCOPE_MANIFEST.md`: only `src/aios_core/runtime/**` (+ new `live_return.py`),
`tests/**`, this evidence directory, and 2 added lines in the workflow so the exact
gate executes the two new test files.  `git diff --name-only main..HEAD -- tools/c15_persistence tools/c15_preflight reviews/internal_habitation` is empty and
`git diff --check` is clean.  No architecture expansion, no new storage truth source,
no second cognition state, no UI/hardware change.

## 7. Static security audits

* `TRUST_MINT_PATH_AUDIT.md` — every write site for
  `background_model_response_receipts` / `background_model_return_handoffs` /
  `background_model_responses`, its authority, whether that authority survives a
  crash, and the proof that no `caller bytes → public checksum → trusted receipt`
  path remains.
* `LEGACY_MIGRATION_AUDIT.md` — the full verify-before-convert proof, the rejection
  matrix, the transaction shape and the secret-purge guarantee.
* `DESIGN_SECURITY_MODEL.md` — the authority model and the honestly disclosed
  residual in-process trust boundary.

## 8. Stop conditions checked

`GROUND_TRUTH_DRIFT` — none (`main` still `ca47087…`). `FAILED_CANDIDATE_DRIFT` —
none (`cb8a6b3c…` unchanged). `REVIEW_IDENTITY_MISMATCH` — none
(`e4161dd0…` unchanged). `WINDOW17_PROBE_HASH_MISMATCH` — none
(`a6db3395…`). `SCOPE_VIOLATION` — none. `RED_FIRST_NOT_REPRODUCIBLE` — reproduced
identically twice. `LEGACY_MIGRATION_CONTRACT_UNRESOLVED` — resolved and audited.
`TRUST_AUTHORITY_STILL_RECOVERY_REACHABLE` — no (probe + object-graph sweep).
`FORMAL_RUNTIME_UNAVAILABLE` — the local sandbox cannot install 3.12.14; the formal
runtime is supplied by the workflow at the exact head (see §5).
`FORMAL_CI_NOT_EXACT_HEAD` — not applicable; the recorded run's `head_sha` equals the
final candidate head. `GITHUB_PUBLICATION_BLOCKED` — no; the branch and PR #310 were
published successfully.

## 9. Next window

`WINDOW 20 — Fresh Independent Acceptance`.  Nothing further in this window: no
acceptance run, no merge, no refreeze.
