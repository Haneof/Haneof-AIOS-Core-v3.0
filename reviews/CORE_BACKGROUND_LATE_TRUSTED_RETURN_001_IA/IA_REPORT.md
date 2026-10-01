# IA_REPORT.md — CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-INDEPENDENT-ACCEPTANCE

**WINDOW:** 14
**ROLE:** Fresh Independent Core Runtime Acceptance Reviewer (not author, not Window 13
engineer, not PM, not corrective engineer, not C15 operator, not Resident, not release
operator, not evaluator)
**MERGE_POLICY:** DO_NOT_MERGE
**VERDICT (see §14):** `ACCEPTANCE_FAIL / blocker=4` · `CORRECTIVE_REQUIRED`

---

## 1. Fresh identity (all values re-derived this session, not copied from author text)

| field | value | how verified |
|---|---|---|
| live `main` | `25591825d88e98f30dfd3de1c7e7cbc6e53267dd` | `git fetch origin main`; `origin/main` |
| PR #305 | `OPEN`, `merged=false`, `mergedAt=null`, title carries `DO NOT MERGE` | `gh api repos/.../pulls/305` |
| PR head ref | `arena/01a0f07b-haneof-aios-core-v3-0` | fresh API |
| PR head SHA | `5ad0524c425592210ff184e00ad52abb2c14e366` | `git rev-parse origin/pr/305` == API `head.sha` |
| candidate parent | `a49c1e6874ecb92ae4dc4783d07d733fdc19fa5d` | `git rev-parse 5ad0524^` |
| candidate tree | `53064b3022254dab33c7793a0a6306c71e3df2b2` | `git rev-parse 5ad0524^{tree}` |
| construction base | `25591825d88e98f30dfd3de1c7e7cbc6e53267dd` | PR base SHA; base is ancestor of head |
| head drift | **none** — head exact == required candidate | no `ACCEPTANCE_BLOCKED_BY_CANDIDATE_DRIFT` |

Fresh read of the required governance comments:

* Window 12 adjudication / PM HOLD `5905176583` (2026-09-30T06:05:27Z) —
  `REVIEW_BLOCKED / CI_VALIDATION_GAP`, release criteria enumerated.
* Window 13 closing comment `5905895496` (2026-09-30T06:58:06Z) —
  `CI_VALIDATION_GAP_CLOSED / READY_FOR_PM_RECHECK`.
* PM release comment `5909943516` (2026-09-30T11:08:05Z) —
  `REVIEW_READY / READY_FOR_FRESH_INDEPENDENT_ACCEPTANCE / DO_NOT_MERGE`, authorizes
  only Fresh IA of exact SHA `5ad0524…`.

### Formal author CI identity (fresh GitHub query; author evidence only)

| field | value |
|---|---|
| workflow | `core-background-late-trusted-return-001` |
| run | `36680355119` (head_sha **exactly** `5ad0524c4255…`, event `pull_request`, attempt 1) |
| job/check | `109774221264` `formal-core-gate` — `success` |
| exact env (check-run annotations API, re-queried) | Python `3.12.14` / Pydantic `2.13.5` / pytest `8.4.2` / SQLite `3.45.1` / OpenSSL `3.0.13 30 Jan 2024` |
| JUnit notices | full `tests=1059 failures=0 errors=0 skipped=0`; accepted `249/0/0/0`; surface `1/0/0/0`; late `61/0/0/0` |
| exact-head workflow runs | **17/17** `success` on `5ad0524…` (36680355048/05058/05063/05066/05070/05074/05083/05093/05112/05119/05126/05131/05148/05149/05164/05182/05189) |

These are **author evidence** and were not transferred to the IA verdict. Every attack
below was executed independently (raw outputs under
`reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_IA/raw*/`).

**Reviewer environment (disclosure):** CPython **3.11.2** / Pydantic **2.13.5** /
pytest **8.4.2** / SQLite **3.40.1** / OpenSSL **3.0.20** in the reviewer sandbox.
Pydantic/pytest pin exact-matches the formal gate; CPython/SQLite/OpenSSL do not and
are disclosed as a deviation. The formal 3.12.14 gate identity above was re-verified
directly from GitHub, not from repo markdown.

---

## 2. Baseline falsification (RED independent reproduction)

Author claim: baseline `25591825…` with frozen probes = **56 failed / 5 passed**.

IA reproduction (exact worktree `git worktree add --detach /tmp/w14_baseline_wt
25591825d88e98f30dfd3de1c7e7cbc6e53267dd`; only the four probe files copied in;
`src/**` byte-identical to baseline — verified `git status`):

```
56 failed, 5 passed in 3.50s
```

Failure classification re-derived from raw output (not from author manifest):

| mechanism | IA count | classification |
|---|---|---|
| `FusedTurnRuntime.__init__() got an unexpected keyword argument 'external_return_observer'` | 42 | `ABSENT_CAPABILITY` product RED |
| `Failed: DID NOT RAISE BackgroundModelResponseConflict` | 7 | **genuine product RED** — false `not_submitted` writable on baseline `main` via `reconcile_not_submitted` (this is the frozen Class-B defect) |
| `has no attribute 'attach_late_trusted_return'` | 2 | `ABSENT_CAPABILITY` |
| `has no attribute 'late_trusted_return_state'` | 1 | `ABSENT_CAPABILITY` |
| `No module named 'aios_core.runtime.late_return'` | 1 | `ABSENT_CAPABILITY` |
| `child exit=1` (SIGKILL probe) | 1 | `ABSENT_CAPABILITY` (capability-issuing dispatch path does not exist) |

**Probe integrity:** the four frozen probe SHA-256 values recomputed at the candidate
tree are byte-identical to `baseline_probe_hashes.txt` (RED sources == GREEN sources,
so no expected-outcome tuning between RED and GREEN):
`159e557a…` fixture, `7482c69a…` main, `94bb807f…` not-submitted, `ac0a576c…` adversarial.
See `raw/frozen_probe_hashes_verified.txt`.

Baseline RED **reproduced**; the 7 `DID NOT RAISE` probes are genuine product RED
(false `not_submitted`), the remaining 49 are absent-capability gaps that the candidate
is supposed to close. No harness-bug contamination found in the frozen counts.

---

## 3. Trust-root review

### 3.1 Signing oracle — **BROKEN** → `BLK-W14-001`

Attack (frozen `IA14-ORACLE-001`, per §10 exactly: process death → `in_doubt` → fresh
process with ordinary recovery objects → reach issuance through the normal object
graph):

```
FAIL | IA14-ORACLE-001
  expected: fresh ordinary recovery cannot reissue/retrieve capability or attach arbitrary bytes
  actual:   CAPABILITY REISSUED and arbitrary bytes staged for bgattempt_dedeb5127fd3921062ff3123e5da9c0b
```

Mechanism (source + repro):

* `FusedTurnRuntime.__init__` stores `self.background_model_attempts =
  BackgroundModelAttemptStore(store)` — a **public attribute** holding the store.
* `_issue_external_return_capability` (`background_attempt.py:1570`) is Python
  private-by-convention only. §9 explicitly forbids treating an underscore as proof;
  a recovery process holding ordinary Core objects calls it as
  `store._issue_external_return_capability(attempt_id, issued_at=now)`.
* It accepts `state ∈ {dispatching, in_doubt}` (`:1620`) — i.e. it works **after
  process death** — and when a capability row already exists it returns the persisted
  capability **including the nonce** (`:1645-1655`, `_capability_from_row :1688`).
* `BackgroundModelReturnCapability.prove_external_return` then mints a valid proof for
  arbitrary bytes; `attach_late_trusted_return` accepts it and mints the Core-owned
  receipt + handoff.

This is precisely the post-hoc signing oracle §10 predicted. The author's own
`test_a1_recovery_caller_cannot_self_issue_a_capability` only asserts that the name
`issue_external_return_capability` (no underscore) raises `AttributeError`, and
`test_a1_capability_issuer_is_not_publicly_callable` only asserts naming — neither
tests reachability of the underscore method. The private-issuer analogy to
`_capture_trusted_response_return` is exactly the "Python underscore as proof" that
§9 rejects. **Blocker.**

### 3.2 Nonce leakage — **BROKEN** → `BLK-W14-002`

Attack (frozen `IA14-NONCE-001`, per §11):

```
FAIL | IA14-NONCE-001
  expected: ordinary recovery object cannot read capability nonce or turn it into trusted bytes
  actual:   public db_path exposed nonce and arbitrary bytes staged for bgattempt_bd420d5b472eeb881bb0c2f10220e1be
```

Mechanism: the nonce is persisted as **plaintext hex** in
`background_model_return_capabilities.capability_nonce` (`:647`, insert `:1660`) in the
same runtime database file whose path is the **public attribute**
`SQLiteWorldStore.db_path` (`sqlite_store.py:183`). Read-only SQLite access (the
normal backup/export/inspection surface named in §11) yields the nonce; the module
function `late_return_proof` is **public and exported** (`late_return.py:62-68`) and
completes the oracle. Route: public `db_path` → nonce → public `late_return_proof()` →
public `attach_late_trusted_return()` → Core mints trusted receipt/handoff.

This is materially worse than the accepted pre-existing authority key
(`background_model_authenticity_authority.secret_hex`, also plaintext in the same DB):
weaponizing that key requires `_capture_trusted_response_return` or raw SQL writes,
whereas the nonce path creates trusted state through **public APIs only** from
read-only DB access. Ordinary inspection surfaces were checked and are clean
(`RuntimeSnapshot` fields, `model_dump`, `repr`, `scope_fields`, `late_trusted_return_state`
all exclude the nonce — verified `raw/ns001_confirmation_variant.txt` adjacent checks
and §3.4), so the leak vectors are the DB file plus the reachable issuer of
BLK-W14-001. **Blocker.**

### 3.3 Issuer reachability / in_doubt reissue (§9, §10)

Covered by BLK-W14-001. All call sites enumerated: the only production caller of
`_issue_external_return_capability` is `turn_runtime.py:1318` (`_mark_background_model_dispatch`);
no public/exported wrapper returns the nonce; recovery-facing objects (`RuntimeSnapshot`,
`TurnExecutionInspection`, `BackgroundModelAttempt`, `BackgroundModelRequestBinding`,
`response_authenticity_receipt`, `outbound_request_binding`, `late_trusted_return_state`)
carry no nonce. The exposure is (a) the underscore method on the public store object and
(b) the plaintext DB row. Reflection/introspection was not needed — plain attribute
access suffices.

### 3.4 Nonce leak surfaces audited (§11 checklist)

| surface | nonce present? |
|---|---|
| `RuntimeSnapshot` / model input / cockpit / capability catalog | no |
| `repr` / `model_dump` / JSON serialization of `BackgroundModelReturnCapability` | no (PrivateAttr) |
| `scope_fields()` | no |
| metering / trace / exception text / evidence strings | no |
| `late_trusted_return_state` / public inspection APIs | no (issued/consumed only) |
| `SQLiteWorldStore.db_path` + SQLite file / backup/export | **YES** → BLK-W14-002 |
| issuer method on ordinary object graph | **YES** → BLK-W14-001 |

### 3.5 Observer trust model (§13)

The capability is handed to `ExternalReturnObserver.accept_return_capability` **before**
the model/provider handler runs (`turn_runtime.py:1313-1322`), and response identity
inside the proof (`provider/model/provider_request_id`) is chosen by the observer's
directive, not by Core. Therefore a misbehaving observer **can** `prove_external_return`
with no real provider return, including in crash windows T4/T5 (capability already
outside Core, submission not yet made). Core cannot mechanically distinguish observer
misuse.

Judgment: this is an **explicit, opt-in trust root** — registration is the embedder's
assertion that the handler reaches a genuine external responder (`late_return.py:244-273`,
`turn_runtime.py:256-263`), the same handler trust the accepted in-process return path
already requires (a handler can equally fabricate in-process bytes), and §26's anonymous
default (no observer ⇒ no capability row ⇒ permanently unattachable) was re-verified
green (`test_ltr_r0/r7/r8`, `test_a4`, all in the fresh 61/61). The window's own charter
(§11: "normal external trusted observer of course must hold the capability") accepts
the root in kind. However: the pre-submission handoff widens the accepted root in
**timing** (fabrication possible for a never-submitted request, after death), and the
only acceptance record for this widening is the candidate's own documentation
(§: "comments are not proof"). Recorded as **disclosure T-ROOT-001** (not a blocker):
the contract states "prove only real returns" and is enforced only by trust. If the PM
wants the root narrower, capability handoff could move to the provider-adapter's
submission-ack edge; that is a design decision, not a regression of an accepted
mechanical invariant.

---

## 4. Lifecycle — crash matrix T1–T12 (§12), races (§14), stale capability (§21)

Dispositions derived from source (`background_attempt.py`, `turn_runtime.py`,
`cognitive_runtime.py:344-370`) plus probes; "late attach" = `attach_late_trusted_return`:

| # | boundary | durable state | disposition | verdict |
|---|---|---|---|---|
| T1 | before `mark_dispatching` | `admitted`, no binding | legal retry (typed route or pre-dispatch reconcile) | safe |
| T2 | after binding txn commit | `dispatching` + binding | restart `admit()` → `in_doubt`; no blind redispatch | fail-closed |
| T3 | after capability DB row commit | + capability row | late attach possible; reconcile refused | fail-closed / late attach |
| T4 | before `accept_return_capability` | capability row orphaned, observer empty | late return **unattachable even for real returns** (no delivery path after death); with BLK-001 an attacker can reissue | fail-closed for honest path (T-ROOT-001 / BLK-001 for hostile) |
| T5 | after observer receives, before handler | capability live outside Core | late attach possible; fabricated return indistinguishable (T-ROOT-001) | accepted-root disclosure |
| T6 | after real submission | `dispatching` + binding | restart → `in_doubt`; late attach or fail-closed | fail-closed / late attach |
| T7 | after external response + proof created | same | attach exact once | exactly-once (verified) |
| T8 | proof durable externally, before Core attach | same | attach later, idempotent | exactly-once (verified) |
| T9 | inside attach txn | BEGIN IMMEDIATE; consumed guard `rowcount==1` (`:1898-1906`) | atomic receipt+handoff+consume | no partial state (verified by race) |
| T10 | after receipt/handoff, before staging | receipt+handoff durable | `_promote_staged_exact_response` → `stage_exact_response` resumes | exactly-once |
| T11 | after exact stage, before semantic application | staged row | `recover_trusted_handoff` continues, no provider call | exactly-once |
| T12 | after semantic/capability effect, before ACK | metered + output | terminal-receipt short-circuit (`turn_runtime.py:3478-3489`) / `TurnAlreadyCompleted` | no re-invoke (verified in SIGKILL probe) |

**Races / multi-proof (§14, frozen `IA14-RACE-001`):** concurrent proof-A/proof-B over
one capability → exactly one canonical staged response, the loser `refused`, no
deadlock. Exact replay of a consumed capability is deterministic and re-attaches the
same bytes; conflicting bytes after consumption fail closed (author R5/R6 + IA race).
`consumed_at` is set with a compare-and-set (`WHERE consumed_at IS NULL`, rowcount
guard) in the same transaction as receipt+handoff. **PASS.**

**Stale capability across legal not-submitted retry (§21) — BROKEN** → `BLK-W14-004`
(frozen `S3`, `raw_s3_stale_capability_rotation.txt`):

```
S3a stale proof rejected: True                       (good — stale capability cannot sign the rotated binding)
S3b retried return outcome: REFUSED: ... the issued late trusted return capability is
    not scoped to this attempt's durable originating request
rotated-capability outcome: REFUSED: (same)          (the "current" capability is also stale-scoped)
cap2 scope fp: req-1   cap2 is cap1 nonce: True      (row never re-scoped, nonce never rotated)
```

`mark_dispatching` explicitly replaces the binding on a `not_submitted` retry
(`:1043-1047`, "A not_submitted retry dispatches a new outbound request"), but
`_issue_external_return_capability` returns the **existing** row without re-scoping
(`:1645-1655`, "Re-issuing never rotates the nonce"). After a retry whose outbound
request is not byte-identical (normal: cockpit/context drift changes
`_outbound_request_fingerprint`), the capability row permanently disagrees with the
durable binding and **no proof can ever attach** for the retried dispatch — the exact
late-return capability this window exists to provide is silently dead for that attempt.
In the identical-fingerprint case (IA `S1-STALE-CAPABILITY-001`, PASS) the retry works
and first-writer-wins holds; the defect appears exactly when the design's own
"retry dispatches a new outbound request" branch runs. §21 demands an explicit contract
for nonce/binding/capability across this retry; none exists. **Blocker** (recovery
availability; fail-closed but permanently unattachable).

---

## 5. Provider identity (§15)

`provider_identity(directive)` = usage-non-null-over-provenance
(`background_attempt.py:398-419`). The apparent ambiguity is mechanically closed at
`ModelDirective.__post_init__` (`cognitive_runtime.py:94-104`): **any** non-null
usage field that differs from provenance raises at construction. Frozen
`IA14-ID-001` confirms ID-A (`usage.provider != provenance.provider`) is refused at
construction (`ValueError: usage provider conflicts with model-call provenance`).
ID-B/ID-C use the same rule; ID-D (partial sources) and ID-E (one side anonymous)
canonicalize through a single mechanical rule (non-null usage fills/overrides; any
conflict is a construction error; late attach additionally **requires** full identity
and refuses anonymous returns). `ModelUsage` rejects blank identity strings
(`ValueError: provider must be non-blank when provided` — verified). No silent
canonicalization, no exploitable ambiguity. **PASS.**

---

## 6. `not_submitted` write-site audit (§18) and pre/post-dispatch matrix (§19)

Complete write-site matrix for `state='not_submitted'` in `src/aios_core/**`
(grep + source audit; no other writers, no direct-SQL helper, no migration rewrite):

| write site | gate | post-dispatch + binding present | verdict |
|---|---|---|---|
| `reconcile_not_submitted` (`:1310`) | binding-absent + state ∈ {admitted} + no receipt | mechanically refused (`BackgroundModelResponseConflict`) | **fixed** (frozen NS-R2/R3/R5 green) |
| `reconcile_turn_model_not_submitted` (`turn_runtime.py:3375`) | delegates to above | refused | fixed (NS-R5-runtime green) |
| `mark_failure(definitely_not_submitted=True)` (`:1135-1195`) | **only** receipt-absence; no binding check; no typed-signal check; caller boolean | **WRITES `not_submitted`** | **BROKEN** → `BLK-W14-003` |
| `admit()` `not_submitted→admitted` reset (`:925`) | n/a (not a `not_submitted` writer) | n/a | ok |
| `adopt_legacy_in_doubt` (`:1082`) | writes `in_doubt` only | n/a | ok |
| schema rebuild migration (`:483-533`) | copies rows byte-for-byte | n/a | ok (S2 verified) |

**BLK-W14-003** (frozen `IA14-NS-001` + confirmation variant,
`raw_candidate_independent_probes_final.txt`, `raw/ns001_confirmation_variant.txt`):

```
IA14-NS-001: state dispatching + durable binding present +
  attempts.mark_failure(attempt_id, definitely_not_submitted=True,
                        error=ModelDispatchNotSubmitted(...))
  → durable row state='not_submitted'        (expected: mechanically refused)
confirmation variant: same call with error=RuntimeError("ordinary post-dispatch
  exception, NOT typed") → ALSO writes state='not_submitted', failure_kind='RuntimeError'
```

The design retains the typed `ModelDispatchNotSubmitted` contract as the legal
pre-submission route (accepted FIX-002/CG003; `cognitive_runtime.py:356-358` correctly
maps only that type to `True` and every ordinary post-dispatch exception to
`False → in_doubt`, which is right). But the durable write site itself enforces
neither: it is a **public** method (exported store class; `runtime.background_model_attempts`
is public) that trusts a caller-supplied boolean and any error object. §19 NS-A
(state dispatching + binding present) and NS-G (caller-asserted non-submission) must
fail closed; through this site they do not. Consequences: a recovery caller can write
the false state, `admit()` resets it to `admitted`, `mark_dispatching` issues a **new**
request identity — blind redispatch with a second request identity while the first may
still complete, the exact §12 forbidden outcome. The candidate's own commit-message
claim ("the post-dispatch / in_doubt → not_submitted transition is now impossible") is
true only for `reconcile_*`, not for `mark_failure`. **Blocker.**

Pre-dispatch legitimate paths re-verified not regressed: NS-R1 (pre-dispatch reconcile
+ retry), NS-R1-typed (`ModelDispatchNotSubmitted` → `not_submitted` → authorize →
retry, retry identity preserved, `test_cg003_*` green in fresh 249/249), NS-R7
receipt-absence guard, NS-R7-metadata (metadata-only reconciliation permanently
disabled).

---

## 7. Proof transplant / replay matrix (§16), duplicate JSON (§17)

Transplant across attempt / subject / work kind / work id / round / fingerprint /
relay / provider / model / request id / changed payload / changed usage / changed
provenance: all fail closed (author R2/R4/R5 + A2/A3 families, re-executed fresh in
the 61/61; IA race + conflict probes corroborate). The MAC message binds all seven
scope fields from the **durable binding** (never caller metadata) plus five response
fields; `hmac.compare_digest` throughout.

Duplicate/ambiguous JSON: `_strict_json_object` (`background_attempt.py:105-122`)
rejects duplicate keys at every nesting level before construction (frozen
`IA14-JSON-001`: duplicate nested `usage.provider` → `ValueError`); unexpected fields
rejected via exact key sets; bool-as-int rejected (`isinstance(value, bool)` guards);
null/blank identities rejected; different JSON spelling of the same semantics changes
`payload_sha256` so the proof is exact-bytes-bound and cannot be replayed across
spellings. **PASS.**

---

## 8. Recovery / R1–R5 (§5, §24, §25)

Real process-loss probe (frozen `IA14-SIGKILL-001`, reviewer-owned, true `SIGKILL`):
child process A runs `FusedTurnRuntime`, sends the observer-held capability over a
pipe, calls `os.kill(SIGKILL)` at the provider boundary (exit `-9` verified); surviving
observer mints the proof after death; process B fresh-opens Core and attaches. Result:

```
response='reviewer SIGKILL response'; terminal=TurnAlreadyCompleted (short-circuit);
provider_calls=[]; meters=1; state=completed; assistant_ref=committed; attempts=['metered']
```

One meter, one durable output, one terminal completion, no provider redispatch, same
attempt identity. Strong-terminal-receipt short-circuit (§24) confirmed: second
`run_turn` refuses (`TurnAlreadyCompleted`) without model/capability/semantic/output
re-execution. R1–R5 exactly-once families green in fresh 249/249 accepted regression.
Anonymous handler (§26): no capability row, no late-proof path, no invented identity,
`in_doubt` fail-closed (fresh 61/61 includes R0/R7/R8/A4). **PASS** — this is the one
core promise of the window that is genuinely delivered end-to-end.

---

## 9. CI validation gap (§3) — independently re-verified

* **12/12 behaviour comparisons**: the split gate asserts all twelve named comparisons
  are present and `True` (`RESIDENT_BEHAVIOURAL_COMPARISONS`, `test_resident_surface.py:54-69`);
  executed independently on a full-history checkout → `1 passed`
  (`raw/resident_surface_full_history_PASS.txt`).
* **Two frozen Resident review trees clean**: gate re-derives both tree diffs against
  the resolved base independent of the checker report and requires empty; passed.
* **Historical Persistence C003 construction** (`016a2f7d…` → `19476641…`): IA
  independent compare = `56 files changed, 12433 insertions(+)`, `-- src/aios_core` =
  **0 files** — matches PM exactly.
* **Shallow must SKIP, not PASS**: IA shallow clone (`git clone --depth 1`) →
  `1 skipped` with the explicit "Skipped, NOT passed" message
  (`raw/resident_surface_shallow_SKIP.txt`). No false green.
* **Formal gate is full-history**: workflow uses `fetch-depth: 0` and a hard
  shallow-detection step ("shallow repository: false" gate); fresh job listing shows
  `Verify required refs resolve` and `Resident-visible behavioural and historical
  scope gate` steps both executed and green on the exact head.
* **Preserved RED**: `historical_scope_tripwire_red.md` retains the `1058 passed /
  1 failed` `HISTORICAL_SCOPE_TRIPWIRE_RED` record; not relabelled green.
* **C15 scope**: `git diff 25591825…5ad0524…` touches no `tools/c15_preflight/**`,
  no `tools/c15_persistence/**`, no C15/Resident evidence, no PR #302 artifacts, no
  persistence refs (verified name-status; `raw` manifest). Window 13 did not touch
  BLK-001 governance.

**Evidence-consistency issue `EVIDENCE-CONSISTENCY-001` (recorded per §4; not counted
as product blocker):** candidate commit `5ad0524`'s message states "the formal gate was
re-run end to end on the exact final head … Final head formal gate: run `36679598965`".
Fresh query: run `36679598965` has `head_sha = a49c1e6874ec…` — the **parent**, not
the candidate. The true exact-head run is `36680355119` (verified above), which is
what Window 13's closing comment and the PM release cite. This is exactly the
self-reference artifact §4 anticipated (the final commit cannot contain its own
future run id); it must not be treated as a blocker merely for referencing an earlier
run id, but the commit message **does wrongly claim** that run tested the current
SHA and should be corrected in the corrective round.

---

## 10. Schema upgrade / restart (§23)

Frozen `S2-SCHEMA-001`: a pre-candidate Core DB (built with baseline code: world commit
+ dispatched attempt + restart `in_doubt`) opened by the candidate runtime:

```
baseline_state=in_doubt  state_now=in_doubt  rev=1->1  cap_rows=0  attempt_preserved=True
```

Old attempts preserved, historical `in_doubt` **not** rewritten to `not_submitted`,
World revision unchanged, and **no capability minted** for historical attempts
(RERUN-003-class historical rows gain no late-return authority). **PASS.**

---

## 11. Regression matrix (§30) — all fresh IA executions

| suite | result |
|---|---|
| IA independent probes (frozen, revision-logged) | 7 probes: 4 FAIL (BLK-001/002/003 + see raw), 3 PASS |
| IA supplementary probes S1/S2 | PASS (S1 identical-binding retry branch) |
| IA S3 stale-capability rotation | FAIL → BLK-W14-004 |
| candidate late + not_submitted + adversarial | **61 passed** |
| accepted trusted-return regression (16 files) | **249 passed** |
| full Core regression, full-history checkout | **1059 passed** (0 fail/err/skip) |
| Resident split gate, full history | **1 passed** |
| Resident split gate, shallow clone | **1 skipped** (SKIP ≠ PASS) |
| baseline RED reproduction | **56 failed / 5 passed** (as claimed) |

---

## 12. Scope audit (§31)

Candidate diff = `src/aios_core/runtime/{__init__,background_attempt,late_return,turn_runtime}.py`
+ the four new test/fixture files + two accepted runtime tests + `tests/c15_persistence/test_resident_surface.py`
+ the formal workflow + `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001/**` evidence.
Forbidden content absent: no `tools/c15_preflight/**`, no `tools/c15_persistence/**`,
no RERUN-003 evidence mutation, no PR #302 evidence mutation, no persistence ref
mutation, no Resident data, no cursor reveal, no governance adjudication rewrite.
Window 13 did not solve BLK-001. **PASS.**

---

## 13. Full public-surface enumeration (§27)

| surface | who may call | authority granted | carries secret | replay semantics | verdict |
|---|---|---|---|---|---|
| `BackgroundModelReturnCapability` (exported) | observer (holder) | mint one proof per (attempt, round, request) | nonce in `PrivateAttr` (not serialized) | single-use via `consumed_at` | ok in itself |
| `ExternalReturnObserver` (exported Protocol) | embedder registration | becomes proof authority at dispatch | receives capability | n/a | trust root (T-ROOT-001) |
| `attach_late_background_return` / `attach_late_trusted_return` | recovery caller | create trusted receipt+handoff from proof | no | deterministic replay of same bytes; conflicting fail-closed | ok |
| `late_trusted_return_state` | anyone | issued/consumed read | no | n/a | ok |
| `late_return_proof` / `late_return_message` (public fns) | anyone with nonce | mint/verify proofs | takes nonce | pure function | amplifies BLK-W14-002 |
| `new_capability_nonce` | anyone | RNG | no | n/a | ok |
| `_issue_external_return_capability` | **reached by recovery object graph** | **(re)issue capability + nonce** | **yes** | returns existing row | **BLK-W14-001** |

`runtime/__init__.py` exports add only `BackgroundModelReturnCapability` and
`ExternalReturnObserver`; no other sensitive authority was widened.

---

## 14. Review publication (§32, §33)

* review branch: session-pinned `arena/01a0f231-haneof-aios-core-v3-0` (platform-fixed
  Arena branch, permitted unpublished session branch per §32; review commit parent is
  the exact candidate `5ad0524…`; the candidate branch `arena/01a0f07b-…` was **not**
  written). Branch is review-only `DO_NOT_MERGE`.
* review SHA / parent / tree / PR comment ID: recorded in
  `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_IA/PUBLICATION.md` after push.

---

## 15. Blockers (each: stable ID · invariant · location · minimal repro · expected · actual · impact)

**BLK-W14-001 — post-hoc signing oracle via reachable capability issuer**
* invariant: a recovery caller must not (re)acquire proof authority after process
  death; §8-§10 ("no legitimate recovery-facing capability issuance path").
* location: `src/aios_core/runtime/background_attempt.py:1570-1705`
  (`_issue_external_return_capability`, `_capability_from_row`), reached via public
  `runtime.background_model_attempts`.
* repro: `reviewer_probes/window14_independent_attack.py` `IA14-ORACLE-001`
  (dispatched attempt → `in_doubt` → fresh store → call issuer →
  `prove_external_return(forged)` → `attach_late_trusted_return`).
* expected: refusal (AttributeError-equivalent unreachable path or state/binding
  denial). actual: capability reissued with nonce; arbitrary bytes staged trusted.
* impact: arbitrary recovery process can fabricate a trusted provider return for any
  dispatched/in_doubt attempt → attacker-controlled model output, metering, World
  writes, assistant output; defeats the window's entire authenticity premise.

**BLK-W14-002 — nonce plaintext in public DB path; public proof function completes oracle**
* invariant: the nonce must not be reachable through ordinary Core/backup/export
  surfaces (§11).
* location: `background_attempt.py:647` (schema), `:1660` (plaintext hex insert);
  `SQLiteWorldStore.db_path` public (`sqlite_store.py:183`); `late_return.py:131`
  public `late_return_proof`.
* repro: `IA14-NONCE-001` (read-only `sqlite3.connect(store.db_path)` → nonce →
  `late_return_proof` → attach).
* expected: nonce unrecoverable outside trusted issuance. actual: read-only DB access
  yields a full proof-minting capability through public APIs.
* impact: any DB backup/dump/replica leak = signing authority; trusted-state creation
  from read-only access.

**BLK-W14-003 — post-dispatch false `not_submitted` writable via `mark_failure`**
* invariant: `not_submitted` requires mechanical pre-dispatch proof; post-dispatch and
  caller-asserted non-submission must be mechanically refused (§3, §18, §19 NS-A/NS-G).
* location: `src/aios_core/runtime/background_attempt.py:1135-1195`
  (`mark_failure`, `UPDATE … WHERE state IN ('admitted','dispatching')`).
* repro: `IA14-NS-001` and `raw/ns001_confirmation_variant.txt` (dispatched attempt +
  binding + `mark_failure(definitely_not_submitted=True, error=<anything>)`).
* expected: refusal. actual: durable `state='not_submitted'` (even from a plain
  `RuntimeError`; typed signal not enforced at the write site).
* impact: recovery caller mints false non-submission → `admit` reset → second request
  identity → blind redispatch while the first may complete; reintroduces the
  adjudicated `IA-B-R003-BLK-002` failure class through the remaining write site.

**BLK-W14-004 — stale capability row across legal `not_submitted` retry with rotated binding**
* invariant: the accepted retry path must have an explicit, coherent capability/binding
  contract and class-A late return must remain attachable for the retried dispatch
  (§21).
* location: `background_attempt.py:1043-1047` (binding replaced on retry) vs
  `:1645-1655` (capability row never re-scoped/rotated).
* repro: `reviewer_probes/window14_s3_stale_capability_rotation.py`
  (typed `not_submitted` → re-admit → `mark_dispatching` with new fingerprint →
  genuine proof for the new request).
* expected: re-scoped capability or documented refusal at retry time. actual: both the
  stale and the "re-issued" capability are permanently unattachable
  ("not scoped to this attempt's durable originating request") — silent recovery
  dead-end exactly on the "retry dispatches a new outbound request" branch.
* impact: for any legal retry whose outbound request is not byte-identical, a real
  late return can never be attached; attempt sticks fail-closed forever, with no
  operator-visible reason.

**Non-blocking disclosure:** `EVIDENCE-CONSISTENCY-001` (§9), `T-ROOT-001` (§3.5).

---

## 16. Verdict

```
ACCEPTANCE_FAIL / blocker=4
CORRECTIVE_REQUIRED
```

The candidate genuinely delivers the headline recovery capability (real SIGKILL
process loss, exactly-once continuation, no redispatch, R1–R5 green, identity and
JSON ambiguity closed, post-dispatch `reconcile_not_submitted` retired, the CI
validation gap honestly closed with shallow=SKIP and the historical C003 zero-diff
proven, and the baseline RED reproduced). But the independent acceptance mandate is
to prove the late-return capability is **not** a signing oracle, that `not_submitted`
is **mechanically** unreachable post-dispatch, and that the capability lifecycle has a
coherent retry contract. All three fail under attack: the issuer is reachable through
the ordinary recovery object graph and re-returns the nonce after process death
(BLK-001); the nonce is plaintext on the public DB surface and weaponizable through
public APIs alone (BLK-002); the durable `not_submitted` write site still trusts a
caller boolean (BLK-003); and the legal retry branch silently kills the capability
for the retried request (BLK-004).

Per §35 no candidate fix was attempted. Per §36 this window performs no merge, no PM
integration, no RC-REFREEZE-004, no Resident A/B, no operator corrective, no
evaluator work.

`WINDOW_14 = COMPLETE / CLOSED`
