# CORE-RC-REFREEZE-003 — Known Limitations and Explicit Non-Claims

## Preserved trust-root limitation

«持有底层 trusted store/runtime 对象的进程内 trusted code 可以调用内部 receipt minting path，或直接读取 SQLite 中保存的 HMAC authority secret。»

Disposition carried from the accepted Corrective-002 review: **`NON_BLOCKING TRUST-ROOT LIMITATION`**. This RC does not reinterpret the store/runtime trust root as a public-boundary authenticity hole, and does not claim that the authority key is inaccessible to trusted in-process code or a party with database compromise. The authority and receipts remain in the same durable World SQLite; missing/malformed authority and unauthenticated historical rows fail closed.

## Operational, environment and release boundaries

- Distributed multi-host / HA writer coordination is **not claimed**. The verified contract is canonical same-World writer behavior and validation-only lock override within the supported local process/filesystem model.
- `--lock` / `AIOS_LOCK_PATH` cannot create a second writer identity; the canonical lock follows the resolved World path.
- The search index is a rebuildable projection, not authority. World SQLite remains authoritative for objects, operations, idempotency and recovery receipts/authority.
- The frozen `pyproject.toml` uses version ranges (`pydantic>=2.10,<3`, dev `pytest>=8,<9`, Python `>=3.12`) and there is no dependency lockfile. The formal run pins required runtime versions and uploads full `pip freeze` outputs; this does not create a general supply-chain lock.
- Clean-wheel smoke uses the frozen-source wheel and `aios_core.headless.testing:deterministic_model_handler`; it is not a real-provider integration or Resident evaluation.
- The formal GitHub runner was Ubuntu 24.04.5 LTS / kernel 6.17.0-1022-azure / x86_64. GitHub emitted non-blocking runner notices about Node.js 20 actions being forced to Node.js 24 and the future `ubuntu-latest` migration to Ubuntu 26.
- The hosted artifact is available from run [36436264055](https://github.com/Haneof/Haneof-AIOS-Core-v3.0/actions/runs/36436264055), with server-reported SHA-256 and per-file hashes in `formal_gate_run.json`. The sandbox's earlier attempt to download the archive failed with EOF/SSL_ERROR_SYSCALL; no downloaded local copy is claimed.
- No Resident A/B/C, C15 evaluator/close, public release tag, or public release was run or authorized.
- RC impact remains **`FRESH_A_REQUIRED`**; A-003 is historical for RC-002 only and is not hash-swapped.

## Fresh formal gate status

The complete exact-target suite passed: 919 tests, 0 failures/errors/skips; focused trusted-return and Core systems runs passed 248/248 and 356/356. Clean install/headless and backup/restore/index-rebuild probes passed. Exact environment, run identity, artifact digest, evidence checksums and probe records are in `environment_manifest.txt` and `formal_gate_run.json`. This is not independent acceptance.
