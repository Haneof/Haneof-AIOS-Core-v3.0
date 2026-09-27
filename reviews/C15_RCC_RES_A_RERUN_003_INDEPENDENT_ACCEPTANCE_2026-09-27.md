# C15-RCC-RES-A-RERUN-003 — Independent Fresh Resident A-003 Evidence Acceptance Review

**VERDICT: `ACCEPTANCE_PASS`**
**CANDIDATE: `5b6367406c13ea9450b7b2598a5813a64129cbd7` / tree `6402fff8b0c8c834e7b3f6b5d7c7427d0f846933`**
**BLOCKERS: `0`**
**DISPOSITION FOR PM: `READY_FOR_PM_INTEGRATION`**

| Field | Value |
|---|---|
| Task | `C15-RCC-RES-A-RERUN-003-INDEPENDENT-ACCEPTANCE` |
| Role | Independent Fresh Resident A-003 Evidence Acceptance Reviewer (fresh context, adversarial posture) |
| Reviewed object | PR #235 evidence candidate, 122 files, `+30247 / -0`, 1 commit |
| Reviewer objective | independently **redden** the exact evidence candidate; not to confirm the author |
| Review date | 2026-09-27 (UTC) |
| Method | read-only over `git cat-file blob <HEAD>:<path>` of the exact PR head; frozen Core re-computation; `mode=ro` scratch copies of the durable DBs; 14 frozen independent probes |
| Prior verdict superseded | none — this is the acceptance review of the re-run candidate |

---

## 1. Verdict lines (25 named gates)

Each line is an independent re-derivation, not a restatement of the author's report. `PASS` means the
reviewer's own computation reproduced the fact; `OBS` marks a non-material observation recorded for
PM visibility.

| # | Gate | Verdict | Independent evidence |
|---|---|---|---|
| L01 | live main, no drift | **PASS** | live `origin/main` re-fetched at review time = `7549322681ada61ab6d3c6eee5082acc00a658d6`; candidate parent = that exact commit; `git rev-list main..HEAD` = `0` behind / `1` ahead |
| L02 | PR #235 state / head | **PASS** | `gh pr view 235`: `state=OPEN`, `isDraft=true`, `mergedAt=null`, `headRefOid=5b636740…cbd7`, base `main`; exactly 1 commit; exactly 1 issue comment (the pin comment `5856077069`), no post-pin commits |
| L03 | evidence-only scope | **PASS** | `git diff --name-status 7549322 5b63674` = 122 `A` (added) files, all under `reviews/internal_habitation/c15-rcc/v1/resident/a003/`; `0` files outside that root, `0` deletions/modifications, `0` touches to `src/`, `tests/`, `governance/`, release-state, or fixture |
| L04 | SHA256SUMS integrity | **PASS** | P01: `120/120` entries recomputed from exact Git blob bytes match `sha256sum`-normalized paths (`./` prefixes normalized); `0` mismatch, `0` duplicate path entries; the only unhashed files are `A003_RESIDENT_RUN_REPORT.md` and `SHA256SUMS` itself |
| L05 | frozen execution software identity | **PASS** | `run_manifest.json.execution_software.frozen_commit = 27a21db5b656d441248b9240020910b66a223830` (CORE_RC_REFREEZE_002), which is an **ancestor of live main** (governance-merge separated from execution software); no drift between claimed and actual |
| L06 | frozen Core tree identity | **PASS** | P00: `git rev-parse 27a21db5:src/aios_core = a9618abe0b3d4ac3b08bd23dbd58f3e3f97e05d6` == manifest `frozen_core_tree` == live-main `src/aios_core` tree (the code the reviewer imported for every re-derivation is byte-identical to the frozen Core) |
| L07 | frozen tests tree identity | **PASS** | P00: `git rev-parse 27a21db5:tests = 92fcbcc5876833735fb3cb7c73a98c4a8a4a3541` == manifest `frozen_tests_tree` == live main `tests` tree |
| L08 | runtime environment | **PASS** | P11: declared CPython `3.12.14` + Pydantic `2.13.5` match `reviews/CORE_RC_REFREEZE_002/environment_manifest.txt`; Pydantic 2.13 behaviour marker (`errors.pydantic.dev/2.13/v/enum`) is present inside the raw provider request payloads themselves, so the version claim is corroborated by artefact content, not by self-report. SQLite question → §Q2 |
| L09 | freshness / non-reuse of A-RERUN-002 | **PASS (proven, not declared)** | P05: zero A-002 identity markers in all 122 files — session slug `c15-rcc-res-a-rerun-002*`, process identity `2079f64af49c…`, A-002 final World rev 98 evidence, A-002 digests `626c6bb3…/ecfabf4e…/eada20a0…`, prior-RC software `773876f9…/fe77f8a0…`, prior evidence PR `#205`, `resident/a00[0-2]` paths — all `False`; structurally impossible to be a copy: A-003 World has 42 revisions / 76 object revisions and session `resident-a003-0f5ffeff…`, A-002 had 245 object revisions / rev 98 |
| L10 | release receipts 1..13 | **PASS** | reviewer recomputation (frozen `c14-resident/v2/release/release_operator.py` + `fixture/release/bindings.py` loaded from scratch copies) reproduces **13/13** receipt records byte-exactly against the sealed fixture: `event_id`, `occurred_at`, `fixture_payload_sha256`, `fixture_projection_sha256`, `ingest_ref/object_id/revision/world_revision` |
| L11 | cursor-14 sealed / never revealed | **PASS** | P03: `0` evidence files for cursor ≥ 14 (sequence set = 1..13, `next_sequence=14`, `pending_reveal=null`); no cursor-14 event id, payload, timestamp or digest string anywhere in the candidate; the **frozen** release operator loaded against a scratch copy of the frozen state raises `ReleaseError: Phase A sealed boundary reached` on `reveal(14)`, and the state file is unmodified by the attempt |
| L12 | fixture projection correctness | **PASS** | P02: for all 13 cursors the released projection content equals `{k: fixture_event[k] for k in VISIBLE}`, exposes exactly the 8 visible keys, and canonicalizes to the receipt's `fixture_projection_sha256`; `fixture_sha256 = sha256:7ccb309d…b5ebf46` equals the reviewer's own digest of `fixture/sealed_fixture.json` |
| L13 | future / B-C leakage | **PASS** | P05: for each of the 25 semantic requests, a 14-gram shingle overlap against every *unreleased* fixture event, net of already-released text = **0 hits**; full-evidence 16-gram sweep against cursors 14..30 = 0 events; no `active_phase:"B"/"C"`, no `c15rcc-014..030` ids, no evaluator design wording (`EVALUATOR_ONLY`, "ground-truth leaves", "unsupported-self", "Do not evaluate by string match"), no future timestamps |
| L14 | canonical USER ingest idempotency | **PASS** | P04, cursors 1,3,5,6,8,10,12: the release receipt's `ingest_object_id` equals the `run_turn` output's `user_observation_id` for all 7 (the canonical USER observation created once at cursor 1 is *reused*, never re-minted); each `obs_conv_user_*` row exists at `revision=1` with exactly one object revision; payload `value`, `metadata.session_id`, `metadata.turn_index` (1..7), UTC-normalized `occurred_at` and `source_kind=user_ai_interaction` all match the frozen projection; semantic-duplicate count per canonical text = 1; the ingest trace records `idempotent_replay=false` (the `reused_existing` field belongs to the mechanical path only) |
| L15 | mechanical ingest cursors | **PASS** | cursors 2,4,7,9,11,13 → `obs_c14_fixture_*` observations recorded in the receipt chain with `ingest_source_class=platform` and confirmed by the durable commit `source_class=platform` at the same world revision (1,10,11,15,16,19,26,30,32,33,36,37,39 ↔ durable wr identical for 13/13); durable `world_commits` source split = user 7 / platform 6 / ai_cognition 17 / maintenance 12; ack traces expose only `status/sequence/event_id/next_sequence/ingest_ref`; receipt-chain `ingest_world_revision` is strictly monotonic (the earlier r1-vs-r2 caution is resolved: 1 → 10 is correct, r1 is the founding commit) |
| L16 | Resident semantic provenance (request → decision → next) | **PASS** | P06: 25 request/decision files `dec-00003..dec-00027` contiguous and paired (`00001/00002` = the two pre-serialization bridge crashes, documented); each request's `model_attempt_id` binds to a durable `background_model_attempts` row and each decision's `capability_history` contains only results produced at **earlier** rounds of the same wake; the causal chain reproduces the recorded 25-step narrative (illegal `standing_engagement` and `active` rejections, rejected `running→ready`, `READY_FOR_UPLOAD ≠ published`, checksum-mismatch refusal to notify stores, digest `sha256:7f2a9d1c54b0` quoted only after wr 39, DRAFT runbook never promoted) |
| L17 | bridge provenance (Q1) | **PASS** | P10 pins the *durable effect* of the bridge in both directions: 25/25 outbound `request_fingerprint` recomputed, 25/25 `provider_request_id` relay ids match the durable bindings, 25/25 decision bodies re-encoded through frozen `encode_model_directive` → `payload_sha256`, 25/25 `_response_fingerprint` match, 25/25 HMAC proofs `bgresponse_v1_…` recomputed with the World's `background_model_authenticity_authority.secret_hex`. See §Q1 for the scope of that proof |
| L18 | cursor-1 double recovery | **PASS** | P08: `attempt_id`/`meter_record_id` for **25/25** attempts re-derived from frozen `background_attempt.py` (`canonical_json_dumps` + `sha256[:32]`) → `0` mismatch, including `bgattempt_e70cedf7b64cf6f18d78253ac8382df0` / `meter_48804a4581b96b271c67c618ef96658f`; first inspect honestly reports `state=in_doubt`, `provider=null`, `provider_request_id=null`, `retry_count=0`; both failures are pre-submission (no durable receipt/binding for 00001/00002, `background_model_responses` count `0`, `failure_kind=NULL`); Core-side reconcile reports `attempts[0].state=not_submitted, recovery_disposition=safe_to_retry` and `retry_authorized=true`; final `retry_count=2`, `retry_authorized=0`, `state=completed`; exactly **1** receipt / **1** binding / **1** metering row for the attempt; `model_rounds=5` in the completed turn and in `cursor-001-turn.out`; no duplicate USER ingest (L14) |
| L19 | due-work re-derivation | **PASS** | independently re-derived from the frozen `src/aios_core/review/periodic.py` against the durable World: due review cursors are exactly **1, 6, 7, 13**; 4 wakes (`wake_review_da0d6bc6…`@wr 6/7/9, `03edc675…`@22/23/25, `8901873e…`@27/28/29, `0b6afd10…`@40/41/42), all `truncated:false`, `reason="periodic review due with eligible world changes"`, windows chain `10-30 → 11-02 → 11-03 → 11-04 → 11-06`, states new→running→completed, `model_rounds 3/3/2/2`; **0** round summaries due is mechanically forced (`7 ≤ recent_turn_limit 8` in frozen `context/continuity.py::prepare_next_round_summary`); final due set empty |
| L20 | request / decision counts | **PASS** | 25 requests, 25 decisions, 25 durable attempts, 25 bindings, 25 receipts, 25 metering records; `work_kind` split `15 user_turn + 10 periodic_review`; `0` missing, `0` orphan, `0` duplicate `provider_request_id` |
| L21 | metering / attempt / receipt discipline | **PASS** | P07: every attempt `state=metered`, `unmetered=0`, `orphan_receipts=0`, `dup_meter_work=0`; `usage_complete=0` with NULL token columns — **no fabricated usage** (declared as omitted); `background_model_responses = 0` (no out-of-band response store); receipts join attempts 25/25 |
| L22 | World / index coherence | **PASS** | P09: `world_commits` = 42 rows, min 1 / max 42, `chain_gap=0`, meta `world_revision=42`, `operations=42`, `idempotency=42`, `orphan_ops=0`, `PRAGMA quick_check=ok`; `object_revisions` = 76 (observations 20 = 7 USER + 7 AI + 6 platform, claim 6, dependency 28, evidence_set 6, task 4, wake 12), max `created_by_world_revision=42`; search index: `76` docs / `76` postings, `0` tombstones, `search_watermark_world_revision = 42` ⇒ **lag 0** |
| L23 | backup coherence | **PASS** | P09: backup is `397312` bytes like the live DB, `quick_check=ok`, backup `world_revision=42`, and **10/10** per-table sorted digests (`world_commits`, `object_revisions`, `operations`, `idempotency`, `metering`, `attempts`, `bindings`, `receipts`, `authority`, `turn_exec`) are identical ⇒ logically identical / `AUTO_RECOVERABLE`; bytes differ (`bytes_identical=False`) as expected for an independent copy (page/rowid ordering), which is not a defect |
| L24 | cognition temporal cut | **PASS** | P12: across all 76 object revisions **no** reference to an object born at a strictly later world revision, **no** dangling reference; every `evidence_set.knowledge_window.world_revision` (1, 7, 11, 16, 19, 33) is strictly prior to its commit; all 25 review anchors resolve inside the released window (none future); claim `clm_d5f6cb68fdb74636f46360e7` revs 1..6 and task `task_835d0a7919485a65096f04ba` revs 1..4 (`draft→ready→running→waiting_user`, never terminal) are temporally legal, with the production-deletion discipline revision 5/6 after cursor 10; cursor-13 boundary cognition appears only after wr 39; `READY_FOR_UPLOAD` never promoted to `PUBLISHED` and no tag/digest written before confirmation |
| L25 | contamination (independent) | **PASS** | P05: `0` future-event matches, `0` unreleased markers, and `0` historical contamination across all 122 exact files (A-002, prior-RC software, PR #117-era ids, `#9x/#10x/#11x/#20x` references, evaluator wording, B/C material, prior evidence paths, other `subject_id`s) — with `A-RERUN-002` mentioned exactly once, in the mandated non-reuse declaration (`rerun002_mentions=1 unqualified=0`) |

**Named outcomes required by the task:** `A-RERUN-002 = HISTORICAL_FOR_PRIOR_RC_ONLY` (retained, not
reused, not graded against) · `A-RERUN-003 = ACCEPTED_FOR_NEW_CANONICAL_RC` · freshness =
`NOT REUSED` **proven** by L09/L25 · `0` blockers, therefore `ACCEPTANCE_PASS`.

Two gates were flagged as "not yet declared" in the author's own framing and remain the PM's to
declare, not the reviewer's: `RELEASE-003` may be prepared; phase **B/C** remain unreleased. This
review neither grants nor withholds that; it only establishes that nothing in the candidate pre-empts it.

---

## 2. Q1 — is the Resident bridge proven to have carried no cognition?

**Answer: `PROVEN` at the mechanical/transport level; the irreducible residue is named and does not
constitute a blocker.** `IA-A003-BLK-BRIDGE-PROVENANCE` is **not** raised.

What was proven, from durable evidence only:

1. `/home/user/a003_run/driver/resident_bridge.py` is **not present** in the sandbox and is **not part
   of PR #235** (the PR is evidence-only: `0` driver files). So the bridge's source cannot be audited
   directly, and "a rewritten bridge looks the same" would have been rejected as evidence.
2. Instead, the bridge's *entire observable effect* is pinned to frozen Core digests in both
   directions (P10): the outbound request fingerprint (Core's canonical request digest), the
   `provider_request_id` relay, the inbound body re-encoded through frozen
   `encode_model_directive` to the receipt's `payload_sha256`, the Core `_response_fingerprint`, and
   the HMAC authenticity proof recomputed from the World's own authority secret — **25/25 in every
   category, 0 mismatch**. A component that authored, selected, edited, reordered, pre-composed or
   replaced any semantic decision would have to break at least one of those five identities, because
   each inbound body is *defined* by the digest the durable receipt attests and each request body is
   *defined* by the digest the Core computed from the then-current World.
3. Direction of causality is additionally excluded by construction, not assertion (P06/L16): a
   decision file can only be paired with the request whose `model_attempt_id` exists durably before
   it, the request's `capability_history` carries only earlier-round results, and the attempt ids are
   Core-derived hashes of that World state (L18) — so the payloads could not have been written from a
   pre-existing answer table without violating the binding chain.
4. `background_model_responses = 0` (L21) removes the "shadow response store the bridge read from"
   hypothesis: there is no second durable place a response could have come from that the receipts do
   not attest.

Residue named for PM: the *cognitive* origin of the 25 decision bodies (why this Resident chose this
text) is not a mechanically checkable property, and no digest method can make it one. What is
mechanically excluded — and was excluded — is scripted, replayed or future-influenced generation, and
the 122-file leakage/temporal sweep (L13, L24, L25) closes the "future fixture" variant of that
concern. Per the task's own rule, A-003 is not graded on agreement with A-002, so no semantic
equivalence was required or assumed.

## 3. Q2 — SQLite 3.53.4 in the run vs the `3.50.4` seen in the RC records

**Answer: `NON_MATERIAL / ACCEPTABLE`.** Decided from the authoritative RC artefacts, not from
"the tests passed".

1. The authoritative environment contract for the RC is
   `reviews/CORE_RC_REFREEZE_002/environment_manifest.txt`, and it **does not pin SQLite**: it pins
   CPython `3.12.14`, Pydantic `2.13.5`, pytest `8.4.2`, records a range-based `requires-python`
   from `pyproject.toml`, and states "no lockfile". `source_manifest.json` pins file digests only.
   `.github/workflows/core-rc-refreeze-002-formal-gate.yml` pins `python-version: "3.12.14"` and
   contains no SQLite reference. `release/rc/CORE_RC_REFREEZE_002_OPERATOR_PACKET.md` mentions
   "SQLite" only as the identity of the durable truth store, never as a version. P11 asserts exactly
   this: `sqlite_pinned_in_rc=False`, `workflow_python_pin=True`, `pyproject_range_based=True`.
2. Repo-wide, `3.50.4` occurs in **exactly one** place: `governance/CORE_RC_REFREEZE_002_INTEGRATION_RECEIPT_2026-09-27.md:51`,
   a PM-side narrative of how the RC machine happened to be assembled. That is an observation about
   one machine, not an execution identity imposed on later runs. It must not be upgraded into a pin,
   and no gate document lists it as one.
3. The run's `3.53.4` is the static amalgamation of its pinned CPython `3.12.14` source build
   (`run_manifest.runtime_environment.python` says so verbatim), i.e. a strictly newer,
   forward-compatible detail of a *pinned* interpreter.
4. Code-sensitivity check: the frozen storage layer uses no version-gated SQL. The only
   version-sensitive construct in the Core SQL surface is `WITHOUT ROWID`
   (`src/aios_core/query/search.py:605`), available since SQLite 3.8.3; no `RETURNING`, no
   `->>`/`->` JSON operators, no `STRICT` tables, no version pragma in the Core.
5. Decisive point: the run's durable output does not depend on the engine's cooperation for
   correctness here, because every identity that could drift with it was **independently recomputed**
   by the reviewer — 42/42 commit-chain, 76/76 index parity, 25/25 attempt and meter ids, 25/25
   payload digests, 25/25 HMAC proofs, and the 13/13 receipt chain. A different SQLite could only
   matter if some durable invariant had to be trusted to it; none was (L22, L23).

Therefore the difference is a runtime detail outside the frozen identity, not
`MATERIAL EXECUTION ENVIRONMENT DRIFT`. The pinned identities that *do* exist (software
`27a21db5…`, Core `a9618abe…`, tests `92fcbcc5…`, CPython 3.12.14, Pydantic 2.13.5) match exactly
(L05–L08).

---

## 4. Independent probe harness (freeze → enumerate → run)

| Item | Value |
|---|---|
| Harness | `reviews/C15_RCC_RES_A_RERUN_003_INDEPENDENT_ACCEPTANCE_2026-09-27/ia_a003_probes.py` |
| Executed harness SHA256 | `8c0033a5619f7eeaec8826562fc43bc248359be02aaa4539ca04189333485b40` |
| Frozen before first run | yes — `SHA256SUMS.probes.v1` records the pre-execution freeze (`5130acc5d49f…`, H0) and the full version trail is in `probe_run.md` / `SHA256SUMS.probes.history` |
| Enumeration | explicit, static, pre-execution: `probe_enumeration.txt`, `sha256 682c3a14bf0cdb11c5a46e1fc7ffd6d065a70c9f970c8767207997ac8620a1f2`, **unchanged through every run** (the harness is a standalone script, so enumeration is the frozen 14-line probe table instead of `pytest --collect-only`) |
| Probe count | 14 (P00..P13) |
| Result | **14/14 PASS** (`probe_results.txt`, `probe_results.json`) |
| Runs executed | 4 executed states: 0/14 (harness path bug, `probe_run_v1_harness_bug.txt`), 6/14 (`probe_run_v2_first_execution.txt`), 10/14 (`probe_run_v3_partial_10of14.txt`), 14/14 final. A re-run of the 6/14 bytes produced byte-identical output (`probe_run_v2_determinism_repeat.txt`, same SHA256), confirming determinism |
| Failure handling | every failing version is preserved verbatim; `probe_run.md` classifies each failure as harness bug or harness over-specification, states precisely what was changed, and confirms for each that the *expectation* it enforces was not softened |
| Negative controls | P13 drives the frozen Core with three synthetic forgeries and confirms fail-closed behaviour: authenticated return cannot be reconciled to not-submitted; unproven-absent execution is blocked; a tampered payload digest is detected against the durable receipt |
| Writer safety | no repo writes; SQLite opened `mode=ro` on scratch copies; the scratch release-state copy survives a `reveal(14)` attempt unmodified |

Two real observations surfaced by the harness are reported rather than tuned away (see `probe_run.md`
§"Real observations"): (a) the released projections are the canonical sorted-key serialization of the
frozen projection — content- and digest-identical, but not the operator's indented key order, so the
report's phrase "byte-exact" is exact for the canonical form only; (b)
`background_model_attempts.reconciliation_evidence` narrates provider non-submission in prose and
contains the literal token `not_submitted` in `0/25` rows, which is why string-matching that column
would be an unsound gate and why P08 checks the Core-produced reconcile record instead. Both are
`NON_MATERIAL` and neither changes any digest, id, revision or ordering.

---

## 5. Evidence digests (reviewer-computed from exact head blobs; independent == author == `SHA256SUMS`)

| Artefact | SHA256 |
|---|---|
| `world/resident_a003_world.db` | `3de9e73883f2676390436090eed0e4964b2e1ad71c79b5d9cc0ffb03a12862ad` (397312 B) |
| `world/resident_a003_world.db.search.sqlite` | `38193612a9ff256bef9fdd0014db5d0e1faa68745107cb79ef165a6a067e48d4` (401408 B) |
| `backup/resident_a003_world_backup.db` | `6d442d5a671e48d7964a8bb4c6ccbd1b9c42a0b276c1b8f73dd21f6912afa95f` (397312 B) |
| `release/a003_release_state.json` | `7728b12e0ff50f63446966f300ef5fd685668d1a7cf04b911de3d429003849e9` (10939 B) |
| `manifest/run_manifest.json` | `34bd0be959a9d082361bcfc8ed502cc9028a2ca071f56ae5fb4af1ab2522eb84` (1110 B) |
| `SHA256SUMS` | `81d92567551d982e9323a0ea4a7d85893c3da410053ffe23a24eff14af459426` (12030 B) |
| `A003_RESIDENT_RUN_REPORT.md` | `9cbec300791878253c0e6c828263db50fc5d19de24f80757f18f6621f957238a` (11583 B) |
| `fixture/sealed_fixture.json` | `7ccb309d207cb6ee240fbc008ee4f535e25571f04ba7ca1b7c95bf9afb5ebf46` (13941 B) — equals `fixture_sha256` in the release state |
| `fixture/release/bindings.py` | `00399004c39172b7…` (first 16 hex, of `reviews/internal_habitation/c15-rcc/v1/release/bindings.py`) |
| `reviews/CORE_RC_REFREEZE_002/environment_manifest.txt` | `d52ba5458014f5828c432bfb2c8a8d28e36b38b9138236d2d178ea8b02904f53` (1297 B) |

Candidate identity: head `5b6367406c13ea9450b7b2598a5813a64129cbd7` · tree
`6402fff8b0c8c834e7b3f6b5d7c7427d0f846933` · parent `7549322681ada61ab6d3c6eee5082acc00a658d6` ·
frozen software `27a21db5b656d441248b9240020910b66a223830` · Core tree
`a9618abe0b3d4ac3b08bd23dbd58f3e3f97e05d6` · tests tree `92fcbcc5876833735fb3cb7c73a98c4a8a4a3541`.

## 6. Reproduction

```bash
cd <repo-root>                      # any checkout of main 7549322… (frozen Core/tests trees)
git fetch origin main && git rev-parse origin/main        # expect 7549322681… (no drift)
gh pr view 235 --json state,isDraft,headRefOid,baseRefName,commits,files,additions,deletions
python3 -c "import ast;ast.parse(open('reviews/C15_RCC_RES_A_RERUN_003_INDEPENDENT_ACCEPTANCE_2026-09-27/ia_a003_probes.py').read())"
sha256sum reviews/C15_RCC_RES_A_RERUN_003_INDEPENDENT_ACCEPTANCE_2026-09-27/{ia_a003_probes.py,probe_enumeration.txt}
# expect 8c0033a5619f…5b40 and 682c3a14bf0c…0a1f2, then:
python reviews/C15_RCC_RES_A_RERUN_003_INDEPENDENT_ACCEPTANCE_2026-09-27/ia_a003_probes.py   # TOTAL 14/14 PROBES PASS
```

The harness inserts `<repo>/src` on `sys.path` itself (P00 first proves the working tree's Core and
tests trees equal the frozen ones, and that `git diff` between them is empty); it needs `pydantic`
available for the frozen Core import. It requires nothing else and reads only through `git cat-file`.

## 7. Reviewer boundary — what was deliberately **not** done

This review modified nothing outside its own evidence directory. It did **not**: merge, comment on,
close or otherwise alter PR #235; touch PRs #232/#234 or any governance merge; edit
`governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md` or the task checkpoint; write to the A-003 run, its
World / index / backup / release-state / raw traces / sealed fixture or the expected outcome; reveal
cursor 14 or any B/C material (the frozen Phase-A boundary was exercised only against a scratch copy);
re-run Resident cognition; grade A-003 on agreement with A-002 or on style; resume B persistence;
start `RELEASE-003`; or run phases B or C.

`ACCEPTANCE_PASS` yields `READY_FOR_PM_INTEGRATION` and nothing further.

## 8. Artefacts in this review

`reviews/C15_RCC_RES_A_RERUN_003_INDEPENDENT_ACCEPTANCE_2026-09-27/`

| File | SHA256 |
|---|---|
| `ia_a003_probes.py` | `8c0033a5619f7eeaec8826562fc43bc248359be02aaa4539ca04189333485b40` |
| `probe_enumeration.txt` | `682c3a14bf0cdb11c5a46e1fc7ffd6d065a70c9f970c8767207997ac8620a1f2` |
| `probe_results.txt` | `3d7330c0bc79372d67892bcaee38962dd1986e19f7ea64da5d4d6faacb566faf` |
| `probe_results.json` | `3d7f4aa0ee8b4d369f1ea2edc7370870215dbd640b0a89ac10e7641b39902022` |
| `probe_run.md` | `a3e8e6d50d9419ffbb7b541a5591467ff0e3ee46baaf686db87a003a6b13dde5` |
| `probe_run_v1_harness_bug.txt` | `90282ec7ba64781931a7cc2d30d75fef216f10258f94181101d063e5cd6a5312` |
| `probe_run_v2_first_execution.txt` | `7b0a6690d68f8585a74e498dd472489d248cf5db11bf5afd953005eece47aa0c` |
| `probe_run_v2_determinism_repeat.txt` | `7b0a6690d68f8585a74e498dd472489d248cf5db11bf5afd953005eece47aa0c` |
| `probe_run_v3_partial_10of14.txt` | `e941ccff5526e95e7a0ecb7cdc513335705cd92bb5589bc2d50ed380008be22c` |
| `SHA256SUMS.probes` | final freeze of all of the above |
| `SHA256SUMS.probes.v1` | pre-execution freeze (H0) |
| `SHA256SUMS.probes.history` | harness version trail H0→H4 |
