# INHERITED_OBSERVATIONS — section 10 disclosure

Window `22-RERUN-001` · Task `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-003`

Contract section 10 requires one specific observation to be classified, disclosed and **not**
fixed, because fixing it would expand scope beyond the frozen Corrective-003 contract.

---

## Observation 1 — receipt/handoff and verifier consumption commit before `stage_exact_response`

| item | value |
|---|---|
| classification | `INHERITED_OBSERVATION / NOT_NEW_CORRECTIVE003_REGRESSION` |
| location | `src/aios_core/runtime/background_attempt.py`, `BackgroundModelAttemptStore.attach_late_trusted_return` (def @ line 2140 on the candidate) |
| present in the frozen failed candidate? | **YES** — `fec30bd1495017bf13f08b0ef5b1e241dfb0e247`, identical statement order |
| fixed in this window? | **NO** — deliberately, per section 10 |
| scope impact of fixing | would change the commit boundaries of the only trusted-return writer, i.e. Corrective-002 behaviour that Window 17 and Window 20 already accepted |

### The ordering, mechanically

Candidate (`30022b06` tree):

```
2330:  INSERT OR IGNORE INTO background_model_response_receipts(
2379:  INSERT OR IGNORE INTO background_model_return_handoffs(
2416:  UPDATE background_model_return_verifiers   (SET consumed_at = …)
2431:  conn.commit()
2433:  return self.stage_exact_response(
```

Frozen failed candidate `fec30bd1…`, same function, same order:

```
2301:  INSERT OR IGNORE INTO background_model_response_receipts(
2350:  INSERT OR IGNORE INTO background_model_return_handoffs(
2387:  UPDATE background_model_return_verifiers
2402:  conn.commit()
2404:  return self.stage_exact_response(
```

So the receipt, the exact-bytes handoff and the verifier-consumption marker are all **committed**
before the staged exact response is written by a separate call. A crash between line 2431 and the
completion of `stage_exact_response` therefore leaves a durable, fully verified receipt + handoff
with **no** staged row.

### Why this is safe, and why it is still worth recording

The intermediate state is fail-closed, not fail-open:

* `pending_exact_response` requires a staged response, so recovery refuses rather than
  improvising;
* `recover_trusted_handoff` reads the handoff and requires all earlier rounds `metered`;
* re-running `attach_late_trusted_return` with the same genuine proof is idempotent: the verifier
  row already has `consumed_at`, so the method requires the existing receipt + handoff to match
  and then proceeds to stage — which is the exactly-once path frozen W17 probe
  `IA17-EXACTONCE`/`IA20-EXACTONCE-001` and `CA2-015` exercise;
* the receipt and handoff are `INSERT OR IGNORE`, so a replay cannot duplicate them.

No probe in Suite A, Suite B or W17 fails because of this ordering, and no case in the 27-case C3
author matrix turns it into a mint path: the trusted rows it commits can only have been produced
by a verified external signature.

### Where it did bite this window — and the design consequence

This ordering is exactly why an earlier Route B draft was wrong. That draft gated
`record_response` and `stage_exact_response` on a boolean `has_verified_receipt(attempt_id)`:
"if a verified receipt already exists, refuse to supersede the durable provenance."

Because `attach_late_trusted_return` commits the receipt **before** staging, that boolean was
already `True` by the time `stage_exact_response` ran inside the same genuine call. The gate
therefore blocked the genuine external return from correcting the unverified provenance that a
prior local live completion had written — i.e. a *forged local return could poison a later
genuine external return*, which is the opposite of the required property.

The shipped design replaces the boolean with a **proof comparison**:

```python
verified_conflicting_receipt = (
    verified_receipt_row is not None
    and str(verified_receipt_row["authenticity_proof"]) != str(supplied_authenticity_proof).strip()
)
```

* a *differing* verified receipt ⇒ strict `BackgroundModelResponseConflict`
  (first-writer-wins for verified state, unchanged from Corrective-002);
* a *matching* verified receipt (normally the one this same genuine proof just committed) or no
  receipt at all ⇒ `supersedes_unverified_local`, a provenance-correcting `UPDATE` that does not
  demote `response_returned` / `metered`.

The absence of a receipt row is itself the durable, unforgeable marker that provenance on the
attempt row was written by an unverified local completion. See `DESIGN_SECURITY_MODEL.md` §4 and
`TRUST_MINT_AUDIT.md` §4.

This is recorded here because it is the one place where the inherited ordering materially shaped a
Corrective-003 design decision. The ordering itself was left untouched.

### Test coverage that pins the behaviour as-is

* `tests/integration/test_core_background_trusted_return_adversarial_001.py::test_forged_local_return_cannot_poison_a_later_genuine_external_return`
  — new in this window; asserts the supersession property directly.
* `tests/integration/test_core_background_response_recovery_001.py::test_case_04c_staged_bytes_must_match_durable_attempt_provenance`
  — asserts a live completion mints no receipt and no staged row, that differing bytes are
  refused, and that genuinely-proven exact bytes stage and restage effect-free.
* `tests/integration/test_core_background_late_trusted_return_corrective_002.py::test_ca2_015_concurrent_attach_yields_one_canonical_winner`
  — first-writer-wins under concurrency, unchanged.
* Frozen Suite B `IA20-EXACTONCE-001` and frozen W17 `IA17-*` exactly-once probes — unchanged and
  green.

---

## Observation 2 — residual local live-completion provenance on verifier-less attempts

| item | value |
|---|---|
| classification | `INHERITED_OBSERVATION / NOT_NEW_CORRECTIVE003_REGRESSION` (pre-existing on live main and on `fec30bd1`) |
| location | `BackgroundModelAttemptStore.record_response` |
| fixed in this window? | **NO** — outside the frozen Corrective-003 scope |

A fresh-process caller that invokes `store.record_response` **directly** on a `dispatching`
attempt with **no bound verifier**, before any `admit()` has forced it to `in_doubt`, can close
that round with caller-supplied provider identity.

Bounded impact — this is **not** the `BLK-W20-001` class of failure:

* it mints no receipt, no handoff and no staged row, so the round is permanently **not
  recovery-eligible** and its bytes can never be replayed as an exact provider reply;
* it cannot poison an external authority: a later genuine external proof supersedes the unverified
  provenance;
* it cannot move a verifier-less attempt out of `in_doubt` once admission has run, because the
  completion `UPDATE` matches `state='dispatching'` only.

It is a liveness / provenance-hygiene concern about a local live completion, not a trust-mint
oracle. Full analysis in `DESIGN_SECURITY_MODEL.md` §6 and `TRUST_MINT_AUDIT.md` §7.

---

## Non-observations (checked and found absent)

* No new `ContextVar`, registry, sentinel or classmethod was introduced by Route B. The tombstone
  keeps one inert diagnostics `ContextVar` (`_ACTIVE_WINDOW`) that no authorization decision
  reads; the formal workflow asserts the tombstone reports `open_windows == 0` and
  `pending_handler_returns == 0`, i.e. no registry survives at all.
* No reviewer probe bytes were modified, wrapped or copied into the tracked tree (`C3-6`).
* No historical Window 14 / 17 / 20 review evidence was touched (`out_of_scope = 0`,
  `forbidden_paths = 0`).
* No C15 persistence or preflight path was touched. Route B's effect on the C15 operator harness
  is classified `DOWNSTREAM_OPERATOR_COMPATIBILITY_DEBT`; unsafe live self-trust was **not**
  restored to make C15 green, and `tests/c15_persistence/**` is not part of the Core gate.
