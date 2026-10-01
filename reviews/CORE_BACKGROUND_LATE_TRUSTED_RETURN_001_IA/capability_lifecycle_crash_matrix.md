# Capability lifecycle & crash matrix (T1–T12) — WINDOW 14

Candidate `5ad0524c425592210ff184e00ad52abb2c14e366`. Dispositions derived from
source (`background_attempt.py`, `turn_runtime.py`, `cognitive_runtime.py:334-370`)
plus frozen probes (`IA14-RACE-001`, `IA14-SIGKILL-001`, S1, S3).

## Dispatch/handoff sequence (source order)

1. `_admit_background_model_attempt` → `admit` (state `admitted`)
2. `_mark_background_model_dispatch` → `mark_dispatching`: binding row committed in
   the SAME transaction as `admitted→dispatching` (`background_attempt.py:988-1078`)
3. `_issue_external_return_capability` (row + nonce committed) — only if observer
   registered
4. `ExternalReturnObserver.accept_return_capability(snapshot, capability)`
5. `model_handler(snapshot)` (provider submission happens inside)
6. return: `_capture_trusted_response_return` (receipt+handoff atomic) →
   `record_response` → metering → semantic effects → output/ACK

## Crash matrix

| # | boundary | state after crash | retry safe? | fail closed? | late attach? | exactly-once? | notes |
|---|---|---|---|---|---|---|---|
| T1 | before `mark_dispatching` | `admitted`, no binding | yes (typed reconcile or admit) | n/a | no (no capability yet) | yes | pre-dispatch legal path intact |
| T2 | after binding txn commit | `dispatching`+binding | no blind redispatch | yes (`in_doubt` on re-admit) | yes if capability issued | yes | `admit()` converts `dispatching→in_doubt` (`:948-970`) |
| T3 | after capability DB row commit | + capability row | no | yes | yes (observer proves) | yes | row survives restart |
| T4 | before `accept_return_capability` | capability row orphaned | no | yes (honest path) | **no honest path** (capability never left Core) | yes | hostile path: BLK-W14-001 reissue; honest observer cannot recover the capability — documented gap of T-ROOT-001 timing |
| T5 | after observer receives, before handler | capability live outside | no | yes | yes (observer may prove) | yes | fabricated return indistinguishable (T-ROOT-001) |
| T6 | after real submission | `dispatching`+binding | **forbidden** (no redispatch) | yes | yes | yes | the core scenario; SIGKILL probe green |
| T7 | after external response+proof created | + proof outside | no | yes | yes | yes | attach idempotent |
| T8 | proof durable externally, before Core attach | same | no | yes | yes | yes | attach later; replay deterministic |
| T9 | inside attach txn | BEGIN IMMEDIATE; receipt+handoff+consumed CAS in one txn (`:1836-1906`) | n/a | atomic rollback | retriable | one canonical consume | `consumed.rowcount != 1` → conflict |
| T10 | after receipt/handoff durable, before staging | receipt+handoff | no | yes | via `_promote_staged_exact_response` | yes | single promotion path (`:1922-1998`) |
| T11 | after exact stage, before semantic application | staged row | no | yes | `recover_trusted_handoff` continues | yes | no provider call (`:2676-2747`) |
| T12 | after semantic/capability effect, before outer ACK | `metered`+output | terminal short-circuit (`turn_runtime.py:3478-3489`) | yes | n/a | no duplicate effect | second `run_turn` → `TurnAlreadyCompleted` |

## Races (§14)

Frozen `IA14-RACE-001`: two threads race proof-A/proof-B against one issued
capability. Result: `[('left','refused'), ('right','accepted')]`, one staged
canonical response, no deadlock. Mechanism: `BEGIN IMMEDIATE` + consumed-at CAS
(`UPDATE … WHERE consumed_at IS NULL`, rowcount guard). Exact replay of the same
bytes after consumption is deterministic; conflicting bytes fail closed
("already consumed for a different exact return", `:1875-1893`).

## Stale capability across legal not_submitted retry (§21) — BLK-W14-004

Frozen S3 (`raw_s3_stale_capability_rotation.txt`):

- binding **does** rotate on a `not_submitted` retry ("A not_submitted retry
  dispatches a new outbound request. Replace the previous binding…",
  `background_attempt.py:1043-1047`);
- the capability row is **never re-scoped or rotated** (`:1645-1655` returns the
  existing row; nonce reused);
- consequence: after a retry with a changed outbound fingerprint, the capability
  row's scope fields disagree with the new durable binding, and every attach —
  including a genuine proof for the retried dispatch's own real return — is refused
  with "the issued late trusted return capability is not scoped to this attempt's
  durable originating request". The stale capability cannot sign the new request
  (good) but the new request can never be attached either (silent recovery dead-end).
- identical-fingerprint retries (S1) work and keep first-writer-wins; the defect
  appears exactly on the documented "new outbound request" branch.

Contract requirement of §21 (nonce reuse? binding change? stale proof? consumed
semantics?) is not addressed anywhere in design_note.md or matrices.md. No explicit
contract exists. Blocker.

## Strong terminal receipt short-circuit (§24)

`run_turn` first inspects the turn execution; if `assistant_ref` is not None or
state `completed`, it only finishes the mechanical ACK and never stages/reapplies
(`turn_runtime.py:3478-3489`). Verified in the SIGKILL probe: second invocation →
`TurnAlreadyCompleted`, provider_calls `[]`, meters `1`. R5-A/B/C/D green in the
fresh 249/249 accepted regression.
