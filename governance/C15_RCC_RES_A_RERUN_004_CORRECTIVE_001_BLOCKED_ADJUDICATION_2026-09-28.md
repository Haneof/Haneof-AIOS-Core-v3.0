# C15-RCC-RES-A-RERUN-004-CORRECTIVE-001 BLOCKED Adjudication — 2026-09-28

## Status

```text
C15-RCC-RES-A-RERUN-004-CORRECTIVE-001
= BLOCKED
= HISTORICAL_BLOCKED_EXACT / IMMUTABLE

C15-RCC-RES-A-RERUN-004-CORRECTIVE-002
= READY
```

This is a PM governance adjudication.

It does not repair PR #277.
It does not authorize any Core implementation change.
It does not release persistence, Resident B/C, evaluator, or C15 close.

## Exact blocked run

Evidence PR:

- PR #277
- exact head: `2968299beea5fe5ec2dc93418d0fa7f3e035ec40`
- parent: `c90b585141864f0687f210b05cde8523e00607e6`
- tree: `e474cd5a3a55959b97c4c3b69400ab258d25f083`
- disposition: `BLOCKED`

Frozen RC remains:

- software: `f20f2edfa7af00d0286493fd15196ca9503bc315`
- Core tree: `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623`
- tests tree: `7e33b5ef8432370234965d3ccd61248c703c4019`

PR #277 remains immutable historical blocked evidence.

## Finding CORR001-BLK-001 — runner/frozen-Core contract mismatch after cursor 1 reveal

The frozen runner serialized `RuntimeSnapshot.capability_history` as if each item were a richer call/result wrapper exposing:

- `arguments`
- `result`
- `error`
- `duration_seconds`

But the accepted frozen Core type is exactly:

```text
CapabilityResult(
  name,
  ok,
  data,
  error_code,
  error_message,
  call_id
)
```

During cursor-1 user-turn round 1, after legal round-0 capability effects, the next real `RuntimeSnapshot` contained `CapabilityResult` entries and the runner raised:

```text
AttributeError: 'CapabilityResult' object has no attribute 'arguments'
```

The failure occurred after cursor 1 had been revealed, ingested and ACKed.

The Resident correctly enforced the binding rule forbidding mid-run harness mutation and stopped at `BLOCKED`.

PM adjudication:

`CORR001-BLK-001 = VALID_BINDING_BLOCKER`

This is a run-local harness compatibility defect, not a Core defect.

No Core change is authorized.

## Finding CORR001-BLK-002 — semantic decisions were scripted in resident_agent.py

PR #277 also contains:

`resident_agent.py`

That file is not mechanical transport.

It contains semantic branching such as:
- matching user-input text/keywords;
- a comment explicitly identifying "Cursor 1";
- hard-coded `record_communication_experience`;
- hard-coded `propose_cognitive_policy`;
- hard-coded `propose_goal`;
- a hard-coded final assistant reply;
- fallback semantic responses/silence.

This violates the binding Resident rule:

> Programs may transport bytes and execute legal capability calls selected by the Resident. Programs may not decide cognition for the Resident.

PM adjudication:

`CORR001-BLK-002 = VALID_BINDING_BLOCKER`

Even if the serializer defect had not occurred, this run could not qualify as authentic Real Resident evidence because a Python semantic policy script was acting as the model/Resident.

The next run must not use any persistent semantic decision function, keyword router, fixture-specific callback, expected-answer script, or prewritten cognition provider.

## Pre-run gate weakness

The 14 synthetic tests validated only the exchange bridge.

They did not execute the frozen runner against the actual frozen Core `RuntimeSnapshot` / `CapabilityResult` contract.

They also ran under system CPython 3.11.2, while the accepted package requires Python >=3.12 and the intended Resident environment is CPython 3.12.14.

This is not counted as a separate historical blocker because the run is already BLOCKED, but Corrective-002 must close both gaps before cursor 1.

## Corrective-002 scope

`C15-RCC-RES-A-RERUN-004-CORRECTIVE-002`

is a completely fresh Phase-A rerun.

Before any release-state init or cursor reveal, it must build and freeze a new run-local harness and prove:

1. exchange bridge atomic/durable chronology;
2. exact compatibility with frozen Core `RuntimeSnapshot`;
3. exact compatibility with both successful and failed frozen Core `CapabilityResult`;
4. an integrated two-round synthetic runtime path in which round 0 returns at least one capability call and round 1 receives non-empty `capability_history`;
5. no serialization exception;
6. no scripted semantic Resident callback in the real run;
7. all pre-run harness tests execute under the same CPython 3.12.14 environment used for the Resident run.

The integrated synthetic test may use a disposable synthetic World and deterministic test-only responses.

It must use no C15 fixture content and must not be reused as the real Resident semantic provider.

## Real Resident response path

For the real run:

- runner publishes a durable decision request;
- the current Resident AI session inspects that request;
- the Resident personally decides the response;
- a mechanical publisher writes/publishes the exact response bytes and ledger record;
- runner consumes only the published response.

The real runner must have no callback that maps keywords/event IDs to cognition.

## Immutability

Preserve unchanged:

- historical failed A-004 PR #273;
- historical failed A-004 IA PR #275;
- blocked Corrective-001 PR #277.

Do not amend, rebase, squash, replace, or hash-swap them.

## Downstream state

Until Corrective-002 completes, receives fresh Independent Acceptance PASS, and is PM-integrated:

- persistence Corrective-003 = BLOCKED;
- Resident B = BLOCKED;
- Resident C = BLOCKED;
- evaluator / C15 close = BLOCKED.
