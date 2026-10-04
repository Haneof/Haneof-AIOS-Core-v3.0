# Formal workflow attack freeze

- Probe: `workflow_false_green_probe.py`
- Candidate source: `.github/workflows/core-rc-refreeze-004-formal-gate.yml`, lines 324-342.
- Attack: feed the exact classifier a pytest usage/collection-style non-zero exit with no `FAILED tests/...` summary records.
- Expected invariant: a non-test-failure pytest exit must block the formal gate.
- Expected candidate behavior: the classifier ignores `pytest_exit`, emits both downstream-debt PASS markers, and exits zero. This is a false-green path.

