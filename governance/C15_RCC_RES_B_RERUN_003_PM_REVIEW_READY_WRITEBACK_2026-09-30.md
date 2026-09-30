# C15-RCC-RES-B-RERUN-003 — PM Readiness Writeback (WINDOW 09)

Date: 2026-09-30
Repository: `Haneof/Haneof-AIOS-Core-v3.0`
WINDOW: `09`
Task: `C15-RCC-RES-B-RERUN-003-PM-READINESS`
Role: C15 Governance PM / Resident-B Acceptance Readiness Reviewer
MERGE_POLICY: `GOVERNANCE_ONLY_AT_END`

**This is a readiness gate, not an acceptance verdict. It does not claim `ACCEPTANCE_PASS`.**

---

## 1. Verdict

```text
PM_READINESS_PASS
C15-RCC-RES-B-RERUN-003          = RUN_COMPLETE / REVIEW_READY
C15-RCC-RES-B-ACCEPT-003         = READY
```

Unique next READY: `C15-RCC-RES-B-ACCEPT-003`.
Still BLOCKED: `RESIDENT_C`, `EVALUATOR` (C15 semantic/R6), `C15_CLOSE`.

The single question this window answers is: «can `C15-RCC-RES-B-RERUN-003` enter an independent
`C15-RCC-RES-B-ACCEPT-003`?» The answer is **yes**, on the conditions recorded in §7–§9 below.

---

## 2. Fresh ground truth (fetched at dispatch, not summary-trusted)

| Anchor | Expected | Freshly observed | Verdict |
|---|---|---|---|
| live `main` | not a permanent baseline | `e25ec95bbe38c9127dd7234117466b429f8bfef6` | recorded, unchanged |
| PR #301 | MERGED | `MERGED`, mergeCommit `e25ec95bbe38c9127dd7234117466b429f8bfef6` | PASS |
| PR #302 | OPEN / EVIDENCE_ONLY / UNMERGED | `state=OPEN`, `isDraft=false`, `mergedAt=null`, `mergeable=MERGEABLE`, `mergeStateStatus=CLEAN` | PASS |
| PR #302 exact head | `846b55e63abe7f4d7c25adde013978cce6084556` | match | **no evidence drift** |
| PR #302 tree | `634ed0bfb5ebfcb9f7d7fe7de4418f1731925ace` | match | PASS |
| PR #302 parent | `f7ee14a23ab3c7de0793cecb7a83291fd2971110` | match | PASS |
| PR #302 base | `e25ec95bbe38c9127dd7234117466b429f8bfef6` | `git merge-base` = match | PASS |
| PR #302 commit count | 5 evidence-only commits | `git rev-list --count main..pr/302` = `5` | PASS |
| Fresh A PR #296 | exact `317316299c332d82e0cbd0431b5c7d50f391bc17`, OPEN | match (`state=OPEN`, `mergeCommit=null`) | PASS |
| authoritative persistence ref | `refs/heads/persistence/c15-rcc-res-b-rerun-003-60997e04` | exists | PASS |
| persistence remote head | `5692a32972f72afb6337aa68cc97310734f14c9c` | `git ls-remote` = match (= FINAL_FREEZE commit) | PASS |
| generation-head | `generation = 48` | `48`, `head_sha256 9cfe2639…`, `previous_head_sha256 ea59ba36…`, `manifest_file_sha256 c6a84e04…` | PASS |

**`PM_READINESS_BLOCKED_BY_EVIDENCE_DRIFT` is NOT triggered.**

Scope check on PR #302: `git diff --name-status main pr/302` = **8 added files, all under
`evidence/w08/`**; zero `src/**`, zero `tools/**`, zero `tests/**`. The
`EVIDENCE_ONLY / DO_NOT_MERGE AS IMPLEMENTATION` header is factually true.

### 2.1 Authoritative run identity (fresh, from `owner.json`)

```json
{"remote_authoritative": true, "phase": "B",
 "run_id": "c15-rcc-res-b-rerun-003-60997e04",
 "session_id": "c15-rcc-res-b-session-003-60997e04",
 "remote_authority": {"remote": "origin",
   "remote_ref": "refs/heads/persistence/c15-rcc-res-b-rerun-003-60997e04",
   "run_id": "c15-rcc-res-b-rerun-003-60997e04",
   "session_id": "c15-rcc-res-b-session-003-60997e04",
   "schema": "c15-remote-authority-v1"},
 "remote_authority_sha256": "e3c4fbfed3e9e15bdb4f20aa98ac52fa153e3513c44de46691e2a6a5723328da",
 "subject_id": "user_1"}
```

All four required fields present and exact. **Identity disambiguation (PM-ruled, not mechanically
error-flagged):** the four distinct identifiers below serve four different purposes and are **not**
competing released identities —

| identifier | purpose |
|---|---|
| `c15-rcc-res-b-session-003-60997e04` | persistence run *session* (release scope) |
| `sess-resident-b-003-8f7f1f11f568` | conversation session (canonical turn binding) |
| `resident-b-003-12da5a13261e4c0d` | resident session |
| `8887ab32-f693-44b7-ba25-5b32fc4dc864` | resident process |

**Illegal second released run/session identity search: NEGATIVE.** Scanning the whole authoritative
tree (`*.json`, `*.jsonl`) yields exactly one persistence run id (285 occurrences) and exactly one
persistence session id (74 occurrences); one resident session (50), one resident process (50), one
conversation session (202). RERUN-002 (`c15-rcc-res-b-rerun-002-65e6e826` /
`c15-rcc-res-b-session-002-65e6e826`) appears **zero** times anywhere in the run state.

---

## 3. Mechanical terminal re-confirmation (read-only, independently recomputed)

Boundary, from the frozen `release-state.json` (sha `90238135…`, identical in the sealed gen 48 tree):

```text
active_phase        = B
last_acked_sequence = 22
last_acked_event_id = c15rcc-022
next_sequence       = 23
pending_reveal      = null
```

- `world_revision = 66` (`world_meta`) == `index_watermark = 66`, `index_lag = 0`.
- **cursor 23 was never revealed.** The audit stream contains `cursor_revealed` for `[14,15,…,22]`
  exactly once each; `next_sequence = 23`; `pending_reveal = null`.
- Current-event terminally clear; no pending binding; no open relay; no unresolved wake; no running
  model work; no pending provider return; no unacked semantic work — see §3.2.

### 3.1 Deep chain — PM independent recompute (on a fresh `git archive` of the authoritative ref)

| W08 claim | PM fresh recompute | Verdict |
|---|---|---|
| generations `1..48` | 48 generation dirs, gens `[1..48]` | PASS |
| manifest self-check `48/48` | `manifest_sha256 == sha256(canonical_json(manifest["artifacts"]))` → **48/48** | PASS |
| archived artifacts `287/287` | **287/287** artifact blobs byte-verified, `0` mismatches | PASS |
| zero byte mismatch | 0 mismatches | PASS |
| final ledger records `129` | `129`, `seq` contiguous `1..129` | PASS |
| total model requests `43` | 43 request files, 43 distinct request bodies, 43 distinct in-body request ids | PASS |
| `request_published = 43` | 43 | PASS |
| `response_published = 43` | 43 | PASS |
| `response_consumed = 43` | 43 | PASS |
| 43 requests each exact 3-event completion | **43/43** exact `[request_published, response_published, response_consumed]` | PASS |
| attempts `= 43`, metered `= 43`, 1:1 meter match | 43 attempts, states `{metered: 43}`, 43 meter rows, **set equality both directions**, 43 distinct attempt ids, 43 distinct meter ids | PASS |
| cursors `14..22 = 9/9` base evidence sets | `9/9` six-kind base sets | PASS |
| `turn_result.json` exactly on USER cursors `15,17,19,22` | exactly `[15, 17, 19, 22]`; PLATFORM cursors carry none | PASS |

Additional PM recomputes (beyond the W08 claim set):

- **Ledger hash chain integrity:** `prev_sha256` linkage verified for all 129 records; recomputed
  `record_sha256` chain head = `1974b697…` = `freeze/exchange_final.json.chain.head_sha256`; `chain.ok = true`.
- **Byte-level ledger↔file agreement:** all 43 request files and all 43 response files re-hashed;
  `sha256(file) == request_sha256/response_sha256` in the ledger for every one; every
  `response_consumed.response_sha256 == response_published.response_sha256` (no substitution).
- **Freeze digests:** `sha256sum -c evidence/freeze/digests.sha256` → **10/10 OK**, zero drift
  (includes `private_world.sqlite f863051a…`, `world_index.sqlite 0581a4ee…`, `release_state.json 90238135…`).
- **Mailbox archive fidelity:** `evidence/freeze/mailbox/{ledger.jsonl,requests/*,responses/*}` is
  byte-identical to the live `exchange/` tree (0 request mismatches, 0 response mismatches; identical
  ledger sha `fa7895c5…`).
- **Attempt/meter identity hygiene:** 43 request bindings → 43 distinct attempts, 43 distinct
  `outbound_request_fingerprint`, 43 distinct `relay_id`. → no duplicate provider request identity.
- **Wake/review closure:** 7 distinct `wake_review_*` ids, each with `review.schedule` + `review.begin`
  + `review.complete`; **zero** wakes begun-but-not-completed. All 66 `operations` rows `status=committed`, zero errors.
- **Turn executions:** 11 rows, all `completed`, `retry_authorized=0`, `retry_count=0` for all 11.
- **Custody anomaly check:** exactly **one** of 43 attempts carries a non-null `reconciliation_evidence`
  (`bgattempt_1d6735f46f05508149948ea5a7de5b01`); zero attempts carry a non-null `failure_kind`.

### 3.2 Documented orderings PM independently confirmed (no hidden closure gap)

- `generation-head.manifest_file_sha256` `c6a84e04…` == `sha256(gen48/manifest.json)` → the
  generation-head genuinely sha-pins sealed gen 48.
- Committed freeze `MANIFEST.json` intentionally lacks `final_barrier` (the barrier seals the
  pre-barrier tree, so a generation cannot contain its own commit sha). Authoritative closure chain is
  instead: remote ref → commit `5692a329` (message binds `run_id` + `generation=48`) →
  `generation-head.json` (sha-pins the gen 48 manifest) → committed audit `final_freeze` +
  `generation_sealed`. **PM accepts this ordering and finds no gap in it.**
- Top-level live `world/*.sqlite` differ from the sealed gen 48 copies by **5 header bytes only**
  (offsets 26/27/43/94/95 = SQLite file change counter, schema cookie, version-valid-for), with all
  remaining bytes identical and all 14 table row counts identical. This is the same benign class as the
  W08 startup `world_header_drift_adjudication.json`. It is committed **at** `5692a329` and is therefore
  **not** a post-seal edit. The authoritative frozen artifacts are the digest-verified seal copies.

**PM note:** W08's claim "no post-seal edits to the run tree" is accurate; the header-only live/working-copy
delta is pre-existing, disclosed at startup, and digest-insulated. PM records it as a nuance, not a finding.

---

## 4. Fresh A → B continuity (independent, from PR #296 bytes)

PM re-extracted the A run artifacts from **PR #296 exact `317316299c332d82e0cbd0431b5c7d50f391bc17`**
and recomputed the four released Fresh A pins from the actual bytes:

| Pin | Released value | Recomputed from PR #296 bytes | Verdict |
|---|---|---|---|
| A world | `0d6970ed99367a456e4baa29092bde8f15bc7544496095cc87ad9f029e2603b2` | match | **EXACT** |
| A index | `79c877a4bf75091fa90ae81076a6bdb2e265cf6376b657c3f195e9e91f9844e5` | match | **EXACT** |
| A release-state | `6b90fc7a09bce7d575dbcb783dcbe838cab81c2e358515adbb5dca9731f57c37` | match | **EXACT** |
| A exchange ledger | `3b2b9e902133c31cc583491aae55834ee9cb71a9bea9ca50a36fd7e8b81da021` | match | **EXACT** |

A boundary content verified independently: `world_revision 38` (38 `world_commits`), index 38,
`last_acked 13 (c15rcc-013)`, `next 14`, `pending null`, receipts 13, **21/21 exchange COMPLETE**
(63 records, chain intact, 21 requests × exact 3 events), A attempts 21/21 metered.

**B gen 1 was truly formed from this Fresh A boundary — proven mechanically, not by prose:**

1. `generations/000001/exchange/ledger.jsonl` sha == `3b2b9e90…` == the A pin, **byte-identical**.
2. The final 129-record ledger is a strict **byte prefix-extension**: records 1..63 are byte-identical
   to the A ledger (63/63), and record 64 is the first B record (`request_published`
   `req-0022-model_directive-22a9c3fe`, `2026-09-29T19:37:19Z`).
3. `generations/000001/release-state.json` vs A: **1 differing byte, offset 21** — i.e. the single
   character `"A"`→`"B"` in `active_phase`. All 13 receipts are byte-identical in content.
4. `generations/000001/world/*.sqlite` vs A: **3 differing bytes each, all inside the SQLite header
   (offsets 27, 43, 95)**; every other byte identical. Same for the index.
5. B gen 1 logical content == A boundary: gen 1 world has `world_revision 38`, `world_commits 38`,
   21 attempts, 21 meter rows, 7 turn executions — identical to A.

**Old A #205 (98/98) lineage: NOT used.** No 98-request ledger exists in this run; the B ledger root
is the A-003/C-003 ledger hash. `HISTORICAL_FOR_PRIOR_RC_ONLY` is honored.

---

## 5. Cursor 14..22 chronology (mechanical, per cursor)

Structure verified per cursor: `REVEAL → K1 → INGEST → K2 → MODEL WORK → K3 trusted return →
continuation/K4 → K5 → DURABLE ACK → next cursor`, with the generation→commit map independently
rebuilt from `git log` on the persistence ref (single linear chain, 45 commits, zero merge commits,
first commit `6ef7a1cb…` root, gens 29–32 bundled in recovery commit `4f12ee0e`):

| cursor | K1 | K2 | K3/K4 | K5 | ACK | due rounds |
|---|---|---|---|---|---|---|
| 14 | gen2 `02473b0d` | gen3 `b162decf` | gen4 `72244e8e` | gen5 `4bb95af9` | gen6 `ec449c47` | 5 (`req-0022..0026`) |
| 15 | gen7 `12061e2a` | gen8 `827cf7de` | gen9 `0827d322` | gen10 `c7166122` | gen11 `05632870` | 0 |
| 16 | gen12 `69c1e9e9` | gen13 `dfd8bba8` | gen14 `c09ffd58` | gen15 `2560b711` | gen16 `4ca883d5` | 0 |
| 17 | gen17 `524da5a7` | gen18 `02d40fa6` | gen19 `ac7dbad0` | gen20 `537e91b3` | gen21 `006d116f` | 2 (`req-0035/36`) |
| 18 | gen22 `24b66dc8` | gen23 `2f33581a` | gen24 `84768a41` | gen25 `f9e635e1` | gen26 `64d83fc5` | 0 |
| 19 | gen27 `de7580b7` | gen28 `4533f92a` | gen29 * | gen30 * | gen31 * | 0 |
| 20 | gen32 * | gen33 `71c3285f` | gen35 `6784f7af` | gen36 `306a90df` | gen37 `79857c7b` | 4 (`req-0039..0042`) |
| 21 | gen38 `f518cc9c` | gen39 `e8d04a40` | gen40 `2efea1c7` | gen41 `bd6c6d2d` | gen42 `35f338d9` | 0 |
| 22 | gen43 `ce180081` | gen44 `eb72627e` | gen45 `ba687a75` | gen46 `b8fc3b96` | gen47 `09688ca3` | 0 |

\* gens 29–32 sealed locally during the auth outage, pushed together in `4f12ee0e` (parent `4533f92a`).
gen34 `a9a24943` = `OPERATOR_RECOVERY_RECONCILE_NOT_SUBMITTED_PM_AUTHORIZED_2026-09-30` (see §7).

**No duplicates and no skips, independently verified:**

- exactly one `cursor_revealed`, `cursor_ingested`, `post_turn_barrier`, `pre_ack_barrier`,
  `cursor_acked`, `binding_cleared` per cursor 14..22 — sequences `[14…22]` each, no repeats;
- no duplicate reveal; no duplicate ingest; no duplicate provider request identity (43 distinct
  fingerprints/relay ids); no duplicate semantic effect; no duplicate meter (set equality both ways);
  no duplicate assistant output (43 distinct response bodies); no duplicate ACK;
- no skipped cursor; 48 generations sealed with all 8 barrier label types present;
- `pending_reveal` lifecycle is monotone and consistent across the whole chain (set at K1, cleared at
  DURABLE ACK), ending at `pending = null`, `next = 23`.

---

## 6. Incident 1 — c19 GitHub auth outage: `RECOVERED_INFRASTRUCTURE_INCIDENT`

PM verdict, adjudicated **separately** from the cursor-20 incident: **not a blocker.**

Independently verified facts:

- The failure is real and loud: `gh auth status` "token in GH_TOKEN is no longer valid";
  `git ls-remote` "could not read Username". Gens 29–32 were sealed locally while unpushable.
- Remote authority was never downgraded: remote stayed at gen 28 `4533f92a…`; `.remote-head` agreed;
  no local-only promotion, no silent fallback.
- The recovery is a single CAS push: `4f12ee0e` with parent `4533f92a` (`--force-with-lease`),
  recorded in the audit as `recovery_push_after_auth_failure` with
  `cas_precondition_remote_head = 4533f92a70d9e65e44fcde68465d34253fe51485`.
- **No history rewrite:** `git diff --name-status 4533f92a 4f12ee0e` = 43 additions + 9 modifications
  + 1 rename, **zero deletions under `generations/0000{01..28}`** — all pre-incident generations
  byte-identical across the push. The one rename is the legitimate archival move
  `binding/current-event-binding.json` → `evidence/cursor_19.binding.json` (cursor-19 CLEAR_BINDING).
- Labels of the recovered generations are exactly `29=K3/K4`, `30=K5`, `31=DURABLE_ACK`, `32=K1_AFTER_REVEAL`.
- At the outage the run stopped at a genuine fail-closed point: c20 was **revealed** (gen 32,
  `pending_reveal = c15rcc-020`, receipts 19) but **not ingested**; no model rounds started for c20.
- No re-reveal (reveals occur once each), no second identity, no replay (prefix property of the ledger
  holds exactly: 63 A records untouched, then 66 strictly new records).

---

## 7. Incident 2 — cursor 20 `in_doubt`: PM ruling (the decisive adjudication)

This section is the core of the readiness gate. The factual chain is reproduced in full and was
independently reconstructed from primary artifacts (ledger, audit, attempt row, barrier commits,
crash logs), **not** from Window 08 prose.

### 7.1 Factual chain (independently confirmed)

1. cursor 20 due phase: round-0 review request `req-0039-model_directive-ed097a32` published —
   ledger `seq 115 request_published`, `2026-09-29T20:06:29.156116Z`, `response_sha256=null`.
   This record is the frozen exchange contract's **semantic dispatch boundary**.
2. The operator process died mid-await (inline blocking invocation exceeded the tool timeout;
   `ResponseTimeoutError` at 1800 s). Crash log preserved:
   `evidence/incident_2026-09-29_remote_auth_and_indoubt/due20_first_attempt_response_timeout.log`.
3. After process death the exchange side obtained the round-0 answer: ledger `seq 116
   response_published`, `2026-09-29T20:37:01.219554Z`, `response_sha256 = 21a31eb306938b1c777f431cff9183e86c1233298344aebb0dcced3a78dd22c2`.
   (≈30.5 min after publish — consistent with the 1800 s await.)
4. Restart: Core `admit()` found `bgattempt_1d6735f46f05508149948ea5a7de5b01` in `dispatching`, moved it
   to `in_doubt` with `failure_kind='restart_after_dispatch_boundary'`, and raised
   `BackgroundModelExecutionInDoubt` **before the model handler could run**. Traceback preserved:
   `due20_second_attempt_indoubt_crash.log` (`background_attempt.py:921`).
5. The run's anonymous-handler transport can never mint a trusted-return receipt: the exchange replies
   carry `authored_by=EXTERNAL_CURRENT_RESIDENT_SESSION` with `provenance=None`. **`background_model_response_receipts`
   has 0 rows for the entire run, for all 43 rounds** — so `stage_exact_response` was unreachable by
   construction, and the accepted `reconcile_response` (metadata path) is deliberately disabled.
6. `reconcile_not_submitted` was therefore the only mechanically available in_doubt exit.
7. The operator executed it under the user/PM directive "继续":
   audit record 211 `operator_reconcile_not_submitted`
   `{before_state: in_doubt, after_state: not_submitted, attempt_id: bgattempt_1d6735f46f05508149948ea5a7de5b01,
   directive: USER_ADJUDICATION_CONTINUE_2026-09-30, unconsumed_request: req-0039-model_directive-ed097a32}`
   at `2026-09-29T20:45:11Z`; sealed as generation 34 = `a9a24943…` with the immutable barrier label
   `OPERATOR_RECOVERY_RECONCILE_NOT_SUBMITTED_PM_AUTHORIZED_2026-09-30`.
8. The requirement that a durable dual record be kept was honored: the same attempt row carries a
   **mandatory non-blank** `reconciliation_evidence` string which states, verbatim, that the dispatch
   boundary was crossed exchange-side, that the response remains durable and unconsumed, that exact
   staging was unreachable, and that *"State set to not_submitted as the implementation's sole
   retry-enabling reconciliation despite the exchange-side dispatch fact recorded here."*
   Neither `req-0039` nor its response bytes were deleted, rewritten, or fabricated.
9. Resume: Core re-admitted → re-established the pre-dispatch binding → the handler resolved round 0 via
   the **`recovered_durable_response`** path (handoff record: `path="recovered_durable_response"`,
   `declared_request_sha256 == request_sha256 == 705f912f…`, `response_sha256 == 21a31eb3…`), and the
   ledger recorded `seq 117 response_consumed` at `20:45:20.168905Z` with the **identical** response sha.
10. **No provider re-dispatch for round 0.** The very next ledger record, `seq 118`, is
    `req-0040-model_directive-25b05eb7` whose body declares `"round_index": 1`; cursors 20's remaining
    handoffs (`req-0040/41/42`) are labelled `path="published_new_request"`. Total requests remain **43**
    (21 A + 22 B) — an illegal re-dispatch would have produced 44.
11. Metering stayed 1:1 and unique: 43 attempts / 43 meter rows / set-equality both directions;
    the reconciled attempt's row ends `state=metered`, `failure_kind=NULL`, and its
    `metering_records` row is `meter_record_id=meter_35bebeca…`, `execution_class=periodic_review`,
    `world_revision 61`.
12. Cursor 20 then completed normally (gen35 K3/K4, gen36 K5, gen37 ACK) and the run reached the
    terminal boundary of §3.

### 7.2 Sources consulted for this ruling (all fresh, read-only)

`src/aios_core/runtime/background_attempt.py` (states; `admit()` L855-923; `mark_dispatching` L926+;
`record_response` L1144+; `reconcile_not_submitted` L1257-1313; disabled `reconcile_response` L1315+;
`stage_exact_response` L1747+; `_STAGABLE_STATES` L1354; response_returned UPDATE L1948-1956),
`src/aios_core/runtime/turn_runtime.py` (L1290 `_mark_background_model_dispatch`, L1301-1326
`_authenticate_background_model_response` anonymous early-return, L3330 only `reconcile_not_submitted`
caller), `tests/runtime/test_background_model_attempt.py` (L51 reconcile→retry round-trip),
`tests/integration/test_core_background_response_recovery_001.py`
(`test_case_01_crash_after_dispatch_without_exact_response_stays_in_doubt`, L333),
`tests/c15_persistence/test_operator_wiring.py::test_no_second_semantic_engine_properties`,
`tools/c15_persistence/operator_session.py:20`, `tools/c15_persistence/relay.py:19`,
the frozen persistence tree, plus the W08 evidence set and the run's own `due_result`/handoff records.

### 7.3 Question A — is writing `not_submitted` after `request_published` a violation?

**Split ruling — partly yes, and PM states it plainly rather than softening it:**

- **Frozen persistence truthfulness — VIOLATED at the field level.** The exchange's own integrity
  surface computes, for `req-0039`, `semantic_dispatch_occurred = true` and
  `not_submitted_allowed = false`. The Core attempt's `state` field was nonetheless set to the exact
  value the run's own evidence declares not allowed. Taken in isolation, that enum is a false statement
  about dispatch history. Additionally, the accepted harness **promises the opposite behaviour in its own
  frozen documentation**: `operator_session.py:20` and `relay.py:19` both declare *"it never rewrites
  `in_doubt` into `not_submitted`"*, and `test_no_second_semantic_engine_properties` forbids the operator
  session from calling `reconcile_not_submitted(` at all. The rewrite was therefore performed **outside
  the accepted, IA-passed persistence harness**, by window-local driver code, on the basis of a user chat
  directive rather than a governance adjudication. PM does not describe this as routine, sanctioned
  operation; it was a deviation from the released contract surface.
- **Exactly-once recovery semantics — NOT violated in effect.** No re-dispatch. No second request for
  round 0. No duplicate semantic effect, capability effect, metering, assistant output or ACK. One
  request, one response, one consumption, with byte identity between publish and consume.
- **"Durable state must not record a false historical fact" — violated in the enum, satisfied in the
  record.** The `state` value is false alone; the record as a whole is truthful, because the identical
  durable row carries a mandatory, non-blank contradiction disclosure, and the deviation is additionally
  and immutably recorded in the audit stream, the generation-34 barrier label, and three evidence
  documents. Nothing was hidden, deleted, or rewritten; the exchange history the field contradicts is
  itself preserved byte-exact.
- **Resident B canonical evidence admissibility — NOT violated.** The deviation is confined to Core's
  internal retry bookkeeping for one attempt. It touches no Resident-authored content, no exchange bytes,
  no World object authored by the Resident, and no semantic record. The Resident's round-0 answer is the
  same single set of bytes it always was.

### 7.4 Question B — may it be left to Fresh Independent Acceptance as a disclosed non-blocking wart?

**YES.** PM re-verified, on the primary artifacts, each of the six conditions the question requires —
all six hold:

1. true dispatch history not deleted — `seq 115/116/117` present, chain intact, `req-0039` intact;
2. exchange ledger remains the authoritative evidence — it is, and it is precisely what exposes the crossing;
3. exact response bytes preserved — file sha `21a31eb3…` == published == consumed;
4. no re-dispatch — proven quantitatively (43 requests; `req-0040` is `round_index 1`);
5. no duplicate semantic effect — proven by uniqueness of attempts, bindings, relay ids, fingerprints,
   meter rows and response bodies;
6. recovery fully auditable — audit record 211, barrier label gen 34, DB `reconciliation_evidence`,
   operator log, incident analysis, final report, acceptance brief.

PM therefore rules the field inconsistency a **disclosed implementation/operator semantic wart**,
admissible for acceptance review, **not upgraded to known-good**, and binding on IA (§9).

### 7.5 Question C — does it make the whole run NON-CANONICAL?

**NO.** `C15-RCC-RES-B-RERUN-003` is **not** ruled non-canonical.

Repository/source/evidence reasons:

1. **Canonicality in this governance line means admissibility of evidence + identity integrity +
   semantic exactly-once.** All three are independently verified intact (§2–§5). The RERUN-002
   precedent for `NON-CANONICAL` was evidence *destruction* — an unrecoverable post-dispatch state.
   Here the evidence is not merely intact, it is richer than the contract requires.
2. **Nothing was fabricated or laundered.** The `state` value is the only false element, it is transient
   and superseded (the attempt ends `metered`), and the durable record contradicts itself *in favour of
   the truth*, in the same row, by construction of the API (`evidence` is a required non-blank argument).
3. **The end state is legal, not hacked.** `not_submitted → admitted → dispatching → response_returned →
   metered` is a first-class path of the accepted state machine; `mark_dispatching` documents the
   `not_submitted` retry explicitly (`background_attempt.py:986-988`). No private authority, no signing
   oracle, no HMAC key was used.
4. **The failure class is already PM-adjudicated and frozen.** `C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_003_CORE_DEPENDENCY_ADJUDICATION_2026-09-28.md`
   already ruled, in terms, that after the provider boundary with no trusted receipt *"current accepted
   Core has no legal continuation that both converges and preserves the authenticity invariant. That is a
   Core recovery surface gap."* The fix (CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001) repaired the
   **trusted** path only; the anonymous path was deliberately left fail-closed and is enshrined as such by
   `test_case_01`. Cursor 20 hit exactly this pre-adjudicated residual boundary — it is not a novel
   integrity failure invented in WINDOW 08.
5. **All terminal hashes/counts are correct *in addition to*, not instead of, the disclosure.** PM did not
   accept "43/43 COMPLETE" as proof of legality (§8 shows PM audited the intermediate provenance
   separately). The COMPLETE classification is genuinely earned: the 3-event completion exists because one
   request really was answered and really was consumed once — not because a fake terminal state was
   papered over an unresolved middle. The unresolved middle is recorded in the Core-side durable record,
   which is exactly where the ledger cannot see it.

**PM explicitly rejects the "all green, therefore fine" reasoning.** The pass above rests on the six
conditions of §7.4 and the five reasons of §7.5, each tied to primary artifacts — not on the terminal
green state.

---

## 8. §11-style historical wash check (independent of the final COMPLETE)

Checked explicitly that the final `43/43 COMPLETE` did not mechanically bleach an illegal intermediate
state. Per-request transition provenance for `req-0039`:

| element | evidence | verdict |
|---|---|---|
| original `request_published` | `seq 115`, 20:06:29Z, `response_sha256=null` | present, unmodified |
| `response_published` | `seq 116`, 20:37:01Z, sha `21a31eb3…` | present, unmodified |
| Core attempt state transitions | `admitted(rev 61)` → `mark_dispatching` (binding `41a79b9b…`, relay `5f58a12f…`) → `in_doubt` (`restart_after_dispatch_boundary`) → raise → `not_submitted` → `admitted` → `dispatching` → `response_returned` → `metered` | attested by crash logs + audit + row |
| reconciliation evidence | mandatory non-blank text on the attempt row | present, truthful, self-contradicting |
| subsequent consumption | `seq 117`, sha identical to `seq 116` | exact, no substitution |
| capability / semantic effects | round-0 read only (`read_periodic_review_anchors`); review completed via `req-0040/41/42`; `review.commit_operation_experience` recorded; no production mutation | consistent with a normal round |
| metering | `meter_35bebeca…`, 1:1, `execution_class=periodic_review` | present, unique |

No duplicate provider request identity, no duplicate semantic effect, no duplicate meter, no duplicate
output, no duplicate ACK. **The final COMPLETE is earned, and the deviation is recorded where the ledger
cannot hide it.**

---

## 9. Findings and mandatory Independent-Acceptance items

PM does **not** clear these; they are handed to WINDOW 10 as binding review scope.

**W09-F1 — disclosed contract deviation (binding disclosure, NON-BLOCKING for readiness).**
The `in_doubt → not_submitted` rewrite was executed outside the accepted, IA-passed persistence harness,
via a public Core API whose documented intended use is the opposite fact pattern
(`test_background_model_attempt.py` passes *"provider gateway confirms no request was accepted"*), on a
user chat directive rather than an invariant-level governance adjudication, and it overrode a fail-closed
invariant that the frozen test suite deliberately enshrines. IA must weigh this as a deviation, not as
sanctioned procedure.

**W09-F2 — MANDATORY IA item: Resident authorship of the `req-0039` round-0 bytes.**
The operator published those bytes *after* the process died, and the transport is anonymous
(`provenance=None`) by design. The evidence labels the path `recovered_durable_response` and preserves
the bytes, but does not independently prove external-Resident authorship. IA must attack this explicitly
under the requirement that no operator may decide for the Resident. PM readiness is not a verdict on it.

**W09-F3 — MANDATORY IA item: `not_submitted_allowed=false`.**
The run's own exchange integrity surface asserts `semantic_dispatch_occurred=true` and
`not_submitted_allowed=false` for `req-0039`. IA must rule on whether the six-surface disclosure is
sufficient for acceptance, or whether it constitutes an acceptance blocker. PM does not pre-empt that.

**W09-F4 — residual Core gap (follow-up, not a W09 blocker).**
The anonymous-handler recovery surface gap remains unfixed in accepted Core. If W10 accepts, PM
recommends scoping a follow-up Core corrective (a sanctioned recovery surface for the anonymous/relay
path, or removal of the retry-enabling exit for post-dispatch attempts) so that no future window faces
an unfixable deadlock — and records that **no future window may use this reconcile shortcut without an
explicit PM adjudication.**

**W09-N1 — non-findings recorded so they are not re-litigated as anomalies.**
`PG_ACCEPTANCE_BRIEF` §1 states PR #302 carries "2 commits" while the head is 5 — an accurate statement
about the brief's own mid-flight authoring point, not an integrity issue. The brief's "unconsumed
`req-0039` artifacts untouched" and the later `recovered_durable_response` consumption are consistent:
"untouched" means not rewritten/deleted by the reconciliation; the consumption happened afterwards,
through the implementation's own recovery path. Neither affects admissibility.

---

## 10. Provider / model trusted identity

`trusted_model_identity = UNKNOWN`, `response_mode = EXTERNAL_CURRENT_RESIDENT_SESSION`
(`evidence/freeze/provider_identity.json`). This is the status RELEASE-003 explicitly allowed as a
**non-blocker**. PM does **not** upgrade it to known / trusted / attested, and does **not** reject B
because of it. Model replacement / `C15-RCC-MODEL-ATTEST-001` / R6 remain downstream and BLOCKED.

---

## 11. PR #302 status (unchanged, protected)

PR #302 remains **OPEN / EVIDENCE_ONLY / UNMERGED**, `DO_NOT_MERGE AS IMPLEMENTATION`, head
`846b55e63abe7f4d7c25adde013978cce6084556`, tree `634ed0bf…`, 5 evidence-only commits. PM did not merge
it, modify it, or write to its branch. No review branch was merged. No authoritative persistence ref,
generation 1..48, exchange ledger, or run artifact was modified, replayed, re-reconciled, or re-run.
Cursor 23 was not revealed. This window performed **read-only** inspection only, and executed no
Independent Acceptance, no evaluator, no Resident C, and no C15 close.

---

## 12. Downstream effect

```text
C15-RCC-RES-B-RERUN-003   = RUN_COMPLETE / REVIEW_READY      (WINDOW 08 → closed as accepted-for-review)
C15-RCC-RES-B-ACCEPT-003  = READY                            (unique next READY, WINDOW 10)
RESIDENT_C                = BLOCKED
EVALUATOR (C15)           = BLOCKED
C15_CLOSE                 = BLOCKED
C15-RCC-MODEL-ATTEST-001  = BLOCKED
```

Binding prompt for WINDOW 10 must carry §9 W09-F1..F4 as mandatory attack items.

WINDOW 09 is governance-only: task board + checkpoint + this receipt. No `src/**`, no `tools/**`,
no `tests/**`, no fixture, no evaluator, no release-state, no persistence ref, no PR #302 change.

---

## Final

```text
WINDOW_09 = COMPLETE / CLOSED after governance PR merge.

NEXT_WINDOW = 10
NEXT_TASK   = C15-RCC-RES-B-ACCEPT-003

DO NOT START WINDOW_10 HERE.
```
