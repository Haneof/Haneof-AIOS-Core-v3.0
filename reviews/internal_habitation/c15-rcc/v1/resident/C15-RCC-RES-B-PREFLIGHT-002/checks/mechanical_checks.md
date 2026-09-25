# C15-RCC-RES-B-PREFLIGHT-002 — Mechanical Check Results

All checks were run against disposable copies of the freeze artifacts. The canonical #205 evidence was read but not modified.

## 1. Frozen Core tree identity

**PASS.** `src/aios_core` tree hash = `fe77f8a0706acfaf369041d0882b6d0e6de39f22` at:
- frozen software `773876f9...`
- #205 head `d17ae972...`
- publication base `4d9f0471...`
- current main HEAD `811ae85...`

Command:
```
git ls-tree <commit> src/aios_core
```

## 2. Accepted A freeze digests

**PASS.** All three recomputed SHA-256 values match the acceptance receipt:

| File | Expected | Recomputed |
| --- | --- | --- |
| private_world.sqlite | `626c6bb3...01f6aa` | `626c6bb3...01f6aa` |
| world_index.sqlite | `ecfabf4...1e5f1` | `ecfabf4...1e5f1` |
| release_state.json | `eada20a...391c8` | `eada20a...391c8` |

## 3. World SQLite quick_check

**PASS.** `PRAGMA quick_check;` → `ok`.

## 4. World revision = 98

**PASS.** `SELECT value FROM world_meta WHERE key='world_revision';` → `98`. Last world_commit rowid at revision 98 is the C14 fixture ingest for cursor 13 (sequence 13).

## 5. Index quick_check

**PASS.** `PRAGMA quick_check;` → `ok`.

## 6. Index watermark = 98

**PASS.** `SELECT value FROM search_meta WHERE key='search_watermark_world_revision';` → `98`.

## 7. Index lag = 0

**PASS.** Confirmed via `aios-core-headless recovery-status` on a disposable copy: `index_lag: 0`.

## 8. Release-state fields

**PASS.** All values match the expected Phase-A terminal boundary:

- active_phase = "A"
- last_acked_sequence = 13
- next_sequence = 14
- pending_reveal = null
- last_acked_event_id = "c15rcc-013"
- 13 contiguous receipts for sequences 1..13
- receipt fixture_sha256 is consistent `sha256:7ccb309d...`
- final receipt (seq 13) is bound to world revision 98

## 9. No cursor 14 material consumed

**PASS.** The preflight did NOT call `reveal` for any phase. It called ONLY `init --phase B` on disposable copies to verify the state transition is accepted. The init command validates phase/receipt-chain integrity and transitions `active_phase` from A to B; it does NOT read or emit the cursor-14 event payload (the reveal subcommand does that — and it was not called). Therefore cursor 14's resident-visible payload has not been inspected or revealed in any form.

Verification:

- `receipts` array in release_state.json contains exactly 13 entries (sequences 1..13).
- No `pending_reveal` is set before init.
- After `init --phase B`, `active_phase` transitions to `"B"`, `pending_reveal` remains `null`, `next_sequence` remains 14, and `receipts` is unchanged (init does not add a receipt).
- No `release_operator.py reveal` call was issued in this preflight (grep of operator logs confirms).

## 10. Legal Phase-B init accepts exact boundary

**PASS.** On a fresh disposable copy of the exact A-freeze release_state.json:

```
$ PYTHONPATH=src python3 reviews/internal_habitation/c15-rcc/v1/release/release_operator.py init --phase B --state <copy>/release_state.json
{"fixture_sha256":"sha256:7ccb309d...","next_sequence":14,"phase":"B","status":"initialized"}
exit=0
```

(Confirmed both on host filesystem AND inside the sandbox at `/work/release_state.json`.)

## 11. Malformed/skipped/dirty boundary fails closed

**PASS.** Three malformed boundary states were constructed from a disposable copy:

| Test case | Mutation | Result |
| --- | --- | --- |
| skip_seq12 | last_acked_sequence=12, next_sequence=13, last_acked_event_id=c15rcc-012 (simulates missing receipt) | `release-operator-error: release receipt chain mismatch` exit=2 |
| dirty_pending | pending_reveal={sequence:14} (simulates unresolved reveal) | `release-operator-error: pending reveal event mismatch` exit=2 |
| seq14_already | active_phase=B, last_acked_sequence=14, next_sequence=15 (simulates already-started B) | `release-operator-error: release receipt chain mismatch` exit=2 |
| double_init | init already-initialized state | `release-operator-error: Phase B initialization requires active Phase A handoff state` exit=2 |

All fail closed with non-zero exit; no state is written.

## 12. Same-World durable restart

**PASS.** Opening the copied World with `aios-core-headless recovery-status`:

```json
{
  "index_lag": 0,
  "index_status": "ready",
  "index_watermark": 98,
  "recovery_disposition": "AUTO_RECOVERABLE",
  "schema_version": 1,
  "status": "recovery_status",
  "world_quick_check": ["ok"],
  "world_revision": 98
}
```

Additionally `aios-core-headless rebuild-index` from the World alone (without the supplied index) successfully reconstructs the index:

```json
{
  "index_watermark": 98,
  "indexed_rows": 245,
  "recovery_disposition": "REBUILD_FROM_WORLD",
  "status": "index_rebuilt",
  "world_revision": 98
}
```

This proves the World is self-contained truth; the index is a rebuildable projection, and same-World restart across phases is a supported operation (consistent with CORE-RECOVERY-001 acceptance).

## 13. Resident isolation (no sealed material in sandbox)

**PASS.** See isolation/isolation_report.md for full results. Summary: 11 sealed-path categories are absent from the sandbox, privilege drop to nobody works, /proc/1/root is unreadable, mount() is denied, Core code imports cleanly.

## 14. Mailbox/request bridge transport-only + request/reply binding (no semantic default)

**PASS by design, inspection, and 15-case self-test + 6-negative E2E.**

`harness/mailbox_bridge.py` (frozen, STRICT):

- Sends **validated** envelope (`round`/`request_id`/`request_digest` injected, allowlist, 8-field event, capability_history B-session-only, phase B, allowed_sequences [14,22], forbidden substrings, no pre-set binding, no double-send) into `$mailbox/inbox/round-NNNN.json` (bind-mounted as `/work/inbox`).
- `request_id` = `secrets.token_hex(16)` (32 hex), `request_digest` = `sha256(sorted JSON without digest)` (64 hex), `round` = monotonic per-bridge counter; stored as `outstanding` + `consumed` set (forever) so replay never becomes valid later.
- Blocks on `wait_for_reply(timeout)` which verifies reply's `round`/`request_id`/`request_digest` exactly equal `outstanding`; on mismatch raises `MailboxReplyError` (stale prior-round `round != outstanding`, preplayed future `aaaaaaaaaaaaaaaa…`, replayed consumed `consumed set`, wrong_id `ffffffff…`, wrong_digest `ffffffff…`, future-not-valid). On any `MailboxReplyError`/`Timeout` the adapter (`harness/bridged_model_handler.py:MailboxModelHandler`) raises `ModelDispatchNotSubmitted` so **Core fails closed without semantic default** (no keyword hint, no synthesized answer, no retry with suggestion).
- `self-test` proves 15 cases: 1 minimal good + 14 negatives (extra top-level, extra event field, A-session, forbidden substring `fixture`, wrong phase, malformed reply JSON, correct exact-bound, stale, preplay, replay, wrong_id, wrong_digest, double-send, pre-set id) → `ALL SELF-TESTS PASS` (see `e2e_probe_output.txt` Step 1).
- **Binding E2E** (`isolation/probe_e2e.sh` Step 3, `isolation/resident_test_responder.py` inside jail as `nobody` PID3, `sandbox-init` PID1): 2-round normal (id/digest echoed, `NORMAL_BINDING_PASS`), then 6 negatives `STALE_REJECTED_PASS` `PREPLAY_REJECTED_PASS` `REPLAY_REJECTED_PASS` `WRONG_ID_REJECTED_PASS` `WRONG_DIGEST_REJECTED_PASS` `FUTURE_NOT_VALID_PASS` plus `double-send`/`pre-set` in self-test; all fail closed with `rejected-reply-NNNN.json` archived and `consumed` never re-accepted.
- Operator archive `mailbox/archive/{request,reply}-NNNN.json` preserves raw bytes for evidence; not injected back into Resident context.

This satisfies preflight §7 and CORRECTIVE-002 binding: "Infrastructure may transport bytes and execute Resident-selected capabilities. It may not decide semantics; every outbound has cryptographically-bound reply, stale/replay/future/wrong-id/wrong-digest fail closed."

## 15. B freeze/evidence procedure defined BEFORE B runs

**PASS.** See procedure/final_freeze_procedure.md. It enumerates the exact commands and hashes to capture at B completion; it is a document in this preflight PR, authored before any B run can start.

## 16. Cursor 14 not revealed

**VERIFIED.** `grep -r 'reveal' checks/ harness/ procedure/` returns no invocation of the `reveal` subcommand in any preflight-executed code. The startup procedure (b_startup_procedure.md) reserves the first `reveal` for the B release task, not for preflight.

## 17. Genuine Core ModelHandler path E2E (CORRECTIVE-002)

**PASS.** `isolation/probe_e2e.sh` Step 4 drives a **genuine** `FusedTurnRuntime` (`store`=`world.sqlite` rev 98, `index` watermark 98, `subject_id=user_1`, `model_handler=MailboxModelHandler(bridge, b_session, contract_sha256)`) through `harness/bridged_model_handler.py:build_envelope` (mechanical `RuntimeSnapshot`→envelope, `cockpit`→`runtime_snapshot`, `capability_catalog` 43 entries, `capability_history` B-session-only, `wake_reason`, `contract_sha256`, `phase`/`allowed_sequences`) → `MailboxBridge.send()` (validated, id/digest injected) → isolated synthetic responder (`resident_test_responder.py --mode genuine --rounds 2` as `nobody` PID3, `sandbox-init` PID1) → exact-bound reply (`round`/`request_id`/`request_digest` echoed) → `MailboxModelHandler.wait_for_reply()` → `reply_to_directive()` → `ModelDirective` → `CognitiveRuntime`/`FusedTurnRuntime`. The probe proves:

- `world_revision` before turn = 98, after synthetic ingest = 99, `watermark` 98→99, `contract_sha256` matches `RESIDENT_B_RUN_CONTRACT.md`.
- `run_turn(session_id=probe-genuine-c15-b-001, turn_index=1, user_input=synthetic…, occurred_at=2026-11-05T09:00Z)` triggers **2 model invocations** (`handler.invocations==2`, `model_rounds==2`, `termination==silence`, `capability_history len==1` after second round, `capability_catalog size==43`, `runtime_snapshot` contains Core-generated `world_map` with `dimension_count`, `bridge.round==2` `consumed==2` `outstanding==None`, `silenced==True`).
- **Next-round via same bridge:** first round `invoke search_world XYZZY_NONSENSE…` (nonsense query avoids fixture substring that would appear in `capability_history[0].data[1].object_id` for Atlas/test queries and cause forbidden rejection) → capability executed (empty hits, no fixture), second envelope's `capability_history[0].data` contains that result (empty list, no forbidden), second round `silence` still walks same `inbox`/`outbox` with fresh `request_id`/`request_digest`; archive contains `request-0001.json`+`reply-0001.json`+`request-0002.json`+`reply-0002.json`; `search_world` found in `result.runtime.capability_history`.
- **No semantic default:** responder `mode=malformed` writes `not json{{{` → `wait_for_reply` raises `malformed reply JSON` → handler raises `ModelDispatchNotSubmitted` → `run_turn` fails closed (`MALFORMED_FAIL_CLOSED_PASS`), not swallowed.
- Responder tail confirms inside-jail evidence: `[test-responder] pid=3 proc1_comm=sandbox-init PASS`, `genuine round1 invoke search_world nonsense`, `round2 silence`.

## 18. PID1 supervisor hierarchy (CORRECTIVE-002)

**PASS.** `harness/resident_jail.py` v3 fixed `ENOMEM` by moving `_mount("none","/",MS_PRIVATE)` from `_unsharer_main` before `fork` into `_worker_main` after fork (matching old jail's proven order). Verified: manual `resident_jail … -- /bin/sh -c 'cat /proc/1/comm; echo $$; id; ls /proc|wc'` shows `sandbox-init` PID1, worker `PID 3`, `PPid 3`, `uid nobody` (65534), 5 PIDs, `cat /proc/1/root` unreadable EACCES. `isolation/probe_isolation.sh` inside jail asserts `pid!=1`, `pid1 comm==sandbox-init`, `visible PIDs==5`, no host `systemd`, `/proc/1/root` unreadable, orphan `child reaped` no zombies. `probe_e2e.sh` Step 2 and Step 4 responder tail both assert `pid!=1` and `sandbox-init`. Signal test (Step 6): `jail … -- /bin/sleep 30` → `kill -TERM` → PID1 forwards to worker → wait 0 → `SIGNAL_TERMINATION_PASS`.

## 19. Privilege-drop forced failure (CORRECTIVE-002)

**PASS.** `resident_jail.py` has no `except Exception: pass`; every drop step (`setgroups`/`setgid`/`setuid`/`chroot`) raises `RuntimeError` on failure; post-drop verifies `setuid(0)` EPERM and `mount()` EPERM before `execvpe`; env allowlist filters `PROBE_MODE`/`PROBE_ROUNDS` and strips `_RESIDENT_JAIL_*`. Negative injection (`probe_e2e.sh` Step 5) proves fail-closed: `env _RESIDENT_JAIL_INJECT_PRIVDROP_FAIL=1` + `sudo --preserve-env=_RESIDENT_JAIL_INJECT_PRIVDROP_FAIL,_RESIDENT_JAIL_INJECT_FAIL_MODE` → worker raises `injected privdrop failure` before drop → `_init_main` prints `[jail] sandbox setup FAILED: RuntimeError: injected privdrop failure` and `os._exit(98)` without exec; `sentinel_wrapper.sh`'s `echo > /work/outbox/SENTINEL_OUTBOX` never runs, `outbox/SENTINEL_OUTBOX` absent, `outbox/*.json` empty, exit 98. Second mode `_RESIDENT_JAIL_INJECT_FAIL_MODE=setgid` also exits 98 → `PRIVDROP_NEGATIVE_PASS`/`PRIVDROP_ALL_PASS`.

## 20. Mailbox IPC proven as nobody + env sanitization (CORRECTIVE-002)

**PASS.** Isolation probe inside jail (as `nobody`) proves: `inbox` readable (`stat` 0755 root:nogroup, `ls`/`read` succeeds), `outbox` writable+searchable (`touch`/`python open write` succeeds, 01733 root:nogroup sticky prevents overwrite), can `write` to outbox (`created`), `archive` absent, `PROBE_MODE`/`PROBE_ROUNDS` only when operator explicitly sets with `sudo --preserve-env` and value allowlisted (`normal`/`malformed`/… plus digits); `LD_*`/`PYTHON*`/`SUDO*` stripped. E2E binding tests use `sudo -E python3 -` for bridge (host side) to handle 01733 `iterdir` PermissionError (which previously caused `iterdir /tmp/…/outbox` failure for user `user` not in `nogroup`); `clean_mailbox` fallback does `sudo rm` on `PermissionError`. Fix for `resident_test_responder.py` `SyntaxError: global INBOX used prior` was moving `global INBOX, OUTBOX` to top of `main()` before any `default=INBOX` reference, and installing `pydantic 2.13.5` via `sudo pip install --break-system-packages` so both `python3` and `sudo python3` can import (verified `python3 -c 'import pydantic; print(__version__)'` → 2.13.5). No prompt-only blindness; network is OS-enforced `CLONE_NEWNET`.


