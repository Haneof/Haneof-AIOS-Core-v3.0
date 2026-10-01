# CORE-BACKGROUND-LATE-TRUSTED-RETURN-001 — Acceptance-Failure PM Adjudication (`WINDOW 15`)

- **Document ID:** `CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_ACCEPTANCE_FAILURE_ADJUDICATION_2026-10-01`
- **Date:** `2026-10-01`
- **Window:** `WINDOW 15` (`CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-ACCEPTANCE-FAILURE-PM-ADJUDICATION`)
- **Role:** Core Governance PM / Acceptance-Failure Adjudicator (`GOVERNANCE_ONLY`)
- **Adjudicated Task:** `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001` (`WINDOW 13` implementation / `WINDOW 14` Fresh Independent Acceptance)
- **Adjudicated Verdict:** `DONE` (`ACCEPTANCE_FAIL / blocker=4`, `CORRECTIVE_REQUIRED`)
- **Failed Exact Candidate Commit:** `5ad0524c425592210ff184e00ad52abb2c14e366` (`PR #305`, head branch `arena/01a0f07b-haneof-aios-core-v3-0`) — `FAILED_EXACT_CANDIDATE / FROZEN / OPEN / UNMERGED / DO_NOT_MERGE`
- **Canonical Window 14 Review Commit:** `84457badc562416f59fb25ca41103700276e0df2` (branch `arena/01a0f231-haneof-aios-core-v3-0`, formal IA comment `5924642667` on `PR #305`) — `REVIEW_ONLY / IMMUTABLE / DO_NOT_MERGE`
- **Original Local-Only Object:** `1c0510cfe989e832f46aa1e2e070134048440e27` — `LOST_LOCAL_OBJECT / NEVER_REMOTE_DURABLE / NON_AUTHORITATIVE`
- **Unique Next `READY` Task:** `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-001` (`WINDOW 16`, new engineering branch + new PR)

---

## 1. Fresh Ground Truth Verification

All git/GitHub ground truth objects were freshly verified in `WINDOW 15` with zero drift:

| Ground Truth Item | Verified Value | Verification Status |
|---|---|---|
| `live main` | `25591825d88e98f30dfd3de1c7e7cbc6e53267dd` | Verified (`origin/main` exact match) |
| `PR #305` state | `OPEN`, `merged: false`, `mergeCommit: null` | Verified (`FROZEN_FAILED_CANDIDATE / DO_NOT_MERGE`) |
| `PR #305` title | `[IA_FAIL / blocker=4 / DO NOT MERGE] CORE-BACKGROUND-LATE-TRUSTED-RETURN-001 — PM adjudication required` | Verified |
| `PR #305` head branch | `arena/01a0f07b-haneof-aios-core-v3-0` | Verified |
| `PR #305` candidate SHA | `5ad0524c425592210ff184e00ad52abb2c14e366` | Verified |
| Candidate parent SHA | `a49c1e6874ecb92ae4dc4783d07d733fdc19fa5d` | Verified (`git cat-file -p 5ad0524c...`) |
| Candidate tree SHA | `53064b3022254dab33c7793a0a6306c71e3df2b2` | Verified (`git cat-file -p 5ad0524c...`) |
| Construction base (`merge-base` with `main`) | `25591825d88e98f30dfd3de1c7e7cbc6e53267dd` | Verified (`git merge-base origin/main 5ad0524c...`) |
| Canonical Window 14 review SHA | `84457badc562416f59fb25ca41103700276e0df2` | Verified |
| Canonical review sole parent SHA | `5ad0524c425592210ff184e00ad52abb2c14e366` | Verified (`git cat-file -p 84457bad...`) |
| Canonical review tree SHA | `bd235452c0b78a7fbeedd48d048fc78b331d92bf` | Verified (`git cat-file -p 84457bad...`) |
| Canonical review branch | `arena/01a0f231-haneof-aios-core-v3-0` | Verified |
| Formal IA comment on `PR #305` | `5924642667` (`https://github.com/Haneof/Haneof-AIOS-Core-v3.0/pull/305#issuecomment-5924642667`) | Verified |
| Exact-head formal GitHub Actions run on `5ad0524c...` | Run `36680355119` / check run `109774221264` (`core-background-late-trusted-return-001`, `SUCCESS`) | Verified |
| Original local-only object | `1c0510cfe989e832f46aa1e2e070134048440e27` | Verified (`LOST_LOCAL_OBJECT / NEVER_REMOTE_DURABLE / NON_AUTHORITATIVE`) |

---

## 2. Verbatim Preservation of Window 14 Fresh IA Verdict

The Window 14 Fresh Independent Acceptance verdict published at commit `84457badc562416f59fb25ca41103700276e0df2` (`reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_IA_WINDOW_14/IA_REPORT.md` and PR #305 comment `5924642667`) is preserved verbatim:

- **Task Verdict:** `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001 = ACCEPTANCE_FAIL / blocker=4`
- **Required Disposition:** `CORRECTIVE_REQUIRED`
- **Four Formal Binding Blockers:**
  1. `BLK-W14-001`: `SIGNING_ORACLE_VIA_RECOVERY_CAPABILITY_REISSUANCE` (`CRITICAL`)
  2. `BLK-W14-002`: `CAPABILITY_NONCE_RECOVERY_SURFACE_LEAK` (`CRITICAL`)
  3. `BLK-W14-003`: `POST_DISPATCH_FALSE_NOT_SUBMITTED_VIA_MARK_FAILURE` (`HIGH`)
  4. `BLK-W14-004`: `STALE_CAPABILITY_AFTER_LEGAL_RETRY_BINDING_ROTATION` (`MEDIUM-HIGH`)

**Governance Invariant:** Mechanical regression green (`1,059 passed, 0 failed, 0 skipped` on candidate run `36680355119` and reproduced by Window 14) **never** offsets, dilutes, or overrides security boundary or state-machine truthfulness blockers. None of `BLK-W14-001` through `BLK-W14-004` may be downgraded to observations, non-blocking hardening notes, or "overly strict test expectations".

---

## 3. Historical Lifecycle Precedent & Candidate Disposition Pattern

This adjudication follows the established AIOS Core governance precedent from `CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001` (`governance/CORE_BACKGROUND_TRUSTED_RETURN_RECOVERY_001_IA_FAILURE_ADJUDICATION_2026-09-28.md` and `governance/CORE_BACKGROUND_TRUSTED_RETURN_RECOVERY_001_CORRECTIVE_001_INTEGRATION_RECEIPT_2026-09-28.md`):

- **Historical Precedent:** Failed candidate PR `#258` (`IA_FAIL / blocker=3`) -> PM failure adjudication PR `#262` (`GOVERNANCE_ONLY`) -> Corrective-001 implementation on a **new branch and new PR `#264`** -> Fresh Independent Acceptance -> PM integration receipt.
- **Applied Disposition for `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001`:**
  1. `PR #305` (`5ad0524c425592210ff184e00ad52abb2c14e366`, branch `arena/01a0f07b-haneof-aios-core-v3-0`) is permanently frozen as `FAILED_EXACT_CANDIDATE / FROZEN / OPEN / UNMERGED / DO_NOT_MERGE`.
  2. Corrective work **must not** be appended onto `PR #305` or branch `arena/01a0f07b-haneof-aios-core-v3-0` (which would turn `5ad0524c425592210ff184e00ad52abb2c14e366` into a non-head intermediate commit and obscure the failed candidate anchor).
  3. `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-001` (`WINDOW 16`) must execute on a **new engineering branch** branched from updated `main` and open a **new PR**.

---

## 4. Technical Adjudication of the Four Formal Blockers

### 4.1 `BLK-W14-001` — `SIGNING_ORACLE_VIA_RECOVERY_CAPABILITY_REISSUANCE` (`BINDING`)

- **Verified Source Facts (`5ad0524c425592210ff184e00ad52abb2c14e366`):**
  - `BackgroundModelAttemptStore._issue_external_return_capability(...)` (`src/aios_core/runtime/background_attempt.py:1570-1705`) resides directly on the ordinary recovery-reachable `BackgroundModelAttemptStore` instance exposed at `FusedTurnRuntime.background_model_attempts` (`src/aios_core/runtime/turn_runtime.py:249,1318`).
  - The method accepts `attempt.state in {"dispatching", "in_doubt"}` (`background_attempt.py:1633`).
  - When a row already exists in `background_model_return_capabilities`, lines `1654-1667` return `self._capability_from_row(existing)`, which reconstructs `LateTrustedReturnCapability` carrying the raw proof-minting `_capability_nonce`.
  - When no row exists (for example, when a turn crashed in `dispatching` with **no** `external_return_observer` registered at dispatch time), calling `_issue_external_return_capability` on the `in_doubt` attempt mints a brand-new capability row and raw `_capability_nonce` post-hoc (`lines 1669-1704`).
  - Window 14 independent probe `IA14-ORACLE-001` (`reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_IA_WINDOW_14/reviewer_probes/window14_independent_attack.py`, SHA-256 `969112b3a13566e30d7cbd4af4e2ecc3299a1cdd9f0f1a62419ef5688d46f181`) proved mechanically that a fresh post-crash recovery process with zero out-of-band state can call `runtime.background_model_attempts._issue_external_return_capability(...)`, call `.issue_proof(...)` on arbitrary attacker-chosen directive bytes, and pass `runtime.attach_late_background_return(...)` to complete the turn (`state == 'metered'`, `1` meter entry, `1` assistant output).
- **PM Constitutional Question & Answer:**
  - *Question:* Does this violate the Window 12 frozen requirement that `"a recovery caller must not obtain signing/minting authority"` (`C3 — Unforgeability / Non-Replay / Binding Invariants`)?
  - *Answer:* **YES.** In Python, a leading underscore (`_issue_external_return_capability`, `_capability_nonce`) is a naming convention only and provides zero runtime access control or cryptographic/privilege isolation. A method on the recovery-facing `BackgroundModelAttemptStore` that accepts `in_doubt` attempts and returns or mints live proof-signing capability is a post-hoc signing oracle.
- **PM Ruling:** **`BLK-W14-001 = BINDING`**. Naming conventions (`_` prefix) are strictly rejected as a security boundary.

---

### 4.2 `BLK-W14-002` — `CAPABILITY_NONCE_RECOVERY_SURFACE_LEAK` (`BINDING`)

- **Verified Source Facts (`5ad0524c425592210ff184e00ad52abb2c14e366`):**
  - `background_model_return_capabilities.capability_nonce` is stored as plaintext hex in the main runtime SQLite database (`src/aios_core/runtime/background_attempt.py:647,1660`).
  - The SQLite path is exposed as the public attribute `SQLiteWorldStore.db_path` (`src/aios_core/storage/sqlite_store.py:183`).
  - `aios_core.runtime.late_return_proof` (`src/aios_core/runtime/late_return.py:131`, re-exported in `src/aios_core/runtime/__init__.py`) is a public function that computes a valid `LateTrustedReturnProof` directly from `capability_nonce` plus caller-computable fields (`attempt_id`, `subject_id`, `work_kind`, `work_id`, `model_round_index`, `outbound_request_fingerprint`, `relay_id`, `provider`, `model`, `provider_request_id`, `response_fingerprint`).
  - Public `attach_late_trusted_return()` / `attach_late_background_return()` verifies the proof against the same plaintext `capability_nonce` column (`background_attempt.py:1750-1778`) and then **mints a Core-owned response receipt and trusted handoff** (`_store_trusted_response_receipt_conn` + `_issue_trusted_return_handoff_conn`, `lines 1806-1848`).
  - Window 14 independent probe `IA14-NONCE-001` proved mechanically that a fresh recovery caller reading `runtime.store.db_path` in read-only mode (`?mode=ro`) can extract `capability_nonce`, call public `late_return_proof(...)` on forged response bytes, and pass public `runtime.attach_late_background_return(...)` without touching any private method or attribute.
- **Threat Model Clarification (Why `BLK-W14-002` Differs Structurally from Legacy `background_model_authenticity_authority.secret_hex`):**
  - The binding threat model for `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001` requires that an ordinary recovery caller holding Core recovery objects and normal runtime durable state must not be able to act as a proof signer for arbitrary late response bytes.
  - Under the symmetric HMAC design in `5ad0524c425592210ff184e00ad52abb2c14e366`, the exact secret required to **mint** a proof (`capability_nonce`) is stored in plaintext inside the same SQLite database that the recovery caller holds to **verify** the proof.
  - Unlike legacy `background_model_authenticity_authority.secret_hex` — where `stage_exact_response` requires a pre-existing row in `background_model_response_receipts` that is only written by in-process callback `_capture_trusted_response_return` (so there is no public `read DB -> public proof helper -> public attach -> Core mints receipt` weaponization chain) — `capability_nonce` is directly weaponizable through the public API chain:
    `read runtime.store.db_path -> public late_return_proof() -> public attach_late_trusted_return() -> Core mints receipt + handoff + completes turn`.
  - Storing raw proof-minting authority in the recovery-readable runtime database therefore violates secret separation between the external return authority (signer/prover) and the Core recovery surface (verifier).
- **PM Ruling:** **`BLK-W14-002 = BINDING`**.

---

### 4.3 Root Cause of `BLK-W14-001` + `BLK-W14-002` & Frozen Security Boundary Constraints (`T1`–`T6`)

- **Frozen Root Cause Classification:** `TRUST_AUTHORITY_COLOCATED_WITH_RECOVERY_CALLER`
- **Core Architectural Principle:**
  Core recovery-side durable state and object graphs may hold **verifier state** (e.g., a one-way cryptographic commitment / token hash `SHA-256(secret_token)`, or a public verification key, scoped to the attempt and outbound request binding), but **must never hold or re-issue the raw signing/proving secret** that allows an ordinary recovery caller to mint a valid late-return proof for arbitrary response bytes.
- **Chain That Corrective-001 Must Eliminate:**
  `ordinary recovery caller + readable Core state + arbitrary response bytes -> accepted trusted return`
- **Frozen Security Boundary Constraints (`T1`–`T6`) for Corrective-001:**
  - **`T1` (Verifier-Only Recovery Surface):** A Core recovery caller and `BackgroundModelAttemptStore` recovery path can **only verify** a late-return proof against durable verifier state.
  - **`T2` (No Recovery Proof Minting):** A Core recovery caller **cannot mint** a valid late-return proof for arbitrary or caller-supplied response bytes.
  - **`T3` (Secret Separation Across All Recovery-Readable Surfaces):** The proof-minting secret / signing authority must not be recoverable from:
    1. the Core recovery-facing object graph (including private/underscore attributes or methods on `FusedTurnRuntime`, `BackgroundModelAttemptStore`, `SQLiteWorldStore`, etc.),
    2. the normal runtime SQLite database (`db_path`, WAL/SHM files, or any table/column stored therein), or
    3. runtime DB backup / export / replica inspection surfaces.
  - **`T4` (No Post-Crash Re-Issuance):** After process death or restart, Core must never re-issue the same signing capability or mint a new signing capability to a recovery caller (`in_doubt` attempts cannot be issued signing capabilities).
  - **`T5` (Legitimate External Return Verification Across Restart):** When a genuinely trusted external return authority received the live capability/signing authority at the dispatch boundary and returns the exact provider response + proof after restart, a fresh Core runtime instance must be able to verify that proof against durable verifier state and complete the turn exactly once.
  - **`T6` (Fail-Closed Without External Authority):** When no genuine external trust authority exists (or when the live capability was lost without an external authority holding the secret), recovery must remain strictly `FAIL_CLOSED` (`in_doubt`).
  - **Explicit Anti-Regression Rule:** It is strictly forbidden to rely on Python `_` private method/attribute naming conventions as a trust boundary.

---

### 4.4 `BLK-W14-003` — `POST_DISPATCH_FALSE_NOT_SUBMITTED_VIA_MARK_FAILURE` (`BINDING`)

- **Verified Source Facts (`5ad0524c425592210ff184e00ad52abb2c14e366`):**
  - This blocker is a direct recurrence of Window 12 `C2` (`not_submitted` Semantics Tightening) on a second durable write-site.
  - While Window 13 tightened `BackgroundModelAttemptStore.reconcile_not_submitted(...)` (`src/aios_core/runtime/background_attempt.py:1202-1284`) to reject `state != 'admitted'` or any attempt with a durable binding/capability/receipt, it left `BackgroundModelAttemptStore.mark_failure(..., definitely_not_submitted=True, error=...)` (`lines 1135-1195`) permitting `state IN ('admitted', 'dispatching')` (`line 1168`) and checking only `_has_trusted_response_receipt_conn` (`line 1152`).
  - Neither `_has_outbound_request_binding_conn(conn, attempt_id)` nor `_has_return_capability_conn(conn, attempt_id)` is checked in `mark_failure`.
  - Furthermore, `mark_failure` does not even inspect the type of `error`: passing `definitely_not_submitted=True, error=RuntimeError("socket timeout")` after `mark_dispatching` has already committed a durable binding and capability row writes `state = 'not_submitted'` and `failure_kind = 'RuntimeError'`.
  - Even on the upper-layer `CognitiveRuntime` / `FusedTurnRuntime` path (`src/aios_core/runtime/cognitive_runtime.py:424-465`, `src/aios_core/runtime/turn_runtime.py:1141-1166`), `_before_model_dispatch` has **already** committed `state = 'dispatching'`, the durable `background_model_request_bindings` row, and the `background_model_return_capabilities` row **before** `model_handler` executes (`turn_runtime.py:1311-1324`). Catching `ModelDispatchNotSubmitted` inside `model_handler` and calling `mark_failure(..., definitely_not_submitted=True)` therefore writes `state = 'not_submitted'` **after** the durable dispatch/binding boundary has already been crossed.
  - Window 14 independent probe `IA14-NS-001` proved mechanically that calling `mark_failure(..., definitely_not_submitted=True, error=RuntimeError(...))` on a post-dispatch attempt with a durable binding and capability transitions the attempt to `not_submitted` and allows a second `run_turn()` to execute a duplicate provider dispatch (`calls == 2`).
- **PM Ruling:** **`BLK-W14-003 = BINDING`**.

---

### 4.5 Frozen `not_submitted` Semantics & PM Ruling on Historical Typed Retry (`ModelDispatchNotSubmitted`)

1. **Frozen `not_submitted` Constitutional Definition:**
   - `not_submitted` means **one thing only**: Core holds mechanical, durable, trustworthy proof that the attempt **never crossed** the semantic/provider dispatch boundary.
   - `not_submitted` **never** means `"the caller or exception handler asserts that submission probably did not happen"`.
   - Corrective-001 must audit **every** write-site capable of producing `state = 'not_submitted'` across the entire codebase — including `reconcile_not_submitted`, `mark_failure`, `CognitiveRuntime` / `FusedTurnRuntime` exception wrappers, migrations, retry helpers, and any internal/direct SQL helpers.
   - **Hard Invariant:** Once a durable dispatch fact exists (`state != 'admitted'`, or a row exists in `background_model_request_bindings`, `background_model_return_capabilities`, or `background_model_response_receipts`), **no code path** may transition that attempt to `not_submitted`. Neither a caller boolean (`definitely_not_submitted=True`), nor an exception type (`ModelDispatchNotSubmitted`, `RuntimeError`, timeout), nor a missing receipt, nor an operator assertion may override a durable dispatch fact.

2. **Explicit PM Ruling on Historical Typed Retry (`ModelDispatchNotSubmitted`):**
  - In Window 13, the candidate attempted to preserve historical `ModelDispatchNotSubmitted` retry tests while moving `mark_dispatching` (and durable request binding / capability commit) ahead of `model_handler`.
  - Window 14 proved that once the durable dispatch/binding boundary is committed before `model_handler`, trusting an exception raised inside `model_handler` or a `definitely_not_submitted=True` boolean on `mark_failure` creates a post-dispatch false `not_submitted` entry point and permits duplicate dispatch.
  - **PM Ruling:** **Historical availability / retry convenience never outranks durable state-machine truthfulness.**
  - Corrective-001 is explicitly authorized to resolve this tension by any of the following truth-preserving mechanisms:
    - **(a) Narrow or retire post-binding `ModelDispatchNotSubmitted` retry:** Once `mark_dispatching` / durable binding has been committed, any failure inside `model_handler` (including `ModelDispatchNotSubmitted`) transitions to `in_doubt` / `FAIL_CLOSED` rather than `not_submitted`; **or**
    - **(b) Introduce a genuine mechanical pre-submission boundary:** Keep the attempt in `admitted` (with no durable dispatch/binding committed) during strictly pre-dispatch local preparation where `ModelDispatchNotSubmitted` is raised, and commit `mark_dispatching` + binding + verifier only at the actual transport/submission handoff boundary after pre-flight checks succeed — such that `mark_failure(..., definitely_not_submitted=True)` is strictly restricted to `state == 'admitted'` with zero durable binding/capability/receipt rows and requires a verified `ModelDispatchNotSubmitted` pre-dispatch failure.
  - **Mandatory Test Evolution Rule:** Corrective-001 **must not** leave a post-binding `not_submitted` backdoor open merely to keep legacy test setups green. If any historical test in `tests/runtime/test_background_model_attempt.py`, `tests/runtime/test_cognitive_runtime.py`, or `tests/runtime/test_turn_execution_recovery.py` previously called `mark_dispatching()` and then expected `mark_failure(..., definitely_not_submitted=True)` to produce `not_submitted`, Corrective-001 is authorized and required to update that test to reflect the tightened invariant, **provided that**:
    1. the historical test intent and prior behavior are explicitly documented in comments and in the Corrective-001 design note,
    2. the comment explains why the old post-`mark_dispatching` expectation was superseded by `BLK-W14-003` / durable truthfulness, and
    3. no test expectation is altered silently.

---

### 4.6 `BLK-W14-004` — `STALE_CAPABILITY_AFTER_LEGAL_RETRY_BINDING_ROTATION` (`BINDING`)

- **Verified Source Facts (`5ad0524c425592210ff184e00ad52abb2c14e366`):**
  - On a retry of the same `attempt_id` (`not_submitted -> admitted -> dispatching`), `BackgroundModelAttemptStore.mark_dispatching(...)` (`src/aios_core/runtime/background_attempt.py:1032-1057`) updates `background_model_request_bindings` via `ON CONFLICT(attempt_id) DO UPDATE SET outbound_request_fingerprint = excluded.outbound_request_fingerprint, relay_id = excluded.relay_id, ...`.
  - In contrast, `_issue_external_return_capability(...)` (`lines 1645-1667`) queries `background_model_return_capabilities` by `attempt_id`, sees `existing is not None`, and returns the stale capability from the first attempt without rotating or re-scoping it to the new `outbound_request_fingerprint` / `relay_id`.
  - When the retried dispatch crashes and its genuine late provider return arrives, `attach_late_trusted_return(...)` (`lines 1729-1739`) compares `capability.outbound_request_fingerprint` (still bound to generation 1) against `binding.outbound_request_fingerprint` (updated to generation 2) and permanently rejects the genuine return with `BackgroundModelResponseConflict("the issued late trusted return capability is not scoped to this attempt's durable originating request")`.
  - Confirmed by Window 14 probes `S3` (`window14_s3_stale_capability_rotation.py`, SHA-256 `7c548aca54e22520417adc2841f21093995ded9c311b40915b9d7fc77297b39f`) and `IA14-ROTATE-001` (`window14_supplementary_probes.py`, SHA-256 `d4f3a2ce4c465f16a568ebfdb42e48d42002890aba922c05f728d44768708ac6`).
- **PM Ruling:** **`BLK-W14-004 = BINDING`**.
- **Authorized Structural Elimination Routes for Corrective-001:**
  Corrective-001 must eliminate `BLK-W14-004` via one of two coherent architectural routes (or both in combination):
  - **Route A (Retain Legal Pre-Dispatch Retry with Scoped Generation Rotation):**
    If an attempt can ever be retried with a new outbound request identity, each new `mark_dispatching` generation must atomically establish:
    1. a new binding generation / scope,
    2. a new verifier / capability scope bound to the new `outbound_request_fingerprint` and `relay_id`,
    3. immediate invalidation of any prior capability/verifier generation so an old proof can never authenticate against the new binding, and
    4. full ability for the genuine late response of the current dispatch generation to attach and complete the turn.
  - **Route B (Structural Elimination of Post-Capability `not_submitted` Retry):**
    Because `not_submitted` is strictly restricted to `state == 'admitted'` **before** `mark_dispatching` ever writes a durable request binding or issues an external return capability/verifier (per `BLK-W14-003`), no attempt that has ever had a binding or capability row can transition to `not_submitted` or re-enter `mark_dispatching`. Even under Route B, `mark_dispatching` and capability/verifier issuance must still enforce consistent binding-to-verifier scope checks and must never silently return a capability/verifier whose `outbound_request_fingerprint` or `relay_id` mismatches the current durable binding.
  - **Hard Prohibition:** Corrective-001 must never leave a reachable state where a legal retry succeeds at dispatch time but permanently breaks late trusted return attachment.

---

## 5. Disposition of Non-Blocking Window 14 Disclosures

### 5.1 `T-ROOT-001` — Pre-Dispatch Observer Capability Hand-Off Timing

- **Window 14 Finding:** In `FusedTurnRuntime._execute_turn_with_Execution` (`src/aios_core/runtime/turn_runtime.py:1311-1324`), the capability is handed to `external_return_observer.accept_return_capability(...)` immediately before `self._model_handler(snapshot)` is invoked.
- **PM Disposition:** **`T-ROOT-001 = ACCEPTED_TRUST_MODEL_DISCLOSURE / CORRECTIVE_DESIGN_NARROWING_RECOMMENDED`** (explicitly **not** promoted to a 5th blocker).
- **Guidance for Corrective-001:** While a registered external return observer / relay is by definition the trusted external boundary in this architecture, Corrective-001 should keep the authority handoff as narrow as practical at the dispatch boundary and ensure Core itself persists only verifier state (`T1`–`T6`).

### 5.2 `EVIDENCE-CONSISTENCY-001` — Self-Referential Commit Message Run ID Citation

- **Window 14 Finding:** Candidate commit `5ad0524c425592210ff184e00ad52abb2c14e366` included a commit message citing GitHub Actions run `36679598965` (which ran on parent commit `a49c1e6874ecb92ae4dc4783d07d733fdc19fa5d`), whereas the actual exact-head formal gate run on `5ad0524c425592210ff184e00ad52abb2c14e366` was run `36680355119` (check run `109774221264`), which was accurately disclosed in the Window 13 closing PR comment (`5924417153`) and independently verified by PM (`5924529954`) and Fresh IA (`5924642667`).
- **PM Disposition:** **`EVIDENCE-CONSISTENCY-001 = NON_BLOCKING_EVIDENCE_METADATA_ISSUE`** (not promoted to a product blocker; caused by git commit-SHA self-reference when recording a CI run ID inside a tracked file / commit message).
- **Hygiene Rule for Corrective-001:** In `WINDOW 16`, if pre-final CI run IDs are cited inside tracked files or commit messages, they must be explicitly labeled as pre-final parent runs, and the exact-head formal gate run ID on the final immutable PR head SHA must be reported in the PR closing comment / handoff metadata after the final push finishes running CI.

---

## 6. Frozen Historical Identity & History Preservation Rules

| Artifact / Ref | Frozen Status | Governance Rule |
|---|---|---|
| `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001` (`WINDOW 13` / `WINDOW 14`) | `DONE` (`ACCEPTANCE_FAIL / blocker=4`) | Closed as a failed candidate cycle requiring Corrective-001 |
| Candidate commit `5ad0524c425592210ff184e00ad52abb2c14e366` | `FAILED_EXACT_CANDIDATE / FROZEN / DO_NOT_MERGE` | Must remain the exact head of `PR #305`; never rebase, amend, or append commits |
| `PR #305` (`arena/01a0f07b-haneof-aios-core-v3-0`) | `OPEN / UNMERGED / FROZEN_FAILED_CANDIDATE / DO_NOT_MERGE` | Must remain open and unmerged as historical evidence anchor |
| Window 14 review commit `84457badc562416f59fb25ca41103700276e0df2` (`arena/01a0f231-haneof-aios-core-v3-0`) | `REVIEW_ONLY / IMMUTABLE / DO_NOT_MERGE` | Canonical source for Window 14 IA report and frozen reviewer probes |
| Formal IA comment `5924642667` on `PR #305` | `IMMUTABLE_REVIEW_RECORD` | Never edit or delete |
| Local-only object `1c0510cfe989e832f46aa1e2e070134048440e27` | `LOST_LOCAL_OBJECT / NEVER_REMOTE_DURABLE / NON_AUTHORITATIVE` | Permanently non-authoritative |

**Strict Prohibitions:**
- Never merge `PR #305` or branch `arena/01a0f07b-haneof-aios-core-v3-0`.
- Never merge review branch `arena/01a0f231-haneof-aios-core-v3-0`.
- Never force-push, rebase, squash, or amend `PR #305` or `arena/01a0f231-haneof-aios-core-v3-0`.
- Never push new commits to `PR #305` (which would bury `5ad0524c425592210ff184e00ad52abb2c14e366` as a non-head commit).

---

## 7. Unique Next `READY` Task: `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-001` (`WINDOW 16`)

### 7.1 Task Identity & Branching Mandate

- **Task ID:** `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-001`
- **Window:** `WINDOW 16`
- **Status:** `READY` (unique active `READY` task on the single-window task board)
- **Branching & PR Mandate:** Must execute on a **brand-new engineering branch** branched from updated `main` (post-Window 15 governance merge) and open a **brand-new Pull Request**. Must **not** push to `PR #305`.

### 7.2 Frozen Scope (`C1`–`C8`)

1. **`C1 — No Post-Hoc Signing Oracle` (`Fixes BLK-W14-001`):**
   A fresh recovery caller (or any caller inspecting `FusedTurnRuntime`, `BackgroundModelAttemptStore`, `SQLiteWorldStore`, or their internal/private attributes and methods) must **not** be able to retrieve an existing signing capability, mint a new signing capability for an `in_doubt` or `dispatching` attempt, obtain a proof-minting nonce/secret, or invoke any Core API to convert arbitrary response bytes into a trusted return.
2. **`C2 — Verifier-Only Recovery` (`Fixes BLK-W14-001 & BLK-W14-002`):**
   Core recovery and `BackgroundModelAttemptStore` may persist and use **verifier-only state** (e.g., a one-way cryptographic commitment / token digest or public verification key bound to the attempt and outbound request scope) to verify a legitimate external late-return proof across process restart, but Core recovery state cannot self-sign or mint a valid proof. Without a valid proof from the genuine external return authority, recovery must `FAIL_CLOSED` (`in_doubt`).
3. **`C3 — Secret Separation Across All Recovery-Readable Surfaces` (`Fixes BLK-W14-002`):**
   Proof-minting authority must never be stored in plaintext or recoverable form in the runtime SQLite database (`db_path`, `background_model_return_capabilities`, or any other table), in the Core recovery-facing object graph, or in database backups/exports. Specifically, the attack chain `read runtime.store.db_path -> extract column -> call late_return_proof() -> call attach_late_trusted_return()` must be structurally impossible because the database contains only a one-way verifier commitment (or public key), never the signing secret/preimage required by `late_return_proof()`.
4. **`C4 — Complete Audit & Closure of All `not_submitted` Write-Sites` (`Fixes BLK-W14-003`):**
   Every write-site capable of setting `state = 'not_submitted'` (`reconcile_not_submitted`, `mark_failure`, `CognitiveRuntime` / `FusedTurnRuntime` exception handlers, migrations, retry helpers, and internal SQL helpers) must enforce that `not_submitted` can **only** be written when `state == 'admitted'` and **zero** durable rows exist for that attempt in `background_model_request_bindings`, `background_model_return_capabilities`, and `background_model_response_receipts`. Once a durable dispatch/binding fact exists, writing `not_submitted` must be mechanically impossible (`BackgroundModelResponseConflict` or `in_doubt` / `FAIL_CLOSED`).
5. **`C5 — Caller Boolean / Exception Type Is Not Post-Binding Proof` (`Fixes BLK-W14-003`):**
   `definitely_not_submitted=True` (or `ModelDispatchNotSubmitted` raised after `mark_dispatching` has committed a durable binding) must never authorize a transition from `dispatching` to `not_submitted`. Furthermore, `mark_failure(..., definitely_not_submitted=True, error=...)` even in `admitted` state must verify that `error` is a genuine pre-dispatch `ModelDispatchNotSubmitted` (not an arbitrary `RuntimeError`) and that no binding, capability/verifier, or receipt row exists.
6. **`C6 — Coherent Retry & Capability/Verifier Lifecycle` (`Fixes BLK-W14-004`):**
   Eliminate stale capability/verifier scope mismatch after retry via Route A and/or Route B:
   - Any pre-dispatch `not_submitted` retry that later reaches `mark_dispatching` must never encounter a stale capability/verifier row from an earlier dispatch, and if capability/verifier issuance ever coexists with retry across distinct outbound request bindings, `mark_dispatching` / capability issuance must atomically rotate the verifier commitment and scope it to the current `outbound_request_fingerprint` and `relay_id`, invalidating any prior generation.
   - `S3` (`window14_s3_stale_capability_rotation.py`) and `IA14-ROTATE-001` must be cleanly resolved so that a legal pre-dispatch retry followed by a genuine late trusted return attaches and completes the turn (`state == 'metered'`), while any stale proof from an invalidated generation fails closed.
7. **`C7 — Preservation of All Exactly-Once & `R1`–`R5` Invariants:**
   Preserve all existing guarantees: zero duplicate provider dispatch after uncertain dispatch, one meter entry, one semantic/world writeback effect, one capability side effect, one assistant output, one turn ACK, conflicting replay `FAIL_CLOSED` (`BackgroundModelResponseConflict`), and full compatibility with `R1`–`R5`.
8. **`C8 — Anonymous / Local Boundary Remains `FAIL_CLOSED`:**
   When no trusted external return observer/authority is registered (or when an untrusted caller supplies unverified bytes), an interrupted `dispatching` attempt must remain strictly `in_doubt` (`FAIL_CLOSED`) with zero automatic promotion.

---

### 7.3 Mandatory Corrective-001 RED-First Protocol

Before modifying any production file under `src/aios_core/**`, `WINDOW 16` must:

1. Extract the frozen Window 14 reviewer probe suite verbatim from canonical review commit `84457badc562416f59fb25ca41103700276e0df2`:
   - `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_IA_WINDOW_14/reviewer_probes/window14_independent_attack.py` (SHA-256: `969112b3a13566e30d7cbd4af4e2ecc3299a1cdd9f0f1a62419ef5688d46f181`)
   - `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_IA_WINDOW_14/reviewer_probes/window14_s3_stale_capability_rotation.py` (SHA-256: `7c548aca54e22520417adc2841f21093995ded9c311b40915b9d7fc77297b39f`)
   - `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_IA_WINDOW_14/reviewer_probes/window14_supplementary_probes.py` (SHA-256: `d4f3a2ce4c465f16a568ebfdb42e48d42002890aba922c05f728d44768708ac6`)
   - `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_IA_WINDOW_14/reviewer_probes/PROBE_CONTRACT.md` (SHA-256: `8a3cfe9006225ff121fe2d9abbb90c5bad94b4f79acddbbc674fd499fc67b0c2`)
   - `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_IA_WINDOW_14/reviewer_probes/PROBE_REVISION_LOG.md` (SHA-256: `198aebb41d47198c155a553bde00c78dac19d0bec4c7b7eae6178957a95c3b25`)
2. Run those frozen reviewer probes fresh against exact failed candidate `5ad0524c425592210ff184e00ad52abb2c14e366` and capture raw RED logs demonstrating all four blockers (`IA14-ORACLE-001`, `IA14-NONCE-001`, `IA14-NS-001`, and `S3` / `IA14-ROTATE-001`) failing on `5ad0524c425592210ff184e00ad52abb2c14e366`.
3. Never weaken or alter the reviewer probes' expected security/state-machine outcomes, and record the exact source commit (`84457badc562416f59fb25ca41103700276e0df2`) and SHA-256 digests in the Corrective-001 review package.

---

### 7.4 Mandatory New Corrective Attack Matrix (`CA1`–`CA5`)

In addition to turning all frozen Window 14 reviewer probes (`IA14-ORACLE-001`, `IA14-NONCE-001`, `IA14-NS-001`, `S3`, `IA14-ROTATE-001`) from RED to GREEN, Corrective-001 must add automated adversarial tests covering:

- **`CA1` (Full Object-Graph & Reflection Audit):** After process crash and restart, recursively traverse `FusedTurnRuntime`, `BackgroundModelAttemptStore`, `SQLiteWorldStore`, and all reachable attributes/methods (including `_`-prefixed private attributes/methods) and prove that no method or attribute yields a signing capability or proof-minting secret for an `in_doubt` or `dispatching` attempt.
- **`CA2` (Full SQLite File / WAL / Dump / Read-Only Inspection Attack):** Inspect the entire SQLite database file (`db_path`, all tables, columns, and raw SQL dump) after dispatch crash and prove that an attacker with full read access to the database cannot compute a valid `LateTrustedReturnProof` for caller-chosen or deterministic response bytes.
- **`CA3` (Exhaustive `not_submitted` Write-Site Attack):** Attempt every public and internal write path (`reconcile_not_submitted`, `mark_failure(..., definitely_not_submitted=True)` with both `ModelDispatchNotSubmitted` and `RuntimeError`, cognitive/turn runtime wrappers, and retry admission) after a durable dispatch/binding exists, and prove every path refuses to write `not_submitted` and prevents duplicate provider dispatch.
- **`CA4` (Pre-Dispatch vs Post-Dispatch Retry & Late-Return Lifecycle):**
  1. Genuine pre-dispatch failure (before `mark_dispatching` / durable binding) -> `not_submitted` -> retry -> crash after dispatch -> genuine late trusted return -> attaches and completes turn (`metered`, `1` meter, `1` output).
  2. If multi-generation capability rotation is reachable, prove stale generation-1 proof is rejected (`BackgroundModelResponseConflict`) while generation-2 proof succeeds.
- **`CA5` (Cross-Attempt / Cross-Round / Conflicting-Payload / Replay Attacks):** Verify that a valid proof for `(attempt_id, round, request_fingerprint, response_fingerprint)` is rejected if replayed against a different attempt, round, request binding, or mutated response payload, while idempotent replay of the exact already-attached response remains side-effect-free.

---

### 7.5 Formal Runtime Gate & Scope Constraints for `WINDOW 16`

1. **Formal GitHub Actions Gate:**
   - Must run `.github/workflows/core-background-late-trusted-return-001.yml` on the exact final candidate head SHA of the new Corrective-001 PR and achieve `GREEN` across the full test suite (including the frozen Window 14 reviewer probes, `CA1`–`CA5`, `R1`–`R5`, and `tests/c15_persistence/test_resident_surface.py`).
2. **Strict C15 / Persistence Scope Prohibition:**
   - Corrective-001 must **not** modify `tools/c15_persistence/**`, `tools/c15_preflight/**`, `evidence/w08/**`, `reviews/C15_RCC_RES_B_ACCEPT_003_WINDOW_10/**`, `reviews/internal_habitation/**`, `PR #302`, `PR #305`, Window 14 review branch `arena/01a0f231-haneof-aios-core-v3-0`, or any persistence remote refs.

---

## 8. Downstream `BLOCKED` Chain & Mandatory Execution Sequence

Until `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-001` completes implementation in `WINDOW 16`, passes Fresh Independent Acceptance in `WINDOW 17`, and receives a PM Integration Receipt in `WINDOW 18`, the following tasks remain strictly **`BLOCKED`**:

| Downstream Task | Status | Blocking Dependency |
|---|---|---|
| `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-001-IA` (`WINDOW 17`) | `BLOCKED` | Blocked on `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-001` (`WINDOW 16`) formal candidate |
| `C15-RCC-RES-B-RERUN-003` (`run_id=c15-rcc-res-b-rerun-003-eab38dc7076e`, `PR #302`) | `RETIRED / SUPERSEDED / DO_NOT_ACCEPT / DO_NOT_MERGE` | Permanently retired by Window 12 adjudication |
| `C15-RCC-RES-B-RERUN-004` | `BLOCKED` | Blocked until `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-001` is `DONE (ACCEPTED)` and merged to `main` |
| `C15-RCC-RES-B-ACCEPT-004` | `BLOCKED` | Blocked on `C15-RCC-RES-B-RERUN-004` |
| `C15-FINAL-RELEASE-DECISION` | `BLOCKED` | Blocked on `C15-RCC-RES-B-ACCEPT-004` |
| `P16` Formal Habitation | `BLOCKED` | Blocked on `C15-FINAL-RELEASE-DECISION` |

**Mandatory Execution Sequence:**
1. **`WINDOW 15` (Current — `GOVERNANCE_ONLY`):** Merge this PM failure adjudication to `main` and post the formal freeze notice on `PR #305`.
2. **`WINDOW 16` (`CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-001`):** Implement `C1`–`C8` on a new branch + new PR, run RED-first against `5ad0524c425592210ff184e00ad52abb2c14e366`, turn all Window 14 probes + `CA1`–`CA5` GREEN, and pass the formal CI gate on exact final PR head.
3. **`WINDOW 17` (`CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-001-IA`):** Fresh Independent Acceptance review of the Corrective-001 candidate.
4. **`WINDOW 18` (`CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-001-INTEGRATION`):** PM integration merge and receipt on `main`, followed by adjudication of C15 re-entry.


---

## 10. Post-Merge PM Entry Clarification — S3 / C4-C5 Consistency (2026-10-01)

Status: **BINDING GOVERNANCE CLARIFICATION / NO VERDICT CHANGE / GOVERNANCE_ONLY**

This clarification resolves an internal conflict discovered after the WINDOW 15 adjudication merge and before WINDOW 16 engineering started. It does **not** change the four binding blockers, the frozen failed candidate, the canonical review, or the unique next READY task.

### 10.1 Conflict found

The adjudication correctly freezes C4/C5:

- once any durable dispatch fact exists (state is no longer `admitted`, or any durable request-binding / verifier-capability / response-receipt row exists), writing `not_submitted` is mechanically forbidden;
- `ModelDispatchNotSubmitted` or `definitely_not_submitted=True` after `mark_dispatching` cannot override that durable fact.

However §7.3 also said all frozen Window 14 probes, including `window14_s3_stale_capability_rotation.py`, must turn GREEN unchanged. The canonical S3 probe's frozen expected contract explicitly requires a sequence in which `mark_dispatching` first creates a durable binding/capability and then `mark_failure(... ModelDispatchNotSubmitted ...)` succeeds with `state == "not_submitted"`. That expected transition is now constitutionally forbidden by C4/C5. Both requirements cannot be satisfied simultaneously.

### 10.2 Binding precedence

**C4/C5 durable truthfulness takes precedence.** The original Window 14 S3 probe remains immutable historical evidence for BLK-W14-004 on failed candidate `5ad0524c425592210ff184e00ad52abb2c14e366`; its source bytes, hashes, and original RED result must never be changed or relabeled.

For Corrective-001:

- `IA14-ORACLE-001`, `IA14-NONCE-001`, and `IA14-NS-001` remain unchanged GREEN requirements where their expected outcomes are compatible with C1-C8.
- The **original S3 is NOT a candidate-GREEN gate under the C4/C5 Route-B semantics**, because its frozen expectation requires the very post-binding `not_submitted` transition that C4/C5 prohibit.
- Instead, Corrective-001 must rerun the original S3 unchanged on failed candidate `5ad0524c...` and preserve it as RED evidence, then add a new frozen corrective probe (suggested ID `CA4-B / S3-ROUTE-B`) proving the same sequence is stopped at the first illegal transition: post-binding `mark_failure(... definitely_not_submitted=True ...)` is refused or leaves the attempt `in_doubt`; no `not_submitted`, no retry, no second outbound identity, and therefore no stale-capability lifecycle is reachable.
- If engineering introduces a genuinely separate **pre-submission** state where `state == admitted` and there are zero request-binding / verifier-capability / receipt rows, a legal `not_submitted -> retry` may still exist. CA4 must then prove that retry followed by the first real dispatch supports a genuine late trusted return exactly once. This is distinct from the historical S3 post-binding sequence.

### 10.3 Route A / Route B interpretation

For the **historical S3 post-binding sequence**, Route B is binding: once a durable binding/verifier exists, `not_submitted` retry is structurally impossible.

Route A is permitted only if a future implementation introduces a genuinely pre-submission lifecycle that still satisfies C4/C5 (no durable dispatch/binding/verifier/receipt fact before `not_submitted`). Route A must never be used to preserve post-binding `not_submitted`.

### 10.4 Canonical review path metadata correction

The canonical Window 14 review commit remains `84457badc562416f59fb25ca41103700276e0df2`. Its actual committed review directory is:

`reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_IA/**`

References in the original WINDOW 15 adjudication text to `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_IA_WINDOW_14/**` are a **non-semantic path metadata typo**. Corrective-001 must source frozen reviewer probes from the actual canonical review tree/path above and verify the recorded SHA-256 values.

### 10.5 Window routing unchanged

`CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-001` remains the unique READY task for **WINDOW 16**, on a new engineering branch + new PR from updated main. WINDOW 17 remains Fresh IA; WINDOW 18 remains PM integration. No downstream gate is released by this clarification.
