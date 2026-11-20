# LIMITATIONS — not obtained / not executed / cannot be proven

- **Review:** `RV20261120-002`, task `PM-REVALIDATION-BASELINE-001`
- **Exit verdict:** `GAPS_CONFIRMED` (see REVIEW_IDENTITY.md).
- **Rule applied throughout:** material insufficiency is recorded as UNKNOWN / INSUFFICIENT_EVIDENCE, never filled in as PASS; unknown files are listed item by item with the role that can supply them. No password, token, private key, or 2FA was requested from anyone.

## 1. Not obtained (material exists somewhere, or is claimed to exist)

| # | Material | Status in this round | Change vs first review | Qualified provider role |
|---|---|---|---|---|
| L1 | Window69 raw report `FINAL_SIGNED_MATRIX_REPORT.json` (+ full commands, exit codes, per-case non-empty run proof, hash receipt from controlled storage), binding exact candidate `52d169e8…` | Not found in repo; only a host absolute path is cited | None — still missing | Operator (host holder) + independent Reviewer (after declassification) |
| L2 | Window67 frozen evidence branch `review/window67-formal-security-evidence` HEAD `391c4815…` (incl. `WINDOW67_TEST_RESULTS.json`, `raw/original38.xml`, `raw/parent-original38.xml`, 154 members) and directory `reviews/C15_RERUN005_FORMAL_SECURITY_WINDOW67/` | **OBTAINED and fully verified** (see §4) | **Closed** — was "object not in local store" | — (obtained) |
| L3 | Old Phase-C candidate `94221b512a573bbe9922eea444552ac9122b3a0e` (run `…bd8446e1205d`) object content and the reason it was replaced | Object not in local store | None — still missing | PR #394 author / Operator |
| L4 | Trusted external provider/model attestation binding actual A/B/C runs/sessions to distinct model/provider identities (server-returned `model` field + request-id binding) | Not found in any frozen evidence | None — still missing | Platform evidence provider (Operator + model platform) |
| L5 | Explanation of the old triple in the Phase-B completion report (`4020a4ca…` / `cfd07e6067fc8662` / `a35fef6bb8be19ca`) | No record anywhere; appears exactly once | Erratum recorded at control level; written confirmation still not supplied | Phase-B evidence author / Operator (written confirmation: typo or draft source) |
| L6 | CI run `39223062778` jobs / logs / artifacts | Public API returns metadata only; log download needs auth | None — still missing; additionally, **no `p16-convergence-gate` run exists at the new baseline `8317769`** (only `governance-drift` run `44698960019`, success) | Repository-authorized party |
| L7 | Per-case semantic evidence table for R1–R9 (`actual input/fact → supported cognition object or justified silence → later retrieval result → actual decision/result → correction under new evidence`, each located to exact run/cursor/request/object/revision) | Not submitted by any party | None — still missing | Independent semantic Evaluator (new analysis; re-run only where a key fact is missing or isolation is proven broken) |
| L8 | Headless deployment configuration that could point `headless/core.py:23–46`'s external `module:attribute` handler at a Window80 class | Statically unknowable | None — still UNKNOWN | Deployment / operations party (actual headless launch command + handler config) |
| L9 | GitHub comment originals cited in the PM audit (e.g. PR #390 Window69 comment `issuecomment-6249472225`) | Not re-read in this window (local-repo read-only method) | None | Main reviewer / PM (remote is authoritative) |

## 2. Not executed (forbidden by the task brief, or not possible read-only)

- No pytest run, no acceptance-probe execution, no model call, no Resident start, no fixture run — including the evaluator probes, the `REPRODUCE.md` steps (A1–A6, B, C), and the live habitation test. The evaluator's 18/18, the receipt's 18/18 and "157 items", the Window82 54/54, the Window83 46/46, and the S1 packet's 410-passed / M1–M3 claims are therefore **reported, not re-verified** by this review. (The PM's 2026-11-20 session independently ran `tools/check.py --quick` → 550 passed / 3 skipped on current main; that is a PM-session observation, not a reviewer verification, and it is not a CI run.)
- No live-endpoint re-capture for R6 (would need `AIOS_LIVE_PROVIDER=1`, a reachable endpoint, and a provenance fix to read the server `model` field first — and this review must not perform that fix).
- No Windows reproduction of T04 concurrent-attach (Linux-only environment here; the failure needs a real Windows run).
- No re-run of the full test suite and no timing re-baseline.
- No import or execution of candidate Python packages.
- No re-run of the Window67 original38 suite (forbidden: the frozen evidence is read-only; the recorded runs stand as the evidence). Item 7 (`test_signer_not_importable_in_recovery_caller`) therefore stays STILL_BINDING.
- One public GitHub API query (workflow runs at head `5a0c38a`) was rate-limited (HTTP 403) and was **not** retried; the `p16-convergence-gate` status at the Window82 commit is therefore UNKNOWN, not a finding either way.

## 3. Cannot be proven on the present record

- That the A/B/C Resident runs were served by distinct underlying models/providers (R6) — the only model-identity material is self-reported strings and NULL fields.
- That any calibration, strategy/experience, or correction cognition was formed as a persisted object (R3/R4/R8) — the submitted probes are negative checks, and the final World holds exactly 1 claim total.
- That prior cognition materially changed a specific later decision (R7) — retrieval happened; the decision-difference link is absent. (The Window82 wiring now makes such a link mechanically observable in a future run; it does not supply one retroactively.)
- That all 47 claimed model requests were real, two-way reconciled model calls (R9) — zero response receipts, zero return handoffs.
- Whether the four Window80 subsystems behave correctly when invoked through the new capabilities on the exact new tree — the wiring exists (Window 82), but no independent acceptance run on that tree was submitted.
- Whether the `p16-convergence-gate` passes at `8317769` — no run exists at that head.
- Anything about local main `1f769d1` beyond the governance records it contains — it is a local-only PM adjudication commit, not pushed; certification of remote main stops at `8317769`.

## 4. L2 — what was obtained and verified in this round

- Branch `review/window67-formal-security-evidence` HEAD `391c4815ac77ef82cabcf13798de4d8fa8e7c0b0`, confirmed identical on the remote via `git ls-remote`; root tree `d4dc287feb2e59f42bdaadbc15cf4d3406c9845a` matches the audit constant `WINDOW67_TREE`; manifest SHA-256 matches `WINDOW67_MANIFEST_SHA256`; all **154** manifest members re-hashed (SHA-256 + size) with **zero mismatches**; tracked files in the evidence directory = 155 (154 members + the manifest itself, exactly as `verify_manifest_members` expects).
- `WINDOW67_TEST_RESULTS.json`: `ORIGINAL_38: 31 PASS / 7 FAIL / 0 SKIP`, `FORMAL_DISPOSITION: FORMAL_VALIDATION_FAIL`, `DO_NOT_MERGE: YES`, candidate head `6fb725407569bc719c049587f67fe65e797eb734` (PR #370 head).
- All four recorded original38 runs parsed from JUnit XML: own 31/7, parent 31/7, regression-attempt1 24/14, parent-attempt1 28/10 — the same seven failures in every run.
- Blockers `W67-VAL-001` (no new TEST_ONLY enrollment), `W67-VAL-002` (seven binding failures), `W67-VAL-003` (cross-environment blocked); `PM54_BLK_001/002/003` UNVERIFIED; publisher import equivalence UNVERIFIED.

## 5. Disposition of the 9 minimum requirements (`RV20261120-001/LIMITATIONS.md §4`)

| # | Requirement | Disposition in this round |
|---|---|---|
| 1 | Freeze a new baseline (new main SHA + protected trees + selected contract blobs + candidate HEADs) and re-issue the audit's `BASELINE.json` for that baseline. Do not amend the first review's pins. | **DONE.** `reviews/PM_REVALIDATION_BASELINE_001/BASELINE.json` freezes main `8317769` with protected trees, contract blobs, and candidate HEADs; this review re-verified all of them first-hand. The first review's pins were not amended. |
| 2 | Re-verify the drift delta `259d0353 → <new baseline>` per protected path and re-establish which old RC/Resident evidence still applies. | **DONE.** 159 files / 78 commits re-verified per protected path; per-area applicability is in CORE_IMPACT_MATRIX.md §3. Two corrections to the first review: count 158 → 159 (pyproject.toml); Window80 wiring now exists (Window 82). |
| 3 | Obtain L4 (trusted attestation) or re-capture R6 live with server `model` field + request-ids; until then R6 stays PARTIAL and C15 cannot PASS. | **OPEN.** L4 not obtained; provenance echo still unfixed at `8317769` (server `model` field never read). R6 stays PARTIAL. |
| 4 | Obtain L1/L2 and disposition original38 items 1–6; item 7 stays STILL_BINDING until independently re-verified or formally superseded. | **PARTIAL.** L2 obtained and fully verified; items 1–6 dispositioned as **confirmed binding failures** (fail in all four recorded runs). L1 still missing. Item 7 stays STILL_BINDING. |
| 5 | Produce L7 (per-case R1–R9 semantic table) under an independent semantic Evaluator; re-run only affected parts. | **OPEN.** L7 not submitted by any party. R3/R4/R8 stay INVALID on the submitted probes. |
| 6 | Apply the two proposed errata as appended notes; do not rewrite frozen text. | **PARTIAL.** Recorded in the task-board 2026-11-20 CURRENT PM CONTROL block and the checkpoint (local commit `1f769d1`, unpushed). **Not** appended in the named locations (B acceptance receipt, Window75 block, C acceptance receipt). |
| 7 | Correct the stale entry `PROJECT_MASTER_MAP.md:100–101` (CLOSED / PRODUCTION READY) to the current task-board control (governance-only change). | **DONE (locally, pending main integration).** Verified at local HEAD `1f769d1`: C15-RCC now reads REVALIDATION_REQUIRED with the R1–R9 verdicts; C16 reads HOLD_PENDING_REVALIDATION. Remote main is still `8317769`, where the stale rows stand. |
| 8 | Decide the Window80 wiring task (headless/runtime registration, capability entries, proposal-execution authorization chain, index-visibility and restart-recovery verification, independent acceptance on the exact new tree) as a separate, precisely frozen task. | **OPEN — decision still pending; the facts changed.** The wiring itself is done (Window 82, `5a0c38a`); what remains is **acceptance of the wiring** on the exact new tree. See CORE_IMPACT_MATRIX.md §4 and the PM recommendation in REVIEW_IDENTITY.md / FINDING_DISPOSITION.md NII-02. |
| 9 | Do not treat the implementer's S1 evidence packet as a review conclusion, do not replace pins merely to clear drift, and do not let the PM or implementer self-sign R1–R9. | **COMPLIED WITH.** The S1 packet is cited only as implementer-submitted, unreviewed material. The new baseline was frozen as a separate manifest; the first review's pins were not amended and no hash was replaced. No R1–R9 verdict in this package is signed by the PM or the implementer. |
