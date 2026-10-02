# SECRET_SEPARATION_UPGRADE_RED_FREEZE

CA2 extension frozen before the production migration repair.

Attack shape:

1. Start from a valid current runtime database.
2. Inject the two historical secret-at-rest surfaces:
   - failed-candidate `background_model_return_capabilities.capability_nonce`;
   - accepted historical `background_model_authenticity_authority.secret_hex`.
3. Confirm the exact known secret bytes are physically present in DB/WAL/SHM.
4. Re-open Current Core (normal schema migration path).
5. Require both legacy tables to disappear logically.
6. Require the known secret bytes to be absent from logical dump, raw DB/WAL/SHM,
   and a SQLite backup made after migration.

A DROP TABLE that leaves recoverable secret bytes in freelist/WAL is not sufficient.
