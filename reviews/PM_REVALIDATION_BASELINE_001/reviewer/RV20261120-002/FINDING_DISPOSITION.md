# FINDING_DISPOSITION — PM-AUD-01..06 and NI-01..NI-05 carried forward, plus new independent findings

- **Review:** `RV20261120-002`, task `PM-REVALIDATION-BASELINE-001`
- **Disposition values:** `supported` / `unsupported` / `unknown` for the carried-forward findings; `CONFIRMED` / `CORRECTED` / `SUPERSEDED` / `STILL_OPEN` for the first review's findings as re-examined here.
- **Exit context:** overall verdict is `GAPS_CONFIRMED`. Dispositions below are as of the new baseline `8317769` and candidate exact HEADs, unless marked as-of the pinned audit baseline `259d0353`.

## PM-AUD-01 (P0) — R6 downgraded "different model" to "different ID"

- **PM claim:** `eval_r6()` checks only B/C `resident_process_id` / `resident_session_id` difference plus C's self-reported inherited rev 60 / cursor 22, with no verification of model/provider identity or platform attestation, yet outputs VALID. The ruling §13.2–13.3 requires provable different model family/provider, else R6 is `PARTIAL / INSUFFICIENT_EVIDENCE`; C15 PASS requires R1–R9 all VALID.
- **Disposition: supported** (carried forward, unchanged).
- **Re-verification in this round:** probe source blob unchanged (`b03625151c0b8aa2264cac17b64e132fc2bc9840`); Phase-C World re-aggregated with identical numbers (47 attempts, provider/model NULL on all 47; 0 receipts; 0 handoffs). No L4 attestation was submitted in this round. R6 stays PARTIAL.
- **Closing condition (unchanged):** submit trusted external attestation binding the actual A/B/C sessions/runs to distinct model/provider identities, or re-run live capture that records the server-returned `model` field with request-ids — which first requires the provenance echo fix (a future minimal engineering task, not authorized here).

## PM-AUD-02 (P0) — Semantic conclusions drawn from too-weak checks

- **PM claim:** R1 counts USER Observations; R3 passes if the reply lacks "已迁完"; R4 passes if the English string `runbook executed successfully` is absent as a Claim; R5 rests on B's self-reported identity; R7 counts `search_world` calls; R8 passes if the reply contains "production"/"生产"; R9's detail string writes `total_requests=47` directly. None of these independently establishes the claimed semantic conclusion.
- **Disposition: supported** (carried forward, unchanged).
- **Re-verification in this round:** probe source blob unchanged; `total_requests=47` re-confirmed as a literal at `probes.py:306` with no counting logic in `eval_r9`. No L7 per-case semantic table was submitted.
- **Closing condition (unchanged):** build the per-case evidence table the PM specified, each item located to an exact run, cursor, request, object, and revision, with an independent semantic judgement and counterexamples/boundaries.

## PM-AUD-03 (P1) — Formal security verification has an unverifiable evidence segment

- **PM claim:** the Option B acceptance receipt records a Window 69 signature matrix 10/10 PASS, but the raw report is pointed at a host absolute path; only the matrix summary was obtained, not the raw report, full commands/exit codes, per-case non-empty run proof, or a hash receipt from controlled evidence storage. The `original38` history (31 PASS / 7 FAIL) must be dispositioned item by item. Phase-C World shows 47 attempts/metering, 0 response receipts, 0 return handoffs — which alone proves nothing about legality, so the actual Resident's accepted path must be shown, not substituted with another TEST_ONLY safety-test PASS. Status: `NOT_INDEPENDENTLY_REVERIFIED`, not "signature vulnerability found".
- **Disposition: supported** (carried forward), **with the L2 half now resolved — see below.**
- **What changed in this round (L2 obtained):** the Window67 frozen-evidence branch `review/window67-formal-security-evidence` HEAD `391c4815ac77ef82cabcf13798de4d8fa8e7c0b0` is now in the local object store (remote head confirmed identical via `git ls-remote`). This reviewer verified it first-hand: root tree `d4dc287feb2e59f42bdaadbc15cf4d3406c9845a` matches the audit constant `WINDOW67_TREE`; manifest SHA-256 `a9acee9a91d28920d42a91ff2db35d63630331a7dd9aaa6868a725fa35d42a76` matches `WINDOW67_MANIFEST_SHA256`; all 154 manifest members re-hashed (SHA-256 + size) with **zero mismatches**; `WINDOW67_TEST_RESULTS.json` records `ORIGINAL_38: 31 PASS / 7 FAIL / 0 SKIP`, `FORMAL_DISPOSITION: FORMAL_VALIDATION_FAIL`, `DO_NOT_MERGE: YES`, candidate head `6fb725407569bc719c049587f67fe65e797eb734` (PR #370 head).
- **Original38 disposition (this review — changes the first review's UNKNOWN):** the seven failures are the exact `FAIL_NAMES` pinned by `tools/agent_gateway/window67_audit.py:26–34`, and they fail in **all four recorded runs** in the frozen evidence — own `raw/original38.xml` (31/7), parent `raw/parent-original38.xml` (31/7), `raw/regression-attempt1/original38.xml` (24/14), `raw/parent-attempt1/parent-original38.xml` (28/10). The extra failures in the attempt runs (e.g. `test_exact_tar_into_independent_sandbox_runs_pinned_entry`, `test_independent_location_exact_bytes_import_resolution`, `test_identity_substitution_fails_before_start[*]`, `test_executable_substitution_rejected`) do not change the seven's status.
  - Items 1–6 — `test_sigkill_after_request_never_regenerates_or_redispatches`, `test_absent_external_response_bounded_fail_closed`, and the four `test_real_core_external_publisher_with_c15_remote_barriers[due|user|summary|delivered]` — move from **UNKNOWN** to **CONFIRMED BINDING FAILURES / STILL_BINDING**, per `W67-VAL-002` ("Seven original assertions fail independently and remain binding pending PM adjudication. No skip/xfail/assertion changes. Matching baseline failures, if any, do not turn this candidate PASS."). They are not closed; the UNKNOWN is resolved into a confirmed negative.
  - Item 7 — `test_signer_not_importable_in_recovery_caller` — remains **STILL_BINDING** (no Window69 case and none of the four regression suites covers it by name; Window 67 remains `FORMAL_VALIDATION_FAIL / DO_NOT_MERGE`). This reviewer did not re-run it and does not supersede it.
- **L1 (Window69 raw report) still missing:** the receipt's 10 cases were read from the Option B acceptance receipt (`governance/C15_RCC_ARENA_ENG_001_OPTION_B_ACCEPTANCE_INTEGRATION_RECEIPT_2026-10-18.md` §2.1): cases 1–4 are `user` / `due` / `summary` / `delivered` (OpenSSL signature verification + `load_grant` scope gate), cases 5–10 are `remote_reject`, `crash_before_proof`, `crash_before_remote_commit`, `crash_after_commit_before_ack`, `revoked_grant`, `open_endpoint_atomicity`. Cases 1–4 map by name to original38 items 3–6; **no** receipt case maps by name to items 1–2 (`sigkill`, `absent_external_response`). Even if L1 were obtained, it could at most bear on items 3–6 — and only as Option B candidate signature-mechanism evidence, not as proof of the actual Resident's call path (TEST_ONLY credentials, lifetime ≤ 1800 s, issued for the 10 pre-set test cases; see the first review's TEST_ONLY vs Resident provenance note, which stands).
- **Closing condition (updated):** items 1–7 remain binding pending PM adjudication. Closure now requires one of: (a) a corrective that makes the test pass with independent re-verification on a stated tree; (b) formal supersession by an approved new contract (none found); or (c) for items 3–6 only, the declassified Window69 raw report (L1) plus a PM ruling that the matrix's scope covers those items — the raw report is still not obtained.

## PM-AUD-04 (P1) — Narrative identity inconsistencies for the same run

- **PM claim:** Phase-B `completion_report.md` records process `4020a4ca-d93a-4da2-b1ba-fa4e99fc3646` / session suffix `cfd07e6067fc8662`, while `RUN_IDENTITY.json` records process `d0642375-5fef-4ca1-ac5c-d5af0e585635` / session suffix `32ed51751aee40a2`; PR #394's summary and the task board record run suffix `bd8446e1205d`, while the accepted HEAD's `RUN_IDENTITY.json` and acceptance receipt record `cf585be261f9`.
- **Disposition: supported** (carried forward, unchanged).
- **Re-verification in this round:** candidate HEADs unchanged (re-verified via `git ls-remote`); the old Phase-C candidate object `94221b51…` is still not in the local object store. No new identity evidence was submitted.
- **Errata status (requirement 6, partial):** the two errata are recorded in the task-board 2026-11-20 CURRENT PM CONTROL block and in the checkpoint (local commit `1f769d1`, unpushed). They were **not** appended in the locations the first review named: the B acceptance receipt carries no appended note, the task-board Window75 block (lines ~201–212) still presents the old candidate without an appended note, and the C acceptance receipt carries no appended note. The PM's choice to record the errata at control level is a governance record, but the requirement as written is only partially met. See RUN_IDENTITY_RECONCILIATION.md.
- **Closing condition (unchanged):** append the errata in the named locations (do not rewrite frozen text); the B-triple origin still awaits written Operator confirmation (L5).

## PM-AUD-05 (P1) — C15 closure extrapolated into production readiness; next task mixed with hardware scope

- **PM claim:** the board wrote `C15-RCC MILESTONE: FULLY CLOSED & PRODUCTION READY` with the next READY as a generalized `C16 / Wearable Physical Grounding & Multi-Model Habitation`, but S2 is SOFTWARE_RC only, C15 still needs C16, broad P16 and P17 acceptance, C16 is a non-world Resident system-improvement feedback chain (not a wearable project), and hardware/device/UI are explicitly deferred.
- **Disposition: supported** (carried forward; the dispatch side is corrected, the stale-entry residual is now closed — see below).
- **Re-verification in this round:** `PROJECT_MASTER_MAP.md` at local HEAD `1f769d1` was read: the C15-RCC row now states **REVALIDATION_REQUIRED (2026-11-20 独立复核 RV20261120-001)** with the R1–R9 verdicts and "在再验证裁决前，C15-RCC 不得表述为 CLOSED / PRODUCTION READY"; the C16 row now states **HOLD_PENDING_REVALIDATION**. At `8317769` the rows still read CLOSED / PRODUCTION READY and UNBLOCKED / READY. Requirement 7 is therefore **done in the local commit `1f769d1`, pending main integration** (remote main is still `8317769`).
- **Closing condition:** none outstanding on this finding, provided the `1f769d1` correction reaches main; if it does not, the stale rows resurface as the live record.

## PM-AUD-06 (P1) — Status entries inconsistent; duplicate-work and mis-dispatch risk

- **PM claim:** the task board/checkpoint were at 2026-10-19 while the master map top still read "当前控制入口 — 2026-09-28 … CORRECTIVE-001 READY", continuing to authorize an old task and blocking the later chain; the local checkout lagged remote main by 12 commits.
- **Disposition: supported** (carried forward; true at the time; the synchronization residual from the first review is now closed by the same `1f769d1` correction as PM-AUD-05).
- **Closing condition (unchanged):** keep the task board as the sole queue; checkpoint/master-map tops must point to the same exact state with "controlled by the latest task board"; maintain one traceable candidate/acceptance/integration/run/evidence identity map instead of replacing historical hashes. Do not bulk merge/close PRs because there are many open; evidence-only PRs keep their disposition.

## First review's new findings — status update

### NI-01 — R6 live-provider evidence is post-baseline and cannot attest model identity

- **Status: CONFIRMED (unchanged).** Re-verified at `8317769`: `grok_provider.py` reads only `chunk.get("id")` (:745, :939); the server-returned `model` field is never read. The live test is skipped by default. No L4 attestation submitted. R6 stays PARTIAL.

### NI-02 — "47 requests two-way reconciled" is asserted, not demonstrated

- **Status: CONFIRMED (unchanged).** `total_requests=47` re-confirmed as a literal at `probes.py:306`; Phase-C World re-aggregated: 0 response receipts, 0 return handoffs. Nothing to reconcile against.

### NI-03 — The 30-cursor "life" is observation-heavy and cognition-light

- **Status: CONFIRMED (unchanged).** Final World re-aggregated: 100 revision rows, exactly **1 claim** vs 45 observations. No new cognition objects were submitted in this round.

### NI-04 — Audit drift: the audit cannot certify current main

- **Status: SUPERSEDED in form, CONFIRMED in substance.** The drift is no longer uncertified drift: the new baseline `8317769` is frozen in `reviews/PM_REVALIDATION_BASELINE_001/BASELINE.json` and re-verified by this review (protected trees, contract blobs, candidate HEADs). But the substance stands — the old evidence still does not certify the new tree: the `p16-convergence-gate` CI success (run `39223062778`) is bound to `259d0353` only, and **no `p16-convergence-gate` run exists at `8317769`** (public API query at head `8317769`: total 1 run, only `governance-drift` run `44698960019`, conclusion `success`, 2026-11-20T07:59:02Z — which corroborates the drift gate passing after the pin advance, not the test suite). The drift count is corrected 158 → 159 (see NII-01).

### NI-05 — Stale PRODUCTION READY wording survives in the master map

- **Status: CLOSED (in local commit `1f769d1`, pending main integration).** See PM-AUD-05 above.

## New independent findings (this review)

### NII-01 — Drift count correction: 158 → 159 (counting-basis, verdict unaffected)

The first review's "158 protected-path files" counts only the four directory trees (39 `.github/workflows` + 48 `src` + 59 `tests` + 12 `tools` = 158). The full protected-path count including `pyproject.toml` is **159** (74 added, 85 modified, 0 deleted, 0 renamed; recomputed by this reviewer with both `src` and `src/aios_core` pathspecs). All five protected objects changed either way; the drift verdict is unaffected. Recorded so the number is not repeated as 158.

### NII-02 — Window80 subsystems ARE wired at 8317769 (first review's "not wired in" is superseded)

The first review's decisive finding — at `259d0353` none of the four subsystems is referenced from headless/runtime — is correct for that baseline but **no longer true at `8317769`**. Window 82 (`5a0c38a`, 2026-10-19 17:28 +08, "integrate 7 cognitive subsystems into FusedTurnRuntime (54/54 PASS)") wires them in:

- `turn_runtime.py:35,37,38,40` imports all four classes; `:442,447,451,455` constructs them in `FusedTurnRuntime.__init__`.
- 10 new capabilities are registered, 9 mapping to the four subsystems plus `associate_topics`: `get_effective_communication_style` (:1235), `open_narrative_segment` (:1296), `seal_narrative_segment` (:1315), `record_dimension_curve_point` (:1333), `detect_burnout_risk` (:1352), `propose_tool` (:1367), plus `record_ai_promise` / `reconcile_ai_promise` / `inspect_ai_self_mind` (AI-self ledger).
- `ExperienceTracker` is on the **automatic** per-turn path: `run_turn` (def :3937) calls `self._record_turn_experience(...)` at :4302 ("DEF-002: Close Bayesian communication adaptation loop automatically"). The other six helpers are model-invokable capability handlers, not automatic per-turn calls.
- The old `CommunicationExperienceService` is still instantiated alongside (`turn_runtime.py:378`); the new tracker does not replace it.
- `headless/` still contains zero references to the four classes; the wiring reaches headless only through `FusedTurnRuntime` construction. The L8 UNKNOWN (caller-supplied `module:attribute` handler, `headless/core.py:23–46`) is unchanged.
- **Limits of this finding:** the wiring evidence is author-reported (Window82 receipt + pasted Windows console transcript, 54/54, `D:\手镯开发\…`); there is no independent acceptance on the exact new tree and no `p16-convergence-gate` run at `8317769` (see NI-04). The wiring commit `5a0c38a` carries **no** `Authorized-Task:` trailer; it predates the `4677043` pin (2026-10-28), so it sits inside adjudicated history under the repo's own pin mechanism — the same mechanism as the 2026-11-20 ratification — and the current drift gate passes. This is recorded for the record, not as a new FAIL.
- **Effect:** the first review's CORE_IMPACT_MATRIX "not wired in" row and its requirement 8 ("decide the Window80 wiring task") must now be decided against the **wired** tree: what remains is independent acceptance of the wiring on the exact new tree (capability authorization, index visibility, restart recovery), not the wiring itself. See CORE_IMPACT_MATRIX.md.

### NII-03 — Window67 evidence fully verified; original38 items 1–6 are confirmed binding failures

See PM-AUD-03 above. New in this round: all 154 manifest members hash-verified with zero mismatches; manifest hash and evidence root tree match the audit constants; the seven failures are identical across all four recorded runs (own, parent, regression-attempt1, parent-attempt1). The first review's UNKNOWN for items 1–6 is resolved into a confirmed negative. The Window69 raw report (L1) remains the only unexamined material that could bear on items 3–6, and no receipt case maps to items 1–2.

### NII-04 — No p16-convergence-gate CI at the new baseline

At head `8317769` the public Actions API returns exactly one run: `governance-drift` run `44698960019`, completed, conclusion `success`. There is no `p16-convergence-gate` run at the new baseline. The old gate success (run `39223062778` at `259d0353`) certifies that tree only. Any claim that the new tree's test suite passes in CI is therefore unsupported by CI evidence in this round (the PM session's local `tools/check.py --quick` 550-passed observation is a PM-session observation, not a reviewer verification and not CI).

### NII-05 — Errata recorded at control level, not in the named locations

See PM-AUD-04 above. The two errata exist in the task-board 2026-11-20 CURRENT PM CONTROL block and the checkpoint (local `1f769d1`), but not in the B acceptance receipt, the Window75 block, or the C acceptance receipt. Requirement 6 is partially met.

### NII-06 — 154 vs 155 member-count clarification (not an error)

The Window67 manifest lists 154 members and does **not** list itself (`SHA256.json` is not a key). The evidence directory tracks 155 files = 154 members + the manifest itself, which is exactly what `verify_manifest_members` in `tools/agent_gateway/window67_audit.py` expects (`expected = {prefix + name for name in manifest} | {prefix + "SHA256.json"}`). Both numbers are correct under their definitions; the first review's "154 members" is the manifest count. Recorded to prevent a future miscount being read as drift.

### NII-07 — Window67 candidate is PR #370's, not the RERUN-005 candidates'

`WINDOW67_EXACT_IDENTITY.json` binds the validated candidate to head `6fb725407569bc719c049587f67fe65e797eb734` (PR #370, draft OPEN) with parent `9d3b19b0e7bf090e5d472d9781b9156f73ea2088` (PR #367, draft OPEN), `tracked_engineering_diff: []`. The Window67 formal validation therefore binds to that candidate, not to PR #390/#392/#393/#394. Its original38 results are historical regression evidence for the shared Core lineage, not a verdict on the RERUN-005 runs themselves. This distinction matters for any future claim that "Window67 passed/failed the Resident" — it did neither; it validated a candidate and failed it on the seven binding assertions.
