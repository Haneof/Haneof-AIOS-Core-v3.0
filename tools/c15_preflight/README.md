# C15 operator preflight — reviewable increment 1

**OPERATOR ONLY. NOT A RESIDENT LAUNCHER. Overall preflight BLOCKED / incomplete.**
Task `C15-RCC-RES-B-PREFLIGHT-001`; claim issue #124. This is new work: the
previous window's local commit/patch was not obtained and is not represented as
recovered. Do not start real B/C using this package.

## Implemented / not implemented

- `audit.py`: immutable accepted-A byte pins, manifest cross-check, read-only
  World/index 88/88, 13 durable Observation references, mechanical restart field
  inventory, tracked Core tree comparison. It does not open a sealed fixture,
  execute A, initialize B, copy a World, or load historical decisions.
- `transport.py`: synchronous request-bound stream callback for existing
  `RuntimeSnapshot`, `RoundSummaryRequest`, and `DimensionSummaryInput`.
  Explicit structured output only; EOF/invalid returns raise. No fallback model,
  silence, answer, inferred telemetry, prompt-side cognition policy or replay.
- `RuntimeRecorder`: observer of existing FusedTurnRuntime entrypoints and
  actual registry invocations. Does not replace Runtime, ingest, clock or budgets.
  Records input/result/error, genuine capability requests/results, World revision,
  Core metering and index watermark. Final results/snapshots retain Core-denied
  capabilities as returned by Core. An exclusive fsynced hash-chain trace is
  operator-private, not a second World. A hash chain is NOT trusted attestation.
- Tests use in-memory **scripted synthetic peers**, never actual Resident/model
  responses. They exercise real Core paths in independent temporary Worlds.
- **Not implemented:** one-event release → canonical adapter → durable ACK →
  timestamp scheduling driver; real restart loading; complete durable due-work
  checkpoint; cancellation/resume; WAL-safe final freeze/export; actual host
  isolation; attested provider telemetry. Do not call this a completed driver.
- Summary callback records are observable transport data, **not proof of a
  provider-metered Summary call**. The current bridge deliberately passes no
  unverified usage/provenance into Core. Transport disconnects are recorded as
  errors, not successful calls.

## Commands and environment

From repository root, with Python >=3.12:

```sh
python --version
python -m pip install -e '.[dev]'
python -m pytest -o addopts='' -q tests/preflight/test_c15_operator_preflight.py
python -m tools.c15_preflight.audit --handoff-dir /PRIVATE/accepted-a --repo "$PWD"
```

The audit CLI refuses Python 3.11. Put the **exact five allowlisted files** listed
in `audit.HASHES` in the private directory, from #117 at `audit.A_SHA`; no A
transcript/decisions/checkpoints are needed or permitted as restart input. Obtain
raw bytes (the index exceeds 1 MB); never substitute a Contents API empty base64
field. Source archives must have no WAL/SHM/journal sidecar. A live DB instead
requires a separately reviewed WAL-safe snapshot process, not `immutable=1`.
The audit's receipt check validates durable refs, NOT a full fixture payload hash
recomputation. Core proof is tracked-source equality, NOT executable import-path
or process isolation attestation. Do not overinterpret these checks.

GitHub workflow `c15-operator-preflight` runs Python 3.12 synthetic mechanics and
relevant regressions. It does not retrieve private A material. Exact CI outcome
and Python version belong in the PR evidence, not inferred from this document.

The existing entrypoints can be wired by a future reviewed host:

```python
bridge = StreamBridge(incoming, outgoing, operator_trace)
runtime = FusedTurnRuntime(
    store=store, index=index, model_handler=bridge.model,
    round_summary_handler=bridge.round_summary,
    dimension_summary_handler=bridge.dimension_summary,
)
observer = RuntimeRecorder(runtime, operator_trace)
# Host, not this adapter, must supply authorized event/session/turn/time bindings.
# No real-session launcher or real-fixture command is provided in this increment.
```

## Isolation and separated packet

`resident_packet/` has only a protocol and draft mechanical manifest. No session
interface is approved (`launchable=false`). Do not give the Resident this README,
operator manifest, audit/source files, repository checkout, Git/PR tools, PM
reports, old A/B outputs or sealed data. A whitelist document alone is **not** an
access boundary. This same-user coding sandbox was negatively probed: an isolated
Python child could actually read PM/operator files and run `git rev-parse`.
**Current environment is not a blind Resident environment.**

Required before release: a separate principal/container or equivalent externally
approved tool interface with no repository/Git/GitHub credential mounts, no shared
operator/private evidence directory, network/tool allowlists and tested denial of
filesystem, Git, PR, search and out-of-band access. Test from the actual Resident
principal, not the operator. The permitted interface must expose only current
request/response data. Packet changes invalidate its pin and require re-review.

## Restart and freeze checklist for independent review (all still open)

1. Approve exact A World/index/release/restart bytes and a fresh B session. The A
   `session_id` and `conversation_turn_index` are historical audit values, not
   defaults for the new session. Retain permitted mechanical clock/Review cadence;
   never inject restart prose, A transcript, old directives or cognition summaries.
2. Prove canonical adapter and run_turn identical subject/session/turn/text/time;
   use the existing release/ingest/ack infrastructure without reading future
   cursors in preflight. Complete synthetic error/retry/due-work integration.
3. Demonstrate real-clock due Summary/Wake/Review paths respecting Core budget
   deferral. Do not force drain or advance clock to manufacture success.
4. Capture durable restart/due-work, release receipts, immediate usage/error chain,
   final synchronized index and World; quiesce writes and snapshot with SQLite's
   supported backup/checkpoint mechanism. Reopen immutable snapshot and validate
   hashes/revisions. No file copy of a live WAL database.
5. Validate actual isolation and obtain independent PM release. Identity/usage
   stays UNKNOWN until trustworthy external evidence exists. No R6 verdict.

No accepted-A private file, generated trace, cache or credential belongs in Git.
