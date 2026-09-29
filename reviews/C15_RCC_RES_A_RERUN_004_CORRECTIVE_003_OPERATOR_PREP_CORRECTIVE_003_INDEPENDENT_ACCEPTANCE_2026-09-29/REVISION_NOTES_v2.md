# Reviewer probe suite — revision 2 correction notes

Role: Independent Resident Launch Infrastructure Acceptance Reviewer.
Candidate: PR #292 head `42a63ed4416585fc0a02045e0bd5190f32a01a2b` (unchanged throughout).

Revision 1 (`probes/`, freeze `REVIEWER_PROBE_FREEZE.json`) was frozen and committed
before its first adversarial execution and produced **39 passed / 9 failed**
(`raw/reviewer_probes_v1.raw.txt`). Every one of the nine failures was triaged to a
probe-defect hypothesis and each hypothesis is now closed by construction or by
direct evidence. Revision 1 and its raw results are preserved unmodified; revision 2
(`probes_v2/`, freeze `REVIEWER_PROBE_FREEZE_v2.json`) is frozen separately and was
executed against the same candidate:

> **revision 2 result: 49 passed / 0 failed, rc=0, 154.31 s**
> (`raw/reviewer_probes_v2.raw.txt`, xml `raw/reviewer_probes_v2.xml`)

## Classification of the nine revision-1 failures (all probe defects)

| # | Revision-1 test | Observed failure | Classification and root cause | Revision-2 correction |
|---|-----------------|------------------|-------------------------------|-----------------------|
| 1 | `test_ra01_two_process_same_intended_request_single_dispatch` | 2 `request_published`, "duplicate semantic dispatch" | **Probe defect — semantic conflation.** The publisher's identity rule is `req-<sequence:04d>-<kind>-<sha8(body)>`; without a caller-declared identity two submissions are *two distinct decision requests* (different sequence), not one duplicated request. The probe asserted a duplicate-suppression contract that only the declared-identity path carries. | Declared-identity race probe (`test_ra01_two_process_explicit_identity_single_dispatch`) plus an informational implicit-identity boundary probe. |
| 2 | `test_ra04_handler_crash_after_dispatch_resumes_without_second_dispatch` | route `recovered_durable_response` ≠ expected `resumed_dispatched_request` | **Probe defect — over-specified route.** Both routes are legal resume paths depending on whether the external response won the race; the binding requirement is "resume, never re-dispatch". | Accept both routes; assert exactly one handoff and the correct request id. |
| 3 | `test_ra05_stale_lock_file_after_process_death` | `FileNotFoundError: hold-gate/go` | **Probe defect — rendezvous on an unspecified handshake.** The `lock-hold-stop` worker never signalled readiness, so the probe timed out and then wrote into a non-existent gate directory. | Worker now signals readiness only after acquiring the lock and holds the lock while waiting for `go`; the probe SIGKILLs the holder and verifies a fresh writer proceeds. |
| 4 | `test_ra05_contention_is_real_cross_process` | `FileNotFoundError: hold-gate-2/go` | Same root cause as #3. | Deterministic rendezvous plus positive assertions: a second process cannot acquire, and no record appears while the lock is held. |
| 5 | `test_ra05_nested_mutation_does_not_self_deadlock` | `FileNotFoundError: requests/ra05-nested.json` | **Probe defect — wrong helper.** The torn-down assertion used the artifact-aware `assert_linear` on a deliberately raw ledger record that has no artifact file. | Chain/ordinal/uniqueness assertions directly on the ledger. |
| 6 | `test_ra06_tamper_between_artifact_write_and_ledger_append` | `AssertionError: request digest drift` | **Probe defect — conflated expectations.** The probe deliberately overwrites a published artifact mid-publication, then used a helper that (correctly) reports the drift as an invariant violation. Drift caused by an external process after `fsync` cannot be prevented by the writer; the contract requires it to be *detected* and *never enter a semantic result*. | Assert: no dispatch of tampered bytes, integrity reports `request file digest mismatch`, the semantic read path fails closed, and a same-identity retry never adopts the drifted bytes. |
| 7 | `test_ra06_direct_consume_after_request_file_mutation` | `KeyError: 'request_sha256'` | **Probe defect — wrong receipt field.** The response publish receipt carries the *response* digest; the probe read a request digest out of it. | Compare the response bytes to the response ledger digest; compare the envelope's `request_sha256` to the durable request binding obtained from the ledger. |
| 8 | `test_c7_exact_runtime_pins` | `foreign import path: /home/user/Haneof-AIOS-Core-v3.0/src/aios_core/__init__.py` | **Environment/execution-method defect.** The product repository's `pyproject.toml` sets ini `pythonpath = ["src"]`; because the probe suite lives below the repository root, pytest injected the live-main `src` tree (later on `sys.path`) and it shadowed the frozen RC. Directly reproduced outside the probe tier and then confirmed fixed by `-o pythonpath=`. | Execution method pins `-o pythonpath=` and runs from outside the product repository; `probes_v2/conftest.py` adds a session guard that fails loudly if any foreign `aios_core` is importable, and C7 additionally asserts the frozen Core tree hash. |
| 9 | `test_c8_clean_room_startup_boundary` | `runner.py references 'fixture'` | **Probe defect — naive substring match.** The token appeared inside a docstring stating that there is deliberately *no* fixture rule. | AST-based reachability: imports, dynamic imports, attribute reach and forbidden literal paths only. |

No candidate defect was concluded from any revision-1 failure, and no revision-1
result was used to weaken or re-tune a revision-2 expectation: revision-2
expectations derive from the packet contracts, the corrected execution method and
the invariants above.

## Evidence of no post-execution tuning

Revision-2 sources were last modified before the freeze (10:29 UTC), the freeze
artifact was written at 10:30 UTC, and the first adversarial execution of revision 2
ran at 10:31–10:32 UTC. `raw/reviewer_probes_v2_integrity.json` records the frozen
source hashes, the post-run source hashes (identical), the freeze/result hashes and
all file mtimes. The enumeration collected from the frozen sources matched the frozen
enumeration exactly (`diff rc=0`,
`raw/reviewer_probes_v2_enumeration.diff` is empty).

Note on commit ordering: revision 1 was committed before its execution; revision 2's
freeze artifact was written into the working tree before execution and committed
immediately afterwards together with the raw results. That ordering is recorded here
transparently, and the mtime/hash evidence above is the binding proof that the
expectations did not change after observing candidate behavior.
