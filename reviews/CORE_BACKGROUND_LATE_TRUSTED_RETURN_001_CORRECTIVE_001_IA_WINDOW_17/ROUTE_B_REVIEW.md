# Route-B & S3 Clarification Review (`ROUTE_B_REVIEW.md`)

- **Reviewed Exact Candidate:** `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd` (`PR #308`)
- **Binding Governance Reference:** `PR #307` (`0b883c71d91e5f0772334514925237f1570fa780`), `governance/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_ACCEPTANCE_FAILURE_ADJUDICATION_2026-10-01.md` §10.

## 1. Original Window 14 S3 (`window14_s3_stale_capability_rotation.py`)

- Freshly verified SHA-256: `7c548aca54e22520417adc2841f21093995ded9c311b40915b9d7fc77297b39f`.
- Freshly reproduced on failed candidate `5ad0524c425592210ff184e00ad52abb2c14e366`: `SUMMARY | failures= 2` (`HISTORICAL RED`, preserved in `raw/historical_w14_red_on_5ad0524c.txt`).
- Per PR #307 binding ruling, original S3 remains immutable historical RED evidence for `5ad0524c425592210ff184e00ad52abb2c14e366` and is not rewritten.

## 2. Corrective Route-B & Genuine Pre-Submission Retry (`IA17-NS-ROUTE-B-001` = `PASS`)

Reviewer probe `IA17-NS-ROUTE-B-001` independently verified on `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd`:
1. **Post-binding `not_submitted` refusal:** After `mark_dispatching` commits a durable binding and verifier, `mark_failure(definitely_not_submitted=True)` (with both `ModelDispatchNotSubmitted` and `RuntimeError`), `reconcile_not_submitted`, and `FusedTurnRuntime.reconcile_turn_model_not_submitted` all raise `BackgroundModelResponseConflict`, transition the attempt to `in_doubt`, refuse retry (`admit` / `mark_dispatching`), and prevent any second request identity or stale verifier rotation.
2. **Genuine pre-submission retry (`state == 'admitted'`, zero binding/verifier/receipt rows):** Pre-submission `mark_failure(definitely_not_submitted=True)` transitions `admitted -> not_submitted`; subsequent `admit` retries the same `attempt_id`, first real `mark_dispatching` binds the first and only `outbound_request_fingerprint` + `LateReturnVerifier`, and after simulated process loss the genuine external RSA-signed return attaches and completes the turn once.
