# C14 Resident B Conversation Ingest Preflight

> Date: 2026-09-21  
> Task: `C14-RES-B-FIX-001`  
> Scope: test/release infrastructure only  
> Core changes: forbidden  
> Resident B semantics: forbidden in this task

## 1. Problem

The Phase-B fixture contains Resident-visible conversation events that must participate in ordinary user interaction.

The frozen release pipeline currently persists every released event through `mechanical_ingest_adapter.py` as a fixture-bound Observation.

The constitutional user-interaction path is `FusedTurnRuntime.run_turn()`. That path itself calls `ConversationIngestor.commit_user_input()` before model inference.

If a Phase-B conversation event is first persisted through the generic fixture adapter and then passed to `run_turn()`, the same user utterance is represented twice in the World:

1. fixture Observation;
2. canonical `user_ai_interaction` Observation.

That duplicate could contaminate Summary/cognition/retrieval evidence. Resident B must not start with this ambiguity.

## 2. Required outcome

Add a narrow canonical-conversation release path outside `src/aios_core/**`.

For a released USER conversation event, the test-side adapter must be able to persist the current utterance through the existing `ConversationIngestor.commit_user_input()` contract using a fresh Resident-B session id and explicit turn index.

The blind release operator must then be able to verify that exact canonical Conversation Observation as durable proof for the current pending released event.

After acknowledgement, a later call to `FusedTurnRuntime.run_turn()` with the exact same:

- subject;
- session id;
- turn index;
- user text;
- occurred_at;

must idempotently reuse the already persisted user Observation rather than create a second user Observation.

The model/runtime response and assistant Observation may then proceed normally.

## 3. Binding requirements

The specialized conversation ack remains fail-closed.

It must verify the exact canonical user Observation:

- exists at the exact revision;
- subject is the fixture subject;
- source authority is USER from durable commit provenance;
- object type is Observation;
- source kind is `user_ai_interaction`;
- modality is `text`;
- metadata role is `user`;
- metadata session id equals the supplied fresh B session;
- metadata turn index equals the supplied turn index;
- value exactly equals the current released `resident_visible_payload`;
- occurred_at exactly equals the released event timestamp;
- no prior/future event ref can satisfy the current pending release;
- release state sequence/event id still match the current pending event.

The mapping from a frozen fixture `dim:conversation / source_kind=conversation` event to the canonical `dim:interaction / source_kind=user_ai_interaction` observation is legal only in this explicitly selected canonical-user-turn binding mode.

No fuzzy/NLP matching is allowed.

## 4. Durable fixture identity

If the canonical Conversation Observation cannot carry fixture event id/sequence metadata without changing Core, do not modify Core merely for the fixture.

The release state itself already pins the pending event id/sequence. Exact equality of subject, role, value, occurred_at, session, turn index and durable provenance may provide the specialized binding, with the successful ack receipt recording:

- fixture event id;
- fixture sequence;
- exact conversation observation ref;
- session id;
- turn index;
- projection digest.

This is release provenance, not a second source of semantic truth.

## 5. Required idempotency test

The key regression must use a real fresh SQLite World:

1. initialize a Phase-B-compatible state at a test boundary;
2. reveal one USER conversation event;
3. canonical-conversation adapter calls `ConversationIngestor.commit_user_input()`;
4. exact user Observation is durably present;
5. release ack succeeds against that ref;
6. instantiate a fresh `FusedTurnRuntime`;
7. call `run_turn()` with the same session id / turn index / text / occurred_at;
8. prove the user-input commit is an idempotent replay;
9. prove there is still exactly one canonical user Observation for that turn;
10. assistant output may create its separate normal assistant Observation.

No pseudo-model semantics are needed for this mechanical regression; use a minimal fixed transport directive only where required to terminate the runtime, and do not count this task as Resident evidence.

## 6. Other fail-closed tests

Reject:

- generic fixture Observation used as canonical user-turn ref;
- wrong session id;
- wrong turn index;
- wrong text;
- wrong timestamp;
- wrong subject;
- assistant-role Observation;
- AI_COGNITION source authority;
- another conversation event;
- nonexistent ref/revision;
- repeated/skip/reordered ack;
- Phase A/B boundary violations.

All existing non-conversation blind release tests must remain GREEN.

## 7. Frozen artifacts

Do not modify:

- sealed fixture v2 bytes;
- fixture SHA256;
- Resident-A evidence at PR #75;
- Resident-A private World;
- Resident-A release state.

Use test copies only.

## 8. Scope boundaries

Allowed:

- v2 release/test infrastructure;
- a specialized canonical conversation ingest adapter;
- release operator/contract changes;
- tests/workflow/evidence/governance updates.

Forbidden:

- `src/aios_core/**` changes;
- semantic fixture changes;
- Resident-B execution;
- reading future events as a Resident;
- expected plan/answer logic;
- cognition rules.

If existing public Core APIs cannot support this without a Core modification, stop and report the blocker. Do not patch Core inside this task.

## 9. Environment

Use Python 3.12+ for the formal candidate Gate when available, matching `pyproject.toml`.

## 10. Closure

After exact mechanical gates pass:

- `C14-RES-B-FIX-001 = DONE`;
- `C14-RES-B-001 = READY`;
- record exact candidate SHA, workflow run, fixture digest proof, and no-Core-diff proof;
- stop without starting Resident B.
