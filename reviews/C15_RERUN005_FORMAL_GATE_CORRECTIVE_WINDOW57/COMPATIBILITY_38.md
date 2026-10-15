# Original 38 compatibility matrix

Source unchanged; tests from PR #361 exact commit in disposable detached worktree with only current delivery packet/Artifact overlaid. Final packet SHA256 04123169ec305273bd971f6254acb66f4bfdccf9bcce29d52e3d93d9fadf5e0c. DEVELOPMENT ONLY; formal 38 remains PENDING.

| Historical case | Development result | Formal |
| --- | --- | --- |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_artifact_delivery::test_exact_tar_into_independent_sandbox_runs_pinned_entry | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_artifact_delivery::test_artifact_substitution_rejected_before_materialization | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_crash_recovery::test_sigkill_after_request_never_regenerates_or_redispatches | BLOCKED_RUNNER_IDENTITY_OR_STARTUP | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_crash_recovery::test_absent_external_response_bounded_fail_closed | BLOCKED_RUNNER_IDENTITY_OR_STARTUP | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_current_trusted_adapter::test_real_core_external_publisher_with_c15_remote_barriers[due] | BLOCKED_RUNNER_IDENTITY_OR_STARTUP | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_current_trusted_adapter::test_real_core_external_publisher_with_c15_remote_barriers[user] | BLOCKED_RUNNER_IDENTITY_OR_STARTUP | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_current_trusted_adapter::test_real_core_external_publisher_with_c15_remote_barriers[summary] | BLOCKED_RUNNER_IDENTITY_OR_STARTUP | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_current_trusted_adapter::test_real_core_external_publisher_with_c15_remote_barriers[delivered] | BLOCKED_RUNNER_IDENTITY_OR_STARTUP | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_identity_delivery::test_independent_location_exact_bytes_import_resolution | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_identity_delivery::test_identity_substitution_fails_before_start[source] | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_identity_delivery::test_identity_substitution_fails_before_start[manifest] | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_identity_delivery::test_identity_substitution_fails_before_start[added_file] | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_identity_delivery::test_identity_substitution_fails_before_start[scripted_router] | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_identity_delivery::test_executable_substitution_rejected | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_identity_delivery::test_signer_not_importable_in_recovery_caller | FAIL_PUBLISHER_IMPORT_CONTRACT | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_mechanical_candidate::test_durable_request_and_response_consumption | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_mechanical_candidate::test_duplicate_response_exact_idempotence_and_conflict | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_mechanical_candidate::test_stale_response_rejected | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_mechanical_candidate::test_hash_identity_mismatch[request_id] | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_mechanical_candidate::test_hash_identity_mismatch[request_sha256] | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_mechanical_candidate::test_invalid_directive_rejected_before_publication | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_mechanical_candidate::test_missing_response_no_default_or_fallback | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_mechanical_candidate::test_tampering_fail_closed[request] | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_mechanical_candidate::test_tampering_fail_closed[response] | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_mechanical_candidate::test_tampering_fail_closed[ledger] | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_mechanical_candidate::test_restart_reopens_same_outstanding_request | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_mechanical_candidate::test_core_zero_local_minting_authority | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_mechanical_candidate::test_actual_user_runner_waits_for_external_bytes | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_mechanical_candidate::test_actual_due_work_empty_entry | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_mechanical_candidate::test_actual_due_work_live_return_has_no_core_authenticity | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_mechanical_candidate::test_historical_publisher_envelope_is_not_schema_proof | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_mechanical_candidate::test_accepted_relay_requires_authentication_before_application | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_mechanical_candidate::test_ambiguous_response_json_fails_closed[{"response_version":1,"response_version":1}] | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_mechanical_candidate::test_ambiguous_response_json_fails_closed[{"x":NaN}] | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_mechanical_candidate::test_durability_error_never_becomes_publication_success[request] | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_mechanical_candidate::test_durability_error_never_becomes_publication_success[response] | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_mechanical_candidate::test_durability_error_never_becomes_publication_success[response_replay] | PASS | PENDING |
| reviews.C15_RERUN005_OPERATOR_HARNESS_WINDOW53.test_mechanical_candidate::test_live_wal_busy_checkpoint_cannot_be_archived | PASS | PENDING |
