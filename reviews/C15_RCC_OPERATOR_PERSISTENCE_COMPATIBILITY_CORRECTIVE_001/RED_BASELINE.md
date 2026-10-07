# RED BASELINE — WINDOW 49

## Execution Details

- **Test Path**: `tests/c15_persistence`
- **Invocation Mode A**: `~/.venv312/bin/pytest tests/c15_persistence --junitxml=reviews/C15_RCC_OPERATOR_PERSISTENCE_COMPATIBILITY_CORRECTIVE_001/red/baseline-bare-junit.xml -v`
- **Invocation Mode B**: `~/.venv312/bin/python3 -m pytest tests/c15_persistence --junitxml=reviews/C15_RCC_OPERATOR_PERSISTENCE_COMPATIBILITY_CORRECTIVE_001/red/baseline-junit.xml -v`
- **Python Version**: CPython 3.12.3
- **pytest Version**: 8.4.2
- **pydantic Version**: 2.13.5
- **Exit Code**: 1 (Failure)
- **Collected Items**: 78
- **Passed**: 32
- **Failed**: 46
- **Errors**: 0
- **Skipped**: 0
- **Mode A vs Mode B Equivalence**: 100% identical collected (78), passed (32), failed (46), and identical nodeid failure set.

## 46 Failing Nodeids

1. `tests/c15_persistence/killpoints/test_killpoints.py::test_kill_point_converges[K1]`
2. `tests/c15_persistence/killpoints/test_killpoints.py::test_kill_point_converges[K2]`
3. `tests/c15_persistence/killpoints/test_killpoints.py::test_kill_point_converges[K3]`
4. `tests/c15_persistence/killpoints/test_killpoints.py::test_kill_point_converges[K4]`
5. `tests/c15_persistence/killpoints/test_killpoints.py::test_kill_point_converges[K5]`
6. `tests/c15_persistence/test_corrective_002_remote_durability.py::test_k1_k5_survive_total_local_cache_loss_from_remote_only[K1_AFTER_REVEAL]`
7. `tests/c15_persistence/test_corrective_002_remote_durability.py::test_k1_k5_survive_total_local_cache_loss_from_remote_only[K2_AFTER_INGEST]`
8. `tests/c15_persistence/test_corrective_002_remote_durability.py::test_k1_k5_survive_total_local_cache_loss_from_remote_only[K3_AFTER_REQUEST_DISPATCH]`
9. `tests/c15_persistence/test_corrective_002_remote_durability.py::test_k1_k5_survive_total_local_cache_loss_from_remote_only[K3_TRUSTED_RETURN_DURABLE]`
10. `tests/c15_persistence/test_corrective_002_remote_durability.py::test_k1_k5_survive_total_local_cache_loss_from_remote_only[K4_AFTER_REPLY_AUTHENTICATED]`
11. `tests/c15_persistence/test_corrective_002_remote_durability.py::test_k1_k5_survive_total_local_cache_loss_from_remote_only[K5_AFTER_APPLIED_BEFORE_ACK]`
12. `tests/c15_persistence/test_corrective_002_remote_durability.py::test_reopen_rejects_deleted_middle_sealed_generation`
13. `tests/c15_persistence/test_corrective_002_remote_durability.py::test_reopen_rejects_modified_sealed_generation_artifact`
14. `tests/c15_persistence/test_corrective_002_remote_durability.py::test_reopen_rejects_incomplete_unsealed_generation`
15. `tests/c15_persistence/test_corrective_003_binding_blockers.py::test_c002_001_c_k4_failure_restart_recovers_from_authoritative_state_once`
16. `tests/c15_persistence/test_corrective_003_binding_blockers.py::test_c002_001_d_ack_barrier_failure_never_acks_the_cursor`
17. `tests/c15_persistence/test_corrective_003_binding_blockers.py::test_c002_002_a_k3_trusted_return_first_round_remote_only_converges`
18. `tests/c15_persistence/test_corrective_003_binding_blockers.py::test_c002_002_b_k3_trusted_return_later_round_remote_only_converges`
19. `tests/c15_persistence/test_corrective_003_binding_blockers.py::test_c002_002_d_k5_push_success_then_total_local_loss_acks_once`
20. `tests/c15_persistence/test_corrective_003_binding_blockers.py::test_c002_002_e_k5_prepush_crash_recovers_from_prior_authoritative_barrier`
21. `tests/c15_persistence/test_corrective_003_binding_blockers.py::test_c002_002_f_changed_trusted_return_bytes_under_same_identity_fail_closed`
22. `tests/c15_persistence/test_corrective_003_binding_blockers.py::test_c002_002_g_changed_relay_journal_reply_bytes_fail_closed`
23. `tests/c15_persistence/test_corrective_003_binding_blockers.py::test_c002_004_a_valid_remote_authoritative_binding_is_durable`
24. `tests/c15_persistence/test_corrective_003_binding_blockers.py::test_c002_004_b_binding_damage_fails_closed_never_local_only[missing]`
25. `tests/c15_persistence/test_corrective_003_binding_blockers.py::test_c002_004_b_binding_damage_fails_closed_never_local_only[truncated]`
26. `tests/c15_persistence/test_corrective_003_binding_blockers.py::test_c002_004_b_binding_damage_fails_closed_never_local_only[malformed-json]`
27. `tests/c15_persistence/test_corrective_003_binding_blockers.py::test_c002_004_b_binding_damage_fails_closed_never_local_only[extra-field]`
28. `tests/c15_persistence/test_corrective_003_binding_blockers.py::test_c002_004_b_binding_damage_fails_closed_never_local_only[missing-field]`
29. `tests/c15_persistence/test_corrective_003_binding_blockers.py::test_c002_004_b_binding_damage_fails_closed_never_local_only[unreadable]`
30. `tests/c15_persistence/test_corrective_003_binding_blockers.py::test_c002_004_b_binding_damage_fails_closed_never_local_only[wrong-run]`
31. `tests/c15_persistence/test_corrective_003_binding_blockers.py::test_c002_004_b_binding_damage_fails_closed_never_local_only[wrong-session]`
32. `tests/c15_persistence/test_corrective_003_binding_blockers.py::test_c002_004_b_binding_damage_fails_closed_never_local_only[non-canonical-ref]`
33. `tests/c15_persistence/test_corrective_003_binding_blockers.py::test_c002_004_k_unavailable_remote_state_fails_closed`
34. `tests/c15_persistence/test_corrective_003_binding_blockers.py::test_c002_004_l_local_only_run_cannot_be_silently_promoted`
35. `tests/c15_persistence/test_corrective_003_regressions.py::test_generation_admission_rejects_seal_content_tamper`
36. `tests/c15_persistence/test_corrective_003_regressions.py::test_generation_admission_rejects_unexpected_artifact`
37. `tests/c15_persistence/test_corrective_003_regressions.py::test_generation_history_cannot_be_shortened_by_lowering_current_ledger`
38. `tests/c15_persistence/test_corrective_003_regressions.py::test_remote_authority_rejects_coordinated_short_history_even_if_local_head_is_rehashed`
39. `tests/c15_persistence/test_environment_reattach.py::test_environment_detach_and_reattach`
40. `tests/c15_persistence/test_environment_reattach.py::test_remote_backend_roundtrip_with_wiped_local_cache`
41. `tests/c15_persistence/test_environment_reattach.py::test_remote_backend_rejects_corrupted_manifest`
42. `tests/c15_persistence/test_operator_wiring.py::test_interrupted_transaction_rolls_back`
43. `tests/c15_persistence/test_operator_wiring.py::test_real_operator_integration_path_reaches_ack`
44. `tests/c15_persistence/test_operator_wiring.py::test_core_receipt_revalidation_rejects_an_operator_invented_receipt`
45. `tests/c15_persistence/test_operator_wiring.py::test_sealed_generations_are_immutable_and_reverify`
46. `tests/c15_persistence/test_resident_surface.py::test_resident_visible_surface_is_unchanged_by_the_durability_layer`
