# WINDOW 20 Reviewer Probe Revision Log (`PROBE_REVISION_LOG.md`)

## Revision 1 (Initial Pre-Execution Freeze — `v1`)

- **Revision:** `v1` (preserved verbatim at `reviewer_probes/window20_independent_attack_v1.py`, `reviewer_probes/SHA256SUMS.v1`, raw log `raw/candidate_w20_probes_v1_defective.txt`)
- **SHA-256:** `0381c6ceef2d0d8eed28d78b452fa8ae7770747537d9ae3ad3ad4ab8e3f87375`
- **Reason:** Initial pre-execution freeze of 4 reviewer-owned acceptance probes (`IA20-MINT-003`, `IA20-MINT-004`, `IA20-OBJGRAPH-002`, `IA20-WINDOW-001`).
- **Outcome:** `DEFECTIVE_HARNESS_REVISION` — the run aborted at the first probe with `KeyError: 'provider'`. Root cause: `BackgroundModelRequestBinding` rows persist only `attempt_id, subject_id, work_kind, work_id, model_round_index, outbound_request_fingerprint, relay_id, bound_at`; the probe wrongly assumed the readable binding row carried `provider` / `model` / `provider_request_id`. No attack was executed and no expectation was evaluated.

## Revision 2 (Binding-Identity Read Harness Fix — `v2`)

- **Old SHA-256 (`v1`):** `0381c6ceef2d0d8eed28d78b452fa8ae7770747537d9ae3ad3ad4ab8e3f87375`
- **Classification:** `HARNESS_FIX_ONLY` (zero expected-outcome changes; all four probe IDs and all frozen expectations are unchanged)
- **Fix:** forged directives now carry attacker-chosen provider/model/request_id (as the frozen Window 17 `IA17-MINT-001` attack did), while the durable binding row is read only for reporting `relay_id` / `outbound_request_fingerprint`.
