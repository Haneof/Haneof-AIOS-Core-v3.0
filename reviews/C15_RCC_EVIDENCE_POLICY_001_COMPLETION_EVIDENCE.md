# C15-RCC-EVIDENCE-POLICY-001 — Completion Evidence

Date: 2026-09-23

Task ID: `C15-RCC-EVIDENCE-POLICY-001`

Purpose: Unify long-term cognition evidence support closure across ordinary user
turns, Periodic Review, Cognitive Derivation, and direct cognition service
invocation behind one mechanical policy layer.

Origin: `governance/C15_RCC_COGNITION_HARDENING_ROADMAP_2026-09-22.md`
(`Status: PLANNED`). This document records implementation evidence only. It does
not itself authorize merge; sequencing against the board remains a PM decision
(see §7).

---

## 1. Baseline

| Item | Value |
|---|---|
| Starting `main` | `e534378572e886f76071ac0dcf59a9a1a4798bb9` |
| Required predecessor | `C15-RCC-COG-FIX-001` (PR #108) merged at `c146cebbdfa8ac714fc236652a4452c60bcfa0bb` — confirmed present |
| First candidate | PR #110 head `34c6810a107e7d6e25ca73e80cab2c5a1a622e4a` |
| Independent review verdict on that candidate | `REQUEST_CHANGES` (2 BLOCKER, 3 MAJOR, 2 MINOR) |
| Working branch | `arena/01a0ca2d-haneof-aios-core-v3-0` |

This work is the remediation of the first candidate. No merge was performed.

---

## 2. Semantic decision — EventAnchor grounding

### 2.1 Question

Is `ObjectType.EVENT` (`EventAnchor`) a legal cognition grounding container?

### 2.2 Facts established from current Core

- `EventAnchor` is committed with `source_class=AI_COGNITION`
  (`src/aios_core/events/service.py:288`), because the resident AI authors its
  `title` and `interpretation`.
- `EventAnchor` **cannot be created without pinned evidence**:
  `EventWriteRequest.evidence_refs` is `Field(min_length=1)` and every ref must be
  pinned (`src/aios_core/events/service.py:71-93`).
- Those refs are persisted as real support edges: `event_uses_evidence_set` and
  `event_evidence_set_contains_source` (`src/aios_core/events/service.py:204-238`).
- Before this task, `Observation -> Event -> Claim` was a **legal, working** path
  on `main` for ordinary user turns.

### 2.3 Ruling

**`EventAnchor` IS a legal case grounding container**, in the same category as
`OPERATION_EXPERIENCE` and `COMMUNICATION_EXPERIENCE`.

Rationale: an EventAnchor *carries* provenance toward reality rather than
asserting an unsupported new fact. It cannot exist without pinned evidence, so
admitting it as a case container cannot manufacture support that does not exist.

### 2.4 Scope limits of the ruling — what it does NOT grant

This ruling is deliberately narrow. Membership in `_CASE_GROUNDING_CONTAINERS`:

- does **not** make an EventAnchor a grounding leaf. It is still recorded as an
  `AI_COGNITION` atomic source, still sets `has_ai_cognition=True`, and is
  **never** added to `grounding_leaf_refs`;
- only removes it as a grounding *barrier*, so traversal continues into the real
  `USER` / `SENSOR` / `PLATFORM` / `SAFETY` leaves underneath it;
- does **not** let Event prose terminate proof. An Event whose own lineage bottoms
  out in AI cognition still fails closed.

This preserves the C14 rule that a navigational or compressing container may not
terminate proof, while keeping the pre-existing legal path formable.

### 2.5 Implementation

- `src/aios_core/policy/evidence.py`: `ObjectType.EVENT` added to
  `_CASE_GROUNDING_CONTAINERS`, with the full rationale and scope limits recorded
  inline at the definition site.
- `src/aios_core/policy/evidence.py`: `event_uses_evidence_set` and
  `event_evidence_set_contains_source` added to `_SUPPORT_DEPENDENCY_TYPES`, which
  were missing, so the Event's own support edges are now traversed.

Both the positive and the anti-laundering negative control are tested (§5).

---

## 3. Before reproduction / after fix

### 3.1 BLOCKER 1 — EventAnchor over-tightening

Identical probe script on both trees: real `USER` Observation →
`EventDimensionService.form_event` → `commit_claim` on the pinned Event ref
through `FusedTurnRuntime.run_turn`.

| Tree | Result |
|---|---|
| `origin/main` @ `e534378` | `ok= True` — legal path forms |
| PR #110 head @ `34c6810` (before) | `ok= False` — `ValueError: Cognition evidence policy (leaf-grounded evidence closure rejected) commit_claim: classification=MIXED; grounding_leaf_count=0; unresolved_count=0; issues=none` |
| This branch (after) | `ok= True` — legal path restored, closure still enforced |

Confirmed regression against `main`, now fixed. Policy-level before/after:
`derive_lineage_for_refs([event_ref])` returned `MIXED, grounding=0` before, and
returns `MIXED, grounding=1` after, with the Observation — not the Event — as the
grounding leaf.

### 3.2 BLOCKER 2 — behaviour change hidden by a test selector

The first candidate added a `metadata.role != "assistant"` filter to
`tests/habitation/test_current_core_target.py`, which silently masked a real
rejection.

- Before: reverting only that one-line filter produced
  `FAILED test_current_core_targets_are_real_world_isolated` —
  `ValueError: ... cognition_writeback.commit_claim: classification=AI_COGNITION_ONLY; grounding_leaf_count=0`.
- Investigation: the first Observation in that snapshot is the **assistant-role**
  turn (`obs_conv_ai_*`, `metadata.role == "assistant"`). Rejecting a Claim
  grounded solely on AI speech is the **intended** C14/C15 anti-self-proof rule,
  not a regression.
- After: the selector filter is **removed**. The test now asserts the rejection
  explicitly with `pytest.raises(..., match="leaf-grounded evidence closure rejected")`
  and separately proves the isolation property under test using real `USER`
  evidence. The behaviour change is recorded, not hidden.

### 3.3 MAJOR 3 — structural unification

Before: `evidence_policy` defaulted to `None` on all three services and each
enforcement site was wrapped in `if self.evidence_policy is not None:`, so any
construction outside `FusedTurnRuntime` silently bypassed the policy.

After: all three services build an equivalent policy when none is injected, and
both `is not None` guards are deleted. Enforcement is now unconditional.

| Service | Default policy | Allowed subjects |
|---|---|---|
| `CognitionWritebackService` | constructed | `self.evidence_subject_ids` |
| `CognitionRevisionService` | constructed | `self.evidence_subject_ids` |
| `AIWorldCognitionService` | constructed | `(user_id, ai_subject_id)` |

Injection is still supported so `FusedTurnRuntime` shares one resolver instance;
omission no longer disables enforcement.

Ordering note: in both writeback and revision the **subject-isolation check now
runs before** the policy check, so cross-user refs keep reporting the precise
isolation violation (`"...crosses the allowed subject scope"`) rather than a
generic closure failure. This preserves `C15-RCC-MECH-FIX-001` error semantics.

### 3.4 Pre-existing tests exposed by closing the bypass

Closing the `None` bypass made six previously-bypassing tests enforce for the
first time. Each was inspected individually; **none** was silenced by weakening
the policy.

| Test | Cause | Resolution |
|---|---|---|
| `test_v3_ai_world.py::test_all_ai_domains_share_one_world_store_without_second_ai_database` | Self Claim grounded **only** on two other Claims — a real `Claim -> Claim` self-proof | Real user Observation pinned alongside the two Claims. The cross-domain single-store property under test is unchanged. |
| `test_v3_cognition_revision.py` (4 tests, shared `_seed_world`) | Dependent Claim `b` grounded **only** on Claim `a` | Real Observation pinned alongside Claim `a`. The `Claim -> Claim` dependency edge these tests exercise is preserved exactly, so revision/propagation semantics are unchanged. |
| `test_v3_cognition_revision.py::test_stale_dependent_can_be_re_evaluated_into_new_active_revision` | Re-evaluation grounded only on revised upstream Claim | Correcting Observation pinned alongside. |
| `test_v3_completeness_closure.py::test_subject_scoped_search_and_cognition_block_cross_user_refs` | Expected the subject-scope error, got the closure error | Fixed in Core by ordering the subject check first (§3.3), not by changing the test. |

In every case the fix adds the **real reality leaf that was always conceptually
behind the assertion**, and each edit carries an inline comment naming this task.
No assertion was deleted and no expected-failure was converted to an
expected-pass.

---

## 4. Unification matrix — one rule, all entrypoints

| Entrypoint | Path | Enforced by |
|---|---|---|
| Ordinary user turn | `FusedTurnRuntime.run_turn` → `commit_claim` / `commit_ai_world_claim` / `revise_claim` / `retract_claim` | `_validate_cognition_evidence` → `CognitionEvidencePolicy.validate` |
| Periodic Review | `FusedTurnRuntime.run_periodic_review` → same four capabilities | same |
| Cognitive Derivation | `WakeSource.COGNITIVE_DERIVATION` → same four capabilities | same |
| Direct service invocation | `CognitionWritebackService` / `CognitionRevisionService` / `AIWorldCognitionService` constructed anywhere | structurally-defaulted policy, no bypass |
| C14 scheduler routing | `CognitiveDerivationScheduler.derive_lineage_for_refs` | delegates to the same `CognitionEvidencePolicy` |

There is exactly one traversal implementation. The previous duplicate resolver in
`src/aios_core/summaries/cognitive_derivation.py` was removed and the scheduler
now delegates; a function-level diff against `origin/main` confirmed only renames
and one `else:` → `continue` refactor, with no algorithmic drift.

Prior behaviour, for the record: on `main` the leaf-grounding check ran **only**
under `COGNITIVE_DERIVATION`. Ordinary turns and Periodic Review had no such gate.
Extending it to those entrypoints is the intended substance of this task.

---

## 5. Test coverage added

`tests/integration/test_v3_c15_cognition_evidence_policy.py` — 16 tests (9 from
the first candidate, 7 added here).

Legal-path positive controls, one per evidence object type:

| Test | Asserts |
|---|---|
| `test_observation_is_a_legal_grounding_path` | `REALITY`; Observation is the grounding leaf; Claim forms |
| `test_action_is_a_legal_grounding_path` | `REALITY`; grounding closes; Claim forms |
| `test_outcome_is_a_legal_grounding_path` | `REALITY`; PLATFORM Outcome is itself a qualifying leaf; `has_ai_cognition is False`; Claim forms |
| `test_event_anchor_is_a_legal_case_grounding_container` | `MIXED`; `has_ai_cognition is True`; Observation **is** a grounding leaf; Event is **not**; Claim forms |

Negative / structural controls:

| Test | Asserts |
|---|---|
| `test_event_anchor_over_ai_only_lineage_still_fails_closed` | Event built on an ungrounded Claim→Summary cannot launder grounding — rejected |
| `test_event_grounded_cognition_forms_on_an_ordinary_user_turn` | End-to-end through `run_turn`, not just the policy object — the exact BLOCKER 1 regression |
| `test_services_enforce_policy_without_explicit_injection` | All three services reject ungrounded evidence with **no** `evidence_policy` argument — the exact MAJOR 3 bypass |

Retained from the first candidate: reality-observation acceptance, direct
`Claim -> Claim` rejection, `Claim -> Summary -> Claim` cycle rejection,
`Observation -> Summary -> Claim` acceptance, chained-ungrounded-summary
rejection, ordinary-turn enforcement, revision-requires-new-reality,
Periodic Review closure, direct-service enforcement.

Anti-freeze / revisability confirmed preserved: `Observation -> Claim ->
revise-with-new-Observation` still forms, and the `test_v3_cognition_revision.py`
suite (stale propagation, re-evaluation into a new active revision, tombstone
retraction, summary rebuild) is green, so C15 §15.3 revisability and R8 later
correction are not frozen by the policy.

---

## 6. Gate results

Environment: Python 3.12 target; local run on CPython with `pydantic 2.13.5`.

| Gate | Result |
|---|---|
| `tests/integration/test_v3_c15_cognition_evidence_policy.py` | **16 passed** |
| Full suite `pytest tests` | **452 passed, 0 failed** |
| Full suite on first candidate (for comparison) | 469 passed — count differs because this branch does not add the habitation selector filter and adds 7 tests; no test was deleted |

New required gate added: `.github/workflows/c15-cognition-evidence-policy.yml`,
covering the C15 policy suite plus the four cognition-entrypoint regression files
(`cognition_writeback`, `cognition_revision`, `ai_world`,
`habitation/test_current_core_target`), triggered on any change to
`src/aios_core/policy/**`, the three cognition services, the derivation scheduler,
or the turn runtime. The first candidate added no workflow, so its new suite was
not a required gate for future PRs.

Minor cleanups also applied: UTF-8 BOM removed from `policy/evidence.py`; dead
`SummaryStatus` import removed from `policy/evidence.py`; dead
`DerivedLineageClass` import removed from `turn_runtime.py`; the misleading
`_validate_c14_cognition_grounding` name and its bare class-body alias replaced by
the single unified name `_validate_cognition_evidence` at all four call sites.

---

## 7. Scope and boundaries

This work did **not**:

- modify the constitution or the Fused Baseline Registry;
- create a second cognition database, provenance store, or scheduler;
- change the `Claim` model or the unified `WorldStore`;
- touch any C15 fixture, Resident A/B/C artifact, or PR #101;
- run a Resident;
- merge anything.

C14/C15 semantics verified preserved: Claim is not fact; `Claim -> Claim` is
rejected; `Claim -> Summary -> Claim` is rejected; AI self-description cannot
prove itself (`metadata.role == "assistant"` maps mechanically to
`AI_COGNITION`, unknown role fails closed); `lineage_cycle` detection intact. No
prose, keyword, occurrence count, confidence score, or expected answer
participates anywhere in the resolver.

### Open PM decision — sequencing

`governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md` lists
`C15-RCC-RES-A-RERUN-001` (row 29.4) as the first `READY` task;
`C15-RCC-EVIDENCE-POLICY-001` is `PLANNED` in the roadmap, which states it does
not authorize implementation by itself, and the frozen execution order places
`C15-RCC-HARDEN-001` next.

This change alters Resident-visible cognition-formation semantics on ordinary
turns and Periodic Review. Per `C15-RCC-RES-A-REPAIR-DECISION-001`, a Core change
of this kind invalidated PR #101 and forced `PATH B = REQUIRED`. Merging it
**before** the canonical Resident A rerun risks the same invalidation; merging it
**after** risks A/B/C running on different Core semantics.

That ordering is explicitly **not** decided here. A board row and a PM sequencing
ruling are required before merge.
