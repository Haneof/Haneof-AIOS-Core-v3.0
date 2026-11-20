# LIMITATIONS — not obtained / not executed / cannot be proven

- **Review:** `RV20261120-001`, task `PM-AUDIT-C15-EVIDENCE-RECONCILIATION-001`
- **Exit verdict:** `REVALIDATION_REQUIRED` (protected-object drift `259d0353` → main `8317769`; see REVIEW_IDENTITY.md).
- **Rule applied throughout:** material insufficiency is recorded as UNKNOWN / INSUFFICIENT_EVIDENCE, never filled in as PASS; unknown files are listed item by item with the role that can supply them. No password, token, private key, or 2FA was requested from anyone.

## 1. Not obtained (material exists somewhere, or is claimed to exist)

| # | Material | Status | Qualified provider role |
|---|---|---|---|
| L1 | Window69 raw report `FINAL_SIGNED_MATRIX_REPORT.json` (+ full commands, exit codes, per-case non-empty run proof, hash receipt from controlled storage), binding exact candidate `52d169e8…` | Not found in repo; only a host absolute path is cited | Operator (host holder) + independent Reviewer (after declassification) |
| L2 | Window67 frozen evidence branch `review/window67-formal-security-evidence` HEAD `391c4815…` (incl. `WINDOW67_TEST_RESULTS.json`, `raw/original38.xml`, `raw/parent-original38.xml`, 154 members) and directory `reviews/C15_RERUN005_FORMAL_SECURITY_WINDOW67/` | Object not in local store; directory does not exist | Repository owner / evidence custodian |
| L3 | Old Phase-C candidate `94221b512a573bbe9922eea444552ac9122b3a0e` (run `…bd8446e1205d`) object content and the reason it was replaced | Object not in local store | PR #394 author / Operator |
| L4 | Trusted external provider/model attestation binding actual A/B/C runs/sessions to distinct model/provider identities (server-returned `model` field + request-id binding) | Not found in any frozen evidence | Platform evidence provider (Operator + model platform) |
| L5 | Explanation of the old triple in the Phase-B completion report (`4020a4ca…` / `cfd07e6067fc8662` / `a35fef6bb8be19ca`) | No record anywhere; appears exactly once | Phase-B evidence author / Operator (written confirmation: typo or draft source) |
| L6 | CI run `39223062778` jobs / logs / artifacts | Public API returns metadata only; log download needs auth | Repository-authorized party |
| L7 | Per-case semantic evidence table for R1–R9 (`actual input/fact → supported cognition object or justified silence → later retrieval result → actual decision/result → correction under new evidence`, each located to exact run/cursor/request/object/revision) | Not submitted by any party | Independent semantic Evaluator (new analysis; re-run only where a key fact is missing or isolation is proven broken) |
| L8 | Headless deployment configuration that could point `headless/core.py:48–74`'s external `module:attribute` handler at a Window80 class | Statically unknowable | Deployment / operations party (actual headless launch command + handler config) |
| L9 | GitHub comment originals cited in the PM audit (e.g. PR #390 Window69 comment `issuecomment-6249472225`) | Not re-read in this window (local-repo read-only method) | Main reviewer / PM (remote is authoritative) |

## 2. Not executed (forbidden by the task brief, or not possible read-only)

- No pytest run, no acceptance-probe execution, no model call, no Resident start, no fixture run — including the evaluator probes, the `REPRODUCE.md` steps (A1–A6, B, C), and the live habitation test. The evaluator's 18/18, the receipt's 18/18 and "157 items", and the S1 packet's 410-passed / M1–M3 claims are therefore **reported, not re-verified** by this review. (The PM's 2026-11-20 session independently ran `tools/check.py --quick` → 550 passed / 3 skipped on current main; that is a PM-session observation, not a reviewer verification, and it post-dates the audit baseline.)
- No live-endpoint re-capture for R6 (would need `AIOS_LIVE_PROVIDER=1`, a reachable endpoint, and a provenance fix to read the server `model` field first).
- No Windows reproduction of T04 concurrent-attach (Linux-only environment here; the failure needs a real Windows run).
- No re-run of the full test suite and no timing re-baseline.
- No import or execution of candidate Python packages.

## 3. Cannot be proven on the present record

- That the A/B/C Resident runs were served by distinct underlying models/providers (R6) — the only model-identity material is self-reported strings and NULL fields.
- That any calibration, strategy/experience, or correction cognition was formed as a persisted object (R3/R4/R8) — the submitted probes are negative checks, and the final World holds exactly 1 claim total.
- That prior cognition materially changed a specific later decision (R7) — retrieval happened; the decision-difference link is absent.
- That all 47 claimed model requests were real, two-way reconciled model calls (R9) — zero response receipts, zero return handoffs.
- Whether the original38 items 1–6 are closed (UNKNOWN) — pending L1/L2.
- Whether the four Window80 subsystems are live anywhere outside their own tests — static evidence says no; the dynamic-handler configuration (L8) is the only residual UNKNOWN.
- Anything about current main `8317769` beyond the drift fact itself — certification of current main is blocked by design of this exit.

## 4. Minimum next-task requirements (for the PM's revalidation task)

1. **Freeze a new baseline** (precisely: new main SHA + protected trees + selected contract blobs + candidate HEADs) and re-issue the audit's `BASELINE.json` for that baseline. Do not amend this review's pins.
2. **Re-verify the drift delta** `259d0353 → <new baseline>` per protected path (the 158 changed files include S1 native-tools T05–T08, cleaning, summaries, prompts, P17 token budget, dedup/filelock/jsonschema fixes, workflow changes) and re-establish which old RC/Resident evidence still applies.
3. **Obtain L4** (trusted attestation) or re-capture R6 live with server `model` field + request-ids; until then R6 stays PARTIAL and C15 cannot PASS.
4. **Obtain L1/L2** (Window69 raw report; Window67 frozen evidence) and disposition original38 items 1–6; item 7 (`test_signer_not_importable_in_recovery_caller`) stays STILL_BINDING until independently re-verified or formally superseded.
5. **Produce L7** (per-case R1–R9 semantic table) under an independent semantic Evaluator; re-run only affected parts.
6. **Apply the two proposed errata** (B completion-report triple; C candidate transition `94221b51` → `6cd89d6e…`) as appended notes; do not rewrite frozen text.
7. **Correct the stale entry** `PROJECT_MASTER_MAP.md:100–101` (CLOSED / PRODUCTION READY) to the current task-board control (governance-only change).
8. **Decide the Window80 wiring task** (headless/runtime registration, capability entries, proposal-execution authorization chain, index-visibility and restart-recovery verification, independent acceptance on the exact new tree) as a separate, precisely frozen task.
9. **Do not** treat the implementer's S1 evidence packet as a review conclusion, do not replace pins merely to clear drift, and do not let the PM or implementer self-sign R1–R9.
