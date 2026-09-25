# C15-RCC-RES-B-PREFLIGHT-002-CORRECTIVE-003 — Report (9 blockers, 31 checks)

Date: 2026-09-25
Branch: `arena/01a0d692-haneof-aios-core-v3-0` (head preserves 3796377/7902367/ee5e4a4, live main aa19af1)
Verdict: **REVIEW_READY** (await PM re-review, no B/C run, no merge)

## Pins (recomputed, STOP if diverged)

| Item | Value | Verified |
| --- | --- | --- |
| frozen software | `773876f92d5f8e53422f8f5a68cc651953d93052` | `git rev-parse` |
| Core tree `src/aios_core` | `fe77f8a0706acfaf369041d0882b6d0e6de39f22` | `git ls-tree` at 773876f/d17ae97/aa19af1 |
| #205 head | `d17ae972ad1d312735c355f775ac024bc4cebdf7` | `git fetch origin pull/205/head` |
| World `626c6bb32c7fdae90a068ee10dd2b4c9cdbc46b6feb2bf5b11cba9363401f6aa` | 790528 | `sha256sum world.sqlite` |
| Index `ecfabf4eb8261f306b5c9f8a59dae2ef8a1629ddc2823b4311d6adffc3c1e5f1` | 811008 | same |
| Release `eada20a0bf59d1cf25446c0153d1dc719b280627d9e0170364e690e1523391c8` | 10841 | same |
| A-002 lineage | rev98 watermark98 lag0 ACK13 next14 pending null | `recovery-status` |
| Contract | `RESIDENT_B_RUN_CONTRACT.md` `28d3262f…` | `sha256sum` |
| Mailbox lineage | rev98→99 after synthetic turn, catalog43, world_map present, archive 4 files | `probe_e2e` |

## 9 blockers closed

| # | Blocker | Fix | Proven |
| --- | --- | --- | --- |
| 1 | Production model path hard-coded 10 tokens, no broker, no provenance | `ProductionResidentHandler` + `ProviderClient`/`FakeProviderClient` separated from `SyntheticProbeHandler`; `build_model_request` = `{system: contract, messages: [envelope_json]}` outside jail; real `provider/model/request_id` or `UNKNOWN`, `usage` from provider (42) or `None` never `10`; phrase “chosen at release time” removed; file frozen | `probe_e2e` step4b `fake-provider/fake-model-v1 42` + `UNKNOWN` + `system+envelope` no leak |
| 2 | Legal durable World fixture false positive (bare `fixture` substring) | `FORBIDDEN_SUBSTRINGS` narrowed to path prefixes `/repo/fixture` etc., bare `fixture` not forbidden; self-test 5b `obs_c14_fixture_*` allowed; probe uses `Atlas` non-empty (2 hits with `obs_c14_fixture_*`) second envelope survives | `mailbox_bridge self-test 5b PASS` + `synthetic genuine second envelope contains obs_c14_fixture_* True` |
| 3 | Current reveal not wired (event=None, no 8-field) | `build_envelope(..., current_event)` validated 8-field `14..22`; `SyntheticProbeHandler.set_current_event` + `ProductionResidentHandler.set_current_event`; negatives 13/23/extra/missing/phase A fail closed | `probe_e2e` step5 `PASS seq13/23/extra/missing/phase A` + step4a `event.sequence 14` OK |
| 4 | Docs claim host network/tmpfs inbox/outbox | `resident_safe_packet_manifest` rewritten: `CLONE_NEWNET` sealed, inbox/outbox host bind `0755/01733` not tmpfs, archive not mounted, RO `ro,nosuid,nodev`, minimal `/dev`, provider outside jail; `known_limitations` closed network & roundtrip; `operator_manifest` sealed | `diff` shows removal of “at discretion” + “tmpfs inbox” |
| 5 | MS_PRIVATE `try:pass` fail-open | `_worker_main` `if _RESIDENT_JAIL_INJECT_MS_PRIVATE_FAIL` raise then `_mount` without `try:pass`; injection → `RuntimeError` → `exit 98` before any bind | `probe_e2e` step8 `MS_PRIVATE injected exit 98 stdout=... injected MS_PRIVATE failure` + no sentinel |
| 6 | Full `/dev` bind | `tmpfs /dev` + only `null/zero/urandom/random` `MS_BIND` + `fd` symlink; `open /dev/sda|mem|kvm|tty` fails | `probe isolation /dev minimal PASS` + `ls /dev` only 4 + `fd` |
| 7 | Signal `|| true` masking | `set +e; wait $SLEEP_PID; EC=$?; set -e` deterministic, no `|| true`; PID1 forwards TERM | `probe_e2e` step9 `SIGNAL_TERMINATION_PASS exit 143 deterministic` |
| 8 | Reply schema no allowlist | `validate_reply` per-action allowlist `silence {round,id,digest,action}` only, extra → `MailboxReplyError`; self-test 7b + probe strict | `probe_e2e` step6 `extra fields ['capability'] not allowed` |
| 9 | Repair contradiction | `per_cursor_interaction.md` Scheme A (no repair, `round_repair_request` unsupported fail closed); `validate_reply` allows shape but `_reply_to_directive_production` raises `ValueError` | `probe_e2e` step7 `repair shape structurally allowed → ValueError unsupported` |

## Evidence summary (31 checks, raw 211-line log at /tmp/b-preflight-e2e-2942)

```
CHECK 1  mailbox self-tests (15) including 5b legal fixture +7b strict
CHECK 2  isolation PID1 sup + NET sealed + RO + mailbox IPC + /dev + env
CHECK 3  PID1 supervisor worker PID≥2 zombie reap
CHECK 4  NET sealed ENETUNREACH 101 x4
CHECK 5  RO bind ro,nosuid,nodev EROFS
CHECK 6  mailbox IPC 0755/01733/archive absent
CHECK 7  /dev minimal 4 + fd only
CHECK 8  env PROBE_* stripped
CHECK 9  binding normal 2 rounds echo
CHECK 10 stale prior rejected
CHECK 11 preplayed future rejected
CHECK 12 replay consumed rejected
CHECK 13 wrong id rejected
CHECK 14 wrong digest rejected
CHECK 15 future not valid
CHECK 16 synthetic genuine 2-round Atlas non-empty legal via MailboxBridge
CHECK 17 current_event seq14 8-field wiring
CHECK 18 production genuine FakeProvider fake-provider 42 tokens REAL provenance
CHECK 19 UNKNOWN handling provenance UNKNOWN usage None
CHECK 20 seq13 rejected
CHECK 21 seq23 rejected
CHECK 22 extra field rejected
CHECK 23 missing field rejected
CHECK 24 phase A rejected
CHECK 25 strict reply silence{capability} rejected
CHECK 26 Scheme A repair unsupported fail-closed
CHECK 27 MS_PRIVATE exit 98 no sentinel
CHECK 28 privdrop generic+setgid exit 98 no sentinel
CHECK 29 signal TERM forwarded exit 143 deterministic
CHECK 30 env without allow not leaked
CHECK 31 env with allow explicitly allowed
ALL_CHECKS=31/26+ → CORRECTIVE_003_E2E_PASS
```

## Raw logs (verbatim, truncated to relevant tails)

### mailbox_bridge self-test (15)

```
self-test 1 PASS: minimal good envelope accepted with binding
self-test 2 PASS: extra top-level key rejected
self-test 3 PASS: extra event field rejected
self-test 4 PASS: A session in capability_history rejected
self-test 5 PASS: forbidden path substring rejected (legal obs_c14_fixture_* allowed)
self-test 5b PASS: legal durable World fixture id allowed (obs_c14_fixture_*)
self-test 6 PASS: wrong phase rejected
self-test 7 PASS: malformed reply rejected
self-test 7b PASS: extra reply field rejected (strict schema)
self-test 8 PASS: correct exact-bound reply accepted
self-test 9 PASS: stale prior-round reply rejected
self-test 10 PASS: preplayed future-round reply rejected
self-test 11 PASS: replayed consumed reply rejected
self-test 12 PASS: wrong request_id rejected
self-test 13 PASS: wrong request_digest rejected
self-test 14 PASS: double send while outstanding rejected
self-test 15 PASS: pre-set request_id rejected
ALL SELF-TESTS PASS
```

### isolation probe (inside jail as nobody, PID1 sandbox-init)

```
ISOLATION_PASS
visible PIDs 4-5, proc1_comm sandbox-init, reap no zombies, ENETUNREACH x4, RO ro,nosuid,nodev, /dev minimal 4+fd, mailbox perms, EPERM, PROBE_* stripped
```

### synthetic + production genuine

```
model_rounds=2 invocations=2 termination=silence
current_event wiring seq14 OK
second envelope capability_history contains obs_c14_fixture_* legal ids: True
prod model_rounds=2 invoc=2 history=1 last_provider=fake-provider model=fake-model-v1 req=fake-req-0002 usage={'total_tokens':42}
UNKNOWN provenance test: UNKNOWN UNKNOWN usage=None
```

### negatives + strict + repair + MS_PRIVATE + signal + env

```
PASS seq13 rejected | PASS seq23 rejected | PASS extra event field rejected | PASS missing field rejected | PASS phase A rejected
PASS strict extra field rejected: reply for action 'silence' has extra fields ['capability'] not allowed
repair shape structurally allowed → PASS repair unsupported fail-closed: unsupported reply action: 'round_repair_request'
MS_PRIVATE injected exit=98 → PASS MSPRIVATE fail-closed
privdrop generic exit=98 → PASS ; setgid exit=98 → PASS
[signal] jail exit code 143 → SIGNAL_TERMINATION_PASS
CHECK 30 env without allow not leaked | CHECK 31 env with allow explicitly allowed
CORRECTIVE_003_E2E_PASS
```

Full raw log saved at `/tmp/probe_003_run5.log` (211 lines) and reproduced in `isolation/e2e_probe_output.txt`.

## Files changed vs 7902367 (preserving 3796377/ee5e4a4)

- `harness/mailbox_bridge.py` (path-aware guard + strict reply + self-test 5b/7b)
- `harness/bridged_model_handler.py` (ProductionResidentHandler+SyntheticProbeHandler+FakeProviderClient, current_event wiring, UNKNOWN)
- `harness/resident_jail.py` (MS_PRIVATE fail-closed, minimal /dev, env allowlist AIOS_ALLOW_PROBE_ENV)
- `isolation/probe_isolation.sh` (/dev minimal, mount ro,nosuid,nodev, env)
- `isolation/probe_e2e.sh` (31-check full E2E, production + synthetic, current_event, strict, Scheme A, MS_PRIVATE, signal deterministic, env)
- `isolation/resident_test_responder.py` (Atlas non-empty)
- `resident_safe_packet_manifest.md` (bind IPC, NET sealed, RO, /dev minimal, frozen handler)
- `known_limitations.md` (closed network & roundtrip, MS_PRIVATE, /dev, signal, strict, Scheme A)
- `operator_manifest.md` (pins, frozen intent ProductionResidentHandler, NET sealed, binding)
- `procedure/per_cursor_interaction.md` (Scheme A 8-field loop)
- `procedure/b_startup_procedure.md` (frozen adapter Production, env, no tmpfs claim)
- `environment_manifest.md` (NEW, env allowlist)
- `isolation/isolation_report.md` (minimal /dev, MS_PRIVATE, production, 31 checks)
- `checks/mechanical_checks.md` (26+ updated)
- `corrective_003_report.md` (this file) + `e2e_probe_output.txt`

No `src/aios_core` change, no fixture/evaluator/governance change, no #205 change, no merge, no force.

## Prohibitions observed

- `grep -r "reveal"` — no cursor14 reveal invocation in preflight.
- `git log --oneline` — branch preserves 3796377, 7902367, ee5e4a4, live main aa19af1, no force.
- `git diff --stat` — no `src/aios_core`, `fixture`, `evaluator`, `governance` changes.

## Verdict

**REVIEW_READY** — awaiting PM re-review. Do not run B/C, do not merge #209 until accepted.

