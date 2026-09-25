# C15-RCC-RES-B-PREFLIGHT-002 — Resident-Safe Packet Manifest

The future Resident B model process will be launched inside the OS-level sandbox defined by `harness/resident_jail.py`. The filesystem view inside the sandbox contains ONLY what is listed below. Everything else in the repository — fixture/, evaluator/, governance/, .git/, task board, checkpoint, PM reports, A-002 evidence, other Resident contracts — is NOT mounted and therefore cannot be read, listed, searched, or indirectly referenced.

## Read-only, inside sandbox (`/repo/...`)

| Sandbox path | Source on host | Purpose |
| --- | --- | --- |
| `/repo/src/` | `src/aios_core/` at frozen tree `fe77f8a...` | Frozen Core code (read-only bind mount) |
| `/repo/reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_B_RUN_CONTRACT.md` | `reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_B_RUN_CONTRACT.md` at frozen RC | The single Resident-safe run contract (read-only, single-file bind mount) |

Note: `/repo/reviews/` is created but only `internal_habitation/c15-rcc/v1/resident/RESIDENT_B_RUN_CONTRACT.md` is mounted under it. The rest of `/repo/reviews/...` (fixture, evaluator, release, prior evidence, C14) is simply absent.

## Read-write durable state (`/work/...`)

Bind-mounted from an operator-owned runtime directory outside the sandbox.

| Sandbox path | Description |
| --- | --- |
| `/work/world.sqlite` | Private durable World (A-002 lineage, will continue through B) |
| `/work/world_index.sqlite` | Synchronized search index |
| `/work/release_state.json` | Phase receipt chain (starts at A→B boundary after `init --phase B`) |
| `/work/world.writer.lock` | Writer lease (prevents multi-process corruption) |

## Scratch tmpfs (ephemeral, 256 MB, mode 0700)

| Sandbox path | Purpose |
| --- | --- |
| `/work/inbox/` | Operator → Resident envelopes (current round only) |
| `/work/outbox/` | Resident → Operator reply (current round only) |
| `/work/scratch/` | Model-side temp |

These are tmpfs mounts; their contents are NOT part of durable state and are wiped when the namespace exits. Archived copies of request/reply envelopes live in the operator-side evidence directory (outside the sandbox), so that B execution evidence can be preserved without exposing A archives to B.

## System (read-only bind mounts of host OS, minimal)

`/usr`, `/lib`, `/lib64`, `/lib32`, `/bin`, `/sbin`, `/etc`, `/opt` — minimal system tree for Python 3.11 + pydantic. `/proc` is mounted (the Resident can see only its own pid namespace; reading `/proc/1/root` is denied by privilege drop). `/dev/null`, `/dev/urandom` are available via `/dev` bind mount.

## Explicitly NOT present in the sandbox

The following paths do not exist inside the sandbox (verified by isolation probe; see isolation/isolation_report.md):

- `/repo/reviews/internal_habitation/c15-rcc/v1/fixture/`
- `/repo/reviews/internal_habitation/c15-rcc/v1/evaluator/`
- `/repo/reviews/internal_habitation/c15-rcc/v1/release/` (release operator stays outside)
- `/repo/reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-A-RERUN-002/`
- `/repo/reviews/internal_habitation/c14-resident/` (v2 release machinery stays outside)
- `/repo/governance/` (task board, prompts, PM receipts, corrective decisions)
- `/repo/prompts/` (all governance prompts including this preflight prompt)
- `/repo/.git/` (history, refs, PR metadata)
- `/repo/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
- `/repo/AIOS_v3.0_CURRENT_CHECKPOINT.md`
- `/repo/PROJECT_MASTER_MAP.md`
- A mailbox archive, A operator log, A RUN_COMPLETE report, A acceptance report
- Any file from `reviews/internal_habitation/c15-rcc/v1/evaluator/`
- Phase C material (cursors 23..30 reside in sealed fixture, unreachable)
- release_contract.md (OPERATOR-only)
- Any other Resident run contract (A's contract, C's future contract)

## Resident process credentials

Inside the sandbox, the Resident process runs as Unix uid/gid `nobody:nogroup` (65534:65534). It cannot:

- call `mount()` (EPERM)
- read `/proc/1/root` of host processes (permission denied)
- write outside the bind-mounted `/work/*` paths and tmpfs scratch
- send signals to host processes outside its pid namespace

## Network access

Network access is at the discretion of the release operator (needed to reach the model provider). The sandbox does not add network restrictions on top of the host environment; however the sealed material is not reachable via any URL hosted from this repository (there are none). The Resident does not get any Git, GitHub, or CI credentials; if a provider API key is required it is supplied only via the operator-side model handler outside the sandbox.
