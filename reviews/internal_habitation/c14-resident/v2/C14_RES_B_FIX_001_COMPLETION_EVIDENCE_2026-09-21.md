# C14-RES-B-FIX-001 Completion Evidence

> Status: **CANDIDATE COMPLETE / CANONICAL CONVERSATION RELEASE GATE PASS**  
> Date: 2026-09-21  
> Task: `C14-RES-B-FIX-001`  
> Role: Release / Test Infrastructure Engineer; Sealed Resident Infrastructure Designer  
> Started from main: `08ceb9ab3f68d5d3ececaaa26832912323d73851`  
> Work branch: `c14/res-b-canonical-conversation-ingest-20260921-sol`  
> PR: #78  
> Pre-evidence GREEN head: `97353dc4e84f1713e14e50cfcd2db466b9a0a32c`

## 1. Scope

This task fixes exactly one Phase-B release-infrastructure problem:

A released USER conversation must not first be persisted as a generic fixture Observation and then be persisted again by `FusedTurnRuntime.run_turn()` as the canonical `user_ai_interaction` Observation.

The solution remains outside `src/aios_core/**`.

This task did not:

- modify Core;
- change sealed fixture semantics or bytes;
- modify Resident-A World, release state, or PR #75 evidence;
- run Resident B semantics;
- form, revise, retract, or evaluate cognition;
- inspect cursor 25+ as a Resident.

## 2. Existing Core API sufficiency

No Core change was required.

The existing public path already supplies the needed identity and idempotency contract:

- `ConversationIngestor.commit_user_input()`;
- stable user Observation id from subject + session + turn + role;
- stable operation/idempotency identity for the same subject/session/turn;
- `FusedTurnRuntime.run_turn()` calls the same `commit_user_input()` before model inference;
- exact equivalent replay returns the existing user Observation without a second World commit.

Canonical interaction dimension is reused from Core as `INTERACTION_DIMENSION = dim:user_ai_interaction`.

## 3. Canonical conversation release adapter

Path:

`reviews/internal_habitation/c14-resident/v2/release/canonical_conversation_ingest.py`

Version:

`c14-canonical-conversation-adapter-v1`

Binding version:

`c14-canonical-conversation-binding-v1`

For an already revealed event with the exact mechanical envelope:

- Phase B / sequence >= 25;
- `dimension=dim:conversation`;
- `source_kind=conversation`;
- `source_class=USER`;
- `modality=text`;

the adapter calls the existing:

`ConversationIngestor.commit_user_input(subject, session_id, turn_index, exact text, exact occurred_at)`.

It does not create a generic fixture Observation and does not perform semantic inference.

## 4. Generic duplicate path closed

The generic `mechanical_ingest_adapter.py` now rejects the Phase-B USER conversation envelope and instructs use of the canonical conversation adapter.

The release operator independently rejects a generic fixture Observation if it is used to masquerade as the canonical user-turn ref.

Thus the duplicate path is closed at both:

1. ingest selection;
2. durable ack verification.

## 5. Release operator v4

Release operator version:

`c14-blind-release-operator-v4`

For Phase-B USER conversation events, ack requires:

- exact `object_id@revision`;
- exact private World;
- `--conversation-session-id`;
- `--conversation-turn-index`.

The specialized verifier checks exact durable equality for:

- exact revision exists;
- content revision;
- subject equals fixture subject;
- durable commit authority is `USER`;
- object type is Observation;
- source kind is `user_ai_interaction`;
- modality is `text`;
- canonical Core interaction dimension;
- metadata role is `user`;
- exact session id;
- exact turn index;
- exact released text;
- exact released occurred_at instant.

No fuzzy matching, NLP similarity, semantic ranking, or model judgment is used.

The pending release state independently pins the current fixture event id and sequence. A successful receipt records the exact canonical ref, fixture event id/sequence, session id, turn index, payload digest, and projection digest.

## 6. Resident-A handoff compatibility

Frozen Resident-A evidence uses release operator v3.

v4 accepts a v3 state only during `init --phase B` and only if the state is the exact sealed handoff:

- active phase A;
- 24 acknowledged receipts;
- `last_acked_sequence=24`;
- `next_sequence=25`;
- no pending reveal.

The test copy is upgraded to v4 only then.

No other v3 state is accepted.

Resident-A evidence itself is unchanged.

## 7. Exact idempotency proof

Formal Python 3.12 regression:

`test_03_exact_ack_then_run_turn_reuses_user_commit_without_duplicate`

Procedure:

1. create/copy a real SQLite World at a legal Phase-B boundary;
2. reveal USER conversation cursor 26;
3. call canonical conversation adapter;
4. verify exact durable canonical user Observation;
5. ack the exact ref successfully;
6. instantiate a fresh `WorldSearchIndex`;
7. instantiate a fresh `FusedTurnRuntime`;
8. call `run_turn()` with the exact same subject/session/turn/text/occurred_at;
9. instrument only the public `commit_user_input()` return value;
10. observe `idempotent_replay=True`;
11. verify returned user Observation id equals the precommitted canonical ref;
12. verify user World revision remains the precommit revision;
13. verify runtime adds only one new World commit for the assistant Observation;
14. verify exactly one canonical user Observation exists for that session/turn;
15. verify no fixture Observation exists for that released conversation event;
16. verify one separate assistant `user_ai_interaction` Observation exists with durable `AI_COGNITION` authority.

The model handler is a fixed one-line transport response only. It performs no cognition and is not Resident B evidence.

Result: **PASS**.

## 8. Fail-closed matrix

Formal regressions reject:

- generic fixture Observation used as canonical user-turn ref;
- canonical conversation ack without session/turn fields;
- wrong session id;
- wrong turn index;
- wrong text;
- wrong timestamp;
- wrong subject;
- assistant-role Observation;
- AI_COGNITION authority with user role;
- another fixture conversation event;
- nonexistent object ref;
- nonexistent revision;
- repeated ack;
- skipped ack;
- reordered event id;
- canonical fields supplied to non-conversation event;
- legacy v3 state outside the exact 24->25 handoff.

All generic non-conversation release regressions remain GREEN.

## 9. Formal environment and gate

Workflow:

`c14-resident-fixture-v2`

Formal Python:

`Python 3.12.14`

Pre-evidence GREEN run:

`35631613259`

Results:

- generic durable blind-release regressions: **30/30 PASS**;
- canonical conversation release/idempotency regressions: **15/15 PASS**;
- existing `test_v3_conversation_world_ingest.py` + `test_v3_fused_turn_runtime.py`: **16/16 PASS**;
- frozen fixture SHA256 proof: **PASS**;
- no Core change proof: **PASS**;
- no Resident-A evidence change proof: **PASS**.

Candidate-iteration history is retained:

- run `35631295628`: generic 30/30 PASS; canonical test exposed test-infrastructure dimension constant mismatch and assertion-order issues; no Core blocker;
- run `35631484831`: canonical success/idempotency path PASS and 14/15 tests PASS; remaining role-negative fixture still used obsolete test dimension; no Core blocker;
- run `35631613259`: all required gates GREEN.

## 10. Frozen artifact proof

Formal sealed fixture:

`reviews/internal_habitation/c14-resident/v2/fixture/sealed_fixture.json`

SHA256 before task:

`sha256:1fb973499664d0d71d94a7b94071e3d7210395ea6a54ec4dcbb1ba115d069253`

SHA256 after implementation:

`sha256:1fb973499664d0d71d94a7b94071e3d7210395ea6a54ec4dcbb1ba115d069253`

Git blob before / pre-evidence candidate:

`7bd1935c9855ee5a71cd74b45bc693e01d21ca1b` / identical.

Resident-A run/evidence paths are absent from the task diff.

## 11. Scope audit

Allowed release/test infrastructure changed:

- `.github/workflows/c14-resident-fixture-v2.yml`;
- v2 fixture manifest metadata only;
- canonical conversation adapter;
- generic adapter Phase-B conversation guard;
- release contract;
- release operator;
- canonical conversation regression suite;
- generic operator regression version update;
- this completion evidence.

`src/aios_core/**` diff: **0**

Resident-A evidence diff: **0**

Sealed fixture semantic/byte diff: **0**

Resident-B semantic execution: **0**

Resident runs in this task: **0**

## 12. Deferred

Only after this task is merged and governance marks it DONE may a new, independent window start `C14-RES-B-001`.

This infrastructure task itself issues no Resident-B semantic verdict.
