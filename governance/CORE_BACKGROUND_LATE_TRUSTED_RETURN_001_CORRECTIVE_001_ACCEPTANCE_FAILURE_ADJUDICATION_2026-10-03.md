# CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-001 — Acceptance-Failure PM Adjudication (WINDOW 18)

- **Date:** 2026-10-03
- **Window:** WINDOW 18
- **Formal task:** `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-001-ACCEPTANCE-FAILURE-PM-ADJUDICATION`
- **Role:** Core Governance PM / Acceptance-Failure Adjudicator
- **Merge policy:** `GOVERNANCE_ONLY_AT_END`
- **Repository:** `Haneof/Haneof-AIOS-Core-v3.0`

## 1. Fresh ground truth

WINDOW 18 independently re-fetched the repository before adjudication.

- live `main`: `0b883c71d91e5f0772334514925237f1570fa780`
- PR #308: `OPEN / UNMERGED / DO NOT MERGE`
- PR #308 branch: `core-background-late-trusted-return-corrective-001-window16`
- failed exact candidate: `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd`
- candidate parent: `293d32c683033ba27c11059fd021e68342a82c77`
- candidate tree: `a762df979826d3a599b93d937c53b633d0cb8466`
- construction base: `0b883c71d91e5f0772334514925237f1570fa780`
- canonical Window 17 review: `e4161dd0ad0a2f825461311a1c8c5ff8234a07f8`
- canonical review sole parent: exact candidate `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd`
- canonical review tree: `30ba1a1d74561abb5db13f4ece587836bbc48df2`
- canonical review branch: `arena/01a0fd4d-haneof-aios-core-v3-0` (`REVIEW_ONLY / DO NOT MERGE`)
- Window 17 formal IA comment on PR #308: `5956828439`
- Window 16 final engineering handoff comment: `5955781379`

No candidate drift, main drift, or review-parent mismatch was observed at adjudication start.

## 2. Adjudicated verdict

`CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-001 = DONE / ACCEPTANCE_FAIL / blocker=3`

Disposition: `CORRECTIVE_REQUIRED`.

All three Window 17 blockers are **BINDING**. None is downgraded to observation, hardening, test-only issue, or documentation issue. The author-owned green CI and the substantial positive properties independently reproduced by Window 17 remain useful evidence, but they do not override a trust-minting oracle, unsafe authenticity migration, or verifier encoding/validation defect.

PR #308 exact candidate `cb8a6b3c...` is permanently frozen as:

`FAILED_EXACT_CANDIDATE / FROZEN / OPEN / UNMERGED / DO_NOT_MERGE`

No corrective commit may be appended to PR #308. No force-push, rebase, squash, amend, or history rewrite is authorized.

The Window 17 review commit `e4161dd0...` and branch `arena/01a0fd4d-haneof-aios-core-v3-0` are permanently:

`REVIEW_ONLY / IMMUTABLE / DO_NOT_MERGE`

## 3. Blocker rulings

### 3.1 BLK-W17-001 — BINDING

`RECOVERY_TRUSTED_RECEIPT_AND_HANDOFF_MINTING_ORACLE_VIA_CAPTURE_HELPER`

**PM ruling:** BINDING / Core trust-boundary defect / curable only in a new corrective candidate.

Fresh source inspection confirms the essential mechanism:

- `_receipt_proof(...)` is a keyless SHA-256 integrity fingerprint.
- `_capture_trusted_response_return(...)` accepts post-dispatch states including `dispatching` and `in_doubt`, computes that public fingerprint, and writes durable trusted receipt + exact handoff rows.
- the helper is reachable through ordinary recovery objects at `runtime.background_model_attempts`.
- it does not require the external RSA proof bound in `background_model_return_verifiers`.
- therefore Python underscore naming and intended call-site provenance remain the only effective boundary for this path.

This directly violates the already-frozen rule that ordinary recovery callers may verify trust but must not mint trusted response state. It also defeats verifier-less fail-closed semantics because a caller can manufacture the trusted receipt/handoff through the recovery object graph.

**Root cause:** `TRUSTED_LIVE_RETURN_MINTING_AUTHORITY_REMAINS_RECOVERY_REACHABLE`.

Corrective-002 must make trusted receipt/handoff creation structurally require evidence unavailable to a post-crash recovery caller. Acceptable designs may use either:

1. the same externally verifiable proof path used for late return; or
2. a genuinely ephemeral in-flight trust capability that exists only in the currently executing trusted provider-return call stack, is never stored/reconstructible/retrievable through runtime/store recovery objects, and is invalid after process death.

Private method naming, call convention, or a keyless checksum is not an authorization boundary.

### 3.2 BLK-W17-002 — BINDING

`RECEIPT_AUTHENTICITY_DOWNGRADE_TO_PUBLIC_CHECKSUM_AND_UNVERIFIED_LEGACY_MIGRATION_LAUNDERING`

**PM ruling:** BINDING / Core authenticity + migration defect / curable in the same new corrective.

Fresh source inspection confirms that the legacy-authority migration:

- reads legacy receipt rows;
- computes a new keyless `bgresponse_v2_<sha256>` value over row fields;
- rewrites receipt/handoff/response proofs;
- then deletes the old HMAC authority;
- but does not first authenticate the legacy receipt with the old HMAC secret and does not first prove exact cross-table payload/proof consistency.

That permits invalid legacy material to be normalized into candidate-trusted state.

**Root cause:** `UNAUTHENTICATED_TRUST_STATE_MIGRATION`.

Corrective-002 must:

- authenticate every legacy `bgresponse_v1` receipt with the legacy HMAC authority before any conversion;
- verify exact cross-table binding among receipt, handoff, staged response, payload digest, provider/model/request identity, attempt, round, outbound binding, and relay;
- fail closed atomically on any mismatch, missing row, malformed proof, or corrupted payload;
- perform no partial trust rewrite and no secret purge on failed verification;
- after successful migration, distinguish integrity checksums from authenticity evidence; a public digest must never by itself authorize creation of new trusted state;
- preserve valid legacy recovery exactly once without permitting forged/tampered legacy rows to be laundered.

### 3.3 BLK-W17-003 — BINDING

`RSA_VERIFIER_KEY_ID_COLON_DELIMITER_AMBIGUITY_AND_NEGATIVE_MODULUS_ACCEPTANCE`

**PM ruling:** BINDING / Core verifier encoding-validation defect / curable in the same new corrective.

Fresh source inspection confirms:

- `LateReturnVerifier.key_id` accepts arbitrary non-empty strings;
- proof parsing uses `encoded.split(":", 1)`;
- therefore a verifier whose key id itself contains `:` can be durably accepted but its legitimate proof cannot be parsed as the same key id;
- modulus parsing checks bit length but not positivity, so negative large-magnitude values can pass construction and can never verify a legitimate signature.

This violates the T5 requirement that a legitimately bound external authority can return after restart and be verified reliably.

Corrective-002 must choose and freeze a canonical proof encoding. Either reject delimiter-bearing/non-canonical key ids at verifier construction or adopt an unambiguous structured/length-prefixed encoding. It must also enforce canonical positive RSA parameters at construction, including a positive odd modulus of the required minimum strength and a valid positive odd public exponent, and add boundary/adversarial cases.

## 4. Positive properties that must not regress

Window 17 independently found several Corrective-001 properties working. Corrective-002 must preserve them while fixing the three blockers:

- C4/C5 Route-B truthfulness: no post-binding `not_submitted`, no second outbound identity.
- verifier substitution attempts fail closed.
- no RSA private key/signing secret is present in normal Core DB/WAL/dump/backup surfaces.
- generic malformed RSA signatures and cross-field transplants fail closed.
- concurrent valid-proof race preserves one canonical winner.
- exact response / replay / metering / semantic-effect exactly-once behavior remains intact.
- real process-loss / fresh-process recovery remains supported when a genuine trusted external authority returns.
- verifier-less / anonymous recovery remains fail closed.
- Window 14 historical failed candidates/reviews and Window 17 review evidence remain immutable.

## 5. Unique next READY — WINDOW 19

The only next READY task is:

`CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-002`

WINDOW 19 must use a **brand-new engineering branch + brand-new PR from fresh live main**. It must not append commits to PR #308.

### 5.1 Frozen Corrective-002 scope

1. **C2-1 — No recovery-reachable trust-mint API.** Direct invocation of every runtime/store object reachable after restart must be unable to create trusted receipt/handoff state without a valid external proof or non-recoverable live-call capability.
2. **C2-2 — Live-return authority separation.** If a live in-process provider return uses a non-RSA fast path, its authorization must be ephemeral, call-stack scoped, non-serializable, non-persisted, non-reissuable, and absent from recovery object graphs after death.
3. **C2-3 — Integrity is not authenticity.** Public SHA/checksum values may detect corruption but may never serve as the sole authority for minting trusted state.
4. **C2-4 — Legacy HMAC migration is verify-before-convert.** Invalid/tampered/cross-table-inconsistent legacy rows fail closed with zero laundering and zero partial rewrite.
5. **C2-5 — Canonical verifier/proof encoding.** Key-id serialization is unambiguous and round-trips all allowed identifiers; otherwise the allowed key-id grammar must reject ambiguous identifiers at construction.
6. **C2-6 — RSA parameter validation.** Reject negative/zero/even/undersized/non-canonical modulus values and invalid exponents before durable binding.
7. **C2-7 — Preserve Window 16/17 positives.** Keep Route-B `not_submitted` closure, verifier-only secret separation, exact proof binding, race safety, SIGKILL recovery, R1-R5, and exactly-once effects.
8. **C2-8 — RED-first against failed exact candidate.** Source the frozen Window 17 reviewer probes byte-for-byte from canonical review `e4161dd0...`; verify hashes; run them against `cb8a6b3c...` and preserve the real failing results before editing `src/**`.
9. **C2-9 — New reviewer-oriented attack matrix.** Add tests that directly invoke every trust-state write helper through ordinary recovery object graphs, exercise verifier-less attempts, tampered legacy HMAC/cross-table rows, ambiguous key ids, and signed/negative/zero/even/undersized RSA parameter cases.
10. **C2-10 — Scope discipline.** No C15 persistence/operator/Resident evidence mutation; no changes to PR #305, PR #308, Window 14 or Window 17 review branches, PR #302, historical persistence refs, or retired run evidence.

Engineering owns implementation only. It may push/update its new branch/PR but must not merge. It stops at `REVIEW_READY / READY_FOR_FRESH_INDEPENDENT_ACCEPTANCE`.

## 6. Mandatory sequence after Window 18

1. WINDOW 19 — `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-002`
2. WINDOW 20 — Fresh Independent Acceptance of the exact Corrective-002 candidate
3. WINDOW 21 — PM Integration Receipt only if Window 20 returns `ACCEPTANCE_PASS / blocker=0`
4. then `CORE-RC-REFREEZE-004` + Fresh IA
5. then fresh `C15-RCC-RES-A-RERUN-005` + Fresh IA
6. then `C15-RCC-RES-B-OPERATOR-PROVENANCE-CORRECTIVE-001` + Fresh IA
7. then `C15-RCC-RES-B-RELEASE-004`
8. then `C15-RCC-RES-B-RERUN-004`
9. then `C15-RCC-RES-B-ACCEPT-004`

All downstream C15 release/Resident/evaluator/close work remains BLOCKED until its upstream dependency is accepted and integrated.

## 7. Window 18 writeback policy

WINDOW 18 is governance-only. It may change only:

- this adjudication record;
- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`;
- `AIOS_v3.0_CURRENT_CHECKPOINT.md`;
- PR #308 title/comment metadata needed to freeze the failed candidate.

No `src/**`, `tests/**`, `tools/**`, Resident evidence, review evidence, or persistence refs may change.

After the governance PR is green and merged, Window 18 must post the formal adjudication comment on PR #308, mark the candidate frozen, and close. It must not start Window 19 engineering in the same window.
