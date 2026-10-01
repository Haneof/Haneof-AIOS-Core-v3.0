# REPRO — WINDOW 14 independent acceptance

Repository: `Haneof/Haneof-AIOS-Core-v3.0`
Candidate: `5ad0524c425592210ff184e00ad52abb2c14e366` (parent `a49c1e6874ecb92ae4dc4783d07d733fdc19fa5d`,
tree `53064b3022254dab33c7793a0a6306c71e3df2b2`, base `25591825d88e98f30dfd3de1c7e7cbc6e53267dd`)

## 0. Environment

```bash
python3 -m venv .venv
.venv/bin/python -m pip install 'pydantic==2.13.5' 'pytest==8.4.2'
# IA results produced on CPython 3.11.2 / SQLite 3.40.1 / OpenSSL 3.0.20 (see formal_environment.md)
```

## 1. Frozen probes — verify hashes, then execute

```bash
sha256sum -c reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_IA/reviewer_probes/SHA256SUMS
PYTHONPATH=src .venv/bin/python \
  reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_IA/reviewer_probes/window14_independent_attack.py
# expected: 7 probes, failures=3 -> IA14-ORACLE-001, IA14-NONCE-001, IA14-NS-001 FAIL

sha256sum -c reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_IA/reviewer_probes/SHA256SUMS_SUPPLEMENTARY
PYTHONPATH=src .venv/bin/python \
  reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_IA/reviewer_probes/window14_supplementary_probes.py
# expected: S1, S2 PASS

sha256sum -c reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_IA/reviewer_probes/SHA256SUMS_S3
PYTHONPATH=src .venv/bin/python \
  reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_IA/reviewer_probes/window14_s3_stale_capability_rotation.py
# expected: failures=2 -> S3b unattachable + rotated binding unattachable (BLK-W14-004)
```

Probe revision history (harness-only fixes, expectations unchanged):
`reviewer_probes/PROBE_REVISION_LOG.md`, `reviewer_probes/PROBE_CONTRACT.md`.

## 2. Baseline RED reproduction (56 failed / 5 passed)

```bash
git worktree add --detach /tmp/w14_baseline_wt 25591825d88e98f30dfd3de1c7e7cbc6e53267dd
cp tests/integration/late_trusted_return_fixture.py \
   tests/integration/test_core_background_late_trusted_return_001.py \
   tests/integration/test_core_background_late_trusted_return_001_not_submitted.py \
   tests/integration/test_core_background_late_trusted_return_001_adversarial.py \
   /tmp/w14_baseline_wt/tests/integration/
cd /tmp/w14_baseline_wt
PYTHONPATH=src /home/user/Haneof-AIOS-Core-v3.0/.venv/bin/python -m pytest -o addopts='' -q --tb=line \
  tests/integration/test_core_background_late_trusted_return_001.py \
  tests/integration/test_core_background_late_trusted_return_001_not_submitted.py \
  tests/integration/test_core_background_late_trusted_return_001_adversarial.py
# expected: 56 failed, 5 passed
```

Frozen probe hashes must match `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001/baseline_probe_hashes.txt`.

## 3. Candidate regression (fresh IA executions)

```bash
PYTHONPATH=src .venv/bin/python -m pytest -o addopts='' -q \
  tests/integration/test_core_background_late_trusted_return_001.py \
  tests/integration/test_core_background_late_trusted_return_001_not_submitted.py \
  tests/integration/test_core_background_late_trusted_return_001_adversarial.py   # 61 passed

PYTHONPATH=src .venv/bin/python -m pytest -o addopts='' -q \
  tests/integration/test_core_background_trusted_return_recovery_001.py \
  tests/integration/test_core_background_trusted_return_adversarial_001.py \
  tests/integration/test_core_background_trusted_return_r5_001.py \
  tests/integration/test_core_background_trusted_return_r5_conflicts_001.py \
  tests/integration/test_core_background_trusted_return_corrective_001_process_loss.py \
  tests/integration/test_core_background_trusted_return_corrective_001_store_fail_closed.py \
  tests/integration/test_core_background_trusted_return_corrective_001_capability_replay.py \
  tests/integration/test_core_background_response_recovery_001.py \
  tests/integration/test_core_background_response_recovery_001_corrective_001.py \
  tests/integration/test_core_background_response_recovery_001_corrective_002_authenticity.py \
  tests/integration/test_core_background_response_recovery_001_corrective_002_recovery.py \
  tests/integration/test_core_gap_fix_002_background_attempts.py \
  tests/runtime/test_background_model_attempt.py \
  tests/runtime/test_cognitive_runtime_trusted_return.py \
  tests/runtime/test_turn_execution_recovery.py   # 249 passed

PYTHONPATH=src .venv/bin/python -m pytest -o addopts='' -q   # 1059 passed (full history)
```

## 4. CI validation gates

```bash
# full-history resident split gate
PYTHONPATH=src .venv/bin/python -m pytest -o addopts='' -q tests/c15_persistence/test_resident_surface.py
# expected: 1 passed

# shallow clone must SKIP, never PASS
git clone --depth 1 file:///home/user/Haneof-AIOS-Core-v3.0 /tmp/w14_shallow_clone
cd /tmp/w14_shallow_clone
PYTHONPATH=src /path/to/.venv/bin/python -m pytest -o addopts='' -q -rs tests/c15_persistence/test_resident_surface.py
# expected: 1 skipped ("Skipped, NOT passed")

# historical Persistence C003 construction (independent compare)
git diff --shortstat 016a2f7db5ed01b41fc614701079c507d2c2c02e 19476641be95e666068e6299f42df9a411f4c0ba
# expected: 56 files changed, 12433 insertions(+)
git diff --name-only 016a2f7db5ed01b41fc614701079c507d2c2c02e 19476641be95e666068e6299f42df9a411f4c0ba -- src/aios_core | wc -l
# expected: 0
```

## 5. Formal CI identity (fresh, not from repo markdown)

```bash
gh api repos/Haneof/Haneof-AIOS-Core-v3.0/actions/runs?head_sha=5ad0524c425592210ff184e00ad52abb2c14e366
gh api repos/Haneof/Haneof-AIOS-Core-v3.0/actions/runs/36680355119/jobs
gh api repos/Haneof/Haneof-AIOS-Core-v3.0/check-runs/109774221264/annotations
# run 36680355119 / check 109774221264 on exact head; 17/17 workflows success
# run 36679598965 (cited in candidate commit message) has head_sha=a49c1e68... = PARENT
```
