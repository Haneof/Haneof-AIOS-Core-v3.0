# Corrective-002 candidate-code checkpoint — NOT FINAL REVIEW READY

This checkpoint precedes the final candidate-tier rerun and final-packet audit tier.

- Historical #286 H2 and all frozen C4–C9 v1/v2 probe sources/results are preserved.
- Genuine v2 H2 baseline: 80 failed / 23 passed (all six groups RED).
- Candidate iteration 2: unchanged v2 probes 103/103 PASS.
- Initial C1–C3 regression GREEN; initial full gates 24/7/2/5 PASS.
- New empty-root build `/home/user/.cache/c002/clean-runtime-002` exited 0.
- Repairs and packet tooling complete; final identity-bound reruns remain pending.
- Earlier H2 evidence was relocated unchanged to `historical_h2/package_evidence`;
  its packet is preserved alongside it. Those are not current candidate results.
- Candidate iteration 1 (101 PASS / 2 FAIL) and Gate iteration 1 (A:22/24)
  are retained, not overwritten. Gate A's diagnostic seq regression was fixed.
- A15's old worker published an unrelated dictionary and then resumed a different
  snapshot: forbidden by C4. The worker now publishes that test's exact snapshot;
  assertion and node IDs are unchanged. Worker is isolated in harness/tests/synthetic.
- No frozen probe/expected outcome, Core, product tests, fixture/evaluator/release,
  governance or real Resident state has been modified.

Final packet remains PREP_REVIEW_READY, never launch authorization. No real
Resident, World/session, cursor reveal, release-state or Phase-A run was created.
