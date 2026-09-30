# C15-RCC-RES-B-ACCEPT-003 — Failure Adjudication (WINDOW 12)

Date: 2026-09-30
Repository: `Haneof/Haneof-AIOS-Core-v3.0`
WINDOW: `12`
Task: `C15-RCC-RES-B-ACCEPT-003-FAILURE-PM-ADJUDICATION`
Role: C15 Governance PM / Acceptance-Failure Adjudicator
MERGE_POLICY: `GOVERNANCE_ONLY_AT_END`

Not this window: not Window 08 Resident B, not Window 10 Independent Acceptance Reviewer, not
Window 11 publication finalizer, not corrective engineer, not Core engineer, not Resident C,
not evaluator. This window does **not** redo Independent Acceptance. It adjudicates the already
published verdict and dispositions the failure.

---

## 0. Verdict block

```text
WINDOW_12 = C15 Governance PM / Acceptance-Failure Adjudication

C15-RCC-RES-B-ACCEPT-003   = DONE / ACCEPTANCE_FAIL / blocker=2
C15-RCC-RES-B-RERUN-003    = FAILED / NON_CANONICAL / RETIRED
run   c15-rcc-res-b-rerun-003-60997e04     = HISTORICAL / IMMUTABLE / DO_NOT_REUSE
session c15-rcc-res-b-session-003-60997e04 = RETIRED / DO_NOT_REUSE

IA-B-R003-BLK-001 = BINDING / EVIDENCE-IRREPARABLE_FOR_RERUN_003
IA-B-R003-BLK-002 = BINDING / NON_CANONICAL / NOT_REPAIRABLE_IN_THE_FROZEN_RUN

ROOT CAUSE = DUAL_LAYER_GAP  (ownership route C)
  - C15 operator / exchange provenance + recovery-integration gap (primary for BLK-001)
  - Core product gap: late trusted external return after Core process death has no legal
    attach path, and a post-dispatch retry-enabling durable false state is writable
    without a non-dispatch proof (primary enabler for BLK-002)

UNIQUE NEXT READY = CORE-BACKGROUND-LATE-TRUSTED-RETURN-001
NEXT_WINDOW       = 13
```

No mechanical PASS from Window 08/09/10 is withdrawn. No historical record is rewritten.
`ACCEPTANCE_FAIL / blocker=2` is **not** restated as "overall PASS with two observations".

---

## 1. Fresh ground truth (fresh fetch at dispatch; no summary trust)

| Anchor | Expected (dispatch) | Freshly observed | Verdict |
|---|---|---|---|
| live `main` | `b947ff548e531169d2bec3f94ddd40eb99129fca` | `b947ff548e531169d2bec3f94ddd40eb99129fca` (`origin/main` = local `main` = `HEAD` base) | match |
| PR #302 | OPEN / EVIDENCE_ONLY / UNMERGED | `state=OPEN`, `mergedAt=null`, `mergeable=MERGEABLE`, base `main`, head branch `arena/01a0ee8c-haneof-aios-core-v3-0`, 1 comment | match |
| PR #302 exact head | `846b55e63abe7f4d7c25adde013978cce6084556` | match (`refs/pull/302/head` = branch tip) | **no drift** |
| PR #302 tree / sole-parent chain | `634ed0bfb5ebfcb9f7d7fe7de4418f1731925ace` | match; parent `f7ee14a23ab3c7de0793cecb7a83291fd2971110`; scope = `evidence/w08/**` only | match |
| PR #303 | MERGED (Window 09 readiness) | `MERGED`, `mergeCommit = b947ff548e531169d2bec3f94ddd40eb99129fca` = live `main` | match |
| Window 10 final review | `bc403bc84d7ad2745b6474537bca427a6f9eab06` | present on `arena/01a0f04c-haneof-aios-core-v3-0` | match |
| review tree | `72845cd6260f9ac30f5d06a828389af424cab7c1` | match | match |
| review sole parent | `846b55e63abe7f4d7c25adde013978cce6084556` | match (single parent = PR #302 exact head) | match |
| review evidence subtree | `79cf6fd197487f125e922742d521a4a1e2740597` | `git rev-parse bc403bc…:reviews/C15_RCC_RES_B_ACCEPT_003_WINDOW_10` = match (34 files) | match |
| PR #302 IA FAIL comment | `5903361483` | present, exactly one comment on #302, `ACCEPTANCE_FAIL / blocker=2` | match |
| transport commit | `0978e735c7b94cd83419712eda2b1b6ad221cedd` | present on `arena/01a0f038-haneof-aios-core-v3-0`, sole parent = `b947ff54…` (= live `main`), identical evidence subtree `79cf6fd1…` | match |
| authoritative ref | `refs/heads/persistence/c15-rcc-res-b-rerun-003-60997e04` | exists; remote head `5692a32972f72afb6337aa68cc97310734f14c9c` = FINAL_FREEZE commit; `generation = 48` | match |
| frozen final head | `5692a32972f72afb6337aa68cc97310734f14c9c` | match | match |
| run / session identity | `c15-rcc-res-b-rerun-003-60997e04` / `c15-rcc-res-b-session-003-60997e04` | `owner.json`: `remote_authoritative=true`, exact run/session, ref, `subject_id=user_1` | match |
| task board / checkpoint | Window 09 top entry | both present, Window 09 = last control entry | match |

`PM_ADJUDICATION_BLOCKED_BY_GROUND_TRUTH_DRIFT` **is NOT triggered**. No relevant drift exists.

Additional fresh, read-only verification performed by this window (no mutation of any artifact):

- the authoritative ref was extracted (`git archive`) and inspected directly;
- `background_model_response_receipts` = **0 rows** and `background_model_responses` = **0 rows**
  in the sealed freeze copy of the private World and in every inspected sealed generation;
- `background_model_attempts` = 43 rows, final states `{metered: 43}`, exactly one row carrying
  `reconciliation_evidence` (`bgattempt_1d6735f46f05508149948ea5a7de5b01`);
- sealed generation `000034` (`label = OPERATOR_RECOVERY_RECONCILE_NOT_SUBMITTED_PM_AUTHORIZED_2026-09-30`,
  `manifest_sha256 = 44a19676ef32f9330a9bdb6195cce0aac8dd926f77e8cad312b647d0b064bd53`) contains the attempt
  row in state **`not_submitted`**; generation `000035` and `000048` contain it `metered`;
- audit stream: 293 records; record **211** = `operator_reconcile_not_submitted`
  (`before_state=in_doubt`, `after_state=not_submitted`, `directive=USER_ADJUDICATION_CONTINUE_2026-09-30`),
  record 292 = `final_freeze`;
- exchange ledger 129 records; `req-0039-model_directive-ed097a32` at seq 115
  (`request_published`, `2026-09-29T20:06:29.156116Z`), seq 116 (`response_published`,
  `2026-09-29T20:37:01.219554Z`, response sha `21a31eb306938b1c777f431cff9183e86c1233298344aebb0dcced3a78dd22c2`),
  seq 117 (`response_consumed`, `2026-09-29T20:45:20.168905Z`, identical sha);
- `exchange/responses/*.json`: 43 files, **0** carrying `directive.provenance`, **0** carrying
  `directive.usage`; envelope keys fixed to
  `[authored_by, directive, request_id, request_sha256, response_version]`;
- negative scan for contemporaneous authorship artifacts in the authoritative tree: only
  `evidence/freeze/b_process_id.txt` (`8887ab32-f693-44b7-ba25-5b32fc4dc864`) and
  `evidence/freeze/b_session_id.txt` (`resident-b-003-12da5a13261e4c0d`) exist; there is **no**
  response receipt, **no** Resident execution log, **no** invocation receipt, **no** signature,
  **no** trusted handoff record, and **no** request→invocation→response chain for `req-0039`.

---

## 2. Frozen Independent Acceptance facts (preserved exactly; not re-derived, not softened)

Window 10 verdict, published by Window 11 strictly as evidence publication finalizer:

```text
C15-RCC-RES-B-ACCEPT-003 = ACCEPTANCE_FAIL / blocker=2
CORRECTIVE_OR_ADJUDICATION_REQUIRED
```

`IA-B-R003-BLK-001` — `UNPROVEN_RESIDENT_AUTHORSHIP_REQ0039`: the `req-0039` round-0 response
publication happened after the assigned process died, through anonymous transport with
`provenance=None`, trusted provider identity `UNKNOWN`, no trusted-return receipt, no durable
invocation receipt binding exact response bytes to the assigned Resident decision process. Evidence
proves the bytes were published and consumed; it does not prove the assigned Resident本人 decided
them. The reviewer did not and does not claim human authorship; the finding is a provenance /
proof-sufficiency failure.

`IA-B-R003-BLK-002` — `FALSE_NOT_SUBMITTED_RECONCILIATION`: `req-0039` was durably
`request_published` (seq 115), the frozen exchange contract declares that record to be the semantic
dispatch boundary, therefore `semantic_dispatch_occurred=true` and the run's own check computes
`not_submitted_allowed=false`; generation 34 still durably wrote `state=not_submitted`; honest
reconciliation disclosure cannot convert a false historical state into a true one; exactly-once
effects and a terminal green end state cannot exempt an independent semantic-contract
falsification (`W09-F3 = BLOCKER / NON_CANONICAL`).

Fresh IA is the higher authority on semantic canonicality. Window 09's `PM_READINESS_PASS` was a
readiness gate only; its §7.4/§7.5 reasoning is **superseded** by the Fresh IA verdict on BLK-002,
exactly as Window 09 itself required ("PM readiness is not a verdict"; W09-F3 was handed to IA
unpre-empted).

### 2.1 Mechanical integrity preserved (all retained, none waived)

48/48 generations (manifest self-digests valid) · 287/287 archived artifacts byte-verified ·
129 contiguous ledger records with valid hash chain · 43/43 exchange 3-event completions
(`request_published → response_published → response_consumed`) · 43/43 attempts metered 1:1 with
outbound request fingerprints · A→B continuity exact (A pins `0d6970ed…` / `79c877a4…` /
`6b90fc7a…` / `3b2b9e90…`) · cursor 14..22 chronology complete and unique · World/index 66/66, lag 0 ·
cursor 23 never revealed · no future-leak blocker · c19 GitHub-auth outage recovered as
`RECOVERED_INFRASTRUCTURE_INCIDENT`.

These remain true. They do **not** cure either blocker, and they are not used here as a
counter-argument to the Fresh IA verdict.

---

## 3. Blocker adjudication table (binding)

| Blocker | PM disposition | Current run curable? | Engineering owner |
|---|---|---|---|
| `IA-B-R003-BLK-001` `UNPROVEN_RESIDENT_AUTHORSHIP_REQ0039` | `BINDING / EVIDENCE-IRREPARABLE_FOR_RERUN_003` — no contemporaneous immutable authorship proof exists anywhere in the repository or platform artifacts; post-hoc evidence is forbidden | **NO** | C15 **operator / exchange** layer (response provenance + process/session binding + non-substitutable Resident authorship). Core is not the authorship authority and is not implicated in the authorship failure. |
| `IA-B-R003-BLK-002` `FALSE_NOT_SUBMITTED_RECONCILIATION` | `BINDING / NON_CANONICAL` — the false durable state is sealed inside immutable generation 34 and cannot be repaired without rewriting frozen evidence; additionally the enabler (a post-dispatch retry-enabling exit writable without a non-dispatch proof) and the missing legal continuation are Core gaps | **NO** | **DUAL**: C15 **operator** (executed `reconcile_not_submitted` after the dispatch boundary, violating both the frozen exchange rule and the accepted operator-session contract) + **Core** (unguarded retry-enabling exit; no legal mechanism to attach a late trusted return) |

Both blockers are binding. Neither is downgraded, merged, or reclassified as an observation.
No frozen-contract clause was found that would authorize accepting a false historical state or
accepting unproven assigned-Resident authorship.

---

## 4. First PM ruling — BLK-001 cannot be cured for RERUN-003

### 4.1 Fresh search for pre-existing contemporaneous immutable evidence: NEGATIVE

The admissible classes were searched fresh in the authoritative persistence ref, PR #302 evidence,
the Window 10 review tree, and current `main`:

| Class sought | Fresh result |
|---|---|
| signed / session-bound response receipt | **absent** (no signature/key/HMAC artifact for the response) |
| immutable Resident execution log | **absent** (no Resident-side log in the frozen tree) |
| response-producing process receipt | **absent** (`b_process_id.txt` only names the released resident process; it binds no request/response) |
| trusted handoff record | **absent** (`background_model_return_handoffs` / `background_model_response_receipts` empty; 0 receipts for all 43 rounds) |
| exact request → Resident invocation → exact response chain | **absent** (the exchange envelope carries only `request_id`, `request_sha256`, `authored_by=EXTERNAL_CURRENT_RESIDENT_SESSION`, `directive`; `authored_by` is a constant required by the response contract, not a process-authenticated fact) |

The exchange file family can prove integrity of the byte path (`sha256` equals ledger records,
consumption is exactly once) and it can prove the request was dispatched and answered — it cannot
prove **who** produced the bytes.

### 4.2 Post-hoc evidence is forbidden as a cure

The following are explicitly **not** admissible to cure BLK-001, and were not used here: a new
explanatory statement; a Resident recollection; a newly added `provenance` field; a newly produced
signature; regenerating the response; operator oral confirmation; PM assertion that "the AI wrote
it". All of these are post-hoc self-assertion, not contemporaneous immutable proof.

### 4.3 Ruling

```text
IA-B-R003-BLK-001 = BINDING / EVIDENCE-IRREPARABLE_FOR_RERUN_003
```

No future software correction can retroactively grant RERUN-003 a proof that did not exist at
runtime. BLK-001 is a live defect of the **C15 external Resident transport**: it published the
round-0 response after the assigned process died, with no process/session/decision binding and no
provider identity, and it is structurally unable to distinguish Resident-produced bytes from
operator-pasted bytes.

---

## 5. Second PM ruling — BLK-002 cannot be repaired inside the frozen run

### 5.1 Mechanical facts re-verified

- generation 34 is an ordinary, sealed, hash-chained member of the authoritative generation chain;
- `request_published` for `req-0039` (seq 115) strictly precedes it;
- generation 34's sealed World durably contains `background_model_attempts.state='not_submitted'`
  for `bgattempt_1d6735f46f05508149948ea5a7de5b01` together with the mandatory non-blank
  `reconciliation_evidence` that itself records that the dispatch boundary was crossed;
- audit record 211 records `in_doubt → not_submitted` under the "continue" directive;
- every later generation is built on top of it (gen 35..48; the attempt returns to `metered` only
  because a later legal retry re-entered the state machine).

The run's own integrity surface makes the contradiction explicit
(`semantic_dispatch_occurred=true`, `not_submitted_allowed=false`). Disclosure is honest; it does
not make the durable field truthful.

### 5.2 Repair paths examined and rejected

| Candidate repair | Why it is forbidden |
|---|---|
| rewrite generation 34 | destroys the frozen evidence chain (sealed generation + remote-authoritative ref) |
| rewrite the ledger / attempt row | rewrites accepted historical evidence; the false write is itself the historical fact |
| generation 49 to "overwrite history" | appends over a sealed contradiction; does not remove it, and would require continuing a run whose canonicality is already falsified |
| rebase or force-push the persistence ref | destroys authoritative remote history and CAS-anchored evidence |
| delete the contradiction | historical erasure |
| re-run only cursor 20 / replay `req-0039` / regenerate the response | retroactively creates a new execution under a consumed identity; explicitly forbidden by the RERUN-002 precedent |
| "continue from gen 33 / gen 35" | continuation of a frozen identity that has already produced a sealed false state |

### 5.3 Second half of the ruling: the enabling defect is not only operator-side

Two independent Core-side facts were confirmed at source level (current `main`):

1. **An unguarded retry-enabling exit exists after the dispatch boundary.**
   `BackgroundModelAttemptStore.reconcile_not_submitted` (`src/aios_core/runtime/background_attempt.py:1257`)
   is callable for `dispatching` / `in_doubt` attempts and its only guard is *absence of a receipt*.
   It writes a durable `state='not_submitted'` together with caller-supplied evidence text. A caller
   that knows the dispatch boundary was crossed can still write the false state; Core cannot detect
   the contradiction because it owns no notion of the external exchange dispatch boundary.
2. **There is no legal continuation for a late trustworthy return.**
   Receipts are minted only by `_capture_trusted_response_return`
   (`background_attempt.py:1462`, private, docstring: "wired only as CognitiveRuntime's trusted
   return callback"), which is reachable only through
   `turn_runtime._authenticate_background_model_response` (`turn_runtime.py:1304-1326`) at the
   in-process model-return boundary; that boundary is unreachable for a `dispatching` / `in_doubt`
   attempt because `admit()` (`background_attempt.py:811-921`) raises
   `BackgroundModelExecutionInDoubt` **before** the model handler runs. `stage_exact_response`
   requires a pre-existing receipt; `reconcile_response` is deliberately disabled; and
   `recover_trusted_handoff` promotes only Core-owned callback bytes. An externally produced
   contemporaneous proof therefore has **no** ingestion path.

### 5.4 Ruling

```text
IA-B-R003-BLK-002 = BINDING / NON_CANONICAL / NOT_REPAIRABLE_IN_THE_FROZEN_RUN
```

The operator's write is the executed violation; the absence of any legal continuation is what made
the violation reachable, and the unguarded exit is what made it writable. Attribution is recorded in
§7 and §8 below, and is **not** collapsed into "operator misuse only" or "Core bug only".

---

## 6. Current-run disposition and hard prohibitions

```text
C15-RCC-RES-B-ACCEPT-003     = DONE / ACCEPTANCE_FAIL / blocker=2
C15-RCC-RES-B-RERUN-003      = FAILED / NON_CANONICAL / RETIRED
run   c15-rcc-res-b-rerun-003-60997e04      = HISTORICAL / IMMUTABLE / DO_NOT_REUSE
session c15-rcc-res-b-session-003-60997e04  = RETIRED / DO_NOT_REUSE
```

`RETIRED` does not mean deleted. The following must be permanently preserved, unmodified:

- PR #302 — `OPEN / EVIDENCE_ONLY / FROZEN / DO_NOT_MERGE` (head
  `846b55e63abe7f4d7c25adde013978cce6084556`, tree `634ed0bf…`, 5 evidence-only commits);
- authoritative persistence ref `refs/heads/persistence/c15-rcc-res-b-rerun-003-60997e04` at
  exactly `5692a32972f72afb6337aa68cc97310734f14c9c`, generations 1..48, exchange ledger,
  mailbox/freeze evidence — **never deleted, never rewritten**;
- Window 10 review `bc403bc84d7ad2745b6474537bca427a6f9eab06` —
  `REVIEW_ONLY / IMMUTABLE / DO_NOT_MERGE`;
- transport `0978e735c7b94cd83419712eda2b1b6ad221cedd` — `TRANSPORT_ONLY / DO_NOT_MERGE`
  (not an accepted review identity);
- Window 11 publication identity and the IA FAIL comment `5903361483`;
- every Window 08/09/10 historical RED, blocker count, and incident record.

Prohibited for the retired run, permanently:

```text
reveal cursor 23
create generation 49
re-run only cursor 20
replay req-0039
regenerate or re-publish the req-0039 response
"continue from gen 33" or "continue from gen 35"
create a corrected final freeze under the same run id
reuse the run id or the session id
```

Authorization to continue the same run was searched for in the frozen contracts and **does not
exist**. Exactly-once effects are not such an authorization: they prove no duplicate happened, not
that a false durable state is admissible.

---

## 7. Source trace — engineering responsibility along the full `req-0039` chain

| # | Layer | Source / artifact | Finding |
|---|---|---|---|
| 1 | Resident decision producer | external Resident session; no Resident-side receipt | no non-forgeable authorship artifact was ever produced; the assigned process died before the bytes existed |
| 2 | C15 response publisher | `aios_exchange/responses.py`, envelope contract in `aios_exchange/schema.py` (`RESPONSE_ENVELOPE_KEYS`, `parse_model_directive:287`) | envelope fixed; `directive.provenance` optional and **never used** (0/43); no process/session field exists at all |
| 3 | file / exchange transport | `aios_exchange/bridge.py` (`DISPATCH_BOUNDARY_RULE`) | the transport *knows* `request_published` is the semantic dispatch boundary and forbids post-boundary `not_submitted`; the response was published post-mortem through it without any authorship binding |
| 4 | `request_published` boundary | ledger seq 115 | dispatch provably crossed |
| 5 | model handler return | `aios_exchange/runner.py:ExternalSessionModelHandler.__call__` → `_resolve` → `parse_model_directive` | handler returns the file's directive; it adds no identity; recovery route `recovered_durable_response` could re-present exact bytes, but Core never reached the handler |
| 6 | provider / model provenance | `evidence/freeze/provider_identity.json` (`EXTERNAL_CURRENT_RESIDENT_SESSION`, `UNKNOWN`) + 0/43 responses with provenance | anonymous by construction for the whole run (allowed by RELEASE-003 as a non-blocker, but structurally incompatible with trusted-return recovery) |
| 7 | Core `_provider_identity` | `turn_runtime.py:1313-1320` | any `None` ⇒ deliberate early return; anonymous handlers are legal but cannot participate in exact external-response recovery |
| 8 | trusted-return receipt capture | `background_attempt.py:_capture_trusted_response_return` | never invoked for this run; `background_model_response_receipts = 0` |
| 9 | `BackgroundModelAttemptStore` | `admit()` L811-921 | restart converted `dispatching → in_doubt` (`restart_after_dispatch_boundary`) and raised **before** the handler; the legal recovery route was unreachable |
| 10 | crash / restart | `evidence/incident_.../due20_first_attempt_response_timeout.log`, `due20_second_attempt_indoubt_crash.log` | 1800 s await timeout and process-group kill; response published 30 min later by the operator |
| 11 | `in_doubt` continuation | — | no legal exit: `stage_exact_response` needs a receipt; `reconcile_response` disabled; `recover_trusted_handoff` only promotes Core-owned bytes; wake resume re-enters the same guard |
| 12 | exact-response recovery API | `stage_exact_response` / `recover_trusted_handoff` | structurally unreachable in this state |
| 13 | reconciliation | `reconcile_not_submitted` L1257; audit 211; sealed gen34 | used despite the known dispatch crossing ⇒ durable false state |

**Layer verdict.** The authorship chain breaks at layers 1–3 (C15 operator / exchange: no
non-forgeable Resident process/session/decision binding, no provider identity, operator can author
or transport bytes indistinguishably). The recovery chain breaks at layers 9–13 (Core: no legal
continuation for a late trustworthy return, and an unguarded retry-enabling write). Both breaks are
real and independent.

---

## 8. Independent Core-gap question (the decisive question of this adjudication)

> «Even if a corrected C15 transport could prove that this exact response was genuinely produced
> by the assigned Resident, does current accepted Core provide a legal mechanism — one that does not
> turn the recovery caller into a signing oracle — to attach that contemporaneous trusted proof plus
> the exact response back to the same durable attempt, when the Core operator process already died
> before the response arrived?»

```text
ANSWER = NO
```

Source-level reasons (current `main`, post-`CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001`):

1. `_capture_trusted_response_return` is private and reachable only through Core's own trusted
   return callback at the **in-process** model-return boundary (`turn_runtime.py:1304-1326`);
2. for a `dispatching`/`in_doubt` attempt, `admit()` raises **before** the model handler, so that
   boundary can never be reached again for the round;
3. `stage_exact_response` verifies an `authenticity_proof` only against a **pre-existing** row in
   `background_model_response_receipts`, and recovery callers hold neither the HMAC key nor a
   signing callable;
4. `recover_trusted_handoff` promotes only Core-owned callback bytes;
5. the only remaining exit is `reconcile_not_submitted`, whose sole guard is receipt absence — it is
   a trust-the-caller mutation that can durably record a false state, and it is precisely the exit
   that produced BLK-002.

Therefore a late external return is, even with perfect external provenance, **unattachable**. This
is a genuine new failure class — *trusted external return arriving after Core process death* — which
is **distinct** from, and not covered by:

- `CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001`
  (`DONE / ACCEPTED / INTEGRATED`, accepted candidate
  `a73e186d40688f5dc181b1128a62eff37a974409`, integration main
  `f20f2edfa7af00d0286493fd15196ca9503bc315`), whose accepted class is *the trusted return already
  crossed the in-process boundary and was durably handed off, with a crash before application*;
- the pre-existing PM ruling of 2026-09-28 that the post-boundary-without-receipt state is a Core
  recovery-surface gap, and W09-F4's residual-gap note.

This adjudication explicitly **does not** claim that "anonymous path fail-closed" is a Core
regression. Fail-closed for an unauthenticated return is correct and must stay. What is missing is
(a) a *legal* way to attach a return that Core can genuinely trust, and (b) closure of the
retry-enabling false-state exit. Both belong to Core.

---

## 9. Ownership route

```text
ROUTE C — DUAL_LAYER_GAP
```

- **C15 operator / exchange layer** owns the authorship gap and the executed false write: the
  transport never bound response bytes to the assigned Resident process/session/decision, never
  emitted provider identity (0/43), allowed publication after process death, could not distinguish
  Resident bytes from operator bytes, and called `reconcile_not_submitted` after the dispatch
  boundary in direct violation of the frozen exchange rule (`DISPATCH_BOUNDARY_RULE`) and of the
  accepted operator-session contract (`tools/c15_persistence/operator_session.py`, which declares
  that it never rewrites `in_doubt` into `not_submitted` and that a crossed boundary without a
  durable trusted return is a hard fail-closed stop).
- **Core** owns the enabling product gap: no legal attach path for a late trusted external return
  after process death, and a post-dispatch retry-enabling durable write that requires no
  non-dispatch proof.

Because the dependency chain runs Core → RC → Resident A → B operator → B release → B run, the
single most-upstream task is the Core corrective. One window / one task / one next READY is
maintained; the operator corrective is **not** released in parallel.

---

## 10. Persistence Corrective-003 disposition (not reopened)

```text
C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003 = DONE / ACCEPTED / INTEGRATED   (unchanged)
```

Its accepted binding scope was `C002-001` (authoritative checkpoint failure must hard-stop),
`C002-002` (later-round remote-only convergence without redispatch/duplicate work/metering/ACK) and
`C002-004` (remote-authoritative binding loss must fail closed), all IA-passed at
`111a25d1f0822bc2b37557aa2364a4030d267082` and integrated at
`ef679ed5678634833dee20d706fe9dfda03194aa`.

Independent reasons this failure does **not** violate that scope:

1. remote-authoritative persistence itself worked: the ref stayed authoritative, CAS
   (`--force-with-lease` + expected head) held through the c19 auth incident, every generation
   sealed, remote head == local head == generation chain from gen 1 to gen 48;
2. generation sealing and evidence durability worked: 48/48 generations, 287/287 artifacts,
   10/10 freeze digests, mailbox byte-identical;
3. exactly-once durable effect held: 43/43 attempts metered 1:1, no duplicate dispatch, capability
   effect, World write, meter, output or ACK;
4. fail-closed held where the accepted design requires it: the restart did fail closed at Core
   admission rather than silently continuing;
5. the failing decisions were taken **outside** the accepted persistence harness, through a public
   Core API invoked by the real-B operator path (already recorded as W09-F1), and the residual
   provider-boundary gap was already PM-classified on 2026-09-28 as a **Core** dependency, not a
   persistence-harness defect.

Therefore the persistence corrective is **not** reopened, rolled back, or re-scoped, and no
historical green is withdrawn. Its own harness contract (hard fail-closed stop on a crossed provider
boundary without a durable trusted return) is in fact *consistent* with this adjudication and is
preserved as evidence that the legal answer to this state is a stop, not a false write.

---

## 11. Unique next READY task (frozen here)

```text
CORE-BACKGROUND-LATE-TRUSTED-RETURN-001 = READY
```

This is a **new** task ID for a **new** failure class. It is not a re-run of, and must not be named
as, `CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001` or its corrective — that task is
`DONE / ACCEPTED / INTEGRATED` within its accepted scope and is not re-opened.

**Failure class (frozen):** *a provider/Resident return that exists only outside the Core process
at the moment the attempt's process dies* — durable attempt state `dispatching` / `in_doubt`, no
row in `background_model_response_receipts`, no legal continuation, and a retry-enabling
`not_submitted` write that Core cannot refuse even though the provider boundary was crossed.

**Binding required closures (C1–C5).** Engineering decides the design; the following are binding.

- **C1 — legal, fail-closed attach (or explicit terminal stop).** Provide a sanctioned mechanism by
  which a *late* return that Core can genuinely trust may be attached to the same durable attempt
  exactly once, **or** — if engineering proves no such mechanism can exist without weakening the
  authenticity invariant — make the post-dispatch dead end explicitly terminal and require the
  operator/release layer to stop and retire the run. Whichever route is chosen must be frozen,
  documented, and mechanically proven. The chosen route must never let caller-supplied bytes become
  a trusted provider return, and must never grant a recovery caller signing/minting authority.
- **C2 — no false post-dispatch reconciliation.** After the dispatch boundary
  (`dispatching` / `in_doubt`), a durable `not_submitted` write must be impossible, or provably
  fail-closed without a non-forgeable non-dispatch proof. The legal `admitted`-only retry path
  (and any `not_submitted → admitted` retry semantics) must be updated coherently, with tests, or
  explicitly retired with justification. Historical rows and sealed generations must never be
  rewritten.
- **C3 — invariants preserved.** No caller-supplied bytes → trusted receipt; metadata-only
  reconciliation stays disabled; no provider redispatch across the boundary; R5 exactly-once
  durable-effect semantics (one meter, one capability/World effect, one output, one ACK identity);
  conflicting/duplicate replay stays fail-closed; anonymous/local handlers remain a legal but
  non-recoverable class unless a registered identity exists, and any change to that rule must be
  explicitly governed.
- **C4 — evidence.** RED-first probes frozen against the exact current `main` before implementation;
  minimum matrix: late trustworthy return after process death; post-dispatch
  `reconcile_not_submitted` attempt; signing-oracle attempt by a recovery caller; conflicting replay;
  crash-after-in-process-return regression (must remain as accepted by CORRECTIVE-001); full
  regression and formal gates at the pinned runtime.
- **C5 — scope discipline.** No `src/aios_core/**` change outside the frozen task scope; no C15
  harness/operator change in this task; no modification of PR #302, the Window 10 review, the
  transport commit, the persistence ref, generations 1..48, or any run evidence; no Resident B/C
  run; no cursor reveal.

**Mandatory downstream sequence after this task is accepted (one READY at a time):**

1. `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-INDEPENDENT-ACCEPTANCE`
2. PM integration of the accepted Core exact candidate
3. `CORE-RC-REFREEZE-004` → `CORE-RC-REFREEZE-004-INDEPENDENT-ACCEPTANCE`
4. fresh `C15-RCC-RES-A-RERUN-005` → its Independent Acceptance
5. `C15-RCC-RES-B-OPERATOR-PROVENANCE-CORRECTIVE-001` → its Independent Acceptance
6. `C15-RCC-RES-B-RELEASE-004`
7. `C15-RCC-RES-B-RERUN-004`
8. `C15-RCC-RES-B-ACCEPT-004`

Because this Core change touches the recovery/restart semantics that Resident turns depend on, the
current Fresh A Corrective-003 lineage (38/38, PR #296) becomes
`HISTORICAL_FOR_PRIOR_RC_ONLY`; it **must not** be silently reused as the RERUN-004 handoff. A new
RC re-freeze and a new fresh Resident A are mandatory, exactly as the C-001 precedent required.

**Frozen downstream scope of `C15-RCC-RES-B-OPERATOR-PROVENANCE-CORRECTIVE-001`** (blocked until
step 5; recorded now so no window re-derives it):

1. exact Resident authorship provenance per invocation;
2. exact request / response / session / process binding (echo of `request_id` + `request_sha256`
   plus non-forgeable process/session identity and a durable per-invocation receipt);
3. no operator semantic substitution — mechanically prevented, not merely promised (the operator
   must be unable to author or patch response payloads);
4. after semantic dispatch, never call `reconcile_not_submitted` — enforced fail-closed in the
   harness;
5. legal exact-response recovery only through the accepted Core path (post-`CORE-BACKGROUND-LATE-TRUSTED-RETURN-001`);
6. fail closed when authorship / trusted-return proof is unavailable, with an explicit run-retirement
   policy instead of a false state;
7. synthetic crash-after-dispatch probes covering the real failure shape (kill mid-await, response
   published after death), plus provenance-absent and identity-mismatch negatives; and no reuse of
   the retired RERUN-003 identities.

---

## 12. Downstream status (effective now)

```text
C15-RCC-RES-B-ACCEPT-003  = DONE / ACCEPTANCE_FAIL / blocker=2
C15-RCC-RES-B-RERUN-003   = FAILED / NON_CANONICAL / RETIRED
C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003 = DONE / ACCEPTED / INTEGRATED (unchanged)
C15-RCC-RES-B-RELEASE-004 = BLOCKED
C15-RCC-RES-B-RERUN-004   = BLOCKED
C15-RCC-RES-B-ACCEPT-004  = BLOCKED
RESIDENT_C                = BLOCKED
EVALUATOR (C15)           = BLOCKED
C15_CLOSE                 = BLOCKED
C15-RCC-MODEL-ATTEST-001  = BLOCKED
UNIQUE NEXT READY         = CORE-BACKGROUND-LATE-TRUSTED-RETURN-001
NEXT_WINDOW               = 13
```

---

## 13. Governance writeback and window closure

- This adjudication is **GOVERNANCE_ONLY**. Changed paths: this file,
  `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`, `AIOS_v3.0_CURRENT_CHECKPOINT.md`.
- No `src/**`, no `tools/**`, no `tests/**`, no `reviews/internal_habitation/**`, no run evidence,
  no PR #302 change, no review-branch change, no persistence-ref change, no release-state change.
- Independent governance PR on the session-fixed branch; applicable checks
  `c15-rcc-fixture-mechanical-gate` and `semantic-repair-mechanical-gate`, both of which must be
  GREEN on the governance PR head before merge.
- Governance PR number, gate run IDs/conclusions, merge SHA and post-merge `main` are recorded in
  the governance PR thread and in the PM adjudication comment on PR #302 (established convention;
  no post-merge rewrite of this frozen document).
- A PM adjudication comment is published on PR #302 recording the Fresh IA verdict, the accepted
  exact review identity, both blocker dispositions, the current-run disposition, the engineering
  owner classification, the unique next READY, and an explicit statement that PR #302 stays
  unmerged/frozen.
- After the governance PR merges: `WINDOW_12 = COMPLETE / CLOSED`, `NEXT_WINDOW = 13`,
  `NEXT_TASK = CORE-BACKGROUND-LATE-TRUSTED-RETURN-001`. WINDOW 13 is **not** started here.

---

## Final

```text
WINDOW_12 = COMPLETE / CLOSED after governance PR merge

C15-RCC-RES-B-ACCEPT-003  = DONE / ACCEPTANCE_FAIL / blocker=2
C15-RCC-RES-B-RERUN-003   = FAILED / NON_CANONICAL / RETIRED

ROOT CAUSE                = DUAL_LAYER_GAP (C15 operator/exchange provenance + Core late-return/
                            false-reconciliation gap)
UNIQUE_NEXT_READY         = CORE-BACKGROUND-LATE-TRUSTED-RETURN-001
NEXT_WINDOW               = 13
```
