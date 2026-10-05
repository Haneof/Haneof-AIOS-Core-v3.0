# CORE-RC-REFREEZE-004 - Corrective-003 trusted-return security checks

Frozen software: `1cee3c5ad12f4b9098232bae11b51df786c5eb2f`.

Fresh preflight run `37210904177` passed the Route B security gate: **214 passed**.

Mechanical trust-writer inventory on the frozen source found all durable trusted-return table DML in `src/aios_core/runtime/background_attempt.py`. Receipt and handoff creation originates only through `attach_late_trusted_return`; staged response creation is a consumer through `stage_exact_response`.

The release gate additionally proves:
- local live-return authority remains decommissioned;
- `live_return.py` remains an inert tombstone and is not imported by authorization modules;
- the compatibility re-export in `runtime/__init__.py` is inert and is not mistaken for authority;
- external verifier + genuine proof remains the trust root;
- verifier-less ambiguous recovery stays fail-closed;
- forged/local provenance cannot block a later genuine proof;
- exact genuine replay is idempotent/effect-free;
- same-key changed bytes, conflicting proof and proof transplant fail closed;
- partial receipt/handoff commit is covered by the RC004 Route B backup/restore probe.

Binding result is the final exact-head workflow run pinned in the candidate PR/commit comment.
