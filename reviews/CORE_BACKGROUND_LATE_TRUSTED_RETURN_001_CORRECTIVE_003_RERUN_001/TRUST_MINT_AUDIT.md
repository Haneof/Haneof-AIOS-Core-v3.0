# TRUST_MINT_AUDIT — every path that can create durable trusted state (Route B)

Window `22-RERUN-001` · candidate branch `arena/01a101e0-haneof-aios-core-v3-0`
Method: exhaustive enumeration of every `INSERT` / `UPDATE` / `DELETE` against the five durable
background-return tables in `src/`, each attributed to its enclosing function, then a verdict on
whether a **local** caller can reach trusted state through it.

The five tables:

| table | meaning |
|---|---|
| `background_model_request_bindings` | `relay_id` + `outbound_request_fingerprint`, written before the handler runs |
| `background_model_return_verifiers` | public verifier material + full request scope + `consumed_at` |
| `background_model_response_receipts` | **trusted state**: the authenticity receipt |
| `background_model_return_handoffs` | **trusted state**: the exact-bytes handoff |
| `background_model_responses` | **trusted state**: the staged exact response |

---

## 1. Complete writer inventory

Enumerated mechanically from `src/aios_core/runtime/background_attempt.py` (the only module in
`src/` that writes these tables):

| line | statement | enclosing function | creates trusted state? |
|---|---|---|---|
| 466 / 559 / 582 | `CREATE TABLE IF NOT EXISTS …` | schema bootstrap | no — empty tables |
| 987 | `UPDATE background_model_response_receipts …` | `_migrate_legacy_authenticity_authority` (def @708) | **no** — see §3 |
| 992 | `UPDATE background_model_return_handoffs …` | `_migrate_legacy_authenticity_authority` | **no** — see §3 |
| 1007 | `UPDATE background_model_responses …` | `_migrate_legacy_authenticity_authority` | **no** — see §3 |
| 1453 | `INSERT INTO background_model_request_bindings` | `mark_dispatching` (def @1376) | no — routing fact, not authenticity |
| 1476 | `INSERT INTO background_model_return_verifiers` | `mark_dispatching` | no — binds **public** verifier material only |
| 2330 | `INSERT OR IGNORE INTO background_model_response_receipts` | `attach_late_trusted_return` (def @2140) | **YES** |
| 2379 | `INSERT OR IGNORE INTO background_model_return_handoffs` | `attach_late_trusted_return` | **YES** |
| 2416 | `UPDATE background_model_return_verifiers SET consumed_at` | `attach_late_trusted_return` | consumption marker (exactly-once) |
| 2747 | `INSERT OR IGNORE INTO background_model_responses` | `stage_exact_response` (def @2561) | **YES, conditionally** — see §4 |

**Conclusion: exactly two functions can create trusted rows, and exactly one is a trust root.**

* `attach_late_trusted_return` is the **only** trust root.
* `stage_exact_response` can only create a staged row for an attempt that **already has a valid
  receipt**, so it cannot originate trusted state.

No other module in `src/` writes these tables. `live_return.py` writes nothing at all — it holds
no connection, no store reference and no SQL.

## 2. The single trust root and its gate

`attach_late_trusted_return` performs, in order, before any `INSERT`:

1. payload decode; **full** `provider` / `model` / `provider_request_id` required;
2. `_response_fingerprint(directive)` and `payload_sha256` computed by Core, not supplied;
3. `_require_origin_binding(require_relay_echo=False)` against the durable pre-dispatch binding;
4. a verifier row must exist for the attempt;
5. the verifier row's scope must equal
   `(attempt_id, subject_id, work_kind, work_id, model_round_index,
   outbound_request_fingerprint, relay_id)`;
6. canonical `LateReturnVerifier` construction (canonical RSA encoding + parameter validation);
7. `late_return_message(...)` → `verify_late_return_proof(...)` with **public material only**;
8. if `consumed_at` is already set, the existing receipt + handoff must match (exactly-once).

Only then: `receipt_proof = _receipt_proof(**receipt_fields)`, **INSERT receipt + INSERT handoff +
COMMIT**, `UPDATE … consumed_at`, then `stage_exact_response`.

A local caller therefore needs a valid RSA signature over Core's own canonical message, produced
by the private half of a key whose **public** half Core bound before dispatch. Core never holds,
derives, caches or accepts the private half. There is no code path that accepts a
self-asserted "the handler returned this" claim: `register_handler_return` in the tombstone is an
inert no-op that records nothing anywhere.

## 3. The legacy migration cannot originate trusted state

`_migrate_legacy_authenticity_authority` (Corrective-002 / Window 17 positive) issues only
`UPDATE`s, never `INSERT`s. It converts a **pre-existing** legacy keyed-authenticator record into
the v2 shape, and it is:

* **verify-before-convert** — the legacy HMAC is verified first; an unauthenticated, tampered,
  inconsistent, transplanted or malformed legacy record fails closed;
* **atomic** — no partial rewrite;
* **secret-retaining on failure** — the legacy secret is not purged when conversion fails.

Because it cannot create a row, it cannot mint trust. Covered by CI job
`corrective-002-migration-rsa-positives` and by `CA2-005 … CA2-009`, and by frozen Suite B
(`IA20-MIGRATE-003`, `IA20-MIGRATE-004`) and W17 (`IA17-MIGRATE-001`, `IA17-MIGRATE-002`), all
green.

## 4. `stage_exact_response` cannot originate trusted state

`_verify_response_authenticity` (def @2461) runs before the staged `INSERT` and requires **all**
of:

1. a receipt row exists for the attempt — otherwise
   `BackgroundModelResponseConflict("trusted provider-return authenticity receipt is missing")`;
2. the stored receipt is internally consistent:
   `hmac.compare_digest(receipt.authenticity_proof, _receipt_proof(**receipt_fields))` —
   otherwise `"trusted provider-return receipt authenticator is invalid"`;
3. the supplied proof equals the stored receipt's proof — otherwise
   `"supplied provider-return authenticity proof is invalid"`;
4. the receipt binds the exact 15-tuple
   `(attempt_id, subject_id, work_kind, work_id, model_round_index,
   outbound_request_fingerprint, relay_id, provider, model, provider_request_id,
   response_fingerprint, payload_sha256)` — otherwise
   `"trusted provider-return receipt does not bind the exact attempt, request, provider
   identity, and response bytes"`.

Since (1) can only be satisfied by §2 or §3, `stage_exact_response` is a **consumer** of trusted
state, never a producer. `_receipt_message` / `_receipt_proof` remain class attributes because
frozen W17 probe `IA17-DOWNGRADE-001` calls them that way; retaining them is required and is not
a mint path (they are pure functions over caller-visible fields, and check (2) is what makes a
downgraded/forged receipt detectable).

## 5. Paths that were mint oracles and are now gone

| removed | old reachability | frozen probe that proved it |
|---|---|---|
| `record_live_provider_return` | public store method; also reachable via `store.__class__.record_live_provider_return.__globals__` | `IA20-MINT-003`, `IA20-OBJGRAPH-002` |
| `LiveProviderReturnWindow._issue` | classmethod; reachable via `._issue.__func__.__globals__` | `IA20-OBJGRAPH-002` |
| `open_live_provider_return_window` as an **authority** | public function ⇒ self-issuance | `IA20-MINT-003/004`, `IA20-WINDOW-001` (subcases `d_replay`, `g_other_world`, `j_detached_context` = `MINTED`) |
| `register_handler_return` as an **authority** | public function ⇒ self-declared handler return | `IA20-MINT-003` |
| `_OPEN_WINDOWS` / `_HANDLER_RETURNS` / `_ISSUE_SENTINEL` | module registries a self-issuer populated legitimately | `IA20-WINDOW-001` |
| `_capture_trusted_response_return` | private store method (removed earlier, by Window 17 `BLK-W17-001`) | `IA17-MINT-001/002` |
| `ModelResponseAuthenticator` / `model_response_authenticator` ctor hook | injectable object ⇒ caller-supplied "authenticator" | C3 matrix `C3-2-11` |
| `_capture_live_provider_return` / `_live_provider_return_window` | production call sites that armed the window | C3 matrix `C3-2-01`, `C3-2-13` |

The retained `open_live_provider_return_window` / `register_handler_return` / 
`LiveProviderReturnWindow` / `_ACTIVE_WINDOW` names are inert. They are retained **only** because
frozen Suite A calls them outside `try` blocks, so deleting them would crash the probe at import
or call time instead of exercising it. Suite A's `main()` has no `try/except` around
`probe_fn(root)`, which is what forces this shape. Suite A now reports
`probes=4 failures=0`, with every subcase `refused:AttributeError` (or `refused:TypeError` for
`e_copy` / `i_direct_ctor`).

## 6. Verifier-less attempts

With no bound verifier there is no scope to sign against and no verifier row to match, so
`attach_late_trusted_return` refuses. `record_response` can still close a live round, but per
§1 it creates no trusted row, so the round is permanently not recovery-eligible; and its
completion `UPDATE` matches `state='dispatching'` only, so once `admit()` has driven the attempt
to `in_doubt` it can never be completed locally. That is contract `C3-3`
("verifier-less attempt permanently `in_doubt`"), proven by frozen probe `IA20-MINT-004`
(`FORGED_ON_VERIFIERLESS_ATTEMPT_VIA_PUBLIC_WINDOW` — now refused), by C3 matrix case
`C3-3-01`, and by `test_cg003_assistant_output_persistence_failure_remains_in_doubt`.

## 7. Residual risk (disclosed, out of scope, pre-existing)

A fresh-process caller invoking `store.record_response` **directly** on a `dispatching`
verifier-less attempt, before any `admit()` forced `in_doubt`, can close that round with
caller-supplied provider identity.

Bounded impact:

* mints **no** receipt, **no** handoff, **no** staged row ⇒ the round is permanently **not
  recovery-eligible**;
* its bytes can never be replayed as an exact provider reply;
* it cannot poison an external authority — a later genuine external proof **supersedes** the
  unverified provenance (see `DESIGN_SECURITY_MODEL.md` §4);
* it cannot move a verifier-less attempt out of `in_doubt` once admission has run.

Pre-existing on live main `1541b1ec…` and on the frozen failed candidate `fec30bd1…` for
anonymous directives. Not fixed here: fixing it would change the live completion contract for
every verifier-less round, which is outside Corrective-003's frozen scope. Classification:
`INHERITED_OBSERVATION / NOT_NEW_CORRECTIVE003_REGRESSION`-adjacent residual risk, disclosed for
the next reviewer.

## 8. Mechanical enforcement

The formal workflow job `scope-discipline-and-identity-guard` re-proves this audit on every run:

* (a) no removed mint symbol may be **defined** (`def`/`class`), **assigned** or **imported**
  anywhere under `src/`;
* (b) an isolated, dependency-free load of the tombstone asserts it exposes none of the
  forbidden attributes, that the decommission marker is `True`, that the snapshot reports
  `open_windows == 0`, `pending_handler_returns == 0`, `trust_conferred == False`,
  `armed_on_this_stack == False` and
  `durable_trusted_return_authority == "external_verifier_plus_genuine_proof_only"`, that
  `LiveProviderReturnWindow` has no `_issue`, that its ctor raises `TypeError`, and that every
  non-copyable / non-serializable hook is still defined;
* (c) no Core authorization module may reference the tombstone at all.

The guard is semantic rather than textual on purpose: the tombstone's history docstring and one
history comment in `cognitive_runtime.py` legitimately **name** the removed machinery to document
why it is gone, and a plain `grep` would either fail on correct documentation or have to be
weakened.
