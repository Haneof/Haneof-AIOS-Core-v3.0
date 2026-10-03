# WINDOW 20 Reviewer Probe Freeze Manifest (`PROBE_FREEZE_MANIFEST.md`)

- **Frozen Before First Candidate Execution:** `YES`
- **Freeze Timestamp (UTC):** `2026-10-03T06:24:39Z`
- **Target Exact Candidate:** `fec30bd1495017bf13f08b0ef5b1e241dfb0e247` (`PR #310`)
- **Historical RED Anchor (frozen failed candidate):** `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd` (`PR #308`)
- **Canonical Window 17 Reviewer Probe (extracted fresh from review object):** `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_001_IA_WINDOW_17/reviewer_probes/window17_independent_attack.py` @ `e4161dd0ad0a2f825461311a1c8c5ff8234a07f8`, SHA-256 `a6db33956bb7bc1e8af19cddd7cebdd320604bba98b6a2b906fd1eb363fba0c3`

## Frozen Reviewer-Owned Probe Suite (`v1`)

```text
7cb32b5fd4a8ddb6eb3a7318c219fdd926d2a1a62edbcf38d4411d859df1c1ba  window20_independent_attack.py
a1a4d29c9cc23db5fbe1457cc561bac47d8fc2c724a7bf7d1e3e3b9c69438270  reviewer_w20_pub.pem
4a2b6482e314ba9555f4ba0ec643639d99d49fb6b64ca9c91b9b17622cd2c00c  reviewer_w20_modulus.hex
```

Reviewer-owned RSA-2048 material was generated inside the reviewer sandbox with
`openssl genrsa 2048` (`reviewer_w20_key.pem`, private half never written into the
candidate tree).  No candidate-side signing/minting helper is used to produce any
"attacking" proof: probes use only reviewer-owned key material and public/readable
Core state (`background_model_request_bindings`).

## Frozen Expected Outcomes (recorded before first execution)

| Probe ID | Attack Surface | Fixed Expected Outcome |
|---|---|---|
| `IA20-MINT-003` | Public-API ephemeral live-window forgery: post-crash recovery caller with no RSA key and no live provider call drives the exported `open_live_provider_return_window` / `register_handler_return` helpers and `BackgroundModelAttemptStore.record_live_provider_return` on an `in_doubt` attempt bound to a `LateReturnVerifier` | `FAIL_CLOSED`: a caller that is not inside a genuine live provider-return frame cannot mint a trusted receipt/handoff nor complete/meter the in_doubt turn |
| `IA20-MINT-004` | Same forgery on an attempt dispatched with `late_return_verifier=None` (anonymous / no external authority) | `FAIL_CLOSED`: attempt remains permanently `in_doubt`; zero receipts, zero handoffs, zero staged responses, zero meters, no completion |
| `IA20-OBJGRAPH-002` | Reflection-only reachability from the post-crash recovery runtime object (`type(store).record_live_provider_return.__globals__` → `LiveProviderReturnWindow._issue.__func__.__globals__` → issuance sentinel / window registry / armed ContextVar) | `FAIL_CLOSED`: the recovery object graph must not yield a callable or module state able to mint trusted receipts/handoffs |
| `IA20-WINDOW-001` | Ephemeral-window negative matrix: `live_window=None`, wrong attempt id, closed window, consumed window, `copy.copy` / `copy.deepcopy` / `pickle`, use from a thread where the ContextVar is not armed, use against a cloned durable world with the same attempt id, unregistered forged window object, public constructor, detached `ContextVar` context | `FAIL_CLOSED`: every non-live-window satisfaction is refused; no sub-case may mint, copy, pickle, or construct a usable window |

## Reviewer Execution Environment (`REVIEWER_ENVIRONMENT_DEVIATION` disclosed)

| Component | Formal target (PR #310 CI) | Reviewer sandbox | Status |
|---|---|---|---|
| CPython | `3.12.14` | `3.11.2` | `REVIEWER_ENVIRONMENT_DEVIATION` — exact 3.12.14 unavailable: sandbox egress permits only `pypi.org`, `api.github.com`, `github.com` (git) and `codeload.github.com`; `objects.githubusercontent.com` / `astral-sh` python-build-standalone assets are blocked and no `libsqlite3-dev`/`zlib`/`openssl` headers exist to build 3.12.14 from source with `_sqlite3` |
| Pydantic | `2.13.5` | `2.13.5` | Exact match |
| pytest | `8.4.2` | `8.4.2` | Exact match |
| SQLite | `3.45.1` | `3.40.1` | `REVIEWER_ENVIRONMENT_DEVIATION` (sandbox libsqlite3) |
| OpenSSL | `3.0.13` | `3.0.20` | `REVIEWER_ENVIRONMENT_DEVIATION` (sandbox libssl) |

Per the task's §24 rule, no `3.11` result is presented as a `3.12.14` formal
result: author formal-CI facts are taken from the GitHub API metadata, and all
security conclusions are drawn from reviewer-owned execution on the sandbox
runtime with this deviation stated explicitly.
