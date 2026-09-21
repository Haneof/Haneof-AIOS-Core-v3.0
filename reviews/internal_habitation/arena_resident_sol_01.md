# AIOS 3.0 P16 Independent Resident Habitation Report

**Review Branch**: `arena/01a0c1df-haneof-aios-core-v3-0`  
**Reviewer / Logical Resident ID**: `resident:arena_reviewer_sol` (Arena.ai Native Large Model)  
**Base Main SHA Tested**: `142533df9123d793edde9ec4f07405182d56af0d`  
**Authority**: `reviews/internal_habitation/ARENA_RESIDENT_YEARLONG_TASK.md`, `governance/P16_INTERNAL_MODEL_HABITATION_REVIEW_PROTOCOL.md`  
**Report Date**: 2026-09-21  

---

## 1. Executive Summary & Attestation

### 1.1 Resident Cognition Attestation
> **Resident cognition attestation**: I did personally act as the Resident model for the semantic checkpoints in this run. Deterministic code was not used to replace semantic Resident decisions. All understanding, recall interpretation, policy proposal, Goal proposal, and cognition synthesis were rendered directly from the visible RuntimeSnapshot by the model during the chronological timeline.

### 1.2 Truthful Progress Summary
- **Simulated Life Range**: 2026-01-01T08:00:00+00:00 to 2026-01-21T23:59:59+00:00
- **Total Simulated Days**: **21 consecutive days** (Segment 001 frozen checkpoint)
- **Total Observable Events**: 23 (including dialogue, lab telemetry, cleanroom numeric time-series, photos, logistics, payments, announcements, decoy isolation probes)
- **Resident Cognition Checkpoints**: 28 distinct model invocations (11 conversational user turns, 10 periodic review wakes, multi-round tool loops)
- **Active / Completed Wakes**: 10 periodic review wakes completed cleanly
- **World Revision Watermark**: Revision 72, search index watermark 72
- **Durable Checkpoint**: `reviews/internal_habitation/arena_resident_sol_01/checkpoint.json`

---

## 2. Unique Life Design (千人千面)

To guarantee complete independence and prevent reviewer groupthink, a distinct persona was constructed:

- **Subject Identity**: Dr. Lin Jiang (江林), Lead Researcher at the Brain-Machine Interface & Neuromorphic Computing Laboratory, Hangzhou.
- **Core Project**: "灵境突触" (Synapse-Nexus) — Neuromorphic spike array and bio-inspired retinal visual coding.
- **Team Collaborators**:
  - **陈潇 (Chen Xiao)**: Research assistant responsible for physical wafer probe station testing and neuromorphic chip packaging.
  - **苏蒙 (Su Meng)**: Research assistant responsible for retinal spike coding algorithms and event-camera data processing.
- **Decoy Subject**: Dr. Fan Yu (樊宇), Lead Researcher at Shanghai Brain Intelligence Institute (audited for subject isolation).
- **Behavioral & Interaction Rhythms**:
  - Direct, concise academic communication style: requires conclusions first, bullet points, strict distinction between facts, inferences, and uncertainties.
  - Strict espresso habit: double espresso, dark roast, zero dairy/sugar, morning and post-lunch.
  - Realistic laboratory events: probe station vacuum/temperature telemetry, ISO cleanroom numeric time series, wafer batch logistics, oscilloscope probe procurement invoices, campus fire drill noise, and commercial marketing coupon noise.

---

## 3. Findings & Discoveries

During 21 days of continuous habitation on the real AIOS Core runtime (`src/aios_core/**`), 3 major architectural and mechanism defects were identified under authentic model usage:

### Finding 1: `CognitionRevisionService` and `search_world` Break on AI-World Self-Domain Cognitions (`ai_agent_self` Scope Mismatch)
- **Severity**: **HIGH / ARCHITECTURAL GAP**
- **Classification**: **BUG / MECHANISM GAP**
- **Impacted Components**:
  - `src/aios_core/runtime/turn_runtime.py` (`_search_world`, `_revise_claim`, `_retract_claim`)
  - `src/aios_core/revision/service.py` (`CognitionRevisionService.apply`)
- **Description**:
  When a resident AI records an inference or self-reflection using `commit_ai_world_claim(domain="self" | "intent" | "personality", ...)` or `commit_claim`, AIOS assigns the claim `subject_id = "ai_agent_self"` (via `AI_SELF_SUBJECT_ID`). However:
  1. In `turn_runtime.py`, `_search_world` delegates to `self.index.recall_candidates(query, subject=self.subject_id)`. Because `self.subject_id` is `"user_lin_jiang"`, the recall index excludes all `ai_agent_self` claims (e.g. `clm_8d7bc7cdef21f6ee2889c811`).
  2. When the resident attempts to revise or retract this claim using `revise_claim`, `self.revision` is instantiated with `subject_id = self.subject_id ("user_lin_jiang")`. `CognitionRevisionService.apply` validates `target.subject_id == self.subject_id`, raising `ValueError: revision target crosses the runtime subject scope: 'ai_agent_self' != 'user_lin_jiang'`.
- **Minimal Reproduction**:
  1. Commit an AI-world claim under `domain="self"`. It is persisted with `subject_id="ai_agent_self"`.
  2. Call capability `revise_claim(target_ref={"object_id": claim_id, "revision": 1}, ...)`.
  3. Runtime crashes with `ValueError: revision target crosses the runtime subject scope`.
- **Suggested Resolution**:
  `CognitionRevisionService` should accept `allowed_subject_ids` (matching `turn_runtime._runtime_subject_scope()`), and `_search_world` should query both the user subject and `ai_agent_self` for resident self-knowledge.

---

### Finding 2: `TaskCreateRequest.task_type` Rejects Domain Task Types via Strict Closed Enum
- **Severity**: **MEDIUM**
- **Classification**: **MECHANISM GAP**
- **Impacted Components**:
  - `src/aios_core/execution/service.py` (`TaskCreateRequest`)
  - `src/aios_core/contracts/enums.py` (`TaskType`)
- **Description**:
  In `turn_runtime.py`, the `create_task` capability documentation advertises `task_type: "string"`. When the resident AI naturally creates an operational task reflecting user requests (e.g., `task_type="hardware_debugging"`), Pydantic validation rejects it with:
  `Input should be 'immediate', 'scheduled', 'deadline', 'todo', 'recurring', 'follow_up', 'observation', 'verification', 'maintenance' or 'app'`.
  The capability schema mislead the resident model by accepting arbitrary strings, while the internal contract strictly enforced workflow schedule classifications rather than semantic task categories.
- **Suggested Resolution**:
  Decouple workflow execution types (`schedule_type` / `cadence`) from semantic domain tags (`category` / `task_type`), or expose the exact enum choices in `create_task` capability catalog.

---

### Finding 3: `EntityProposalRequest.entity_key` Requires Undocumented Prefix `entity:`
- **Severity**: **MEDIUM**
- **Classification**: **MECHANISM GAP**
- **Impacted Components**:
  - `src/aios_core/world_graph.py` (`EntityProposalRequest`)
  - `src/aios_core/runtime/turn_runtime.py` (`_propose_entity` capability schema)
- **Description**:
  The capability catalog describes `entity_key` as `"string"`. When the resident AI generates structured semantic keys like `person:chen_xiao` or `project:synapse_nexus`, the Pydantic validator throws: `Value error, entity_key must start with 'entity:'`.
- **Suggested Resolution**:
  Either document `entity:<kind>:<id>` explicitly in the capability catalog, or normalize the prefix automatically inside `turn_runtime._propose_entity`.

---

## 4. Validated Invariants & Positive Findings

During the 21 days of operation, the following Core subsystems operated reliably without violation:
1. **Periodic Review Scheduler & Wake Lifecycle**:
   - `advance_to` correctly computed background periodic review intervals (48h cadence).
   - 10 periodic review wakes were automatically dispatched, processed, claimed, and transitioned (`new` -> `running` -> `completed`) without hanging.
2. **Cognitive Policy Proposal & Reflection**:
   - The resident model learned communication policies directly from user feedback (`communication.style_preference`), persisted them, and verified they appeared in future cockpit contexts.
3. **Decoy Subject Isolation**:
   - Decoy events injected into platform logs for `decoy_dr_fan` remained completely unlinked from `user_lin_jiang`'s recall index.
4. **World Commits & Index Watermark Synchronization**:
   - 72 atomic commits were executed on SQLiteWorldStore and immediately synchronized to SQLite FTS index without corruption or drift.

---

## 5. Segment Checkpoint & Artifact Audit

All evidence artifacts are preserved on this branch:
- **Segment 001 Run Directory**: `reviews/internal_habitation/arena_resident_sol_01/segments/segment_001/`
- **World Database**: `reviews/internal_habitation/arena_resident_sol_01/segments/segment_001/world_segment_001.sqlite`
- **Cognitive Trace Ledger**: `reviews/internal_habitation/arena_resident_sol_01/segments/segment_001/cognition_traces.jsonl`
- **Master Checkpoint Manifest**: `reviews/internal_habitation/arena_resident_sol_01/checkpoint.json`

### Continuation Pointer
To resume Segment 002 (Day 22–45):
- Restore from `world_segment_001.sqlite` with `require_fresh=False`.
- Start cursor at `2026-01-21T23:59:59+00:00` (World revision 72).
