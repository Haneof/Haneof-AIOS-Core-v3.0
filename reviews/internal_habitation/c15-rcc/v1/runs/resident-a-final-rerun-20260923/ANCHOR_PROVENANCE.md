# C15 Resident A Anchor Provenance Proof

Status: **VERIFIED — METADATA-ONLY CORRECTION**

## Canonical identity

- Frozen C15 Core anchor: `bcd6bf353126318f9a97076b52ec1740d43f35a4`
- Governance-only main child used as the evidence-branch baseline: `6abfd4d19d03a60a81b7ca336efbe3c9c726b3bb`
- Original PR #117 evidence head: `67a687477cfbe54d3bd251d204f064a7d4ab8ca3`
- Original PR #117 evidence-head parent: `6abfd4d19d03a60a81b7ca336efbe3c9c726b3bb`
- Superseded manifest/report label: `30e0dca1f08c49ed9bacc66b49313ac536d512af`

## Git proof

1. GitHub resolves `bcd6bf353126318f9a97076b52ec1740d43f35a4` and `6abfd4d19d03a60a81b7ca336efbe3c9c726b3bb`; `6abfd4d19d03a60a81b7ca336efbe3c9c726b3bb` is the direct child of `bcd6bf353126318f9a97076b52ec1740d43f35a4`.
2. The exact compare `bcd6bf353126318f9a97076b52ec1740d43f35a4...${baseline}` is one commit ahead and changes only `governance/C15_RCC_HARDENING_FINAL_ANCHOR_HANDOFF_2026-09-23.md`. It changes zero files under `src/aios_core/**` and zero frozen cognition-semantic files.
3. Original PR #117 head `67a687477cfbe54d3bd251d204f064a7d4ab8ca3` is one commit on top of `6abfd4d19d03a60a81b7ca336efbe3c9c726b3bb`; its changed files are confined to `reviews/internal_habitation/c15-rcc/v1/runs/resident-a-final-rerun-20260923/**`. It changes zero files under `src/aios_core/**`.
4. GitHub cannot resolve `30e0dca1f08c49ed9bacc66b49313ac536d512af` as a commit, branch, or comparable Git object in this repository. That value appears only in the original `ARTIFACT_MANIFEST.json` and `REPORT.md` anchor labels; it does not appear in the driver source, release state, restart state, stage records, checkpoints, decisions, World, or index artifact names.
5. The recorded runtime capability catalog exposes the frozen hardening contract, including `valid_time`, `unknown_items`, `counter_evidence_refs`, and forward-only `revise_claim` inputs.

## Decision

The evidence execution Core is canonically identified by the frozen Core tree at `bcd6bf353126318f9a97076b52ec1740d43f35a4`. The intervening `6abfd4d19d03a60a81b7ca336efbe3c9c726b3bb` commit is governance-only and Core-tree equivalent.

Therefore `30e0dca1f08c49ed9bacc66b49313ac536d512af` is classified as an erroneous metadata label, not a distinct execution baseline. This correction changes only:

- `ARTIFACT_MANIFEST.json`
- `REPORT.md`
- this proof file
- PR #117 descriptive metadata

The frozen `private_world.sqlite`, `world_index.sqlite`, release/restart state, cursor events, stages, checkpoints, and Resident-authored decisions remain byte-identical.
