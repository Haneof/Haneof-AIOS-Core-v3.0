# CORRECTIVE_002_ATTACK_MATRIX — `C2-9`

Two new executable files, plus the unchanged frozen Window 17 probe matrix.

| File | Cases | Local result |
| --- | --- | --- |
| `tests/runtime/test_late_return_canonical_encoding_002.py` | 64 | 64 passed |
| `tests/integration/test_core_background_late_trusted_return_corrective_002.py` | 20 | 20 passed |
| frozen `window17_independent_attack.py` (v3) | 14 probes | `probes=14 failures=0` |

## A. Canonical encoding / RSA contract (`test_late_return_canonical_encoding_002.py`)

| Case | Attack | Expectation |
| --- | --- | --- |
| `CA2-010` | ambiguous, delimiter-bearing, padded, whitespace, unicode, over-length, non-canonical key ids | refused at construction; allowed ids round-trip identically through `encode → decode` |
| `CA2-011` | negative, zero, one, even, 1025-bit, even 2048-bit, leading-zero, uppercase, `0x`-prefixed, `+`-prefixed, underscore-suffixed, space-prefixed and non-hex moduli | `LateReturnEncodingError` before durable binding |
| `CA2-012` | exponent `-65537, -1, 0, 1, 2, 4, 6, 65536, N, N+2` | refused |
| `CA2-013` | non-integer / `None` / float / bool exponent; wrong algorithm string | refused |
| `CA2-014` | genuine RSA-2048 signature + all 12 single-field transplants (attempt, subject, work kind, work id, round, outbound fingerprint, relay id, provider, model, request id, response fingerprint, payload digest) | genuine verifies; every transplant fails |

## B. Corrective-002 integration matrix (`test_core_background_late_trusted_return_corrective_002.py`)

| Case | Attack | Expectation |
| --- | --- | --- |
| `CA2-001` | recovery object graph of a fresh runtime over a crashed dispatching attempt: mechanically invokes every trust-suggesting reachable callable with attacker-controlled arguments | zero trust rows ever created; no minting name reachable; removed helpers `not hasattr` |
| `CA2-002` | direct writer attacks: missing window, `None` window, forged `_issue` sentinel, `object.__new__` fabricated window, closed window replay, cross-thread window, handler-return identity mismatch | all `LiveReturnAuthorityError`; direct construction `TypeError`; attempt stays `in_doubt` |
| `CA2-003` | verifier-less/anonymous interrupted dispatch (no bound RSA verifier) | forged recovery refused (`BackgroundModelResponseConflict`); turn rerun refused; state `in_doubt`; no meter |
| `CA2-004` | genuine in-process live return | receipt + handoff captured, response applied; then: no open window, nothing armed, no window in the object graph, nothing window-related persisted; fresh process cannot mint, only recover |
| `CA2-004b` | **real `os.kill(SIGKILL)` child** that crashes inside the provider handler after the trusted side captured the signing context | exit `-SIGKILL`; fresh process: 0 open windows, 0 pending handler returns, removed helper absent, 0 trust rows; **genuine** RSA proof then recovers exactly one metered turn |
| `CA2-005` | valid pre-upgrade legacy DB (HMAC receipt + handoff + authority table) | verified, proof converted to the public integrity fingerprint, legacy table dropped, legacy secret absent from DB/WAL, exactly one metered completion |
| `CA2-006` | invalid HMAC / proof signed with another key | `LegacyTrustMigrationError`, rows untouched, secret **not** purged |
| `CA2-007` | tampered handoff payload bytes | refused |
| `CA2-008` | handoff proof mismatch, digest mismatch, staged-response mismatch, receipt digest mismatch, cross-attempt transplant, relay-binding mismatch, missing handoff, missing request binding | refused (8 parametrised cases) |
| `CA2-009` | failed migration, then retry with a still-broken DB, then repaired DB | failure leaves **no** partial `bgresponse_v2_` state, secret intact, legacy proofs intact; retry still fails closed; repaired DB migrates and recovers exactly once |
| `CA2-014` | proof signed for attempt A attached to attempt B (different verifier key + scope) | `BackgroundModelResponseConflict`; zero trust rows |
| `CA2-015` | two threads attaching competing valid proofs | exactly one accepted / one refused; one receipt, one handoff, one staged response; verifier consumed |

## C. Frozen Window 17 probe matrix (unchanged, `C2-8`)

`IA17-MINT-001`, `IA17-MINT-002`, `IA17-DOWNGRADE-001`, `IA17-MIGRATE-001`,
`IA17-MIGRATE-002`, `IA17-VERIFIER-SUB-001`, `IA17-OBJGRAPH-001`,
`IA17-DB-AT-REST-001`, `IA17-RSA-001`, `IA17-RSA-DELIMITER-001`,
`IA17-RACE-CRASH-001`, `IA17-NS-ROUTE-B-001`, `IA17-ID-JSON-001`,
`IA17-SIGKILL-001` → `SUMMARY | probes=14 failures=0` (raw log:
`GREEN_FROZEN_PROBE_RAW.txt`).

## D. Non-necessary findings (recorded as observations only, `C2-10`)

* `LiveProviderReturnWindow` is not a defence against deliberate in-process
  sabotage (documented in `DESIGN_SECURITY_MODEL.md`).
* `_PYDANTIC_INTERNALS` handling in the audit sweep exists only to avoid pydantic
  2.11+ deprecation noise; it is test scaffolding, not a security control.
