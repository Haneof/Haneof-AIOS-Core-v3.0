# C15 Corrective-003 Operator Prep Independent Acceptance Failure Adjudication — 2026-09-28

## Status

```text
C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP
= ACCEPTANCE_FAIL / blocker=3
= HISTORICAL_FAILED_EXACT / IMMUTABLE

C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-001
= READY

C15-RCC-RES-A-RERUN-004-CORRECTIVE-003
= BLOCKED_ON_OPERATOR_PREP
```

This is a PM governance adjudication.

It does not repair PR #281.
It does not merge Operator Prep.
It does not release a Resident.
It does not authorize Core changes.

## Exact failed Operator Prep

Candidate:

- PR #281
- exact head: `10901d467679b70437ae112747eab81f889fd5cb`
- parent: `abb8b435e5187c7c6c2f4332aea37cd805b4a53c`
- tree: `db79761216529cf83f217ab00c937bc79806a510`

Independent Acceptance:

- review-only PR #283
- exact review head: `e3394da5d607e34c0286c16a11837ac7ea173a56`
- verdict: `ACCEPTANCE_FAIL / blocker=3`

Reviewer frozen probe identities include:

- `probe_git_scope_and_packet_head.py`
  SHA-256 `4f9c9a19e739522ac9fcae9f3ce715d81309b4c9a57158bdb2b04310272dce98`
- `probe_exchange_adversarial.py`
  SHA-256 `69a5f31fe40e45506da7837e3a41354c1ae91084c763b498099d65475f1c584f`

The exchange probe preserved RED:

```text
published-overwrite:
FAIL: accepted idempotent replay over tampered file
```

PR #281 and PR #283 remain immutable historical evidence.

No hash-swap or post-hoc evidence repair is permitted.

## PM scope verification

PM independently verified PR #281 contains 56 changed files and all 56 are under the single Operator Prep package, with zero Core/tests/workflow/fixture/evaluator/release-source drift.

The IA report phrase `changed paths: 4` is not used as the authoritative PR-wide file count. It does not affect the three binding blockers below because PM independently verified the full candidate scope.

## IA-OP-001 — VALID_BINDING_BLOCKER

### Finding

Exact path:

`harness/aios_exchange/responses.py`

In `ResponsePublisher.publish_bytes()`, when a durable `response_published` ledger record already exists, the implementation verifies only:

- ledger `response_sha256` equals the digest of the replay input.

It does not first verify that the already-published response file on disk:

- still exists; and
- still hashes to the durable ledger digest.

Therefore:

1. publish response R;
2. mutate the published response file to R';
3. call `publish_bytes(..., R)` again;

can return:

`idempotent_replay=True`

even though the durable artifact has been overwritten/tampered.

A later consume fails, but the publication boundary already returned successful idempotent replay.

### PM adjudication

`IA-OP-001 = VALID_BINDING_BLOCKER`

Gate A requires duplicate/overwrite ambiguity to fail closed at the publication operation itself.

### Minimal corrective scope

In the existing-record/idempotent branch, before returning success:

- require response file existence;
- read exact existing bytes;
- require on-disk SHA-256 == durable ledger `response_sha256`;
- require replay input digest == durable ledger digest;
- otherwise raise the mechanical fail-closed error;
- never adopt, rewrite, heal, or overwrite the file in this branch.

Add a regression proving tampered/missing published bytes cannot receive idempotent success.

No Core or Resident change is authorized.

## IA-OP-002 — VALID_BINDING_BLOCKER

### Finding

Exact path:

`bootstrap/bootstrap_runtime.sh`

The CPython/zlib/OpenSSL/SQLite source artifacts are pre-pinned by hashes.

The Python package wheel closure is not.

`ensure_wheelhouse()`:

1. asks the live package index to download `pydantic==2.13.5`, `pytest==8.4.2`, and their dependency closure;
2. only after those bytes have been downloaded does it calculate hashes;
3. writes those observed hashes into `requirements.hashes.txt`;
4. then installs from that freshly-created file.

This detects later local mutation, but it does not provide an immutable trust root for the initial acquisition.

A different artifact served under the same version could become the newly accepted hash.

### PM adjudication

`IA-OP-002 = VALID_BINDING_BLOCKER`

A frozen/reproducible launch environment requires dependency artifact identities to be fixed before acquisition.

### Minimal corrective scope

Create a source-controlled, pre-download wheel lock/trust-root file containing the complete Python dependency closure needed for the qualified runtime.

For every distribution, freeze before download:

- normalized project name;
- exact version;
- exact wheel filename/platform tag;
- SHA-256;
- optional source URL/index identity if useful.

The bootstrap must:

- download only the exact locked artifacts;
- verify each artifact against the pre-frozen SHA-256 before use;
- reject unexpected/missing/additional wheels;
- install only from the verified wheelhouse;
- never generate the trust-root hashes from the just-downloaded bytes.

A post-download local SHA256SUMS may still exist as evidence, but it is not the trust root.

No Core or Resident change is authorized.

## IA-OP-003 — VALID_BINDING_BLOCKER

### Finding

Exact paths:

- `harness/operator_tools/gate_runner.py`
- `evidence/gates/gate_a_result.json`
- `gate_b_result.json`
- `gate_c_result.json`
- `gate_d_result.json`

The real collect-only output contains:

- Gate A: 19 test node IDs;
- Gate B: 7;
- Gate C: 2;
- Gate D: 5.

But every result JSON records:

- `test_count: 0`
- `test_ids: []`

because the parser accepts a line only when it:

- contains `::`; and
- ends in `)`.

The actual `pytest --collect-only -q` node IDs do not end in `)`.

### PM adjudication

`IA-OP-003 = VALID_BINDING_BLOCKER`

Frozen test enumeration metadata must agree with the hashed collect-only evidence.

### Minimal corrective scope

Fix the enumeration parser so it records the actual pytest node IDs.

The gate runner must fail closed if:

- collect-only command fails;
- parsed node ID list is empty for a gate expected to have tests;
- parsed count differs from pytest's collected count;
- executed PASS/FAIL totals are inconsistent with the frozen enumeration.

Regenerate all A/B/C/D evidence after the fix.

Do not retroactively rewrite #281 evidence.

## Corrective discipline

Task:

`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-001`

must repair only IA-OP-001/002/003.

Before candidate modification:

1. create a new independent corrective probe suite targeting exactly these three blockers;
2. freeze probe sources + SHA-256 + expected outcomes;
3. run probes against failed exact #281 `10901d467679b70437ae112747eab81f889fd5cb`;
4. preserve the expected RED evidence.

Then build a new Operator Prep candidate from current live main by carrying forward the exact failed Operator Prep package and applying only the three authorized corrections.

Do not modify PR #281.

## Required post-fix proof

The new candidate must provide:

- targeted IA-OP-001/002/003 corrective probes GREEN;
- full Gate A/B/C/D rerun under CPython 3.12.14 / Pydantic 2.13.5;
- clean scratch bootstrap using the pre-pinned wheel trust root;
- correct non-empty test enumeration metadata;
- regenerated harness/freeze manifests;
- regenerated packet audit;
- a new `RESIDENT_SAFE_LAUNCH_PACKET.json` with status `PREP_REVIEW_READY`;
- no real Resident execution;
- zero Core/tests/fixture/evaluator/release-source drift.

## Downstream

Until the new Operator Prep Corrective-001 receives fresh Independent Acceptance PASS and PM integration:

- `C15-RCC-RES-A-RERUN-004-CORRECTIVE-003` = BLOCKED;
- real Resident release/run = BLOCKED;
- persistence Corrective-003 = BLOCKED;
- Resident B/C = BLOCKED;
- evaluator / C15 close = BLOCKED.
