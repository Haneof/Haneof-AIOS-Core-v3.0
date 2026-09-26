# C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001 — PM Scope Amendment

Date: 2026-09-26
Repository: `Haneof/Haneof-AIOS-Core-v3.0`
Applies to: `C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001`

## Decision

`CONTINUE SAME CORRECTIVE / NO NEW CORE TASK`

The engineering WIP exposed a real distinction that the original state-loss adjudication acceptance wording did not express precisely enough:

- **exactly-once safety** is mandatory;
- **automatic same-run liveness through every ambiguous crash point is not mandatory**.

The frozen Core intentionally treats an ambiguous post-dispatch state as `in_doubt` and refuses blind retry. That behavior is part of the accepted Core recovery contract, not a regression to be worked around by operator code.

The persistence corrective MUST NOT modify `src/aios_core/**` merely to turn an intentionally fail-closed `in_doubt` state into automatic replay.

## Core facts revalidated by PM

Current frozen Core contains:

- durable provider-attempt states including `dispatching`, `in_doubt`, and `response_returned`;
- `BackgroundModelAttemptStore.reconcile_response(...)` for externally proven provider-response provenance;
- deliberate blocking of blind reinvocation after the provider dispatch boundary;
- Core response recording before metering/capability/output work during an ordinary uninterrupted run.

The current Core does **not** expose a general operator API that safely resumes arbitrary partially-applied capability/output work from an externally journaled reply. The persistence task must not invent such semantics outside Core.

## Corrected acceptance meaning

The original requirement that all five kill points "converge to the same durable cursor" is replaced by this two-part rule.

### A. Safety invariant — mandatory at every kill point

After any tested kill/restart point:

1. authoritative run state and required evidence survive;
2. the exact current cursor/event/binding/request/reply provenance remains inspectable;
3. no second reveal occurs;
4. no duplicate ingest occurs;
5. no second Resident/provider semantic decision is fabricated;
6. no duplicate capability side effect is applied;
7. no duplicate semantic reply/output is applied;
8. no duplicate ACK occurs;
9. no cursor is skipped or advanced without proof;
10. uncertainty is represented durably and fail-closed.

A durable terminal/in-doubt stop **passes the safety invariant** when the frozen Core cannot prove a replay safe.

### B. Forward continuation — required only where safety is mechanically proven

The corrective must continue the same run automatically/operationally only for states where durable evidence proves that no non-repeatable semantic boundary has been crossed.

At minimum:

- after reveal / before ingest: recover the same pending cursor without second reveal;
- after ingest / before provider dispatch: recover without duplicate ingest and continue;
- provider request durably staged/exposed but no Resident reply exists: preserve/re-present the exact same request identity/bytes without minting a second semantic request.

For later ambiguous boundaries:

- reply durably staged but Core response/application state is not proven;
- Core response recorded but capability/output application may be partial;
- capability/model work occurred but ACK proof is incomplete;

the legal result may be a durable fail-closed terminal state requiring PM adjudication/new release rather than unsafe replay.

## Reply-staged rule

An operator journal containing exact reply bytes is evidence, not authority to claim that Core applied the directive.

If the journal proves a reply exists but Core remains `dispatching/in_doubt`, operator code MUST NOT:

- relabel it as `not_submitted`;
- blindly rerun the provider;
- reapply the directive/capabilities;
- forge `response_returned`;
- ACK the cursor.

It may use an already-supported Core reconciliation surface only when all inputs required by that surface are mechanically derivable and the resulting state does not imply unsupported replay.

If safe forward application is not supported, persist the state as terminal/in-doubt and stop.

## Effect on the current engineering WIP

The current findings described by the engineering window are **not a blocker requiring a new Core task**:

- 13 synthetic journal/persistence tests passing are useful evidence;
- frozen 158/158 and lifecycle mutation-red remaining green are required;
- the SIGKILL reply-staged -> Core `in_doubt` result is an expected fail-closed boundary, provided the durable journal/evidence survive and no duplicate semantic application occurs.

The same corrective must continue from its existing WIP. Do not restart from scratch and do not discard red evidence.

Still outstanding before `REVIEW_READY`:

1. production operator wiring to the non-ephemeral authoritative location;
2. full corrected kill-point matrix under the safety/liveness distinction above;
3. platform detach/re-attach persistence proof for authoritative run state and evidence;
4. proof that a terminal/in-doubt case survives restart with exact request/reply/binding provenance;
5. frozen 158/158 + lifecycle mutation-red regression unchanged;
6. complete evidence package and exact candidate pin.

Engineering may declare only `REVIEW_READY`. Independent Acceptance remains separate.

## Downstream sequence unchanged

- persistence corrective -> Independent Acceptance
- RELEASE-003
- fresh RERUN-003
- B-ACCEPT-003
- then C / evaluator / close

No real Resident B is authorized during this corrective.
