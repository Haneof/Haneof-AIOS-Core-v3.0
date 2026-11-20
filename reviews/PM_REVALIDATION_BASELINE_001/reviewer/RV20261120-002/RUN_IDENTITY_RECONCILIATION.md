# RUN_IDENTITY_RECONCILIATION — single-value identity map (revalidation)

- **Review:** `RV20261120-002`, task `PM-REVALIDATION-BASELINE-001`
- **Authority order for identity:** `RUN_IDENTITY.json` (hash-sealed via `FREEZE_MANIFEST.json` and `SHA256SUMS`) > `SESSION_END.json` > acceptance receipt / IA report > `completion_report.md` (unhashed narrative) > task-board historical blocks.
- **Verification:** candidate HEADs re-verified live via `git ls-remote` in this round (all four match their pins). Identity values below are carried forward from `RV20261120-001`, which read them first-hand from the exact candidate git objects; this review re-verified the heads and the absence of the old object, and found no new identity material.

## Single-value identity map (accepted runs only — unchanged)

| Phase | Run ID (single value) | Process ID | Session ID | Conversation session ID | Minted (UTC) | Inherits | Final World rev | Final cursor | Exchanges | Candidate HEAD |
|---|---|---|---|---|---|---|---|---|---|---|
| A | `c15-rcc-res-a-rerun-005-8e605da939b0` | `eb935e2d-575c-44dc-bf48-5f8907390d9e` | `resident-a-005-d49cb630c1014fac` | `sess-resident-a-005-75029e633ec54fd0` | 2026-10-18T13:40:10Z | — (fresh start) | 38 | 13 | 21 | `2d923282…` (PR #392) |
| B | `c15-rcc-res-b-rerun-005-4b4993c81a85` | `d0642375-5fef-4ca1-ac5c-d5af0e585635` | `resident-b-005-32ed51751aee40a2` | `sess-resident-b-005-632f06ba3df940f3` | 2026-10-19T00:32:50Z | A rev 38 / cursor 13 | 60 | 22 | 12 | `302dab25…` (PR #393) |
| C | `c15-rcc-res-c-rerun-005-cf585be261f9` | `01961445-e0d9-4373-bb70-8e3543fafb4f` | `resident-c-005-826a8a7bcef345ab` | `sess-resident-c-005-7969eff964ce44c9` | 2026-10-19T01:19:17Z | B rev 60 / cursor 22 | 82 | 30 | 14 | `6cd89d6e…` (PR #394) |

**What is absent from every identity file (unchanged):** no `provider`, `model`, or `author` field exists in any A/B/C `RUN_IDENTITY.json`, `FREEZE_MANIFEST.json`, or `SESSION_END.json`. Mechanical identity is complete; model/author attribution is not recorded anywhere in the frozen evidence (see AXIS_EVIDENCE_MATRIX.md, R6).

## Discrepancy 1 — Phase B completion report vs RUN_IDENTITY (unchanged)

| Source | Process ID | Session ID | Conversation session ID |
|---|---|---|---|
| `completion_report.md` §一 (`302dab25…`) | `4020a4ca-d93a-4da2-b1ba-fa4e99fc3646` | `resident-b-005-cfd07e6067fc8662` | `sess-resident-b-005-a35fef6bb8be19ca` |
| `RUN_IDENTITY.json` (same commit) | `d0642375-5fef-4ca1-ac5c-d5af0e585635` | `resident-b-005-32ed51751aee40a2` | `sess-resident-b-005-632f06ba3df940f3` |

- Classification (carried forward): **narrative typo (completion-report side)**; "unaccepted-draft residue" not excludable — the old triple's origin is undocumented.
- **Erratum status:** recorded in the task-board 2026-11-20 CURRENT PM CONTROL block and in the checkpoint (local commit `1f769d1`, unpushed): "the RUN_IDENTITY values govern; the triple is recorded as a reporting-side narrative typo (that file is not hash-sealed)". **Not** appended in the B acceptance receipt as the first review proposed. Written Operator confirmation of the triple's origin (L5) is still not supplied.

## Discrepancy 2 — Phase C old run vs accepted run (unchanged)

| Record | Candidate commit | Run ID | Status |
|---|---|---|---|
| Task-board Window75 block | `94221b512a573bbe9922eea444552ac9122b3a0e` (parent `302dab25…`) | `c15-rcc-res-c-rerun-005-bd8446e1205d` | First PR #394 candidate, **not accepted** |
| Acceptance receipt, Gate 0 receipt, IA P09, `RUN_IDENTITY.json` (`6cd89d6e…`) | `6cd89d6e3761347487946ca95e59bae380a3ae46` (same parent `302dab25…`) | `c15-rcc-res-c-rerun-005-cf585be261f9` | **Accepted run (single value)** |

- The old candidate object `94221b51…` is still **not in the local object store**. The replacement reason is still not supplied (L3).
- **Erratum status:** recorded in the task-board 2026-11-20 CURRENT PM CONTROL block and in the checkpoint (local commit `1f769d1`, unpushed). **Not** appended in the task-board Window75 block (which still presents the old candidate at lines ~201–212 without a note) or in the C acceptance receipt.

## Discrepancy summary

| Difference | Classification | Second-run evidence? |
|---|---|---|
| B completion-report triple vs RUN_IDENTITY triple | Narrative typo (report side); "unaccepted-draft residue" not excludable | None |
| C old run `…bd8446e1205d` / candidate `94221b51` vs accepted run `…cf585be261f9` / HEAD `6cd89d6e…` | Unaccepted candidate replaced | None |
| Any other A/B/C identity value | Consistent, no difference | — |

## Note on the Option B candidate

PR #390 HEAD `52d169e8…` is the parent of the A evidence chain (A's parent is `52d169e8…`; B's parent is A's HEAD; C's parent is B's HEAD). Its identity files concern the engineering candidate and its signature/tooling tests, not a Resident run; they must not be read as Resident A/B/C run identity.

## Note on the Window67 candidate (new in this round)

The Window67 frozen evidence binds to a **different** candidate: head `6fb725407569bc719c049587f67fe65e797eb734` (PR #370, draft OPEN), parent `9d3b19b0e7bf090e5d472d9781b9156f73ea2088` (PR #367, draft OPEN), per `WINDOW67_EXACT_IDENTITY.json` in the frozen branch. Its original38 results (31 PASS / 7 FAIL) are historical regression evidence for the shared Core lineage. They must not be read as a verdict on the RERUN-005 runs (`…8e605da939b0` / `…4b4993c81a85` / `…cf585be261f9`), which ran under different candidate heads. The seven binding failures are failures of the asserted Core behavior in the Window67 validation, and they remain binding pending PM adjudication regardless of which candidate they were measured on.
