# C15 operator preflight — increment 2

**OPERATOR ONLY. Preflight remains IN_PROGRESS / BLOCKED; no real Resident launch.**
PR #125 / claim #124. Fixed branch `arena/01a0cf25-haneof-aios-core-v3-0`.
No recovered previous-window local patch; increment 1 was new engineering.

## Implemented boundaries

- `audit.py`: fixed accepted-A bytes, manifest, 88/88 watermarks, durable receipt
  references, tracked Core tree. Does not open a real sealed fixture.
- `restart.py`: exact A copied into an exclusive new directory; mechanical-only
  fresh-session plan. A note/prose/old session turn index is not injected. Core
  services open only the COPY, with a callback that raises on any model request.
  Validate unchanged watermarks and the normal durable Review marker's next due
  time. SUPPRESSED is a legitimate terminal *scheduling* marker, not semantic
  success. Unresolved/backlogged markers fail closed. Verify Core import paths.
- `transport.py`: request UUID + request kind + canonical input SHA256 binding;
  explicit directive/summary only. No default answer/silence, output replay or
  self-reported telemetry. Callback failure poisons further execution even if
  Core catches the exception internally (e.g. round Summary). Observe full
  actual returns, tools, failures, metering and revisions. Trace files are
  exclusive, mode 0600 from creation, fsynced and hash chained; not attestation.
- `driver.py`: single-writer/flock coordination of frozen C15 release, canonical
  user/mechanical ingest, existing durable ACK and ordinary Fused run_turn. ACK
  certifies ingest only; processing completion is a separate checkpoint. Session,
  turn, text and timestamp are identical between canonical adapter and run_turn.
  Stop before revealing beyond the authorized synthetic boundary. Persist phase
  intent before effects; failed/interrupted stages cannot silently resume/replay.
- `clock.py`: reuse `tests/habitation/current_core.py`'s existing advance_to and
  task/Review helpers attached to the *same* Runtime/store/index, not its target
  constructor. Genuine Runtime calls pass through the observer. Its direct Wake
  helper is routed through normal `dispatch_next_pending_wake` to respect batching
  and REVIEW_QUEUE exclusions. Prior clock deadlines run before current-event
  ingest so earlier snapshots cannot see that future input. At the event time,
  normal Summary/Wake paths run and legitimate queued/deferred work is recorded.
  No clock jumps to force a successful response. Safety/source caps fail closed.
- `freeze.py`: only a clean, owned boundary. Canonical index rebuild, simultaneous
  SQLite BEGIN IMMEDIATE writer reservations on BOTH DBs, SQLite backup API
  including WAL, verify joint watermarks, durable receipt refs, source state and
  release hashes. Publish the private hash manifest/package only after checks.
  A partial backup is not a completed freeze. Source becomes FROZEN, not runnable.
  Advisory file lock is not protection against a malicious same-user operator.
- `restore_frozen`: requires an externally pinned manifest hash; copies only
  durable World/index/release/mechanical checkpoint, NOT old trace/model output.
  New callback and new trace are required. This is clean-boundary resume only.
- `isolation_probe.py`: an actual minimal user/mount/network/PID namespace + chroot
  probe, no capabilities/no-new-privileges, read-only allowlisted Python/packet,
  no proc/Git/gh/shell/env credentials. **Synthetic process only, not a Resident.**

The executable ReleasePort refuses the real C15 fixture pin. Tests configure
copies of existing release modules with newly generated synthetic files in tmp
folders. No fixture source is modified and no real B/C content is loaded.
Only tests contain scripted peers. There is no live model/provider implementation.

## Commands (repository root; Python >=3.12)

```sh
python --version
python -m pip install -e '.[dev]'
python -m pytest -o addopts='' -q tests/preflight
python -m pytest -o addopts='' -q tests
python -m tools.c15_preflight.audit --handoff-dir /PRIVATE/accepted-a --repo "$PWD"
python -m tools.c15_preflight.isolation_probe --repo "$PWD" --private-a /PRIVATE/accepted-a
```

The isolation probe additionally requires Linux unprivileged user/mount/net/PID
namespaces, mount/chroot/setpriv, `/usr/bin/python3.11` and its stdlib. It reports a
failure instead of pretending success if unavailable. Its supervisor can be 3.12;
the minimal child's exact system interpreter is separately reported. It is **not**
a provider/runtime test. Public CI does not require this host facility or private A.

For private restart verification (operator only, no model/fixture calls):

```python
from pathlib import Path
from tools.c15_preflight.restart import stage_accepted_a, validate_staged_core
stage_accepted_a(Path('/PRIVATE/accepted-a'), Path('/PRIVATE/new-copy'), Path.cwd(),
                 new_session='operator-restore-validation-NOT-B')
validate_staged_core(Path('/PRIVATE/new-copy'))
```

Supply exact five files in `audit.HASHES`, raw bytes from #117 at `audit.A_SHA`.
Never use an empty base64 Contents API field for the >1MB index. Real A originals
must have no live WAL/SHM/journal; hash check precedes immutable read. Do not use
`immutable=1` for a live database. Initial staging uses exact frozen bytes; final
freezing of a running synthetic World uses SQLite backup, not file copy.

## Remaining blockers and limits (not a complete preflight)

1. Independent PM approval of real session/restart/packet and a real release host
   is absent. No real launch command is supplied; packet `launchable=false`.
2. Linux synthetic denial checks do NOT isolate this Arena coding agent's tools.
   A Resident-safe broker/client must actually be connected to the minimal
   boundary, with platform tool/network/search/PR access denied and tested. Same
   user subprocess without that boundary remains known unsafe.
3. Interrupted/ambiguous ACK/model/freeze phases stop for operator review. No
   general mid-phase crash recovery or automatic model re-request. Clean frozen
   restart is tested; arbitrary RUNNING-Wake/deferred recovery across process
   death still needs dedicated end-to-end coverage before release.
4. Summary text callback does not provide trusted provider usage. Core C13
   metering is retained for its normal model calls; identity/tokens remain
   UNKNOWN without trusted external telemetry. Hash chains are not provenance
   attestation; no R6 claim.
5. A private cache survives ordinary processes in this sandbox, not session
   snapshot restoration. No approved persistent private store was provided.
   Re-fetch exact pins from #117; do not upload A to Git or public CI/artifacts.
6. Local Python 3.12.11 was built from upstream CPython tag in an external cache
   because binary/apt HTTPS endpoints were unavailable. It has SQLite 3.40.1;
   SSL and some optional stdlib modules are absent. Mechanical tests can run,
   but this is NOT certification of a production/provider Python environment.

Detailed evidence: `reviews/C15_RCC_RES_B_PREFLIGHT_ROUND2_2026-09-24.md`.
The protocol-only `resident_packet/` excludes operator documents/source/old runs.
It is not an approved launch packet or proof of the actual model's tool isolation.
