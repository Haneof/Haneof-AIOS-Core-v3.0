# AIOS v3.0 Code Completeness Re-Audit — 2026-09-20

> Role: independent second-pass constitution/code/runtime completeness review  
> Repository: `Haneof/Haneof-AIOS-Core-v3.0`  
> Audited branch: `main`  
> Latest functional anchor: `8ddb7a606fda375aad98a0b2545a992c2497d828`  
> Latest main at audit start: `1e43f51e555ad423a7b9c2ca5378ddd90c49a405`  
> Governing authority: `docs/constitution/AIOS_v3.0_Fused_Baseline_Registry.md`

## 1. Executive verdict

The prior closure PR #20 genuinely implemented the five gaps that the first constitution/code audit had identified. Its 16 green workflows are valid mechanical/regression evidence.

However, a second independent pass that audits:

- all WorldObject contracts;
- all resident runtime capabilities;
- subject isolation;
- durable identity encoding;
- real P16 Current-Core wiring;
- CognitivePolicy consumption/evaluation;
- multi-scale Summary runtime scheduling;
- Entity/Relation production paths;
- fail-closed storage semantics;
- habitation fixture coverage;

finds that the Core is **not yet code-complete for P17**.

### Re-audit decision

**Architecture spine: PASS**  
**Previously identified PR #20 features: IMPLEMENTED**  
**Code completeness: NOT COMPLETE**  
**P16 real-model readiness: NOT COMPLETE**  
**P17: BLOCKED**

The current project has multiple code blockers in addition to the already-known absence of real-provider cognition artifacts.

---

## 2. BLOCKERS

### B1 — Cross-subject isolation is not enforced across core read/write paths

This is the highest-severity finding.

The unified WorldStore stores `subject_id`, but its generic reference validation checks only:

- object/revision existence;
- knowledge-time visibility;
- self-reference;
- dependency acyclicity.

It does **not** require a referenced object to belong to the same subject as the new object.

Affected write services commonly validate refs with only `store.get_payload(...)`:

- `CognitionWritebackService.commit_claim()`;
- `CognitionRevisionService.apply()`;
- `DimensionRegistryService._validate_refs_exist()`;
- `EventDimensionService._validate_refs()`;
- `GoalTaskActionService._validate_refs_exist()`;
- `CognitivePolicyRegistry._validate_refs()`;
- `CommunicationExperienceService`.

Therefore one subject can form Evidence/Claim/Event/Dimension/Goal/Policy from another subject's pinned world objects if both exist in the same WorldStore.

Read paths also leak subject boundaries:

- `WorldSearchIndex.search_mind()` has no `subject` parameter;
- `FusedTurnRuntime._search_timeline()` calls `search_mind()` without a subject filter;
- `FusedTurnRuntime._focus_entity()` -> `search_by_entity()` -> `search_mind()` without a subject filter;
- `DimensionSummaryService.prepare()` uses `search_mind()` without a subject filter;
- query-less `AllDimensionsProjectionService.project()` uses `search_mind()` without a subject filter.

Consequences in a multi-subject world can include:

- user A seeing user B timeline results;
- user A Summary incorporating user B anchors;
- user A ALL_DIMENSIONS projection including user B world material;
- user A Claim/Policy/Event citing user B Evidence;
- revision propagation crossing subject boundaries.

The projection-side retrospective annotation path is additionally hard-coded to `subject_id="user_1"`.

Existing P6/P7/P8/P11/P12 tests do not include cross-subject cases.

**Required closure:**

1. define the constitutional subject-isolation rule explicitly;
2. enforce it in WorldStore reference validation or an equally universal layer;
3. add `subject` to `search_mind` / `search_by_entity`;
4. make every runtime search/projection/summary path subject-scoped;
5. add cross-subject read/write/propagation regression tests.

---

### B2 — CognitivePolicy is currently a versioned ledger, not an operational adaptive policy system

PR #20 added a valid `CognitivePolicy` WorldObject with:

- version;
- evidence;
- `mutable_by_ai`;
- rollback pointer;
- evaluation window.

But the live system does not yet complete the R6 loop.

#### No resident proposal/registration path

Resident capabilities expose:

- `read_cognitive_policies`;
- `update_cognitive_policy`;
- `rollback_cognitive_policy`.

There is no resident capability to propose/register a new CognitivePolicy.

`CognitivePolicyRegistry.register()` is a system/maintenance API.

#### Real P16 Current-Core starts with no registered policies

`tests/habitation/current_core.py` does not bootstrap CognitivePolicy records.

`run_provider_benchmark.py` creates CurrentCore with provider model + conversation summary handler only.

Therefore a real resident may have update/rollback tools while having nothing to update.

#### Policies are not consumed by runtime behavior

There is no policy resolver that applies active policy values to:

- recommendation candidate count / recall policy;
- search expansion / stopping;
- proactive intervention;
- communication style;
- review cognition strategy;
- dimension evaluation;
- other R6 cognitive choices.

Current behavior remains driven mainly by constructor constants and hard-coded mechanics.

#### Evaluation window has no execution semantics

`evaluation_window` is stored as a nonblank string.

There is no scheduler/cursor that says:

> this policy version is now due for outcome-based evaluation.

Periodic Review's reviewable object types do not include `CognitivePolicy`.

#### AI policy evidence is not restricted to real outcome/feedback

`CognitivePolicyRegistry._validate_refs()` checks existence only.

An AI policy update can therefore cite:

- an AI-authored Claim;
- an AI-authored Summary;
- another subject's object.

This reopens a self-reinforcement path:

`AI Claim -> Policy change -> behavior -> AI Claim`

without the R6-required real-result grounding.

**Required closure:**

- resident policy proposal/candidate path or explicit audited bootstrap policy catalog;
- policy scope resolver;
- actual consumers for policy-controlled cognition behavior;
- real-result evidence boundary;
- policy evaluation scheduler/window;
- Periodic Review policy anchors;
- evaluation -> keep/revise/rollback tests and P16 scenarios.

---

### B3 — Multi-scale Dimension Summary is not wired into the real long-running Current-Core path

`MultiScaleSummaryScheduler` exists and direct tests are green.

But:

- `CurrentCoreHabitationTarget` has no `dimension_summary_handler`;
- it constructs `FusedTurnRuntime` without one;
- `advance_to()` processes Task wakes and Periodic Review, but never calls `run_due_dimension_summaries()`;
- `run_provider_benchmark.py` supplies provider summary handler only as the P14 conversation `round_summary_handler`.

Therefore real P16 habitation does **not** use the P6 multi-scale world summary mechanism.

#### Missed-window/backlog problem

`MultiScaleSummaryScheduler.run_due(now)` evaluates only one `previous_closed_window` per scale.

If the system is offline for many daily/weekly windows, there is no durable cursor/backlog drain that reconstructs all missed windows.

#### Truncation can produce incomplete CURRENT summaries

`DimensionSummaryService.prepare()` fetches at most `max_source_objects + 1`, then keeps the first `max_source_objects`.

It records `truncated=True`, but still commits a CURRENT Summary.

There is no paging/drain protocol analogous to the P15 review backlog hardening.

#### Late facts in historical windows

A late-arriving Observation for an older closed window does not automatically schedule rebuild of that old Summary because the scheduler only targets the immediately previous window.

#### "active_dimensions" includes non-active lifecycle states

`MultiScaleSummaryScheduler.active_dimensions()` adds DimensionDefinition keys without checking lifecycle.

Candidate / Rejected / Archived definitions can therefore remain scheduled for summary maintenance.

**Required closure:**

- integrate P6 scheduler into Current-Core virtual/runtime scheduler;
- provider-backed dimension-summary handler;
- durable per-scale cursor/backlog;
- source paging/completeness semantics;
- late-data rebuild invalidation;
- lifecycle-aware active dimension selection;
- P16 fixture coverage for day/week/month+ transitions.

---

## 3. HIGH findings

### H1 — Topic State / Need-History remains over-deterministic and constitutionally partial

`TopicStateService` uses hard-coded:

- social-only vocabulary;
- continuation cues;
- history cues;
- `len(topic) >= 4` as sufficient to set `history_may_help=True`.

The constitution says:

> topic exists does not mean history is needed.

Current implementation mechanically opens history for almost any nontrivial utterance.

Topic sources required by the constitution include:

- person/entity;
- event;
- project;
- task;
- time range;
- continuing previous topic.

Current service mainly sees current text + recent same-session user text + optional explicit topic.

There is no durable topic state/decay model beyond recent-turn continuity.

The current-turn ordering itself is correct: `run_turn()` calls continuity with `before_turn=turn_index`, so the incomplete current turn is excluded. The gap is the topic/history decision quality, not self-reference.

**Required closure:** make deterministic code provide topic signals, but let a bounded policy/model mechanism decide history usefulness; add topic switch/decay/entity/task/time false-positive tests.

---

### H2 — Entity / Relation infrastructure is operationally inert

Contracts and index support `Entity` and `Relation`.

Runtime exposes:

- `focus_entity`;
- `follow_relation`.

But accepted production services do not provide resident write paths for:

- create/upsert/merge Entity;
- create/revise Relation.

No main runtime capability such as `form_entity`, `upsert_entity`, `form_relation`, or `revise_relation` exists.

Current entity/relation behavior is mostly demonstrated by manually seeded index fixtures.

Consequences:

- people/entities do not naturally become canonical world anchors;
- alias disambiguation cannot grow from real life;
- relationship graph navigation is mostly dormant;
- the index constitution's person/event/relation navigation examples are not end-to-end operational.

Typed relationship-understanding Claims in AI World are useful, but they do not replace explicit Entity/Relation world anchors.

---

### H3 — Stable identity encoding remains collision-prone in several core modules

P13 Reality ingest was hardened to use structured canonical JSON before hashing.

Several other modules still use:

`"|".join(str(part) for part in parts)`

Confirmed:

- `src/aios_core/writeback/cognition.py`;
- `src/aios_core/revision/service.py`;
- `src/aios_core/dimensions/registry.py`;
- `src/aios_core/execution/service.py`;
- `src/aios_core/summaries/dimension_summary.py`.

These IDs include free text, metadata, payloads, dimension keys and other compound values.

Delimiter-boundary ambiguity can alias logically different identities and idempotency keys.

**Required closure:** one canonical stable-ID helper for all Core modules, based on `canonical_json_dumps(list(parts))`, with collision-boundary regression tests.

---

### H4 — Core truth paths still swallow storage failures with broad `except Exception`

Examples:

#### Cognition writeback

`CognitionWritebackService.commit_claim()` treats any `get_payload` exception as "Claim does not exist".

A storage/database failure can therefore become an attempted new write rather than fail closed.

#### Dimension Summary

`DimensionSummaryService.commit()` treats any lookup exception as "no existing Summary".

#### Proactive recommendation

A failure reading a recalled world object is silently skipped, producing an apparently valid but incomplete memory bundle.

#### ALL_DIMENSIONS

A broad read exception is converted into a projection fallback intended for projection-only annotations, so a real WorldStore failure can masquerade as a non-world annotation case.

#### WorldSearchIndex

Several annotation/current-view paths swallow broad exceptions; the retrospective annotation adapter is especially permissive.

The Policy service already uses the correct narrow pattern:

`StoreError + ErrorCode.NOT_FOUND`.

**Required closure:** standardize fail-closed durable reads and only special-case exact expected NOT_FOUND/projection-annotation conditions.

---

### H5 — Event lifecycle has no actual transition matrix

`EventDimensionService` claims to enforce legal forward lifecycle transitions.

Current code enforces:

- current revision only;
- pinned evidence;
- MERGED target;
- SPLIT children;
- REVISED replacement text.

It does not enforce previous-status -> next-status legality.

Potentially legal by current code:

- REJECTED -> ACTIVE;
- MERGED -> CANDIDATE;
- RESOLVED -> ACTIVE;
- SPLIT -> REVISED.

The Event contract enforces status-specific fields, not transition legality.

**Required closure:** define the canonical Event transition graph and deterministic tests, or explicitly declare Event status revisions unrestricted if that is the intended constitution.

---

## 4. MEDIUM findings / incomplete surfaces

### M1 — Intelligent World Index is a strong lexical substrate, not yet the full navigation constitution

Implemented:

- rebuildable projection;
- CJK/ASCII lexical postings;
- exact entity alias resolution if Entity objects exist;
- dimension/time/type filters;
- current-view filtering;
- entity/timeline helpers;
- one-hop Relation follow through runtime.

Not complete:

- unified structured search request/planner;
- explicit quick/deep strategy selection;
- bounded multi-hop graph expansion;
- summary-tree coarse-to-fine navigation;
- anchor response with explicit source/current-validity/drill-down route;
- semantic/vector route (optional constitutionally, so not a blocker by itself).

This should be described as a complete **foundation**, not a fully realized "intelligent search planner".

---

### M2 — Multiple WorldObject contracts remain orphaned or future-only

Current canonical contracts include, among others:

- ToolProposal;
- Prediction;
- LifeChapter;
- Reinterpretation;
- NarrativeSegment;
- DimensionCurvePoint;
- BudgetPolicy;
- AssemblyPolicy;
- Session.

There is no complete resident write/read lifecycle for several of these in the current fused runtime.

Some may be intentionally retained legacy contracts or future P17/P18 work.

The governance problem is that the Master Map does not clearly mark which are:

- active required Core mechanisms;
- compatibility contracts;
- deferred mechanisms;
- deprecated leftovers.

This creates false completeness ambiguity.

---

### M3 — Retrospective annotation projection is hard-coded to user_1

`WorldSearchIndex._catch_up_annotations()` inserts annotation search rows with:

`subject_id="user_1"`

and emits `MindSearchHit(... subject_id="user_1")`.

If the legacy `retrospective_annotations` table is present in a non-default/multi-subject world, subject provenance is wrong.

This compounds B1.

---

## 5. P16 completeness audit

Current real-provider manual workflow offers four sealed-life manifests:

1. `learning_independence_v1` — 5 events;
2. `cross_session_continuity_v1` — 4 events;
3. `cognition_revision_v1` — 4 events;
4. `uncertainty_restraint_v1` — 4 events.

They are useful for:

- cross-session continuity;
- sparse-evidence restraint;
- forward cognition revision;
- broad long-horizon mechanics.

They do not currently exercise the full newly claimed cognition system:

- Event formation + revise/merge/split lifecycle;
- CognitivePolicy proposal/activation/evaluation/rollback;
- CommunicationExperience accumulation and downstream use;
- P6 multi-scale world Summary;
- Entity creation/alias resolution/Relation graph;
- dynamic Dimension candidate -> trial -> active -> reject/archive/merge/split;
- sustained Goal/Task/Action/Outcome learning with real resident decisions;
- policy/experience effects after process restart/model handoff.

The fixtures contain only 4-5 explicit resident events each and span weeks to roughly two months.

Therefore even after provider secrets are configured, these four current fixtures are insufficient to claim:

> complete AIOS cognition has been empirically validated.

P16 needs broader sealed-life suites after the Core blockers above are closed.

---

## 6. What remains genuinely strong

This re-audit does **not** invalidate the current architecture spine.

Still strong:

- one canonical WorldStore;
- append-forward revisions;
- global world revision;
- Observation / Claim / Summary separation;
- EvidenceSet + Dependency;
- Claim revise/retract + propagation;
- ALL_DIMENSIONS causal boundary;
- dynamic dimension lifecycle concept;
- Goal/Task/Action/Outcome authorization model;
- Reality ingest mechanical boundary;
- Conversation raw-history continuity;
- Wake -> Step-0 -> same CognitiveRuntime;
- Periodic Review reuse of same resident runtime;
- OperationExperience real-result hardening;
- provider/oracle isolation;
- restart/model-handoff mechanics;
- evaluator provenance;
- no second AI cognition database.

The issue is not architectural collapse. It is that several layers are **mechanisms without full production orchestration or universal isolation/error invariants**.

---

## 7. Gate interpretation

The 16 SUCCESS workflows on PR #20 remain valid evidence that:

- the implemented interfaces compile/run;
- existing deterministic invariants stay green;
- the new PR #20 mechanisms did not break known regressions.

They do **not** prove the newly found failure modes because current tests do not cover them.

Notably absent from the relevant Gate suites:

- cross-subject read/write isolation;
- cross-subject revision propagation;
- stable-ID delimiter collision;
- policy real-result evidence;
- policy evaluation-window lifecycle;
- policy-to-runtime behavior application;
- dimension-summary backlog/restart/late data;
- dimension-summary > source-cap completeness;
- P16 multi-scale Summary integration;
- Entity/Relation resident writeback;
- Event transition legality;
- topic decay/history false-positive cases.

Green CI and incomplete coverage can both be true.

---

## 8. Required closure order

Recommended engineering order before any paid P16 cognition run is used as release evidence:

### Phase C1 — World isolation / correctness hardening

1. subject isolation at universal reference layer;
2. subject-scoped `search_mind` / entity / timeline / Summary / ALL_DIMENSIONS;
3. canonical stable ID helper everywhere;
4. replace truth-path broad exception handling with fail-closed StoreError semantics.

### Phase C2 — Complete live cognition mechanisms

5. make CognitivePolicy operational:
   - policy registration/proposal;
   - real-result evidence;
   - resolver/consumers;
   - evaluation scheduling;
   - Periodic Review integration;
6. wire MultiScaleSummaryScheduler into Current-Core / long-running scheduler;
7. durable Summary backlog + late-data invalidation;
8. Entity / Relation resident lifecycle;
9. Event transition state machine;
10. finish Topic State / Need-History orchestration.

### Phase C3 — Expand P16

11. add sealed lives specifically covering:
    - policy learning/rollback;
    - communication learning;
    - event lifecycle;
    - entity/relation;
    - dimension lifecycle;
    - multi-scale Summary;
    - real Goal/Action/Outcome;
    - restart/model handoff after learned state;
12. then run at least two real providers independently;
13. separate oracle evaluation + red-team.

---

## 9. Final verdict

The statement:

> "The only remaining blocker is real-provider P16 evidence"

is **no longer accurate** after this second-pass audit.

Current accurate state:

- **constitution architecture direction:** PASS;
- **core world/cognition spine:** STRONG;
- **PR #20 feature implementation:** REAL / not fake;
- **code completeness for P17:** FAIL;
- **subject isolation:** BLOCKER;
- **Adaptive CognitivePolicy operational loop:** BLOCKER;
- **P6 multi-scale Summary real-runtime integration/completeness:** BLOCKER;
- **identity/error hardening:** HIGH;
- **Entity/Relation operational completeness:** HIGH;
- **P16 coverage:** INSUFFICIENT for whole-system cognition claim;
- **P17:** NOT READY.

This re-audit supersedes the narrower statement in
`reviews/AIOS_V3_CONSTITUTION_CODE_ALIGNMENT_CLOSURE_2026-09-20.md`
that all code-side blockers had been closed. That report remains historically accurate
for the first audit's enumerated findings, but it was not a full second-order
completeness proof.
