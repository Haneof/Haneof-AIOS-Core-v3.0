# LEGACY_MIGRATION_AUDIT — verify-before-convert proof (`C2-4`)

Method: `BackgroundModelAttemptStore._migrate_legacy_authenticity_authority(conn)`
in `src/aios_core/runtime/background_attempt.py`, invoked from `_initialize` when a
`background_model_authenticity_authority` table exists.  The audit below reads the
source in execution order and states, for each step, what would have to be true for a
trusted row to be produced.

## 0. Transaction shape

```
started_transaction = not conn.in_transaction
if started_transaction: conn.execute("BEGIN IMMEDIATE")
try: self._migrate_legacy_authenticity_authority(conn)
except BaseException: conn.rollback(); raise
if started_transaction: conn.commit()
```

Every refusal path raises `LegacyTrustMigrationError` (or the underlying SQLite
error), and the wrapper rolls the whole migration back.  There is no path that
commits a partially converted database: the conversion statements are the last
statements in the method, they run only after the verification loop has completed
for **every** receipt, handoff and staged response, and each conversion checks
`rowcount == 1`.

## 1. Authority row identity

* `_legacy_authority_rows(conn)`: the table must hold **exactly one** row and its
  `authority_id` must be the recognised `trusted-return-v1`; otherwise refuse.
* `_read_legacy_authority_key(rows)`: `secret_hex` must be a `str`, must parse as
  hexadecimal, and must be exactly 32 bytes; otherwise refuse.  (The non-hex
  synthetic secret used by the historical secret-upgrade fixture is exactly what
  this check rejects — never silently.)

## 2. Whole-database verification before any rewrite

The method loads `background_model_response_receipts`,
`background_model_return_handoffs`, `background_model_responses`,
`background_model_request_bindings` and `background_model_attempts` first, then:

| # | Check | Laundered state it refuses |
| --- | --- | --- |
| 1 | receipt and handoff attempt-id sets are duplicate-free and **one-to-one** | duplicated / orphaned / partial legacy rows |
| 2 | every receipt proof starts with `bgresponse_v1_` while the legacy authority still exists | rows already rewritten, or rows carrying a foreign authenticator |
| 3 | `hmac.compare_digest(proof, HMAC_sha256(legacy_key, canonical receipt message))` | tampered/invalid HMAC, wrong secret, forged authenticator (`IA17-MIGRATE-002` subcase A) |
| 4 | a durable attempt row exists; its state ∈ {`dispatching`, `in_doubt`, `response_returned`, `metered`} | receipts attached to attempts that never crossed the provider boundary |
| 5 | attempt `subject_id`/`work_kind`/`work_id`/`model_round_index` equal the receipt's | cross-subject / cross-work / cross-round transplant |
| 6 | attempt `provider`/`model`/`provider_request_id`/`response_fingerprint` (when present) equal the receipt's | provenance substitution |
| 7 | a durable pre-dispatch request binding exists and its identity fields equal the receipt's | missing/duplicated binding, cross-attempt transplant |
| 8 | binding `outbound_request_fingerprint` and `relay_id` equal the receipt's | outbound-request transplant |
| 9 | `binding.relay_id == relay_id_for(binding fields)` (mechanical relay identity) | hand-edited relay id |
| 10 | handoff `authenticity_proof` equals its receipt proof | corrupted handoff proof (`IA17-MIGRATE-002` subcase C) |
| 11 | handoff `payload_sha256` equals the receipt `payload_sha256` | digest mismatch |
| 12 | handoff payload is a `str` whose SHA-256 equals that digest | tampered payload bytes (`IA17-MIGRATE-002` subcase B) |
| 13 | payload decodes as a **canonical** `ModelDirective` and the decoded directive's response fingerprint and provider identity equal the receipt's | semantic smuggling through non-canonical JSON / re-encoded bytes |
| 14 | for every staged response: if its attempt has no verified receipt it must not carry a `bgresponse_v1_` authenticator; if it has one, its proof, provider, model, request id, response fingerprint, payload digest and **exact bytes** must equal the verified handoff | staged-response substitution, stranded legacy authenticators |
| 15 | staged responses that carry no legacy authenticator and have no receipt are ignored (not trusted, not converted) | historical staged rows without authority stay unusable |

Only after all 15 checks pass for all rows does the method convert:
`UPDATE background_model_response_receipts / background_model_return_handoffs /
background_model_responses SET authenticity_proof = <bgresponse_v2_…>` with
`rowcount == 1` enforced per row, followed by `DELETE FROM
background_model_authenticity_authority` and `DROP TABLE
background_model_authenticity_authority`.

## 3. Empty-trust-state branch (no receipts, no handoffs)

If the authority table exists but there are **no** receipts and **no** handoffs,
there is no legacy trust state to authenticate.  The branch therefore:

1. refuses (fail closed) if **any** staged response carries a `bgresponse_v1_`
   authenticator — purging the secret first would strand unverifiable state;
2. otherwise deletes and drops the authority table without converting anything.

This grants no trust (nothing becomes trusted), rewrites nothing, and only removes
the obsolete secret. It is what allows a pre-upgrade database that never captured a
trusted return to start safely. It is deliberately **narrow**: it excludes any
receipt- or handoff-bearing database, which always goes through the full check set
above.

## 4. Secret purge guarantee

`_initialize` sets `PRAGMA secure_delete = ON` as soon as a legacy capability or
legacy authority table is present, and after the transaction commits it runs
`PRAGMA wal_checkpoint(TRUNCATE)`, raising
`RuntimeError("legacy signing material purge could not truncate SQLite WAL")` if the
checkpoint does not report success.  Receipts/handoffs keep only the public
integrity fingerprint; no HMAC key, nonce or private key survives in the database.

## 5. Evidence

| Obligation | Evidence |
| --- | --- |
| valid legacy state migrates and recovers exactly once | `IA17-MIGRATE-001` (GREEN, unchanged), `CA2-005` |
| invalid HMAC → FAIL_CLOSED, atomic, secret **not** purged | `IA17-MIGRATE-002` subcases A/B/C (now refused), `CA2-006[invalid_hmac]`, `CA2-006[wrong_secret]` |
| tampered payload/digest/handoff/staged rows → FAIL_CLOSED | `CA2-007`, `CA2-008[8 parametrised subcases]` |
| no partial rewrite and no secret purge on failure; retry still fails closed; repaired DB migrates | `CA2-009` |
| empty-trust-state purge cannot strand a legacy staged authenticator | `tests/integration/test_core_background_late_trusted_return_secret_upgrade_001.py` (passes) and the guard branch in §3 |
