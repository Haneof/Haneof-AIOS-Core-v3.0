# WINDOW 17 Reviewer Probe Freeze Manifest (`PROBE_FREEZE_MANIFEST.md`)

- **Frozen Before First Candidate Execution:** `YES`
- **Target Exact Candidate:** `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd` (`PR #308`)
- **Candidate Parent:** `293d32c683033ba27c11059fd021e68342a82c77`
- **Candidate Tree:** `a762df979826d3a599b93d937c53b633d0cb8466`
- **Construction Base:** `0b883c71d91e5f0772334514925237f1570fa780`

## Pre-Execution Frozen SHA-256 Digests (`v1`, `v2`, and `v3`)

### Initial Freeze (`v1` — preserved at `window17_independent_attack_v1.py` & `SHA256SUMS.v1`)
```text
c950d158ed0582fce2c1610f8dab9507cd3e90296ae43f98cb514c9e904fb09f  window17_independent_attack_v1.py
266e4204ece1007b465247b5a25361a6e42a01a2e7afdfcecf02fa3bf7d3c774  PROBE_CONTRACT.md
da8c24e04be20ef8b6ca6d42576709526e200ecda4299c74741c02cebb30b270  PROBE_REVISION_LOG.md (v1)
```

### Revision 2 (`v2` — preserved at `window17_independent_attack_v2.py` & `SHA256SUMS.v2`)
```text
fdefecd8edf20a3b9ede4e0432cac0864e51bb82c098c4d8568fbd08651a4900  window17_independent_attack_v2.py
2237d1aed24b6b9066b6e7b20081231979cc153daac27821b1b57e0125c207b9  PROBE_REVISION_LOG.md (v2)
```

### Current Frozen Probe Suite (`v3` — setup precondition harness fix only; zero expected-outcome change)
```text
a6db33956bb7bc1e8af19cddd7cebdd320604bba98b6a2b906fd1eb363fba0c3  window17_independent_attack.py
fdefecd8edf20a3b9ede4e0432cac0864e51bb82c098c4d8568fbd08651a4900  window17_independent_attack_v2.py
c950d158ed0582fce2c1610f8dab9507cd3e90296ae43f98cb514c9e904fb09f  window17_independent_attack_v1.py
266e4204ece1007b465247b5a25361a6e42a01a2e7afdfcecf02fa3bf7d3c774  PROBE_CONTRACT.md
```

## Reviewer Execution Environment Record (`REVIEWER_ENVIRONMENT_DEVIATION` Disclosed)

| Component | Formal Target | Reviewer Sandbox | Match Status |
|---|---|---|---|
| CPython | `3.12.14` | `3.11.2` | `REVIEWER_ENVIRONMENT_DEVIATION` (sandbox OS image provides CPython 3.11.2) |
| Pydantic | `2.13.5` | `2.13.5` | Exact match |
| pytest | `8.4.2` | `8.4.2` | Exact match |
| SQLite | `3.45.1` | `3.40.1` | `REVIEWER_ENVIRONMENT_DEVIATION` (sandbox libsqlite3 3.40.1) |
| OpenSSL | `3.0.13` | `OpenSSL 3.0.20 7 Apr 2026` | `REVIEWER_ENVIRONMENT_DEVIATION` (sandbox libssl 3.0.20) |
