# C15 operator preflight — round 3 evidence (PM/operator only)

Task remains **IN_PROGRESS / BLOCKED, not DONE**. PR #125 stays OPEN.
No real B/C; no frozen Core/fixture change; no merge/close/auto-merge.
Be-reviewed SHA: `90fec6dbff2b28ac531e0083acc9e753c0d06b42`.

## Six findings — before/after

All six were reproduced independently on the reviewed HEAD with synthetic
resources only (no real credentials/private A/sealed future reads).

### Reproduction summary (before)

From `/home/user/.cache/c15-round3/before.py` on 90fec6d:

- 1 journal: append after I/O failure succeeded, latched_failure null
- 2 send: zero bytes written but reply read and silence accepted
- 3 future visibility: old BACKGROUND wake saw `SYNTHETIC event 1` via real search_world
- 4 checkpoint: completed 0 -> 1 inferred from ACK after checkpoint deletion
- 5 publication: uncertain package exists and actual restore accepted
- 6 isolation: host resources did NOT exist, yet probe reported all_denied true

After round3 fixes, `/home/user/.cache/c15-round3/after.py` reports:

- 1 journal latched, after blocked, bridge after journal fail blocked
- 2 short write 206 chunks success, zero/progress/partial/flush failures without reply read
- 3 old wake saw future false, only synthetic-old background
- 4 missing/corrupt checkpoint blocked
- 5 freeze post-publication fsync failure: package exists but restore without confirmation blocked, fake confirmation blocked
- 6 new probe PASS with canaries verified, controls true, real_resources NOT_TESTED

### Fix table

| # | Problem | Repro before | Fix location | Permanent regression | Result |
|---|---------|--------------|--------------|----------------------|--------|
| 1 | log I/O failure still usable | write/flush/fsync failure not latched, append after failure succeeded, bridge continued | `transport.py: Trace` unbuffered wb, `io_failure` latch, `JournalPoisoned` on further appends, close tolerates poisoned state, `StreamBridge._request` checks `failure`, latches and blocks second call, retains file | `test_journal_write_failure_latches_and_blocks`, `test_journal_flush_failure_latches`, `test_journal_fsync_failure_latches`, `test_bridge_stops_after_first_request_log_failure_and_retains_file` in `test_round3_fixes.py` | PASS: write/flush/fsync each latch, after blocked, bridge second call TransportError, file retained |
| 2 | short write/zero progress still reads reply | outgoing.write returning 0 still read reply and accepted silence | `transport.py: StreamBridge._request` strict positive-progress loop, remainder only, no whole-request resend, flush wrapped to TransportError, invalid progress raises TransportError, no reply read until full send+flush success | `test_short_writes_success`, `test_zero_progress_fails_without_reply_read`, `test_partial_send_then_exception_fails_without_reply`, `test_flush_failure_fails_without_reply` | PASS: short writes 1-char loop succeeds, zero/illegal/exception/flush fail without readline |
| 3 | old BACKGROUND wake reads future input | clock.py 40-69, driver.py 206-229: old wake dispatched after new event ingest, real search_world returned new event payload | `clock.py: ClockAdapter.advance_to` now does protocol-boundary pre-ingest dispatch via normal router BEFORE ingest; `driver.py` already advances clock before ingest; budget-deferred wakes return queued not forced | `test_old_wake_cannot_see_future_input` observes real Runtime/tool excerpts, proves no future payload; `test_budget_deferral_not_forced` verifies budget-blocked wake stays queued | PASS: old wake sees only past, budget not forced |
| 4 | checkpoint missing inferred completed from ACK | driver.py 117-131: checkpoint deletion caused completed 0->1 from ACK | `driver.py: _validate_checkpoint` rejects unreadable/corrupt/ambiguous; missing checkpoint requires explicit `initialize_fresh` plus verified pristine conditions (phase A, last_acked 0, next 1, empty receipts, rev 0, watermark 0, no metering, empty trace); symlink/tmp ambiguity blocked | `test_checkpoint_missing_with_ack_blocks`, `test_checkpoint_corrupt_blocks`, `test_explicit_legal_first_init`, `test_normal_restore_with_complete_checkpoint` | PASS: ACK exists but checkpoint lost blocks, corrupt blocks, fresh genesis explicit, normal restore OK |
| 5 | freeze after fsync leaves acceptable READY package | freeze.py 99-114: post-publication fsync failure left package still accepted by ordinary restore | `freeze.py` + new `publication.py`: live non-serializable `PublicationConfirmation` issued ONLY after every I/O succeeded, bound to manifest SHA and publication id via WeakKeyDictionary; package internal READY not sufficient; `restore_frozen` requires pinned hash AND live confirmation; exception leaves visible-but-unconfirmed package, source FAILED/UNCERTAIN, ordinary restore BLOCKED; no delete-marker/warning as safety | `test_freeze_post_publication_fsync_failure_blocks_restore` injects fsync failure after rename, proves restore without confirmation and with fake object blocked, source FAILED | PASS, plus existing WAL and partial backup tests retained |
| 6 | isolation probe false positive on non-existent path | isolation_probe.py 21-25,45-56: checked host paths that may not exist, reported PASS | `isolation_probe.py` now creates only synthetic canaries in private tmpdir, never reads real credentials/private A/sealed future; `outside_checks` verifies existence/readable/hash before and after child; `assess` returns NOT_TESTED/INCONCLUSIVE when premise missing; positive control allowed packet readable SHA verified; real_resources marked NOT_TESTED; `resident_arena_isolation` BLOCKED, `launchable` false | `test_isolation_canary_preconditions_and_positive_control` PASS with canaries verified; `test_isolation_outside_checks_not_tested_when_missing` proves missing canary => NOT_TESTED and INCONCLUSIVE not PASS | PASS: canary premise verified, real resources NOT_TESTED, historical 13/13 scope corrected |

## Engineering details

- Transport: Trace now `wb` unbuffered, prevents buffered tail flush behind failure. `io_failure` separate from `failure` but both latched. `close()` tolerates already-poisoned journal to retain failed file.
- StreamBridge: send loop `while offset < len(frame)` with `0 < count <= remaining` check; `OSError` from write/flush wrapped to `TransportError` with chaining; `model_error` append attempted only if journal still writable; failure blocks further model requests.
- Clock: `_dispatch_pending_wakes` uses `dispatch_next_pending_wake` preserving background batch window and REVIEW_QUEUE exclusion. `advance_to` calls it at target instant BEFORE new event ingest, not backdating execution to wake origin. Budget hard-deny returns `runtime None` and stops loop.
- Driver: `_validate_checkpoint` checks format, integers, session nonblank, clock/review iso, due_work dict, stage str, release_sha256 64 hex, stop boundary. Missing checkpoint only allowed with `initialize_fresh=True` and full pristine predicate. Symlink and `.tmp` ambiguity blocked.
- Freeze/publication: `FrozenPackage` dataclass with manifest and live confirmation. `_confirm` stores in `WeakKeyDictionary`, `require_confirmation` checks instance and binding. `PublicationConfirmation.__new__` raises, `__reduce__` raises to prevent pickle replay. Freeze transitions: FREEZING -> (backup/validate/manifest) -> PUBLISHING -> rename -> fsync parent -> FROZEN -> issue confirmation. Exception path: state FAILED, UNCERTAIN, preserved_package path retained, checkpoint attempted, no manifest deletion relied upon for safety.
- Isolation: `create_canaries` generates random 32-byte hex plus header, mode 0600, dir 0700. `outside_checks` checks not symlink, is file, hash matches. `assess` combines before/after VERIFIED and controls true and denied bool. Real resources explicitly NOT_TESTED, not opened.

## Tests / CI

Local Python 3.12.11 (source build, SQLite 3.40.1):

```
PYTHONDONTWRITEBYTECODE=1 /home/user/.cache/c15-python312/bin/python3.12 -m pytest -o addopts='' -q tests/preflight
# 98 passed (81 previous + 17 round3)
PYTHONDONTWRITEBYTECODE=1 /home/user/.cache/c15-python312/bin/python3.12 -m pytest -o addopts='' -q tests/runtime ... (8 suites)
# 146 passed
```

Previous exact-head CI for 90fec6d was SUCCESS for both c15-operator-preflight and p16-convergence-gate. New head will be pushed; exact-head CI to be recorded separately.

## Remaining blockers (not complete preflight)

- Real Resident broker/client not connected to minimal boundary; Arena tool permissions remain BLOCKED; launchable false.
- Interrupted/ambiguous ACK/model/freeze phases stop for review; no general mid-phase crash recovery across arbitrary RUNNING wake/process death.
- Provider identity/usage remains UNKNOWN; no trusted telemetry.
- No approved durable private A storage; cache not persisted across snapshots.
- Python 3.12.11 local build lacks SSL/optional modules; not production certification.

No real B/C executed; no frozen Core/fixture modification; no merge/close/auto-merge.

## Artifacts

- Diff: `C15-PR125-round3.diff` (to be generated)
- New tests: `tests/preflight/test_round3_fixes.py`
- Modules: `transport.py`, `clock.py`, `driver.py`, `freeze.py`, `publication.py` (new), `isolation_probe.py`, `README.md`, `operator_manifest.json`
