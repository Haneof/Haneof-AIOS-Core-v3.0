# C15-RCC-RES-A-RERUN-002 Independent Acceptance

Task: `C15-RCC-RES-A-RERUN-002-ACCEPT-001`

Role: Independent Fresh Resident A Evidence Acceptance Reviewer

Review date: 2026-09-25

## 1. Final verdict

**ACCEPTANCE_PASS / blocker = 0**

`PR #205 @ d17ae972ad1d312735c355f775ac024bc4cebdf7 is independently accepted as the canonical Fresh Resident A-002 Phase-A evidence for frozen software 773876f92d5f8e53422f8f5a68cc651953d93052 / Core tree fe77f8a0706acfaf369041d0882b6d0e6de39f22.`

This acceptance is for the exact evidence head above only. PR #205 remains OPEN / UNMERGED. No Resident B/C execution, future cursor release, Core modification, or repair was performed by this review.

## 2. Review-time pins

- review-time live `main`: `a83363caf028d8eb0d97c5eb0966e7a06a3ee75e`
- candidate evidence PR: #205, OPEN / UNMERGED
- exact evidence head: `d17ae972ad1d312735c355f775ac024bc4cebdf7`
- PR publication base: `4d9f04711769737219d921c8187fc8f52e7d0d6a`
- frozen execution software: `773876f92d5f8e53422f8f5a68cc651953d93052`
- frozen Core tree: `fe77f8a0706acfaf369041d0882b6d0e6de39f22`
- task: `C15-RCC-RES-A-RERUN-002`
- subject: `user_1`
- session: `c15-rcc-res-a-rerun-002-2079f64af49c`
- process identity: `2079f64af49c406895541da042bf2192`
- allowed cursor range: 1..13

The #205 head was re-read immediately before publication of this acceptance and had not moved.

## 3. Evidence-only scope

Independent changed-file enumeration found 191 changed files in PR #205.

All 191/191 paths are confined to:

`reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-A-RERUN-002/**`

There are zero changed paths outside the authorized run evidence root. No `src/aios_core/**`, production tests, workflows, constitution, governance control-plane file, or RC packet file is changed by #205.

Verdict: **PASS**.

## 4. Frozen software identity

Git tree identity was checked directly rather than inferred from branch names.

The `src/aios_core` tree is exactly:

`fe77f8a0706acfaf369041d0882b6d0e6de39f22`

at all three relevant commits:

1. frozen software `773876f92d5f8e53422f8f5a68cc651953d93052`
2. publication base `4d9f04711769737219d921c8187fc8f52e7d0d6a`
3. evidence head `d17ae972ad1d312735c355f775ac024bc4cebdf7`

Therefore later governance/review commits did not substitute different Core bytes into this Resident run, and #205 itself does not mutate Core.

Verdict: **PASS**.

## 5. Freshness and contamination

The run operator contains an explicit fresh-start guard: if the private World, search index, or release-state already exists, execution aborts. It creates a new SQLite World, rebuilds a fresh index, and verifies initial World revision/index watermark are both zero before release initialization.

The evidence identifies a unique fresh Resident session/process:

- session: `c15-rcc-res-a-rerun-002-2079f64af49c`
- process identity: `2079f64af49c406895541da042bf2192`

The operator trace contains one `fresh_world`, one `release_init`, 13 reveals, 13 ingests, 13 ACKs, 56 mailbox requests, 56 matching mailbox replies, 25 due-work records, and one terminal `phase_a_complete`.

No mailbox request remained unanswered; there are no orphan replies.

### Future/fixture leakage test

The reviewer cross-checked all 13 saved Resident-visible event projections against the sealed fixture's Phase-A projection schema. Each saved event contains exactly the eight allowed visible fields:

- `event_id`
- `sequence`
- `occurred_at`
- `dimension`
- `source_kind`
- `source_class`
- `modality`
- `resident_visible_payload`

For sequences 1..13 there were **0 field mismatches and 0 extra fields**.

Additionally, every one of the 56 mailbox requests was checked against sealed fixture events not yet released at that request's active cursor. Neither unreleased event IDs nor complete unreleased Resident-visible payloads appeared in the model request context. Result: **0 future-event matches**.

No Resident B/C content, cursor 14+ content, or historical #117/#109/#101 semantic output was found in the Resident model context.

Mechanical fixture access by release/ingest infrastructure stayed outside the Resident semantic context and is permitted by contract.

Verdict: **PASS / uncontaminated**.

## 6. Sequential release 1..13

The release state and receipts prove a contiguous Phase-A chain:

- initialized at Phase A
- revealed/ingested/ACKed exactly sequences 1 through 13
- no skip
- no reorder
- no duplicate new reality event
- final `last_acked_sequence = 13`
- final `next_sequence = 14`
- final `pending_reveal = null`

The 13 event IDs and durable ingest refs are:

| seq | event | ingest ref | path |
| ---: | --- | --- | --- |
| 1 | c15rcc-001 | `obs_conv_user_e3f254f5a3f691c9f1ae5870@1` | canonical USER |
| 2 | c15rcc-002 | `obs_c14_fixture_5248cdfd5a23b6ea88ce0a96@1` | mechanical |
| 3 | c15rcc-003 | `obs_conv_user_c4bef35968765b7f621c3ab2@1` | canonical USER |
| 4 | c15rcc-004 | `obs_c14_fixture_5d4dfcf42055c00135a78a54@1` | mechanical |
| 5 | c15rcc-005 | `obs_conv_user_d4953379e0fd7ae84b9a27ee@1` | canonical USER |
| 6 | c15rcc-006 | `obs_conv_user_76b4c03c31db54c18b1f02ee@1` | canonical USER |
| 7 | c15rcc-007 | `obs_c14_fixture_87474a7fb5036c38638a6c37@1` | mechanical |
| 8 | c15rcc-008 | `obs_conv_user_10c0bcfb2f7bf80aa9b324b8@1` | canonical USER |
| 9 | c15rcc-009 | `obs_c14_fixture_b798e2dbd5b0fabdec6680a2@1` | mechanical |
| 10 | c15rcc-010 | `obs_conv_user_fbe20407ffd68ca6f1bc5f5c@1` | canonical USER |
| 11 | c15rcc-011 | `obs_c14_fixture_291beec37165eb34a35f8f85@1` | mechanical |
| 12 | c15rcc-012 | `obs_conv_user_e0dbe4b6cc248f47e013943c@1` | canonical USER |
| 13 | c15rcc-013 | `obs_c14_fixture_e2c76be3450b6e9dc8316b9d@1` | mechanical |

The saved projections for all 13 sequences independently match their sealed-fixture Phase-A projections.

Verdict: **PASS**.

## 7. USER canonical conversation ingest

Seven Phase-A USER conversation events were found at sequences 1, 3, 5, 6, 8, 10, and 12.

They use one stable session ID and turn indices exactly 1..7.

For all seven turns, the user Observation ID in the ordinary runtime turn receipt is the same canonical Observation ID produced by the preceding canonical ingest. No second user Observation identity is minted for the same turn.

The Core implementation was inspected at the frozen software SHA. `run_turn` calls `commit_user_input` before model inference and uses stable subject/session/turn idempotency. The aggregate turn receipt's `idempotent_replay=false` is not evidence of duplicate USER ingest: the aggregate flag combines user replay with the first-time assistant-output commit. The stable user IDs across canonical ingest and ordinary run prove the intended reuse.

All seven turn receipts have the expected session/turn ordering; turns 2..7 respond normally. Turn 1 terminates with `capability_call_budget_exhausted` after real capability work and therefore records an empty assistant Observation; the later Resident calibration Claim explicitly marks this as a runtime artifact, not intentional silence or evidence of user preference. This is transparent and not a provenance blocker.

Verdict: **PASS**.

## 8. Non-conversation ingest

The six non-conversation Phase-A events are sequences 2, 4, 7, 9, 11, and 13.

Each uses the mechanical ingest path. The resulting Observation metadata identifies the C15 mechanical fixture binding, preserves the released payload/source class/time, and the ACK receipt binds the exact resulting durable ref to the corresponding sequence/event.

No semantic cognition is generated by the mechanical adapter.

Verdict: **PASS**.

## 9. Resident-authored semantic provenance

This was treated as a mandatory semantic-provenance audit, not inferred from cursor completion.

The operator's `MailboxResident` is transport-only:

- it serializes the then-current `RuntimeSnapshot`, capability catalog/history, wake reason, round index, and summary request;
- writes a mailbox request;
- blocks until a matching Resident reply appears;
- validates only reply structure;
- returns the Resident directive to Core.

No keyword rule, hidden fixture answer, semantic decision table, or operator-authored cognition path was found in the operator.

There are 56 request/reply pairs, all matched.

The decision stream shows strong evidence of live Resident reasoning from capability feedback rather than precomputed scripted answers. Examples:

- an invalid `entity_key` is rejected; the next Resident round corrects it to the required `entity:` form;
- a task creation using stale Goal revision 1 is rejected after the Goal transitions to revision 2; the Resident retries using revision 2;
- malformed `revise_claim` calls at the release-status turn produce capability argument errors; the next Resident round repairs the arguments;
- release cognition evolves only as evidence is released: READY_FOR_UPLOAD/queued is not treated as published; the checksum-mismatch event causes a failure revision; only after the later tag+digest+`PUBLISHED` event does the Resident revise the release Claim to success.

The Resident also correctly distinguishes:
- task completion from whole-goal completion;
- reported completion from queued/prepared state;
- Wake silence from user preference;
- Summary from independent reality proof.

Verdict: **PASS**.

## 10. Runtime / Wake / Review / Summary completeness

The due-work ledger contains 25 entries:

- cursor 1 post
- cursor 2..13 pre and post

No summary execution error is recorded.

Triggered background/cognitive Wakes were processed to terminal completion. The three observed cognitive/background Wake deliveries terminate in model-selected silence, with no fabricated user-facing completion claim.

Four periodic review cycles complete to terminal review Wake revision 3:
- cursor 1 post
- cursor 6 pre
- cursor 7 pre
- cursor 13 pre

Dimension summaries are produced through the same Resident mailbox model path. Summary maintenance shows expected commits/skips as dimensions become due, with no abandoned model request.

The final ordering is:
1. cursor 13 pre due-work
2. cursor 13 ingest
3. cursor 13 ACK
4. cursor 13 post due-work
5. final World/index state 98/98
6. `phase_a_complete(stop_sequence=13)`

No pending mailbox request remains at freeze.

Verdict: **PASS**.

## 11. World / index integrity

The frozen package identifies:

- World revision: 98
- index watermark: 98
- index lag: 0
- object revision count: 245
- World `PRAGMA quick_check`: `ok`
- index `PRAGMA quick_check`: `ok`

The final cursor-13 checkpoint and final due-work state independently converge on World revision 98 / index watermark 98 before phase completion.

The model-visible World snapshots and periodic-review anchors are consistent with only the Phase-A reality released up to their respective temporal cutoffs. The future-event leakage comparison described above found no unreleased future payload in Resident inputs.

The exact frozen SQLite blobs were re-read from the exact #205 head and their bytes were independently hashed during review; the hashes match the freeze manifest exactly. This binds the recorded integrity metadata to the actual reviewed database artifacts rather than to a differently named or substituted file.

Verdict: **PASS**.

## 12. Freeze integrity / digest validation

The reviewer independently recomputed SHA-256 from the exact #205 Git blobs for the required frozen files:

| artifact | bytes | independently recomputed SHA-256 |
| --- | ---: | --- |
| `freeze/private_world.sqlite` | 790528 | `626c6bb32c7fdae90a068ee10dd2b4c9cdbc46b6feb2bf5b11cba9363401f6aa` |
| `freeze/world_index.sqlite` | 811008 | `ecfabf4eb8261f306b5c9f8a59dae2ef8a1629ddc2823b4311d6adffc3c1e5f1` |
| `freeze/release_state.json` | 10841 | `eada20a0bf59d1cf25446c0153d1dc719b280627d9e0170364e690e1523391c8` |
| `freeze/identity.json` | 813 | `0544b022a6d4c6c93897be7f0f5afac82db28f84d30c2bd34d0d269515c4f975` |
| `freeze/software_identity.json` | 510 | `c6a9c6babe6723567a6fb9d346a320204f516f690da91eed85031bcf523129c7` |

All five independently recomputed values match the freeze manifest/digest file exactly.

The live mutable World/index hashes are not required to be byte-identical to SQLite online backup copies; the reviewed freeze copies are the canonical coherent snapshots.

Verdict: **PASS**.

## 13. Capability / cognition audit

Evidence-bound cognition was inspected across USER turns, periodic review anchors, final AI-world reads, and capability histories.

Key findings:

- Claim writes/revisions cite pinned current evidence refs.
- Forward revisions are selected when later released evidence changes the state.
- The user-understanding Claim is under `user_1`; AI intent/boundary/calibration remain under `ai_agent_self`.
- Unknowns are retained where evidence is incomplete, e.g. whole Atlas-staging completion and upload retry/root-cause questions.
- No cognition quota behavior was observed.
- No future knowledge was found before release.
- The completed observation task closes only the two evidence-supported non-production items and explicitly keeps the broader Atlas-staging goal open.
- Summary text is not used as independent reality proof.
- Wake completion/silence is not treated as user preference or external success.
- The first-turn empty assistant Observation is explicitly calibrated as a budget-exhaustion artifact rather than misread as intentional silence.

Verdict: **PASS**.

## 14. PR #205 CI

GitHub Actions run `36033027900`, job `107746211123` (`c15-rcc-fixture-mechanical-gate`), concluded **SUCCESS**.

Successful steps include:
- C15 mechanical gate
- sealed fixture SHA-256 proof
- mature C14 release gate
- C15 subject-isolation/fused-runtime regressions
- canonical conversation ingest regressions
- zero-Core-diff proof

Nuance: the pull-request workflow checkout log uses GitHub's synthetic PR merge ref `fb69b81cda64c458ca59b2f7ea08c5dc3f667044`, while run metadata is associated with PR head `d17ae972ad1d312735c355f775ac024bc4cebdf7`. CI is therefore supporting evidence, not the basis for exact-head semantic acceptance. All material evidence/provenance checks above were performed directly against the exact #205 head.

Verdict: **supporting CI PASS**.

## 15. Blockers

**None.**

No provenance, contamination, sequence, ingest, semantic-execution, due-work, freeze-integrity, or Core-identity blocker was found.

## 16. Acceptance handoff

Final verdict:

**ACCEPTANCE_PASS / blocker = 0**

`PR #205 @ d17ae972ad1d312735c355f775ac024bc4cebdf7 is independently accepted as the canonical Fresh Resident A-002 Phase-A evidence for frozen software 773876f92d5f8e53422f8f5a68cc651953d93052 / Core tree fe77f8a0706acfaf369041d0882b6d0e6de39f22.`

This review authorizes only the governance conclusion above. It does not merge #205 and does not execute or preflight Resident B.
