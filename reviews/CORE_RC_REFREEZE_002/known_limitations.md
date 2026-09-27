# CORE-RC-REFREEZE-002 known limitations

## NON_BLOCKING TRUST-ROOT LIMITATION (Corrective-002 IA residual)

«持有底层 trusted store/runtime 对象的进程内 trusted code 可以调用内部 receipt minting path，或直接读取 SQLite 中保存的 HMAC authority secret。»

This is **not** a public-boundary authenticity hole.

Clarifications (binding):

1. The HMAC authority secret lives inside the trusted SQLite World / runtime store (`background_model_authenticity_authority`). The store is the trust root.
2. External staging / recovery / reconcile public APIs do not expose the secret.
3. A caller who only has receipts, staged rows, or provider-visible relay identifiers cannot mint a valid proof for arbitrary bytes.
4. DB compromise / in-process trusted-code access to the store object is **outside** the public-boundary invariant. This freeze does **not** claim “there is no way to access the key”.
5. Backup / restore must copy the authority with the durable store. A restore that fabricated a second key would invalidate historical receipts; the accepted path preserves authority so historical valid receipts still verify.
6. Missing / malformed authority fails closed.
7. Historical unauthenticated rows are not upgraded to authenticated.

## Other non-blocking RC limitations (carried from CORE-RC-FREEZE-001)

- Distributed multi-host/HA writer coordination is not claimed.
- `--lock` / `AIOS_LOCK_PATH` cannot select a second writer identity; canonical lock is `<world>.writer.lock`.
- Search index is a rebuildable projection, never an authority.
- No public release tag is created by this freeze.
- Fixture-scope zero-Core-diff guards (C14 semantic-repair fixture / C15 RCC fixture) may still RED on branches that contain genuine Core history; they are KNOWN FIXTURE-SCOPE / BRANCH-SHAPE when substantive steps are green.

## Explicitly not claimed

- Resident A/B/C evidence on this Core.
- Hash-swap of A-RERUN-002 onto this RC.
