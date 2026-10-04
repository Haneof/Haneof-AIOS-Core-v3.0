# Window 25 reviewer-owned probe freeze

Frozen before first execution against candidate/frozen software.

- Target software: `1cee3c5ad12f4b9098232bae11b51df786c5eb2f`
- Candidate under review: `70134269ddfc7c80c4a703a933253bd099746504`
- Expected result: every enumerated case passes; any trusted-row creation by a
  local/reflection/tombstone/verifier-less path, any proof transplant acceptance,
  any conflicting genuine proof acceptance, any partial-state widening, provider
  redispatch, or duplicate meter/effect is a blocker.
- Enumeration: `W25-OWN-01` through `W25-OWN-08`, declared in
  `reviewer_attacks.py::REVIEW_CASES`.
- Source SHA-256 is recorded in `PROBE_SHA256.txt` before execution.

