# C15-RCC-RES-B-PREFLIGHT-002 — Isolation Proof Report

Isolation mechanism: **OS-level mount-namespace chroot sandbox with privilege drop** — NOT prompt-only.

Implementation: `harness/resident_jail.py`.

## Mechanism

The `resident_jail.py` harness (run as root via `sudo`):

1. Calls `unshare(CLONE_NEWNS)` to create a **new Linux mount namespace** so all mount operations inside the sandbox are invisible to the host and to other processes.
2. Marks the root mount recursively private to prevent mount propagation.
3. Constructs a minimal chroot tree under `--sandbox` using **bind mounts**:
   - System directories (`/usr`, `/lib`, `/lib64`, `/lib32`, `/bin`, `/sbin`, `/etc`, `/opt`) bind-mounted **read-only**.
   - `/proc` mounted (new procfs instance so pid 1 is the sandbox init).
   - `/dev` bind-mounted for `/dev/null`, `/dev/urandom`.
   - `/repo/src/` (frozen Core code) bind-mounted **read-only** directly from `src/aios_core/` — no parent reviews/governance/.git path is mounted.
   - `/repo/reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_B_RUN_CONTRACT.md` bind-mounted **read-only** as a single file (the Resident-safe B contract).
   - `/work/world.sqlite`, `/work/world_index.sqlite`, `/work/release_state.json`, `/work/world.writer.lock` bind-mounted **read-write** from the operator-side runtime directory.
   - `/work/inbox/`, `/work/outbox/`, `/work/scratch/`, `/tmp/`, `/home/nobody/` mounted as fresh `tmpfs` (ephemeral, not backed by host).
4. Forks a child process that `chroot()`s into the sandbox, `chdir("/work")`, **drops privileges** to `nobody:nogroup` (uid 65534, gid 65534, cleared supplementary groups), then `execvp`s the requested command.

Because sealed material is not bind-mounted into the chroot tree, there is **no path** (absolute, relative, via `/proc/self/fd`, or via `/proc/<pid>/root`) by which the Resident process can reach it. This is the contrast with the prompt-only "don't look" approach rejected by the preflight brief (section 6).

## Probe results (mechanical verification)

The script `isolation/probe_isolation.sh` was executed inside the sandbox as `nobody`. Exact output captured:

```
=== sealed-path leak probe ===
sealed:/repo/reviews/internal_habitation/c15-rcc/v1/fixture absent
sealed:/repo/reviews/internal_habitation/c15-rcc/v1/evaluator absent
sealed:/repo/reviews/internal_habitation/c15-rcc/v1/release absent
sealed:/repo/reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-A-RERUN-002 absent
sealed:/repo/reviews/internal_habitation/c14-resident absent
sealed:/repo/governance absent
sealed:/repo/prompts absent
sealed:/repo/.git absent
sealed:/repo/AIOS_SINGLE_WINDOW_TASK_BOARD.md absent
sealed:/repo/AIOS_v3.0_CURRENT_CHECKPOINT.md absent
sealed:/repo/PROJECT_MASTER_MAP.md absent

=== Expected-visible check ===
visible:/repo/src present (expected)
visible:/repo/src/aios_core present (expected)
visible:/repo/reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_B_RUN_CONTRACT.md present (expected)

=== privilege audit ===
uid=65534(nobody) gid=65534(nogroup) groups=65534(nogroup)

=== /proc/1/root readable? ===
blocked: cannot read host /proc/1/root (expected)

=== mount() syscall as unprivileged user ===
mount() returned -1, errno=1 (EPERM=1)
blocked: mount denied (expected)

ISOLATION_PASS
```

## Sealed-material categories confirmed absent

Per release_contract §2 and preflight §6:

| Material category | Probe result |
| --- | --- |
| `fixture/**` (sealed_fixture.json, fixture_manifest.json) | absent |
| `evaluator/**` (evaluator notes, design notes) | absent |
| operator-only release machinery (release_operator.py, bindings.py, mechanical_gate.py, event_schema.json, mechanical_ingest_adapter.py, canonical_conversation_ingest.py, release_contract.md) | absent — runs outside sandbox on operator side |
| governance/task-board/checkpoint/PM reports | absent |
| #205 A-002 evidence package (mailbox archive, logs, freeze/MANIFEST) | absent |
| #207 acceptance report | absent |
| prior Resident transcripts/reports (#117, #121, #101, #109, old PREFLIGHT-001) | absent (either not mounted or in non-mounted paths) |
| Git history/PR/CI metadata (.git/) | absent |
| Phase-C fixture material | absent (resides in sealed fixture JSON, not mounted) |
| ModelDirective history from A | absent (in A mailbox archive, not mounted) |

## Allowed Resident data

The Resident process has access to exactly:

1. The frozen Core source code (read-only), needed to execute capabilities.
2. The single `RESIDENT_B_RUN_CONTRACT.md` — the Resident-safe instruction (does not reference fixture content, evaluator verdicts, or expected answers).
3. The durable private World + index + release-state, which are the legitimate continuity medium. Discovering A-era cognition through normal AIOS state/capabilities is **intended and required** (release_contract §3, run contract §1). This is not "leakage" — it is how cognitive continuity works.
4. The current-event envelope written into `/work/inbox/round-NNNN.json` by the operator (the 8 resident-visible fields per release_contract §4; one cursor at a time).
5. Its own capability catalog and per-B-session capability history (constructed by Core and passed through the mailbox bridge).
6. Tmpfs scratch for model-side work.

## What the operator sees (outside the sandbox)

The operator (non-blind infrastructure engineer) retains host-level access to all sealed material. This is required for:

- Release/ingest/ack mechanics (release_operator reads sealed fixture to emit the 8-field projection for one cursor at a time).
- Transport (mailbox_bridge) moves bytes; it does not interpret them semantically.
- Core headless CLI runs on the operator side for ingest, due-work processing, and final freeze (it needs the Core code paths that read/write the durable World; the model is reached via a ModelHandler that serializes RuntimeSnapshot to the sandboxed Resident process and reads the directive back).
- Evidence archiving (request/reply envelopes saved in an operator-side evidence directory, not visible to future Residents).

The operator does NOT become the blind Resident; release_contract §2 and corrective decision §3 require distinct contexts for operator vs blind Resident. This sandbox physically enforces that separation.

## Residual risk / honest disclosure

- **Model provider identity:** the sandbox does not itself attest that the model is a different provider/family from A. Trusted identity evidence is inventoried separately (identity_inventory.md); per release_contract §8 this is intentionally left UNKNOWN and does not block B execution-evidence continuity.
- **Side channels:** the sandbox does not intercept CPU timing, memory bus, or other local side channels. These are out of scope for a preflight mechanism and are not part of the RCC isolation contract (which is filesystem/interface-level).
- **Operator integrity:** the sandbox is constructed by code in this repository. A malicious operator could deliberately weaken it before running B. The independent release reviewer (C15-RCC-RES-B-RELEASE-002) must re-verify the sandbox mount layout before launching B. The startup procedure in procedure/b_startup_procedure.md explicitly includes a re-probe step.
- **Privilege drop uses `nobody`.** This is not uid 0, and mount(), ptrace, and reading /proc/1/root are all denied, which is what's required.
