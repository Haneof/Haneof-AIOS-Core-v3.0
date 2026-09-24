# C15 RCC Resident B Preflight - Real A Mechanical Import Report (Desensitized) - 2026-09-24 v2

Branch: `arena/01a0cf25-haneof-aios-core-v3-0`
PR: #125 OPEN (BLOCKED / DO NOT MERGE)
Exact-head: `2528c22a0d3ffc5107b385aee2db9cd7e7238afc`
Previous exact-head: `def9174d0c428a307513770aae635a5c5ebacf8b` (real-a-312 SUCCESS 35924742929)
New exact-head: `2528c22` real-a-312 Run `35924990859` SUCCESS, c15 Run `35924990848` SUCCESS, p16 Run `35924990895` SUCCESS

## 1. Source Evidence - Fixed A

- Fixed A SHA: `3e51f728d7959048b75fea01d405bc837b0e8185` (from PR117 `arena/01a0cca8-haneof-aios-core-v3-0`)
- Fixed source path: `reviews/internal_habitation/c15-rcc/v1/runs/resident-a-final-rerun-20260923/`
- Branch SHA equals Fixed SHA: true (verified in CI)
- Operator SHA (tested SHA): `2528c22a0d3ffc5107b385aee2db9cd7e7238afc`
- Mode: exact-head (checkout `${{ github.event.pull_request.head.sha || github.sha }}`)
- CORE_SHA (frozen): `bcd6bf353126318f9a97076b52ec1740d43f35a4` (src/aios_core tree)
- FIXTURE_HASH: `sha256:7ccb309d207cb6ee240fbc008ee4f535e25571f04ba7ca1b7c95bf9afb5ebf46`

### HASHES (from tools/c15_preflight/audit.py)

- private_world.sqlite: `9ff2b13cc1ec6e4d61a7910b4177ed3e1f25cfc47df8e18481a0199dd1aad395`
- world_index.sqlite: `55282a61d714f732f1b10fa6b450853f8425b5c9f741090fcaad0f1e673a6643`
- release_state.json: `b626cdd7d8ee16bc...` (full in manifest)
- restart_state.json: `7bc91400f6fa609e...`
- ARTIFACT_MANIFEST.json: `cc79379f4bcc7c65...`

Verified via `verify_files(directory, HASHES)` - exact bytes, refuse sidecars.

### Key Source File SHA256 (operator head 2528c22)

- freeze.py: `70c3979692d26404deeca2452ad54febf0cd6aa49a019660d8df829f4f8f1efc`
- publication.py: `d2854628d972c698da8b34a1ff52dd8662e4d57f48820bf2a3e3160d8b20cc1f`
- resident_broker.py: `c623877da99ea57784f371f6917918953a87a935b0bdda7d9e98d378f3678b96`
- driver.py: `9bf0ec92f402ed5ea5165fa0f8cfedd0d025ccf4b0fac6d0828e33fe429eb498`
- restart.py: `7bc644f37388aa829a60e459827038a8fc78f817a8b96770148b74d0fe991652`
- audit.py: `8ab0d1bcc27472f360c61ca30fbd4b3b7bbcb7ac726b471b39036aa6a6ef14ac`
- real-a-import-312.yml: `763f748e7f720ea258b3809e7d3f187e7bc0fe0d542f3c92b8449874148f7590`

## 2. Entry - Formal A Import

- Entry: `import_accepted_a_to_driver_run(staging, driver_run_dir, repo=REPO_ROOT, synthetic=False)`
- Synthetic flag: False (formal, not SYNTHETIC)
- Forbidden model adapter: Driver instantiated with model adapter that immediately errors if called (ensures no model calls during import)
- No manual driver_state.json creation, no skipping hash/Core checks, no real B, no wall-clock injection
- Operations on independent copy: `/tmp/real_a_original` is read-only save, `/tmp/real_a_staging` is independent copy for operations
- Original file hashes unchanged verified (staging does not modify original)

### CI Implementation (.github/workflows/real-a-import-312.yml)

- checkout: `ref: ${{ github.event.pull_request.head.sha || github.sha }}` for exact-head evidence
- setup-python: 3.12 (formal gate)
- Fetch accepted A branch: `git fetch origin arena/01a0cca8-haneof-aios-core-v3-0:accepted_a_ref --no-tags`
- Archive to `/tmp/real_a_original` via `git archive accepted_a_ref -- reviews/internal_habitation/... | tar -x`
- Record sys.version, sys.executable, operator SHA, branch SHA, fixed SHA equality
- Verify HASHES, stage_accepted_a, import_accepted_a_to_driver_run(synthetic=False, forbidden model), world/index 88/88, boundary 13->14, model_requests 0, cross-process restore

## 3. Environment

- sys.version: `3.12.14 (main, Aug 13 2026, 02:47:42) [GCC 13.3.0]` (from CI annotation)
- sys.executable: `/opt/hostedtoolcache/Python/3.12.14/x64/bin/python`
- PYTHONDONTWRITEBYTECODE=1, clean __pycache__ before checks
- No private A uploaded to Git/CI/artifact/chat: only desensitized receipt JSON in CI annotation
- No model calls, no wall-clock injection

## 4. Acceptance 10 Items

1) Input from fixed A hash match: PASS - branch_sha == fixed_A_SHA == 3e51f728d7959048b75fea01d405bc837b0e8185
2) Executed source matches frozen Core bcd6bf3: PASS - verify_core() checks HEAD:src/aios_core == CORE_SHA tree, no dirty
3) Formal A imports complete Driver checkpoint: PASS - import creates driver_run with private_world.sqlite, world_index.sqlite, release_state.json, restart_state.json, trace.jsonl, mechanical_restart.json
4) World/index 88/88: PASS - world_revision 88, index_watermark 88 (from restart_state final_world_revision, final_index_watermark, and SQLite watermark query)
5) Release boundary last_acked=13 next=14 no reveal/ACK/B completion: PASS - release_state pending_reveal None, last_acked 13, next 14, receipts length 13, no B14-22
6) Import status formal not SYNTHETIC: PASS - synthetic=False, validation status FORMAL_A_VERIFIED (not SYNTHETIC_A_VERIFIED), plan synthetic False
7) New session/turn per restart rules: PASS - restart_plan creates new session_id, conversation_turn_index reset per RESTART_KEYS 13 fields
8) Model requests 0: PASS - trace.jsonl contains 0 model requests (forbidden adapter would error if called)
9) Original file hashes unchanged: PASS - /tmp/real_a_original file hashes match HASHES before and after staging/import
10) Stop process + fresh-process load checkpoint via legal recovery, no model/B: PASS - cross_process PASS - fresh process restores driver checkpoint via restore_frozen? Actually via Driver loading existing driver_run, no model, no B, no trace.jsonl exclusive create conflict fixed by using new trace file

## 5. Separate Reports

- synthetic_mechanics: PASS (131 preflight + 146 regression, Python 3.12.14, exact-head 2528c22, 0 failures, 0 skipped)
- real_A_import: PASS (Run 35924990859, receipt JSON with world_revision 88, index_watermark 88, last_acked 13, next 14, model_requests 0, cross_process PASS)
- actual_namespace_probe: INCONCLUSIVE (unshare permission not permitted in GitHub runner, expected)
- actual_Resident_isolation: BLOCKED (real Resident not launchable without formal approval, by design)
- launch_authorized: false

## 6. Publication / Freeze Fixes (this round)

### Source Evidence Non-Mutating

- _verify_sqlite_integrity now:
  - Refuses if sidecar present (-wal/-shm/-journal) before verification, preserving original bytes
  - Uses immutable open only, no fallback to ro mode; if immutable fails, explicitly stop with ValueError
  - MUST NOT delete sidecars, verifies no sidecar created after verification
  - File list and bytes unchanged regression enforced

### Publication Confirmation Not Only exists()

- create_receipt:
  - Checks for existing receipt, verifies it if present (prevents marking CONFIRMED only by exists)
  - After atomic_json + parent fsync, verifies receipt via load_and_verify_receipt (complete, valid, matching)
  - Parent fsync failure -> persistence uncertain, cannot ordinary auto pass, raise, require explicit re-verification
  - Receipt incomplete/invalid/mismatched after creation -> ValueError, uncertain

- freeze exception handling:
  - Distinguishes three states: already completed prescribed commit steps (receipt_created True + receipt_valid True), commit result uncertain (receipt missing/incomplete/invalid/parent fsync failed), re-confirmed via independent explicit recovery (requires load_and_verify_receipt actually executed)
  - Uses load_and_verify_receipt to verify complete receipt and package and fixed pin, not just exists()
  - receipt_created flag only True if create_receipt succeeded including parent fsync and verification
  - If receipt exists and valid but flag false (parent fsync after receipt failed), mark UNCERTAIN, not CONFIRMED, to force explicit verification via confirm_uncertain_package

- confirm_uncertain_package:
  - Requires operator attestation with required checks manifest_hash, file_digests, sqlite_integrity, watermark_match
  - Performs actual mechanical checks corresponding to verified_checks
  - Verifies receipt after creation
  - Does not overwrite existing valid receipt, ordinary restore should be used

### Broker Declaration Alignment

- Based on approved input structure and source, not string blacklist
- _check_packet_boundary:
  - Requires packet keys == {protocol, request_id, kind, input_sha256, input}, protocol c15-resident-broker-v1, kind runtime
  - Approved snapshot keys: user_input, wake_reason, cockpit, capability_catalog, capability_history, round_index, remaining_tool_rounds
  - Forbidden: world_revision, index_watermark, release_sha256, driver_state, session, clock, private_world, world_index, release_state, operator, git_metadata, private_a
  - Operator private checkpoint, credentials, governance must not enter model input
  - No arbitrary filtering/rewriting real Runtime semantic content
- Synthetic endpoint:
  - Transport test double only, does NOT claim no filesystem unless OS permission verified
  - No sensitive info sent and process has no read permission separately accounted
  - Logs has_auth_header, has_forbidden_private, has_token_in_body, has_repo_in_body
- Credentials stay in HTTP auth layer (Authorization Bearer), not in model message or ordinary log
- Core provided legal AIOS capability calls retained via Runtime execution, not filtered
- c15-resident-broker-v1 is internal protocol, not require user to develop compatible external model service
- Provider not yet selected, clearly pending config, no Token in chat, no fake接入 completed
- Request/reply binding validation, error propagation, data boundary code shown

## 7. No Private Material

- No private World content, no trace.jsonl content, no driver.log, no private_world.sqlite bytes in report
- Only hashes, watermarks, release boundary, model count, exit status
- Source file hashes are of operator code, not private A

## 8. CI Evidence

- c15-operator-preflight Run 35924990848: 131 preflight, 146 regression, Python 3.12.14, exact-head 2528c22a0d3ffc5107b385aee2db9cd7e7238afc, 0 failures, 0 skipped
- p16-convergence-gate Run 35924990895: SUCCESS
- real-a-import-312 Run 35924990859: SUCCESS with annotation JSON:
  {"sys_version":"3.12.14 (main, Aug 13 2026, 02:47:42) [GCC 13.3.0]","sys_executable":"/opt/hostedtoolcache/Python/3.12.14/x64/bin/python","operator_sha":"2528c22a0d3ffc5107b385aee2db9cd7e7238afc","branch_sha":"3e51f728d7959048b75fea01d405bc837b0e8185","fixed_A_SHA":"3e51f728d7959048b75fea01d405bc837b0e8185","branch_equals_fixed":true,"world_revision":88,"index_watermark":88,"last_acked":13,"next_sequence":14,"model_requests":0,"cross_process":"PASS"}

## 9. Remaining Blocks

- actual Resident access isolation: requires OS-level namespace/cgroup mechanisms not available in GitHub runner, reported as INCONCLUSIVE/BLOCKED, launchable false until formal approval
- No real B14-22/C future/real Resident: not executed, by design
- No B/C/R6 PASS, no self-release, no DONE while incomplete

## 10. Fault Injection Results

- test_fault_window_after_publish_before_receipt: PASS - no receipt, blocked, driver FAILED UNCERTAIN
- test_fault_window_receipt_write_and_dir_fsync: PASS - atomic_json failure, no receipt, blocked
- test_fault_window_receipt_parent_fsync_after_receipt: PASS - per new strict protocol, parent fsync after receipt failure -> UNCERTAIN, ordinary restore BLOCKED until explicit confirm_uncertain_package, driver receipt_created False
- test_fault_window_after_receipt_before_frozen_checkpoint: PASS - receipt exists, restore succeeds, driver FAILED CONFIRMED_BUT_SOURCE_FAILED (receipt is commit point)
- test_no_uncertain_product_considered_confirmed: PASS - uncertain product without receipt blocked
- test_confirm_uncertain_package_*: PASS - blank/arbitrary attestation rejected, missing/tampered/wrong pin rejected, verified_checks correspondence, no overwrite existing receipt
- test_checkpoint_loss_cannot_bypass_via_accepted_a_import: PASS - existing progress -> checkpoint loss/damage -> accepted_a_dir import rejected, no overwrite, no deleting WAL/SHM/journal

## 11. End Condition

- Formal import + cross-process load result: PASS (88/88, 13->14, model 0, cross-process PASS)
- Source + evidence delivered: PASS (key sources in reviews/key_sources_2528c22/, diff attached)
- Remaining blocks listed: PASS (isolation BLOCKED, no B/C launch)
- No DONE, no B/C launch

Launch authorized: false
