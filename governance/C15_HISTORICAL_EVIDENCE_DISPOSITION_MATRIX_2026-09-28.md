# C15 Historical Evidence / PR Disposition Matrix — 2026-09-28

> Status: **GOVERNANCE REFERENCE / NON-EXECUTABLE**
> Purpose: prevent accidental merge, evidence reuse, hash-swap, or lineage confusion during C15 exit.

| PR | Current identity | Disposition | Rule |
|---|---|---|---|
| #101 | `bfbfa059...` | HISTORICAL / PRE-FIX DIAGNOSTIC | Never canonical for current RC; do not rewrite/merge as current evidence. |
| #117 | `3e51f728...` | HISTORICAL CANONICAL FOR OLD C15 LINEAGE | Immutable evidence-only history; superseded by later RC lineages. |
| #121 | `b6e5ac93...` | HISTORICAL FAILED B / PM HOLD | DO NOT MERGE; not reusable as current B. |
| #205 | `d17ae972...` | HISTORICAL A-002 / PRIOR RC ONLY | Never hash-swap to newer RC. |
| #216 | `63ca5923...` | FROZEN WIP | Preserve; not current candidate; do not resume directly. |
| #219 | merged via accepted corrective lineage | INTEGRATED HISTORICAL CORE RECOVERY | Keep provenance; not an open implementation task. |
| #230 | `2c846baa...` | REVIEW-ONLY IA EVIDENCE | DO NOT MERGE as implementation. |
| #232 | `a93972c9...` | MERGED RC-REFREEZE-002 | Prior accepted RC freeze history; will become prior RC after RC-003. |
| #233 | `40492585...` | REVIEW-ONLY RC IA EVIDENCE | Open/draft/unmerged by design. |
| #235 | `5b636740...` | A-003 EVIDENCE-ONLY | Canonical only for the pre-current-fix RC; becomes historical after new Core integration. |
| #236 | merged review result | A-003 IA INTEGRATED | Historical acceptance receipt; not evidence for A-004. |
| #249 | `08468beb...` | REVIEW-ONLY PERSISTENCE IA HISTORY | Preserve; do not merge. |
| #251 | `7b2556e7...` | FAILED PERSISTENCE CORRECTIVE-002 | Historical failed exact candidate; reviewer red remains red. |
| #254 | `a2d815c9...` | CLOSED / FROZEN / NOT A CANDIDATE | Contains unauthorized Core diff; preserve history only. |
| #255 | merged | GOVERNANCE SCOPE RULING | Binding narrowed persistence scope. |
| #258 | `1ebf51c4...` | FAILED TRUSTED-RETURN CANDIDATE | OPEN/DRAFT/UNMERGED/PINNED; do not hash-swap or merge. |
| #261 | `b9d692dd...` | REVIEW-ONLY IA FAIL | Preserve blocker evidence; do not merge. |
| #262 | merged | GOVERNANCE CORRECTIVE RELEASE | Authorizes current Corrective-001 only. |
| #263 | `3e32a190...` | PERSONA GOVERNANCE CANDIDATE | DRAFT/OPEN/UNMERGED; requires independent review; PM author does not self-accept. |

## Global rules

1. Historical evidence is preserved, not cleaned up to make the graph look simpler.
2. Evidence-only/review-only PRs are not implementation merge candidates.
3. Failed exact candidates retain their exact SHA and failure verdict.
4. A new RC requires a fresh A lineage whenever Resident-visible/runtime semantics changed.
5. B/C must descend from the currently accepted fresh lineage only.
6. No historical World, Claim set, transcript, or decision package may be copied into a new run as a semantic shortcut.
7. Closing a PR does not delete its evidentiary value; open status does not imply merge eligibility.
