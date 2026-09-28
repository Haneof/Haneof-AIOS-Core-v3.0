# C15 Corrective-003 Operator Prep — Competing IA Adjudication and Corrective-001 PM Review Block — 2026-09-28

## Status

```text
C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-001
= OPERATOR_PREP_CORRECTIVE_COMPLETE / REVIEW_READY
= PM_REVIEW_BLOCKED / KNOWN_UNRESOLVED_FINDINGS
= HISTORICAL_REVIEW_BLOCKED_EXACT

C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-002
= READY

C15-RCC-RES-A-RERUN-004-CORRECTIVE-003
= BLOCKED_ON_OPERATOR_PREP
```

This is a PM conflict adjudication.

It does not mark PR #286 as an Independent Acceptance failure because fresh IA for #286 was never released or run.
It does not authorize any Core implementation change.
It does not release a Resident.

## Exact Corrective-001 candidate

- PR #286
- final freeze head H2: `c32e544b747cb1f1d9b7418e2163a65ac55ee39c`
- corrected candidate H1b: `99af8e268a1f9e8944b163d8087005e0e3698620`
- H2 parent = H1b
- base at task start: `30db1cc49910e37694123460755747f57bf47889`

PR #286 successfully closed the three blockers adjudicated from review PR #283:

- `IA-OP-001` — response idempotent replay validates durable on-disk bytes before success;
- `IA-OP-002` — Python wheel closure now has a pre-download source-controlled trust root;
- `IA-OP-003` — gate enumeration/result/execution counts now reconcile.

These three repairs remain valid and must be preserved.

## Competing historical review discovered during PM readiness

A second independent review of the same historical failed Operator Prep exact #281 exists:

- review-only PR #284
- exact review head: `dce47c0d8f3ac7e34efb47e22c63c6f9acbea1a6`
- reviewed candidate: #281 @ `10901d467679b70437ae112747eab81f889fd5cb`
- verdict: `ACCEPTANCE_FAIL / blocker=6`

This review was not included in the earlier PM adjudication that authorized Corrective-001.

During fresh PM readiness for #286, PM discovered #284 and independently checked its findings against the current #286 frozen code.

The findings cannot be ignored merely because #283 had already produced another valid review.

## IA284-OP-01 — VALID / UNRESOLVED ON #286

Historical finding:

The external-session runner recovery path:
- reads current `RuntimeSnapshot`;
- then selects `durable_unconsumed[0]` or `open_dispatched[0]`;
- resolves that old request without proving its durable request body matches the current serialized snapshot;
- silently selects the first item when more than one candidate exists.

Current #286 still contains this behavior.

### Binding correction

Recovery may resume an existing request only when:

1. there is exactly one recoverable candidate;
2. the candidate's durable request digest exists;
3. the exact durable request body/digest matches `serialize_runtime_snapshot(current_snapshot)`;
4. no other outstanding/durable-unconsumed candidate exists.

Otherwise fail closed with an ambiguity/recovery-binding error.

Do not regenerate a semantic answer.

## IA284-OP-02 — VALID / UNRESOLVED ON #286

Historical finding:

The ledger has a `verify_chain()` helper, but operational reads/appends/recovery/consume paths do not require chain validity and event uniqueness before acting.

Current #286 `ledger.py` still allows `read_records()`, `latest_event()`, `append()` etc. without first enforcing the hash chain and per-request event uniqueness.

### Binding correction

Any path that can drive semantic recovery or durable exchange state must fail closed on:

- broken hash chain;
- non-monotonic sequence;
- duplicate `request_published`;
- duplicate `response_published`;
- duplicate `response_consumed`;
- illegal event order;
- request/response digest inconsistency.

Operational integrity must be enforced before:
- append;
- recovery-state classification;
- response consume;
- runner recovery.

A whole-record tail deletion still requires an external head anchor to prove history length; that limitation may remain documented if not otherwise required.

## IA284-OP-03 — VALID / UNRESOLVED ON #286

Historical finding:

The approved bootstrap verify path can fail open on frozen-RC identity.

Current #286 still has:

`REPO_ROOT_DEFAULT="$(cd -- "$SCRIPT_DIR/../../../../../.." ...)"`

and still logs a warning rather than blocking when repo git metadata is unavailable.

The current identity check verifies committed Git objects/HEAD trees but does not prove the actual working-tree Core bytes used by import are byte-identical to the frozen Core.

### Binding correction

The approved `bootstrap --verify` command must:

- resolve or require the real repository root correctly;
- fail closed when Git metadata/frozen objects are unavailable;
- verify exact software/Core/tests Git identities;
- verify working-tree `src/aios_core/**` and relevant tests against the frozen identity or one canonical frozen content manifest;
- verify `aios_core.__file__` resolves inside the expected frozen working tree;
- use one deterministic sorted manifest algorithm shared by bootstrap/tooling/packet.

Missing verification must return BLOCKED/non-zero, not WARNING+success.

## IA284-OP-04 — PARTIALLY CLOSED / STILL BINDING ON SQLITE

The historical finding combined:
1. unpinned Python wheel closure;
2. SQLite pin not enforced by `--verify`.

Corrective-001 closed the wheel trust-root portion.

However current #286 still reads and logs `sqlite3.sqlite_version` without requiring:

`sqlite3.sqlite_version == 3.45.1`

Therefore the SQLite component remains binding.

### Binding correction

`bootstrap --verify` must require exact SQLite `3.45.1`.

It should also validate the intended OpenSSL `3.0.13` runtime when that value is part of the accepted environment identity.

No system-library fallback may be accepted as qualified if the observed version differs.

## IA284-OP-05 — VALID / GOVERNANCE CLARIFICATION REQUIRED

Historical finding:

The launch packet's `allowed_startup_inputs` does not match the clean-room contract:
- packet includes the canonical Resident A run contract;
- packet omits the clean-room contract itself.

The clean-room contract then refers to the canonical run contract for sequential mechanics, creating an avoidable ambiguity.

### PM ruling

For Corrective-003, the Resident-approved startup contract set is exactly:

1. `RESIDENT_A_CORRECTIVE_003_CLEAN_ROOM_CONTRACT.md`;
2. `RESIDENT_A_RUN_CONTRACT.md` — canonical safe mechanical run contract only;
3. the exact PM-approved `RESIDENT_SAFE_LAUNCH_PACKET.json`;
4. mechanical environment/harness status emitted by approved launch tooling.

The clean-room contract is the access-control wrapper.
The canonical Resident A run contract supplies reveal/ingest/ACK/runtime mechanics.
They are a paired approved contract set for this run.

The phrase "any other Resident run contract" in the canonical run contract means historical, alternate, or run-specific Resident contracts other than this exact PM-approved clean-room wrapper.

All prior run contracts/artifacts remain forbidden.

The launch packet and packet audit must encode this exact four-item startup set.

## IA284-OP-06 — VALID / UNRESOLVED ON #286

Historical finding:

The accepted launch packet identifies only:

`aios_exchange.runner:run_user_turn`

But the Resident contract requires due:
- maintenance;
- Wake;
- Review;
- Summary/derivation processing

through frozen Core, and those paths may invoke the model handler.

Current #286 still has no approved harness entrypoint that drives frozen `HeadlessCore.process_due_work` (or exact equivalent) through the same `ExternalSessionModelHandler`.

### Binding correction

Add a purely mechanical due-work entrypoint, e.g. `run_due_work(...)`, that:

- constructs the same external-session model boundary;
- drives frozen Core due-work processing at an explicit timezone-aware `now`;
- returns mechanical status/result/handoff evidence;
- makes no semantic decision itself;
- is listed in the launch packet.

Add a synthetic integration gate that proves a due Wake/Review path can request a model decision through the external exchange and complete using a test-only responder.

Do not use real C15 fixture content.

## Why #286 is not sent to fresh IA

Fresh IA is intended to discover unknown defects, not to repeatedly rediscover known valid blockers already present in repository review evidence.

Because #286 still contains known unresolved binding defects, PM classifies it:

`PM_REVIEW_BLOCKED / KNOWN_UNRESOLVED_FINDINGS`

This is not `ACCEPTANCE_FAIL` because no independent acceptance of #286 was run.

PR #286 must remain unchanged as historical review-blocked evidence.

## Next task

`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-002`

must preserve all Corrective-001 fixes and close only the unresolved #284 findings above.

No Core product change is authorized.

## Downstream

Until Corrective-002 Operator Prep receives fresh IA PASS + PM integration:

- real Corrective-003 Resident = BLOCKED;
- persistence Corrective-003 = BLOCKED;
- Resident B/C = BLOCKED;
- evaluator / C15 close = BLOCKED.
