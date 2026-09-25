# C15-RCC-RES-B-PREFLIGHT-002 — Mechanical Check Results (CORRECTIVE-003, 26+ checks)

All checks run against disposable copies of freeze artifacts. Canonical #205 evidence read but not modified.

## 1. Frozen Core tree identity

**PASS.** `src/aios_core` tree hash = `fe77f8a0706acfaf369041d0882b6d0e6de39f22` at: frozen software `773876f9`, #205 head `d17ae972`, publication base `4d9f047`, main HEAD `aa19af1`.
`git ls-tree <commit> src/aios_core`

## 2. Accepted A freeze digests

**PASS.** `626c6bb32c7fdae90a068ee10dd2b4c9cdbc46b6feb2bf5b11cba9363401f6aa` / `ecfabf4eb8261f306b5c9f8a59dae2ef8a1629ddc2823b4311d6adffc3c1e5f1` / `eada20a0bf59d1cf25446c0153d1dc719b280627d9e0170364e690e1523391c8`.

## 3. World SQLite quick_check

**PASS.** `PRAGMA quick_check;` → `ok`.

## 4. World revision = 98

**PASS.** `world_meta world_revision` → 98, last commit is C14 fixture ingest seq13.

## 5. Index quick_check

**PASS.** `ok`.

## 6. Index watermark = 98

**PASS.** `search_watermark_world_revision` → 98.

## 7. Index lag = 0

**PASS.** `recovery-status` → lag 0.

## 8. Release-state fields

**PASS.** `active_phase A, last_acked 13, next 14, pending null, 13 receipts, fixture_sha256 7ccb309d, final receipt bound to rev98`.

## 9. No cursor 14 consumed

**PASS.** `receipts` 13, `pending null`, `init --phase B` does not emit a payload. A disposable `reveal --phase B` IS executed by the E2E probe on a throwaway release-state copy to prove the `init → reveal → receipt → handler` chain; it prints mechanical metadata only and its payload bytes are never committed (CORRECTIVE-009 / BLK-01, gate `NO_COMMITTED_CURSOR14_PAYLOAD_PASS`).

## 10. Legal Phase-B init

**PASS.** `release_operator.py init --phase B` → `{"next_sequence":14,"phase":"B","status":"initialized"}` exit 0.

## 11. Malformed boundary fails closed

**PASS.** `skip_seq12`, `dirty_pending`, `seq14_already`, `double_init` all `exit 2` with receipt chain mismatch.

## 12. Same-World durable restart

**PASS.** `recovery-status` `AUTO_RECOVERABLE` `world_rev 98 watermark 98`, `rebuild-index` `indexed_rows 245 watermark 98`.

## 13. Isolation (no sealed material, PID1 sup, NET sealed, RO, /dev minimal, env)

**PASS.** `isolation/isolation_report.md` + `probe_e2e.sh` Step2 `ISOLATION_PASS`:
- `nobody 65534`, `sandbox-init PID1` `worker PID≥2` `visible 4-5 PIDs`, no `systemd`, `/proc/1/root` unreadable, orphan reap no zombies.
- `CLONE_NEWNET` `ENETUNREACH 101` for github/raw/api/8.8.8.8, `lo` only.
- RO `ro,nosuid,nodev` `EROFS`.
- 13 sealed paths absent.
- `/dev` minimal `null/zero/urandom/random+fd` only, no `sda/mem/kvm/tty`.
- `PROBE_MODE` stripped unless `AIOS_ALLOW_PROBE_ENV=1`, `LD_*` stripped.

## 14. Mailbox transport + binding + path-aware guard (blockers 2,8)

**PASS by inspection + 15 self-tests + 7 E2E bindings.**
- `MailboxBridge` allowlist 11 top-level, 8-field event `14..22`, `phase B`, `allowed_sequences [14,22]`, B-session only history, **path-aware** `FORBIDDEN_SUBSTRINGS` = path prefixes `/repo/fixture` etc. **not bare `fixture`** (legal `obs_c14_fixture_*` allowed — test 5b `search_world Atlas` non-empty survives second envelope).
- Bridge-assigned `round/request_id(32 hex)/request_digest(64 hex)`, `outstanding+consumed` prevents replay, `wait_for_reply` verifies exact 3, rejects stale/preplay/replay/wrong-id/wrong-digest/future-not-valid.
- Self-test 15 PASS (including legal fixture allowed + extra reply field rejected).
- Binding E2E `normal` 2 rounds + 6 negatives → `ALL_BINDING_TESTS_PASS`.

## 15. Production vs synthetic handler separation + UNKNOWN (blocker 1)

**PASS.** `bridged_model_handler.py` frozen with **separated** classes:
- `SyntheticProbeHandler` (mailbox, inside-jail responder, `sandbox-bridge/10 tokens`) — disposable.
- `ProductionResidentHandler` (`build_envelope(+current_event)` → `build_model_request(contract+envelope)` → `FakeProviderClient(fake-provider/fake-model-v1/42)` outside jail → `validate+verify binding` → `reply_to_directive_production` maps **REAL** `provider/model/request_id` or `"UNKNOWN"` and `usage` from provider or `None` never `10`).
- Preflight proves `FakeProvider` 42 tokens propagated, `UNKNOWN` when provider returns `None` (provenance UNKNOWN, usage None), provider request contains only `system+envelope` no `/repo/fixture` leak, no file edit at release (constructor swap only). Prompt phrase “exact model handler implementation is chosen at release time” removed.

## 16. Current-event wiring 8-field 14..22 (blocker 3)

**PASS.** `build_envelope(snapshot, b_session, contract_sha256, current_event)` validated via `MailboxBridge` path. Probe proves:
- Positive `synthetic-fixture-seq-14` seq14 with 8 fields → envelope `event.sequence 14` OK, second round still OK.
- Negatives: `seq13`, `seq23`, extra `fixture_hint`, missing `resident_visible_payload`, `phase A` all `MailboxEnvelopeError` before write, no inbox file, no round advance.

## 17. Docs sync (blocker 4)

**PASS.** `resident_safe_packet_manifest.md` corrected: inbox/outbox are host bind IPC `0755/01733` not tmpfs, archive not mounted, network `CLONE_NEWNET` sealed (not “at operator discretion”), RO `ro,nosuid,nodev` mount, minimal `/dev`, PID1 sup, provider outside jail, contract exact bytes. `known_limitations.md` closed “network not restricted” and “no real model roundtrip”. `operator_manifest.md` pinned `NET sealed`, `ProductionResidentHandler`, binding:time. `procedure/b_startup_procedure.md` updated to frozen adapter + env allowlist + no tmpfs claim.

## 18. MS_PRIVATE fail-closed + inject negative (blocker 5)

**PASS.** `resident_jail._worker_main` no `except: pass` around `MS_REC|MS_PRIVATE`; failure raises `RuntimeError` → `os._exit(98)` before any bind/proc/chroot/exec. Probe proves ` _RESIDENT_JAIL_INJECT_MS_PRIVATE_FAIL=1` → exit 98, `SHOULD_NOT_RUN` not executed, outbox empty.

## 19. Minimal /dev (blocker 6)

**PASS.** `tmpfs /dev` + only `null/zero/urandom/random` `MS_BIND` + `fd` symlink. Probe `ls /dev` shows only those, `open(/dev/sda|mem|kvm|tty)` fails.

## 20. Deterministic signal (blocker 7)

**PASS.** `probe_e2e.sh` signal step no `|| true` masking: `set +e; wait $SLEEP_PID; EC=$?; set -e` → `kill -TERM` → PID1 forwards to worker sleep → `wait` returns 143 deterministic (`SIGNAL_TERMINATION_PASS`).

## 21. Strict reply schema (blocker 8)

**PASS.** `validate_reply` per-action allowlist; `silence` extra `capability` → `MailboxReplyError: extra fields ['capability']`. Probe `STRICT_REPLY_PASS`. Also `mailbox_bridge self-test 7b` covers.

## 22. Repair Scheme A (blocker 9)

**PASS.** `per_cursor_interaction.md` Scheme A: `round_repair_request` unsupported, fail closed, no repair turn. Handler `validate_reply` allows shape but `_reply_to_directive_production` raises `ValueError: unsupported reply action` → `ModelDispatchNotSubmitted`. Docs contradiction removed, probe `repair shape structurally allowed → ValueError` `CHECK 26 PASS`.

## 23. Environment manifest frozen

**PASS.** `environment_manifest.md` lists `PYTHONPATH=/repo/src` forced, `LD_*/PYTHON*/SUDO*` stripped, `PROBE_MODE/PROBE_ROUNDS` only when `AIOS_ALLOW_PROBE_ENV=1`. Probe step10 proves both `without allow not leaked` and `with allow explicitly allowed`.

## 24. Genuine Core 2-round transport (synthetic + production)

**PASS.** `probe_e2e.sh` steps 4a+4b:
- Synthetic: `FusedTurnRuntime(98→99) → SyntheticProbeHandler(seq14) → bridge → genuine responder Atlas` → `invocations 2 model_rounds 2 termination silence catalog 43 world_map present archive 4 files non-empty legal fixture in second envelope`.
- Production: `FusedTurnRuntime → ProductionResidentHandler(FakeProvider fake-provider 42)` → `request system+envelope only` → `invocations 2 history 1 provider fake-provider usage 42 UNKNOWN handling`.

## 25. PID1 supervisor hierarchy

**PASS.** `unshare → fork init PID1 sandbox-init → fork worker PID≥2`; init reaps/forwards. Verified `cat /proc/1/comm sandbox-init`, `orphan reap no zombies`, `signal TERM forwarded`.

## 26. Privdrop forced failure + env sanitization

**PASS.** No `except: pass`; post-drop `setuid(0) EPERM` + `mount EPERM`. Injection `generic` + `setgid` both exit 98 no sentinel, no outbox. Env `LD_*` stripped, `_RESIDENT_JAIL_*` stripped.

## 27. B freeze/evidence procedure defined before B

**PASS.** `procedure/final_freeze_procedure.md` enumerates hashes to capture at B completion.

## 28. Cursor14 not revealed

**VERIFIED.** No `reveal` output ever reaches a model. The preflight's disposable reveal runs on a copied release state inside `/tmp`; its stdout is reduced to `DISPOSABLE_REVEAL seq=… event_id=… projection_sha256=… payload_sha256=…` and the committed `e2e_probe_output.txt` / `probe_output.txt` are scanned for every sealed fixture payload before the gate passes. Disposable reveal ≠ Resident reveal; the projection was never presented to a Resident or model and is never sent to a model.

## CORRECTIVE-009 gate (checks 125–139)

Every check below is produced by a real test inside `isolation/probe_e2e.sh`, never echoed by the gate
itself; the gate re-scans its own run log for each marker and also runs a negative self-test proving the
marker search is non-vacuous. `EXPECTED_CHECKS=139`, success marker `CORRECTIVE_009_E2E_PASS`.

| Check | Blocker | Result |
| --- | --- | --- |
| 125 | BLK-01 | `NO_COMMITTED_CURSOR14_PAYLOAD_PASS` — every `resident_visible_payload` of the sealed fixture is scanned out of `e2e_probe_output.txt`, `probe_output.txt`, the completion report, the mechanical checks, the operator manifest, the runbook and the probe script. 0 hits. Event ids / sequences / SHA digests remain visible. |
| 126 | BLK-01 | `NO_FALSE_NO_REVEAL_PROSE_PASS` — the completion report, the mechanical checks and the operator manifest contain none of the banned no-reveal phrasings; the disposable-reveal wording and the "disposable reveal ≠ Resident reveal" / "projection never sent to a model" statements are all present. |
| 127 | BLK-02 | `PORTABLE_CHECKOUT_PASS` — the probe re-runs from a random `/tmp/<random>/` checkout and still PASSes; `grep -R` for the operator's absolute path over harness/isolation/procedure/checks/`*.md` returns 0 in code or execution paths. |
| 128 | BLK-02 | `NEGATIVE_JAIL_ACTUALLY_EXECUTED_PASS` — each injected failure (MS_PRIVATE, privdrop, setgid, setgroups, setuid) exits exactly `98`, prints the injected marker on stderr, leaves no `can't open file` / traceback, and does not execute the payload sentinel. "nonzero == PASS" is not accepted anywhere. |
| 129 | BLK-03 | `CANONICAL_RUNBOOK_STATIC_PASS` — documented `--lock` uses `$RUN_ROOT/runtime/world.sqlite.writer.lock`, the code fences are balanced, the occurrence timestamp is derived mechanically, the projection loop and the production-transport wording are consistent. |
| 130 | BLK-03 | `CANONICAL_RUNBOOK_EXECUTABLE_PASS` — the runbook is actually executed against a disposable lineage copy: rev 98, watermark 98, index lag 0, `AUTO_RECOVERABLE`, `quick_check ok`. |
| 131 | BLK-04 | `MISSING_RELEASE_STATE_FAIL_CLOSED_PASS` — the handler is constructed normally, `release_state.json` is deleted, the same handler is invoked again: 0 provider invocations, handler poisoned, durable failure receipt written. |
| 132 | BLK-05 | `NO_EVENT_NO_DISPATCH_PASS` — `periodic_review` at rounds 0/1/3 (and every other wake reason) with a missing current event fails closed with 0 provider invocations. |
| 133 | BLK-06 | `FAILURE_RECEIPT_COLLISION_PASS` — two handlers, same session, same round, same second → two distinct mode-0400 receipts, no collision, both `outstanding is None`, original failure class preserved. |
| 134 | BLK-07 | `INHERITED_FD_SEALED_PASS` — operator-held sealed-fixture, evaluator-only and unrelated FDs are inherited into the jail and are not visible in `/proc/self/fd` or readable via `/dev/fd/N`; the payload still runs. |
| 135 | BLK-08 | `CONTRACT_PROVENANCE_PASS` — the handler resolves the repo root mechanically, binds the accepted contract with exact SHA, is copied to a random `/tmp/candidate-<random>/` and imported with `cwd=/tmp` where it still finds that candidate's contract, is unaffected by an external same-named contract, and fails closed on a candidate contract mismatch. |
| 136–139 | — | Adversarial extensions of 131–135 (negative jail exit-98 / jail-executed proof for BLK-02, missing-state + no-event regression matrix, receipt-name shape assertion, and the same-checkout contract binding). |

`grep -R` for the operator's absolute checkout path over `harness/`, `isolation/`, `procedure/`, `checks/`,
`completion_report.md`, `checks/mechanical_checks.md`, `operator_manifest.md`, `environment_manifest.md`,
`resident_safe_packet_manifest.md`, `known_limitations.md`, `source_pins_and_digests.md`,
`identity_inventory.md` and `corrective_009_report.md` returns **0 hardcoded dependencies in code or
execution paths** (the only permitted mentions are in prose that explicitly forbids them).
