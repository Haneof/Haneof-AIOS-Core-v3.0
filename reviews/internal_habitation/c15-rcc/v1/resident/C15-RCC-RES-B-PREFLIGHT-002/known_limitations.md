# C15-RCC-RES-B-PREFLIGHT-002 — Known Limitations (local-scope preflight; CORRECTIVE-009 frozen)

> This preflight validates **filesystem and interface isolation + transport and genuine model-roundtrip wiring** on the operator machine. It does NOT simulate full C15-RCC evaluation (PM-01..07), nor does it deduce external review outcomes. Finding so far: none blocking for B launch with frozen invariants (see `isolation_report.md`). All historic CORRECTIVE-001/002 blockers are closed; this file reflects CORRECTIVE-003 frozen behavior.

1. **Not sealed-verified release**: the underlying `A-002` durable state is operator-reported (World `626c6bb…`, Index `ecfabf4…`, Release `eada20a…`, runtime `773876f…`, Core `fe77f8a`, PLAT-05-17 `d17ae97`; rev98 watermark98 ACK13 next14 pending null). It is accepted as-is for this residency. A verifier rerunning this probe need only supply a `world.sqlite` with the same interface contract.
2. **Sudo required**: `harness/resident_jail.py` requires `CAP_SYS_ADMIN`/`CAP_SYS_CHROOT` to call `unshare(CLONE_NEWNS|CLONE_NEWPID|CLONE_NEWNET)`. Without `sudo`, the probe cannot prove namespace isolation.
3. **Operator sees sealed material (operator-trusted model)**: the model still runs outside the filesystem sandbox, inside the operator-supplied `ProviderClient` (Path A — external trusted broker) which sees only `contract text + Resident-safe envelope`. The network inside the Resident jail itself is `CLONE_NEWNET` sealed (no public internet; proven via `ENETUNREACH` probes), but the `ExternalBrokerClient` network call originates outside the jail (there is no `FakeProviderClient`/`RealProviderClient` production path). This is attested — not blind — and prior local testing will be discarded per `retention_policy.md`.
4. **Model provider identity is configurable**: provenance `provider/model/request_id` maps the provider's **real** reported values; where a field is not credibly available the provenance records the literal string `"UNKNOWN"` and `usage.total_tokens` is left incomplete (never the synthetic `10`). In this preflight, `FakeProviderClient(provider="fake-provider", model="fake-model-v1", total_tokens=42)` proves the exact mapping without forging provenance.
5. **Real model roundtrip proven via production code path**: this preflight exercises a genuine `FusedTurnRuntime`/`CognitiveRuntime → ProductionResidentHandler*` path (fake provider) that mirrors the real B model dispatch. The previous limitation "no real FusedTurnRuntime roundtrip — isolated synthetic helper only" is **closed** (see `probe_e2e.sh` 6-step E2E). Synthetic mailbox probe remains as disposable complement.
6. **Current-reveal wiring is explicit**: per-cursor Phase B reveal is **wired** — `current_event` is the exact 8-field projection (`event_id/sequence/occurred_at/dimension/source_kind/source_class/modality/resident_visible_payload`) with `sequence 14..22`, built mechanically for each cursor loop iteration and tested with sequence 14 plus negatives (13/23/extra-field/missing-field/wrong-phase). On the **production** path `event=None` is now an unconditional STOP (no dispatch, handler poisoned, durable receipt, zero provider invocations) — see `per_cursor_interaction.md` §5a; `event=None` is only reachable on the disposable synthetic probe path.
7. **`/dev` is minimal, not whole-host bind**: `/dev` inside jail is a `tmpfs` with only `null/zero/urandom/random` bind-mounted plus `/dev/fd` symlink. Whole-host `/dev` bind is **not** present (closed).
8. **Mount propagation is fail-closed**: `MS_REC|MS_PRIVATE` failure raises `RuntimeError(98)` before any bind/proc/chroot/exec — injection via `_RESIDENT_JAIL_INJECT_MS_PRIVATE_FAIL=1` proves no sentinel and no outbox reply. Previous `except: pass` fail-open is closed.
9. **Signal probe is deterministic**: `|| true` masking removed; probe now waits `sleep 1` and strictly asserts exit status/exit code.
10. **Reply schema is strict per action**: `validate_reply` uses per-action top-level allowlist; `silence` with extra `capability`, etc., fails closed (`MailBoxReplyError`). Repair contradiction removed — `repairRequest` unsupported per `per_cursor_interaction.md` Scheme A (fail closed, no repair).

* **Production transport (CORRECTIVE-009)**: `ExternalBrokerClient` is the only production transport and the file `bridged_model_handler.py` is frozen. There is no client swap at release — real B supplies `AIOS_REAL_PROVIDER_API_KEY` + `AIOS_REAL_PROVIDER_ENDPOINT` and the same unchanged class performs the HTTP POST. The frozen `FakeProviderClient` cannot be constructed and exists only so the production entrypoint can be proven to refuse it.

## CORRECTIVE-009 — independent-acceptance blockers closed

| Blocker | Closure | Gate |
| --- | --- | --- |
| BLK-01 sealed cursor-14 payload in committed evidence + false "no reveal" prose | disposable reveal prints mechanical metadata only; logs regenerated; prose corrected | `NO_COMMITTED_CURSOR14_PAYLOAD_PASS`, `NO_FALSE_NO_REVEAL_PROSE_PASS` |
| BLK-02 negative isolation false green | `REPO_ROOT`/`B_PREP`/`HARNESS_DIR` exported and derived from the script; no absolute fallback; exact exit 98 + injected marker + jail-executed proof | `PORTABLE_CHECKOUT_PASS`, `NEGATIVE_JAIL_ACTUALLY_EXECUTED_PASS` |
| BLK-03 canonical runbook not executable | `--lock` uses `world.sqlite.writer.lock`; doubled fence repaired; `--at` derived from the projection; per-cursor `event-NNN.projection.json` evidence; stale provider docs removed | `CANONICAL_RUNBOOK_EXECUTABLE_PASS` |
| BLK-04 binding fails open when live release state missing | live state mandatory; missing/unreadable/malformed/non-object → fail closed | `MISSING_RELEASE_STATE_FAIL_CLOSED_PASS` |
| BLK-05 dispatch with `event=None` | unconditional STOP for any wake reason / round index | `NO_EVENT_NO_DISPATCH_PASS` |
| BLK-06 failure-receipt collision | `time_ns` + nonce, `O_CREAT|O_EXCL`, `_outstanding` cleared before I/O | `FAILURE_RECEIPT_COLLISION_PASS` |
| BLK-07 inherited-FD escape | `_close_inherited_fds()` before `execvpe` | `INHERITED_FD_SEALED_PASS` |
| BLK-08 contract provenance hardcoded path | mechanical repo-root resolution, symlink-escape guard, no absolute fallback | `CONTRACT_PROVENANCE_PASS` |

**Superseded leaked evidence (historical):** commits `3796377` … `670c05b` of this branch are preserved
(no force-push, no rebase, no history rewrite), but the pre-CORRECTIVE-009 committed
`isolation/e2e_probe_output.txt` / `isolation/probe_output.txt` inside them contain the sealed cursor-14
`resident_visible_payload` in cleartext. Those historical blobs are **superseded leaked evidence**:
the current tip's evidence files are regenerated and payload-free, and **no Resident (B or C) may ever
read git history or those old commits** — all B/C evidence must be produced from the current tip.

