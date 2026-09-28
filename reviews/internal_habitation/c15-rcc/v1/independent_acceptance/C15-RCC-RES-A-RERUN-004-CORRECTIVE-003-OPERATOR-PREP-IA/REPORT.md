# Independent Resident Launch Infrastructure Acceptance

Task: `C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-INDEPENDENT-ACCEPTANCE`

## Exact identity and boundary

- PR #281 was freshly fetched and remained at exact head `10901d467679b70437ae112747eab81f889fd5cb`.
- Parent: `abb8b435e5187c7c6c2f4332aea37cd805b4a53c`.
- Tree: `db79761216529cf83f217ab00c937bc79806a510`.
- Changed paths: 4, all below the required operator-prep package; no `src/**`, `tests/**`, `.github/**`, fixture, evaluator, release, or accepted-RC implementation path changes.
- Packet `operator_prep_exact_head` equals the required parent and the packet is absent from the parent.
- Packet status remained `PREP_REVIEW_READY`; response mode remained `EXTERNAL_CURRENT_RESIDENT_SESSION`.

## Independent execution

The bootstrap was rebuilt from a new scratch root, not `/opt/aios`, and produced the qualified runtime. Frozen RC identity was independently verified with `rc_identity.py`; the full candidate A/B/C/D suite was rerun under the qualified interpreter: 33 passed. SHA256SUMS verification passed from the operator-prep root. Gate C evidence was inspected and is non-vacuous. No real Resident was run.

## Reviewer probes

Probe source and source hashes are frozen in `reviewer_probe_freeze.json`. The adversarial probe was intentionally not altered after its RED result; its captured output is retained as RED history. The probe covered response overwrite, tampered response consumption, orphan request detection, and ledger-tail truncation classification.

## Verdict

**ACCEPTANCE_FAIL / blocker=3**

### IA-OP-001 — published response overwrite is accepted as an idempotent replay

- Exact path: `reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP/harness/aios_exchange/responses.py`, `ResponsePublisher.publish_bytes`, existing-ledger branch.
- Reproduction: publish a valid response; overwrite `responses/<request_id>.json` with different bytes; call `publish_bytes` again with the original valid bytes.
- Observed: returns `idempotent_replay=True` without reading or validating the existing published file. The subsequent `consume_response` fails with `ExchangeContractError`, but the duplicate publication operation itself accepts the tampered published artifact.
- Expected: fail closed immediately on a published-file overwrite or digest mismatch; never accept the existing-ledger branch without checking on-disk bytes against the durable response digest.
- Binding reason: Gate A explicitly covers duplicate/overwrite published response and the infrastructure must make ambiguous/tampered durable exchange fail closed.
- Minimal corrective scope: response-publisher existing-record path plus a regression probe; do not modify Core or Resident code.

### IA-OP-002 — bootstrap package artifacts are not pre-pinned trust roots

- Exact path: `.../operator_prep/.../bootstrap/bootstrap_runtime.sh`, `ensure_wheelhouse`.
- Reproduction: inspect the qualified branch and the fallback branch. Both download `pydantic==2.13.5` and `pytest==8.4.2` from the live package index, then generate `requirements.hashes.txt` from whatever was downloaded. No expected wheel hashes are embedded or checked before acceptance.
- Observed: hashes are calculated after download and then trusted; a changed or substituted artifact at the same version becomes the new accepted hash. The clean build passed, but this demonstrates successful local provisioning, not immutable artifact identity.
- Expected: artifact hashes/SRI or an immutable lock must be pinned before download and verified against those fixed values, including transitive dependencies.
- Binding reason: the acceptance requires reproducible/frozen runtime and forbids mutable/unpinned artifacts. A post-download checksum list does not prevent a mutable registry artifact from becoming the frozen runtime.
- Minimal corrective scope: bootstrap dependency acquisition and its recorded evidence; no Core or Resident changes.

### IA-OP-003 — frozen gate results contain incorrect test enumeration metadata

- Exact paths: `.../evidence/gates/gate_a_result.json`, `gate_b_result.json`, `gate_c_result.json`, `gate_d_result.json`, and `.../harness/operator_tools/gate_runner.py` (`test_ids` parser).
- Reproduction: inspect each result and its corresponding `*_tests.txt`; rerun the same collection command. The result files report `test_count: 0` and `test_ids: []`, while collection files report 19, 7, 2, and 5 collected tests respectively and raw runs report the same pass counts.
- Observed: `gate_runner.py` only accepts collection lines that end with `)`, but pytest `--collect-only -q` emits IDs without that suffix. The freeze therefore records internally contradictory enumeration evidence.
- Expected: frozen result metadata must enumerate the actual collected test IDs and counts, matching the hashed collect-only output; a freeze with contradictory gate evidence must not be accepted.
- Binding reason: the task requires reviewer-frozen collect-only/enumeration and freeze-integrity verification; the candidate’s own gate result artifacts do not faithfully record that enumeration.
- Minimal corrective scope: gate enumeration/result generation and regenerated evidence in a new operator-prep freeze; do not edit the candidate in this review.

## Disposition

Do not merge PR #281, do not run a Resident, and do not change the candidate. This report is evidence-only. Since the required durable review publication cannot be made from a separate review branch in this fixed Arena session without violating the session branch constraint, publication status is handled by the agent response.
