# IA28-BLK-001 — terminal protected-drift correction

## RED-first record

`raw/RED_FIRST_TERMINAL_DRIFT.txt` was produced before editing the formal workflow. The probe extracts both EREs from the exact #336 workflow and passes real `git diff --name-only` paths to GNU `grep -E` in a disposable repository. The initial pattern detects the synthetic changes, while terminal line 464 misses newly added/modified `.github/workflows/**`, `pyproject.toml`, and `setup.cfg`; terminal still matches the existing `src/**` and `tests/**` prefixes.

## Corrected behavior

The terminal check now compares the **initial main snapshot** (`RC004_LIVE_MAIN`, captured at the beginning of Job A) to the terminal main ref, not the frozen software commit to the terminal ref. It calls `probes/terminal_protected_drift_guard.sh`, the same shell helper invoked by the initial drift check and by all regression controls. The helper uses `git diff --no-renames`, so additions, modifications, deletions, and renames cannot hide the protected old path.

Protected classifications include:

- `src/**`, `tests/**`, `.github/workflows/**`;
- `pyproject.toml`;
- `setup.py`, `setup.cfg`, `setup/**`;
- `MANIFEST` / `MANIFEST.in`;
- `requirements*` and `requirements/**`;
- common dependency/build manifests (`Pipfile*`, `poetry.lock`, `uv.lock`, `tox.ini`, conda/environment YAML).

## Positive and negative controls

`probes/terminal_protected_drift_controls.py` creates a temporary Git repository with an initial snapshot and executes the exact shell helper used by formal CI. It asserts:

- no drift passes;
- late workflow additions/modifications fail closed;
- late `pyproject.toml`, setup, manifest, and requirements changes fail closed;
- existing `src/**` and `tests/**` protection remains active;
- protected deletion fails closed;
- an unrelated review-evidence change remains classified as unprotected and passes.

The hosted formal gate reruns these controls and separately invokes the guard on the initial-to-terminal main snapshot.
