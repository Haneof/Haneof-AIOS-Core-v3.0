# CORE-RC-REFREEZE-004 — Known Limitations and Explicit Non-Claims

## Trust-root limitation (carried, unchanged)

The accepted design does not consider the durable World SQLite trust root as a public-boundary authenticity hole; a party with full database compromise or arbitrary in-process trusted-code execution is outside the claimed threat model. What the accepted Corrective-003 **does** guarantee is that no ordinary application/recovery caller can mint a durable trusted return: local issuer APIs are removed, the `live_return.py` tombstone is inert and outside the authorization chain, and a durable trusted return requires a durable external verifier bound before dispatch plus a genuine external cryptographic proof.

## Environment limitation of the local evidence runs

- The sandbox's locally built CPython 3.12.14 has **no `_ssl`/`_hashlib`** (no OpenSSL development headers were available to link). Core imports no `ssl` at all (`grep -rn 'import ssl' src/` → 0 matches; hashing uses the built-in `_sha2`), so this does not affect any binding check; dependency wheels were pre-fetched and installed offline. The **formal CI gate** runs on a GitHub runner whose `environment_manifest.txt` records the actual OpenSSL/OS/kernel identity for the same frozen software, and that record is authoritative for the §4 environment line.
- Local OS/kernel: Debian GNU/Linux 12 (bookworm), Linux 6.1.158+ x86_64; interpreter `/home/user/.local/py312/bin/python3.12`; `aios_core.__file__` = `<frozen worktree>/src/aios_core/__init__.py`.

## Other boundaries

- Distributed multi-host / HA writer coordination is **not claimed**; the verified contract is canonical same-World single-writer behavior and validation-only lock override in the supported local process/filesystem model.
- The search index is a rebuildable projection, not authority; the World SQLite file remains authoritative.
- `pyproject.toml` uses version ranges (`pydantic>=2.10,<3`, dev `pytest>=8,<9`, `requires-python >=3.12`) and there is no dependency lockfile; the formal runs pin the required versions and record `pip freeze`.
- The clean-install smoke uses the deterministic mechanical adapter and a disposable World; it is not a real-provider integration and not a Resident evaluation.
- The full-repository run includes the pre-existing downstream C15 operator debt (45 failed / 1092 passed, all under `tests/c15_persistence/**`). It is preserved RED, is not repaired, and does not block the Core freeze (see `c15_downstream_adjudication.md`).
- The prior-window backup/restore probe (`reviews/CORE_RC_REFREEZE_003/probes/backup_restore_trusted_return.py`) asserts the removed pre-Corrective-003 local-trust receipt and therefore fails by design on this frozen target; it is superseded by the fresh RC-004 probe (see `backup_restore_rebuild_smoke.md`).
- No Resident A/B/C, C15 evaluator/close, public release tag, UI/hardware work, or Independent Acceptance was performed or authorized in this window.
- RC impact remains `FRESH_A_REQUIRED` + `FRESH_OPERATOR_PREP_REQUIRED`; A-003/A-004 are historical for prior RCs only and are not hash-swapped.
