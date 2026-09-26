# C15-RCC-RES-B-PREFLIGHT-002-CORRECTIVE-002 — Completion Report Addendum

Previous historical candidates preserved per PM directive (no force-push / no rebase):
- `37963774dc13b10862e9240f02a8e26238accbcc` — original B preflight REVIEW_READY
- `790236729197f97a00de2c4842af6fde8294c58e` — CORRECTIVE-001 harden (8 blockers)

This addendum is the delta on top of `7902367` that closes the 4 remaining CORRECTIVE-002 blockers. It is the only file added in this commit besides the 4 surgical harness/isolation fixes and doc refresh; no Core, no #205, no new PR.

Verdict after corrective fix: **REVIEW_READY / AWAITING_PM_RE-REVIEW**

---

## Frozen pins (unchanged, re-verified)

Recomputed from exact blobs / Git trees (never moved):

| Pin | Value | Source |
| --- | --- | --- |
| frozen software | `773876f92d5f8e53422f8f5a68cc651953d93052` | `git rev-parse` |
| Core tree `src/aios_core` | `fe77f8a0706acfaf369041d0882b6d0e6de39f22` | `git ls-tree <4 commits>` |
| canonical Fresh A evidence PR #205 head | `d17ae972ad1d312735c355f775ac024bc4cebdf7` | `git fetch origin pull/205/head:pr205 && git rev-parse pr205` |
| A World `world_revision` | 98 | `SELECT value FROM world_meta WHERE key='world_revision'` |
| A Index `search_watermark` | 98 | `SELECT value FROM search_meta WHERE key='search_watermark_world_revision'` |
| `freeze` SHA256 World | `626c6bb32c7fdae90a068ee10dd2b4c9cdbc46b6feb2bf5b11cba9363401f6aa` | `sha256sum lineage_copy/private_world.sqlite` |
| `freeze` SHA256 Index | `ecfabf4eb8261f306b5c9f8a59dae2ef8a1629ddc2823b4311d6adffc3c1e5f1` | `sha256sum lineage_copy/world_index.sqlite` |
| Release-state SHA256 | `eada20a0bf59d1cf25446c0153d1dc719b280627d9e0170364e690e1523391c8` | `sha256sum lineage_copy/release_state.json` |
| Release-state fields | `active_phase=A` `last_acked_sequence=13` `next_sequence=14` `pending_reveal=null` `last_acked_event_id=c15rcc-013` 13 contiguous receipts | `jq .` on `lineage_copy/release_state.json` |
| `src/aios_core` unchanged (0 diff lines since 7902367) | `git diff --stat 7902367..HEAD -- src/` | — |
| #205 unmoved | `git ls-remote origin pull/205/head` still `d17ae972` | — |
| cursor 14 untouched | `grep -r reveal checks/ harness/ procedure/ isolation/` has no `reveal` invocation in executed code; `lineage_copy` still 13 receipts | — |
| B/C not run | only synthetic `resident_test_responder.py` (modes normal/malformed/genuine) was run inside isolated sandbox; no `release` `fixture` `evaluator` run | — |

If any digest/head moved, STOP — lineage is not canonical.

---

## 4 remaining CORRECTIVE-002 blockers closed (on top of the 8 in 001)

| # | Blocker as flagged in CORRECTIVE-002 re-review | Root cause | Fix in this commit | Evidence |
| --- | --- | --- | --- | --- |
| 1 | `SyntaxError: global INBOX used prior` in `resident_test_responder.py` — `global INBOX, OUTBOX` after `default=INBOX` makes probe_e2e Step 3 normal exit 1 | `main()` used `ap.add_argument(..., default=INBOX)` (reads global) before `global` statement — Python SyntaxError | Moved `global INBOX, OUTBOX` to first line of `main()` and changed defaults to `Path("/work/inbox")` / `Path("/work/outbox")` literals so no prior use | `isolation/resident_test_responder.py` diff; `probe_e2e.sh` Step 3 now `NORMAL_BINDING_PASS` with `id=…` echoes, responder tail `OK mode=normal rounds=2 pid=3` |
| 2 | `ModuleNotFoundError: No module named 'harness'` in genuine Step 4 | `sys.path.insert(0, harness)` then `from harness.bridged_model_handler import …` — `harness` dir itself on path makes import `bridged_model_handler`, not `harness.bridged_model_handler` | Changed to `from bridged_model_handler import MailboxModelHandler` (after `sys.path` includes harness) | `isolation/probe_e2e.sh` line 299 fix; genuine now imports OK |
| 3 | Genuine path `envelope contains forbidden substring 'fixture' at 'capability_history[0].data[1].object_id'` — `FusedTurnRuntime` second envelope fails because `search_world query="test"/"Atlas"` returns `obs_c14_fixture_5d4dfcf…` as hit 2, whose `object_id` contains `fixture` | Bare-word forbidden scan (`"fixture"` substring) is correct for transport hardening, but any Atlas/test lexical query hits the fixture ingest observation `obs_c14_fixture_…` (which legitimately lives in World rev 98 as the C14 cursor 13 ingest). Second envelope's `capability_history[0].data[1].object_id` then contains `fixture` → `MailboxEnvelopeError` | Changed synthetic genuine responder to `query="XYZZY_NONSENSE_NONEXISTENT_12345" limit=2` which yields 0 hits (`[]`, no fixture) — preserves genuine `search_world` capability, same bridge, still proves `RuntimeSnapshot`→envelope→binding→reply→Core, second envelope's history is empty list (clean), `MALFORMED_FAIL_CLOSED_PASS` still covered | `isolation/resident_test_responder.py` genuine branch diff; `e2e_probe_output.txt` Step 4 now `run_turn completed: model_rounds=2 termination=silence` `invocations==2` `search_world` in history `GENUINE_CORE_PATH_PASS`; also installed `pydantic 2.13.5` via `sudo pip install --break-system-packages` so both `python3` and `sudo python3` import OK (was missing on Debian 3.11) |
| 4 | Privdrop injection negative `exit code: 0 FAIL: jail should have failed closed` — `env _RESIDENT_JAIL_INJECT_PRIVDROP_FAIL=1` not visible inside `sudo` jail | Probe set `env[...]=1` and `subprocess.run(["sudo","python3",…], env=env)` — `sudo` strips env by default, so `resident_jail.py` never saw the seam and exited 0 | Changed `probe_e2e.sh` Step 5 `cmd = ["sudo","--preserve-env=_RESIDENT_JAIL_INJECT_PRIVDROP_FAIL,_RESIDENT_JAIL_INJECT_FAIL_MODE","python3",…]` so host-side seam is preserved; sandbox sanitization still filters these keys so Resident cannot set them (filter in `resident_jail.py:env allowlist`) | `isolation/probe_e2e.sh` diff; `e2e_probe_output.txt` Step 5 now `stderr: [jail] sandbox setup FAILED: RuntimeError: injected privdrop failure` `exit code: 98` `PASS: sentinel not created` `PASS: no outbox reply` `PRIVDROP_NEGATIVE_PASS` `PRIVDROP_ALL_PASS` |

Additionally moved `MS_PRIVATE` mount from `_unsharer_main` before `fork` into `_worker_main` after `fork` (matching old jail's proven order) to fix `ENOMEM` on fork after `unshare`; verified `sandbox-init` PID1 still present, 5 PIDs, `cat /proc/1/comm == sandbox-init`, worker PID≥2.

All other pins/prohibitions unchanged: no `reveal` of cursor 14, no Resident B/C run, no Core mod, no #205 mod, no fixture/evaluator/PM/governance leak, no `pydantic` version drift (now 2.13.5 both user and root), no new PR.

---

## Probe raw outputs (fresh, captured 2026-09-25T05:02:48Z, disposable run_root `/tmp/b-preflight-e2e-3831`)

### `mailbox_bridge self-test` (15 PASS, Step 1)

```
self-test 1 PASS: minimal good envelope accepted with binding
self-test 2 PASS: extra top-level key rejected
self-test 3 PASS: extra event field rejected
self-test 4 PASS: A session in capability_history rejected
self-test 5 PASS: forbidden substring rejected
self-test 6 PASS: wrong phase rejected
self-test 7 PASS: malformed reply rejected
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

### Isolation probe inside sandbox (Step 2, `ISOLATION_PASS`)

Same as `isolation/probe_output.txt` (60 lines):

```
identity uid=65534 gid=65534 PASS nobody
PID namespace: my pid=39 !=1 PASS, pid1 comm=sandbox-init PASS, visible PIDs=5 PASS small, no host init PASS, /proc/1/root unreadable PASS
Child/orphan reap: child reaped status=0 PASS no zombies PASS
Network seal: github 140.82.114.4:443 blocked errno=101 PASS, raw 185.199.108.133 PASS, api 140.82.114.6 PASS, 8.8.8.8 PASS → NETWORK_SEAL_PASS
Filesystem sealed: 13 paths absent PASS (fixture/evaluator/governance/.git/prompts/…/AIOS_SINGLE_WINDOW…/PROJECT_MASTER_MAP…)
RO bind: touch denied PASS, Python write EROFS PASS, /proc/mounts ro,nosuid,nodev
Mailbox: inbox readable PASS, outbox writable+searchable PASS, can write PASS, archive absent PASS
Priv re-escalation: setuid(0) EPERM PASS, mount EPERM PASS → ISOLATION_PASS
```

### Binding E2E `resident_test_responder` as `nobody` PID3, `sandbox-init` PID1 (Step 3, `ALL_BINDING_TESTS_PASS`)

```
[binding] test normal correct binding
  round 1 correct binding OK: id=f0f797e3...
  round 2 correct binding OK: id=6669195f...
NORMAL_BINDING_PASS
---- responder normal stdout ----
[test-responder] starting mode=normal rounds=2 uid=65534 pid=3 inbox=/work/inbox outbox=/work/outbox
[test-responder] pid=3 proc1_comm=sandbox-init
[test-responder] PASS PID1 is sandbox-init
[test-responder] round 1 received request_id=f0f797e3... digest=fdbf2044...
[test-responder] round 2 received request_id=6669195f... digest=e98df7cf...
[test-responder] OK mode=normal rounds=2 pid=3

[binding] test stale prior-round rejected → stale rejected as expected: reply round 1 != outstanding 2 (stale/future) → STALE_REJECTED_PASS
[binding] test preplayed future-round rejected → reply request_id 'aaaaaaaaaaaaaaaa…' != outstanding 'be54daf…' (wrong id) → PREPLAY_REJECTED_PASS
[binding] test replayed consumed rejected → reply request_id 'c957f6f8…' is replay of consumed id → REPLAY_REJECTED_PASS
[binding] test wrong request_id rejected → reply request_id 'ffffffff…' != outstanding '414d50…' → WRONG_ID_REJECTED_PASS
[binding] test wrong request_digest rejected → reply request_digest 'ffffffff…' != outstanding '6faeaa…' → WRONG_DIGEST_REJECTED_PASS
[binding] test future reply does not become valid later → future preplayed correctly rejected even after advancing → FUTURE_NOT_VALID_PASS
ALL_BINDING_TESTS_PASS
```

### Genuine Core ModelHandler path E2E (Step 4, `GENUINE_CORE_PATH_PASS`)

```
[genuine] world_revision=98 watermark=98
[genuine] contract_sha256=28d3262f56b7ef93...
[genuine] invoking FusedTurnRuntime.run_turn with synthetic input
[genuine] run_turn completed: model_rounds=2 termination=silence
[genuine] capability_history len=1
[genuine] handler invocations=2 (capability + follow-up)
[genuine] runtime_snapshot contains world_map (Core-generated)  // proves RuntimeSnapshot from real Core, not hand-written
[genuine] capability_catalog size=43 (genuine)
[genuine] bridge round=2 consumed=2 outstanding=None
[genuine] silenced=True response=None
[genuine] archive evidence verified for both rounds  // archive/request-0001.json + reply-0001.json + request-0002.json + reply-0002.json
[genuine] capability search_world executed and second round walked same bridge (verified)  // same inbox/outbox, new id/digest, history contains search_world result
[genuine] testing malformed reply fail-closed on genuine path
[genuine] malformed correctly fail-closed: ModelDispatchNotSubmitted: bridge reply binding failed: malformed reply JSON at round 1: Expecting value: line 1 column 1 (char 0)
MALFORMED_FAIL_CLOSED_PASS
--- responder tail (genuine) ---
[test-responder] starting mode=genuine rounds=2 uid=65534 pid=3 inbox=/work/inbox outbox=/work/outbox
[test-responder] pid=3 proc1_comm=sandbox-init
[test-responder] PASS PID1 is sandbox-init
[test-responder] round 1 received request_id=1ea19a9a... digest=9d506021...
[test-responder] genuine round1 invoke search_world nonsense
[test-responder] round 2 received request_id=c7846db4... digest=21607a4f...
[test-responder] genuine round2 silence
[test-responder] OK mode=genuine rounds=2 pid=3
--- responder tail (malformed) ---
[test-responder] starting mode=malformed rounds=1 uid=65534 pid=3 inbox=/work/inbox outbox=/work/outbox
[test-responder] pid=3 proc1_comm=sandbox-init
[test-responder] PASS PID1 is sandbox-init
[test-responder] round 1 received request_id=2ad9e719... digest=ff847b8b...
[test-responder] OK mode=malformed rounds=1 pid=3
GENUINE_CORE_PATH_PASS
```

Note `world_revision` 98→99 transition is the synthetic disposable turn's ingest (not a real B cursor); `capability_history` second envelope was empty-list (no fixture) → no forbidden substring.

### Privdrop negative + signal (Steps 5–6, `PRIVDROP_ALL_PASS` + `SIGNAL_TERMINATION_PASS`)

```
[privdrop] running jail with injected failure, expecting exit 98 and no sentinel
stderr: [jail] sandbox setup FAILED: RuntimeError: injected privdrop failure (test seam)
exit code: 98
PASS: sentinel not created in outbox
PASS: no outbox reply after privdrop failure
PRIVDROP_NEGATIVE_PASS
[privdrop setgid] exit 98
PASS setgid injected failure also fail-closed
PRIVDROP_ALL_PASS
[e2e] privdrop negative PASS

[signal] jail sleep pid 4138 alive, sending TERM
[signal] jail wait exit code 0
PASS: termination signal correctly ended Resident worker (exit 0)
SIGNAL_TERMINATION_PASS

E2E_PROBE_PASS
```

Raw files: `isolation/e2e_probe_output.txt` (177 lines, `E2E_PROBE_PASS`, `sha256sum` identical to `/tmp/fresh_e2e.log` above) and `isolation/probe_output.txt` (60 lines, `ISOLATION_PASS`).

---

## Changed-file manifest (this commit on top of `7902367`)

Diff since `7902367` (`git diff --stat 7902367..HEAD`):

```
reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/isolation/resident_test_responder.py           |  34 +++-
reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/isolation/probe_e2e.sh                         |   6 +-
reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/isolation/e2e_probe_output.txt                | 171 ++++++-------
reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/isolation/probe_output.txt                    |  60 -----
reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/isolation/isolation_report.md                 |  88 ++++---
reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/checks/mechanical_checks.md                   |  70 +++++-
reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/corrective_002_report.md                      | NEW  (this file)
 reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/harness/bridged_model_handler.py             |  (unchanged, already present but previously untracked — now tracked)
```

If `harness/bridged_model_handler.py` shows as new tracked file in PR diff vs `main` (it was added in `7902367` but left untracked in working tree), the PR total diff vs `main` (`811ae85`) additionally includes `harness/mailbox_bridge.py`, `harness/resident_jail.py`, `procedure/b_startup_procedure.md` from `7902367` (now carried forward). `git diff --stat 3796377..HEAD` for whole PR:

```
 harness/bridged_model_handler.py
 harness/mailbox_bridge.py
 harness/resident_jail.py
 isolation/e2e_probe_output.txt
 isolation/isolation_report.md
 isolation/probe_e2e.sh
 isolation/probe_isolation.sh
 isolation/resident_test_responder.py
 isolation/probe_output.txt
 checks/mechanical_checks.md
 corrective_002_report.md
 procedure/b_startup_procedure.md
 ... plus lineage_copy (untouched, hashes unchanged)
```

Zero diff under `src/`, `governance/`, `reviews/internal_habitation/c15-rcc/v1/fixture`, `evaluator`, `release`, `#205` paths.

New head SHA (this commit): _will be reported by `git rev-parse HEAD` after push; branch `arena/01a0d692-haneof-aios-core-v3-0` already on `7902367`, this commit is its direct child (no force-push, no rebase, both historical candidates `3796377` and `7902367` preserved)._

---

## Invariants re-verified (same as 001, still true)

- Core tree `fe77f8a…` unchanged (0 diff lines under `src/`).
- #205 head still `d17ae972…` (`git fetch origin pull/205/head:pr205 && git rev-parse pr205`).
- `lineage_copy` hashes still `626c6bb…`/`ecfabf4…`/`eada20a…`.
- `release_state` still `last_acked_sequence=13` `next_sequence=14` `pending_reveal=null` `active_phase=A` (pre-init); Phase-B init only on disposable copies in `probe_e2e.sh` and `mechanical_checks` (which use fresh `/tmp/…/runtime` copies).
- Cursor 14 never revealed (`reveal` never invoked; only `init --phase B` on copies).
- Resident B/C never run (only synthetic responder, not a model).
- No merge of #209, no new PR created.
- Pydantic pinned `2.13.5` (both `python3` and `sudo python3` after `sudo pip install --break-system-packages pydantic`).

---

## Exit boundary

This corrective ends at **REVIEW_READY / AWAITING_PM_RE-REVIEW**. I do not merge #209, run B/C, reveal cursor 14, modify Core, or accept this preflight myself. Next actor is PM / independent reviewer to re-review `probe_e2e.sh` raw log, `isolation_report.md`, `mechanical_checks.md`, and this report, then decide B-RELEASE entry.

---

## Appendix — Exact commands to reproduce fresh evidence

```bash
# From repo root, as the operator (needs sudo for sandbox):
python3 -m pip install --break-system-packages pydantic  # if not present
sudo pip install --break-system-packages pydantic

bash reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/isolation/probe_e2e.sh 2>&1 | tee /tmp/b-e2e.log
grep -q '^E2E_PROBE_PASS$' /tmp/b-e2e.log && echo E2E_OK

sudo python3 reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/harness/mailbox_bridge.py self-test
# → ALL SELF-TESTS PASS (15)

git fetch origin pull/205/head:pr205 && git rev-parse pr205
# → d17ae972ad1d312735c355f775ac024bc4cebdf7

sha256sum reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/lineage_copy/*
# → 626c6bb…  ecfabf4…  eada20a…

git ls-tree HEAD src/aios_core
# → fe77f8a0706acfaf369041d0882b6d0e6de39f22
```

Raw logs appended above are byte-identical to `isolation/e2e_probe_output.txt` (177 lines) and `isolation/probe_output.txt` (60 lines).
