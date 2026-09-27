# Independent probe harness run log — C15-RCC-RES-A-RERUN-003

Reviewer-owned, read-only verification of candidate
`5b6367406c13ea9450b7b2598a5813a64129cbd7` (tree `6402fff8b0c8c834e7b3f6b5d7c7427d0f846933`).
The harness reads every artefact as `git cat-file blob <HEAD>:<path>` from the **exact PR #235
head**, never from a checked-out worktree, and opens the durable databases only as
`mode=ro` copies under `tempfile.mkdtemp`. Nothing is written into the repository, the
candidate, PR #235, the A-003 run, World, release-state, raw traces or the task board.

## Final result

    TOTAL 14/14 PROBES PASS        (probe_results.txt / probe_results.json)

* Frozen harness (executed): `ia_a003_probes.py`
  `sha256 8c0033a5619f7eeaec8826562fc43bc248359be02aaa4539ca04189333485b40`
* Frozen expectations: `probe_enumeration.txt`
  `sha256 682c3a14bf0cdb11c5a46e1fc7ffd6d065a70c9f970c8767207997ac8620a1f2`
  — **hash unchanged from the pre-execution freeze**: no expected outcome was moved after any run.
* Runner: `/home/user/work/ia-venv/bin/python` with `<repo>/src` on `sys.path`; the working tree
  is live main `7549322681ada61ab6d3c6eee5082acc00a658d6`, whose `src/aios_core` tree
  `a9618abe0b3d4ac3b08bd23dbd58f3e3f97e05d6` and `tests` tree
  `92fcbcc5876833735fb3cb7c73a98c4a8a4a3541` are the frozen execution identity (P00 proves the
  equality before any probe that imports Core runs).

## Revision history (failures preserved, not hidden)

| ver | harness sha256 (short) | run output | result | classification |
|---|---|---|---|---|
| H0 | `5130acc5d49f` | not executed | — | freeze recorded in `SHA256SUMS.probes.v1` |
| H1 | `ad7a6a34ba9c` | `probe_run_v1_harness_bug.txt` | 0/14, all `harness error` | **harness bug**: repository-root discovery used `Path.parents[3]`, resolving to `/home/user`, so `git -C` ran outside the repository (`fatal: not a git repository`) |
| H2 | `0857d096fb80` | `probe_run_v2_first_execution.txt` (+ `probe_run_v2_determinism_repeat.txt`, byte-identical output ⇒ run is deterministic) | 6/14 | 8 failures: 6 harness bugs, 2 harness over-specifications (see below) |
| H3 | transient | `probe_run_v3_partial_10of14.txt` | 10/14 | after 7 mechanical harness corrections; remaining 4 were matcher defects |
| H4 | `8c0033a5619f` | `probe_results.txt` | **14/14 PASS** | final frozen state |

Between H0 and H1 one pre-execution harness correction was applied and is disclosed here:
P04's `occurred` comparator had been written as `x == x` (a tautology). It was replaced by a real
UTC-normalised comparison against the sealed fixture's `occurred_at`. The **expectation** ("text /
session / turn / occurred must match the frozen projection") is unchanged; only the broken
computation was repaired, before the first execution.

## Per-failure classification (H2/H3 → H4)

| probe | failure observed | classification | what was changed | did the gate change? |
|---|---|---|---|---|
| P02 | `keyset@1..13` | harness over-specification | `list(keys)==list(VISIBLE)` → `set(keys)==set(VISIBLE)` | **No.** The gate is "released file exposes exactly the frozen visible projection, digest-identical to `fixture_projection_sha256`"; both the content-equality check and the canonical-digest check already passed, and still pass |
| P04 | `KeyError: 'reused_existing'` | harness bug | `.get()` fallback for the canonical-USER ingest shape | No |
| P05 | `ValueError: too many values to unpack` | harness bug | iterate `.items()` over the marker table | No |
| P07 | `no such column: subject_id` | harness bug | single-subject gate moved from `world_commits` (no such column) to `object_revisions` | No |
| P09 | `sqlite3.Row is not orderable` | harness bug | compare `sorted(tuple(r) …)` digests | No |
| P09 | `chain_gap=40` | harness bug | the chain SQL omitted the subtraction: it selected `lag(world_revision)` instead of `world_revision - lag(world_revision)`. Corrected query reports `chain_gap=0` | No |
| P11 | `sqlite_pinned_in_rc=True` | harness bug | the pin test matched any mention of "SQLite" (the operator packet names the storage engine) and the run manifest (which describes the run, not the contract). Corrected: a pin must be a version-bearing SQLite reference in `environment_manifest.txt` / `source_manifest.json` / operator packet / workflow / `pyproject.toml` → `False` | No — the probe's expectation ("SQLite is not a frozen execution identity") is exactly what is being tested |
| P12 | 6× `future-ref: clm… → evs…@same wr` | harness over-specification | refs born in the **same** world revision as the referring row are the frozen Core's atomic write-back (claim + evidence_set + dependency commit in one transaction); the hard temporal gate is "nothing born strictly later", which is what is now enforced | No — same-revision write-back is Core behaviour, not future evidence; the strict `>` rule still fails on any genuinely future reference, and the dangling-reference rule is unchanged |
| P05 | `prior_evidence_paths: True` | harness over-specification | pattern `resident/a00[0-9]` matched the run's **own** directory `resident/a003`; and `RERUN-002` matched the report line `A-RERUN-002 = NOT REUSED`, which the task *requires* to exist. Now: prior-run paths only (`resident/a00[0-2]`, `/home/user/a00[0-2]`, `C15-RCC-RES-B`), and every `RERUN-002` mention must carry a non-reuse / prior-RC-scope qualifier (`rerun002_mentions=1 unqualified=0`) | No — reuse of prior-run artefacts would still fail; unqualified reuse claims would still fail |
| P08 | durable `reconciliation_evidence` lacks the literal token `not_submitted` | harness over-specification | replaced a prose-token match with the substantive checks: Core-side `attempts[0].state == "not_submitted"` + `recovery_disposition == "safe_to_retry"` on both reconcile records (from the frozen CLI's own output), non-blank durable evidence asserting non-submission, and `failure_detail IS NULL` | No — the requirement "reconciled to `not_submitted` through the legitimate frozen path" is now checked on the Core-produced transition record rather than on narration wording |

Real observations surfaced by the harness and kept as findings (non-material, reported in the
acceptance verdict rather than suppressed by the corrections above):

1. **Serialization form of the released projections.** `events/cursor-00N.json` are the
   canonical **sorted-key, compact** serialisation of the frozen visible projection
   (`content == projection` and canonical digest `== fixture_projection_sha256` for 13/13), not the
   indented `_projection()` key order. The report's "byte-exact" wording is therefore exact only for
   the canonical form and its digest; the sealed `fixture/released/` files in the candidate are the
   same canonical form. No digest, id, revision or ordering differs.
2. **Durable reconciliation wording.** `background_model_attempts.reconciliation_evidence` for
   `bgattempt_e70cedf7b64cf6f18d78253ac8382df0` narrates the no-submission proof ("no directive bytes
   crossed it and no authenticated provider return receipt exists"); the machine-readable
   `not_submitted` disposition lives in the `reconcile_turn_model_not_submitted` /
   `authorize_turn_retry` CLI output. `0/25` attempts carry the literal token in that column, so
   string-matching Core wording there would be an unsound gate.

## Probe index (14)

P00 identity/scope/frozen-tree/live-PR · P01 SHA256SUMS from exact blobs · P02 receipt chain vs sealed
fixture · P03 cursor-14 absence + frozen sealed-boundary refusal · P04 canonical USER ingest
idempotency · P05 future-leakage + contamination · P06 request/decision pairing and causality ·
P07 metering/attempt/binding/receipt counts · P08 cursor-1 double recovery · P09 World/index/backup
coherence · P10 bridge transport-only pinning (fingerprints, digests, HMAC) · P11 RC environment
contract vs SQLite 3.53.4 · P12 cognition temporal cut · P13 negative controls (forgery paths
refused by frozen Core).
