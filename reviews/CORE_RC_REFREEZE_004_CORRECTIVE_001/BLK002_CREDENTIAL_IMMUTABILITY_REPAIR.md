# BLK002_CREDENTIAL_IMMUTABILITY_REPAIR

Job A is read-only (contents:read, pull-requests:read). actions/checkout@v4 sets persist-credentials:false and the workflow mechanically rejects persisted local git extraheaders. workflow_dispatch is pinned to the canonical Window 26 branch.

After all candidate-controlled execution, the terminal gate rechecks local/remote exact head, frozen HEAD/root/Core/tests/workflows/pyproject objects, frozen tracked/staged mutation, checkout credential absence, fresh current main, and protected implementation/package/test/existing-workflow drift.
