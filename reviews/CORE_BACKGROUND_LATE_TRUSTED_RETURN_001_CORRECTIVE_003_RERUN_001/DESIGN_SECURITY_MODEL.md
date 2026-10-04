# DESIGN_SECURITY_MODEL — Route B (Corrective-003 / Window 22-RERUN-001)

Blocker closed: `BLK-W20-001`
= `RECOVERY_CALLER_TRUSTED_RETURN_MINT_ORACLE_VIA_SELF_ISSUED_EPHEMERAL_WINDOW`,
root cause `TRUST_AUTHORITY_ISSUANCE_REMAINS_CALLER_MANUFACTURABLE`.

PM design ruling implemented: **Route B** — remove the local self-trusting provider-return
authority entirely. Durable trusted late return depends **only** on a durable external
verifier plus a genuine external cryptographic proof. Python object identity may act at most
as a consistency/sequencing guard, **never** as an authenticity authority.

---

## 1. What was removed

| removed symbol | where it lived | why it was a trust root |
|---|---|---|
| `BackgroundModelAttemptStore.record_live_provider_return` | `runtime/background_attempt.py` (187 lines) | public store method that turned caller-supplied bytes plus a window into a durable receipt + handoff |
| `LiveProviderReturnWindow._issue` | `runtime/live_return.py` | classmethod issuance path, reachable via `__func__.__globals__` |
| `consume_live_provider_return_window` | `runtime/live_return.py` | consumption half of the same authority |
| `_ISSUE_SENTINEL`, `_OPEN_WINDOWS`, `_HANDLER_RETURNS` | `runtime/live_return.py` | registry + sentinel + handler-return identity map: the "guards" a self-issuing caller simply satisfied |
| `CognitiveRuntime._live_provider_return_window` and its ctor parameter `model_response_authenticator` / `ModelResponseAuthenticator` | `runtime/cognitive_runtime.py` | an injectable authenticator hook and the frame that armed the window |
| `TurnRuntime._capture_live_provider_return` and its wiring | `runtime/turn_runtime.py` | the production call site of the writer |

`src/aios_core/runtime/live_return.py` is retained as an **inert tombstone**. It holds no
authority: nothing in Core reads anything defined there to make an authorization decision.
The historical public names are retained *only* so the frozen third-party reviewer probes —
which import them by name and call them outside `try` blocks — remain executable
byte-for-byte. Each is a documented inert no-op:

* `open_live_provider_return_window(attempt_id=…)` — context manager yielding an inert marker;
  arms nothing;
* `register_handler_return(window, directive)` — inert no-op, records nothing;
* `LiveProviderReturnWindow` — never constructible (`TypeError`), never copyable, never
  serializable, carries no state any Core code reads;
* `_ACTIVE_WINDOW` — inert diagnostics `ContextVar`, **never** consulted by any authorization
  decision;
* `live_return_authority_snapshot()` — read-only diagnostics reporting
  `decommissioned=True`, `route="B"`, `open_windows=0`, `pending_handler_returns=0`,
  `armed_on_this_stack=False`, `trust_conferred=False`,
  `durable_trusted_return_authority="external_verifier_plus_genuine_proof_only"`;
* `LOCAL_LIVE_RETURN_AUTHORITY_DECOMMISSIONED = True` — a public, non-secret marker so audits
  can assert mechanically that Route B is in force instead of trusting a docstring;
* `LiveReturnAuthorityError` — the fail-closed refusal exception still raised by Route B writers.

No Core authorization module (`background_attempt`, `turn_runtime`, `cognitive_runtime`,
`late_return`) references the tombstone at all; the formal workflow enforces this.

## 2. The only remaining route to durable trusted return

```
durable external verifier bound BEFORE the provider boundary
        +
genuine external cryptographic proof over that verifier
        ↓
BackgroundModelAttemptStore.attach_late_trusted_return(...)
```

Durable tables involved:

| table | role |
|---|---|
| `background_model_request_bindings` | `relay_id` + `outbound_request_fingerprint`, written by `mark_dispatching` **always**, before the handler runs |
| `background_model_return_verifiers` | public verifier material + full request scope + `consumed_at`; bound at dispatch |
| `background_model_response_receipts` | the trusted receipt; only `attach_late_trusted_return` writes it |
| `background_model_return_handoffs` | exact-bytes handoff for recovery |
| `background_model_responses` | staged exact response |

`attach_late_trusted_return` sequence (unchanged from Corrective-002, still the only writer):

1. decode the payload; require a **full** provider/model/request_id;
2. compute `_response_fingerprint(directive)` and `payload_sha256`;
3. `_require_origin_binding(require_relay_echo=False)` against the durable pre-dispatch binding;
4. require a verifier row, and require its scope to equal
   `(attempt_id, subject_id, work_kind, work_id, model_round_index,
   outbound_request_fingerprint, relay_id)`;
5. build the canonical `LateReturnVerifier`, form `late_return_message(...)`, and
   `verify_late_return_proof` with **public material only**;
6. if `consumed_at` is already set, require the existing receipt + handoff (exactly-once);
7. compute `receipt_proof = _receipt_proof(**receipt_fields)`;
8. **INSERT receipt + handoff and COMMIT**;
9. `stage_exact_response`.

`_STAGABLE_STATES = {dispatching, in_doubt, response_returned, metered}`.
`recover_trusted_handoff` reads the handoff and requires all earlier rounds `metered`;
`pending_exact_response` requires a staged response.

## 3. Why a live local return is no longer a trust root

`record_response` now:

1. writes **only** the live completion transition (`dispatching` → `response_returned`) plus
   the round's *unverified* live provenance;
2. creates **no** receipt, **no** handoff and **no** staged exact response — so the round it
   closes is permanently **not recovery-eligible**: no caller can later adopt arbitrary bytes
   for it, and a local completion can never be replayed as an exact provider reply;
3. is **refused** when durable trusted-return rows already exist for the attempt. Those rows
   can only have been created by genuine external proof, so a local completion can never race
   or replace them — first-writer-wins for the external authority;
4. cannot complete an attempt already driven to `in_doubt`: the completion `UPDATE` matches
   `state='dispatching'` only. `admit()` on an unresolved `dispatching` attempt therefore makes
   it permanently `in_doubt` (`BackgroundModelExecutionInDoubt`), which is contract `C3-3`.

## 4. Supersession: why a forged local return cannot poison a genuine external return

This is the subtle part of Route B, and it replaced an earlier, wrong design ("gate 1": refuse
`record_response` whenever a verifier was bound).

Because a receipt row can now only have been created by genuine external proof, **the absence
of a receipt row is itself the durable, unforgeable marker** that any provider provenance
already on the attempt row was written by an *unverified* local live completion and carries no
authenticity. `stage_exact_response` therefore:

* reads `verified_receipt_row` for the attempt;
* computes `verified_conflicting_receipt` = a receipt exists **and** its
  `authenticity_proof` differs from the supplied proof;
* when the attempt is `response_returned`/`metered` and the supplied identity differs from the
  durable provenance:
  * if `verified_conflicting_receipt` → `BackgroundModelResponseConflict`
    (strict first-writer-wins for **verified** state, unchanged from Corrective-002);
  * otherwise → `supersedes_unverified_local = True`, and a provenance-correcting `UPDATE`
    runs that does **not** demote `response_returned`/`metered`.

Net effect: a local caller cannot block, corrupt or pre-empt a later genuine RSA trusted
return, and a genuine external return cannot overwrite another *verified* return.

Note the ordering consequence: `attach_late_trusted_return` commits the receipt **before**
staging, so a matching receipt at step 9 is normally the one this same genuine proof just
created. That is inherited observation 1 — see `INHERITED_OBSERVATIONS.md`. It is also exactly
why the earlier `has_verified_receipt` formulation was wrong and had to become a
proof **comparison**.

## 5. Contract compliance map

| contract | how it is satisfied | mechanical evidence |
|---|---|---|
| `C3-1` no caller-manufacturable authority | the writer, the issuance classmethod, the registry, the sentinel and the handler-return map are deleted, not guarded | C3 matrix cases `C3-1-01…13`; workflow guard steps (a)(b)(c) |
| `C3-2` reflection-proof | no forbidden symbol is defined, assigned or imported anywhere under `src/`; no reachable `__globals__`, closure cell, default, descriptor, `sys.modules` entry, exception frame or object-graph node holds one | C3 matrix cases `C3-2-01…13` |
| `C3-3` verifier-less attempt permanently `in_doubt` | `record_response`'s `UPDATE` matches `state='dispatching'` only; `admit()` forces `in_doubt` | C3 matrix `C3-3-01`; `test_cg003_assistant_output_persistence_failure_remains_in_doubt`; `IA20-MINT-004` |
| `C3-4` exact-bytes binding cannot self-assert | `register_handler_return` records nothing; only a signature over the durable binding is accepted | C3 matrix `C3-1-01`, `C3-1-08`; Suite A `4/0` |
| `C3-5` Corrective-002 positives preserved | W17 `14/0`, Suite B `7/0`, migration/RSA/exactly-once/SIGKILL suites green | `raw/GREEN_W17_ON_CANDIDATE_v2.txt`, `raw/GREEN_SUITE_B_ON_CANDIDATE_v2.txt`, CI jobs 4/5/8/9 |
| `C3-6` reviewer probe bytes unchanged | probes are extracted from the pinned review commits at run time and never copied into the tracked tree | `PROBE_MANIFEST.md`; CI job 1 |
| `C3-7` hygiene closure | cross-world / cloned DB / cloned store / detached ContextVar / copied context / other thread / other task / stale / reused / nested / reentrant / exception / cancellation / fork / SIGKILL / fresh process all leave `(0,0,0)`, and no residual armed state denies a genuine return | `test_core_background_trusted_return_adversarial_001.py` (27 cases) |
| `C3-8` scope discipline | `out_of_scope = 0`, `forbidden_paths = 0` | `SCOPE_AUDIT.md`; CI job 11 |

## 6. Residual risk (disclosed, not fixed — out of scope)

A **fresh-process** caller that invokes `store.record_response` directly on a `dispatching`
attempt with **no bound verifier**, *before* any `admit()` has forced it to `in_doubt`, can
close that round with caller-supplied provider identity.

Why this is not the `BLK-W20-001` class of failure:

* it mints **no** receipt, **no** handoff and **no** staged response;
* the round therefore becomes permanently **not recovery-eligible** — its bytes can never be
  replayed as an exact provider reply;
* it cannot poison an external authority: a later genuine external proof supersedes the
  unverified provenance (section 4);
* it cannot make a verifier-less attempt recoverable, and it cannot mint trust that any
  recovery path will honour.

It is a *liveness/provenance-hygiene* concern about a local live completion, not a trust-mint
oracle. It existed on live main and on the frozen failed candidate `fec30bd1` for anonymous
directives. Fixing it would require changing the live completion contract for every verifier-less
round, which is outside Corrective-003's frozen scope. Recorded here and in `TRUST_MINT_AUDIT.md`
so the next reviewer does not have to rediscover it.

## 7. Python object identity ruling

Per the frozen design ruling, object identity is at most a consistency/sequencing guard. In
this implementation it is used for **nothing**:

* the tombstone keeps no identity-bearing state at all — there is no registry to compare
  against;
* `RouteBExternalSigner` / `ExternalSigner` in tests hold signing contexts keyed by
  `attempt_id`, which is the *external* side's own bookkeeping, not a Core authorization input;
* Core's authorization input is the durable verifier row plus the RSA proof, both of which are
  data, not object identity.

Consequently object identity cannot mint a receipt, mint a handoff, establish provider
authenticity, make caller bytes trusted, make bytes recovery-eligible, move a verifier-less
attempt out of `in_doubt`, or replace RSA/external proof. C3 matrix case `C3-1-08` proves this
by running a real live turn whose handler returns the exact object and asserting zero trusted
rows afterwards.

## 8. Downstream operator compatibility debt

C15 harness failures caused by Route B are classified
`DOWNSTREAM_OPERATOR_COMPATIBILITY_DEBT`. Unsafe live self-trust was **not** restored to make
C15 green. `tests/c15_persistence/**` is not part of the Core gate and is on the forbidden-path
list; it is untouched by this window.
