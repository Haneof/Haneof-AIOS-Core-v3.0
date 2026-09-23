# C15-RCC-RES-B-001 independent PM execution-evidence review

Date: 2026-09-23
Access: **PM / OPERATOR ONLY — must not be supplied to a blind Resident**
Reviewed main: `ed07b5890909ae09cb2a0849729662b4235c1e3b`
Candidate: [PR #121](https://github.com/Haneof/Haneof-AIOS-Core-v3.0/pull/121) @ `b6e5ac939bef83615292bcf9b9099d76737d82b0`
Verdict: **NOT ACCEPTED — execution evidence insufficient and final index stale**

## Scope

The reviewer did not execute the candidate and is not judging C15 R1–R9 semantics. This is an independent inspection of the submitted evidence package against `reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_B_RUN_CONTRACT.md`, particularly §§5–7. No Core, fixture, private World or historical run was modified. No tests were run locally. GitHub CI conclusions are historical observations, not new test results.

Disposition/next tasks: `governance/C15_RCC_RES_B_CORRECTIVE_DECISION_2026-09-23.md`.

## 1. Anchors and directly verified bytes

A is accepted by `governance/C15_FINAL_RELEASE_DECISION_2026-09-23.md` at PR #117 @ `3e51f728d7959048b75fea01d405bc837b0e8185`. Frozen Core remains `bcd6bf353126318f9a97076b52ec1740d43f35a4`.

The reviewer downloaded the following B files at the **exact candidate commit**, recomputed SHA256 and opened SQLite read-only. The >1 MB index must be downloaded as raw bytes, not inferred from an empty Contents API base64 field.

| File | Bytes | Verified SHA256 |
|---|---:|---|
| private_world.sqlite | 741376 | `73520db502430917f6814c5a1349bdf57f2bd28c6d7170e1bc794c7b71f33f92` |
| world_index.sqlite | 1060864 | `55282a61d714f732f1b10fa6b450853f8425b5c9f741090fcaad0f1e673a6643` |
| release_state.json | 17847 | `bdd50e655964dd82e999bc40dccb511c33b6cb56f4ff0cc00b3b6bc8f7f51c74` |

All three match B's manifest. This confirms the reviewed bytes, **not** the behavioral claims in its prose.

Release-state has 22 receipts including nine B receipts (14–22), `last_acked_sequence=22`, `next_sequence=23`, `pending_reveal=null`. This review does not claim a full independent recomputation of every receipt's fixture payload binding.

## 2. Findings

### B-01: No submitted contemporaneous proof of the claimed Runtime behavior — blocking

Queries show:

- World revision 97; revisions 89–97 are nine input Observations only.
- Five `ingest.c14_resident_fixture_event` operations; four `conversation.commit_user_input` operations for B's session.
- No B-era assistant output, Summary, Wake update, Claim or Experience is present in the new World revisions.
- Metering contains 12 session-null A-era calls at revisions 19–78 and 13 calls for `resident-a-final-rerun-20260923-001` at revisions 1–67. No B-session model metering exists.
- Ten submitted files: six Markdown reports, one manifest, two SQLite files and release-state. No separate B RuntimeSnapshot/directive/capability-result trace or restart checkpoint is submitted.

The normal `FusedTurnRuntime` wires `model_usage_recorder=self._record_model_usage`, which records real model returns through the non-world metering ledger. Even unavailable token telemetry is not an excuse to fabricate or silently omit the call chain.

B's prose asserts search/inspection, responses and behavioral consumption. Those assertions are not independently established by the package. Absence from the submitted package is not a claim that every unsubmitted event was impossible; it means the candidate cannot pass the required evidence gate.

**No new Claim is required.** Silence and retaining existing cognition can be correct. They still require their actual model/runtime execution to be observable. Nor does a fixture-provided later success establish that the Resident performed the earlier action.

### B-02: Final index is unchanged from A and lags B World — blocking

- `world_meta.world_revision = 97`.
- `search_meta.search_watermark_world_revision = 88`.
- Lag = 9; B index SHA256 equals A's index SHA256.

This violates the required final synchronized/rebuilt index and does not demonstrate per-event normal index processing. It is not, by itself, proof of a Core indexing bug. Post-hoc index repair does not establish historical model-visible context.

### B-03: Summary receipt disagrees with durable lineage — secondary

`REVISION_RECEIPTS.md` lists Strategy rev2 at World revision 60. The actual Claim `clm_52276ec49967d10c72861d07` has revisions 1/2/3 at World revisions **14/36/60**. The raw World is authoritative; a prose receipt cannot replace it.

### B-04: Self-acceptance is not independent acceptance

The PR and `ACCEPTANCE_REPORT.md` say PASS/VALID. At review time the PR had no review or comment supplement. The package's own conclusions must be treated as assertions, not PM acceptance or R1–R9 verdicts.

## 3. Gate interpretation and preservation

[Run 35874824798](https://github.com/Haneof/Haneof-AIOS-Core-v3.0/actions/runs/35874824798) is SUCCESS, but `.github/workflows/c15-rcc-fixture.yml` validates fixture infrastructure and selected regressions. It does not audit the B behavioral claims or assert the submitted B index watermark. Therefore the green fixture gate does not cure B-01/B-02.

Keep #121 OPEN / UNMERGED / PINNED / NON-CANONICAL. Do not backfill missing historical model decisions or mutate its SQLite bytes. Keep #117 and prior C14 canonical evidence immutable. C/EVAL/CLOSE remain blocked.

## 4. Reproducible read-only audit queries

Use the raw files at the pinned commit; do not initialize AIOS services against them. For frozen SQLite copies with no pending WAL, `mode=ro&immutable=1` avoids creating sidecars. If a future package has a live WAL, inspect a correctly frozen snapshot including its committed state instead of ignoring the WAL.

```sql
-- private_world.sqlite
SELECT key, value FROM world_meta;
SELECT world_revision, object_id, object_type
FROM object_revisions WHERE world_revision > 88 ORDER BY world_revision;
SELECT result_world_revision, operation_name, session_id
FROM operations WHERE result_world_revision > 88 ORDER BY result_world_revision;
SELECT session_id, COUNT(*), MIN(world_revision), MAX(world_revision)
FROM metering_records GROUP BY session_id;
SELECT object_id, revision, world_revision FROM object_revisions
WHERE object_type = 'claim' ORDER BY object_id, revision;

-- world_index.sqlite
SELECT key, value FROM search_meta;
```

## 5. Project-level observations, not extra release decisions

- The exact frozen Core has 19 successful push workflows, including [full-core regression 35810185682](https://github.com/Haneof/Haneof-AIOS-Core-v3.0/actions/runs/35810185682). This is different from Resident success.
- Current main differs from frozen Core only in five governance/checkpoint files, per exact GitHub compare.
- [PR #120 CI run 35844880234](https://github.com/Haneof/Haneof-AIOS-Core-v3.0/actions/runs/35844880234) failed in `Prove fixture task has zero Core diff`, exit 128; previous fixture/runtime/conversation steps succeeded. Full log retrieval failed, so exact Git failure cause is unresolved. No claim that all PR #120 checks were green.
- R6 trusted replacement-model attestation remains unresolved under the accepted A release decision. A model's self-identification is not attestation.

**Recommendation adopted by the corrective decision:** reject current B candidate acceptance, prepare and independently release a transport-only operator setup, then run a genuinely fresh B from exact accepted A. Do not infer Core failure or alter frozen semantics from a deficient evidence package.
