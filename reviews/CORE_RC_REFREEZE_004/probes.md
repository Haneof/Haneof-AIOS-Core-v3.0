# CORE-RC-REFREEZE-004 — Frozen Reviewer Probe Identity and Results

Status: **PASS — all three canonical reviewer probes re-extracted fresh and green on the frozen target.** Prior-window numbers were not inherited.

## Provenance (extracted from canonical reviewer commits, never from author copies)

| Probe | Reviewer commit | Path | Git blob | SHA-256 |
|---|---|---|---|---|
| Window 20 Suite A `window20_independent_attack.py` | `220311759e88fb3948ad3f4dba655058e0f392a8` | `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_002_IA_WINDOW_20/reviewer_probes/window20_independent_attack.py` | `527edd8d92243cabc417f176c0f7c4f6c358e65c` | `ec1dc5c2c5406d5d9e74825f62e0a17fb80f8ebd6dc250817fa048511ce292b5` |
| Window 20 Suite B `window20_migration_rsa_attack.py` | `220311759e88fb3948ad3f4dba655058e0f392a8` | `.../reviewer_probes/window20_migration_rsa_attack.py` | `867f0ee993595c2d334a3940ad66308166693c97` | `769242465817f31734661ba7ba9c3d5f7d06b8d3f5235d72d2026956d9b98eb1` |
| Window 17 `window17_independent_attack.py` | `e4161dd0ad0a2f825461311a1c8c5ff8234a07f8` | `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_001_IA_WINDOW_17/reviewer_probes/window17_independent_attack.py` | `bb25d184a5cb813ae4058de9a75fa23d9591b041` | `a6db33956bb7bc1e8af19cddd7cebdd320604bba98b6a2b906fd1eb363fba0c3` |

Blobs were resolved with `git ls-tree` and file bytes obtained with `git cat-file blob`; each SHA-256 was checked against the reviewer `SHA256SUMS` before execution. The exact bytes are also archived in `probes/reviewer-*.py` (same SHA-256 values). The reviewer RSA private key is not needed: Suite A/B embed the reviewer public modulus and the suites sign with the reviewer-side key material supplied for the review.

## Execution

Executed against the frozen worktree with `PYTHONPATH=<frozen>/src` and `AIOS_RC_TARGET_ROOT=<frozen>` so the import path is asserted to be below the frozen target.

| Probe | Result | Raw output |
|---|---|---|
| Suite A (W20) | **4 probes, 0 failures** | `raw/local/window20-suite-a.txt` |
| Suite B (W20) | **7 probes, 0 failures** | `raw/local/window20-suite-b.txt` |
| Window 17 | **14 probes, 0 failures** | `raw/local/window17-probe.txt` |

Highlights preserved in the raw files: `IA20-MINT-003/004` refuse minting outside the genuine live-provider frame; `IA20-OBJGRAPH-002` finds no reachable mint callable; `IA20-RSA-TRANSPLANT-001` rejects all 12 bound-field transplants while the genuine reviewer-signed return completes exactly once; `IA20-EXACTONCE-001` shows first-wins + conflict-refusal + effect-free exact replay; `IA17-SIGKILL-001` recovers after a real `SIGKILL` (`exitcode=-9`) with `meters=1` and `replay_blocked=True`.

## Note

The three probes are the §6 binding probes. The Corrective-003 C3 matrix (`tests/integration/test_core_background_late_trusted_return_corrective_003_c3_matrix.py`, 27 enumerated cases) is part of the 928-test Core gate and is re-run by the CI gate.
