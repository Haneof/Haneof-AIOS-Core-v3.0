# Signing-oracle analysis — BLK-W14-001 / BLK-W14-002

Candidate: `5ad0524c425592210ff184e00ad52abb2c14e366` · WINDOW 14

## Threat model as mandated (task §8–§11)

A recovery caller knows: attempt id, subject, work kind/id, round, request
fingerprint, relay id, provider, model, provider request id, response digest —
everything caller-computable. It must be unable to turn arbitrary response bytes
into a trusted return.

## Route 1 — issuer reachability (BLK-W14-001)

```
ordinary recovery object
  └─ runtime.background_model_attempts          # PUBLIC attribute, turn_runtime.py:372
       └─ ._issue_external_return_capability(    # underscore = convention ONLY
            attempt_id, issued_at=now)          # background_attempt.py:1570
            ├─ accepts state ∈ {dispatching, in_doubt}   # :1620 — works AFTER death
            ├─ requires only the durable binding (which exists by construction post-dispatch)
            └─ if row exists: returns _capability_from_row(existing)  # :1645-1655
                 └─ BackgroundModelReturnCapability(..., capability_nonce=nonce)  # :1688-1704
                      └─ .prove_external_return(forged_directive) -> bglate_v1_...
                           └─ attach_late_trusted_return(...) -> trusted receipt+handoff
```

The mandated test (§10) — original process dies, attempt `in_doubt`, fresh process
with ordinary recovery runtime/store, attempt to re-obtain proof authority through
the normal object graph — **succeeds**. Frozen probe `IA14-ORACLE-001`:

```
CAPABILITY REISSUED and arbitrary bytes staged for bgattempt_dedeb5127fd3921062ff3123e5da9c0b
```

Why the author's proof is insufficient (§9):

| author claim | reality |
|---|---|
| "issuer is private like `_capture_trusted_response_return`" | Python `_` is naming convention, not access control; the method is a plain bound method on an object recovery code already holds |
| `test_a1_capability_issuer_is_not_publicly_callable` | asserts only that `issue_external_return_capability` (no underscore) is absent from `dir()` — never touches the underscore method |
| `test_a1_recovery_caller_cannot_self_issue_a_capability` | asserts `AttributeError` for the *no-underscore* name only |
| "never returned by a recovery API" | true of the *public* API surface, false of the object graph: `runtime.background_model_attempts._issue_external_return_capability(...)` returns the full capability **including the nonce** |

No monkeypatching, no reflection beyond plain attribute access, no SQL was needed.
The frozen probe deliberately reaches the issuer through the normal object graph
precisely because §9 forbids treating the underscore as proof.

`in_doubt` re-issue behaviour (§10): confirmed — the issuer's state gate is
`{dispatching, in_doubt}` (`background_attempt.py:1620`), and an existing row is
returned unchanged ("Re-issuing never rotates the nonce", `:1645-1655`). After
process death the row is still there, so the fresh process re-acquires the *same*
proof authority the observer held. This is a **post-hoc signing oracle**.

## Route 2 — nonce at rest on a public surface (BLK-W14-002)

```
SQLiteWorldStore.db_path                    # PUBLIC attribute, sqlite_store.py:183
  -> sqlite3.connect(db_path)               # read-only, backup/export/inspection shape
  -> SELECT capability_nonce FROM background_model_return_capabilities
  -> bytes.fromhex(row)                      # plaintext hex, background_attempt.py:647/:1660
  -> late_return_proof(nonce, **fields)      # PUBLIC exported function, late_return.py:131
  -> attach_late_trusted_return(...)         # PUBLIC entry, mints Core receipt+handoff
```

Frozen probe `IA14-NONCE-001`: `public db_path exposed nonce and arbitrary bytes
staged for bgattempt_bd420d5b472eeb881bb0c2f10220e1be`.

Severity note: the accepted pre-existing receipt authority
(`background_model_authenticity_authority.secret_hex`) is *also* plaintext in this
DB, but weaponizing it requires `_capture_trusted_response_return` or raw SQL
writes. The nonce path needs only **read** access plus public functions — trusted
state is then created through public APIs alone. Any backup/dump/replica of the
runtime DB therefore carries signing authority.

## Surfaces audited CLEAN (§11 checklist)

- `RuntimeSnapshot` (including `_outbound_relay_id` private slot): no nonce, no
  capability object.
- `BackgroundModelReturnCapability.model_dump()` / `repr` / `scope_fields()`: nonce
  absent (pydantic PrivateAttr).
- metering records, cockpit, capability catalog/history, exception text
  (`BackgroundModelAttemptBlocked`, `BackgroundModelResponseConflict` messages),
  `late_trusted_return_state` (issued/consumed only), `outbound_request_binding`,
  `response_authenticity_receipt`: no nonce.
- model input construction (`_outbound_request_fingerprint` payload): no nonce.

## Conclusion

Two independent routes give a recovery caller full proof authority for arbitrary
bytes: (1) the reachable issuer that re-returns the capability after process death,
and (2) the plaintext nonce on the public DB path plus the public proof function.
Either alone defeats "arbitrary bytes cannot become a trusted return".
`ACCEPTANCE_FAIL` blockers BLK-W14-001, BLK-W14-002.
