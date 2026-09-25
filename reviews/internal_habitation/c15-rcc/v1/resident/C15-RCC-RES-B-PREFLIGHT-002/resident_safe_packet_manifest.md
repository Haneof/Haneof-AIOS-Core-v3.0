# C15-RCC-RES-B-PREFLIGHT-002 — Resident-Safe Packet Manifest (CORRECTIVE-003 frozen)

The future Resident B model process (real B, not synthetic probe) will be launched inside the OS-level sandbox defined by `harness/resident_jail.py` + `harness/bridged_model_handler.py` (ProductionResidentHandler). The filesystem view inside the sandbox contains ONLY what is listed below. Everything else — `fixture/`, `evaluator/`, `governance/`, `.git/`, `prompts/`, task board, checkpoint, PM reports, A-002 evidence, other Resident contracts — is NOT mounted and cannot be read, listed, searched, or indirectly referenced. This manifest is authoritative; any older document claiming host network inheritance, tmpfs inbox/outbox, or no genuine model roundtrip is superseded.

## Read-only, inside sandbox (`/repo/...`) — bind + remount RO, `ro,nosuid,nodev`

| Sandbox path | Source on host | Purpose | Mount |
| --- | --- | --- | --- |
| `/repo/src/` | `src/aios_core/` at frozen tree `fe77f8a0706acfaf369041d0882b6d0e6de39f22` | Frozen Core code | `MS_BIND+MS_REMOUNT+MS_RDONLY` |
| `/repo/reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_B_RUN_CONTRACT.md` | same file at frozen RC `28d3262f…` | Single Resident-safe run contract (system instruction) | single-file `MS_BIND+MS_REMOUNT+MS_RDONLY` |

Note: `/repo/reviews/` is created but only the single contract file is mounted. The rest of `/repo/reviews/...` (fixture, evaluator, release, prior evidence, C14) is absent — verified `ls /repo/reviews/...` fails inside jail.

## Read-write durable state (`/work/...`) — host bind RW, operator-owned runtime dir

Bind-mounted from an operator-owned `$RUN_ROOT/runtime` (outside jail). These are the SAME files the operator uses for `recovery-status`/`rebuild-index`/`init --phase B`; the sandbox sees them as RW but with operator-controlled leases.

| Sandbox path | Description | Host perm |
| --- | --- | --- |
| `/work/world.sqlite` | Private durable World (A-002 lineage rev98 → B) | `tmp` file bind `MS_BIND|MS_NOSUID|MS_NODEV` |
| `/work/world_index.sqlite` | Synchronized search index (watermark98, lag0) | same |
| `/work/release_state.json` | Phase receipt chain (A→B after `init --phase B`) | same |
| `/work/world.writer.lock` | Writer lease | same |

## Mailbox IPC — host bind IPC (NOT tmpfs) + operator archive NOT in sandbox

| Path | Location | Purpose | Perm | Visible inside sandbox? |
| --- | --- | --- | --- | --- |
| `/work/inbox/` | `$RUN_ROOT/mailbox/inbox` bind RW | Operator → Resident validated envelopes (one round at a time, round/request_id/request_digest bound) | host `0755 root:nogroup` | YES (`/work/inbox`) — Resident (group `nogroup`) can read, operator (root) writes |
| `/work/outbox/` | `$RUN_ROOT/mailbox/outbox` bind RW | Resident → Operator replies (same binding echo) | host `01733 root:nogroup` (sticky) | YES (`/work/outbox`) — Resident can create 0644 files, cannot overwrite others |
| `$RUN_ROOT/mailbox/archive/` | host only | Operator archive `request-NNNN.json` / `reply-NNNN.json` / `rejected-*` | host `0700 root:root` | **NO** — not mounted, `ls /work/archive` fails |
| `/work/scratch/` | tmpfs 256m mode 0700 | Model-side temp, ephemeral, wiped on namespace exit | tmpfs | YES, but not durable |

Archived copies live in operator-side `mailbox/archive` (outside sandbox) so B execution evidence is preserved without exposing A archives to B. The probe verifies `inbox` readable, `outbox` writable searchable, `archive` absent, and extra top-level / extra event field / A-session / forbidden path / wrong phase all fail closed before file write (no inbox file, no round advance).

## System (minimal RO bind + fresh mounts)

- **OS tree RO:** `/usr`, `/lib`, `/lib64`, `/lib32`, `/bin`, `/sbin`, `/etc`, `/opt` — minimal for Python + pydantic, each `MS_BIND` then `MS_REMOUNT|MS_RDONLY|MS_NOSUID|MS_NODEV` (verified `touch` and Python `open().write` raise `EROFS` and `/proc/mounts` shows `ro,nosuid,nodev`).
- **Loopback only:** `CLONE_NEWNET` — no eth0, no default route; only `lo` brought up via `SIOCSIFFLAGS`. Verified `connect(140.82.114.4:443)`, `raw.githubusercontent.com`, `api.github.com`, `8.8.8.8:53` all `ENETUNREACH 101`. **No public internet inside Resident jail.**
- **PID namespace + supervisor:** `CLONE_NEWPID` — fresh `/proc` (5 PIDs), `PID1 = sandbox-init` (`prctl PR_SET_NAME`, `comm=sandbox-init`), worker `PID≥2`. PID1 never runs payload, only reaps zombies and forwards `TERM/INT/HUP` to worker; `unsharer` also forwards to PID1. Verified `cat /proc/1/comm == sandbox-init`, `my pid 39 !=1`, `ls /proc` small, no host `systemd`, orphan `waitpid` no zombies.
- **Mount propagation private:** `_mount("none","/",MS_REC|MS_PRIVATE)` is **fail-closed** (no `except: pass`; test seam `_RESIDENT_JAIL_INJECT_MS_PRIVATE_FAIL=1` forces `RuntimeError` → `exit 98` before any bind/proc/chroot/exec, sentinel not executed, outbox empty). Previously `CLONE_NEWNS|MS_REC|MS_PRIVATE` was `try: pass` (fail-open) — now fixed.
- **`/proc` fresh:** `proc` `MS_NOSUID|MS_NODEV|MS_NOEXEC`, only own namespace; `read /proc/1/root` denied (EPERM).
- **`/dev` minimal:** `tmpfs` at `/dev` (8m) then **only** `null`, `zero`, `urandom`, `random` individually bind-mounted (`MS_BIND`), plus `/dev/fd → /proc/self/fd` symlink and `stdin/out/err → /proc/self/fd/0-2`. **No whole-host `/dev` bind.** Verified `ls /dev` shows only those 4 + `fd`, no `sda`, `tty`, `mem`, `kvm`, `block/*`. Adversarial probe (`open /dev/sda`, `open /dev/tty`, `open /dev/mem` all `ENOENT/EPERM`) passes.
- **`/tmp` and `/home/nobody`:** separate `tmpfs` (`/tmp` 64m 1777, `/home/nobody` 16m 0700), `chroot(sandbox)` then `chdir(/work)`.
- **Privdrop fail-closed:** `setgroups([])`, `setgid(nobody)`, `setuid(nobody)` each raise `RuntimeError` on failure; post-drop verifies `geteuid!=0`, `setuid(0)` EPERM, `mount(tmpfs, /tmp/test_mount)` EPERM before `execvpe`. Injection seams `_RESIDENT_JAIL_INJECT_PRIVDROP_FAIL=1` and `_RESIDENT_JAIL_INJECT_FAIL_MODE=setgid/setuid/setgroups` both `exit 98` (no sentinel, no outbox reply). `sudo --preserve-env` required for seam to be visible to parent before mount; sandbox env filtering strips it.

## Production model adapter — exact file/module (BLOCKER 1)

**Frozen:** `harness/bridged_model_handler.py`

- **ProductionResidentHandler** (frozen production path, Path A — external trusted model broker):
  - `Core RuntimeSnapshot (cockpit/world_map/capability_catalog/history/wake_reason/round_index) → build_envelope(snapshot, b_session, contract_sha256, current_event)` → Resident-safe envelope (11 top-level allowlist fields, `event` is either `None` (synthetic) or exact current 8-field projection `event_id/sequence/occurred_at/dimension/source_kind/source_class/modality/resident_visible_payload` with `sequence 14..22`, `phase B`, `allowed_sequences [14,22]`, `contract_sha256`, no extra keys). `current_event` is the ONLY channel for the reveal-provided projection; `event=None` means no cursor has been revealed for that turn (synthetic).
  - `build_model_request(contract_text, envelope)` → **exact** provider request: `{"system": <exact bytes of RESIDENT_B_RUN_CONTRACT.md>, "messages": [{"role":"user","content": JSON(envelope)}]}` — no repo path, no fixture, no evaluator, no governance, no A transcript, no PM report, no archive. Provider visibility is exactly `contract + envelope`.
  - `provider_client.invoke(request)` runs **outside the jail** (operator / trusted broker side, with `CLONE_NEWNET` still sealed inside). For preflight, `FakeProviderClient(provider="fake-provider", model="fake-model-v1", request_id_prefix="fake-req-")` walks the same code path; for real B, replace with `RealProviderClient` (same interface, same file unchanged).
  - Raw provider result → parsed as Resident reply JSON → **strict validate_reply** (common `round/request_id/request_digest/action` + per-action allowlist) + **binding verification** (`round/request_id/request_digest` must exactly equal outstanding `round/request_id/request_digest`; stale/preplay/replay/wrong-id/wrong-digest fail closed) → **production `reply_to_directive_production`** maps **REAL provider metadata**: `provider/model/request_id` from `ProviderResponse` (or `"UNKNOWN"` if not credibly available), `usage` from `ProviderResponse.usage` (total/input/output tokens as provider reported, or `None`/`0` if unavailable — never `total_tokens=10` synthetic), `provenance=ModelCallProvenance(provider=actual or "UNKNOWN", model=actual or "UNKNOWN", request_id=actual or "UNKNOWN")`.
  - Every model round (including capability-result follow-up) walks the **same** adapter (verified: one `run_turn` triggers 2 handler invocations, `envelope round 1 → reply invoke search_world` → capability executed → `envelope round 2` with `capability_history` containing that result including `obs_c14_fixture_*` legally → `silence`).

- **SyntheticProbeHandler** (disposable probe only, mailbox bridge):
  - Uses `MailboxBridge(inbox,outbox,archive,b_session)` + `resident_test_responder.py` inside jail as `nobody`. Hard-codes `provider="sandbox-bridge", model="synthetic-responder-v1", total_tokens=10` but is **separated in code** (`SyntheticProbeHandler` vs `ProductionResidentHandler`) and never used for real B. Probe proves 15 self-tests, 6 binding negatives, genuine `FusedTurnRuntime` 2-round, `current_event` projection, extra reply field reject, malformed fail-closed (Scheme A).

System instruction is always **exact** `RESIDENT_B_RUN_CONTRACT.md` bytes (sha `28d3262f…`); `PYTHONPATH` inside jail is forced to `/repo/src`, `HOME=/home/nobody`, `TMPDIR=/tmp`, `LD_*`/`PYTHON*`/`SUDO*` stripped, only `PROBE_MODE`/`PROBE_ROUNDS` when allowlisted.

## Explicitly NOT present in the sandbox (verified)

- `/repo/reviews/internal_habitation/c15-rcc/v1/fixture/` (sealed fixture)
- `/repo/reviews/internal_habitation/c15-rcc/v1/evaluator/` (oracle)
- `/repo/reviews/internal_habitation/c15-rcc/v1/release/` (operator)
- `/repo/reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-A-RERUN-002/` (A evidence)
- `/repo/reviews/internal_habitation/c14-resident/`
- `/repo/governance/` (task board, prompts, PM receipts)
- `/repo/prompts/`
- `/repo/.git/` (history, PR metadata)
- `/repo/AIOS_SINGLE_WINDOW_TASK_BOARD.md`, `/repo/AIOS_v3.0_CURRENT_CHECKPOINT.md`, `/repo/PROJECT_MASTER_MAP.md`
- `mailbox/archive/` (operator archive)
- `release_contract.md` (OPERATOR-only), any other Resident contract
- Phase C material (`cursors 23..30`)

## Resident process credentials

`nobody:nogroup` `65534:65534` inside jail. Cannot `mount()` (EPERM), `read /proc/1/root` (EPERM), write outside `/work/*` + `/tmp` tmpfs + `scratch`, signal host outside pid namespace. Host `nogroup` permits `inbox` read (`0755`) and `outbox` create (`01733` sticky).

## Network access (CORRECTIVE-003 frozen invariant)

**`CLONE_NEWNET` — no public internet inside Resident jail.** Provider network access occurs **only outside** the jail via the operator-side `ProviderClient`. The Resident inside the jail has only loopback (`lo` up, no eth0, no routes). Verified `connect` to `github.com:443`/`raw.githubusercontent.com:443`/`api.github.com:443`/`8.8.8.8:53` → `ENETUNREACH 101`. The model-visible context is exactly `contract + envelope`; following this manifest cannot recreate the original isolation failure.

