# CORE-RC-REFREEZE-004 — Known limitations and non-authorizations

- This is an internal release-candidate freeze. No public tag or public release is authorized.
- PR #321 and Window 23 publication staging are evidence/transport, not frozen software.
- The accepted Corrective-003 disclosure remains: a direct fresh-process `record_response` against a still-`dispatching`, verifier-less attempt can record unverified completion, but it mints no trusted receipt/handoff/staged response, cannot become recovery-eligible trusted provider return, and a genuine external proof can supersede that unverified provenance. This is inherited/pre-existing and is not expanded by this freeze.
- No distributed multi-host/HA writer guarantee is claimed; the release gate proves the canonical same-World local process/filesystem writer contract.
- C15 persistence/operator compatibility debt is downstream. It must not be “fixed” by restoring the retired local self-trust path.
- Historical Resident evidence is not valid for this RC; `FRESH_A_REQUIRED`.
- Formal runtime evidence is authoritative only when produced by the exact-head GitHub Actions run on CPython 3.12.14. Historical CI and author evidence are provenance only.
