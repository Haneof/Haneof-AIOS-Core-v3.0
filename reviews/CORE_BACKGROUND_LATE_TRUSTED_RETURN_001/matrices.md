# CORE-BACKGROUND-LATE-TRUSTED-RETURN-001 — behaviour matrices

All rows are mechanically asserted by the probe suites. Counts are from the local
author-candidate run; the formal CPython 3.12.14 gate is in `green_ci_formal_31214.txt`.

---

## 1. Late trusted return matrix (LTR)

| # | Probe | Scenario | Baseline `main` | Candidate | Result class |
|---|---|---|---|---|---|
| R0 | `test_ltr_r0_absent_authorized_observer_keeps_the_late_return_permanently_unattachable` | dispatch crossed, process dead, **no** registered observer | RED (false `not_submitted` was writable) | terminal dead end: `in_doubt`, no receipt, no staging, metadata reconciliation still disabled, meters 0 | fail closed |
| R1a | `test_ltr_r1_late_trusted_return_while_dispatch_is_still_durable` | proof minted after death, attached while `dispatching` | absent | same attempt, same request, no redispatch, exactly 1 meter, response applied once, later `TurnAlreadyCompleted` | converged |
| R1b | `test_ltr_r1_late_trusted_return_after_restart_admission_raised_in_doubt` | restart admission raises first, then the proof arrives | absent | `dispatching → in_doubt` then attach → converged, exactly once | converged |
| R1c | `test_ltr_r1_capability_is_single_use_and_consumed` | capability consumption | absent | `consumed_at` set in the same transaction as the receipt | single use |
| R1d | `test_ltr_r1_real_sigkill_then_late_trusted_return_converges_exactly_once` | **real `SIGKILL`** at the dispatch await in a child process, capability delivered to the surviving observer over a synchronous pipe, proof minted after the kill | child died before dispatch (`exit=1`) | attach → converged, 1 meter, `TurnAlreadyCompleted` after | converged |
| R2 | `test_ltr_r2_forged_late_response_and_caller_made_proof_fail_closed` | forged bytes + caller-invented / empty / wrong-namespace proofs | absent | refused ×4, no receipt, no staging, meters 0 | fail closed |
| R2b | `test_ltr_r2_real_proof_over_caller_substituted_bytes_fails_closed` | **genuine** proof over substituted bytes | absent | refused | fail closed |
| R3 | `test_ltr_r3_correct_bytes_without_a_trusted_proof_fail_closed` (8 params) | correct bytes, proof `None`/empty/blank/wrong length/non-string | absent | refused ×8 | fail closed |
| R3b | `test_ltr_r3_pre_dispatch_attempt_has_no_return_capability_at_all` | no dispatch boundary crossed | refused by the existing accepted guard | refused; no capability row exists | fail closed |
| R4a | `test_ltr_r4_proof_from_another_attempt_cannot_be_transplanted` | proof from attempt B into attempt A | absent | refused; the genuine owner can still use it on its own attempt | fail closed |
| R4b | `test_ltr_r4_proof_cannot_be_transplanted_to_another_subject_or_work` | another subject | absent | refused; target stays `admitted` | fail closed |
| R4c | `test_ltr_r4_proof_cannot_be_transplanted_to_another_round` | another round **and** another outbound request | absent | refused; stays `dispatching` | fail closed |
| R4d | `test_ltr_r4_durable_binding_tampering_invalidates_the_proof` | the durable originating request rewritten underneath | absent | refused; no staging | fail closed |
| R5 | `test_ltr_r5_changed_response_under_the_same_proof_fails_closed` | response / model / request id / provider changed under one proof | absent | refused ×4 | fail closed |
| R6a | `test_ltr_r6_consumed_proof_replay_is_deterministic_exact_recovery` | replay a consumed proof with identical bytes | absent | identical staging returned, state unchanged, 1 meter, no duplicate effect | deterministic exact recovery |
| R6b | `test_ltr_r6_consumed_proof_replay_with_different_bytes_fails_closed` | replay a consumed proof with different bytes | absent | refused; state stays `metered`; meters unchanged | fail closed |
| R7 | `test_ltr_r7_anonymous_handler_gets_no_capability_and_no_attach` | no observer registered | 0 capability rows | 0 capability rows; attach refused | fail closed |
| R8 | `test_ltr_r8_anonymous_external_return_can_never_mint_a_late_proof` | registered observer but the return is anonymous | absent | `ValueError` at the boundary; capability stays `issued` | fail closed |
| R9 | `test_ltr_r9_leaked_capability_cannot_mint_a_proof_for_another_attempt` | capability leaked, reused outside its scope | absent | the leak still works for its own exact scope, and is refused for any other attempt | narrowly contained |
| R10 | `test_ltr_r10_no_public_surface_converts_arbitrary_bytes_into_a_trusted_return` | source-level oracle audit | absent | no signing-shaped surface; the only bytes→trusted path is the proof-gated attach | no oracle |
| R10b | `test_ltr_r10_the_only_proof_minting_surface_needs_the_capability_object` | proof minting API shape | absent | `prove_external_return(self, directive)`; the nonce is not a model field | no oracle |

---

## 2. Non-submission transition matrix (NS)

| # | Probe | From state | Call | Baseline `main` | Candidate | Result class |
|---|---|---|---|---|---|---|
| NS-R1a | `test_ns_r1_pre_dispatch_admitted_attempt_may_be_reconciled_and_retried` | `admitted`, no binding | `reconcile_not_submitted` | refused (could not reach this state) | `not_submitted` → `safe_to_retry` → re-admit → dispatch; the **same** call is then refused | legal retry preserved, then permanently closed |
| NS-R1b | `test_ns_r1_in_process_definitely_not_submitted_dispatch_failure_still_retries` | typed in-process `ModelDispatchNotSubmitted` | `mark_failure(definitely_not_submitted=True)` | `not_submitted` | `not_submitted`, `safe_to_retry` | accepted in-process contract preserved |
| NS-R2a | `test_ns_r2_post_dispatch_reconcile_not_submitted_is_mechanically_refused[dispatching]` | `dispatching` | `reconcile_not_submitted` | **wrote the false state** | `BackgroundModelResponseConflict`, state and `reconciliation_evidence` unchanged | fail closed |
| NS-R2b | `…[in_doubt]` | `in_doubt` | `reconcile_not_submitted` | **wrote the false state** | `BackgroundModelResponseConflict`, unchanged | fail closed |
| NS-R2c | `test_ns_r2_false_state_cannot_be_written_even_with_a_verbose_justification` | `dispatching` | 6 different justifications incl. 4000 chars | **wrote the false state** | refused ×6 | fail closed |
| NS-R3 | `test_ns_r3_missing_receipt_alone_never_justifies_not_submitted` | `dispatching`, no receipt | `reconcile_not_submitted` | **wrote the false state** | refused | fail closed |
| NS-R4 | `test_ns_r4_uncertain_dispatch_fails_closed_instead_of_recovering` | `in_doubt` | ordinary retry ×3 | `TurnExecutionInDoubt` ×3 | `TurnExecutionInDoubt` ×3, 0 meters, no staging | fail closed |
| NS-R5a | `test_ns_r5_caller_forged_non_submission_assertion_fails_closed` | `dispatching` | `evidence` = `None`/`""`/`"   "`/`42`/`[]`/`{}`/proof-shaped | mixed | all refused | fail closed |
| NS-R5b | `test_ns_r5_runtime_level_turn_reconciliation_is_refused_after_dispatch` | `dispatching` | `reconcile_turn_model_not_submitted` (public runtime surface) | **wrote the false state** | refused | fail closed |
| NS-R6 | `test_ns_r6_legitimate_late_return_proof_uses_attach_not_reconciliation` | `in_doubt` + genuine proof | `reconcile_not_submitted`, then attach | absent | reconciliation still refused; attach succeeds; 1 meter | attach, not reconciliation |
| NS-R7a | `test_ns_r7_receipt_absence_guard_still_protects_a_real_authenticated_return` | `dispatching` + real receipt | `reconcile_not_submitted` | refused | refused (accepted guard retained) | fail closed |
| NS-R7b | `test_ns_r7_metadata_only_reconciliation_stays_disabled` | `dispatching`, `in_doubt` | `reconcile_response` | refused | refused | permanently disabled |

### Legal routes to `not_submitted` after this change

| route | status | why |
|---|---|---|
| `mark_failure(definitely_not_submitted=True)` from a typed in-process `ModelDispatchNotSubmitted` | **kept** | Core's own configured handler raises it synchronously at the dispatch site while the process is alive; accepted FIX-002/CG003 semantic, frozen by existing tests |
| `reconcile_not_submitted` on a pre-dispatch `admitted` attempt with no binding row | **kept** | Core mechanically knows the outbound request was never published |
| `reconcile_not_submitted` on `dispatching` / `in_doubt` | **retired** | the durable originating-request binding proves the crossing; the transition is now mechanically impossible |

---

## 3. Authenticity / adversarial attack matrix

All rows in `test_a3_every_attack_fails_closed` plus the A1–A4 probes.

| attack | result |
|---|---|
| caller-supplied correct bytes + self-made proof (`bglate_v1_` + zeros / ones) | FAIL CLOSED |
| caller-supplied forged bytes + self-made proof | FAIL CLOSED |
| valid proof, wrong attempt | FAIL CLOSED |
| valid proof, wrong work id | FAIL CLOSED |
| valid proof, wrong subject | FAIL CLOSED |
| valid proof, wrong round | FAIL CLOSED |
| valid proof, wrong originating request (binding tampered) | FAIL CLOSED |
| valid proof, changed response | FAIL CLOSED |
| valid proof replay after the round completed | FAIL CLOSED, no second effect |
| corrupted proof (last hex digit flipped) | FAIL CLOSED |
| truncated proof | FAIL CLOSED |
| payload with duplicate top-level JSON key | FAIL CLOSED (strict decoder) |
| payload with duplicate nested key (ambiguous provider) | FAIL CLOSED (strict decoder) |
| old historical receipt transplant (`bgresponse_v1_…`) | FAIL CLOSED |
| late proof for an already-completed stronger terminal receipt | FAIL CLOSED; turn stays completed, 1 meter, no re-entry into the model path |
| post-dispatch false non-submission assertion | FAIL CLOSED |
| proof computed with a guessed / random / wrong nonce over fully correct, self-computable binding fields (4 nonces × 2 prefixes) | FAIL CLOSED |
| recovery caller calling `issue_external_return_capability` | `AttributeError` — the issuer is private |
| recovery caller enumerating the public store surface for a nonce | no member accepts or returns `capability_nonce` |
| anonymous handler bytes with a made-up proof | FAIL CLOSED |

---

## 4. Regression matrix

| suite | count | result |
|---|---|---|
| new late-trusted-return + not-submitted + adversarial | 61 | 61 PASS |
| accepted trusted-return / background-response / gap-fix / runtime regression | 249 | 249 PASS |
| **full Core suite** | **1059** | **1059 PASS**, 0 fail, 0 error, 0 skip |

Baseline `main` for comparison: **997 PASS**. Delta = `+61` new probes, `+1` from
splitting one accepted test into two, with **no** previously passing test lost.

### Historical R1–R5 replay families explicitly re-proved (rule 21)

| family | suite | result |
|---|---|---|
| `propose_goal` (transition goal) | `test_core_background_trusted_return_corrective_001_process_loss.py::test_process_sigkill_after_transition_goal_replays_exactly_once` | PASS |
| `form_event` | `…::test_process_sigkill_after_form_event_replays_exactly_once` | PASS |
| `revise_claim` | `…::test_process_sigkill_after_revise_claim_replays_exactly_once` | PASS |
| `propose_entity` / `propose_dimension` / `propose_cognitive_policy` | `test_core_background_trusted_return_corrective_001_capability_replay.py` (whole file) | PASS |
| R5-A/B/C/D durable identity and conflict | `test_core_background_trusted_return_r5_001.py` + `…_r5_conflicts_001.py` | PASS |
