# C14-RES-FIX-003 Completion Evidence

> Status: **CANDIDATE COMPLETE / DURABLE WORLD ACK GATE PASS**  
> Date: 2026-09-21  
> Task: `C14-RES-FIX-003`  
> Role: Life Director / Sealed Release Infrastructure Designer  
> Started from main: `0ec8d8bc16c2b0e572a9ae1de5cdc89c0416ea70`  
> Work branch: `c14/res-fixture-v3-durable-ack-20260921-sol`  
> PR: #72

## 1. Scope

This task fixes one mechanical release-infrastructure blocker only:

> a syntactically valid `object_id@revision` must not be accepted as durable ingest proof unless that exact revision exists in the private AIOS World and mechanically matches the currently revealed fixture event.

This task does **not**:

- modify `src/aios_core/**`;
- redesign or edit the 36-event fixture;
- change Phase A/B semantics or timestamps;
- run a Resident model;
- run a pseudo-LLM or semantic oracle;
- form/revise/retract a Claim;
- start `C14-RES-A-001`, `C14-RES-B-001`, `C14-RES-EVAL-001`, or P16.

## 2. Frozen fixture proof

Formal fixture:

`reviews/internal_habitation/c14-resident/v2/fixture/sealed_fixture.json`

Frozen SHA256 before FIX-003:

`sha256:1fb973499664d0d71d94a7b94071e3d7210395ea6a54ec4dcbb1ba115d069253`

The Git blob before and after implementation is identical:

`7bd1935c9855ee5a71cd74b45bc693e01d21ca1b`

The PR workflow independently runs `sha256sum` over the committed fixture and requires the same frozen digest.

Result: **fixture bytes unchanged / PASS**.

The manifest is metadata and was updated only to record the stronger release infrastructure:

- subject: `user_1`;
- release operator: `c14-blind-release-operator-v3`;
- ingest adapter: `c14-mechanical-ingest-adapter-v1`;
- binding version: `c14-fixture-event-binding-v1`.

## 3. Formal AIOS World mechanisms reused

No test-side World registry or second durable source of truth was introduced.

Durable ingest uses existing public Core contracts/APIs:

- `Observation`;
- `OperationRequest`;
- `SQLiteWorldStore.commit(...)`.

Durable ack uses existing exact-revision public reads:

- `SQLiteWorldStore.object_revision_record(object_id, revision=N)`;
- `SQLiteWorldStore.get_payload(object_id, revision=N)`.

`object_revision_record` supplies exact revision mechanical provenance from the existing `object_revisions + world_commits` ledger, including:

- object id/revision;
- object type;
- subject id;
- world revision;
- revision kind;
- actual committed `source_class`.

Therefore ack does not trust a caller-provided source class or a sidecar receipt.

## 4. Mechanical ingest adapter

Path:

`reviews/internal_habitation/c14-resident/v2/release/mechanical_ingest_adapter.py`

Version:

`c14-mechanical-ingest-adapter-v1`

The adapter accepts only the already-released Resident-visible projection and creates one durable `Observation`.

It does not read the sealed fixture and contains no:

- NLP;
- search;
- Summary interpretation;
- pattern detection;
- importance ranking;
- preference/personality inference;
- Claim selection;
- revise/retract/silence decision;
- Resident model invocation.

Mechanical binding metadata stored on the Observation:

- `fixture_version`;
- `fixture_sha256`;
- `fixture_binding_version`;
- `fixture_event_id`;
- `fixture_sequence`;
- `fixture_payload_sha256`;
- `fixture_projection_sha256`;
- `dimension`;
- `occurred_at_original`;
- `external_record_id`;
- `external_revision`;
- `mechanical_ingest=true`.

Source authority itself is committed through `OperationRequest.source_class` and is re-read by ack from the exact revision's `world_commits` provenance.

## 5. Release operator v3

Path:

`reviews/internal_habitation/c14-resident/v2/release/release_operator.py`

Version:

`c14-blind-release-operator-v3`

State version:

`c14-release-state-v3`

The `ack` command now requires:

```text
--world-db <private-world.db>
--sequence <N>
--event-id <EVENT_ID>
--ingest-ref <OBJECT_ID>@<REVISION>
```

Before advancing the cursor, ack reopens/queries the actual SQLite World.

For the exact current ref it mechanically verifies:

1. exact `object_id@revision` exists;
2. object is an Observation;
3. revision kind is content;
4. exact durable subject is `user_1`;
5. payload subject is `user_1`;
6. payload object id/revision exactly equal the supplied ref;
7. commit provenance source_class equals the released event;
8. source_kind equals the released event;
9. modality equals the released event;
10. value exactly equals the Resident-visible payload;
11. durable point timestamp equals the released event instant;
12. dimension equals the released event;
13. fixture event id equals the pending event;
14. fixture sequence equals the pending cursor;
15. fixture version/digest/binding version match;
16. deterministic payload SHA256 matches;
17. deterministic full visible-projection SHA256 matches;
18. original occurred_at metadata matches;
19. mechanical-ingest marker is present.

No semantic similarity or fuzzy matching is used.

## 6. Same-private-World receipt-chain closure

FIX-003 additionally closes a World/checkpoint substitution gap.

If state already contains acknowledged receipts, every prior receipt is revalidated against the same supplied `--world-db` before the current ack may advance.

Thus a second SQLite World that contains only the current event but lacks prior acknowledged exact revisions is rejected.

This binds:

`release state receipt chain -> one durable World history`

without adding another World identity database.

## 7. Durable receipt

A successful ack now records:

- `fixture_sha256`;
- event id;
- sequence;
- occurred_at;
- exact `ingest_ref`;
- exact ingest object id;
- exact ingest revision;
- exact ingest world revision;
- actual durable commit source class;
- fixture payload SHA256;
- fixture projection SHA256.

A later evaluator can mechanically follow:

`release receipt -> exact World revision -> released event binding`.

## 8. Regression matrix

Real GitHub Actions tests use Python 3.12, install the current repository package, create actual private SQLiteWorldStore databases, perform real `Observation + OperationRequest + SQLiteWorldStore.commit` writes, reopen stores, and call the real operator.

Required regressions:

| Case | Result |
|---|---|
| frozen fixture SHA unchanged | PASS |
| init Phase A at cursor 1 | PASS |
| reveal cursor 1 only | PASS |
| reveal does not advance | PASS |
| ack before ingest | REJECT / PASS |
| formatted fake ref `fake_object@1` against real empty World | REJECT / PASS |
| actual ingest returns exact durable ref | PASS |
| reopen SQLiteWorldStore and exact revision exists | PASS |
| exact ack after reopen | PASS |
| cursor advances exactly 1 -> 2 | PASS |
| nonexistent revision of real object | REJECT / PASS |
| existing wrong revision with changed content | REJECT / PASS |
| previous-event ref at cursor 2 | REJECT / PASS |
| other/future fixture-event ref | REJECT / PASS |
| real Observation from other subject | REJECT / PASS |
| wrong private World missing prior receipt chain | REJECT / PASS |
| payload mismatch | REJECT / PASS |
| timestamp mismatch | REJECT / PASS |
| dimension mismatch | REJECT / PASS |
| source_kind mismatch | REJECT / PASS |
| source_class mismatch checked from commit provenance | REJECT / PASS |
| modality mismatch | REJECT / PASS |
| success receipt revalidated from reopened World | PASS |
| skip ack | REJECT / PASS |
| repeat ack | REJECT / PASS |
| cursor 24 exact durable ingest + ack -> next 25 | PASS |
| Phase A reveal cursor 25 | REJECT / PASS |
| Phase B wrong-state init | REJECT / PASS |
| Phase B exact 24->25 handoff init | PASS |
| Phase B reveal cursor 25 | PASS |
| future N+1 payload absent from reveal stdout | PASS |
| evaluator-only content absent from reveal stdout | PASS |
| operator/adapter version mismatch | REJECT / PASS |

The committed unittest module contains 30 test methods and completed:

`Ran 30 tests ... OK`.

## 9. Gate history

### Run 35597626462 — expected candidate iteration failure

The first PR run failed before durable logic because the copied temporary release script used a fixed `parents[5]` bootstrap and raised `IndexError`.

No Core/runtime blocker was implicated.

Fix: both release scripts now walk ancestors looking for `src/aios_core`; when absent they use the installed package/PYTHONPATH.

### Run 35597785208 — durable logic 27/29 PASS, test assertion issue

All durable binding paths ran. Two wrong-event tests correctly rejected refs at the earlier source-class check, while the tests had over-specified a later error-message string.

Fix: regressions now assert the safety property—reject + no cursor advancement + pending reveal preserved—rather than one particular rejection order.

### Run 35598032585 — **SUCCESS**

Job: `durable-release-gate`

- World-verified blind release tests: **SUCCESS**
- `30/30` unittest cases: **PASS**
- frozen fixture SHA256 proof: **SUCCESS**
- no `src/aios_core/**` diff: **SUCCESS**

This run also includes the additional wrong-private-World receipt-chain regression.

## 10. Scope audit

Current branch changes are confined to:

- v2 manifest metadata;
- release operator;
- mechanical ingest adapter;
- release contract;
- release mechanical tests;
- release workflow;
- this evidence file.

`src/aios_core/**` changes: **0**

Resident semantic runs: **0**

The frozen sealed fixture file is not in the branch diff.

## 11. Deferred

Real cognition validation remains exclusively:

`C14-RES-A-001 -> C14-RES-B-001 -> C14-RES-EVAL-001`.

FIX-003 establishes only durable chronological input integrity. It issues no semantic cognition verdict and starts no Resident task.
