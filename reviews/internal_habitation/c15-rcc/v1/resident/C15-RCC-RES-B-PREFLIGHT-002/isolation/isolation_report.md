# C15-RCC-RES-B-PREFLIGHT-002-CORRECTIVE-002 — Isolation Report (Hardened + Binding + Genuine)

Isolation mechanism: **OS-enforced mount + PID + network namespaces, bind+remount read-only, bind-mounted host mailbox for explicit IPC, chroot, privilege drop to `nobody` (fail-closed), no sysfs**. NOT prompt-only.

Implementation: `harness/resident_jail.py`.

## Namespaces created (blockers 1, 2)

The jail wrapper invokes `unshare(CLONE_NEWNS | CLONE_NEWPID | CLONE_NEWNET)` in a forked child:

- **MOUNT namespace (`CLONE_NEWNS`):** All bind mounts are invisible to the host and to other processes. The root mount is recursively made private (`MS_REC|MS_PRIVATE`) so mounts never propagate back.
- **PID namespace (`CLONE_NEWPID`):** A fresh PID space with **PID1 supervisor** (`sandbox-init`): host → unsharer (unshare) → fork init (PID1, `prctl(PR_SET_NAME)=sandbox-init`) → fork worker (PID ≥2). Init **never** runs Resident code; it only reaps zombies (orphan grandchild reaped, no zombies), forwards TERM/INT/HUP to worker, and returns worker's exit code. Worker does private mount, bind mounts, chroot, privdrop to `nobody`. Host pids invisible through freshly-mounted `/proc` (verified: 5 PIDs visible in /proc, `cat /proc/1/comm == sandbox-init`, no `systemd`/`init`, `/proc/1/root` unreadable EACCES acceptable, `ls /proc` small count, host init not visible).
- **NETWORK namespace (`CLONE_NEWNET`):** No network interfaces exist except loopback (which is brought up via SIOCSIFFLAGS so AF_UNIX/localhost works). No routes, no default gateway, no eth0. Verified: connect() to github.com/140.82.114.4:443, raw.githubusercontent.com/185.199.108.133:443, api.github.com/140.82.114.6:443, and 8.8.8.8:53 all return ENETUNREACH (errno=101).

Because the model handler (provider API calls) runs on the **operator side**, outside the sandbox, Resident access to the public internet is not required. The sandbox default is **no internet**. This eliminates the NETWORK_SEAL_BYPASS: the Resident cannot `urllib.request` raw.githubusercontent.com to re-read fixture/governance/PR content because there is no route.

## Read-only bind mounts verified (blocker 6)

We no longer rely on a single `MS_BIND|MS_RDONLY` (which the kernel may not enforce for pre-existing submounts). For every read-only path we do TWO mount calls:

```
mount(src, tgt, NULL, MS_BIND|MS_REC)
mount(src, tgt, NULL, MS_BIND|MS_REC|MS_REMOUNT|MS_RDONLY|MS_NOSUID|MS_NODEV)
```

This is the canonical Linux recipe for truly read-only bind mounts. Verification via `/proc/mounts` inside the sandbox shows `ro,nosuid,nodev` flags, and writes fail with EROFS (errno=30 "Read-only file system"):

```
/dev/root /repo/src ext4 ro,nosuid,nodev,...
dd: failed to open '/repo/src/TEST_RO': Read-only file system
```

The Resident-safe contract file is also mounted RO and cannot be overwritten.

## Privilege drop fail-closed (blocker 3)

Every security-sensitive step raises on failure; there is NO `except Exception: pass` in the hot path. Specifically:

- `setgroups([])` — failure raises `RuntimeError`.
- `setgid(nobody)` — failure raises.
- `setuid(nobody)` — failure raises.
- `chroot(sandbox)` — failure raises.
- After drop, we VERIFY:
  1. `os.geteuid() != 0` and `os.getuid() != 0`.
  2. `os.setuid(0)` raises OSError (EPERM) — we cannot re-acquire root.
  3. A test `mount("tmpfs", "/tmp/test_mount", ...)` returns EPERM.
- Only if ALL checks pass do we `execvp` the Resident command.

Negative testing: if `nobody` user is absent or any syscall fails, the child exits with status 98 BEFORE the Resident command is executed. The parent reports `[jail] sandbox setup FAILED: ...` and never execs.

## Mailbox IPC is a real host bind-mount (blocker 4)

We no longer rely on the operator "seeing" private tmpfs mounts. Instead:

- Operator creates `$RUN_ROOT/mailbox/{inbox,outbox,archive}` on the host.
- `inbox/` (root:nogroup, mode 0755) is bind-mounted rw into `/work/inbox`; only root (operator) can write; Resident (in group `nogroup`) can read.
- `outbox/` (root:nogroup, mode 01733 — sticky bit + group wx) is bind-mounted rw into `/work/outbox`; Resident can create new files (0644 nobody:nogroup) but cannot overwrite or delete operator/other-round files.
- `archive/` is operator-only (root:root mode 0700) and is **not mounted** into the sandbox.

IPC is therefore explicit, auditable, and does not require any magic to share mounts across namespaces — bind mounts of host directories are visible to both sides by design.

Probe verifies:
- inbox readable as nobody (0755 root:nogroup, worker uid 65534 can ls/read)
- outbox writable as nobody (01733 root:nogroup, sticky, worker can create 0644 files but cannot overwrite/delete others; write test succeeded, outbox searchable via bind-mounted host dir)
- /work/archive absent from sandbox (not mounted)
- **Request/reply binding:** every `send()` generates cryptographically-random `request_id` (32 hex via `secrets.token_hex(16)`) and canonical `request_digest` (SHA-256 of sorted JSON), injects `round`/`request_id`/`request_digest` into envelope, tracks `outstanding` + `consumed` set; `wait_for_reply()` verifies exact match on all three (round/id/digest) and rejects stale prior-round, preplayed future-round, replayed consumed, wrong-id, wrong-digest, future-does-not-become-valid-later (6 negatives + pre-set id rejection).
- 2-round synthetic normal binding (round1 id/digest echoed, round2 id/digest echoed, `NORMAL_BINDING_PASS`)
- 6 binding negatives proven (STALE_REJECTED_PASS, PREPLAY_REJECTED_PASS, REPLAY_REJECTED_PASS, WRONG_ID_REJECTED_PASS, WRONG_DIGEST_REJECTED_PASS, FUTURE_NOT_VALID_PASS) plus double-send and pre-set rejection in self-test
- Archive evidence: `mailbox/archive/request-NNNN.json` + `mailbox/archive/reply-NNNN.json` preserved for both rounds, consumed ids never re-accepted
- Malformed envelope (extra top-level, extra event field, A-session in history, forbidden substring, wrong phase) rejected before inbox write; round counter does not advance

## Strict envelope validation (blocker 5)

`harness/mailbox_bridge.py` implements strict allowlist validation BEFORE writing the envelope to inbox. Violations raise `MailboxEnvelopeError` and no file is written:

- Top-level keys must be in `{round, event, runtime_snapshot, capability_catalog, capability_history, wake_reason, is_periodic_review, is_summary_request, contract_sha256, phase, allowed_sequences}`.
- `event`, if present, must contain EXACTLY the 8 release_contract §4 fields. Any extra field (e.g. `fixture_secret`) triggers rejection.
- Forbidden substrings (`fixture`, `evaluator`, `governance`, `sealed_fixture`, path references to sealed files) anywhere in the envelope trigger rejection.
- `capability_history[*].session_id` must equal the current B session id (A-session references rejected).
- `phase` must be `B`; `allowed_sequences` must equal `[14,22]`.
- **Binding fields `round`/`request_id`/`request_digest` are BRIDGE-ASSIGNED**; envelope must not pre-set them (rejected).
- **Double-send while outstanding** is rejected (no file write, no advance).
- Reply validation: `round`/`request_id`/`request_digest` must exactly equal outstanding; `action` must be in `{silence, end_turn, invoke_capability, summary_response, round_repair_request}`; extra reply fields rejected; consumed ids stored forever so replay never becomes valid.

Self-tests in `mailbox_bridge.py self-test` exercise 15 binding-aware cases (including 6 negatives: stale, preplay, replay, wrong_id, wrong_digest, double-send, pre-set id, plus malformed reply, forbidden substring, A-session, extra field, wrong phase, extra top-level, double-send, correct binding); all 15 PASS.

## Privilege-drop fail-closed + synthetic negative injection (blocker 3)

Every security-sensitive step raises on failure; there is **no** `except Exception: pass` in the hot path. Post-drop verifies `setuid(0)` EPERM and `mount()` EPERM before exec. **Negative injection test** (`probe_e2e.sh` Step 5) proves fail-closed: operator sets ` _RESIDENT_JAIL_INJECT_PRIVDROP_FAIL=1` (host-side seam, never propagated into sandbox) → worker raises `RuntimeError("injected privdrop failure")` before `setgroups`/`setgid`/`setuid` → `_init_main` catches, prints `[jail] sandbox setup FAILED: RuntimeError: injected privdrop failure`, exits **98** without exec; `work/outbox/SENTINEL_OUTBOX` is **not** created, `outbox/*.json` remains empty. Second injection ` _RESIDENT_JAIL_INJECT_FAIL_MODE=setgid` similarly exits 98. `sudo --preserve-env` is required so the seam is visible to the unprivileged parent before mount; sandbox env sanitization explicitly filters these keys so Resident cannot set them.

## Startup procedure filename bug fixed (blocker 7)

Fixed (see b_startup_procedure.md §1): copies are named `world.sqlite` / `index.sqlite` / `release_state.json` to match the names used by the headless CLI and release operator, and the digest check is run against those names. The startup procedure's Step 4 was also updated to pass `--mailbox-root` and to include an E2E probe step (Step 4a).

## E2E transport probe (blocker 8 + CORRECTIVE-002 4 remaining blockers)

`isolation/probe_e2e.sh` (must run as `sudo -E`; 6 steps, ends `E2E_PROBE_PASS`, raw log saved as `e2e_probe_output.txt`):

1. **Disposable lineage copy + digest verify:** copies `lineage_copy/private_world.sqlite → world.sqlite` etc., SHA-256 checks `626c6bb3…` / `ecfabf4…` / `eada20a…` OK, lineage copy `world_revision=98` `watermark=98`.
2. **Mailbox bridge self-tests (15 cases, including binding):** 1 minimal good + 14 negatives (extra top-level, extra event field, A-session, forbidden substring, wrong phase, malformed reply, correct exact-bound, stale, preplay, replay, wrong_id, wrong_digest, double-send, pre-set id) → `ALL SELF-TESTS PASS`.
3. **Hardened isolation probe inside sandbox (PID1 supervisor):** identity `uid=nobody`, PID namespace (`pid!=1`, `pid1 comm=sandbox-init`, 5 PIDs visible, no host init, `/proc/1/root` unreadable), orphan reap (child reaped, no zombies), network `ENETUNREACH` for github/raw/api/8.8.8.8, 13 sealed paths absent, RO-bind (`touch` denied, Python write EROFS, `/proc/mounts ro,nosuid,nodev`), mailbox perms (`inbox` readable, `outbox` writable searchable, `archive` absent), priv re-escalation (`setuid(0)` EPERM, `mount` EPERM) → `ISOLATION_PASS`, PID1 supervisor evidence OK.
4. **Mailbox binding E2E (normal + 6 negatives) via `resident_test_responder.py` inside jail as nobody:** `sudo --preserve-env=PROBE_MODE,PROBE_ROUNDS` + `sudo -E python3 -` for bridge (to handle 01733 outbox perms); responder validates `pid>=2`, `proc1_comm==sandbox-init`, `uid==65534`, network sealed, no archive. Tests: `normal` 2 rounds correct binding (`id=…` echoed), `stale` prior-round rejected (`round 1 != outstanding 2`), `preplay` future `aaaaaaaa…` rejected (`wrong id`), `replay` consumed `…` rejected (`replay of consumed`), `wrong_id` `ffffffff…` rejected, `wrong_digest` `ffffffff…` rejected, `future_not_valid` `cccccccc…` stays rejected after advancing → `ALL_BINDING_TESTS_PASS`.
5. **Genuine Core ModelHandler path E2E (`FusedTurnRuntime` → `BridgedModelHandler` → `MailboxBridge` → isolated synthetic responder → exact-bound reply → `MailboxModelHandler` → Core):** fresh `private_world` `world_revision=98` `watermark=98`, `contract_sha256=28d3262f…` (from `RESIDENT_B_RUN_CONTRACT.md`), `bridge` + `MailboxModelHandler(…)` (frozen adapter, `build_envelope` from real `RuntimeSnapshot`), responder `mode=genuine rounds=2` (`round1 invoke search_world XYZZY_NONSENSE…`, `round2 silence`) — use nonsense query to avoid fixture substring in second envelope's `capability_history[0].data[1].object_id`. `FusedTurnRuntime.run_turn(session_id=probe-genuine-c15-b-001, turn_index=1, user_input=synthetic…, occurred_at=2026-11-05T09:00Z)` invokes handler **twice** (`invocations==2`, `model_rounds==2`, `termination==silence`, `capability_history len==1`, `capability_catalog size==43`, `runtime_snapshot` contains Core-generated `world_map` at revision 99, `bridge.round==2` `consumed==2`, `archive/request-0001.json`+`reply-0001.json`+`request-0002.json`+`reply-0002.json` exist, `search_world` found in history, second round walked same bridge). After success, malformed reply (`mode=malformed` writes `not json{{{`) → `ModelDispatchNotSubmitted: malformed reply JSON` correctly fail-closed (`MALFORMED_FAIL_CLOSED_PASS`, no semantic default). Responder tail proves PID1 still `sandbox-init`, `uid nobody`, `invocations==2`.
6. **Privdrop injection negative + signal termination:** see privdrop section above (`PRIVDROP_NEGATIVE_PASS`/`PRIVDROP_ALL_PASS` exit 98, sentinel not created, no outbox reply); signal test: `jail … -- /bin/sleep 30` PID1 forwards TERM → worker exits, `wait` returns 0/128+15 → `SIGNAL_TERMINATION_PASS`.

Responder for all modes asserts (exit non-zero on violation): `uid==65534`, `pid!=1` & `proc1_comm==sandbox-init`, `/work/archive` absent, network sealed, envelope has `request_id`/`request_digest`, per-round binding echoed exactly. No real B fixture payload, no cursor 14 reveal (receipts still 13, `pending_reveal=null`, `next_sequence=14`), no Resident B/C cognition, no Core modification, no #205 modification.

## Probe raw outputs (captured 2026-09-25, saved alongside)

- `isolation/probe_output.txt` (60 lines, `ISOLATION_PASS`): proves `nobody` (65534), `sandbox-init` PID1, 5 PIDs, reap, ENETUNREACH×4, 13 sealed absent, RO deny, inbox/outbox/archive perms, EPERM.
- `isolation/e2e_probe_output.txt` (177 lines, `E2E_PROBE_PASS`): full run at `/tmp/b-preflight-e2e-3831` — digests OK, 15 self-tests PASS, isolation PASS, 7 binding tests PASS (normal+6 negatives with request_id/digest echoes), genuine 2-round `FusedTurnRuntime`→`MailboxModelHandler`→bridge→sandbox responder→Core (world_rev 98→99, watermark 98, contract 28d3262f…, invocations 2, model_rounds 2, termination silence, world_map present, catalog 43, archive 4 files, search_world in history, malformed fail-closed), privdrop injection exit 98 no sentinel, signal TERM PASS. Also `mailbox_bridge self-test` 15 PASS and `isolation_probe.log` retained at run_root.

Fresh raw logs are also reproduced in `corrective_002_report.md` Appendix.

## Remaining disclosed properties (CORRECTIVE-002 updated)

- **PID1 is `sandbox-init` (15-char `prctl` name, also `/proc/self/comm`), worker is PID ≥2; init never runs payload, only reaps/forwards.**
- **Mount propagation is set `MS_PRIVATE` in worker after fork** (moved from unsharer before fork to avoid `ENOMEM` on immediate fork after `unshare`; matches old jail's proven order, verified `sandbox-init` PID1 still present).
- `/sys` not mounted; `/dev` bind-mounted; `/proc` fresh (5 PIDs, no host init), `/proc/1/root` unreadable.
- **Env sanitization:** only `PROBE_MODE` (allowlist `normal/malformed/stale/preplay/replay/binding/genuine`) and `PROBE_ROUNDS` (digits) are preserved when operator sets them; `LD_*`/`PYTHON*`/`SUDO*`/`_RESIDENT_JAIL_*` never propagated to sandbox; `PATH`/`HOME`/`TMPDIR` sanitized; `PYTHONPATH` forced to `/repo/src`.
- **RO bind verified via both `touch` and Python `open().write()`** raising `EROFS`/`EACCES`, plus `/proc/mounts` shows `ro,nosuid,nodev`.
- **Mailbox perms verified as `nobody`:** `inbox` read+exec, `outbox` write+exec (create succeeds, list via `sudo rm` fallback due to 01733, not via `iterdir`), archive absent; host `inbox` 0755 root:nogroup, `outbox` 01733 root:nogroup, `archive` 0700 root:root.
- **Signal forwarding:** `sandbox-init` installs `SIGTERM`/`SIGINT`/`SIGHUP` handlers that `kill(worker_pid, sig)`; on `SIGCHLD` reaps all children; `unsharer` also forwards to init; `probe_e2e.sh` Step 6 proves `sleep 30` terminated via `kill -TERM` → wait 0.
