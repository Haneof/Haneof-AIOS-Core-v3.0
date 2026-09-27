# CORE-RC-REFREEZE-002 Open PR contamination review

Inventoried via `gh pr list --state open` on 2026-09-27 against live main `27a21db5b656d441248b9240020910b66a223830`.

| PR | Classification | RC disposition |
|---|---|---|
| #232 | OUT_OF_SCOPE (this freeze PR) | Evidence/governance + freeze-gate workflow only. |
| #230 | REVIEW-ONLY IA evidence | Must not merge as implementation. Frozen authenticity evidence only. |
| #216 | FROZEN_WIP / B persistence corrective | EXCLUDED. Do not resume until RC IA + fresh A-003. |
| #205 | HISTORICAL EVIDENCE ONLY | A-RERUN-002 canonical for **prior** RC `773876f9...` only. Do not hash-swap. |
| #144 | SUPERSEDED / NOT INTEGRATED | Historical first CI-FIX line. |
| #130 | SUPERSEDED / NOT INTEGRATED | Competing CORE-OPERATOR candidate. |
| #126 | SUPERSEDED / NOT INTEGRATED | Old draft; fixes integrated elsewhere. |
| #125 | SUPERSEDED / NOT INTEGRATED | BLOCKED historical C15 preflight. |
| #121 | HISTORICAL EVIDENCE ONLY | Failed/non-canonical Resident B. |
| #119 | OUT_OF_SCOPE | Governance-only. |
| #118 | OUT_OF_SCOPE | Governance-only. |
| #117 | HISTORICAL EVIDENCE ONLY | Historical Resident A. |
| #113 / #111 / #110 | INTEGRATED via accepted route | Open PRs are not new Core. |
| #112 | HISTORICAL EVIDENCE ONLY | Scale benchmark clue. |
| #109 / #107 / #101 | HISTORICAL EVIDENCE ONLY | Older Resident A. |
| #92 / #79 / #75 / #74 | HISTORICAL EVIDENCE ONLY | Pinned C14 evidence. |
| #37 | OUT_OF_SCOPE | Historical P16 triage. |

**BLOCKER — unaccounted Core implementation open PR: none.**

PR #230 is explicitly not implementation.
PR #216 remains FROZEN_WIP and is KNOWN POST-RC / EXCLUDED.

No competing unmerged Core implementation shares the Corrective-002 runtime symbols as an alternate candidate.
