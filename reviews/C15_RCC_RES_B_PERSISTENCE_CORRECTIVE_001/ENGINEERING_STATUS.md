# C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001 — execution checkpoint

Date: 2026-09-26

**Engineering status: WIP / BLOCKED — NOT REVIEW_READY.**
This is an incomplete implementation checkpoint, not Independent Acceptance,
not a PM ruling, and not authorization for RELEASE-003 or RERUN-003.
The task's dispatch status was confirmed READY before work. Its completion
contract has **not** been met; do not promote this checkpoint into a pass.

## Baseline and boundaries

- Fetched live `origin/main`: `f0f2eb8a7030b9b56cbec43c09574e056b2f7c61`.
- Worked only on `arena/01a0dce5-haneof-aios-core-v3-0` from that same commit.
- Read the task prompt, state-loss adjudication, current board/checkpoint,
  preserved operator incident report, and accepted preflight startup/per-cursor,
  final-freeze, environment and harness material.
- Core tree remains `fe77f8a0706acfaf369041d0882b6d0e6de39f22`.
- No tracked Core, sealed fixture, accepted preflight file, canonical A artifact,
  or historical incident report was changed. No real Resident was invoked.
- No real cursor was revealed; frozen E2E ran only its disposable probes. The
  new journal unit tests use cursor 101 and synthetic byte bundles; the Core
  boundary probe uses a newly created, empty synthetic World and synthetic turn.
- No retired run/session/request was used. No new B release identity was minted.
- No release/rerun/independent acceptance, PR, merge, or push was performed.

## Implemented subcomponent (deliberately disabled for production)

`tools/c15_persistence/journal.py` is an operator-side **synthetic-only prototype**:

- Requires `synthetic-` run/session/request identities. There is no launch path
  for a real Resident and no network provider.
- Explicit backend used by tests:
  `/home/user/c15-persistence-unit-probes/synthetic-unit-*/backend/journal.sqlite`.
  This is outside `/tmp`, inside the platform-persisted workspace, and outside
  platform snapshot exclusions. It rejects excluded paths, symlink aliases,
  `/tmp`, `/var/tmp`, and tmpfs/ramfs backing mounts. It is **not yet an installed
  authoritative backend for the released operator**.
- Private directory/database modes; exclusive initialization; reopen refuses
  absent state or mismatched identity rather than rebuilding a lost run.
- SQLite `journal_mode=DELETE`, `synchronous=EXTRA`, transactions and directory
  fsync. Immutable checkpoint generations hold exact artifact BLOBs and SHA-256
  manifests in the same transaction, including World/index/release/current-event/
  binding/projection/mailbox/failure evidence slots.
- Journal records cursor/event/round/request/nonce/request-digest/binding-digest,
  exact request/reply bytes and transport SHA-256. The protocol request digest
  is kept separate from the raw request body digest.
- Verifies checkpoint integrity and binding digest before staging; commits
  `exposed` before returning request bytes. Re-exposure and concurrent double
  exposure are refused. A lost exposure acknowledgement remains WAIT_NO_RESEND.
- Exact duplicate reply delivery is idempotent; conflicting bytes are refused.
- `staged -> exposed -> reply-staged -> applying -> applied` is journaled.
  Interrupted `applying` returns `IN_DOUBT_STOP`, not a fabricated successful
  application. An externally supplied synthetic application receipt is explicitly
  labelled **not Core verified**.

This component neither captures a live Core directory coherently nor validates
Resident semantics. Callers provide checkpoint bytes; the unit test uses SQLite
backup for synthetic DB bytes. Presence of the required slots is NOT proof of a
real World/release binding. This distinction is intentional and blocks release.

## Fresh verification and preserved red evidence

All logs are in `evidence/`; none of the failing logs were overwritten.

| Attempt | Actual result | Meaning |
|---|---|---|
| `frozen-attempt-01.log` | exit 1 after Python check | Frozen dependencies absent in sandbox; retained red |
| `environment-install.log` | exit 0 | Installed only exact frozen requirements, not an upgrade of the contract; this was engineering setup, not release |
| `frozen-attempt-02.log` | **158/158, 0 failures, exit 0** | Unchanged accepted E2E; `CORRECTIVE_013_E2E_PASS` |
| `lifecycle-attempt-01.log` | exit 0 | Unchanged lifecycle checker self-test; cross-document 5, executable 18, shell semantics 82 mutation-red cases |
| `persistence-attempt-01.log` | 13 setup errors, exit 1 | Root-owned E2E parent was not writable by unit runner; no test state created; retained red |
| `persistence-attempt-02.log` | **13 tests OK, exit 0** | Separate user-owned synthetic unit root; storage/journal tests only |
| `core-boundary-attempt-01.log` | **exit 2 / CORRECTIVE_CONVERGENCE_BLOCKED** | Actual SIGKILL after synthetic reply staging, before Core application; durable bytes survive but runtime continuation remains in doubt |

Unit tests cover process SIGKILL after staging/exposure/reply-staging/application
admission, interrupted SQLite transaction rollback, exact byte preservation,
concurrent exposure, missing/modified barriers, missing state, identity and path
rejection. They do NOT test the full release cursor lifecycle or claim to.

The Core boundary red state is preserved both in its original workspace directory
(named in the log) and byte-for-byte in `evidence/synthetic-core-boundary/`:
new synthetic `world.sqlite`, `index.sqlite`, opaque `reply.raw`, and result JSON.
No A or sealed-fixture bytes occur in that new synthetic red-state directory.
The frozen disposable E2E roots are separately retained at
`/home/user/c15-persistence-probes/frozen-attempt-01` and `frozen-attempt-02`.

## Reproduced recovery gap — not a Core regression verdict

`tests/c15_persistence/probe_core_boundary.py` creates a new World, enters a
synthetic user turn, writes/fsyncs opaque synthetic reply bytes, then kills its
own process with SIGKILL before returning a directive. A fresh runtime opens the
same World and observes:

- child exit `-9`;
- reply SHA-256 `5cfc42b2f36aba93f32045d8a40022ec8b9f99a669b51eab0d8b725cef10421f`;
- `recovery_disposition = in_doubt`;
- ordinary re-entry and explicit retry both refused;
- zero redispatches.

This proves a limitation of the **current candidate**, not the impossibility of
an operator-only solution. It intentionally does not invoke the production
handler or a real provider. Frozen handler inspection additionally shows
`_round`, `_outstanding`, and `_consumed` are process-local; returning a directive
is not a durable receipt that the runtime's effects have been applied.

Relevant existing Core surfaces were inspected but not modified:
`inspect_turn_execution`, `authorize_turn_retry`, `recover_turn_completion`, and
`BackgroundModelAttemptStore.reconcile_response`. Response reconciliation records
an attempt response fingerprint; it is not itself an exactly-once continuation
of the interrupted capability/work/ACK sequence. Neither declaring an actually
submitted request `not_submitted`, resetting execution rows, rewinding World,
nor blindly resending the saved reply is an admissible repair.

## Completion-contract matrix / remaining work

| Required contract | Current evidence / remaining gap |
|---|---|
| Authoritative non-ephemeral storage | Prototype workspace backend only. Real operator path/writer routing not integrated. |
| World/index/release/event/binding/projection/mailbox/failure durability | Synthetic bundle process-reopen demonstrated. Full live bundle coherence and platform environment reattachment not proven. |
| Durable provider relay journal | Byte-preserving library implemented; no HTTPS relay/frozen handler integration. |
| Durable barrier before Resident exposure | Library boundary tested. Production path can bypass it because it is not wired in. |
| Kill after reveal / after ingest | **Not implemented/proven** in the real release driver on disposable state. |
| Kill after request/reply staging | Journal persistence demonstrated; runtime convergence still blocked at reply/application boundary. |
| Kill after model/capability work before ACK | **Not implemented/proven**. Synthetic receipt cannot substitute for Core effects. |
| No duplicate reveal/ingest/application/ACK or skipped cursor | **Not proven end-to-end**. Library no-double-exposure is only at-most-once transport admission. |
| Frozen 158 + lifecycle mutation-red | Fresh pass, unchanged tests/materials. |
| REVIEW_READY | **Not reached**. Do not independently accept or release. |

A process restart is not an environment restart. No tool-triggered platform
restart/reattachment was performed; local fsync plus the platform workspace
persistence contract must not be misreported as a measured cross-environment
survival proof. A later controlled reattachment check needs to read a pre-pinned
manifest and all artifact bytes without reconstructing missing state.

## Reproduction (synthetic only)

From the repository root, with the frozen dependency subset installed:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/c15_persistence -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python3 tests/c15_persistence/probe_core_boundary.py
# Second command intentionally returns 2 for the unresolved convergence boundary.
python3 reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/checks/runbook_lifecycle_checker.py \
  --base reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002 --self-test
# Use a fresh disposable root for each frozen E2E invocation; never a live run.
RUN_ROOT=/home/user/c15-persistence-probes/frozen-attempt-UNUSED sudo -E bash \
  reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/isolation/probe_e2e.sh
```

Keep subsequent failed attempts under new log names. Continue only this corrective;
production launch is still prohibited. No expansion into Core modification or
later task is requested or authorized by this checkpoint.
