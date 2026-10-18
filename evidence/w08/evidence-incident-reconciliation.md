# Incident 2026-09-29: remote push auth failure + bgattempt in_doubt fail-closed (cursor 20 due work)

## Timeline (mechanical)
1. Cursor 17 (USER) full lifecycle: gens 18-21, req-0032..34. Cursor 18 (PLATFORM): gens 22-26. Cursor 19 (USER): gens 27-28, req-0037/38.
2. Cursor 19 K3/K4 seal push FAILED: GitHub token invalid ("could not read Username for 'https://github.com': terminal prompts disabled"; gh: "The github.com token in GH_TOKEN is no longer valid"). Local seals continued unpushed: gen29 K3/K4, gen30 K5, gen31 DURABLE_ACK, gen32 K1 c20. clear 19 ok. Remote paused at gen28 `4533f92a…` (`.remote-head` consistent, CAS intact).
3. After Arena GitHub reconnect: CAS precondition verified (remote still `4533f92a…`); `push_run_state` once -> commit `4f12ee0e…` (parent `4533f92a…`, --force-with-lease); `verify_local_remote_authority` PASS. Operator log: RECOVERY entry.
4. Resume at INGEST c15rcc-020: K2 gen33 `71c3285f…` pushed; remote head == `.remote-head` == gen33. World state: c20 current-event + binding installed, due work pending.
5. due 20 (first attempt, inline blocking invocation — operator process error): review request req-0039 published (ledger seq 115 `request_published`, response_sha256=null); operator could not answer while blocked; harness `await_response_bytes` timed out at 1800s -> ResponseTimeoutError; the bash tool killed the process group mid-await.
6. Operator published the round-0 Resident response for req-0039 (response_published; sha 21a31eb3…) AFTER process death. Exchange-side the request stayed open_dispatched/durable-unconsumed.
7. due 20 re-run (backgrounded): Core admission `BackgroundModelAttemptStore.admit` found attempt `bgattempt_1d6735f46f05508149948ea5a7de5b01` in state `dispatching` -> set `in_doubt` (failure_kind=restart_after_dispatch_boundary) -> raised `BackgroundModelExecutionInDoubt` BEFORE the model handler could run the exchange recovery. Traceback preserved (due20_second_attempt_indoubt_crash.log).

## Why no honest recover-and-continue exists in the accepted implementation
All findings are from the frozen worktree rc-f20f2edf (Release-003 accepted implementation):

- `src/aios_core/runtime/background_attempt.py:920-921` — admit() raises InDoubt for state=in_doubt; only stage_exact_response moves in_doubt->response_returned (line ~1933 UPDATE ... WHERE state IN ('dispatching','in_doubt')).
- `background_attempt.py:1315-1336` — `reconcile_response` (metadata path) deliberately disabled: "metadata-only response reconciliation is disabled; exact provider bytes and a trusted return-path proof are required".
- `background_attempt.py:1747+` — `stage_exact_response` requires a non-null `authenticity_proof` (line ~1863: "trusted provider-return authenticity proof is missing") verified via `_verify_response_authenticity` (line 1647+) against a pre-existing row in `background_model_response_receipts`.
- Receipts are minted ONLY by `_capture_trusted_response_return` (line 1462), docstring: "intentionally private and is wired only as CognitiveRuntime's trusted return callback. Recovery staging has no path to this authority and receives neither the HMAC key nor a signing callable." Its only caller: `turn_runtime.py:1322` inside `_authenticate_background_model_response`, which RETURNS WITHOUT CAPTURING when `_provider_identity(directive)` has any None (line ~1308-1320): "Anonymous/local handlers remain valid but cannot participate in exact external-response recovery because there is no provider identity to bind."
- This run's transport (`operator-prep/harness/aios_exchange/schema.py:287 parse_model_directive`) produces directives with `provenance=None` for operator-authored responses -> the ENTIRE B run operated in anonymous-handler mode: zero receipts ever existed, for any round. Therefore stage_exact_response is unreachable for bgattempt_1d6735f4 by construction.
- `reconcile_not_submitted` (line 1257) is the only other in_doubt exit. Its sole guard is receipt absence. The exchange ledger (`request_published`, seq 115) plus the Core pre-dispatch binding (`mark_dispatching`, turn_runtime.py:1290) PROVE the dispatch boundary was crossed; harness `aios_exchange/requests.py:1-13` declares "The request_published ledger record is the semantic dispatch boundary: after it exists, the exchange may never be reconciled as 'not submitted'." Using it here would write a durable FALSE fact into the World.
- `mark_failure` (line 1082) transitions only from admitted/dispatching and targets in_doubt/not_submitted; no terminal exit.
- Wake layer: `review/periodic.py begin_review` docstring — "A RUNNING wake is resumable after process failure" — every resume re-enters run_turn -> admission guard -> InDoubt. No stale-wake expiry/takeover path exists.
- The frozen test tree enshrines exactly this situation as fail-closed: `tests/integration/test_core_background_response_recovery_001.py` test_case_01 "crash_after_dispatch_without_exact_response_stays_in_doubt" (line 333) asserts the raise and that the wake stays running with no retry.

## Unconsumed exchange artifacts (left untouched, honestly)
- req-0039-model_directive-ed097a32: request_published (ledger seq 115), response_published (round-0 directive: capability call read_periodic_review_anchors; response sha 21a31eb3…), NEVER consumed by Core. No capability effect was applied from it. Consuming it now would falsely imply Core delivery.

## Disposition
RUN_STATE_TOUCHED at cursor 20 due phase; accepted persistence mechanism offers no honest recover-and-continue -> STOP / PM_ADJUDICATION_REQUIRED. Remote authority current and verified through gen33 (`71c3285f…`). No second run identity, no re-reveal, no replay, no local-only downgrade at any point.
