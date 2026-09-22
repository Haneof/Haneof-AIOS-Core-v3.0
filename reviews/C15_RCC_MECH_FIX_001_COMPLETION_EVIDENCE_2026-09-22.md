# C15-RCC-MECH-FIX-001 Completion Evidence

- Date: 2026-09-22
- Repository: `Haneof/Haneof-AIOS-Core-v3.0`
- Task: `C15-RCC-MECH-FIX-001`
- Starting main: `a6e2adf5d5676f765e40150aa3e21d145d4aef30`
- Engineering branch: `fix/c15-rcc-mech-fix-001-20260922-sol`
- PR: #98
- Exact gated implementation candidate: `de65572d2ce31cc53d5daadc252fe91e94e045d2`

## 1. Reproduced defect

The defect was reproduced before any Core modification.

A test-only head `9cfe55d6ca920441b37799e51ed1330e8c26ca08` was built directly on starting main; its Core blobs were unchanged from `a6e2adf5d...`.

Reproduction CI:

- `p10-ai-world` run `35698757405`: **FAILURE**, 9 failed / 18 passed.
- `fused-turn-runtime` run `35698757513`: **FAILURE**, 1 failed / 25 passed.
- `p10-ai-world-gate` run `35698757399`: **FAILURE**.

Observed failures mechanically proved:

1. User B `current(USER_UNDERSTANDING)` returned User A cognition.
2. User B `current(RELATIONSHIP)` returned User A cognition.
3. User B `current(STRATEGY)` returned User A cognition.
4. User B `core_context()` included User A tagged user-scoped cognition.
5. User B `snapshot()` included User A user-scoped cognition.
6. User B typed `revise()` on User A user-scoped cognition did not raise.
7. User B typed `retract()` on User A user-scoped cognition did not raise.
8. malformed AI-world metadata did not fail closed for typed mutation.
9. normal FusedTurnRuntime `read_ai_world` exposed User A cognition to User B.

## 2. Exact root cause

`AIWorldCognitionService.current()` recognized AI-world metadata/domain/status/scope, but did not compare the Claim `subject_id` with the subject legally derived for that domain in the current service context.

`AIWorldCognitionService.revise()` and `retract()` fetched the target payload and then constructed `CognitionRevisionService(subject_id=payload["subject_id"])`. This trusted the target's own subject as authorization instead of validating it against the caller/service context.

Therefore a shared WorldStore containing more than one user subject allowed the typed AI-world facade to cross user boundaries even though ordinary scoped search/direct-inspect paths already enforced subject scope.

## 3. Minimal implementation

Changed Core file:

- `src/aios_core/ai_world/cognition.py`

The existing ownership rule remains authoritative and unchanged:

```text
USER_UNDERSTANDING -> current user_id
RELATIONSHIP       -> current user_id
STRATEGY           -> current user_id

SELF               -> ai_subject_id
CALIBRATION        -> ai_subject_id
INTENT             -> ai_subject_id
COGNITIVE_BOUNDARY -> ai_subject_id
PERSONALITY        -> ai_subject_id
```

Implementation changes:

- `current()` now computes `expected_subject = self._subject_for(domain)` after parsing the domain and excludes any payload whose `subject_id` is not that expected subject.
- `core_context()` and `snapshot()` continue to reuse `current()`; no duplicate subject filter was introduced.
- A single typed-mutation authorization helper validates:
  - `ai_world is True`;
  - `ai_domain` exists and parses as `AIWorldDomain`;
  - target `subject_id` equals `self._subject_for(domain)`.
- `revise()` / `retract()` construct `CognitionRevisionService` with the derived expected subject only after the target passes validation.
- Target payload subject is verification input only; it no longer grants authorization.

No WorldStore, WorldSearchIndex, Runtime, domain ownership, semantic inference, or constitution/ruling architecture was changed.

## 4. Regression coverage added

Changed test files:

- `tests/integration/test_v3_ai_world.py`
- `tests/integration/test_v3_fused_turn_runtime.py`

Coverage includes:

- User Understanding read isolation.
- Relationship read isolation.
- Strategy read isolation.
- `core_context()` cross-user isolation.
- `snapshot()` cross-user isolation.
- shared Resident Self continuity across User A/User B service contexts.
- shared Resident Calibration continuity across User A/User B service contexts.
- cross-user typed revise rejection for all three user-scoped domains.
- cross-user typed retract rejection for all three user-scoped domains.
- legitimate AI-self Self and Calibration revision from another current-user service context.
- fail-closed malformed typed mutation for `ai_world != True`, missing domain, and invalid domain, for both revise and retract.
- normal FusedTurnRuntime `read_ai_world` cross-user isolation.

## 5. Read / context / snapshot result

On exact candidate `de65572d...`:

- User B sees only User B cognition for User Understanding / Relationship / Strategy.
- User B `core_context()` does not include User A user-scoped cognition.
- User B `snapshot()` does not include User A user-scoped cognition.
- legal `ai_agent_self` Self remains visible across both User A and User B services.

## 6. Revise / retract authorization result

On exact candidate:

- User B cannot revise or retract User A User Understanding / Relationship / Strategy through the typed facade.
- target subject mismatch fails before construction/use of the revision service.
- malformed AI-world metadata fails closed.
- legal AI-self Self / Calibration revisions continue to work.

## 7. AI-self non-regression

The regression suite explicitly proves:

- Self cognition under `ai_agent_self` remains recoverable from both User A and User B service contexts.
- Calibration cognition under `ai_agent_self` remains recoverable from both contexts.
- legitimate Self and Calibration revision still succeeds.

This closes the cross-user leak without incorrectly converting AI-self domains into per-user cognition.

## 8. Targeted Gates

Exact candidate `de65572d...`:

- `p10-ai-world` run `35698883015`: **SUCCESS**, 31 passed.
- `fused-turn-runtime` run `35698882956`: **SUCCESS**, 26 passed.
- `p9-revision-gate` run `35698883322`: **SUCCESS**, 54 passed.
- `p10-ai-world-gate` run `35698883102`: **SUCCESS**.
- `p11-dimension-gate` run `35698882916`: **SUCCESS**.
- `p12-execution-gate` run `35698883026`: **SUCCESS**.
- `constitutional-cognition-closure` run `35698882994`: **SUCCESS**.
- `c14-cognitive-derivation-runtime` run `35698883045`: **SUCCESS**; all component jobs succeeded, including cognition closure, targeted C14 runtime, P15/C13/P14/T28, dimension/index/execution, runtime/wake/turn, P16 habitation and P16 convergence.
- `c14-cognitive-derivation-loop` run `35698882999`: **SUCCESS**; all component jobs succeeded.

## 9. Full regression

- `p16-convergence-gate` run `35698883072`: **SUCCESS**.
- The full `pytest -q` job completed to 100%; the emitted progress contained 431 test dots on this exact candidate.
- Ordinary scoped search, timeline/recommendation/direct-inspect behavior was not modified; related C14 dimension/index/execution and full Core regression remained GREEN.

## 10. Core diff summary

Starting main -> gated candidate:

- `src/aios_core/ai_world/cognition.py`: +25 / -8.
- `tests/integration/test_v3_ai_world.py`: subject-isolation and mutation authorization regressions.
- `tests/integration/test_v3_fused_turn_runtime.py`: real `read_ai_world` runtime isolation regression.
- No second DB.
- No second Runtime.
- No ACL/identity database.
- No change to Strategy ownership semantics.
- No semantic inference added.

## 11. P12 explicitly untouched

`P12 replacement-model identity attestation` remains **INSUFFICIENT_EVIDENCE**.

This task did not:

- add model-name signature fields;
- treat configured/declared model identity as attestation;
- modify provider harness to fabricate identity proof;
- create a model identity database.

R6 must remain non-VALID until a later execution/evidence environment supplies trusted replacement-model identity attestation.

## 12. Completion verdict

All Core acceptance conditions for `C15-RCC-MECH-FIX-001` are satisfied on the exact candidate:

- defect reproduced on starting-main Core;
- read/context/snapshot isolation fixed;
- typed revise/retract fail closed;
- AI-self continuity preserved;
- ordinary scoped paths do not regress;
- targeted Gates GREEN;
- full Core regression GREEN.

The next task may be unlocked only by governance writeback:

`C15-RCC-FIXTURE-001`.
