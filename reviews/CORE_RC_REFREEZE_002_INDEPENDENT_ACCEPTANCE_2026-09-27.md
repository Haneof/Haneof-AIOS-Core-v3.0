# CORE-RC-REFREEZE-002-INDEPENDENT-ACCEPTANCE

**REVIEW-ONLY ARTIFACT — must not be merged as implementation. Produced by the Independent RC Re-Freeze Acceptance Reviewer window. It does not modify, approve downstream, or integrate PR #232.**

- Task: `CORE-RC-REFREEZE-002-INDEPENDENT-ACCEPTANCE`
- Tested exact RC candidate: **`a93972c95356f46d20f5e9e7be82026fe84c0687`** (PR #232 head; observed state OPEN / CLEAN / unmerged; no drift at review time)
- Frozen software (live `main` = freeze parent): `27a21db5b656d441248b9240020910b66a223830`
- Candidate parent: `91c93c4eb818960f16b89ca74d16e8ede72fa797`
- Verdict: **ACCEPTANCE_PASS**
- Blocker count: **0**
- Role boundary respected: candidate not modified; Core not fixed; #232 not merged; Resident not run; #216 not restored; A-RERUN-003 not entered.

## 1. Identity pinning

| Item | Value | How verified |
|---|---|---|
| RC candidate (PR #232 head) | `a93972c95356f46d20f5e9e7be82026fe84c0687` | live `gh pr view 232` + local ref `origin/pr232head`; re-checked immediately before publication |
| Candidate tree | `66d89a0344b68520b840690c43aead629e9f7957` | `git rev-parse a93972c^{tree}` |
| Frozen parent | `27a21db5b656d441248b9240020910b66a223830` | ancestry + PR metadata |
| Core tree (`src/aios_core`) | `a9618abe0b3d4ac3b08bd23dbd58f3e3f97e05d6` | `git rev-parse a93972c:src/aios_core`; identical on `27a21db`, `227327c6`, and both merge refs |
| tests tree | `92fcbcc5876833735fb3cb7c73a98c4a8a4a3541` | `git rev-parse a93972c:tests`; identical on `27a21db`, `227327c6`, both merge refs |
| Frozen `main` tree | `a2e6b03b306413a2d82ca4ca8c9fc7099c0dc065` | `git rev-parse 27a21db^{tree}` |
| Historical RC (prior freeze) | `773876f92d5f8e53422f8f5a68cc651953d93052`, Core tree `fe77f8a0706acfaf369041d0882b6d0e6de39f22` | `git rev-parse` (distinct from new freeze; no hash swap — see §12) |
| Corrective-002 accepted exact head | `227327c657788efb1b5de1bc26e69c35c900a85e`, Core tree `a9618abe…` (identical to frozen RC) | ancestry + `git rev-parse 227327c6:src/aios_core` |

Drift protocol: none triggered. PR #232 was OPEN / CLEAN, head unchanged at `a93972c9…`; no new candidate was self-selected.

## 2. Re-freeze, not a Core change (enumerated)

`git diff --name-status 27a21db a93972c` → **24 files, +1342 / −7**:
`.github/workflows/core-rc-refreeze-002-formal-gate.yml` (new), `AIOS_v3.0_CURRENT_CHECKPOINT.md`, `PROJECT_MASTER_MAP.md`, `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`, `release/rc/CORE_RC_REFREEZE_002_MANIFEST.json` (new), `release/rc/CORE_RC_REFREEZE_002_OPERATOR_PACKET.md` (new), `reviews/CORE_RC_FREEZE_002_COMPLETION_EVIDENCE_2026-09-27.md` (new), and the 17 files under `reviews/CORE_RC_REFREEZE_002/`.

- `src/**`: **ZERO diff** (tree `a9618abe…` on both sides)
- `tests/**`: **ZERO diff** (tree `92fcbcc5…` on both sides)
- `pyproject.toml`: no diff
- Only additions elsewhere are packet/governance documents and the freeze-gate workflow

## 3. Formal merge-ref gate equivalence — **MERGE_REF_EQUIVALENCE PROVEN**

| Merge ref | Tree | Parents | `src/aios_core` | `tests` |
|---|---|---|---|---|
| `f9e5cdc6f4ec9b26be1722779fb7f7756389bdc9` (GitHub-signed; final gate) | `66d89a03…` == candidate tree | `[27a21db5, a93972c9]` | `a9618abe…` | `92fcbcc5…` |
| `4da836b930d99e7c12162cba4e9bc5cffbbafb66` (earlier gate @`91c93c4e`) | `0c58c3b6…` (earlier packet state) | `[27a21db5, 91c93c4e]` | `a9618abe…` | `92fcbcc5…` |

The final gate merge ref reproduces the candidate tree **exactly** and both merge refs carry the identical frozen Core and tests trees. Independently re-derived with git only (no packet self-report). Verdict: `FORMAL_GATE_IDENTITY_NOT_PROVEN` **not** triggered.

## 4. Manifests

- `sha256sum -c reviews/CORE_RC_REFREEZE_002/SHA256SUMS` → **20/20 OK** (includes environment `d52ba545…`, release manifest `2036b3f5…`, operator packet `91fb6902…`, workflow `c615a87b…`, completion evidence `4be5621e…`).
- `source_manifest.json` self-hash: `34b3d8adfad376a9cd7170ebec3e6093d40444b03ffd61130ed79602e63e3883` (matches manifest pin); independent verifier → **127/127 entries exact**.
- Added-line identifier scan over all 24 packet files: **180/180 forty-hex tokens resolve as real git objects**; every sixty-four-hex token traces to SHA256SUMS, `source_manifest.json` entry hashes, or the pinned authenticity probe hash. No dangling or self-contradictory identifier; no stale RC SHA; no old-RC hash swap.

## 5. Formal environment

Pinned: Python **3.12.14**, pydantic **2.13.5**, pytest **8.4.2**, SQLite **3.50.4**. CI "Freeze environment identity" step recorded success (jobs API). CI raw logs are not retrievable in this sandbox (see §18 limitation); compensating evidence: an independent interpreter + wheel set was assembled to those exact pins and used for all review runs below.

## 6. Fresh full regression (from the new RC, not reused)

Independent, from a fresh extraction of the frozen software `27a21db` (Core/tests trees identical to the candidate):

```
763 passed, 0 failed, 0 errors, 0 skipped — 234.73s
```

JUnit: `/tmp/accept/ia-junit.xml`; log: `/tmp/accept/ia-full.log`. Matches the frozen gate's reported `763/0/0/0` (PR #232 comment, 184.08s) and the `Fresh full pytest -q` step success (11:08:24→11:11:29Z). Corrective-002 output was **not** reused.

## 7. Own adversarial RC probes (frozen → SHA256 → collect-only → executed; 17/17 PASS)

| Probe file | sha256 | Result |
|---|---|---|
| `test_ia_world_boundary.py` (11 runtime attacks) | `833fdac6f3392a4955ac493d9276e68952d01a02374bd309ebdfeec9b44a6aa2` | **11 passed** |
| `ia_freeze_integrity.py` (6 freeze attacks) | `e1b746b1c02a64eded4ee5e8cd88cf551e9be6079cbc65991399ec07d3a8d4d8` | **6/6 PASS** |

Harness history preserved unoverwritten: gen1 (4 harness bugs), gen2 (1), gen3 (2 expectation bugs on F5/F6 — corrected to the true invariants: “candidate tree + parents + identical Core/tests + only declared packet paths may differ”, and “flag only blobs absent from main history”), gen4 (final, run reported here).

| # | Named attack area | Probe | Result |
|---|---|---|---|
| 1 | Manifest tamper | F1 (recompute + single-byte mutation) | PASS |
| 2 | Wrong Core tree substitution | F2 (frozen vs historical tree) | PASS |
| 3 | Wrong tests tree substitution | F3 | PASS |
| 4 | Stale RC SHA swap | F4 (old/new RC pinned separately, ancestry-checked) | PASS |
| 5 | Merge-ref mismatch | F5 (tree/parents/trees/delta vs declaration) | PASS |
| 6 | Authority malformed / missing | family A (fail-closed) | PASS |
| 7 | Writer-lock bypass | family D (second writer busy; lock-path override rejected) | PASS |
| 8 | Restart duplicate side effect | family E (no re-dispatch, single meter) | PASS |
| 9 | Unauthenticated row migration | families B/C/D (no-proof staging rejected; legacy NULL-proof fail-closed; no upgrade) | PASS |
| 10 | Second truth store | family G (+ index projection rebuild) | PASS |
| 11 | Crash/restart (real SIGKILL) | family D (lock recovery after SIGKILL) | PASS |
| 12 | Backup / restore / rebuild | family F (authority+receipt preserved; forged second key rejects old receipts; logical table-hash comparison) | PASS |
| — | Open-PR contamination false-negative | F6 | PASS |

## 8. Headless

Independent `HeadlessCore` smoke run: one turn `HEADLESS_MECHANICAL_OK`; exactly 1 attempt `metered`, 1 receipt (`bgresponse_v1_…`), authority `trusted-return-v1`, 0 staged rows; world dir contains precisely `world.sqlite(+ -wal/-shm)`, `.search.sqlite`, `.writer.lock`. Packet `headless_smoke.md` consistent with these mechanics.

## 9. Writer / headless writer enforcement

Second concurrent writer → busy rejection; `lock_path`/`AIOS_LOCK_PATH` cannot select a second writer identity (rejected as configuration error); canonical lock remains `<world>.writer.lock`; recovery after kill acquires the lock correctly. PASS.

## 10. Recovery, crash/restart, exactly-once

Ordering provider-return → authenticate → record → meter is enforced before accounting; authenticity failure prevents all downstream effects. Legacy rows with NULL `authenticity_proof` remain fail-closed and are never silently upgraded. Real SIGKILL probe: no output duplication, no double metering, exactly-once capability/output semantics preserved across restart. PASS.

## 11. Backup / restore / rebuild

Restore carries the HMAC authority with the durable store so historical receipts still verify; a restore that fabricates a different key causes old receipts to reject (fail-closed, as required); backup/restore/rebuild equivalence verified on **logical table content** (file-byte comparison would be misled by WAL/SHM artifacts). PASS.

## 12. Authenticity spot checks (Corrective-002 line)

- Probe blob `6f0c3850368475e166d28d0a6df4b86b610d2c60` resolves in the object store; recomputed content sha256 **`35cba59f318b752ed872821961296f35810443c61db6fd98c8c8f5eee4215225`** == manifest `authenticity_probe_sha256`. Independently confirmed, not packet-reported.
- `227327c6…` (Corrective-002 accepted exact head) is an ancestor of the frozen RC and carries the **identical** Core tree `a9618abe…`.
- Receipt minting/verification, forged receipt, tampered receipt, no-proof staging, malformed authority → all correctly reject. PASS.

## 13. Scale (S10K / S100K / S1M)

`core-scale` run `36313973913` SUCCESS; focused suite includes scale semantics; thresholds **not** moved by this freeze (byte-identical scale tests — tests tree unchanged). PASS.

## 14. Legacy FIX-001 / FIX-002 / FIX-003

Focused 9-file authenticity/recovery/headless/scale/writer suite on the frozen tree: exit 0, **98 tests green** (`/tmp/accept/ia-focused.log`); packet `legacy_fix_spot_checks.md` consistent. PASS.

## 15. No second truth store

The added tables (`background_model_authenticity_authority`, `background_model_response_receipts`) live inside the same World SQLite; no second cognition DB, no external answer oracle, no fixture-answer leakage; index projection rebuild from the same store. PASS.

## 16. Open-PR contamination (independent)

All 22 open-PR heads scanned against their own merge-base with live main: only **#110, #111, #113, #126** change `src/`; #216 is tests-only; the remainder carry zero unmerged `src/`/`tests/`/`pyproject` content.
- #126's changed `src/` blobs are **verbatim historical versions of main's own files** (stale branch — its flagged content already lives in main history).
- #113 / #111 / #110 feature symbols (`valid_time`, `unknown_items`, `counter_evidence`, `TemporalExtent`, `evidence_policy`/`CognitionEvidencePolicy`) and their test modules **already exist in evolved, integrated form** in frozen main.

⇒ No competing unmerged Core implementation exists that could invalidate “sole frozen baseline”. False-negative attack (F6) PASS.

## 17. Known limitation honesty

Preserved as **NON_BLOCKING TRUST-ROOT LIMITATION**: in-process trusted code holding the trusted store/runtime object can reach the internal receipt-minting path or read the HMAC authority secret from SQLite. The freeze explicitly **does not** claim “there is no way to access the key”; it correctly scopes this outside the public-boundary invariant. Fail-closed behaviours (missing/malformed authority; historical rows not upgraded) verified by probe. Other carried limitations (no distributed multi-host writer coordination; `--lock` cannot select a second writer identity) are accurately disclosed.

## 18. Review limitations disclosed by this window (non-blocking)

- **NON_BLOCKING EVIDENCE-AVAILABILITY LIMITATION:** raw CI logs for run `36314755816` are not retrievable from this sandbox (four retrieval methods; the signed log-blob host returns EOF/302-empty). Compensating evidence: jobs API step-level success for all 9 steps (steps 7 "Fresh full pytest -q" and 8 focused both success with timestamps), the gate's JUnit `763/0/0/0` from the PR comment, and this window's **own** independent 763/0/0/0 run at the frozen software with the pinned environment — i.e. the invariant is affirmatively reproduced rather than merely read.
- Gate `36314228639` (intermediate head `c7796490…`) FAILED **only at step 9 (comment publish)**; steps 1–8 were green. Non-semantic, historically superseded by `36314420939` and `36314755816` (both success).
- Harness bugs found during probe development are preserved and documented (§7), not overwritten.

## 19. RC impact adjudication (independent)

| RC | Core tree | Disposition |
|---|---|---|
| Prior RC `773876f9…` | `fe77f8a0…` (distinct) | `A-RERUN-002 = HISTORICAL_FOR_PRIOR_RC_ONLY` |
| New freeze `27a21db5…` | `a9618abe…` | sole current frozen baseline → **`FRESH_A-RERUN-003_REQUIRED`** |

Old→new delta is exactly 6 runtime files (+1868/−78) with no test-tree drift; ancestry verified (`227327c6…`, `773876f9…` are ancestors; zero `src/`, `tests/`, `pyproject.toml` commits after `227327c6…`). No old-RC hash is silently reused for the new baseline.

## 20. Verdict

**ACCEPTANCE_PASS — blockers: 0.** The RC re-freeze is internally self-consistent, Core/tests-identical to frozen main, gate-merge-ref equivalent, manifest-verified, independently regression-clean (763/0/0/0) and adversarially probed (17/17). It can serve as the **only** frozen Core baseline for a subsequent fresh Resident `A-RERUN-003`.

This window performs no integration: PR #232 is **not** merged, `main` is **not** updated, no Resident is run, and `A-RERUN-003` is not entered. Downstream integration is a PM decision.

READY_FOR_PM_INTEGRATION
