# Window 05 Independent Acceptance — exact reproduction commands

All commands run from the repository root with the working tree at the exact
candidate `19476641be95e666068e6299f42df9a411f4c0ba` (detached checkout).
Environment: `/home/user/.venv-ia` = CPython 3.11.2 / pydantic 2.13.5 /
pytest 8.4.2 / SQLite 3.40.1 (DISCLOSED non-formal; formal 3.12.14 unobtainable
in the sandbox — see report §8).

```bash
PY=/home/user/.venv-ia/bin/pytest
UN=/home/user/.venv-ia/bin/python

# [0] identity
git fetch origin
git rev-parse origin/main            # 016a2f7db5ed01b41fc614701079c507d2c2c02e
git rev-parse origin/pr/299          # 19476641be95e666068e6299f42df9a411f4c0ba
git checkout --detach origin/pr/299
git diff --stat origin/main origin/pr/299            # 56 files, +12433, -0
git diff origin/main origin/pr/299 -- src/aios_core/ pyproject.toml   # empty

# [1] enumeration (bare pytest, the CI invocation shape)
$PY --collect-only -q                            # 997 total; c15_persistence = 78
git worktree add --detach /tmp/ia/main-tree origin/main
(cd /tmp/ia/main-tree && $PY --collect-only -q)  # 919 total; per-file diff vs candidate = only the new suite

# [2] full repository suite (CI parity invocation)
$PY -q --tb=short                                # 997 dots, 0 failures/errors, exit 0

# [3] persistence suite (78)
$PY tests/c15_persistence                        # 78 passed

# [4] frozen historical journal contract (13, frozen unittest invocation)
$UN -m unittest tests.c15_persistence.test_journal    # Ran 13 tests ... OK

# [5] killpoints (5) / binding matrix (23 collected, 15 probe ids) / regressions (6)
$PY tests/c15_persistence/killpoints
$PY tests/c15_persistence/test_corrective_003_binding_blockers.py
$PY tests/c15_persistence/test_corrective_003_regressions.py

# [6] trusted-return focused suites
# 6a. CORE-RC-REFREEZE-002 formal gate focused list (9 files)
$PY tests/integration/test_core_background_response_recovery_001_corrective_002_authenticity.py \
    tests/integration/test_core_background_response_recovery_001_corrective_002_recovery.py \
    tests/integration/test_core_background_response_recovery_001.py \
    tests/runtime/test_cognitive_runtime_trusted_return.py \
    tests/integration/test_core_headless.py \
    tests/integration/test_core_recovery.py \
    tests/integration/test_core_scale_semantics.py \
    tests/integration/test_core_gap_fix_002_background_attempts.py \
    tests/runtime/test_turn_execution_recovery.py                       # 98 passed
# 6b. CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001 gate: r5 + focused
$PY -o addopts='' -q \
    tests/integration/test_core_background_trusted_return_r5_001.py \
    tests/integration/test_core_background_trusted_return_r5_conflicts_001.py   # 24 passed
$PY -o addopts='' -q \
    tests/integration/test_core_background_trusted_return_recovery_001.py \
    tests/integration/test_core_background_trusted_return_adversarial_001.py \
    tests/integration/test_core_background_response_recovery_001.py \
    tests/integration/test_core_background_response_recovery_001_corrective_001.py \
    tests/integration/test_core_background_response_recovery_001_corrective_002_authenticity.py \
    tests/integration/test_core_background_response_recovery_001_corrective_002_recovery.py \
    tests/runtime/test_background_model_attempt.py                      # 99 passed

# [7] C15 preflight / operator regression (131)
$PY tests/preflight

# [8] workspace portability
$UN -m unittest tests.c15_persistence.test_journal -v   # with HOME + C15_PERSISTED_WORKSPACE
      # set to foreign dirs (probe IA-13); 13/13 OK
C15_PERSISTED_WORKSPACE=<fresh dir> $PY tests/c15_persistence   # 78 passed

# [9] scope gate
$UN tests/c15_persistence/probe_core_boundary.py 2>/dev/null
PYTHONPATH=src $UN tests/c15_persistence/probe_core_boundary.py   # exit 2, CORRECTIVE_CONVERGENCE_BLOCKED (by design)

# [10] reviewer-independent adversarial probes (frozen sources, SHA-256 below)
$PY ia_independent_acceptance/ia_probes.py -v     # 15 passed
```

Frozen reviewer probe sources (SHA-256, recorded before each execution):

```text
9795e3844f1b3ec3868ab537344085f5d9b127f7b8936c06fa271bd0d747f780  ia_independent_acceptance/ia_probes.py   (v1 draft — import bootstrap gap in the reviewer file, never executed green)
08cc8a613f6e69eba2216e18067e53cc1b0022475fb9d5a220403e5a84c31221  ia_independent_acceptance/ia_probes.py   (v2 — bootstrap added; 10/15 pass, 5 reviewer-probe bugs)
2fd99a3ded6a2c44e7f293c8c4480b5a1424e62834ab6471d77a8d7a39082da5  ia_independent_acceptance/ia_probes.py   (v3 — reviewer probe bugs fixed; IA-14 converted to observation probe; 14/15 pass)
2e01947e2194f4eef73ec1b6fc5389bc465a1dfe11a30e769bc7a3ac50b68d72  ia_independent_acceptance/ia_probes.py   (v4 FINAL — assistant-output count semantics fixed; 15/15 pass)
```

The v2→v4 changes were mechanical fixes to the reviewer's own probe code
(counter default on absent key, wrong remote-commit path, missing `--force`
for a deliberate ref rewind, unittest stderr stream, assistant-output count
semantics matching the durable World schema) plus the documented IA-14
conversion (asserting strict rejection would encode a requirement that is not
in the frozen contract; observed behaviour is recorded instead and classified
in the report). No candidate-affecting expectation was tuned in any direction.
