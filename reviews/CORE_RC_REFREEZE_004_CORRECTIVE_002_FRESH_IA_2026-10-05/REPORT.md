# Fresh Independent Acceptance — CORE-RC-REFREEZE-004-CORRECTIVE-002

> **REVIEW_ONLY / DO NOT MERGE**
> Reviewer-owned acceptance evidence. This report does not modify or authorize merging candidate PR #336.

## Verdict

**`ACCEPTANCE_FAIL / BINDING_BLOCKERS=2 / IA27-BLK-002_NOT_CLOSED / DO NOT MERGE`**

The exact candidate remains PR **#336** at `5a5d384f16798bfff46ffe03f87310b0eafb2321`, **OPEN / UNMERGED**. No candidate files or commits were changed. The candidate's latest exact-head hosted run is green, but that run did not exercise the final post-read race or a main-branch protected-drift update during the run.

### Binding findings

1. **`IA27-BLK-002` — whole-run identity remains vulnerable to a final check-to-completion race (BINDING / CRITICAL).** The final seal checks the canonical ref once, then checks run/comment metadata and prints `WHOLE_RUN_IDENTITY_SEAL=PASS`. A reviewer-owned local mock of the candidate's exact final-seal shell code advanced the ref immediately after that one branch response; the step still returned 0 and printed PASS while the mock ref held a different SHA. This is a deterministic counterexample to the claimed whole-run invariant. It is a local mocked-API reproduction, **not** a live GitHub Actions reproduction of that final interval.
2. **`IA28-BLK-001` — terminal protected-drift gate misses protected path changes (BINDING for the required carry-forward gate).** The initial check at workflow line 93 has the correct ERE escaping. The terminal check at line 464 doubles the backslashes; exact GNU `grep -E` probes miss `.github/workflows/**`, `pyproject.toml`, and `setup.cfg`. A protected main-branch change after the initial snapshot can therefore be logged but fail to make the terminal guard exit nonzero.

A lower-priority credential-audit regex issue is documented in `FINDINGS.md` as an observation, not a blocker: the current checkout explicitly sets `persist-credentials: false` and Job A is read-only.

## Ground truth

- Fresh `main`: `5927d7917112819c53593149ee8fab1eebdcfda6`.
- PR #336: `OPEN`, non-draft, base `main`; branch `release/core-rc-refreeze-004-corrective-002-window28`.
- Candidate head / current canonical branch head: `5a5d384f16798bfff46ffe03f87310b0eafb2321`.
- Candidate parent: `091ccc95e3e0d67ee7e01bdc576f821868cc98dc`.
- Candidate tree: `6976a82af383f89bce196e1d8ef766e24f6ed6c8`.
- Failed predecessor: `2380121639865b1bd29176cf944f5a20afe4112d` (ancestor of #336).
- Frozen software: `1cee3c5ad12f4b9098232bae11b51df786c5eb2f`.
- Latest exact-head formal run: [37320392029](https://github.com/Haneof/Haneof-AIOS-Core-v3.0/actions/runs/37320392029), overall success. Job A `111797678752`, publisher `111800414428`, and identity seal `111800463630` all report success. The exact candidate pin is provisional comment `203496684`.

Full identities, scope, control-run reconciliation, and evidence limitations are in `GROUND_TRUTH.md` and `CONTROL_ASSESSMENT.md`.

## Acceptance basis and limits

- Candidate workflow permissions, publisher behavior, exact candidate identity, and changed-path scope were reviewed. The diff from failed predecessor is one workflow modification plus 22 Corrective-002 evidence files; there is no `src/**`, product `tests/**`, `tools/**`, or `pyproject.toml` delta.
- The candidate's hosted green control advances the canonical ref during the 30-second guard; the old seal then fails/cancels. That is useful evidence for that interval, but does not close the interval after the final branch read.
- Candidate run `37289298552` is a separate legacy RED-control workflow (`w28-toctou-red-control.yml`, `cancel-in-progress: false`), not the corrected candidate workflow. It must not be counted as a reproduction of the candidate's final-seal behavior.
- The final-seal probe uses the exact shell block extracted from candidate SHA `5a5d384...` and mocked API responses. It does not model GitHub concurrency cancellation; the evidence labels that limitation explicitly.
- GitHub run metadata and the candidate's evidence manifest were checked. The hosted Azure artifact body could not be downloaded in this environment (`EOF`), and the local environment is Python 3.11 without pytest; full test counts remain candidate-reported rather than independently rerun here.

## Required disposition

Keep PR #336 **OPEN / UNMERGED / DO NOT MERGE**. Do not PM-integrate or merge it on the basis of the current green run. Any corrective work must leave #336 immutable and must demonstrate, with an exact final-window control, that no stale run can become authoritative after a post-read branch move; it must also correct and test the terminal protected-drift ERE. This review performed no corrective engineering.

## Evidence map

- `FINDINGS.md` — binding findings and non-binding observation.
- `GROUND_TRUTH.md` — exact GitHub and object identities.
- `CONTROL_ASSESSMENT.md` — hosted controls, permissions/publisher review, and limits.
- `probes/final_seal_postread_race.py` + `raw/final_seal_postread_race.txt` — exact candidate final-seal mock.
- `probes/terminal_protected_drift_regex.py` + `raw/terminal_protected_drift_regex.txt` — exact terminal guard false-negative reproduction.
- `probes/credential_guard_regex.py` + `raw/credential_guard_regex.txt` — non-binding credential-check observation.
- `SHA256SUMS` — reviewer evidence-file integrity list.
