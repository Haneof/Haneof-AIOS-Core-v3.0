# WINDOW 20 Reviewer Probe Freeze Manifest — Batch 2 (`PROBE_FREEZE_MANIFEST_BATCH2.md`)

- **Frozen Before First Candidate Execution:** `YES`
- **Freeze Timestamp (UTC):** `2026-10-03T06:29:00Z`
- **Target Exact Candidate:** `fec30bd1495017bf13f08b0ef5b1e241dfb0e247` (`PR #310`)
- **Probe file:** `reviewer_probes/window20_migration_rsa_attack.py`
- **Frozen SHA-256:** `1e429dfea56430bf5ba6f7d1ed1ac0ead09b67fcb014e9e01313d372922b1e34`
- **Reviewer-owned RSA-2048 key:** generated in-sandbox via `openssl genrsa 2048`; all signatures produced by the reviewer's own PKCS#1 v1.5 implementation over the reviewer private key (no candidate signing/minting helper is used).

## Frozen Expected Outcomes

| Probe ID | Attack Surface | Fixed Expected Outcome |
|---|---|---|
| `IA20-MIGRATE-003` | Legacy conversion atomicity: 3 valid legacy rows, the **last** one tampered | `FAIL_CLOSED`: nothing converted (byte-identical trust state), no `bgresponse_v2_` proof anywhere, legacy secret + authority table preserved, first attempt and every retry raise `LegacyTrustMigrationError` |
| `IA20-MIGRATE-004` | Legacy edge branches: (a) empty trust state + staged legacy authenticator, (b) empty trust state + staged v2 row, (c) two authority rows, (d) wrong authority id, (e) non-hex secret, (f) wrong-length secret, (g) already-converted receipts under a live authority table, (h) orphan receipt without handoff | (a,c,d,e,f,g,h) `FAIL_CLOSED` with the legacy secret preserved; (b) completes with the secret purged, **zero** receipts created and the attempt left un-laundered |
| `IA20-RSA-ENC-001` | Frozen proof encoding `bglate_rsa_v1:<key_id>:<sig>` + key-id grammar | every accepted `key_id` round-trips exactly and verifies genuine reviewer signatures; non-canonical ids (colon, empty, padding, whitespace, control, NUL, unicode confusable, 129 chars, leading hyphen/dot/underscore) and ambiguous/malformed proofs are refused |
| `IA20-RSA-PARAM-001` | Verifier parameter matrix: modulus (negative/zero/one/even/undersized/leading-zero/`+`/`0x`/uppercase/whitespace/non-hex), exponent (bool/float/None/negative/0/1/2/even/e≥n), algorithm | every non-canonical parameter is refused at construction; legal 2048-bit odd modulus with `e ∈ {3, 65537}` is accepted |
| `IA20-RSA-TRANSPLANT-001` | 12 bound fields (attempt, subject, work kind/id, round, outbound fingerprint, relay, provider, model, provider request id, response fingerprint, payload digest) | reviewer-signed genuine return completes exactly once with 1 meter; all 12-field transplants are rejected |
| `IA20-NOTSUB-002` | Post-binding `not_submitted` write sites (`reconcile_not_submitted`, `mark_failure(definitely_not_submitted=True)`) after a durable dispatch/binding | `FAIL_CLOSED`: both refused, state never `not_submitted`, no redispatch on a second `run_turn` |
| `IA20-EXACTONCE-001` | Duplicate/conflicting genuine returns on one attempt | first genuine return wins exactly once (1 meter, 1 completion, assistant ref set); conflicting second and exact replay are refused |
