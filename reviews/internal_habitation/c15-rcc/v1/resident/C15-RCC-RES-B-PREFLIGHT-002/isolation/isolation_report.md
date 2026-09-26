# C15-RCC-RES-B-PREFLIGHT-002 — Isolation Report (CORRECTIVE-010: hardened + binding + genuine + production + inherited-FD closure + canonical runbook order)

Isolation mechanism: **OS-enforced mount + PID + network namespaces, bind+remount RO (ro,nosuid,nodev), host bind-mounted mailbox IPC, minimal /dev (tmpfs + 4 nodes), chroot, privdrop to nobody (fail-closed), no sysfs**. NOT prompt-only.

Implementations: `harness/resident_jail.py` (sandbox), `harness/mailbox_bridge.py` (transport), `harness/bridged_model_handler.py` (production + synthetic).

## Namespaces (blockers 1,2,4,5,6)

Jail wrapper: `unshare(CLONE_NEWNS|CLONE_NEWPID|CLONE_NEWNET)` in forked child:

- **MOUNT (`CLONE_NEWNS`)** — private `MS_REC|MS_PRIVATE` **fail-closed** (no `except: pass`; injection `_RESIDENT_JAIL_INJECT_MS_PRIVATE_FAIL=1` → `RuntimeError` → exit 98 before any bind/proc/chroot/exec, sentinel not executed, outbox empty). Previously `try: pass` fail-open closed.
- **PID (`CLONE_NEWPID`)** — fresh `/proc` (4-5 PIDs), `PID1 = sandbox-init` (`prctl(PR_SET_NAME)=sandbox-init`, `comm` 15-char), worker `PID≥2`. Init never runs payload; only reaps zombies (orphan grandchild reaped, no zombies), forwards `TERM/INT/HUP` to worker, returns worker exit. Verified `cat /proc/1/comm == sandbox-init`, `my pid 43 !=1`, `ls /proc` small, no `systemd/init`, `/proc/1/root` unreadable.
- **NET (`CLONE_NEWNET`)** — only `lo` up via `SIOCSIFFLAGS`; no eth0, no route. Verified `connect(140.82.114.4:443)`, `185.199.108.133:443`, `140.82.114.6:443`, `8.8.8.8:53` all `ENETUNREACH 101`. **No public internet inside jail.** Provider network is **outside jail** via `ProviderClient` (Path A — external trusted broker) which sees only `{system: contract, messages: [envelope_json]}`. This eliminates docs claim “network at operator discretion inside jail” — now sealed and proven.

## RO binds verified (blocker 6)

Two-step `MS_BIND|MS_REC` then `MS_BIND|MS_REMOUNT|MS_RDONLY|MS_NOSUID|MS_NODEV` for `/repo/src` and contract file. Verified `touch` denied, Python `open().write` `EROFS 30`, `/proc/mounts` shows `ro,nosuid,nodev`.

## /dev minimal (blocker 6 fix)

Not whole-host `MS_BIND|MS_REC` of `/dev`. Now `tmpfs` at `/dev` (8m) + only `null/zero/urandom/random` individually `MS_BIND` + `/dev/fd → /proc/self/fd` + `stdin/out/err → /proc/self/fd/0-2`. Verified `ls /dev` shows only those 4 + `fd`/`stdin/out/err`, no `sda/sda1/nvme0n1/mem/kmem/kvm/port/tty/tty0/ptmx/pts/block`; `open(/dev/sda|mem|kvm|tty)` fails `ENOENT/EPERM`.

## Privdrop fail-closed (blocker 3 + 5)

No bare `except: pass`. `setgroups/setgid/setuid` raise `RuntimeError`; post-drop verifies `geteuid!=0`, `setuid(0)` `EPERM`, `mount(tmpfs,/tmp/test_mount)` `EPERM 1` before `execvpe`. Negatives:
- Generic ` _RESIDENT_JAIL_INJECT_PRIVDROP_FAIL=1` → exit 98 before exec, no sentinel, no outbox.
- ` _RESIDENT_JAIL_INJECT_FAIL_MODE=setgid` → exit 98.
Requires `sudo --preserve-env` so seam visible to parent before mount; sandbox env strips it.

## Mailbox IPC host bind (blocker 4)

Operator `$RUN_ROOT/mailbox/{inbox 0755 root:nogroup, outbox 01733 root:nogroup sticky, archive 0700 root:root not mounted}`. Bind `MS_BIND|MS_NOSUID|MS_NODEV` to `/work/inbox` (readable) and `/work/outbox` (writable searchable, 0644 create, cannot overwrite). Verified `nobody` can read inbox, write outbox, cannot see `/work/archive`. Not tmpfs (docs corrected).

## Strict envelope + path-aware leakage guard (blockers 2,3,8)

`mailbox_bridge.validate_envelope` before inbox write:
- Top-level 11 allowlist: `round/request_id/request_digest/event/runtime_snapshot/capability_catalog/capability_history/wake_reason/is_periodic_review/is_summary_request/contract_sha256/phase/allowed_sequences`.
- `event` exactly 8 fields: `event_id/sequence/occurred_at/dimension/source_kind/source_class/modality/resident_visible_payload`; `sequence 14..22`; `phase B`; `allowed_sequences [14,22]`.
- `capability_history[*].session_id` must equal B-session (A-session rejected).
- Forbidden **path** prefixes: `sealed_fixture, /repo/fixture, /repo/evaluator, /repo/governance, /repo/.git, /release/, /c14-resident` etc. **Bare `fixture` NOT forbidden** — legal durable World ids `obs_c14_fixture_5d4dfcf...` (Atlas search) are explicitly **allowed** (self-test 5b). Only `/repo/fixture/...` etc. blocked. This fixes legal durable World false positive.
- Bridge-assigned `round/request_id/request_digest` must not be pre-set; double-send while outstanding rejected.

Self-tests 15 PASS (including 5b legal fixture allowed, 7b extra reply field rejected).

## Reply binding + strict schema (blockers 8,9)

`validate_reply` per-action allowlist: `silence {round,request_id,request_digest,action}` only, `invoke_capability {+capability,arguments}`, `end_turn {+response}`, `summary_response {+response|summary}`; extra fields → `MailboxReplyError`. `round_repair_request` structurally allowed but **handler** treats as unsupported per Scheme A (fail closed, no repair turn) — contradiction removed.

Binding: `send()` increments `round`, `secrets.token_hex(16)` 32-hex nonce, canonical `request_digest` SHA256(sorted JSON without digest), tracks `outstanding` + `consumed` set; `wait_for_reply` verifies `round/request_id/request_digest` exact, rejects `stale` prior, `preplayed` future, `replayed` consumed, `wrong id`, `wrong digest`, `future never becomes valid later` (all 6 + pre-set/double-send).

## Production vs synthetic handler separation (blocker 1)

`bridged_model_handler.py` frozen with two classes:

- **SyntheticProbeHandler** (disposable): `FusedTurnRuntime → build_envelope(snapshot,+current_event) → MailboxBridge.send → inbox → inside-jail responder (nobody) → outbox → wait_for_reply (binding) → reply_to_directive_synthetic (hard-coded provider=sandbox-bridge model=synthetic-responder-v1 tokens=10)` — never for real B.

- **ProductionResidentHandler** (frozen for real B): `build_envelope(snapshot,+current_event wiring) → build_model_request(contract_text, envelope) = {system: exact RESIDENT_B_RUN_CONTRACT.md bytes, messages: [{role:user, content: JSON(envelope)}]}` → `provider_client.invoke(request)` **outside jail** → `ProviderResponse{provider,model,request_id,usage,content: reply JSON}` → `validate_reply + verify_binding` → `reply_to_directive_production(uses REAL provider/model/request_id or "UNKNOWN", usage.total_tokens from provider or None, provenance ModelCallProvenance(provider=actual or UNKNOWN))`. The **only** production transport is `ExternalBrokerClient` (pinned `bridged_model_handler:ExternalBrokerClient`, HTTPS-only, pure transport — no semantic default, no keyword→directive mapping, no timeout fallback answer). `FakeProviderClient` is **not** a drop-in: its `__init__` raises unconditionally, so the production entrypoint can never instantiate it. There is **no** `RealProviderClient`; real B supplies `AIOS_REAL_PROVIDER_API_KEY` + `AIOS_REAL_PROVIDER_ENDPOINT` and uses the same unchanged `ExternalBrokerClient`.

Current-event wiring: `current_event` is exact 8-field projection (synthetic `synthetic-fixture-seq-14 sequence 14` for probe, real fixture projection for B). Validated before envelope; negatives `13/23/extra/missing/phase A` all fail closed before write.

## E2E probes (26+ checks, ends CORRECTIVE_003_E2E_PASS, raw log 211 lines at /tmp/b-preflight-e2e-2942)

1. **Lineage digest verify** `626c6bb…/ecfabf4…/eada20a…` OK.
2. **Mailbox self-tests 15** PASS (including legal fixture allowed, strict extra field).
3. **Isolation probe** `ISOLATION_PASS` (nobody, sandbox-init PID1 4-5 PIDs, reap, ENETUNREACH×4, 13 sealed absent, RO ro,nosuid,nodev, /dev minimal, mailbox perms, EPERM, PROBE_* stripped).
4. **Binding E2E 7** `normal` 2 rounds echo OK + 6 negatives + future-not-valid.
5. **Synthetic genuine 2-round** `FusedTurnRuntime(98→99) → SyntheticProbeHandler(current_event seq14) → bridge round1 invoke search_world Atlas limit2 → capability_history contains obs_c14_fixture_* legal (non-empty) → round2 silence` (`invocations 2 model_rounds 2 termination silence catalog 43 world_map present archive 4 files`).
6. **Production genuine 2-round** `FusedTurnRuntime → ProductionResidentHandler(FakeProviderClient fake-provider/fake-model-v1 42 tokens) → request system+envelope only, no /repo/fixture leak → invocation 2 history 1 provider fake-provider usage 42 provenance REAL → UNKNOWN handling (empty provider → provenance UNKNOWN usage None not 10)`.
7. **Current-event negatives 5** `13/23/extra/missing/phase A` rejected.
8. **Strict reply** `silence{capability}` extra field rejected.
9. **Scheme A** `round_repair_request` unsupported → `ValueError` fail closed.
10. **MS_PRIVATE + privdrop** `MS_PRIVATE injected exit 98 no sentinel` + generic/setgid privdrop exit 98 no outbox.
11. **Signal deterministic** `sleep 30` TERM forwarded `PID1→worker` `wait` exit 143 deterministic (set +e wrapper, no || true masking).
12. **Env allowlist** `without AIOS_ALLOW_PROBE_ENV: PROBE_* not leaked` + `with AIOS_ALLOW_PROBE_ENV=1 PROBE_MODE=genuine: allowed`.

All `CHECK 1..31 PASS` → `CORRECTIVE_003_E2E_PASS`.

## Probe raw outputs (captured 2026-09-25)

- `isolation/probe_output.txt` (211-line isolation log `ISOLATION_PASS` + mount ro,nosuid,nodev, /dev minimal, env).
- `isolation/e2e_probe_output.txt` (corrective-003 31-check log `CORRECTIVE_003_E2E_PASS` at `/tmp/b-preflight-e2e-2942`).
- `corrective_003_report.md` appendix reproduces verbatim.

## Frozen env (environment_manifest.md)

`PYTHONPATH=/repo/src` forced, `HOME=/home/nobody`, `TMPDIR=/tmp`, `LD_*/PYTHON*/SUDO*/PROXY*/GIT*/GH*` stripped, `PROBE_MODE/PROBE_ROUNDS` only when `AIOS_ALLOW_PROBE_ENV=1` explicitly, provider sees only `system+envelope`.

## Inherited-FD closure (CORRECTIVE-009 / BLK-07)

`/dev/fd → /proc/self/fd` is still provided, but `_close_inherited_fds()` now runs **immediately before
`execvpe`** (after all mount/privdrop setup is complete) and closes every descriptor `>= 3`, with a
second sweep over `/proc/self/fd` for anything the bulk close missed. Only `0/1/2` survive.

Adversarial proof (probe gate `INHERITED_FD_SEALED_PASS`): the operator opens the sealed fixture, the
evaluator-only design notes and an unrelated file, dups two of them to higher descriptor numbers, and
passes all five descriptors through `sudo` into the jail. Inside the sandbox:

- `/dev/fd/{0,1,2}` still resolve (the mechanism is alive),
- `/dev/fd/3`, `/dev/fd/4`, `/dev/fd/5`, `/dev/fd/7`, `/dev/fd/9` and `/proc/self/fd/{3,4,5,7,9}` do **not** exist,
- `head -c 32 /dev/fd/N` fails for every inherited number,
- no surviving descriptor symlink points at `sealed_fixture.json` or `EVALUATOR_ONLY_design_notes.md`,
- the payload still runs normally (`PAYLOAD_RAN_OK`).

## Fail-closed live-state binding (CORRECTIVE-009 / BLK-04) and no-event-no-dispatch (BLK-05)

`validate_current_event_binding()` treats the live `release_state.json` as **mandatory**: a missing,
unreadable, malformed or non-object state file raises before any receipt-only shortcut. The production
handler additionally refuses **every** dispatch whose `current_event is None` — for any `wake_reason`
and any `round_index`, including `periodic_review` at rounds 1 and 3 — poisoning itself, writing a
durable failure receipt, and performing zero provider invocations.

## Scheme-A evidence collision safety (CORRECTIVE-009 / BLK-06)

Failure receipts are named `failure-<session>-round-<round>-<time_ns>-<8-hex nonce>.json` and created
with `O_CREAT|O_EXCL` at mode `0400`. `_poisoned` is set, `_outstanding` is snapshotted **and cleared**
before any disk I/O, so an evidence-write failure can never leave stale outstanding state and is
surfaced as its own `evidence_persistence_failure` class rather than masking the original failure.

## Portability (CORRECTIVE-009 / BLK-02, BLK-08)

`probe_e2e.sh` derives `REPO_ROOT` / `B_PREP` / `HARNESS_DIR` from its own location, exports them, and
`cd`s to the repo root; no absolute path is hardcoded anywhere in the executable path. `resident_jail.py`
and `bridged_model_handler.py` resolve their repository root mechanically from `__file__` (unique
ancestor containing `src/aios_core`), with a symlink-escape guard and **no** absolute fallback.

## Canonical runbook order (CORRECTIVE-010 / BLK-03)

Section 6 of `procedure/b_startup_procedure.md` is **configuration only**: it exports B session,
provider endpoint/key/adapter, contract/wire/adapter hashes, the four canonical paths and
`PYTHONPATH`, then asserts that `current-event.json`, `current-event-binding.json` and a non-null
`pending_reveal` are all absent. It contains no `CURRENT_OCCURRED_AT` derivation and no model `turn`.

Section 7 carries the production turn as numbered steps 7.1–7.12 in the only legal order
(reveal → current-event.json → event-XXX.projection.json →
current-event-binding.json → verify binding → derive `CURRENT_OCCURRED_AT` → ingest →
headless turn / due / model rounds → finish model work → durable ACK → clear → reveal
next), with the exact receipt-creation command written inline at step 7.4.

`CANONICAL_RUNBOOK_ORDER_PASS` executes that order on a disposable Phase-B copy and reaches the
provider transport boundary through `ExternalBrokerClient` + `FakeBrokerServer`; the pre-reveal STOP
is proven through the real production handler (0 provider invocations, poisoned, durable receipt).
