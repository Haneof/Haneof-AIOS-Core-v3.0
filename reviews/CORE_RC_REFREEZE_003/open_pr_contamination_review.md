# CORE-RC-REFREEZE-003 — Open-PR Contamination Review

Snapshot time: **2026-09-28T13:43:50Z** (UTC)
Repository: `Haneof/Haneof-AIOS-Core-v3.0`
Freshly fetched live `main`: `c532b9fe3dfff594ee0b68bcac4fff6160f8b4b5`
Frozen software target: `f20f2edfa7af00d0286493fd15196ca9503bc315`

## Method and scope

- Fresh GitHub REST inventory: `GET /repos/Haneof/Haneof-AIOS-Core-v3.0/pulls?state=open&per_page=100`, followed by paginated `/pulls/{number}/files` requests for every open PR. Pages were drained until fewer than 100 files were returned; evidence-heavy PRs with 100+ paths were fully enumerated. The complete path/count snapshot is `open_pr_snapshot.json`.
- **31 open PRs** were present at this snapshot. Changed paths were classified for `src/**`, `tests/**`, `.github/workflows/**`, `pyproject.toml`, and recovery/runtime/Resident release evidence.
- Candidate heads, bases, draft status and changed-file categories were read from the live GitHub API; an open PR was not treated as accepted or merge-authorized.
- Exact code-bearing heads #110, #111, #113 and #126 were fetched as remote review refs for blob comparison against the frozen software target. Their unmerged source/test/workflow changes are not imported into this RC.
- This inventory is a point-in-time contamination screen, not a merge authorization. It must be rechecked by the Independent Acceptance reviewer and again before any later integration.

Fresh target-to-main verification at this snapshot:

| Protected surface | `f20f2ed...` → `c532b9f...` drift |
|---|---:|
| `src/**` | **0 paths** |
| `tests/**` | **0 paths** |
| `pyproject.toml` | **0 paths** |
| `.github/workflows/**` | **0 paths** |
| `src/aios_core` tree | identical: `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623` |
| `tests` tree | identical: `7e33b5ef8432370234965d3ccd61248c703c4019` |
| `.github/workflows` tree | identical: `fb168f8540070ff7b0c521e5990b03c7f3c56bf4` |

The seven commits reachable after the frozen software target resolve only to the five aggregate governance/evidence paths recorded in `source_manifest.json`. No implementation workflow or package metadata moved after `f20f2ed...`.

## Explicit required classifications

| Item | Live status / exact identity | Surface and disposition |
|---|---|---|
| **#258 — failed historical exact** | OPEN / DRAFT; head `1ebf51c4cb905e2a2578a09b64007b50bca0d4ac`; base `main` | 4 Core source files, 7 ordinary tests and its recovery workflow. This is the failed exact candidate, not a new accepted implementation. **Do not import, cherry-pick, rebase, merge, or use as the RC target.** Preserve its historical failure identity. |
| **#261 — failed review-only evidence** | OPEN / DRAFT; head `b9d692ddca055b13fb29e646186e929a08bf8955`; base is failed #258 exact | Review report/probes plus 6 files under `tests/independent_acceptance/`; no production `src/**`. It records `ACCEPTANCE_FAIL / blocker=1` for the original trusted-return task. **Review-only; not code, not this RC's acceptance, and not importable into the release test tree.** |
| **#263 — persona-governance candidate** | OPEN / DRAFT; head `3e32a190f644dc9901b428b62fcbde2e01fe6d50` | 9 governance/constitution files; zero `src/**`, `tests/**`, workflows or `pyproject.toml`. It is unaccepted and changes constitution/baseline documentation on its own branch. **Not imported or modified; frozen constitution hashes remain those at `f20f2ed...`.** |
| **#265 — C15 exit-readiness draft** | OPEN / DRAFT; head `7734e434777ce0b03b5b106b086ebfac7de4e699` | 17 governance/checkpoint/prompt files; zero `src/**`, `tests/**`, workflows or `pyproject.toml`. It contains only draft future C15 readiness material and is not accepted. **Not imported, edited or merged; this task does not enter evaluator/close.** |
| **PM reviewer CPython 3.12 validation branch** | Branch `governance/corrective001-ia2-py312-replay-20260928`; head `679717e9713b1274ef9e6ddc3e38650652889ac0`; base `0df757e9666c2c75571df7a7a3dedf27d44e5b7f`; not an open PR | Dedicated workflow plus reviewer probe/report artifacts; no Core source change. It is corroborative PM evidence for Corrective-001 IA (`36423849252` is separately recorded in the integration receipt), **not a re-freeze regression run and not part of this RC**. No reviewer-only tests are copied into `tests/**`. |
| **#254 — old persistence WIP** | CLOSED / DRAFT / UNMERGED; branch head `a2d815c9f5154d87a56b152ed7cf5d1eb1baaaae` | Its first scope-violating WIP `f7848952b6519fc40f50806f4a4d8d350ac0f38a` changed `src/aios_core/runtime/turn_runtime.py` outside the frozen persistence scope. Task board classifies that SHA `SCOPE_VIOLATION / NOT_A_CANDIDATE`. **Keep frozen; do not resume or import.** |
| **New PRs** | No newly opened PR beyond the 31 items below at snapshot time | Every currently open PR was included in the API scan. This RC candidate PR had not yet been opened at the time of the inventory; its later exact head is separately pinned in the candidate PR comment. |

Corrective-001's accepted implementation PR **#264** is already MERGED at accepted exact `a73e186d40688f5dc181b1128a62eff37a974409` / integration point `f20f2edfa7af00d0286493fd15196ca9503bc315`. The review-only exact acceptance report remains `eeda251e057e98b15a919694af4689786faf8c55`; supplemental post-acceptance evidence is classified by the merged #268 adjudication as supplemental, not a replacement exact.

## Complete open-PR inventory (31)

| PR | Head (short) / status | Relevant surface | Disposition for this RC |
|---:|---|---|---|
| #265 | `7734e434` / draft | Governance/checkpoint/future C15 prompts only | Explicitly excluded; no evaluator/close work. |
| #263 | `3e32a190` / draft | Constitution/baseline and governance docs only | Explicitly excluded; no constitution drift imported. |
| #261 | `b9d692dd` / draft | 6 reviewer-only test files + IA evidence | Failed IA for #258; review-only. |
| #258 | `1ebf51c4` / draft | `src/**`, `tests/**`, recovery workflow | Failed historical exact; do not import. |
| #251 | `7b2556e7` / draft | 18 `tests/c15_persistence/**` files, 4 workflows, `pyproject.toml`, review/WIP artifacts | Draft persistence Corrective-002 WIP, unaccepted and outside this task; no import, rerun, or resume. |
| #249 | `08468beb` / draft | One persistence IA workflow plus review-only evidence | Review-only; not a release implementation. |
| #235 | `5b636740` / draft | A-003 Resident evidence-only (122 files; the paginated inventory is complete) | Historical A-003 is prior-RC-only; never hash-swap onto this RC. |
| #233 | `40492585` / draft | Prior REFROZEN-002 independent acceptance report/probes | Review-only evidence for prior RC-002; not current acceptance. |
| #230 | `2c846baa` / open | Prior response-recovery Corrective-002 IA evidence | Review-only/historical; no implementation import. |
| #216 | `63ca5923` / draft | C15 persistence Corrective-001 frozen WIP; 6 source, 24 test, 2 workflow files, `pyproject.toml`, 83 review/evidence files | PR body labels it `FROZEN_WIP / BLOCKED`; its reported tested head does not match the live PR head. No import, rerun, rebase, or resume in this task. |
| #205 | `d17ae972` / open | A-002 Resident evidence-only | Prior-RC evidence only; no hash swap. |
| #144 | `da35e477` / open | 3 legacy Core-diff-guard workflow files | Historical workflow candidate; no Core/test change and no import into frozen workflow tree. |
| #130 | `16eb1d40` / open | Operator preflight tests/workflow + evidence | Historical operator candidate; not software freeze input. |
| #126 | `8e31deca` / draft | 12 source, 3 test, 1 workflow changes; based on a non-main branch | Stale alternate-base Core candidate; changed blobs were checked against the freeze; not accepted or imported. |
| #125 | `b14b5d84` / open | 7 preflight tests, 3 workflows, review evidence | Explicitly blocked/do-not-merge historical preflight; not imported. |
| #121 | `b6e5ac93` / open | Resident-B evidence-only | PM-held/noncanonical B evidence; no software import. |
| #119 | `b58b8734` / open | Governance ruling only | Historical governance PR; no software drift/import. |
| #118 | `352b4875` / open | Governance plan only | Historical governance PR; no software drift/import. |
| #117 | `3e51f728` / open | Historical A-001 evidence-only | Old-Core evidence; not this RC's A lineage. |
| #113 | `72d902c7` / open | 7 source, 5 test, 1 workflow changes | Unmerged historical cognition-policy proposal; branch-specific blobs differ from current freeze; not imported. |
| #112 | `c3be5099` / open | Scale benchmark documentation only | Documentation/evidence; no software import. |
| #111 | `cf2dd154` / open | 4 source, 2 test changes | Unmerged historical cognition-fields proposal; branch-specific blobs differ from current freeze; not imported. |
| #110 | `34c6810a` / open | 7 source, 2 test changes | Unmerged historical cognition-policy proposal; branch-specific blobs differ from current freeze; not imported. |
| #109 | `dfca8d36` / open | Historical Resident-A evidence-only | No implementation; not reused. |
| #107 | `57943128` / open | Blocked-startup evidence and governance only | No Resident run/canonical software; not imported. |
| #101 | `bfbfa059` / open | Pre-fix Resident-A evidence-only | Superseded diagnostic evidence; not reused. |
| #92 | `9e870514` / open | C14 repair evidence plus one evidence workflow | Historical Resident evidence; not a Core implementation or current release workflow. |
| #79 | `546449a4` / open | C14 Resident-B evidence-only | Historical evidence; no software import. |
| #75 | `cb9b56b7` / open | C14 Resident-A evidence-only | Historical evidence; no software import. |
| #74 | `7f397479` / draft | C14 Resident-A trial artifacts only | Noncanonical historical evidence; no import. |
| #37 | `058bada3` / open | Central P16 triage documentation only | Documentation only; no software import. |

## Contamination ruling

At the fresh-main snapshot, **no open PR content was imported**. The frozen target is mechanically the accepted post-merge Corrective-001 software point. The current main delta after that point consists only of governance/evidence, with zero protected source/test/package/implementation-workflow drift. Historical and review-only PRs remain separate identities. In particular, #263/#265 and the frozen persistence work were left untouched; no tag, release, Resident run, A-004, B resume, evaluator, or C15 close was performed.
