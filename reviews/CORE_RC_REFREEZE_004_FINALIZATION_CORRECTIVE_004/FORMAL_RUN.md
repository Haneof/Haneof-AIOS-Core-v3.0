# Formal Run Contract

**NO_AUTHORITATIVE_FINAL_RUN_EMBEDDED_PRE_FREEZE**

This document establishes the exact cryptographic and systemic contract that defines a mathematically successful formal run. A speculative or partial pass is not recognized.

## Formal Success Contract
The execution must satisfy ALL of the following deterministic conditions exactly once:

* `event` = `workflow_dispatch`
* `attempt` = `1`
* `branch` = EXACT `release/core-rc-refreeze-004-finalization-corrective-004-window41`
* `candidate SHA` = EXACT matched candidate HEAD at freeze.
* `overall result` = `SUCCESS`
* `Job A (rc004-freeze-gate)` = `SUCCESS`
* `Evidence Integrity Gate` = `SUCCESS`
* `Publisher (rc004-mandatory-pin-publisher)` = `SUCCESS`
* `Whole-run identity seal` = `SUCCESS`
* `Newer canonical successor run` = NONE (No newer run exists on the branch).
