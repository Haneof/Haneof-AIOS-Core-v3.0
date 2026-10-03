# WINDOW14_COMPATIBILITY

The canonical Window 14 probe bytes remain immutable and are executed unchanged only against failed candidate `5ad0524c...` for historical RED.

The Corrective architecture intentionally removes the old HMAC capability API (`late_return_proof`, `_issue_external_return_capability`, bearer capability nonce). Therefore several Window 14 probe functions are not executable unchanged against the new candidate because importing/calling those retired symbols would test API existence rather than the binding security property.

Binding-property compatibility mapping:

- IA14-ORACLE-001 -> CA1: recovery object graph/reflection exposes verifier only and no signer/mint/capability callable.
- IA14-NONCE-001 -> CA2 + secret-upgrade attack: DB/WAL/dump/backup contain no nonce/private/HMAC authority and cannot forge.
- IA14-NS-001 -> CA3 + S3-ROUTE-B: post-binding not_submitted is refused/in_doubt.
- IA14-ID-001 -> accepted provider identity validation + CA5 identity transplant.
- IA14-JSON-001 -> CA5 duplicate JSON fail-closed.
- IA14-RACE-001 -> verifier consumption/first-writer-wins + conflicting valid signature refusal.
- IA14-SIGKILL-001 -> new real-SIGKILL verifier-only fresh-process probe.
- original S3 -> historical RED only, per PR #307; replacement is CA4-B / S3-ROUTE-B.

No historical probe expected outcome is rewritten. Architecture-incompatible HMAC/capability mechanics are replaced only where the governance contract explicitly requires verifier-only recovery.
