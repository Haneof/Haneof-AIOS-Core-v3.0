# CORE-BACKGROUND-LATE-TRUSTED-RETURN-001 — design note and trust-boundary record

Task: `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001` (WINDOW 13)
Baseline: live `main` `25591825d88e98f30dfd3de1c7e7cbc6e53267dd`
Binding authority: `governance/C15_RCC_RES_B_ACCEPT_003_FAILURE_ADJUDICATION_2026-09-30.md` §11 (C1–C5)

---

## 1. The two failure classes this closes

### Class A — a trusted external return arrives after the Core process died

Frozen sequence (adjudication §5, source-verified at baseline):

1. Core admits a durable attempt, crosses the dispatch boundary, commits
   `background_model_request_bindings` in the **same transaction** as
   `admitted → dispatching`, before the provider handler runs.
2. The Core process dies. No `background_model_response_receipts` row exists,
   because receipts are minted only by the private in-process trusted-return
   callback `_capture_trusted_response_return`.
3. Restart: `admit()` converts `dispatching → in_doubt` and raises
   `BackgroundModelExecutionInDoubt` **before** the model handler, so that callback
   is unreachable for that round forever.
4. The external trusted responder finishes the exact response **after** the death.

At step 4 baseline Core had no legal attach path, and its only remaining exit was
the class-B false state.

### Class B — a post-dispatch `not_submitted` false state was writable

`reconcile_not_submitted(...)` was callable for `dispatching` / `in_doubt` attempts
and its only guard was *absence of a trusted-return receipt*. That made
«I have no return evidence» into «therefore the request was never submitted» —
the exact enabler of `IA-B-R003-BLK-002`.

---

## 2. The trust root for the late return

### Chosen mechanism: a pre-issued, single-use, per-attempt return capability

```text
   Core (dispatch boundary)                        External responder
   ------------------------                        ------------------
   mark_dispatching()  ── commits attempt state 'dispatching'
                      └─ commits background_model_request_bindings
                         (outbound_request_fingerprint, relay_id)
                                            ┌──  _issue_external_return_capability()
   nonce = random 32 bytes  ── persisted ───┘
        │
        └── handed ONCE to the registered ExternalReturnObserver
                │
                │   ... Core process dies here ...
                │
                └── observer receives the real external response AFTER the death
                        │
                        capability.prove_external_return(directive)
                          = HMAC-SHA256(nonce, canonical(binding ‖ response))
                        │
                        └── proof + exact bytes handed to the recovery caller
                                                          │
   Core verifies:  recompute HMAC under the stored nonce,
                   compare_digest against the supplied proof,
                   and compare every binding field against the DURABLE row
                                                          │
                   commit receipt + exact-bytes handoff atomically
```

### Why this is not a signing oracle

`arbitrary recovery caller + response bytes + caller-computable metadata`
**≠** trusted return. Concretely:

| route a recovery caller might try | why it fails |
|---|---|
| supply correct bytes, invent a proof | the proof is an HMAC under a nonce the caller never sees; the store recomputes and `compare_digest`s it |
| supply correct bytes, compute every binding field itself | every binding field is compared against the **durable pre-dispatch row**, never against caller metadata; and they are all inside the MAC |
| ask Core for the capability | `_issue_external_return_capability` is **private**, exactly like `_capture_trusted_response_return`; it is wired only as the runtime's dispatch-time issuer. A test asserts it is absent from the public surface |
| ask Core to mint a receipt for bytes | no such public API exists. `attach_late_trusted_return` mints a receipt **only** after the capability proof verifies |
| reuse a leaked capability for another attempt | the MAC message pins `attempt_id`, `subject_id`, `work_kind`, `work_id`, `model_round_index`, `outbound_request_fingerprint`, `relay_id`; Core recomputes the expected proof for the *presented* attempt and the values differ |
| use a leaked capability twice | the capability is single-use (`consumed_at` is set in the same transaction as the receipt); a second presentation is only honoured as deterministic exact recovery of the identical durable bytes, never as a new effect |
| replay an old proof into a new run/subject/round | the durable binding and the durable attempt must both match; a transplanted row is rejected by `_require_origin_binding` and the identity comparison |

**Residual, explicitly stated.** A capability holder (the registered observer) can
mint exactly one return for exactly one attempt. That is inherent to any design in
which an external party proves its own return, and it is the same trust domain as
the provider call itself. It is bounded to: one attempt, one round, one originating
request, one response, once. It is not, and cannot become, a general signer.

**Trust boundary that remains Core-private.** `background_model_authenticity_authority`
(the receipt HMAC key) is untouched: still store-private, still never returned by an
API, still only used after a capability proof verifies, and still never attached to a
`RuntimeSnapshot`, evidence, or metering. The capability nonce is a *separate* secret.

### The nine required questions

1. **Who produces the proof?** The registered `ExternalReturnObserver` — the
   provider/relay adapter that Core dispatched to and that actually observed the
   external return — via `BackgroundModelReturnCapability.prove_external_return`.
2. **Why can a recovery caller not forge it?** It never holds the per-attempt
   nonce, and the nonce is reachable only from the private dispatch-time issuer and
   the Core-private database. A test enumerates the entire public store surface and
   asserts no member accepts or returns a nonce.
3. **When is it produced?** At the moment the observer receives the real external
   response — which in the target failure shape is *after* the Core process died, so
   the artifact is contemporaneous with the return rather than reconstructed later.
4. **How is it bound to the original outbound request?** The MAC message contains
   `outbound_request_fingerprint` and `relay_id` taken from the durable
   `background_model_request_bindings` row written at dispatch, and Core rejects the
   attach if that row is not internally consistent with its own derived relay id.
5. **Is it one-attempt / one-round?** Yes — both are inside the MAC message, and the
   capability row is keyed by `attempt_id`.
6. **Does substituting the response still pass?** No — `response_fingerprint` and
   `payload_sha256` are inside the MAC message, and the payload is strictly decoded
   (duplicate JSON keys rejected at every level) and re-fingerprinted by Core.
7. **Do cross-run / cross-subject / cross-round transplants fail?** Yes — all
   asserted in `test_ltr_r4_*` and `test_a3_every_attack_fails_closed`.
8. **Does replaying an old proof fail?** It cannot produce a second effect: the
   capability is consumed, and the downstream metering / capability / World / output
   / ACK effects remain the accepted R5 exactly-once path.
9. **Does a leak become a signing oracle?** No — see the table above and
   `test_ltr_r9_leaked_capability_cannot_mint_a_proof_for_another_attempt` /
   `test_a1_capability_issuer_is_not_publicly_callable`.

Nothing is hard-coded to `req-0039` or to any C15 identifier. The mechanism is a
general Core contract keyed on durable attempt identity.

---

## 3. Exact binding requirements

`late_return_message()` requires every one of these and raises if any is missing —
it never fills a placeholder:

```text
aios.background-model-late-return.v1
  attempt_id                     <- durable attempt
  subject_id                     <- durable attempt
  work_kind                      <- durable attempt
  work_id                        <- durable attempt
  model_round_index              <- durable attempt
  outbound_request_fingerprint   <- durable pre-dispatch binding
  relay_id                       <- durable pre-dispatch binding
  provider                       <- observed at the trusted return boundary
  model                          <- observed at the trusted return boundary
  provider_request_id            <- observed at the trusted return boundary
  response_fingerprint           <- recomputed by Core from the exact bytes
  payload_sha256                 <- recomputed by Core from the exact bytes
```

**Anonymous / external transports with no provider identity.** No string is
fabricated. `prove_external_return()` and `attach_late_trusted_return()` both refuse
when provider, model or provider_request_id is absent, so an anonymous transport is
governed by its own trust model: *legal, but never recoverable via this path.*
`provider_identity()` returns `None` components rather than placeholders, and
`test_ltr_r8_*` / `test_a4_*` freeze that.

---

## 4. `not_submitted` — frozen new semantics

```text
not_submitted  ⇔  Core holds mechanical, trustworthy evidence that this attempt
                  never crossed the semantic/provider dispatch boundary.
```

`reconcile_not_submitted` is now legal **only** from a pre-dispatch Core-owned
state with no originating-request binding. Two guards, both Core-owned and
mechanical:

1. a durable `background_model_request_bindings` row exists, or the attempt is
   `dispatching` / `in_doubt` → **refused** (that row is written in the same
   transaction as `admitted → dispatching`, before the handler runs, and is never
   caller-supplied);
2. an authenticated receipt exists → **refused** (the accepted guard, retained).

Explicitly *not* accepted as proof of non-submission: no receipt, no response, a
timeout, a caller/operator statement, "the request may not have been delivered", or
"recovery needs to continue". `test_ns_r2_false_state_cannot_be_written_even_with_a_verbose_justification`
drives exactly that list.

**After the dispatch boundary, Core fails closed.** The attempt converges only
through (a) a legitimate trusted late-return attach, or (b) a transport-specific
mechanically safe reattach/poll. It never recovers by writing a false state.

### Deliberately unchanged, with justification

`mark_failure(definitely_not_submitted=True)` is retained. It is not the
recovery-facing reconciliation path; it is the **in-process typed contract**
`ModelDispatchNotSubmitted`, raised synchronously by Core's own configured model
handler at the dispatch site, while the process is alive. It is the accepted
FIX-002/CG003 semantic and is frozen by existing Core tests
(`test_definitely_not_submitted_can_retry_same_attempt_identity`,
`test_core_background_response_recovery_001.py:1009`,
`test_turn_execution_recovery.py::test_cg003_known_not_submitted_requires_explicit_retry_authorization`).
Removing it would break accepted invariants the adjudication told us to preserve.
It is now one of exactly two legal routes to `not_submitted`, alongside the
pre-dispatch reconciliation, and both are mechanically gated.

Historical rows and sealed generations are never rewritten: this change only
refuses new writes.

---

## 5. Two accepted tests updated, coherently (adjudication C2 requires "with tests")

Both asserted the now-retired post-dispatch reconciliation. Each was rewritten so
that everything it actually protects is preserved and the retired shape is asserted
*refused*:

| test | preserved | added |
|---|---|---|
| `tests/runtime/test_background_model_attempt.py::test_background_model_attempt_reconciliation_keeps_same_identity_and_non_world_revision` | same attempt identity across reconcile → re-admit → dispatch → response → meter; World revision untouched; restart durability; full lifecycle to `metered` | the post-dispatch `in_doubt` attempt is refused and stays `in_doubt` with `reconciliation_evidence IS NULL` |
| `tests/runtime/test_turn_execution_recovery.py::test_cg003_reconciled_not_submitted_attempt_can_be_authorized_after_restart` | renamed to `..._not_submitted_...`; a `not_submitted` turn can still be authorized after a restart and re-run to completion | reached through the still-legal typed in-process contract; a **new** test `test_cg003_post_dispatch_reconciliation_is_refused_after_restart` asserts the retired shape fails closed, the turn stays `in_doubt`, and `authorize_turn_retry` / `run_turn` both refuse |

No expected outcome was weakened to make a test pass; the removed assertions are
the ones the adjudication retires.

---

## 6. Preserved accepted invariants (C3)

Unchanged and re-proved by the existing suites:

- no caller-supplied bytes → trusted receipt (only the capability proof opens the path);
- metadata-only `reconcile_response` stays permanently disabled;
- no provider redispatch across the boundary;
- R5 remains *exactly-once durable effect*, not "never re-enter the function";
- conflicting / duplicate replay stays fail-closed;
- stronger terminal receipts (durable assistant output, delivery, completed
  execution, completed Wake) still short-circuit and never re-enter the model path —
  `test_a3_..._late_proof_for_completed_stronger_terminal_receipt` and the accepted
  `test_r5_d_terminal_receipt_bypasses_all_runtime_replay`;
- the five historical replay families (`propose_goal`, `form_event`, `propose_entity`,
  `propose_dimension`, `propose_cognitive_policy`) are untouched and green.

## 7. No second truth store (C5 / rule 24)

The new durable artifact is `background_model_return_capabilities`: attempt
identity, the binding fields, the nonce, and a consumption timestamp. It holds **no
response bytes and no semantic state**. The trusted receipt and the exact-bytes
handoff are written into the *existing* `background_model_response_receipts` and
`background_model_return_handoffs` tables, and the late return is promoted through
the *existing* `stage_exact_response` verification path, so there is exactly one
verification route and no second semantic truth store. `BackgroundModelAttemptStore`
is not bypassed and the ordinary `FusedTurnRuntime` continuation performs the
single metering / capability / World / output / ACK effects.

## 8. Anonymous / local handlers (rule 17)

Not auto-upgraded. A capability is issued only when the embedder explicitly registers
`external_return_observer`; the default is `None`, so `background_model_return_capabilities`
stays empty and the late-return path is mechanically unavailable — fail closed.
Double protection: even a registered observer cannot produce a proof for an anonymous
return. This is why the real C15 anonymous handler behaviour is unchanged.

## 9. Scope discipline (C5)

Changed: `src/aios_core/runtime/{late_return.py (new), background_attempt.py,
turn_runtime.py, __init__.py}`, the probe files, two updated accepted tests, and one
new CI workflow. **Not touched**: `tools/c15_preflight/**`,
`tools/c15_persistence/**`, `evidence/w08/**`, PR #302, the Window 10 review, the
transport commit, the persistence ref, generations 1..48, and any run evidence. No
Resident was run and no cursor was revealed.
