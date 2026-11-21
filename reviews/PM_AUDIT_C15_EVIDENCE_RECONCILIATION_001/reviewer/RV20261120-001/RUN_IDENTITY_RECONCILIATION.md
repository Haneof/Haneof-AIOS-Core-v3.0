# RUN_IDENTITY_RECONCILIATION — single-value identity map

- **Review:** `RV20261120-001`, task `PM-AUDIT-C15-EVIDENCE-RECONCILIATION-001`
- **Authority order for identity:** `RUN_IDENTITY.json` (hash-sealed via `FREEZE_MANIFEST.json` and `SHA256SUMS`) > `SESSION_END.json` > acceptance receipt / IA report > `completion_report.md` (unhashed narrative — see below) > task-board historical blocks.
- **Verification:** all values below were read first-hand from the exact candidate git objects (#392 `2d923282…`, #393 `302dab25…`, #394 `6cd89d6e…`). No value was taken from a summary alone.

## Single-value identity map (accepted runs only)

| Phase | Run ID (single value) | Process ID | Session ID | Conversation session ID | Minted (UTC) | Inherits | Final World rev | Final cursor | Exchanges | Candidate HEAD |
|---|---|---|---|---|---|---|---|---|---|---|
| A | `c15-rcc-res-a-rerun-005-8e605da939b0` | `eb935e2d-575c-44dc-bf48-5f8907390d9e` | `resident-a-005-d49cb630c1014fac` | `sess-resident-a-005-75029e633ec54fd0` | 2026-10-18T13:40:10Z | — (fresh start) | 38 | 13 | 21 | `2d923282…` (PR #392) |
| B | `c15-rcc-res-b-rerun-005-4b4993c81a85` | `d0642375-5fef-4ca1-ac5c-d5af0e585635` | `resident-b-005-32ed51751aee40a2` | `sess-resident-b-005-632f06ba3df940f3` | 2026-10-19T00:32:50Z | A rev 38 / cursor 13 | 60 | 22 | 12 | `302dab25…` (PR #393) |
| C | `c15-rcc-res-c-rerun-005-cf585be261f9` | `01961445-e0d9-4373-bb70-8e3543fafb4f` | `resident-c-005-826a8a7bcef345ab` | `sess-resident-c-005-7969eff964ce44c9` | 2026-10-19T01:19:17Z | B rev 60 / cursor 22 | 82 | 30 | 14 | `6cd89d6e…` (PR #394) |

Corroboration: for each phase, `FREEZE_MANIFEST.json` embeds a `run_identity` identical to the `RUN_IDENTITY.json` above; each phase's `SESSION_END.json` agrees on end time, exchange count, and the next cursor being unrevealed (A ends 13:40:41Z / 21 / cursor 14 unrevealed; B ends 00:33:09Z / 12 / cursor 23 unrevealed; C ends 01:19:36Z / 14 / cursor 31 unrevealed); each phase's independent-acceptance report P09 uses the same run id. Ledger counts are consistent (A 63 records = 21/21/21; B 36 = 12/12/12; C 42 = 14/14/14).

**What is absent from every identity file:** no `provider`, `model`, or `author` field exists in any A/B/C `RUN_IDENTITY.json`, `FREEZE_MANIFEST.json`, or `SESSION_END.json`. Mechanical identity is complete; model/author attribution is not recorded anywhere in the frozen evidence (see AXIS_EVIDENCE_MATRIX.md, R6).

## Discrepancy 1 — Phase B completion report vs RUN_IDENTITY

| Source | Process ID | Session ID | Conversation session ID |
|---|---|---|---|
| `completion_report.md` §一 (`302dab25…`) | `4020a4ca-d93a-4da2-b1ba-fa4e99fc3646` | `resident-b-005-cfd07e6067fc8662` | `sess-resident-b-005-a35fef6bb8be19ca` |
| `RUN_IDENTITY.json` (same commit) | `d0642375-5fef-4ca1-ac5c-d5af0e585635` | `resident-b-005-32ed51751aee40a2` | `sess-resident-b-005-632f06ba3df940f3` |

- Run id, inheritance (A rev 38 / cursor 13), cursor range, final rev 60, and 12 exchanges **agree** between the two sources; only the three identity values differ.
- The old triple (`4020a4ca…` / `cfd07e6067fc8662` / `a35fef6bb8be19ca`) appears **nowhere else** in the repository (whole-repo grep hits only this report and the PM audit's quotation of it).
- `completion_report.md` is **not inside the hash seal**: each phase's IA report P01 lists `unhashed=['SHA256SUMS', 'completion_report.md']`. Its narrative authority is therefore below RUN_IDENTITY / FREEZE_MANIFEST / SESSION_END.
- **Classification: narrative typo (completion-report side).** Most likely the report copied an identity block from an unaccepted draft or an earlier run. The alternative "unaccepted-candidate residue" cannot be excluded on the present record, because the old triple's origin is undocumented — the erratum below must say so.
- **No evidence of a second actual run:** no second ledger, World, SESSION_END, or manifest supports the old triple.

**Proposed erratum (append only — do not rewrite the frozen report):** in the B acceptance receipt or the task board, add: "Phase-B `completion_report.md` §一 lists process `4020a4ca…` / session `resident-b-005-cfd07e6067fc8662` / conversation `sess-resident-b-005-a35fef6bb8be19ca`; the authoritative values are `d0642375…` / `resident-b-005-32ed51751aee40a2` / `sess-resident-b-005-632f06ba3df940f3` per `RUN_IDENTITY.json` (corroborated by FREEZE_MANIFEST and IA P09). The old triple is treated as an unaccepted-draft remnant pending written Operator confirmation."

## Discrepancy 2 — Phase C old run vs accepted run

| Record | Candidate commit | Run ID | Status |
|---|---|---|---|
| Task-board Window75 block (`governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md:188–199`) | `94221b512a573bbe9922eea444552ac9122b3a0e` (parent `302dab25…`) | `c15-rcc-res-c-rerun-005-bd8446e1205d` | First PR #394 candidate, **not accepted** |
| Acceptance receipt, Gate 0 receipt, IA P09, `RUN_IDENTITY.json` (`6cd89d6e…`) | `6cd89d6e3761347487946ca95e59bae380a3ae46` (same parent `302dab25…`) | `c15-rcc-res-c-rerun-005-cf585be261f9` | **Accepted run (single value)** |

- The old candidate object `94221b51…` is **not in the local object store** (`git cat-file -t` fails); the accepted HEAD is not its descendant but a parallel re-creation on the same parent.
- Every numeric claim is identical between the two records (cursors 23–30, 14 requests, rev 82, cursor 31 refused, 82 files 100% verified, zero drift) — consistent with the same run re-packaged/re-proposed, not with two different runs.
- **Classification: unaccepted candidate replaced.** The task-board Window75 block describes PR #394 as first created; the accepted HEAD later superseded it, and the IA and receipts all use the new HEAD.
- **No evidence of a second actual run:** the old run has no RUN_IDENTITY, manifest, ledger, or World file retained anywhere.
- **Open question (cannot be judged on the present record):** *why* the candidate was replaced — content difference unknown because the old object is not retained.
- **Proposed erratum (append only):** in the task-board Window75 block and the C acceptance receipt, add: "`94221b51` (run `…bd8446e1205d`) was the first, unaccepted PR #394 candidate; it was replaced by `6cd89d6e…` (run `…cf585be261f9`), accepted via Window76 IA. The old object is not retained locally; the replacement reason is to be supplied by the Operator/author. The accepted identity is `…cf585be261f9` only."

## Discrepancy summary

| Difference | Classification | Second-run evidence? |
|---|---|---|
| B completion-report triple vs RUN_IDENTITY triple | Narrative typo (report side); "unaccepted-draft residue" not excludable | None |
| C old run `…bd8446e1205d` / candidate `94221b51` vs accepted run `…cf585be261f9` / HEAD `6cd89d6e…` | Unaccepted candidate replaced | None |
| Any other A/B/C identity value | Consistent, no difference | — |

## Note on the Option B candidate

PR #390 HEAD `52d169e8…` ("Arena-C15-ENG-001 corrective 2: provenance correction + regenerator fail-closed hardening") is the parent of the A evidence chain (A's parent is `52d169e8…`; B's parent is A's HEAD; C's parent is B's HEAD). Its identity files (`NEW_CANDIDATE_IDENTITY.json`, `ENGINEERING_REPORT.md`, corrective test records) concern the engineering candidate and its signature/tooling tests, not a Resident run; they must not be read as Resident A/B/C run identity.
