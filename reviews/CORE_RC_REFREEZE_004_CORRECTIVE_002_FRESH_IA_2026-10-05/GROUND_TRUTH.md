# Fresh Ground Truth — REVIEW_ONLY / DO NOT MERGE

Checked on 2026-10-05. This is reviewer-owned evidence for PR #336, not candidate evidence and not a merge authorization.

## PR and candidate identity

| Field | Independently checked value |
|---|---|
| Repository | `Haneof/Haneof-AIOS-Core-v3.0` |
| Fresh `main` | `5927d7917112819c53593149ee8fab1eebdcfda6` |
| PR | `#336`, `OPEN`, non-draft, `mergedAt=null`, base `main` |
| Candidate branch | `release/core-rc-refreeze-004-corrective-002-window28` |
| Candidate / current canonical head | `5a5d384f16798bfff46ffe03f87310b0eafb2321` |
| Candidate parent | `091ccc95e3e0d67ee7e01bdc576f821868cc98dc` |
| Candidate tree | `6976a82af383f89bce196e1d8ef766e24f6ed6c8` |
| Failed predecessor #330 | `2380121639865b1bd29176cf944f5a20afe4112d` |
| Failed predecessor relation | ancestor of candidate: YES |
| Frozen software SHA | `1cee3c5ad12f4b9098232bae11b51df786c5eb2f` |

Fresh `gh` queries returned PR #336 OPEN / non-draft / unmerged, exact head `5a5d384...`, and live branch `refs/heads/release/core-rc-refreeze-004-corrective-002-window28` at that same SHA. No candidate drift was observed during this review.

## Frozen tree identities

Independently recomputed from frozen commit `1cee3c5ad12f4b9098232bae11b51df786c5eb2f`:

- root tree: `70b2711258567863ea0d93025a6a07e39631726a`
- `src/aios_core` tree: `16f1487e291b009c55bee402abfd79fdacbae960`
- `tests` tree: `9db1bfa08143bc99fe03836e2752ee6e05694eb6`
- `.github/workflows` tree: `72cde9d2dc2b35d071bfa36c954dac2faff4a803`
- `pyproject.toml` blob: `b38833c7537fa60d5c2f02ed4bb19158d8995a11`

These match the frozen identities recorded in the candidate evidence.

## Candidate diff scope

Compared with failed predecessor `2380121639865b1bd29176cf944f5a20afe4112d`, the candidate has 23 changed paths: one modified `.github/workflows/core-rc-refreeze-004-formal-gate.yml` and 22 added files under `reviews/CORE_RC_REFREEZE_004_CORRECTIVE_002/`. No product implementation, product tests, tools, or `pyproject.toml` path changed. `git diff --check` passed. This is within the stated Window 28 change boundary.

The candidate evidence directory's 22-entry SHA-256 manifest was independently verified from the extracted candidate evidence directory; all 22 entries passed.

## Exact-head formal run and provisional pin

Fresh GitHub API metadata for run `37320392029`:

- event SHA: `5a5d384f16798bfff46ffe03f87310b0eafb2321`
- branch: `release/core-rc-refreeze-004-corrective-002-window28`
- event: `push`
- overall conclusion: `success`
- Job A / exact frozen software formal gate `111797678752`: `success`
- mandatory publisher `111800414428`: `success`
- whole-run identity seal `111800463630`: `success`
- uploaded artifact `11350081011`, digest `sha256:8dc40dad22814ffb081e5fe1817b45905e72dbc77bcecf432be2bce8b67771bd`
- provisional commit comment `203496684`, created for run `37320392029`
- branch head after the run: still `5a5d384f16798bfff46ffe03f87310b0eafb2321`

The formal run is real and exact-head, but its success does not falsify either static/mechanical counterexample in this report. Current branch equality after the run is not proof that a branch could not have advanced in the unsealed final interval.

## Collection limits

The GitHub artifact metadata and job conclusions were available. Downloading hosted logs/artifact bytes failed with Azure `EOF` in this environment, so the individual formal test counts in the candidate evidence were not independently re-executed. Local Python is 3.11.2 and pytest is unavailable; no claim is made that the full Python 3.12.14 suite was rerun locally.
