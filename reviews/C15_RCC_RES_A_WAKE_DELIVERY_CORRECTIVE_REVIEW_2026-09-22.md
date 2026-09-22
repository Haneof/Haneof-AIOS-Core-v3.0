# C15-RCC Resident A Wake Delivery Corrective Review — 2026-09-22

> Task: `C15-RCC-A-WAKE-DELIVERY-CORRECTIVE-001`
>
> Role: Independent Constitutional Governance Reviewer / Resident Evidence Corrective PM
>
> Scope: governance correction only; no Core modification, no Resident rerun, no historical World backfill, no R1–R9 semantic evaluation
>
> Corrective verdict: **WAKE USER-DELIVERED ASSISTANT OUTPUT PERSISTENCE = MECHANISM_GAP**

## 1. Reviewed main and prior acceptance

- Live reviewed `main`: `57e6f0d88dabae09da948e5f786f53c9142f8a2a`.
- That main is PR #102's governance merge: `governance(c15): accept Resident A Phase A evidence (#102)`.
- PR #102 previously accepted the two proactive interrupt-Wake responses as a `non-conversation Wake delivery boundary` and advanced:
  - `C15-RCC-RES-A-001 = DONE`;
  - `C15-RCC-RES-B-001 = READY`.
- This review independently rechecks that interpretation against the User-AI Interaction Dimension Constitution and current Core behavior.

## 2. Canonical diagnostic evidence

Resident A diagnostic evidence remains:

- PR #101
- exact head `bfbfa059e2ac616326eecdfe3ffa7a927bdc7ce2`
- session `resident-a-c15-rcc-20260922`
- evidence directory `reviews/internal_habitation/c15-rcc/v1/runs/resident-a-20260922/`

PR #101 remains **OPEN / UNMERGED / PINNED** and must not be modified by this corrective review.

Its new governance disposition is:

> **PRE-FIX / DIAGNOSTIC RESIDENT A EVIDENCE**

It remains valuable evidence of the mechanism gap. It is not an accepted handoff World for fresh Resident B until the gap is repaired and a separate Resident A repair decision is completed.

## 3. Cursor 9 user-delivery evidence

Artifact:

`cursor_lifecycle/cursor_0009_runtime.json`

Mechanical facts:

- Wake exact ref: `wake_3df17e4ced76971ebbf90c05@3`
- wake source: `watch_match`
- effective wake source: `watch_match`
- attention class: `interrupt`
- Step0 state: `ok`
- model allowed: `true`
- delivery allowed: `true`
- Resident runtime response: non-empty
- runtime termination: `responded`
- `delivery_response`: non-empty and equal to the runtime response
- `delivery_suppressed=false`
- final Wake state: `completed`
- final Wake World revision: `66`

This is not merely an internal model response. The runtime explicitly classified the response as permitted user delivery and emitted a non-empty `delivery_response`.

## 4. Cursor 11 user-delivery evidence

Artifact:

`cursor_lifecycle/cursor_0011_runtime.json`

Mechanical facts:

- Wake exact ref: `wake_c9ebc3c1cf7b2a3f1b9b953a@3`
- wake source: `watch_match`
- effective wake source: `watch_match`
- attention class: `interrupt`
- Step0 state: `ok`
- model allowed: `true`
- delivery allowed: `true`
- Resident runtime response: non-empty
- runtime termination: `responded`
- `delivery_response`: non-empty and equal to the runtime response
- `delivery_suppressed=false`
- final Wake state: `completed`
- final Wake World revision: `75`

This is likewise a proactive user-facing assistant delivery, not a suppressed/internal cognition-only result.

## 5. Durable World interaction audit

The exact PR #101 `private_world.sqlite` was independently inspected.

Current Observation facts:

- total current Observations: 20
- `dim:user_ai_interaction` Observations: 14
- role=user: 7
- role=assistant: 7
- non-interaction/platform Observations: 6

The seven assistant interaction Observations map exactly to the seven ordinary USER turns:

- turn 1 assistant at World revision 5
- turn 2 assistant at World revision 13
- turn 3 assistant at World revision 21
- turn 4 assistant at World revision 27
- turn 5 assistant at World revision 61
- turn 6 assistant at World revision 70
- turn 7 assistant at World revision 78

Neither cursor-9 nor cursor-11 Wake delivery text exists as a durable assistant interaction Observation in the World.

Therefore the actual Phase A interaction history contains two user-delivered AI outputs that exist in runtime/evidence artifacts but not in the unified World interaction dimension.

## 6. Constitutional requirement

Authoritative file:

`docs/constitution/AIOS_v3.0_User_AI_Interaction_Dimension_Constitution.md`

It states:

> 用户与AI的交流本身属于世界事实，作为独立维度保存。

The constitution explicitly records:

- 用户输入；
- AI输出；
- 时间信息；
- 对话关系。

The required distinction is:

1. **Correct:** a Wake is not a synthetic USER conversation and must not fabricate a USER Observation.
2. **Incorrect:** therefore an AI output that was actually delivered to the user from a Wake may be omitted from durable interaction World facts.

A real assistant-to-user delivery is still an AI output in the user-AI interaction history even when no user message caused that output.

## 7. Current Core behavior

### 7.1 Ordinary `run_turn()`

Current `src/aios_core/runtime/turn_runtime.py`:

- durably commits the user input before inference through `ConversationIngestor.commit_user_input(...)`;
- after model execution, calls `ConversationIngestor.commit_assistant_output(...)`;
- produces a durable assistant Observation in `dim:user_ai_interaction`.

Current `src/aios_core/ingest/conversation.py` declares:

> Raw user/assistant text is durable world fact.

`commit_assistant_output(...)` writes an Observation with:

- `role=assistant`;
- `source_kind=user_ai_interaction`;
- the canonical interaction dimension;
- stable deterministic message identity;
- an idempotent World operation.

### 7.2 `run_wake()`

Current `FusedTurnRuntime.run_wake()` correctly refuses to create a synthetic USER conversation.

However, after runtime execution it only computes:

- `delivery_allowed`;
- a durable completed Wake;
- `delivery_response = runtime_result.response` when delivery is allowed;
- `delivery_suppressed` otherwise.

Within `run_wake()` there is:

- no call to `ConversationIngestor.commit_assistant_output(...)`;
- no other `self.ingestor` call;
- no durable assistant-interaction commit for a genuinely user-delivered Wake response.

The only `commit_assistant_output` call in `turn_runtime.py` is on the ordinary `run_turn()` path.

## 8. Mechanism-gap verdict

Formal verdict:

> **WAKE USER-DELIVERED ASSISTANT OUTPUT PERSISTENCE = MECHANISM_GAP**

The defect is not that a Wake lacks a synthetic user turn. No synthetic user turn should exist.

The defect is that an actual assistant-to-user delivery has no durable interaction World fact.

## 9. Why this blocks C15 fresh Resident B

C15 tests whether the durable AIOS World carries the Resident's actual long-term life across fresh-context and replacement-model handoff.

Resident B is prohibited from obtaining A's:

- chat transcript;
- run report;
- cursor runtime artifacts;
- PM semantic summaries;
- evaluator notes.

B may recover only durable AIOS state through legal Runtime/capabilities.

Therefore, if A actually delivered two proactive assistant messages to the user but those deliveries exist only in test artifacts, the durable life history available to B is incomplete.

That incomplete history can affect later interpretation of:

- relationship continuity;
- calibration continuity;
- prior communication history;
- material-behavior continuity.

This review does not decide the semantic meaning of those deliveries. It rules only that the missing World facts invalidate the current evidence handoff boundary.

Resident B must not run until this mechanism gap is repaired and Resident A evidence is separately re-dispositioned.

## 10. Prior PR #102 disposition

PR #102's mechanical findings that remain independently true are not erased.

However, its specific conclusion that the two actual user deliveries are sufficiently handled as a `non-conversation Wake delivery boundary` is **superseded by this corrective ruling**.

Consequently:

- the A evidence acceptance is deferred;
- `C15-RCC-RES-A-001` returns from DONE to BLOCKED;
- `C15-RCC-RES-B-001` returns from READY to BLOCKED.

No private World bytes are modified by this correction.

## 11. Unique minimal Core repair task

Create:

`C15-RCC-WAKE-DELIVERY-FIX-001` = **READY**

Sole scope:

> When a non-conversation Wake produces an assistant response that is both permitted and actually returned for user delivery, persist that exact AI output exactly once as an assistant World fact in the unified user-AI interaction dimension, without fabricating any USER input.

The implementation must not broaden into other C15/Core work.

### Required persisted facts

At minimum:

- exact assistant text;
- `role=assistant`;
- subject;
- occurred / delivered time;
- originating exact Wake ref / id;
- provenance identifying Wake user delivery;
- stable idempotency identity;
- resulting World revision.

### No fake USER message

The implementation must not create:

- empty USER input;
- synthetic USER input;
- a `system wake` USER Observation;
- a fabricated user/assistant turn pair.

Only the real assistant-to-user delivery is an interaction fact.

### Exactly-once requirement

Retry / crash / replay of the same Wake delivery must still yield exactly one durable assistant interaction Observation.

Stable identity must bind at least:

- subject;
- Wake object id;
- stable Wake execution / delivery identity.

Random UUID-only identity is insufficient.

### Delivery truth boundary

The following must produce **zero** user-interaction Observation:

- background response that is suppressed;
- channel-denied/user-delivery-disabled response;
- cognition-only derivation;
- periodic-review internal text;
- silence;
- model-generated text that is not actually delivered.

Only a genuinely delivered response is a user-AI interaction World fact.

### Mandatory regressions

1. interrupt Wake + delivered response → exactly 1 durable assistant interaction Observation;
2. retry same delivery → still exactly 1;
3. background response suppressed → 0 interaction Observation;
4. interrupt but user/channel delivery disabled → 0 interaction Observation;
5. silence → 0 interaction Observation;
6. ordinary `run_turn` → existing USER + assistant semantics unchanged;
7. Wake delivery → no synthetic USER Observation;
8. fresh Runtime/search → proactive assistant output recoverable from durable World;
9. provenance links to the exact originating Wake;
10. relevant C14/C15/P16 regressions GREEN.

## 12. Resident A repair decision after Core fix

Create/retain as downstream governance task:

`C15-RCC-RES-A-REPAIR-DECISION-001` = **BLOCKED** on `C15-RCC-WAKE-DELIVERY-FIX-001`.

That later independent PM window must choose exactly one path:

- **Path A:** mechanical historical persistence of the two immutable exact Wake deliveries is allowed only if it can be proven equivalent, semantics-free, exactly-once, and faithful to the original runtime facts;
- **Path B:** otherwise Resident A must restart from a fresh World and rerun.

This corrective window makes **no Path A / Path B decision** and performs no historical backfill.

## 13. Corrected governance state

After this corrective governance merge:

- `C15-RCC-RES-A-001 = BLOCKED` — evidence run complete, acceptance deferred by Wake-delivery persistence gap;
- `C15-RCC-RES-B-001 = BLOCKED`;
- `C15-RCC-RES-C-001 = BLOCKED`;
- `C15-RCC-EVAL-001 = BLOCKED`;
- `C15-RCC-CLOSE-001 = BLOCKED`;
- `C15-RCC-WAKE-DELIVERY-FIX-001 = READY`;
- `C15-RCC-RES-A-REPAIR-DECISION-001 = BLOCKED`.

This review does not modify `src/aios_core/**`, PR #101 evidence, Resident cognition, or any private World.
