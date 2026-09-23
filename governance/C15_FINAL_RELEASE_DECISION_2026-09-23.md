# C15_FINAL_RELEASE_DECISION

> Historical A acceptance / original B-start release. Accepted A and its immutable hashes remain authoritative. The later `C15_RCC_RES_B_CORRECTIVE_DECISION_2026-09-23.md`, once integrated into main, supersedes only the unconditional B-start authorization below: #121 is not accepted, operator preflight and independent release must precede a fresh B. Until that integration is resolved, do not start a duplicate B from this historical status. Consult the current task-board snapshot; do not merge private evidence PRs.

Historical status at issuance: **PASS — C15-RCC-RES-B-001 READY**
Decision date: 2026-09-23  
Authority: C15 Release PM + Independent Governance Integrator

## Scope

This is the release decision from canonical Resident A Phase A into fresh-context Resident B. It is not the final C15 close: Resident B, Resident C, independent evaluation, and C15 close remain separate gated tasks.

## Canonical anchors

- Frozen C15 Core anchor: `bcd6bf353126318f9a97076b52ec1740d43f35a4`
- Reviewed main before this governance close: `6abfd4d19d03a60a81b7ca336efbe3c9c726b3bb`
- Canonical Resident A evidence: PR #117 @ `3e51f728d7959048b75fea01d405bc837b0e8185`
- PR #117 disposition: **OPEN / UNMERGED / PINNED**

`6abfd4d19d03a60a81b7ca336efbe3c9c726b3bb` is the direct governance-only child of the frozen Core anchor. Exact Git compare shows one added governance handoff file and zero `src/aios_core/**` changes.

## Anchor provenance decision

**Case A — metadata-only mismatch.**

The original `anchor_commit=30e0dca1f08c49ed9bacc66b49313ac536d512af` cannot be resolved by GitHub as a commit, branch, or comparable Git object in this repository. It appeared only in the original manifest/report labels.

The PR #117 branch is rooted at `6abfd4d19d03a60a81b7ca336efbe3c9c726b3bb`; its original evidence commit changed only the Resident A run package. The frozen Core tree is therefore the tree at `bcd6bf353126318f9a97076b52ec1740d43f35a4`.

Correction commit `3e51f728d7959048b75fea01d405bc837b0e8185` changed only `ANCHOR_PROVENANCE.md`, `ARTIFACT_MANIFEST.json`, and `REPORT.md`. Frozen World, index, release/restart state, cursor events, stages, checkpoints, Resident decisions, and cognition remained byte-identical.

## Resident A acceptance

| Gate | Verdict | Verified evidence |
|---|---|---|
| Execution boundary | PASS | Cursors 1..13 present and ordered; 13 unique durable receipts; `last_acked_sequence=13`; `next_sequence=14`; no pending reveal; Phase A process permanently stopped; final World/index `88/88`. |
| Freshness | PASS | Driver fails if World/index already exist; session is `resident-a-final-rerun-20260923-001`; PR #101 session, claim IDs, World digest, transcript markers, and old cognition are absent. Deterministic platform fixture Observation IDs are expected to repeat; user Observation and cognition IDs are new. |
| User understanding | PASS | `clm_d95e2508b26a0292b94a7a59` advanced rev1→rev5 as user boundaries became more precise. |
| Relationship / role | PASS | `clm_776c4bbfaab7540a23c418cb` advanced rev1→rev3 and explicitly avoided promoting one collaboration into a stable trust level. |
| Strategy | PASS | `clm_52276ec49967d10c72861d07` formed only after a real outcome plus user feedback, then advanced rev1→rev3 with deletion and status-evidence rules. |
| Communication experience | PASS | `commexp_f3778968f998cd698281e0ee@1` is grounded in the staging result and the user's accepted reaction. |
| Operation experience | PASS | `opexp_4c982ed6ba398f2a8404e4d0@1` was created only after a complete queued→rejected→successful registry episode; two earlier reviews correctly remained silent. |
| Revision lineage | PASS | Every successful revision records exact old/new revisions, a new EvidenceSet, pinned leaf refs, and increasing World revisions: UU 1→2→3→4→5; Relationship 1→2→3; Strategy 1→2→3. |
| UNKNOWN discipline | PASS | READY_FOR_UPLOAD/queued was not reported as completed; checksum mismatch remained rejected; completion was recognized only after tag+digest+PUBLISHED evidence. The cursor-13 runbook remained DRAFT and was not promoted to reviewed, accepted, executed, or Outcome-backed. |
| Package integrity | PASS | Manifest binds 121 artifacts; World `sha256:9ff2b13cc1ec6e4d61a7910b4177ed3e1f25cfc47df8e18481a0199dd1aad395`; index `sha256:55282a61d714f732f1b10fa6b450853f8425b5c9f741090fcaad0f1e673a6643`; release-state `sha256:b626cdd7d8ee16bcc9123ef8641bb05637d73d713023a471a74d7f6a392e052e`; manifest `sha256:cc79379f4bcc7c655d36ce8700fa24375c6c2bee84a4d9f1144e4314ece09899`. |

## Resident B release

`C15-RCC-RES-A-RERUN-001 = DONE / ACCEPTED`.

`C15-RCC-RES-B-001 = READY`.

Resident B must:

- start in a completely new model process/session;
- receive only the exact durable World, rebuilt/restored index, legally required runtime state, and release-state receipt chain;
- receive no Resident A chat transcript, report, decisions, checkpoints, prose handoff, hidden summary, evaluator material, or fixture future;
- verify the exact digests before Phase B initialization;
- execute only sealed cursor 14..22 and then stop permanently.

## Remaining risks

1. `execution_attestation_ref` and `trusted_model_identity_artifact` remain null. This does not block Resident B, but R6 replacement-model validity cannot be awarded from PR #117 alone.
2. Three capability argument errors remain honestly preserved: `expand_recall`, `search_world`, and the first `commit_operation_experience` schema attempt. They produced no invalid durable write; the operation experience succeeded only after a legal resubmission.
3. The cursor-8 decision note says the failed `search_world` call “confirmed” absence. The user-facing answer was nevertheless grounded in the latest already-visible World fact and correctly remained “not completed.” Treat the wording as a non-blocking audit note, not search evidence.
4. PR #117 must remain OPEN / UNMERGED / PINNED until the later evaluator/governance flow disposes of it.
5. The C15 cognition semantic freeze remains ACTIVE through `C15-RCC-EVAL-001`; any semantic Core change requires a new governance decision.

## Final ruling

Resident A Phase A is canonical and accepted on the sole frozen Core anchor `bcd6bf353126318f9a97076b52ec1740d43f35a4`.

The release gate to Resident B is open.
