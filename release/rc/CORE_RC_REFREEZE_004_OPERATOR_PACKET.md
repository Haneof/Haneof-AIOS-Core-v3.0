# CORE-RC-REFREEZE-004 — Operator Packet

**Task:** `CORE-RC-REFREEZE-004` · **Window:** 24 · **Repository:** `Haneof/Haneof-AIOS-Core-v3.0`
**Role:** Release PM / Release Engineer (no Core modification, no C15 corrective, no Resident, no acceptance).

**Terminal state of this packet:** `CORE-RC-REFREEZE-004 = REVIEW_READY` + `READY_FOR_INDEPENDENT_ACCEPTANCE` + `DO NOT MERGE`
(conditioned on the exact-head formal gate published to the candidate PR/commit comment; if that gate is red, this candidate is `BLOCKED` and the RED evidence stands).

---

## 1. Frozen software identity (§1, §3)

| Item | Value |
|---|---|
| Frozen software SHA | `1cee3c5ad12f4b9098232bae11b51df786c5eb2f` (PR #318 PM-integration merge, 2026-10-04T13:43:53Z) |
| Parents | `fb53cf938b138a67d1890618eed41282c61bce00`, `7ecb2250a488766915e1042a76472b3cd26d9107` (Window-23 IA-accepted candidate) |
| Repository tree | `70b2711258567863ea0d93025a6a07e39631726a` |
| `src/` tree | `b95b1ccf49b4e7fc6b145bba3eb49e481256cbd2` |
| `src/aios_core` tree | `16f1487e291b009c55bee402abfd79fdacbae960` |
| `tests` tree | `9db1bfa08143bc99fe03836e2752ee6e05694eb6` |
| `tools` tree | `63918ce81e47ccc20eb9da3a9bf17943d087a2d7` |
| `.github/workflows` tree | `72cde9d2dc2b35d071bfa36c954dac2faff4a803` |
| `pyproject.toml` blob / SHA-256 | `b38833c7537fa60d5c2f02ed4bb19158d8995a11` / `993a6e9dd821d8d5885f4cc1f2da0aa34d40284618097a1de507e885f2eaab30` |
| Per-file manifest | `reviews/CORE_RC_REFREEZE_004/source_manifest.json` (79 `src/aios_core` files, 123 `tests` files, 43 release-relevant workflows, constitution/baseline set) |

Package: `aios-core 0.3.0.dev0`, `requires-python >=3.12`, dependency `pydantic>=2.10,<3` (dev `pytest>=8,<9`), console script `aios-core-headless = aios_core.headless.cli:main`, no lockfile.

## 2. Drift audit vs fresh live main (§2)

- Freshly fetched live main: `ee4556989fea16a28d2c727eb345d48385a453fe` (PR #324 governance merge), observed 2026-10-04T14:39:04Z.
- 9 commits after the frozen software, all governance/checkpoint/review-evidence/publication transport.
- Aggregate delta: 5 files (checkpoint, task board, Corrective-003 PM integration record, RC-004 entry decision, RC-004 prompt).
- Protected-surface delta: **0** for `src/**`, `tests/**`, `pyproject.toml`, `.github/workflows/**`; `src`, `tests`, `tools`, `.github/workflows` trees are **identical** at the frozen SHA and live main.
- PR #321 (`22aa00cb…`, REVIEW_ONLY, Window-23 reviewer evidence) and the Window-23 publication staging branch/workflow are excluded from software.
- **No unadjudicated implementation drift** ⇒ §2 does not trigger `BLOCKED`.

## 3. Environment (§4)

Formal pins: **CPython 3.12.14, Pydantic 2.13.5, pytest 8.4.2, SQLite 3.45.1**. Local candidate runs used a self-built CPython 3.12.14 on Debian 12 / Linux 6.1.158+ / x86_64 (no `_ssl` in the sandbox interpreter; Core imports no `ssl`). The CI gate records the GitHub runner's OpenSSL/OS/kernel identity for the same frozen software. Details: `reviews/CORE_RC_REFREEZE_004/environment_manifest.txt`.

## 4. Fresh regression (§5) — PASS

- **Core gate `tests/unit tests/integration tests/runtime tests/habitation`: 928 tests, 0 failed, 0 errors, 0 skipped.** Fresh run on the frozen commit; the prior window's number was not inherited.
- Focused: trusted-return group **388 passed**, Core-systems group **341 passed**, FIX spot checks **24 passed**, writer/restart/scale **52 passed**, real-SIGKILL selection **9 passed**.
- Full repository: **1137 tests, 45 failed, 0 errors** — every failure under `tests/c15_persistence/**` (see §7).

## 5. Frozen reviewer probes (§6) — PASS

Extracted fresh from the canonical reviewer commits (never from author copies), blob-verified and SHA-256-verified, then executed against the frozen worktree:

| Probe | Canonical commit | SHA-256 | Result |
|---|---|---|---|
| W20 Suite A | `220311759e88fb3948ad3f4dba655058e0f392a8` | `ec1dc5c2…292b5` | **4 / 0** |
| W20 Suite B | `220311759e88fb3948ad3f4dba655058e0f392a8` | `7692424658…8eb1` | **7 / 0** |
| W17 | `e4161dd0ad0a2f825461311a1c8c5ff8234a07f8` | `a6db3395…ba0c3` | **14 / 0** |

Details and raw outputs: `reviews/CORE_RC_REFREEZE_004/probes.md`, `raw/local/window20-suite-a.txt`, `window20-suite-b.txt`, `window17-probe.txt`.

## 6. Corrective-003 security spot checks (§7) — PASS

Local trust authority removed; `live_return.py` tombstone inert and outside the authorization chain; AST inventory shows the **only** durable trust writers are `attach_late_trusted_return` (receipt/handoff/verifier) and `stage_exact_response` (staged exact response), with no trust write on the `response_returned` live path; durable external verifier + genuine proof still required; alternate-mint, verifier-less, transplant, conflict and replay attacks fail closed; exactly-once meter/effect; partial commit recovers or refuses without duplicate effect. Registry inventory: 43 reachable / 22 side-effecting, `REGISTRY_MATRIX_PASS`. Details: `reviews/CORE_RC_REFREEZE_004/trusted_return_authenticity_spot_checks.md`.

## 7. C15 downstream debt (§13) — RULED

`CORE_FREEZE_NOT_BLOCKED_BY_DOWNSTREAM_OPERATOR_DEBT` + `C15_OPERATOR_ADAPTATION_REQUIRED_BEFORE_RESIDENT`.

All 45 full-repository failures are under `tests/c15_persistence/**` and exercise `tools/c15_persistence/**`; zero non-downstream failures. The operator code itself documents the Route B boundary (`DurableTrustedReturnMissing`: *"Accepted Core deliberately has no legal path that lets a recovery caller turn externally supplied bytes into a trusted provider return. The operator therefore stops fail-closed…"*). These suites still expect a Core-owned durable trusted return on the ordinary local path — the authority accepted Corrective-003 removed. Restoring the rejected local self-trust path is forbidden. RED preserved unmodified; no repair performed. Details: `c15_downstream_adjudication.md`.

## 8. Process loss, headless, backup/restore, writer/restart (§8–§11) — PASS

- **Real process loss:** SIGKILL selection 9 passed; W17 `IA17-SIGKILL-001` recovers from a real `SIGKILL` child (`exitcode=-9`) with 1 meter, 1 effect, no redispatch, replay blocked.
- **Clean install / headless:** `HEADLESS_CLEAN_INSTALL_PASS` from a non-editable install of a clean export; 5 separate CLI processes; World revision 2 / index watermark 2 / lag 0 / `AUTO_RECOVERABLE`; no Resident fixture.
- **Backup / restore / rebuild:** `BACKUP_RESTORE_REBUILD_PASS` — backup and source immutable, per-table logical state preserved, verifier/receipt/handoff continuity, index rebuilt from World truth, and **restore does not widen trusted-return authority** (forged/transplanted/verifier-less refused; genuine proof exactly-once; completed replay fails closed).
- **Writer / restart:** `WRITER_RESTART_PASS` — canonical same-World writer exclusion in-process and cross-process, validation-only lock override, stale metadata cannot block restart, restart continuity, completed-turn resubmission fails closed with no duplicate meter/effect.
- **Historical FIX/current-time:** 24 passed (FIX-001 cutoff, FIX-002 ambiguous background dispatch + restart no-reinvoke, FIX-003 ambiguous user turn, current-time control).

## 9. Open-PR / branch contamination (§15)

Fresh inventory of **52 open PRs** (snapshot `open_pr_snapshot.json`). Required classifications recorded in `open_pr_contamination_review.md`: #310, #311, #308, #305 (failed/frozen candidate lines), #321 (REVIEW_ONLY doc-only), #325 (transport publication candidate for this window — **not reused**), Window-23 publication staging branches (transport only), C15 persistence/operator historical WIP (#258/#216/#251/#249/#261 — not auto-absorbed), older implementation-touching PRs (#110/#111/#113/#126/#130/#144). Open ≠ accepted; nothing is imported into the frozen identity.

## 10. RC impact (§14)

`FRESH_A_REQUIRED` + `FRESH_OPERATOR_PREP_REQUIRED`. A-003/A-004 are prior-RC historical only; **no hash-swap**. Mechanically: `src/aios_core` changed **6 files, +1733 / −215** vs the prior RC's frozen software (Corrective-003 trusted-return/recovery boundary). Legal downstream order (later, separately authorized windows): this RC → Fresh Independent RC Acceptance → PM Integration → C15 operator/persistence compatibility corrective against the frozen RC → Fresh IA of that corrective → Fresh Resident A only on explicit PM release. Steps 2–6 are forbidden in Window 24 and were not performed.

## 11. Candidate and formal CI (§17–§18)

- Branch: `arena/01a10764-haneof-aios-core-v3-0`.
- A **new** candidate PR is opened from this branch; the historical RC-REFREEZE-003 PR and the transport candidate PR #325 are **not** reused.
- Formal gate: `.github/workflows/core-rc-refreeze-004-formal-gate.yml` runs on the exact pushed head — frozen-identity and drift checks, fresh Core regression, reviewer-probe extraction + verification + execution, Corrective-003 mint inventory and security suites, real SIGKILL, clean install/headless, backup/restore (fresh probe; stale prior-window probe recorded non-gating), writer/restart, FIX/scale, C15 adjudication, open-PR inventory, source manifest and SHA256SUMS — then publishes a commit comment and uploads the evidence artifact.
- After that run **no evidence-only commits are added**; run id, environment and results are recorded in the candidate PR body/comment.

## 12. Known limitations and non-claims

See `known_limitations.md`. Not independent acceptance; not merged; no Resident, evaluator/close, C15 corrective, public release/tag, UI/hardware, or multi-host/HA claim.

## 13. Terminal state

```
CORE-RC-REFREEZE-004 = REVIEW_READY
READY_FOR_INDEPENDENT_ACCEPTANCE
DO NOT MERGE
```
