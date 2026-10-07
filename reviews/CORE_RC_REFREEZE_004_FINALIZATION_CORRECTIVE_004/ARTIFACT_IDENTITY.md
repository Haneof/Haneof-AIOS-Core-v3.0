# Artifact Identity Contract

This document mathematically bounds the resulting evidentiary artifact to prevent untracked replacement or injection.

* **Expected Artifact Name**: `core-rc-refreeze-004-finalization-corrective-004-evidence`
* **Expected Task Identity**: `CORE-RC-REFREEZE-004-POST-INTEGRATION-FINALIZATION-CORRECTIVE-004`
* **Exact Run/Head Binding**: The artifact MUST be cryptographically bound to the EXACT `workflow_dispatch` run ID and the exact frozen `HEAD` SHA.
* **Digest Authority**: The authoritative SHA256 digest MUST come strictly from the GitHub Actions artifact immutable metadata API.
* **Expiration Status**: `expired=false`

*(The actual digest, ID, and size will be recorded directly into the FINAL_REPORT after the workflow has concluded.)*
