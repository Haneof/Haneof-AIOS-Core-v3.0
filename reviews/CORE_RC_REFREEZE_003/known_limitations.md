# CORE-RC-REFREEZE-003 — Known Limitations and Explicit Non-Claims

## Preserved trust-root limitation

«持有底层 trusted store/runtime 对象的进程内 trusted code 可以调用内部 receipt minting path，或直接读取 SQLite 中保存的 HMAC authority secret。»

Disposition carried from the accepted Corrective-002 review: **`NON_BLOCKING TRUST-ROOT LIMITATION`**. This RC does not reinterpret the store/runtime trust root as a public-boundary authenticity hole, and does not claim that the authority key is inaccessible to trusted in-process code or a party with database compromise. The authority and receipts remain in the same durable World SQLite; missing/malformed authority and unauthenticated historical rows fail closed.

## Operational and release boundaries

- Distributed multi-host / HA writer coordination is **not claimed**. The verified contract is the canonical same-World writer behavior and validation-only lock override within the supported local process/filesystem model.
- `--lock` / `AIOS_LOCK_PATH` cannot create a second writer identity; the canonical lock follows the resolved World path.
- The search index is a rebuildable projection, not an authority. World SQLite remains authoritative for objects, operations, idempotency and recovery receipts/authority.
- `pyproject.toml` uses version ranges (`pydantic>=2.10,<3`, dev `pytest>=8,<9`, Python `>=3.12`). The repository has no dependency lockfile. The formal gate pins and records the required runtime versions explicitly; this does not create a general supply-chain lock.
- The clean-install smoke uses the built frozen-source wheel and `aios_core.headless.testing:deterministic_model_handler`; it is not a real-provider integration or Resident evaluation.
- No Resident A/B/C, C15 evaluator/close, public release tag, or public release was run or authorized.
- RC impact remains `FRESH_A_REQUIRED`; A-003 is historical for RC-002 only.

## Formal environment and regression status

The exact observed CPython, Pydantic, pytest, SQLite, OS, kernel, architecture, workflow run, test counts and evidence hashes are recorded in `environment_manifest.txt`, `full_regression.md`, `focused_regressions.md`, and `SHA256SUMS` after the formal gate completes. Historical reviewer/PM evidence is provenance only, never a substitute for the fresh RC-003 run.
