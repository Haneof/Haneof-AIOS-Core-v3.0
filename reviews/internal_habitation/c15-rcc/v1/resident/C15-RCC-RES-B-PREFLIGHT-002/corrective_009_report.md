# C15-RCC-RES-B-PREFLIGHT-002-CORRECTIVE-009 — Closure Report

Closes exactly the **8 blockers** from independent acceptance review `5315355377`
(ACCEPTANCE_FAIL) that PM review `5315384072` formally reopened as CORRECTIVE-009 (READY).
No architecture expansion: the frozen sandbox, mailbox binding and transport design are unchanged.
Failed candidate `670c05b11fd3837c5c190baaf1f81d5464f57438` is preserved in history (no force-push,
no rebase, no squash) and is explicitly **superseded leaked evidence** — see the last section.

Success marker: **`CORRECTIVE_009_E2E_PASS`** with `EXPECTED_CHECKS=139` and `FAILURES=0`.

---

## BLK-01 — sealed cursor-14 payload in committed evidence + false "no reveal" prose

* `isolation/probe_e2e.sh` step 15 no longer runs `cat "$DISP_ROOT/reveal.json"`. The single
  disposable `release_operator reveal --phase B` (still required for the mechanical
  `init → reveal → receipt → handler` proof) now prints only:
  `DISPOSABLE_REVEAL seq=… event_id=… projection_sha256=… payload_sha256=… field_count=…`
  plus a `REVEAL_SHAPE_VALID_PASS` marker. No payload bytes, ever.
* `isolation/e2e_probe_output.txt` and `isolation/probe_output.txt` are **regenerated** from a fresh
  run; the current tip contains no `resident_visible_payload` for any sequence, and specifically
  nothing for cursor 14.
* Every "reveal was never called" / "no reveal" claim was replaced with the disposable-reveal
  wording, and the gate now **greps for the banned phrase itself** (`NO_FALSE_NO_REVEAL_PROSE_PASS`).
* Evidence-integrity gate scans the committed logs, this report, `checks/mechanical_checks.md`,
  `operator_manifest.md`, `environment_manifest.md` and the runbook for (1) payload bytes → 0 hits,
  (2) event id / sequence / digest allowed, (3) no false no-reveal prose, (4) "disposable reveal ≠
  Resident reveal" stated, (5) "projection never sent to a model" stated.
* `grep -c` over the whole candidate tree for the cursor-14 payload string: **0**.

## BLK-02 — negative isolation probes were false green

* `probe_e2e.sh` derives `SELF_DIR` → `B_PREP_DEFAULT` → `REPO_ROOT` mechanically, exports
  `REPO_ROOT`, `B_PREP`, `HARNESS_DIR`, asserts structural preconditions (exit 97) and `cd`s to
  `$REPO_ROOT`. Every hardcoded copy of the operator's absolute checkout path was purged from all
  executables and from the committed evidence.
* Paths are passed by argv with `_need()` fail-closed helpers; no hardcoded fallback exists.
* Negative jail probes use `_require_exact(...)`, which asserts: the candidate
  `harness/resident_jail.py` actually exists and was executed, the exact exit code `98`, the injected
  failure marker on stderr, the absence of `can't open file`/traceback text, and that the payload
  sentinel was **not** executed. "nonzero == PASS" appears nowhere.
* Applied to MS_PRIVATE, privdrop, setgid, setgroups and setuid; marker
  `NEGATIVE_JAIL_ACTUALLY_EXECUTED_PASS`.
* `PORTABLE_CHECKOUT_PASS`: the probe is copied to a random `/tmp/<random>/` checkout and re-run end
  to end; it still reaches the gate.

## BLK-03 — canonical startup/freeze runbook was not executable

* `--lock` is now `$RUN_ROOT/runtime/world.sqlite.writer.lock` everywhere (0 residue for the old
  `world.writer.lock` spelling); the documented invocation matches `cli.py`'s
  `--lock == <canonical-world>.writer.lock` requirement.
* The doubled ```bash fence in `procedure/b_startup_procedure.md` is repaired (fence count balanced).
* The hardcoded `2026-11-05T09:00:00-08:00` is replaced by a mechanically derived
  `CURRENT_OCCURRED_AT` from the actual projection, with a guard that refuses to proceed if it cannot
  be derived.
* The per-cursor projection loop is closed: after each reveal the runbook writes
  `current-event.json` **and** the operator-side `$RUN_ROOT/evidence/event-014.projection.json` …
  `event-022.projection.json`; the final freeze verifies count = 9, sequences 14..22, unique event ids
  and a SHA manifest.
* Stale `RealProviderClient` / working-`FakeProviderClient`-in-production wording is gone;
  `ExternalBrokerClient` is documented as the only production transport.
* `CANONICAL_RUNBOOK_STATIC_PASS` + `CANONICAL_RUNBOOK_EXECUTABLE_PASS` (real execution against a
  disposable lineage copy: rev 98, watermark 98, lag 0, `AUTO_RECOVERABLE`, `quick_check ok`).

## BLK-04 — binding fails open when live release state is absent

* `validate_current_event_binding()` re-reads and re-validates the live `release_state.json` on
  **every** production dispatch. `None`, missing, unreadable, malformed JSON and non-object states
  all raise `BLK-04: release_state …` before anything else happens. There is no receipt-only
  shortcut that lets the check pass without live state.
* Mandatory adversarial regression: build the handler normally, delete `release_state.json`, invoke
  the same handler again → provider invocations stay **0**, the handler is poisoned and fail-closed,
  and a durable failure receipt is produced. Gate `MISSING_RELEASE_STATE_FAIL_CLOSED_PASS`.

## BLK-05 — production dispatch with `event=None`

* `current_event is None` is an unconditional STOP: poison, `ModelDispatchNotSubmitted`, no provider
  call. The old relaxation based on `wake_reason` / `round_index` was deleted outright.
* `procedure/per_cursor_interaction.md` documents the full lifecycle: reveal → immutable receipt →
  event present → ingest → rounds → complete all model work → durable ACK → only then clear
  event/receipt → reveal next before any further model invocation.
* Regressions: `periodic_review` round0 / round1 / round3 with a missing event all FAIL with
  provider invocation count 0 (`NO_EVENT_NO_DISPATCH_PASS`).

## BLK-06 — Scheme-A receipt collision + outstanding clear ordering

* Receipt names are `failure-<session>-round-<round>-<time_ns>-<8-hex nonce>.json`, created with
  `os.open(..., O_CREAT|O_EXCL|O_WRONLY, 0o400)` — exclusive creation, never overwriting an old
  receipt. `failure-latest-<round>.json` is a separate pointer written unlink-then-write.
* Cleanup order is now: capture the outstanding snapshot → poison the handler → clear
  `self._outstanding` → build the evidence → persist the unique receipt. An evidence-write failure
  leaves the handler poisoned and `outstanding == None`, and is reported as its own
  `evidence_persistence_failure` class instead of destroying the original failure class.
* Regression: two handlers, same session + same round + same second → two distinct mode-0400
  receipts, no collision, both `outstanding is None`, original failure class preserved
  (`FAILURE_RECEIPT_COLLISION_PASS`).

## BLK-07 — inherited-FD isolation escape

* `_close_inherited_fds()` runs **after** all mount/setup work and **immediately before**
  `os.execvpe`, keeping only `0/1/2`. It uses `os.close_range(3, …)` when available, falling back to
  `os.closerange`, then a safe walk of `/proc/self/fd` that skips the fd opened by the walk itself.
  If `/dev/fd` is retained it can only ever show `0/1/2`.
* Adversarial proof: the operator opens the sealed fixture, the evaluator-only design notes and an
  unrelated file, dups two to higher numbers, and inherits all five into the jail. Inside the sandbox
  `/proc/self/fd` shows no such descriptors, `/dev/fd/N` has no entry / `EBADF`, the sealed bytes are
  unreadable, and the payload still runs (`PAYLOAD_RAN_OK`). Gate `INHERITED_FD_SEALED_PASS`.

## BLK-08 — contract provenance bound to a hardcoded repo path

* `REPO_ROOT_DEFAULT` is deleted. The repo root is resolved mechanically from
  `Path(__file__).resolve()` by walking up to the unique ancestor containing **both** `src/aios_core`
  and `reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_B_RUN_CONTRACT.md`; 0 or >1 matches
  fail closed. There is no absolute-path fallback of any kind.
* The resolved contract must be a regular, non-symlink file inside the resolved root and its SHA must
  equal the frozen `28d3262f…`; the wire protocol is bound to the same checkout.
* Test: the exact candidate is copied to a random `/tmp/candidate-<random>/`, the handler is imported
  with `cwd=/tmp`, it finds **that candidate's** contract with the exact SHA, never touches the
  operator checkout, is unaffected by an external same-named contract, and fails closed on a
  candidate contract mismatch (`CONTRACT_PROVENANCE_PASS`).

---

## Fresh run evidence

| Item | Value |
| --- | --- |
| Probe | `reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/isolation/probe_e2e.sh` |
| Fresh raw log | `/tmp/probe_run18.log` (copied to `isolation/e2e_probe_output.txt`) |
| Raw log SHA-256 | recorded in `operator_manifest.md` (recomputed at every run, not trusted) |
| Result | `ALL_CHECKS=139/139 FAILURES=0` |
| Marker | `CORRECTIVE_009_E2E_PASS` |

## Superseded leaked evidence — mandatory notice to future Residents

Commits `3796377` → `670c05b` on this branch remain reachable in history by design (no force-push,
no rebase, no squash, no history rewrite). Their pre-CORRECTIVE-009 `isolation/e2e_probe_output.txt`
and `isolation/probe_output.txt` contain the **sealed cursor-14 `resident_visible_payload` in
cleartext**.

* Those commits are **superseded leaked evidence**.
* **No Resident (B or C) may read git history, old commits, or those blobs.**
* All B and C evidence must be produced from the current candidate tip, whose evidence files are
  regenerated and payload-free.

## Not performed

No PR #209 merge, no `src/aios_core/**` change, no sealed-fixture / evaluator / governance / #205
change, no real cursor-14 reveal to a model, no real Resident B run, no Resident C run, no B release
entry, no C15 evaluator/close, no C16/P16/P17.
