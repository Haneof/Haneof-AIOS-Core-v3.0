# BLOCKER evidence: the candidate patch breaks frozen identity-pinned evidence

These runs were produced with the 2-line candidate patch APPLIED to
`harness/r005/response_authorization.py` (see
`../../CANDIDATE_FIX_enrollment_scope_gate.patch`).

Effect on the new Arena suite: the 8 RED defect-acceptance tests turn GREEN
(`../GREEN-after-patch`, 108/108, exit 0).

Effect on the PRESERVED Window55/Window57 evidence suites: regression.

| suite | frozen candidate | with candidate patch |
| --- | --- | --- |
| Window55 | 33 tests, OK, exit 0 | 33 tests, 5 failures + 3 errors, exit 1 |
| Window57 | 29 tests, 5 failures (host-path only), exit 1 | 29 tests, 6 failures, exit 1 |

New Window55 failures (all in `test_harness_identity.py`):
`test_actual_repository_protected_trees_match_pinned_identity`,
`test_detects_same_bytes_inode_replacement_after_initial_snapshot`,
`test_full_harness_core_and_c15_trees_scan_as_closed_identity`,
`test_private_finder_imports_from_snapshots_and_rejects_module_substitution`,
`test_rejects_unapproved_pyc_so_python_and_package_overlay` (4 params).

New Window57 failure: `test_exact_identity_and_closed_members`.

Root cause: `harness/r005/response_authorization.py` is identity-pinned twice.

* `harness/IDENTITY.json` -> `harness_files["r005/response_authorization.py"]`
  = `abc30a28661f22390a9f4a34df5d9764fe27e155f7c285c9e2008c16448defa6`,
  plus `accepted_baseline` = `703a8967878d8eaee70a8a8fce9df068204f5f76`.
* `RESIDENT_SAFE_LAUNCH_PACKET.json` -> member identity for
  `response_authorization.py` = the same `abc30a28...` digest, bound to the
  frozen `artifacts/resident-harness.tar.gz` delivery packet.

The patched file hashes to
`5ec8cc012fadfdc98d59e0566fb513bc9a6a234c48dafaba4722601485f69a28`, so both
pins fail. Regenerating them would create NEW official evidence and a NEW
candidate identity, which the Issue #388 authorization forbids ("do not ...
edit ... archived evidence"; "Do not change ... official evidence") and which
would require a fresh PM freeze before any Window69 formal validation.

Therefore the patch was REVERTED. The delivered branch head leaves every
protected tree byte-identical to `6fb725407569bc719c049587f67fe65e797eb734`.
