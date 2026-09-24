# C15-RCC-RES-A-RERUN-002 Acceptance Integration Receipt — 2026-09-25

Status: ACCEPTED / CANONICAL FOR FROZEN RC
Task: C15-RCC-RES-A-RERUN-002
Acceptance task: C15-RCC-RES-A-RERUN-002-ACCEPT-001

## Pins

- Frozen software: `773876f92d5f8e53422f8f5a68cc651953d93052`
- Frozen Core tree: `fe77f8a0706acfaf369041d0882b6d0e6de39f22`
- Evidence PR: #205 — OPEN / UNMERGED / PINNED
- Exact evidence head: `d17ae972ad1d312735c355f775ac024bc4cebdf7`
- Publication base: `4d9f04711769737219d921c8187fc8f52e7d0d6a`
- Independent acceptance PR: #207
- Acceptance report head: `bbea52dd573a073ffef6a9736f456f56a5dc2534`
- Acceptance merge: `c1236bf2fd6ea259fe7d487c5ac0e96abd072141`
- Verdict: `ACCEPTANCE_PASS / blocker = 0`

## Accepted Phase-A boundary

- subject: `user_1`
- session: `c15-rcc-res-a-rerun-002-2079f64af49c`
- process identity: `2079f64af49c406895541da042bf2192`
- allowed cursors: 1..13
- final World revision: 98
- final index watermark: 98
- index lag: 0
- object revision count: 245
- seven canonical USER turns
- six mechanical non-conversation events
- 13/13 release / ingest / exact durable ACK
- no cursor 14+ reveal
- Resident B not run
- no Core/test/workflow/constitution/RC-packet mutation

## Freeze digests

Accepted exact #205 freeze artifacts include:

- World:
  `626c6bb32c7fdae90a068ee10dd2b4c9cdbc46b6feb2bf5b11cba9363401f6aa`
- index:
  `ecfabf4eb8261f306b5c9f8a59dae2ef8a1629ddc2823b4311d6adffc3c1e5f1`
- release-state:
  `eada20a0bf59d1cf25446c0153d1dc719b280627d9e0170364e690e1523391c8`
- identity:
  `0544b022a6d4c6c93897be7f0f5afac82db28f84d30c2bd34d0d269515c4f975`
- software identity:
  `c6a9c6babe6723567a6fb9d346a320204f516f690da91eed85031bcf523129c7`

World and index both passed SQLite quick_check.

## Independent acceptance findings

The independent reviewer did not accept based only on cursor count.

It verified:

- all 191 PR #205 files are confined to the A-002 evidence root;
- exact frozen Core tree identity at frozen software, publication base and evidence head;
- fresh World/index/release-state/session/process identity;
- zero future/fixture leakage in 56 Resident model requests;
- 56 mailbox requests matched 56 Resident replies;
- all 13 saved resident-visible projections exactly matched their Phase-A sealed projections;
- seven USER turns reused canonical user Observation identity;
- six non-conversation events used mechanical ingest;
- 25 due-work checkpoints;
- actual Wake / Periodic Review / Summary model decisions;
- no pending mailbox request at freeze;
- evidence-bound cognition and forward revision behavior;
- no Summary/Wake treated as independent reality proof;
- exact freeze artifact SHA256 values recomputed from #205 Git blobs.

## Transparent non-blocking anomaly

Turn 1 exhausted its capability-call budget and produced an empty assistant Observation.

The run did not relabel that as intentional silence or user preference. Later cognition explicitly calibrated it as a runtime artifact.

Independent acceptance treated this as transparent non-blocking run behavior, not a provenance failure.

## Canonical disposition

PR #205 @ `d17ae972ad1d312735c355f775ac024bc4cebdf7` is the canonical Fresh Resident A-002 Phase-A evidence for this frozen RC.

PR #205 remains OPEN / UNMERGED / PINNED as evidence.
It must not be rebased, repaired in place, squashed, or hash-swapped.

Historical #117 remains valid historical evidence only for its older Core and is not the B initialization source for this RC.

## Next legal task

Only:

`C15-RCC-RES-B-PREFLIGHT-002`

may become READY.

Preflight is non-Resident and mechanical only.
It may prepare and verify a B handoff from the accepted A-002 durable lineage, but must not reveal cursor 14, run Resident B, or expose A transcript/decision logs to the future B Resident.

Downstream B release/rerun/accept, C, C16, broad P16 and P17 remain BLOCKED.
