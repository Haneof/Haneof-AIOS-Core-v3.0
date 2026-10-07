# Known Limitations

The following inherent limitations exist within this formal evidence execution boundary:

1. **Pre-Freeze Future Identity Embedding**: The committed packet cannot embed the future `final run ID` prior to the exact freeze, as it is dynamically allocated by GitHub Actions upon dispatch.
2. **Authoritative Identity Derivation**: The final run, artifact, and pin authoritative identity are strictly secured and fixed via GitHub immutable metadata, the exact pin hash, whole-run seal checks, and subsequent PM fresh verification.
3. **Probe Authorship Status**: The author-owned probes and evidence gates executed in this run do **NOT** constitute Fresh Independent Acceptance. They are strict technical prerequisites for PM adjudication.
4. **Historical PR Status**: Historical failed or "technical green but PM-failed" PRs (e.g., #341, #342, #343) **MUST NOT** be merged.
5. **Single Dispatch Limitation**: This finalization requires exactly ONE `workflow_dispatch`. Any failure immediately blocks the window and requires PM adjudication; no implicit reruns or debugger loops are permitted on the frozen candidate.
