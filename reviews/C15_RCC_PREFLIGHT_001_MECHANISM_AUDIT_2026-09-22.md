# C15-RCC-PREFLIGHT-001 — Resident Cognitive Continuity Mechanism Audit

- Date: 2026-09-22
- Repository: `Haneof/Haneof-AIOS-Core-v3.0`
- Task: `C15-RCC-PREFLIGHT-001`
- Role: Resident Cognitive Continuity Preflight Architect / Independent Mechanism Auditor
- Reviewed main: `fb7921df2231ac8fb6af85f29d6e9eff64272245`
- Ruling anchor: `governance/C15_RESIDENT_COGNITIVE_CONTINUITY_RULING_2026-09-22.md`
- Test-plan anchor: `governance/C15_RESIDENT_COGNITIVE_CONTINUITY_TEST_PLAN_2026-09-22.md`
- C14 closure anchor: `reviews/C14_CLOSE_001_FINAL_CLOSURE_REVIEW_2026-09-22.md`
- Audit PR: #97
- Core changes in this audit: **NONE**
- Audit verdict: **ONE MECHANISM GAP FOUND**
- Next implementation task: `C15-RCC-MECH-FIX-001`
- `C15-RCC-FIXTURE-001`: remains **BLOCKED**

## 1. Scope and audit rule

This preflight answers one question only:

> Does the current `main` already provide the mechanical substrate required for C15 Resident Cognitive Continuity?

Each capability is classified only as:

- `ALREADY_IMPLEMENTED`
- `MECHANISM_GAP`
- `INSUFFICIENT_EVIDENCE`

The audit does not treat missing semantic Resident proof as a Core mechanism gap. It also does not create a second identity/personality/self database, a second Resident runtime, a hidden handoff store, a fixture, or expected cognition.

The C15 ruling itself was the only change between the C14 closure base `623f8471cdd6ac2d756c15231f65f311e662f9d9` and reviewed `main@fb7921df2231ac8fb6af85f29d6e9eff64272245`: the compare contains only the C15 ruling plus task-board/checkpoint governance files and **no `src/aios_core/**` change**. Therefore the existing C14/P15 test evidence remains applicable to the same Core blobs. This audit does not claim a new GitHub Actions run for the reviewed merge SHA.

## 2. P1–P13 preflight matrix

| ID | Capability | Verdict | Code evidence | Test / runtime evidence | Gap? |
|---|---|---|---|---|---|
| P1 | Unified cognition persistence | **ALREADY_IMPLEMENTED** | `src/aios_core/storage/sqlite_store.py`; `contracts/base.py`; `contracts/models.py`; `ai_world/cognition.py` | `test_v3_ai_world.py::test_all_ai_domains_share_one_world_store_without_second_ai_database` | No |
| P2 | User Understanding writeback | **ALREADY_IMPLEMENTED** | `AIWorldCognitionService.commit` → `CognitionWritebackService.commit_claim`; unified EvidenceSet/Claim/Dependency; index catch-up | `test_v3_ai_world.py`; fused-runtime commit/read path; C14 durable-cognition recovery test | No |
| P3 | Relationship / Role writeback | **ALREADY_IMPLEMENTED** | Relationship is a typed AI-world Claim; evidence-grounded commit; unified revision path | `test_v3_ai_world.py::test_snapshot_contains_only_current_active_ai_world_claims`; Relationship revise coverage in `test_v3_ai_world.py` | No; isolation defect is separately P11 |
| P4 | Self / Calibration writeback | **ALREADY_IMPLEMENTED** | Self/Calibration are AI-self-scoped typed Claims over the same World; evidence refs and unified revision/retraction | `test_v3_ai_world.py::test_calibration_can_record_real_correction_evidence`; all-domain typed-view test; C14 grounding regressions | No; semantic validity remains Resident/evaluator responsibility |
| P5 | Strategy / Experience writeback | **ALREADY_IMPLEMENTED** | Strategy Claim; `OperationExperience`; `CommunicationExperience`; exact case refs; dependencies; same World; index catch-up | `test_v3_periodic_review.py` real-case/cross-subject/assistant-evidence tests; `test_strategy_cognition_can_close_through_real_operation_outcome_case` | No |
| P6 | Indexing / search / active retrieval | **ALREADY_IMPLEMENTED** | `WorldSearchIndex`; claim/outcome/operation-experience/communication-experience indexing; `search_world`; `read_ai_world` | memory-recommendation tests; fresh-runtime recovery test uses `read_ai_world -> search_world -> inspect_world_object` | No, except P11 typed-facade subject leak |
| P7 | Relevant cognition selection / runtime exposure | **ALREADY_IMPLEMENTED** | bounded topic recommendation; explicit `core_context` tags; model can actively search/inspect deeper evidence | `test_no_topic_means_zero_historical_injection`; `test_unrelated_topic_returns_empty_bundle`; `test_new_session_loads_only_explicit_core_ai_world_context` | No, except P11 subject leak |
| P8 | Fresh-runtime recovery | **ALREADY_IMPLEMENTED** | durable World + rebuildable WorldSearchIndex + new FusedTurnRuntime | `test_loop_new_runtime_recovers_exact_durable_ai_world_cognition` reopens SQLite, rebuilds Index, creates new Runtime/session, retrieves exact durable Claim | No |
| P9 | Unified revise / retract | **ALREADY_IMPLEMENTED** | `CognitionRevisionService`; forward revisions; retraction; dependent stale propagation; index catch-up | `test_v3_cognition_revision.py`; Periodic Review revision test; C14 revise/retract grounding test | No |
| P10 | Anti-self-proof mechanical boundary | **ALREADY_IMPLEMENTED** | EvidenceSet requirement; C14 deterministic lineage closure; Summary/Wake not terminal proof; Experience follows real cases | old-AI-Claim self-grounding rejection; assistant-only rejection; cross-subject fail-closed; Wake-completion-no-semantic-write tests | No; semantic truth is not a Core text classifier |
| P11 | Subject / User / AI-self isolation | **MECHANISM_GAP** | ordinary runtime search/direct inspect are scoped, but `AIWorldCognitionService.current/core_context/snapshot` omit domain-derived subject filter; typed `revise/retract` trust target payload subject | shared-store multi-subject continuity test proves a WorldStore can contain multiple subjects; runtime `read_ai_world` and auto `core_context` directly expose the defective typed facade | **Yes** |
| P12 | Replacement-model identity attestation | **INSUFFICIENT_EVIDENCE** | provider harness stores configured provider/model + provider response/request id; Core metering persists that provenance but does not independently attest the configured model | provider-runtime tests prove provenance serialization and immutability, not trusted model identity binding | No Core gap established; **R6 remains blocked** |
| P13 | No second DB / no second Resident runtime | **ALREADY_IMPLEMENTED** | AI-world domains are typed Claims in one WorldStore; FusedTurnRuntime reuses one CognitiveRuntime; non-world metering is not cognition truth | no-second-AI-database test; C14 same-runtime closure; fresh-runtime reopen test | No |

## 3. Current code evidence

### 3.1 Unified World and cognition write path

`SQLiteWorldStore` persists every WorldObject revision into the same durable `object_revisions` table with `object_id`, `revision`, `object_type`, `subject_id`, `world_revision` and durable JSON payload. Claims, EvidenceSets, Dependencies, Outcomes, OperationExperience and CommunicationExperience are all ordinary typed WorldObjects.

`AIWorldCognitionService` does not own an identity/personality database. It maps User Understanding, Relationship, Self, Strategy, Calibration and the other AI-world domains onto the existing Claim engine. User Understanding / Relationship / Strategy write with the current user subject; Self / Calibration write with `ai_agent_self`.

`CognitionWritebackService.commit_claim` requires pinned evidence, creates a durable EvidenceSet, Claim and Dependency closure, commits them through the same WorldStore, then catches the WorldSearchIndex up.

### 3.2 Revision / retraction

`CognitionRevisionService` implements forward-only Claim revision and retraction. It preserves the historical revision, writes a new current revision, records new evidence, marks exact downstream dependents review-required where applicable, and refreshes the index. Retraction is not “ignore the old Claim in the prompt”; it is durable World state.

### 3.3 OperationExperience / CommunicationExperience

`PeriodicReviewService.commit_operation_experience` requires at least one exact pinned real-case ref and accepts only Observation, Outcome or CommunicationExperience cases. It rejects cross-subject cases and rejects assistant conversation Observation as real result evidence. It writes the Experience and exact dependency lineage into the unified World.

`CommunicationExperienceService.record` requires exact evidence refs, enforces the runtime subject, requires at least one real user/world Observation or Outcome, excludes assistant output as the sole feedback proof, writes exact dependency edges, and catches the shared index up.

These objects are durable, indexable and searchable after Runtime recreation. They are evidence-bearing experience records; nothing in these services automatically turns an Experience into a hard runtime policy.

### 3.4 Relevant cognition rather than full dump

`ProactiveMemoryRecommender` is topic-gated, bounded, subject-scoped and can legally return zero cards. The new-session AI identity cockpit uses `AIWorldCognitionService.core_context()`, which only takes Claims explicitly tagged `core_context`; untagged User Understanding is not automatically dumped. The Resident retains active `search_world`, `read_ai_world`, `inspect_world_object`, Claim comparison, Outcome inspection, timeline, recall expansion and ALL_DIMENSIONS access.

The relevant-selection mechanism therefore exists. P11 below is a separate authorization/isolation defect in one typed facade; it does not justify replacing the retrieval architecture.

## 4. Current test / runtime evidence

The existing codebase already contains direct mechanical evidence for the required continuity substrate:

1. `tests/integration/test_v3_ai_world.py::test_all_ai_domains_share_one_world_store_without_second_ai_database` verifies all AI domains share the WorldStore and explicitly verifies there is no `runtime_ai_self_memory`, `ai_user_understanding` or `ai_relationship` table.
2. `tests/integration/test_v3_ai_world.py::test_calibration_can_record_real_correction_evidence` proves Calibration can be grounded in a real correction and retrieved as a typed current view.
3. `tests/integration/test_v3_ai_world.py::test_ai_world_claim_reuses_p9_revision_chain` and the Relationship revision coverage prove AI-world claims reuse the unified revision engine.
4. `tests/integration/test_v3_fused_turn_runtime.py::test_new_session_loads_only_explicit_core_ai_world_context` proves a fresh session receives only explicitly selected continuity cognition rather than a whole cognitive-world dump.
5. `tests/integration/test_v3_c14_cognitive_derivation_runtime.py::test_loop_new_runtime_recovers_exact_durable_ai_world_cognition` closes and reopens SQLite, rebuilds the index, creates a new FusedTurnRuntime and new session, and retrieves the same durable cognition through ordinary `read_ai_world -> search_world -> inspect_world_object`.
6. `tests/integration/test_v3_periodic_review.py::test_operation_experience_requires_pinned_real_case_refs` and `test_operation_experience_rejects_non_real_cross_subject_and_assistant_evidence` enforce real-case, exact-revision and subject boundaries for OperationExperience.
7. `tests/integration/test_v3_c14_cognitive_derivation_runtime.py::test_strategy_cognition_can_close_through_real_operation_outcome_case` demonstrates Strategy cognition closing through OperationExperience to a real platform Outcome.
8. `test_old_ai_claim_via_summary_cannot_self_ground_new_claim`, `test_t28_assistant_only_summary_is_rejected_but_user_leaf_can_ground_cognition`, `test_derivation_grounding_missing_unknown_and_cross_subject_fail_closed`, and `test_loop_wake_completion_is_lifecycle_only_not_semantic_evidence` cover the anti-self-proof mechanical boundary.
9. `tests/integration/test_v3_long_context_continuity.py::test_same_session_id_is_isolated_between_subjects` demonstrates that one WorldStore can legally contain multiple user subjects. That fact makes P11’s missing typed-facade subject filter a real leak rather than a theoretical issue hidden by “one DB per user”.

C14 closure records 341/341 deterministic tests GREEN on the same Core blobs. Reviewed main differs from the C14 closure anchor only by C15 governance files, so this preflight reuses that evidence instead of manufacturing duplicate tests. No new CI run is claimed for `main@fb7921d`.

## 5. Subject / User / AI-self isolation audit

### 5.1 User Understanding isolation — MECHANISM_GAP

Writeback is correctly user-scoped. Ordinary `search_world` is correctly called with `subject=self.subject_id`. Exact `inspect_world_object` is guarded by `_scoped_payload`.

However `AIWorldCognitionService.current()` currently iterates:

`self.store.list_payloads(object_type=ObjectType.CLAIM)`

without a `subject_id` filter. It filters only AI-world metadata, domain, active status and optional scope key. Therefore a service constructed for User B can return User A’s active `user_understanding` Claim when A and B share a WorldStore.

`FusedTurnRuntime._read_ai_world()` calls this method directly, so the defect reaches the Resident capability surface.

### 5.2 Relationship isolation — MECHANISM_GAP

Relationship uses the same `current()` path. User A’s Relationship Claim can therefore be returned inside User B’s `read_ai_world` result.

The problem is stronger for Claims tagged `core_context`: `core_context()` calls `current()` and can place the foreign Relationship Claim directly into a later Runtime cockpit.

### 5.3 User-specific Strategy isolation — MECHANISM_GAP

Current Strategy writeback is user-scoped. But typed retrieval does not enforce the expected subject derived from the Strategy domain. A Strategy learned for User A can therefore be read by User B through `read_ai_world(domains=["strategy"])`.

C15 does not authorize silently treating that Claim as a general cross-user strategy. A future general strategy scope, if ever introduced, must be explicit; it cannot be inferred from the current missing filter.

### 5.4 Self / Calibration boundary — ALREADY_IMPLEMENTED with semantic responsibility retained

Self / Calibration Claims use the Resident AI subject `ai_agent_self`, so they are intentionally recoverable across the Resident’s user interactions. Their EvidenceSet / Dependency lineage preserves the exact user/world evidence that supported them.

Core must preserve that provenance, which it does. Core must not attempt semantic text classification such as “this conclusion from User A applies to all users.” Whether a Self/Calibration conclusion overgeneralizes its evidence remains a Resident/evaluator semantic judgment. The P11 fix must not accidentally hide legitimate AI-self cognition.

### 5.5 Search/index/direct object-id isolation

The ordinary Runtime paths are already fail-closed:

- `search_world` passes the current user subject to WorldSearchIndex.
- timeline / recall / recommendation paths pass the current user subject.
- `inspect_world_object` uses `_scoped_payload`, which permits only the current user plus `ai_agent_self`.
- Claim comparison and Outcome inspection reuse scoped payload reads.

The low-level WorldStore and index are intentionally multi-subject primitives; authorization belongs at the Runtime/facade boundary. The defect is therefore narrow: the AI-world typed facade does not apply its own domain-derived subject authorization.

### 5.6 Typed revise / retract fail-closed — MECHANISM_GAP

`AIWorldCognitionService.revise()` and `retract()` fetch the requested target payload and then construct `CognitionRevisionService(subject_id=str(payload["subject_id"]))`.

That means a User B service can be handed User A’s AI-world Claim and will adopt A’s subject from the target itself instead of checking that the target subject is the one legally implied by the target AI-world domain for User B.

The generic FusedTurnRuntime `revise_claim/retract_claim` path is separately configured to the current user and is safer, but the public typed AI-world facade is not fail-closed. C15 requires the facade itself to be safe.

### Subject-isolation verdict

**P11 = MECHANISM_GAP.**

This is a true mechanical authorization defect in an existing path. It is not a request for a new cognitive architecture and does not justify a second store/runtime.

## 6. Replacement-model identity attestation audit

### 6.1 Evidence acceptable for R6

R6 may use evidence whose provider/model identity is outside Resident control, for example:

- execution-platform model metadata that the Resident cannot modify;
- provider response metadata that binds the response/request identifier to the provider/model;
- trusted orchestration metadata produced outside the Resident;
- a provider/model binding record signed or otherwise controlled by the provider/platform;
- equivalent external execution metadata that an evaluator can independently inspect.

The attestation must make “Resident C ran on a different underlying model/provider” independently checkable.

### 6.2 Evidence that is never sufficient by itself

The following cannot alone establish R6:

- a prompt saying “you are Claude/GPT/...”
- the Resident’s own self-report
- a Python constant or variable such as `DECLARED_MODEL = "..."`
- branch names
- README/run-report prose
- fixture metadata
- evaluator guessing
- style/fingerprint inference

### 6.3 Current repository/platform evidence

`tests/habitation/provider_runtime.py` has useful request provenance but not yet a sufficient model attestation:

- `ProviderConfig.provider` and `ProviderConfig.model` are selected/configured by the execution harness.
- requests are sent to provider endpoints and provider response IDs are recorded.
- `ModelCallProvenance(provider, model, request_id)` copies `model` from `self.client.config.model`.
- `provenance_snapshot()` serializes that configured provider/model plus a config fingerprint and provider response/request IDs.
- `.github/workflows/p16-provider-habitation-manual.yml` takes `provider` and `model` from workflow inputs.
- `ModelMeteringLedger` durably preserves provider/model/request-id provenance and rejects replay conflicts, but it cannot make an upstream declared model identity independently true.

The tests prove secret-safe provenance serialization and immutable accounting identity. They do **not** prove that the configured model string is an immutable provider/platform attestation of the actual underlying model used for the response.

The current ChatGPT execution environment available to this audit likewise does not expose an evaluator-verifiable immutable platform model-attestation record through the repository interface.

### Replacement-model identity verdict

**P12 = INSUFFICIENT_EVIDENCE.**

This is not converted into a Core mechanism gap. It does, however, remain a hard **R6 evidence blocker**: a later Resident-C run must capture an accepted trusted attestation source or R6 cannot be VALID.

## 7. R1–R9 responsibility split

The C15 evaluator must not reuse one artifact to silently prove five different responsibilities.

| Rule | What it proves | What it does not prove |
|---|---|---|
| R1 | User Understanding was legitimately formed/grounded | fresh Runtime or replacement-model recovery |
| R2 | Relationship/Role cognition was legitimately formed/grounded | later behavioral consumption |
| R3 | Self/Calibration cognition had real-case grounding and was not mere self-description | replacement-model identity |
| R4 | Strategy/Experience closed through real Outcome/feedback lineage | that a later model actually used it |
| R5 | cognition survived a fresh-window/new-Runtime boundary through ordinary AIOS state | that the underlying model changed |
| R6 | a provably different underlying model/provider recovered the cognition | that its later action was materially affected |
| R7 | recovered cognition materially affected later behavior | that cognition remained correct forever |
| R8 | later reality could retain/weaken/revise/retract the cognition | replacement-model proof |
| R9 | no self-proof, pseudo-LLM, future leak or hidden handoff contaminated the result | any positive cognition result by itself |

## 8. Anti-self-proof mechanical boundary

### Core already guarantees

- durable Claim writes require pinned EvidenceSet support;
- exact Dependency lineage is persisted;
- Summary is a navigation/compression container, not terminal truth;
- C14 derivation computes deterministic provenance closure to qualifying reality leaves;
- old AI semantic Claims cannot recursively certify a new Claim merely because they were once grounded;
- assistant raw conversation does not qualify as sole user/world reality grounding in the C14 derivation boundary;
- Wake completion is lifecycle state, not semantic proof;
- OperationExperience pins real case refs and rejects Claim/self-cognition as a real result case;
- CommunicationExperience requires real user/world Observation or Outcome feedback and rejects assistant output alone;
- cross-subject support refs fail closed in the derivation resolver.

### Resident/evaluator must still judge

Core does not and should not infer from natural-language semantics whether:

- a real Outcome semantically proves success for the particular claim;
- a Self/Calibration sentence overgeneralizes from one user;
- a Strategy is applicable to a later case;
- a model actually relied on a recovered cognition;
- a Resident’s wording corresponds to the intended R1–R4 semantic proposition.

Those are semantic-validity questions for the Resident/evaluator, not reasons to introduce a deterministic semantic oracle into Core.

## 9. Runtime capability audit

The current FusedTurnRuntime already allows the Resident to:

- `search_world`
- `inspect_world_object`
- compare Claims
- inspect Outcome
- inspect OperationExperience / CommunicationExperience through World search/direct inspection
- request ALL_DIMENSIONS projection
- `read_ai_world`
- commit cognition
- revise cognition
- retract cognition
- remain silent

C15 therefore does **not** require a second Resident runtime. The P11 fix must preserve the existing Runtime and only close subject authorization in the typed AI-world facade.

## 10. ALREADY_IMPLEMENTED list

- P1 unified cognition persistence
- P2 User Understanding writeback
- P3 Relationship/Role writeback
- P4 Self/Calibration writeback substrate
- P5 Strategy/OperationExperience/CommunicationExperience writeback
- P6 shared index/search/active retrieval
- P7 bounded relevant-context selection and deeper model search
- P8 fresh-runtime durable recovery
- P9 unified retain/revise/retract semantics
- P10 anti-self-proof mechanical provenance boundary
- P13 no second identity/personality/self DB and no second Resident runtime

## 11. MECHANISM_GAP list

### P11 — typed AI-world subject isolation

Exact defect:

1. `AIWorldCognitionService.current()` reads all active AI-world Claims without filtering each domain to its legally expected subject.
2. `core_context()` and `snapshot()` inherit that result.
3. Runtime `read_ai_world` exposes it to the Resident; tagged foreign cognition can also enter automatic cockpit context.
4. typed `AIWorldCognitionService.revise/retract` derive the authorized subject from the target payload itself instead of independently deriving it from the target domain plus the current service identity.

Impact:

- User A User Understanding can be exposed as User B cognition.
- User A Relationship can enter User B context.
- User A Strategy can be reused as User B-specific learned strategy.
- typed mutation is not fail-closed against a foreign user-scoped AI-world Claim.

## 12. INSUFFICIENT_EVIDENCE list

### P12 — replacement-model identity attestation

Current provider/request provenance is useful but the model identifier is still configured/declared rather than independently bound by trusted provider/platform attestation. R6 must remain unproven until that trusted external evidence exists.

Future semantic R1–R4/R7/R8 validity is also intentionally not claimed by this preflight; those are Resident/evaluator tests, not missing Core mechanisms.

## 13. Core implementation decision

**A Core change is required, but only one narrow change.**

Create exactly one task:

### `C15-RCC-MECH-FIX-001`

**Exact gap**

Make `AIWorldCognitionService` enforce domain-derived subject authorization for every typed AI-world read and mutation.

**Affected code**

Primary target:

- `src/aios_core/ai_world/cognition.py`

Runtime code should change only if needed to preserve the same fail-closed contract; no new store, database, runtime or handoff layer is permitted.

**Minimal completion definition**

1. In a single shared WorldStore containing User A and User B:
   - User B `current()/read_ai_world/snapshot/core_context` cannot return A’s User Understanding, Relationship or user-scoped Strategy.
2. AI-self domains such as Self/Calibration remain legally retrievable as `ai_agent_self` cognition.
3. typed `revise/retract` reject a target whose subject does not match the subject legally derived from the Claim’s AI-world domain for the current service.
4. ambiguous/missing AI-world domain/subject scope fails closed rather than becoming global.
5. ordinary subject-scoped `search_world` and `inspect_world_object` behavior remains unchanged.
6. no second identity/personality database, no new Resident runtime, no hidden cross-model handoff state.
7. targeted regressions must cover read, automatic core context, direct typed mutation, and negative controls for legitimate AI-self cognition.

Suggested targeted regression locations:

- `tests/integration/test_v3_ai_world.py`
- `tests/integration/test_v3_fused_turn_runtime.py`

The task must remain minimal; it must not redesign Strategy scope, infer semantic generality, or attempt to solve R6 attestation inside Core.

## 14. Next task decision

Because P11 is a real `MECHANISM_GAP`:

- `C15-RCC-PREFLIGHT-001 = DONE`
- create `C15-RCC-MECH-FIX-001 = READY`
- `C15-RCC-FIXTURE-001 = BLOCKED`
- do not run fixture, Resident A/B/C or evaluator in this window.

After `C15-RCC-MECH-FIX-001` is independently completed and gated, the C15 chain may return to fixture preparation. R6 will still require trusted replacement-model identity evidence at the actual Resident-C execution stage; declared identity alone remains unacceptable.

## 15. Final preflight verdict

`C15 RCC CORE MECHANISM = NOT YET FULLY ALREADY_IMPLEMENTED`

Reason: **one narrow P11 subject-isolation mechanism gap exists in the AI-world typed facade.**

All other audited Core continuity mechanisms are already present. Replacement-model identity attestation is separately `INSUFFICIENT_EVIDENCE`, not a proven Core mechanism defect, and remains a future R6 evidence blocker.
