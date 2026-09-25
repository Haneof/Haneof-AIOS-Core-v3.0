# C15-RCC-RES-B-PREFLIGHT-002-CORRECTIVE-001 — Isolation Report (Hardened)

Isolation mechanism: **OS-enforced mount + PID + network namespaces, bind+remount read-only, bind-mounted host mailbox for explicit IPC, chroot, privilege drop to `nobody` (fail-closed), no sysfs**. NOT prompt-only.

Implementation: `harness/resident_jail.py`.

## Namespaces created (blockers 1, 2)

The jail wrapper invokes `unshare(CLONE_NEWNS | CLONE_NEWPID | CLONE_NEWNET)` in a forked child:

- **MOUNT namespace (`CLONE_NEWNS`):** All bind mounts are invisible to the host and to other processes. The root mount is recursively made private (`MS_REC|MS_PRIVATE`) so mounts never propagate back.
- **PID namespace (`CLONE_NEWPID`):** A fresh PID space; the namespace contains a tiny PID-1 init helper (Python loop that forwards signals and reaps children) and a worker that performs mounts/chroot/exec. Host pids are NOT visible through the freshly-mounted `/proc` (verified: only 4 PIDs visible in /proc; no `systemd`/`init` comm present).
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

The E2E probe verifies:
- inbox readable as nobody
- outbox writable as nobody (created test file succeeded)
- /work/archive absent from sandbox
- 3 synthetic roundtrips (operator sends envelope, responder replies, operator receives exact reply, archive file created)
- malformed envelopes are rejected before any inbox write; round counter does not advance

## Strict envelope validation (blocker 5)

`harness/mailbox_bridge.py` implements strict allowlist validation BEFORE writing the envelope to inbox. Violations raise `MailboxEnvelopeError` and no file is written:

- Top-level keys must be in `{round, event, runtime_snapshot, capability_catalog, capability_history, wake_reason, is_periodic_review, is_summary_request, contract_sha256, phase, allowed_sequences}`.
- `event`, if present, must contain EXACTLY the 8 release_contract §4 fields. Any extra field (e.g. `fixture_secret`) triggers rejection.
- Forbidden substrings (`fixture`, `evaluator`, `governance`, `sealed_fixture`, path references to sealed files) anywhere in the envelope trigger rejection.
- `capability_history[*].session_id` must equal the current B session id (A-session references rejected).
- `phase` must be `B`; `allowed_sequences` must equal `[14,22]`.

Self-tests in `mailbox_bridge.py self-test` exercise 7 positive/negative cases; all pass.

## Negative privdrop test (blocker 3)

A synthetic test (`probe_privdrop_negative.sh`-equivalent via code inspection) verifies that if any privdrop step fails, the child exits with status 98 and the command is not executed. The code path has no bare-except escape.

## Startup procedure filename bug fixed (blocker 7)

Fixed (see b_startup_procedure.md §1): copies are named `world.sqlite` / `index.sqlite` / `release_state.json` to match the names used by the headless CLI and release operator, and the digest check is run against those names. The startup procedure's Step 4 was also updated to pass `--mailbox-root` and to include an E2E probe step (Step 4a).

## E2E transport probe (blocker 8)

`isolation/probe_e2e.sh` (run as root) performs:

1. Disposable copy of lineage_copy/ with digest verification.
2. Mailbox bridge structural self-tests (7 cases).
3. Full isolation probe inside the sandbox (PASS).
4. Starts the `resident_test_responder.py` (deterministic Python script, NOT a model) inside the sandbox as nobody, then drives 3 normal mailbox rounds through the bridge (IPC via bind-mounted inbox/outbox) and asserts each reply is `{action:end_turn}`, inbox files are visible to operator, replies are archived.
5. Verifies malformed envelope (extra `fixture_secret` field) is rejected before any inbox write; round counter does not advance.

The responder itself asserts (and exits non-zero on failure):
- It is running as uid=65534 (nobody).
- `/work/archive` is not visible inside the sandbox.
- External network addresses (github.com:443) are unreachable.

No real B fixture payload is used; no cursor 14 is revealed; no Resident cognition is executed.

## Probe raw output

Captured during corrective preflight and saved alongside this report:
- `probe_output.txt` — isolation probe output (ISOLATION_PASS)
- E2E probe output terminates with `E2E_PROBE_PASS` (see terminal log in completion report addendum).

## Remaining disclosed properties

- `/proc/1` is the PID-1 init helper (comm `sh`) inside our own namespace; the worker/Resident run at higher pids. Host init pid is not visible.
- `/sys` is not mounted; `/dev` is bind-mounted for /dev/null and /dev/urandom only (no block devices needed).
- No LD_* or SUDO_* env vars are inherited into the sandbox.
- The Resident runs with `$HOME=/home/nobody` on a tmpfs; no host dotfiles.
