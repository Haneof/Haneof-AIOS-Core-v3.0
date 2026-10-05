# Corrective-003 carry-forward gate inventory

This inventory documents the *formal workflow's fresh rerun*, not a claim that the gates have passed. The final exact-head hosted run and its artifact must be recorded in the PR after all evidence is committed.

| Required gate | Formal workflow step / evidence output |
|---|---|
| Full Core | Fresh complete Core regression → `core-regression.txt`, JUnit XML |
| Window20 A/B and Window17 | Frozen reviewer probes extracted by pinned blob and SHA → `window20-suite-a.txt`, `window20-suite-b.txt`, `window17-probe.txt` |
| Corrective-003 security | Frozen trust-root/replay/conflict/supersession checks and pinned integration tests → `corrective003-security.txt`, plus static workflow/security checks |
| Real process loss / SIGKILL | Fresh real process-loss and recovery tests → `real-process-loss.txt` |
| Clean wheel / headless | Non-editable wheel, clean venv, headless lifecycle → wheel/install/headless logs |
| Backup / restore | Byte-for-byte carry-forward backup/restore route B probe → `backup-restore-rebuild.txt` |
| Writer / restart / FIX / current-time / SCALE | Existing selected integration/runtime tests → `writer-restart-fix-scale.txt` |
| C15 actual pytest/JUnit classification | Actual pytest exit code, emitted JUnit, unchanged classifier self-test/adjudication → `c15-persistence.*`, `c15-adjudication.txt` |
| Open-PR contamination | Fresh GitHub open-PR/file snapshot → `open-pr-snapshot.json`, `open-pr-contamination.txt` |
| Frozen identities | Exact commit/tree/blob assertions and run-time source manifest → `frozen_identity.txt`, `source_manifest_runtime.json` |
| Protected drift | Same helper at initial/terminal snapshots plus positive/negative temp-repository matrix → `terminal-protected-drift*` |
| Publisher fault matrix | Exact inline publisher shell under mocked HTTP 201/200/401/403/500 and POST transport-failure cases → `publisher-exact-shell-fault-matrix.txt` |

## Carry-forward assets in this evidence directory

The formal gate references these unchanged copies because fresh `main` does not contain the open #336 candidate's evidence paths:

| New path | Read-only source in #336 at `5a5d384...` | SHA-256 of copied bytes |
|---|---|---|
| `probes/carry_forward/backup_restore_route_b.py` | `reviews/CORE_RC_REFREEZE_004/probes/backup_restore_route_b.py` | `0ed97a59ffda74bda5067f9362f3fee387ff5f622cfe11d0b7824e639066ce06` |
| `probes/carry_forward/c15_junit_classifier.py` | `reviews/CORE_RC_REFREEZE_004_CORRECTIVE_001/probes/c15_junit_classifier.py` | `6d9eb05e8dbd34127ff67f7cc0e9c7e431308895bfa2d1d864096f3fdb5816c3` |
| `probes/carry_forward/publisher_http_contract.sh` | `reviews/CORE_RC_REFREEZE_004_CORRECTIVE_001/probes/publisher_http_contract.sh` | `e4925f77458f6dc593ab4e9409b4d3bf5f7adc701b2bf8a32f466388dcd601d8` |

No C15 implementation, product test, Resident, evaluator, release manifest, or JUnit hardening change is included. The additional transport-failure matrix executes the exact inline publisher shell; it does not modify the carry-forward classifier or broaden C15 behavior.
