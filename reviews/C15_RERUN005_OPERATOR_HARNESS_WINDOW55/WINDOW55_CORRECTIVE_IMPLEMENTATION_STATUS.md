# C15-RCC-RES-A-RERUN-005 — Window 55 Corrective Implementation Status

**Disposition:** `IMPLEMENTATION_WIP_COMPLETE / FORMAL_VALIDATION_PENDING / DO NOT MERGE`

This records the authorized Harness-only implementation and development-stage verification. It does **not** constitute approved-Runtime validation, the formal 38-condition regression, real Core/C15 injection, independent acceptance, or Resident launch authorization.

## Scope and source identity

- Work remained within the RERUN-005 standalone Harness and the new `reviews/C15_RERUN005_OPERATOR_HARNESS_WINDOW55/` engineering-test area.
- No changes were made to `src/aios_core/**`, `tools/c15_persistence/**`, product `tests/**`, frozen fixtures, evaluator/release/operator workflows, Resident state, or PR #361/#362/#363 evidence.
- Source commit: `b80b06e0df97cc81f47c7661295e235ae37eb6ad`.
- Final `harness/IDENTITY.json` SHA-256: `ef8cb44913c50fad7f5da8b3dcc8c20a510ea66d15af14c090e147e037e682cd`.
- Final `harness/launch.py` SHA-256: `6b46ac1531e04aeb836066c403898e7917a44857cfff910e819a45c633ff436b`.
- The manifest closes over 21 Harness Python files, 79 Core Python files, 18 C15 persistence Python files, file and directory modes, and runtime identity metadata. The scanner's protected snapshot includes the manifest itself (119 protected files total).

## Corrective work

| Blocker | Implementation | Development evidence / remaining boundary |
|---|---|---|
| `PM54-BLK-001` — protected import identity | Replaced the narrow import check with a closed Harness/Core/C15 tree inventory. It rejects unlisted files and directories, `.pyc`/`.so` shadows, package overlays, symlinks, hardlinks/duplicate inodes, mode or byte drift, device boundaries, and nested mount overlays. Reads use directory-fd traversal, `O_NOFOLLOW`, `O_NONBLOCK`, size limits, before/after inode and metadata checks, and a final path identity check. Approved modules execute from hash-pinned in-memory snapshots through a private source-only importer; the `tools` namespace has no ambient search path. Loaded module object, path, loader, and content identities are checked, including `r005.checks` and `aios_core.headless.core`. The isolated child bootstrap separately verifies the exact `launch.py` bytes before execution. | Synthetic attacks cover exact `checks.pyc/.so` and `headless.core.pyc/.so` shadows, unapproved/package files, symlink/hardlink aliases, same-byte inode substitution, post-read path replacement, mounted overlays, and module substitution. A final recorded test also scanned the actual repository tree. Approved-Runtime module execution remains pending. |
| `PM54-BLK-002` — Runner registration and authorization | Removed caller-supplied PID identity. AF_UNIX RPC authenticates kernel `SO_PEERCRED`; the Publisher accepts registration only from the exact live Runner PID/UID/GID, tied to a pidfd/lifetime pipe and `/proc` start time. Registration is one-shot and bound to the random Runner instance, operation, request digest, Core attempt, provenance, and Publisher key. Runner-side RPC also pins Publisher PID and process start time. Registration state is in-memory only and is never restored. Resident response authorization is separate: a random, one-use token is issued per registered request and bound to the operation and Runner instance; it is not returned over Runner registration RPC or persisted, and is disclosed only via a validated controlling TTY (never stdout/log files). It is retired only after proof publication. Authorization failure produces no proof or durable success acknowledgement. | Tests cover a same-UID child self-claiming the Runner's true PID, PID-start mismatch/restart/replay, missing Publisher process identity, a successful kernel-peer RPC, operation/attempt/provenance binding, and Resident-token request/operation/instance scope and retirement. Formal Publisher/Runner process integration remains pending. |
| `PM54-BLK-003` — remote-authority-gated completion | Operation state now moves from an exact `started` marker to a durable `remote_committing` candidate containing the exact operation/spec/result digest. Local `completed` is written only after the authoritative remote commit is verified and its candidate bytes equal the local candidate; finalization re-reads and byte-checks the current disk candidate. Recovery binds the operation, result, remote ref, and commit; it compares the local persistence tree with the remote commit (allowing only append-only audit growth), re-anchors only after exact verification, and replays cached results without re-entering Core or a semantic model. CAS uncertainty or mismatch fails closed. | Fault coverage is runnable through the Window 55 test command for (1) before local result write, (2) after local candidate write/before remote commit, (3) a CAS race during push, (4) remote commit before local confirmation, and (5) restart recovery after remote commit/local-head uncertainty. The Git/C15 tests use temporary bare repositories and synthetic backend state only; formal Core/C15 fault injection is pending. |

## Recorded development run

- **Classification:** `DEVELOPMENT_TEST_ONLY`
- **Command:** `bash reviews/C15_RERUN005_OPERATOR_HARNESS_WINDOW55/run_development_tests.sh`
- **Result:** exit code `0`; 33 tests, 0 failures, 0 errors, 0 skipped.
- **Python:** 3.11.2; `/usr/bin/python3` (real path `/usr/bin/python3.11`).
- **Source commit:** `b80b06e0df97cc81f47c7661295e235ae37eb6ad`.
- **Tested-source SHA-256:** `c23c3831f7f458958e35e719f38b53e8fa79aa4b3abf17c34c0283a54081a279` (canonical digest over the sorted source inventory; per-file hashes are in the record).
- **Identity-manifest SHA-256:** `ef8cb44913c50fad7f5da8b3dcc8c20a510ea66d15af14c090e147e037e682cd`.
- **Approved Runtime:** not present at the qualified path; not used. The run record labels formal Runtime validation pending.
- Run directory: `development-test-runs/20261014T070025Z-4556/`
  - `test-record.json` — Python/executable, commit, tested-source and manifest hashes, command, exit status, test type, Runtime status, and artifact hashes.
  - `stderr.txt` — complete raw unittest output; `stdout.txt` — raw stdout (empty for this runner).
  - `test-results.xml` — JUnit-equivalent result.

Earlier exploratory runs are retained in the same `development-test-runs/` directory with their own source hashes and records; the 33-test run above is the final record for the current implementation.

## Formal boundary and repository state

The approved Python 3.12.14 Runtime was not available in this environment. Therefore the original formal 38-condition regression, approved dependency/runtime checks, real Core/C15 fault-injection integration, and independent acceptance have **not** run and are **not** claimed as passed. Development tests do not replace or reduce any of those conditions. Formal validation remains gated on the approved Runtime and PM authorization.

No Resident A/B/C was started, no Cursor 1 was revealed, and no merge or launch authorization was issued. PR #364 remains OPEN/DRAFT; its GitHub head remains `b80b06e0df97cc81f47c7661295e235ae37eb6ad`. This checkout is on Arena's fixed session branch `arena/16809921-haneof-aios-core-v3-0`; no push, commit, or PR update was made.
