# CORRECTIVE-001 — rev6 expectation reclassification: rationale and mechanical proof

Status: **disclosed expectation change on three scenarios**, rev5 preserved verbatim.
rev5 SHA-256 `15bc7a93ad7e0d2386c89bb665ad081af9ba4185caad65a9dde2853b3b616488`
rev6 SHA-256 `01258503c7cba19ce0bb4d06d516347012dee4aad465854c1a202e9810aa1650`

## What changed

Only three scenario rows in
`tests/integration/test_core_background_trusted_return_corrective_001_capability_replay.py`
moved their changed-field mutations from the `conflicts` class to the
`identity_shifts` class:

| scenario | moved mutations |
|---|---|
| `upsert_relation` | changed confidence, changed reason, changed evidence |
| `update_cognitive_policy` | changed value, changed reason, changed evidence |
| `rollback_cognitive_policy` | changed reason, changed evidence |

No other expectation in the matrix was altered. All 22 exact-replay expectations,
the inventory guard, and the remaining 16 same-key conflict expectations are
byte-identical to rev5.

## Why rev5 was wrong for these three

rev5 derived those expectations from the **pre-corrective** key schemes:

* `relation-upsert:{relation_id}:{revision}`
* `policy:{object_id}:{policy.revision}`

Both embed a value read from **mutable world state**. That is not a neutral
detail — it is the defect under correction. After the first application advances
the world, a mechanically identical recovered replay derives a *different*
revision, therefore a *different* key, and therefore cannot converge. The
"changed request under the same key" case that rev5 expected to be reachable was
only reachable *because* the key was state-derived.

None of the three request contracts pins the revision being written:

* `RelationUpsertRequest` — `src/aios_core/world_graph.py`: `left_ref`,
  `relation_type`, `right_ref`, `confidence`, `reason`, `evidence_refs`,
  `valid_time`. No relation-revision pin.
* `CognitivePolicyUpdateRequest` — `src/aios_core/policy/service.py:127`:
  `policy_id`, `current_value`, `reason`, `evidence_refs`, `changed_by`,
  `evaluation_window`. No version pin.
* `rollback(policy_id, target_version, ...)` — `target_version` pins the rollback
  **target**, not the position of the new version, which is `current.revision + 1`.

So for these three the request itself is the operation identity.

## What the corrected contract is

Keyed on `canonical_request_identity(...)` — a SHA-256 over the complete
canonical request — plus the object id:

* `relation-upsert:{relation_id}:{identity[:24]}`
* `policy-update:{object_id}:{identity[:24]}`
* `policy-rollback:{object_id}:{identity[:24]}`

Consequences, both asserted by the suite:

1. an **identical** recovered replay reuses the original key, the original
   `operation_id`, the original `expected_world_revision` and the original object
   revision — R5-C convergence;
2. a **changed** request yields a different key, so it is a distinct auditable
   operation: the original operation row, idempotency record and object revision
   are untouched. This is the upsert / policy-version contract these capabilities
   already documented through `RelationReceipt.reused_existing` and
   `CognitivePolicy.previous_version` / `rollback_pointer`.

A changed request is never reported as the original. That is what
`identity_shifts` asserts: the original durable object is never overwritten, and
success requires a genuinely new durable identity.

## Mechanical proof (executed, not asserted)

Querying `operations` and `object_revisions` directly for each of the three:

```
=== upsert_relation / changed confidence -> ok=True
   original op key(s) : ['relation-upsert:relation_4522956a535eb31b183c9be1:746cca088bdb84adbf2598ec']
   NEW op key(s)      : ['relation-upsert:relation_4522956a535eb31b183c9be1:399c9d3d13154f88101aff6f']
   key REUSE (must be empty): set()
   original revisions intact : True

=== update_cognitive_policy / changed value -> ok=True
   original op key(s) : ['policy-update:policy_ddbc0c4d7ec9886da3bb8a13:a818fb70e7c115a83b0a60f9', 'policy:policy_ddbc0c4d7ec9886da3bb8a13:1']
   NEW op key(s)      : ['policy-update:policy_ddbc0c4d7ec9886da3bb8a13:e23eed6e5f6672131a64d0fe']
   key REUSE (must be empty): set()
   original revisions intact : True
   revisions added           : [... ('policy_ddbc0c4d7ec9886da3bb8a13', 3) ...]

=== rollback_cognitive_policy / changed reason -> ok=True
   original op key(s) : ['policy-rollback:policy_5ffe9d8e5dc334033739875e:5d19f4d8a6b8bab712c6ecde', 'policy-update:policy_5ffe9d8e5dc334033739875e:977c4d2306ed7b1d2584597f', 'policy:policy_5ffe9d8e5dc334033739875e:1']
   NEW op key(s)      : ['policy-rollback:policy_5ffe9d8e5dc334033739875e:06958cfe575659a834fdc19b']
   key REUSE (must be empty): set()
   original revisions intact : True
   revisions added           : [... ('policy_5ffe9d8e5dc334033739875e', 4) ...]
```

Zero key reuse, all original revisions intact, a new revision rather than a
silent overwrite of the original.

## Where the fail-closed guarantee now lives, and its proof

A shared key holding a different request cannot arise from these three
capabilities. It remains a hard failure at the layer that owns it —
`SQLiteWorldStore` — and
`tests/integration/test_core_background_trusted_return_corrective_001_store_fail_closed.py`
pins it directly (17 probes, all passing):

* identical request replays the original result and writes nothing;
* the replay lookup is read-only when the key is unused;
* changed request under an existing key → `IDEMPOTENCY_CONFLICT`, no write;
* changed request through `commit()` directly → `IDEMPOTENCY_CONFLICT`, no write;
* changed objects under an existing key → `IDEMPOTENCY_CONFLICT`, no write;
* a replay never persists caller-supplied objects (tampered bytes absent from the
  durable payload);
* operation/idempotency skew → `STORAGE_FAILURE` / `operation_idempotency_skew`;
* missing idempotency record → `STORAGE_FAILURE`;
* corrupt or non-`CommitResult` `result_json` → `corrupt_idempotency_result`;
* missing committed object revision → `replay_object_missing`;
* transplanted object payload → `corrupt_replay_object_payload` /
  `corrupt_replay_object`;
* reused operation id under another key → fails closed, no write;
* reused idempotency key under another operation → `IDEMPOTENCY_CONFLICT`;
* invalid (empty) idempotency key → `INVALID_ARGUMENT`;
* an unrelated later World revision does not break exact replay.

Nothing in this reclassification weakens `request_fingerprint`,
`expected_world_revision`, or the trusted-return path.
