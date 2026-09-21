# C14-RES-FIX-002 Independent PM Review

> Date: 2026-09-21  
> Reviewed main: `47355c503fc72ef748f6746360a6954abf45b601`  
> PR: #70  
> Fixture v2 digest: `sha256:1fb973499664d0d71d94a7b94071e3d7210395ea6a54ec4dcbb1ba115d069253`  
> Verdict: **SEMANTIC DESIGN PASS / BLIND-ACK DURABILITY BLOCKER**

## 1. What passed

The v2 fixture closes the two semantic-design blockers from v1.

### Genuine cross-dimensional positive

The Phase-A positive design is now distributed across schedule, work outcome, sleep/current condition, device attention, and bounded local conversation.

Independent PM review of all 36 Resident-visible events confirmed that no single Phase-A Resident-visible dimension independently states the intended longitudinal high-level synthesis.

In particular, `dim:conversation` now contains bounded same-day facts rather than a stable preference/strategy statement.

### Phase-B underdetermination

The fresh-window 09:00 versus 11:00 collaboration decision is no longer mechanically decided by current deadline arithmetic.

Both options remain plausible under Phase-B facts alone:

- early synchronization can reduce rework by resolving visual hierarchy questions;
- later synchronization can preserve a longer initial drafting block and still meet the deadline.

No fixture-side correct option is encoded.

### Future isolation surface

The executable blind release operator correctly:

- reveals only the current event projection;
- does not print hidden `phase`;
- does not print evaluator material;
- does not print the next event;
- enforces Phase-A cursor 24/25 boundary;
- requires reveal before ack;
- rejects skip/repeat/order/version/digest errors.

The fixture v2 content itself is accepted and should remain frozen.

## 2. Remaining blocker — ack proves syntax, not durable ingest

Current `release_operator.py` validates `--ingest-ref` only with:

`^[A-Za-z0-9_.:/-]+@[1-9][0-9]*$`

It does not open or query the actual AIOS durable World.

Therefore this currently succeeds mechanically:

`--ingest-ref fake_object@1`

provided the string format is valid.

The committed tests also use syntactically valid placeholder refs such as `obs_001@1` without proving that those object revisions exist in an AIOS World.

This means the release cursor can advance without mechanically proving:

1. the object revision exists durably;
2. it belongs to the expected subject;
3. it represents the current revealed event;
4. its timestamp/dimension/source/payload correspond to the released projection.

That violates the frozen release rule:

> the cursor advances only after the current event has been durably ingested.

A string that looks like `object_id@revision` is not durable-ingest evidence.

## 3. Required repair

Create a narrow test-infrastructure task:

`C14-RES-FIX-003`

Do **not** redesign fixture v2 and do not alter its event payloads/digest.

The release/ingest boundary must gain mechanical verification against the actual durable AIOS World or an equivalently trusted durable ingest receipt generated from that World.

Preferred design:

- keep `reveal` blind and unchanged;
- make `ack` receive the current private World/checkpoint location or a mechanically generated ingest receipt;
- verify the exact `object_id@revision` exists in durable AIOS storage;
- verify it is the correct subject;
- verify the stored observation/event is bound to the current released fixture event through stable non-semantic fields;
- only then advance the cursor.

The binding should use mechanical fields, for example:

- fixture event id stored as external/source event id or immutable metadata;
- exact occurred_at;
- dimension;
- source kind/class;
- normalized resident-visible payload or a deterministic payload digest.

Do not use NLP or semantic similarity.

If the current ingestion path does not preserve enough mechanical identifiers, add a **test-harness ingestion adapter outside `src/aios_core/**`** that ingests the event through existing public AIOS APIs while preserving a fixture-event binding. Do not change Core for this fixture task.

## 4. Fail-closed requirements

The strengthened ack must reject:

- syntactically valid but nonexistent `fake@1`;
- existing object from another subject;
- existing object for another released event;
- wrong revision of the right object;
- timestamp mismatch;
- dimension mismatch;
- source-kind/source-class mismatch where mechanically represented;
- payload/binding mismatch;
- World/checkpoint mismatch;
- stale prior receipt replay.

The operator must still reject all previous cursor/future/digest violations.

## 5. Required tests

At minimum:

1. reveal current event;
2. ingest current event into a fresh private AIOS World through the approved mechanical adapter;
3. ack exact returned durable ref -> success;
4. reopen World -> exact ref still exists;
5. fake formatted ref -> reject;
6. wrong revision -> reject;
7. previous event ref -> reject;
8. future/other event ref -> reject;
9. other-subject ref -> reject;
10. payload/dimension/timestamp mismatch -> reject;
11. ack success advances exactly one cursor;
12. Phase-A 24 -> 25 boundary remains sealed;
13. no fixture v2 content mutation;
14. no `src/aios_core/**` change;
15. no Resident model execution.

## 6. Decision

- fixture v2 semantic design: **PASS**
- blind reveal isolation: **PASS**
- current ack durable-ingest proof: **FAIL / HARDENING REQUIRED**

Do not start `C14-RES-A-001` yet.

Insert `C14-RES-FIX-003 = READY`, block Resident A on it, and preserve the already-frozen v2 fixture digest.
