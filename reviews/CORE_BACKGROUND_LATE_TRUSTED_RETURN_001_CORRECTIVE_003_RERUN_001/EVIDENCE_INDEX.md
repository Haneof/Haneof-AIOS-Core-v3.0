# EVIDENCE_INDEX — Window 22-RERUN-001

Task `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-003` · Window `22-RERUN-001`
Directory `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_003_RERUN_001/`
Branch `arena/01a101e0-haneof-aios-core-v3-0` · base live main `1541b1ec1a8b40bdc67debd52af986c2869ee00e`

Stop state: **`REVIEW_READY / READY_FOR_FRESH_INDEPENDENT_ACCEPTANCE / DO NOT MERGE`**

This index maps every contract requirement to the file that discharges it, so a reviewer never has
to guess where a claim is proven. `SHA256SUMS` covers every file below except itself.

---

## 1. The 19 entries in this package

| # | entry | what it establishes |
|---|---|---|
| 1 | `GROUND_TRUTH.md` | fresh live main, PR #310 / #311 / #317 states, PM reset comment `5969477812`, absence of the lost prior candidate `39917591…` |
| 2 | `PUBLICATION_CAPABILITY_PREFLIGHT.md` | GitHub write/publication capability proven **before** any source edit — the hard new gate for this rerun |
| 3 | `CARRY_FORWARD_MANIFEST.md` | the 21 code-bearing paths materialized byte-exact from `fec30bd1…` onto fresh main; `ALL_MATCH=YES`; merge-base proof that main touched nothing under `src/aios_core/runtime`, `tests` or `.github/workflows` |
| 4 | `PROBE_MANIFEST.md` | all three frozen reviewer probe suites: canonical review commit, path, git blob id, SHA-256, size, probe ids, summary-line format, and the superseded sibling drafts deliberately not used |
| 5 | `BASELINE_RED.md` | RED-first reproduction: Suite A `probes=4 failures=4` on `fec30bd1…` **and** byte-identical on the carry-forward base; Suite B `7/0` and W17 `14/0` as positive baselines; preflight environment disclosure |
| 6 | `FAILED_CANDIDATE_IDENTITY.md` | identity, reachability and drift status of the frozen failed candidate; the forbidden lost prior candidate; what it fails and what it passes |
| 7 | `REVIEW_IDENTITY.md` | identity and reachability of the Window 20 and Window 17 canonical reviews; frozen probe identities; constraint compliance |
| 8 | `DESIGN_SECURITY_MODEL.md` | Route B as built: what was removed, the tombstone's exact inert surface, the only remaining route to durable trusted return, why a live local return is no longer a trust root, the supersession design, the contract compliance map, the residual risk, and the object-identity ruling |
| 9 | `TRUST_MINT_AUDIT.md` | exhaustive writer inventory for all five durable background-return tables, attributed to enclosing functions, with a verdict per path; the single trust root and its gate; why the legacy migration and `stage_exact_response` cannot originate trusted state |
| 10 | `TIGHTEN_AUDIT.md` | the section-8 seven-item record for **all 13** historical test files modified TIGHTEN_ONLY, plus the modification scope table and the cross-file invariants |
| 11 | `C3_ATTACK_MATRIX.md` | the section-16 author matrix: 27 enumerated cases (13 + 13 + 1), the uniform durable properties P1/P2/P3, why properties rather than names, and the per-case RED status on the failed candidate |
| 12 | `INHERITED_OBSERVATIONS.md` | the section-10 inherited observation, classified `INHERITED_OBSERVATION / NOT_NEW_CORRECTIVE003_REGRESSION`, mechanically shown present in `fec30bd1…`, deliberately not fixed, plus how it forced the proof-comparison design; and the residual-risk observation |
| 13 | `SCOPE_AUDIT.md` | `out_of_scope = 0`, `forbidden_paths = 0`, build-artifact hygiene without touching root `.gitignore`, role scope, and the full stop-condition table |
| 14 | `DURABLE_PUBLICATION_LOG.md` | the section-22 staged push chain (11 commits), formal CI run history, the sandbox interruption and its zero-loss recovery, the post-formal-CI evidence channel, and the branch-name deviation |
| 15 | `FORMAL_CI_RESULTS.md` | the formal environment actually observed on CPython 3.12.14, run history, job-by-job verdicts for run `37147989026`, the gate-by-gate mapping, and where the final run's identifiers are published |
| 16 | `FINAL_HANDOFF.md` | the stop state, what was wrong and what was done, every required final gate, all eight disclosures, what the next window should check first |
| 17 | `EVIDENCE_INDEX.md` | this file |
| 18 | `SHA256SUMS` | integrity manifest for entries 1–17 and every file under `raw/` |
| 19 | `raw/` | 15 verbatim, unedited tool outputs (see §3) |

## 2. Requirement → evidence map

| contract / task requirement | discharged by |
|---|---|
| publication capability proven before source edits | 2, and `raw/PUBLICATION_CAPABILITY_RAW.txt` |
| fresh live main, not the prompt-quoted SHA | 1 |
| forbidden prior candidate `39917591…` not used or reconstructed | 1, 6 |
| byte-exact engineering carry-forward from `fec30bd1…` | 3 |
| frozen probes hash-verified before first execution; bytes unchanged (`C3-6`) | 4, 7, and CI job `probe-identity-verification` |
| RED-first reproducible; not the Window 14 RED (§14, §17) | 5, 6, and CI job `red-first-window20-failed-candidate-4of4` |
| `C3-1` no caller-manufacturable authority (13 invalid trust roots) | 8, 9, 11 |
| `C3-2` reflection-proof (13 paths) | 8, 9, 11 |
| `C3-3` verifier-less attempt permanently `in_doubt` | 8, 9, 11 |
| `C3-4` exact-bytes binding cannot self-assert | 8, 11 |
| `C3-5` Corrective-002 positives preserved | 8, 15, and CI jobs `candidate-suite-b-green-7of7`, `candidate-w17-green-14of14`, `corrective-002-migration-rsa-positives`, `real-sigkill-and-genuine-external-return` |
| `C3-7` hygiene closure, no residual armed state denying genuine returns | 10 (file 3), 11 |
| `C3-8` / section 20 scope discipline | 13, and CI job `scope-discipline-and-identity-guard` |
| section 8 TIGHTEN_ONLY, seven items per file | 10 |
| section 10 inherited observation, classified and disclosed, scope not expanded | 12, 16 §3.1 |
| section 16 author C3 matrix, 27 enumerated cases, property checks | 11, and CI jobs `c3-author-matrix-green-27-cases` / `…-red-on-failed-candidate` |
| section 17 workflow: pin three commits, verify three probe hashes, ≥ 10 jobs, no Window 14 RED reuse | 14, 15, and `.github/workflows/core-background-late-trusted-return-001.yml` (12 jobs) |
| section 21 evidence package | this directory |
| section 22 staged durable pushes; no evidence-only commit after formal CI | 14 §1, §4; 15 §5 |
| exact-head formal CI on CPython 3.12.14 / pydantic 2.13.5 / pytest 8.4.2 | 15 §1, §4 |
| full Core failures=0 errors=0 | 15 §3; `raw/PREFLIGHT_FULL_CORE_GATE_ON_CANDIDATE_v4.txt` (preflight) and the CI job (formal) |
| new PR OPEN + UNMERGED, head == exact tested SHA | 16 §2, §4 |
| stop conditions | 13 §5 |
| `DOWNSTREAM_OPERATOR_COMPATIBILITY_DEBT` for C15 | 8 §8, 12 (non-observations), 16 §3.6 |
| branch-name deviation disclosed | 14 §5, 16 §3.3 |
| sandbox interruption disclosed | 14 §3, 16 §3.5 |

## 3. `raw/` contents

Verbatim tool output. Nothing in `raw/` was edited, truncated, re-run silently or reformatted; where
a file was superseded by a later run, both versions are kept and labelled.

| file | content |
|---|---|
| `PUBLICATION_CAPABILITY_RAW.txt` | the publication-capability preflight transcript |
| `RED_SUITE_A_ON_FAILED_CANDIDATE_fec30bd.txt` | Suite A on `fec30bd1…` — `probes=4 failures=4` |
| `RED_SUITE_A_ON_CARRY_FORWARD_BASE.txt` | Suite A on `50a3e1f` — **byte-identical** to the line above (SHA-256 `a138c12d…`) |
| `POSITIVE_SUITE_B_ON_FAILED_CANDIDATE_fec30bd.txt` | Suite B on `fec30bd1…` — `probes=7 failures=0` |
| `POSITIVE_W17_ON_FAILED_CANDIDATE_fec30bd.txt` | W17 on `fec30bd1…` — `probes=14 failures=0` |
| `GREEN_SUITE_A_ON_CANDIDATE_v1.txt` | Suite A on the Route B candidate, first verification |
| `GREEN_SUITE_B_ON_CANDIDATE_v1.txt` | Suite B, first verification (byte-identical to the `fec30bd1…` run) |
| `GREEN_W17_ON_CANDIDATE_v1.txt` | W17, first verification |
| `GREEN_SUITE_A_ON_CANDIDATE_v2.txt` | Suite A after the supersession refinement — identical to v1 |
| `GREEN_SUITE_B_ON_CANDIDATE_v2.txt` | Suite B after the supersession refinement — identical to v1 |
| `GREEN_W17_ON_CANDIDATE_v2.txt` | W17 after the supersession refinement — differs from v1 in **one** line only: `IA17-RACE-CRASH-001` reports the nondeterministic winner of a genuine concurrency race, `meters=1` either way, probe still 0 failures |
| `GREEN_C3_AUTHOR_MATRIX_ON_CANDIDATE.txt` | the 27-case author matrix on the candidate — `28 passed`, verbose per-case verdicts |
| `RED_C3_AUTHOR_MATRIX_ON_FAILED_CANDIDATE_fec30bd.txt` | the byte-identical matrix replayed on `fec30bd1…` — `17 failed, 11 passed`, with the RED case ids |
| `PREFLIGHT_FULL_CORE_GATE_ON_CANDIDATE_v3.txt` | preflight full Core gate at the 900-passed stage |
| `PREFLIGHT_FULL_CORE_GATE_ON_CANDIDATE_v4.txt` | preflight full Core gate with the matrix included — `928 passed in 295.54s`, 0 failed, 0 errors |

## 4. What is deliberately **not** in this package

* No Independent Acceptance verdict, no acceptance decision, no merge recommendation. This window
  is the corrective engineer; acceptance belongs to a fresh independent reviewer.
* No copy of any frozen reviewer probe. They are extracted from the pinned review commits at run
  time and executed in place; copying them into the tracked tree would violate `C3-6` and is
  mechanically blocked by CI.
* No modification of Window 14 / 17 / 20 reviewer evidence, PR #310 or PR #311 branches, C15
  persistence or preflight paths, governance/task-board/checkpoint files, release artifacts, or
  UI/hardware.
* No post-formal-CI evidence commit. The final run's identifiers live in the PR body and the
  per-job commit comments — see `DURABLE_PUBLICATION_LOG.md` §4 and `FORMAL_CI_RESULTS.md` §5.
* No local-run result presented as acceptance evidence. Every local run is CPython 3.11.2 and is
  labelled **PREFLIGHT**.
