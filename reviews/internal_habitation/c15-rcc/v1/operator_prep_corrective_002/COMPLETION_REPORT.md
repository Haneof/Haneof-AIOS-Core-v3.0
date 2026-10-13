# Corrective-002 Operator Prep — author completion report

**EVIDENCE-ONLY / DO NOT MERGE AS IMPLEMENTATION**

`OPERATOR_PREP_CORRECTIVE_002_COMPLETE / REVIEW_READY`
`READY_FOR_INDEPENDENT_ACCEPTANCE`

This is author evidence, not independent acceptance or Resident launch approval.

## Exact lineage

- Task-start live main: `b7c9e85014806637f7a01c8fd6695bc9f57672ba` (refetched unchanged).
- Initial carry/freeze: `4b7afc6f5bff1deb7407eb2f1470a3b68c0aa79a`, sole parent main.
- v2 freeze before baseline execution: `95d9da9d6d75b7f563afe42d88a14b07e86911c1`.
- Genuine H2 RED commit before any repair: `8e34fba00edf4fdb5b80f04d7a648f6b5bb8c40e`.
- Corrected H1: `63c972ad7a19671cbdf809177f7a552aa2c2ecc6`; parent `8e34fba00edf4fdb5b80f04d7a648f6b5bb8c40e`;
  tree `8cd4a2d8b4cdf1f85699c5d78166f774741b420b`.
- Final freeze commit H2 is evidence/packet-only; sole parent H1. Its exact SHA/tree
  are pinned in the PR, not recursively inside this report.
- Historical #286 H2 `c32e544b747cb1f1d9b7418e2163a65ac55ee39c`, H1b
  `99af8e268a1f9e8944b163d8087005e0e3698620`; #284
  `dce47c0d8f3ac7e34efb47e22c63c6f9acbea1a6` remain unchanged/open/unmerged.

## Results

| Group | Exact #286 H2 v2 baseline | Candidate, unchanged v2 |
|---|---:|---:|
| C4 recovery binding | 2 PASS / 7 FAIL | 9 PASS |
| C5 operational ledger | 14 PASS / 56 FAIL | 70 PASS |
| C6 frozen RC | 3 PASS / 5 FAIL | 8 PASS |
| C7 runtime pins | 2 PASS / 3 FAIL | 5 PASS |
| C8 startup set | 1 PASS / 6 FAIL | 7 PASS |
| C9 due work | 1 PASS / 3 FAIL | 4 PASS |
| **Total** | **23 PASS / 80 FAIL** | **103 PASS** |

- C1/C2/C3 frozen v6 regression GREEN, including gate ID/count/execution consistency.
- Full A/B/C/D: 24/7/2/5 PASS, nonzero collected/result/execution counts and exact IDs.
- Final synthetic due-work raw request/ledger/result: `raw/h1_final_runtime/due_work_*`.
- Final packet-tier repeated probes: 103 PASS, identical immutable source/expectations.
- Clean bootstrap: new absent root `/home/user/.cache/c002/final-runtime-003`, exit 0;
  default and explicit repository-root `--verify` exit 0. Previous baseline/iteration
  runtimes were not reused for this final build.
- CPython 3.12.14; Pydantic 2.13.5; pytest 8.4.2; SQLite 3.45.1;
  OpenSSL 3.0.13. Wrong library fallback/import/working bytes/Git-object attacks fail closed.

## Minimal repairs

C4 serializes current snapshot once, rejects ambiguity, validates durable full-file
ledger digest and exact canonical snapshot-body bytes before resume/consume. These
are distinct digest domains; the timestamped envelope hash is not the body hash.

C5 uses one nonrecursive whole-record validator for operational lookup, append,
recovery and consume. Sequence/digest chain/event order/uniqueness and digest
continuity are enforced. Whole-record tail deletion still cannot be distinguished
from a valid prefix without an external head anchor; no stronger claim is made.

C6 uses a shared deterministic sorted path/SHA256/size manifest; only __pycache__
directories excluded, symlinks rejected. Git commit/repo/Core/tests identities,
actual Core/tests bytes and verified-root import path are checked. C7 enforces
exact SQLite/OpenSSL runtime pins and preserves the pre-download wheel trust root.

C8's packet/audit require the exact four approved inputs and current-main paired
contract hashes. C9 delegates explicit aware `now` to frozen Core process_due_work
through the same external handler; no semantic routing/callback is added.

## Revisions and retained failures

- Original v1 baseline: 81 FAIL / 22 PASS, including a scanner argument bug.
  v2 corrects only the directory-versus-source-file argument, frozen separately
  before execution. Both revisions/results preserved; no expected outcome changed.
- Candidate iteration 1: 101 PASS / 2 FAIL while packet still carried old manifest
  and three startup inputs; retained under raw/candidate_iteration_1.
- Gate iteration 1: A 22/24. Restored first_bad_seq diagnostic reporting and fixed
  the old crash worker's unrelated dictionary (S1) versus recovery snapshot (S2).
  Now the worker publishes the exact recovery snapshot, lives in tests/synthetic,
  and keeps the same gate assertion/node ID. Frozen targeted probes are untouched.
- Historical H2 package evidence relocated unchanged into historical_h2; 71 evidence
  files independently compared with exact H2 Git blobs. Not current evidence.

## Final pins

- Packet SHA256: `f6b61c33dc41d20438ab1b56bd1c8f2e46fcf6593532f3793c3c51ee7fbf7cdc`
- Packet status: `PREP_REVIEW_READY`
- Harness manifest: `e3b9ca6cd502bc27f22bff59a09ff6024bed17ea0865d46018d1ab70a77d7632`
- Canonical Core: `220718d6b5a2650b5e4263bbe8b7e661444cb33b486a7ecd7b5ad3d7d3399caa`
- Wheel trust root: `6fa2587c98662588e4758ac9b579fee8d800ce4fc2d36e692dbaaabd6f4c8afe`

See FINAL_PACKET_AUDIT.json, H1_CANDIDATE_IDENTITY.json, BASELINE_RED.v2.json,
package evidence/corrective_candidate_green.json, clean_bootstrap_manifest.json,
rc_identity.json, canonical Core/tests manifests, gates/, and both FREEZE_MANIFEST
and SHA256SUMS scopes. EVIDENCE_METHOD.md explains the non-circular two-tier binding.

## Scope and stop

No Core/product tests/governance/fixture/evaluator/release source modifications.
No real C15 Resident or release-state, cursor reveal, World/session, or Phase-A
execution. No historical PR changes, self-acceptance, merge, tag or release.
Stop for fresh independent acceptance; Resident and downstream work remain blocked.
