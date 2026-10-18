# PM ACCEPTANCE BRIEF — C15-RCC-RES-B-RERUN-003 (WINDOW 08)
**For: PM / review process. Navigation material only — makes no PASS/ACCEPT claim.**
Run terminal state: `RUN_COMPLETE / AWAITING_INDEPENDENT_ACCEPTANCE`.
Decision owned by PM: release (or not) `C15-RCC-RES-B-ACCEPT-003`.

## 1. Where to look (60-second index)
| Artifact | Location |
|---|---|
| Final report (§25-style, all mandated items) | PR #302 → `evidence/w08/FINAL_REPORT.md` |
| Contemporaneous operator log (gates→startup→each cursor→incidents→freeze→terminal) | PR #302 → `evidence/w08/OPERATOR_LOG.md` |
| In_doubt incident mechanical analysis (file:line) | PR #302 → `evidence/w08/evidence-incident-reconciliation.md` |
| Post-freeze read-only terminal verification | PR #302 → `evidence/w08/TERMINAL_VERIFICATION.json` |
| Authoritative run state (gens 1–48, exchange, per-cursor evidence, freeze/**) | `refs/heads/persistence/c15-rcc-res-b-rerun-003-60997e04` @ `5692a32972f72afb6337aa68cc97310734f14c9c` (local mirror `~/c15-persistence-runs/c15-rcc-res-b-rerun-003-60997e04/`) |
| Freeze digests | run `evidence/freeze/digests.sha256` (10 artifacts) |
| Final exchange ledger (129 records, 43/43 COMPLETE) | run `exchange/ledger.jsonl` sha256 `fa7895c5103eebf3a2d8b7e635b80b54f7118d02d37065908cbbc0d930320ff8` |
| Evidence PR | #302 (EVIDENCE_ONLY, 2 commits: 64765fe, 1ab586b) |

## 2. Mechanical result summary
- Fresh A Corrective-003 boundary (PR #296 exact `317316299…`, four-hash EXACT_MATCH) → Resident B cursors **14–22** sequentially ACKed under remote-authoritative persistence; each barrier sealed (generations 1–48); FINAL_FREEZE gen 48 = remote head.
- Boundary at freeze: phase B, last_acked 22 (`c15rcc-022`), next 23 (never revealed), pending none; world 66 == index 66; wakes 7/7 completed; bg attempts 43/43 metered; nothing in flight.
- Provider exchange: req-0022..0043 exact bytes + ledger chain preserved; trusted model identity **UNKNOWN** (attested; anonymous exchange transport — directives carry no provider provenance by design).

## 3. Incidents & the one PM-relevant adjudication (disclosed in full)
1. **GitHub auth outage** (c19 POST_TURN): local seals 29–32 pushed post-recovery via single CAS `push_run_state` → `4f12ee0e…`; `verify_local_remote_authority` PASS. No re-identity/re-reveal/replay.
2. **bgattempt in_doubt** (c20 due, operator process death mid-await): accepted implementation is fail-closed for anonymous-handler rounds (no trusted-return receipt can exist — `stage_exact_response` unreachable; `reconcile_response` disabled; `reconcile_not_submitted` would record a state field contradicting the exchange ledger's dispatch fact).
   **PM/user adjudicated "继续" → operator executed `reconcile_not_submitted` (gen 34 `a9a24943…`)** with the true history in the reconciliation evidence text; unconsumed req-0039 artifacts untouched; resume consumed it via the implementation's `recovered_durable_response` path (exact snapshot bytes matched; no provider re-dispatch).
   **PM-review caveat**: the World's `background_model_attempts` state field for `bgattempt_1d6735f46f05508149948ea5a7de5b01` reads `not_submitted` as the implementation's only retry-enabling value, while the exchange ledger proves the dispatch boundary was crossed exchange-side. The semantics live in the evidence text + operator log ADJUDICATION entry. Weigh this disclosure in acceptance.
3. Everything else uneventful: capability errors (task_type/transition enums, outcome_refs, experience schema) were REAL capability-surface errors returned to the Resident and corrected in later rounds — ordinary model work, not operator intervention.

## 4. Explicitly OUT OF SCOPE of this window (remaining pipeline)
Independent Acceptance / evaluator run / Resident C / C15 closure / cursor 23+ (Fixture C). None executed; cursor 23 unrevealed; `C15-RCC-RES-B-ACCEPT-003` unclaimed.

## 5. Integrity anchors for re-verification
- Remote head: `5692a32972f72afb6337aa68cc97310734f14c9c` (== `.remote-head`, == freeze MANIFEST.final_barrier, == TERMINAL_VERIFICATION).
- Frozen A-start hashes: world `0d6970ed…` index `79c877a4…` release `6b90fc7a…` ledger `3b2b9e90…`.
- Runtime pins: CPython 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2 / SQLite 3.45.1 / OpenSSL 3.0.13 (unchanged all window).
- Recovery/terminal generations of interest: 29–32 (auth outage seals), `4f12ee0e` (recovery push), 33 (K2 c20), 34 (authorized reconcile), 35–37 (c20 completion), 38–42 (c21), 43–47 (c22), 48 (FINAL_FREEZE).
