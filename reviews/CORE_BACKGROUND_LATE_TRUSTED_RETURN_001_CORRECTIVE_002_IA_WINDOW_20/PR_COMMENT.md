## WINDOW 20 — Fresh Independent Core Runtime Acceptance — `ACCEPTANCE_FAIL / blocker=1 / CORRECTIVE_OR_ADJUDICATION_REQUIRED`

**Task:** `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-002-INDEPENDENT-ACCEPTANCE`
**Reviewer role:** Fresh Independent Core Runtime Acceptance Reviewer (not the Window 19 author, not a corrective engineer, not PM/merge owner)
**Review PR (review-only / do not merge):** #311
**Exact review SHA:** `220311759e88fb3948ad3f4dba655058e0f392a8`
**Reviewed exact candidate:** `fec30bd1495017bf13f08b0ef5b1e241dfb0e247` (this PR, unchanged; remote branch tip re-verified at review time)
**Review base:** `ca47087fb68c90d6ac380c11143a0e36e80fc04a` (fresh live main)
**Verdict:** `ACCEPTANCE_FAIL / blocker=1 / CORRECTIVE_OR_ADJUDICATION_REQUIRED`
**Disposition:** returned to PM. No merge, no Window 21 integration, no RC-REFREEZE-004, no Resident/persistence/evaluator/release work authorized by this verdict. Candidate was **not** modified and no corrective work was performed.

---

### Binding blocker — `BLK-W20-001` (`CRITICAL`)

`RECOVERY_CALLER_TRUSTED_RETURN_MINT_ORACLE_VIA_SELF_ISSUED_EPHEMERAL_WINDOW` — **`BLK-W17-001` is not closed.**

`aios_core.runtime.live_return.open_live_provider_return_window` and `register_handler_return` are public module-level functions (exported in `__all__`), and `BackgroundModelAttemptStore.record_live_provider_return` (`src/aios_core/runtime/background_attempt.py:2416+`) accepts `dispatching|in_doubt|response_returned|metered` with the ephemeral window as its only gate. Every precondition of that window — `isinstance`, process-registry identity, armed `ContextVar`, handler-return object identity, attempt id — is satisfied by a caller that issues the window itself. A post-crash recovery caller with no RSA key and no provider call therefore mints a durable receipt + handoff and completes/meters the turn with its own bytes; with a `late_return_verifier=None` dispatch it also leaves the mandatory permanent `in_doubt` state; and the same authority is reachable by pure reflection (`type(store).record_live_provider_return.__globals__` → `LiveProviderReturnWindow._issue.__func__.__globals__`) without importing the module by name.

Frozen reviewer probes (frozen before execution; raw output in review PR #311 `raw/`):

| Probe | Expected | Observed |
|---|---|---|
| `IA20-MINT-003` public-API forgery | FAIL_CLOSED | **FAIL** — `minted=True, state=metered, receipts=1, handoffs=1, responses=1, meters=1, turn_response='FORGED_VIA_PUBLIC_LIVE_WINDOW_API_NO_PROVIDER_CALL', genuine_rsa_return_conflicted=True` |
| `IA20-MINT-004` verifier-less attempt | permanent `in_doubt` | **FAIL** — `state=metered, receipts=1, meters=1, turn_response='FORGED_ON_VERIFIERLESS_ATTEMPT_VIA_PUBLIC_WINDOW'` |
| `IA20-OBJGRAPH-002` object-graph reachability | no mint authority reachable | **FAIL** — `minted=True, receipts=1, handoffs=1` |
| `IA20-WINDOW-001` window hygiene matrix | all non-live satisfactions refused | **FAIL** — self-issued window and armed-context copy accepted (all others correctly refused) |

Invariants violated: `BLK-W17-001`; `C1`, `C2`, `C3`, `C8`; `T1`, `T2`, `T3`, `T4`, `T6`; and the Window 15 anti-regression rule that naming conventions / self-asserted boundaries are not authority. The frozen W17 probe suite passes on this candidate only because `IA17-MINT-001/002` are name-based (`AttributeError` on the removed helper) and `IA17-OBJGRAPH-001` is a name-filtered, depth-limited walk — green frozen probes are necessary, not sufficient.

**Minimal corrective scope:** make the trusted-return writer reachable only with authority a recovery caller cannot manufacture — e.g. bind capture to a capability created inside `CognitiveRuntime.run_turn` and never exported/importable, remove the public issuance helpers, and ensure the sentinel/registry/armed-context are not reachable via `__globals__` from the recovery object graph; then re-run the frozen W17 suite **and** the W20 probes unchanged.

### Independently verified positives

- **Frozen W17 replay (mandatory RED-first):** probes extracted fresh from canonical review `e4161dd0ad0a2f825461311a1c8c5ff8234a07f8` (SHA-256 `a6db33956bb7bc1e8af19cddd7cebdd320604bba98b6a2b906fd1eb363fba0c3`, exact match) → `probes=14 failures=6` on `cb8a6b3c…` (the exact W17 blocker set) and `probes=14 failures=0` on `fec30bd…`. The formal `red-first-window14` job is historical W14 evidence (`5ad0524c…` / `84457bad…`) and was not used as W17 evidence.
- **`BLK-W17-002` genuinely corrected** (reviewer probes `IA20-MIGRATE-003/004`): verify-before-convert, whole-DB transaction, tampered *last* row converts nothing, secret preserved, every retry fail-closed, orphan/duplicate/mismatch/already-converted/multiple-authority/malformed-secret branches fail closed.
- **`BLK-W17-003` genuinely corrected** (`IA20-RSA-ENC-001`, `IA20-RSA-PARAM-001`, `IA20-RSA-TRANSPLANT-001` with a reviewer-generated RSA-2048 key and reviewer-owned signer): canonical key-id grammar round-trips, parameter matrix refused at construction, genuine signature accepted once, **12/12** bound-field transplants rejected.
- `IA20-NOTSUB-002` post-binding downgrade refused with no redispatch; `IA20-EXACTONCE-001` first-writer-wins with exactly one staged row/meter/completion; R5-A/B/C/D and the frozen race/SIGKILL/Route-B positives green; focused reviewer regression **231 passed / 0 failed**.
- **Scope/identity:** 39 files `+6049/−261`, out-of-scope `0`, forbidden paths `0`; `7db79da5 → fec30bd1` is exactly one evidence-only commit with byte-identical `src`/`tests`/`.github` subtrees.
- **`OBS-PM-W19-001`** independently confirmed as stale `SCOPE_MANIFEST.md` metadata (`git diff --shortstat main 7db79da5` = `37 files, +5801/−261`), not hidden scope.

### Observations (non-blocking)

- `OBS-W20-002`: the resident-visible gate's pinned-tree check (`tools/c15_persistence/resident_surface_check.py:308-322`) ignores the diff return code, so with `--base main` unresolvable in CI it passes vacuously; in a resolved reviewer sandbox the same test fails because this candidate legitimately modifies `src/aios_core`. Pre-existing tooling, untouched by this PR — an evidence-quality note, not a corrective blocker.
- `OBS-W20-003`: a stray armed module `ContextVar` (settable by any code reaching `live_return` state) permanently blocks later provider returns on that call stack; windows are attempt-id scoped only (accepted against a cloned DB with the same attempt id).
- `OBS-W20-004`: `canonical_late_return_proof` accepts odd-length hex signatures that can never verify (fail-closed encoding nit).
- `OBS-W20-005`: pydantic lax coercion converts integral `float` `65537.0` → `int` `65537` for `public_exponent` (legal value, no authority impact).
- `OBS-W20-006`: CI artifact bytes/logs are not retrievable from the reviewer sandbox (egress policy); run/job conclusions and all four artifact digests were verified through the GitHub API as metadata.
- Reviewer environment deviation disclosed: CPython `3.11.2` (formal `3.12.14`; exact 3.12.14 unattainable in-sandbox), SQLite `3.40.1`, OpenSSL `3.0.20`; pydantic `2.13.5`, pytest `8.4.2` exact. No 3.11 result is presented as a 3.12.14 result.

Full report, probe sources, revision logs, freeze manifests, raw outputs and integrity records: **PR #311** (`reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_002_IA_WINDOW_20/`).