# C15-RCC-RES-B-RELEASE-002 — Release Record

Date: 2026-09-26  
Repository: `Haneof/Haneof-AIOS-Core-v3.0`

## Verdict

`C15-RCC-RES-B-RELEASE-002 = DONE / RELEASED`

Blockers: `0`

This is a non-Resident release record. It authorizes only the next task,
`C15-RCC-RES-B-RERUN-002`, after this record is integrated on `main`.
No Resident B/C cognition was executed in this release-review window.

## Ground truth reviewed

Live `main` reviewed immediately before writeback:

`5db649fdd34ae49303e18e5a224720e9a3a82fe3`

Accepted B-preflight:
- PR #209 accepted candidate: `aab3a30cc48e8c7041ef4b37e0e5f379c3060c93`
- candidate tree: `6de6c9bcc8cc7de64802f68b59178e0881e3a42d`
- merged as: `65e6e8266bb0541d624eb8e5bba825b91145564f`
- PM exact-head review: `5323959000`
- Independent Acceptance: `5323972504`
- verdict: `ACCEPTANCE_PASS / blocker=0`

Canonical A evidence:
- PR #205 remains OPEN / UNMERGED / PINNED
- exact head: `d17ae972ad1d312735c355f775ac024bc4cebdf7`

Frozen software:
- software: `773876f92d5f8e53422f8f5a68cc651953d93052`
- Core tree: `fe77f8a0706acfaf369041d0882b6d0e6de39f22`

The `src/aios_core` subtree on reviewed `main` was independently resolved from Git trees and is still exactly
`fe77f8a0706acfaf369041d0882b6d0e6de39f22`. The frozen-software-to-reviewed-main comparison contains zero
`src/aios_core/**` file changes.

## A -> B lineage revalidation

The three preflight lineage-copy files were compared directly with PR #205 exact-head freeze objects.
Their Git blobs are byte-identical:

- World blob: `708904868d4069de68b74aff305f99d29c128da0`
- Index blob: `9155f8e67a770e990c511b384810bf44ae4ea72b`
- release-state blob: `4bc5f7093d81d0000959042d6fe60ebbf2124561`

Fresh SHA-256 recomputation from repository bytes:

- World: `626c6bb32c7fdae90a068ee10dd2b4c9cdbc46b6feb2bf5b11cba9363401f6aa`
- Index: `ecfabf4eb8261f306b5c9f8a59dae2ef8a1629ddc2823b4311d6adffc3c1e5f1`
- release-state: `eada20a0bf59d1cf25446c0153d1dc719b280627d9e0170364e690e1523391c8`

Boundary state:
- World revision: `98`
- index watermark: `98`
- index lag: `0`
- last ACK: `13`
- next sequence: `14`
- pending reveal: `null`
- Resident B has not run.

## Frozen release surfaces

All blobs were re-read from reviewed `main` and matched exactly:

- lifecycle checker: `72f674b2d430262a5eff9cb66c7004917c0f4ae4`
- startup runbook: `c56f528f4ea181ae002ed22d3e810ab6022ddb17`
- per-cursor runbook: `17f27956152f4edd49b57f72c7546eef668406fa`
- Resident-safe packet manifest: `ac3da8b204b93fc47b32a7d5a98ae6a2a89e0d7c`
- Resident-B contract: `32d2dc99c2a9d391fad1a4c84824ebce8ca46d79`
- environment manifest: `c6ce70a78a413510f8ae52ff21616c1638c81f7d`
- final-freeze procedure: `d77a25c11304d142d8e3fc816f5dde78a6fafbb6`
- committed preflight E2E evidence: `52da0673309781ab9f9a98aa9b59b4748d9bd225`

Fresh SHA-256 checks:
- Resident-B contract: `28d3262f56b7ef93a32a842f1d4d66f99748f2b07adcece43e815eb9d5cd18ef`
- requirements freeze: `bd7a76d1171c137f9daee9c0a3dbff029b8cbbccef88f0a1aff7907710a82375`
- wire protocol: `a6bbeaef4aab369ef23659a1ce46df24b970fd48176edc8feb78b9f62228ff3a`
- production adapter: `da74eb97a6d35b535f298f52a72a32fc35dfbd1fca1ec4585aa1d7c090e92911`
- Resident jail: `d766c1857163528cacf90e6b876466d099456062914747eab25dd1220e8615eb`

## Runtime / isolation findings

Source inspection and fresh validation confirm:
- production transport is `ProductionResidentHandler + ExternalBrokerClient`;
- production requires a real provider endpoint/key and the exact pinned adapter; there is no fake fallback;
- production loopback remains test-only and is not enabled by the production entrypoint;
- provider token usage is never synthesized; missing provider total => `usage=None`;
- every production dispatch requires the current event and its immutable binding receipt;
- missing/stale/malformed event, release state, receipt, provider config, or protocol hashes fail closed;
- Resident-visible filesystem/network surfaces remain limited by the accepted Resident-safe packet;
- governance, fixture, evaluator, Git metadata, A prose/transcripts/reports and Phase-C material are not Resident-readable.

Canonical per-cursor lifecycle remains frozen as:

`REVEAL -> INSTALL_CURRENT_EVENT -> PERSIST_PROJECTION_EVIDENCE -> CREATE_BINDING_RECEIPT -> VERIFY_BINDING -> DERIVE_OCCURRED_AT -> INGEST -> MODEL_WORK -> FINISH_CURSOR_MODEL_WORK -> DURABLE_ACK -> CLEAR_BINDING -> NEXT_REVEAL`

The final-freeze/evidence procedure is frozen before Resident B begins.

## Fresh release validation

A release-specific validation branch was created from the reviewed `main` only to execute the fresh gate:

`validation/c15-rcc-b-release-002-20260926`

Validation workflow commit:

`526815b859c095385d06ce0de24481542cd9168a`

GitHub Actions run:

`36216433668`

The validation branch/workflow is evidence-only and MUST NOT be merged into `main`.

Attempt 1 is preserved as real red evidence:
- post-merge ground truth/pins: PASS
- external lifecycle adversarial probes: PASS
- frozen Debian 12 E2E: `157/158`, one failure
- failure: isolation PID-map probe did not observe `pid1_host/worker_host` in that runner instance.

One retry of the same job was used only to distinguish a repeatable release blocker from an isolation/runner transient.

Attempt 2, job `108333412334`: SUCCESS
- post-merge ground truth/pins: PASS
- release external adversarial matrix: PASS
- lifecycle self-test: PASS
- frozen Debian 12 E2E: PASS
- `ALL_CHECKS=158/158 FAILURES=0`
- `RUNBOOK_SHELL_SEMANTICS_MUTATION_RED_PASS cases=82`
- `NO_COMMITTED_CURSOR14_PAYLOAD_PASS`
- `CORRECTIVE_013_E2E_PASS`
- `B_RELEASE_002_FROZEN_E2E_PASS`
- fresh E2E log SHA-256:
  `cc1ab9e9a7224fab85ebe0bf2e7ca3a41c39bf2a06cc5e3fa168435b21b5840a`
- artifact id: `10897781975`
- artifact digest:
  `sha256:a17353897c88ee3045892698474e634e354a2f6c140492f314d23dd7652eafa0`

For transparency, a rerun of the old pre-merge Independent Acceptance workflow `36207911770` failed at its
historical `test -s <candidate-vs-main diff>` assertion because the accepted candidate is now an ancestor of
`main`. PR #205 and Core-tree checks passed before that assertion. That old pre-merge workflow is not used as
the release qualification.

The fresh E2E uses only disposable operator-side reveal mechanics. It did not present the real cursor-14 payload
to a Resident/model. No real B run was started.

## Exact B release identity

Exactly one B execution identity is released:

- run ID: `c15-rcc-res-b-rerun-002-65e6e826`
- B session ID: `c15-rcc-res-b-session-002-65e6e826`
- canonical run root: `/tmp/c15-rcc-res-b-rerun-002-65e6e826`
- preflight source anchor: PR #209 merge `65e6e8266bb0541d624eb8e5bba825b91145564f`
- accepted candidate anchor: `aab3a30cc48e8c7041ef4b37e0e5f379c3060c93`
- safe packet manifest blob: `ac3da8b204b93fc47b32a7d5a98ae6a2a89e0d7c`
- Resident contract SHA-256: `28d3262f56b7ef93a32a842f1d4d66f99748f2b07adcece43e815eb9d5cd18ef`

No second run/session identity may be minted.

### Release identity overlay over the frozen startup runbook

The frozen startup runbook is not edited. Its historical preflight template in §5 mints a random `B_SESSION`.
For this released run, that random `B_SESSION=...` assignment MUST NOT be executed.

Before startup §6, set exactly:

```bash
RUN_ROOT=/tmp/c15-rcc-res-b-rerun-002-65e6e826
B_SESSION=c15-rcc-res-b-session-002-65e6e826
B_PROCESS="$(openssl rand -hex 16)"
export RUN_ROOT B_SESSION B_PROCESS
```

`B_PROCESS` is fresh process evidence only; it is not a second run/session identity.

## Exact B entry procedure

The next `C15-RCC-RES-B-RERUN-002` window must:

1. start from the integrated release record and the exact run/session identity above;
2. create the canonical run root and copy the byte-exact A-002 World/index/release-state lineage;
3. reverify all three hashes and recovery status (`98/98`, lag 0);
4. initialize Phase B mechanically, leaving `next_sequence=14` and `pending_reveal=null`;
5. establish the accepted sandbox and exact frozen environment:
   - Debian 12 or equivalent proven execution contract;
   - `python3 == Python 3.11.2`;
   - `/usr/bin/python3 == Python 3.11.2`;
   - Pydantic `2.13.5`;
   - pydantic_core `2.46.5`;
   - annotated-types `0.8.0`;
   - typing-inspection `0.4.4`;
   - typing_extensions `4.16.0`;
   - exact requirements freeze hash above;
6. set the exact released B session identity and a fresh process identity;
7. assert that before the first real reveal, `current-event.json` and the binding receipt are absent;
8. only then perform the first real cursor-14 reveal and execute the frozen lifecycle one cursor at a time through 22;
9. after cursor 22 and all attributable due/model work complete, execute the predefined final-freeze procedure;
10. open the B evidence PR and stop at `RUN_COMPLETE / AWAITING_INDEPENDENT_ACCEPTANCE`.

## Stop conditions

STOP without advancing the release cursor on any:
- pin/hash/Core-tree mismatch;
- A-lineage mismatch;
- environment mismatch;
- isolation failure;
- missing/invalid current event or binding;
- provider/adapter/protocol mismatch;
- model dispatch before legal event binding;
- fixture/evaluator/governance/A-transcript/future material exposure;
- inability to persist required evidence;
- unexpected second run/session identity.

## Identity evidence

Trusted provider/model identity remains `UNKNOWN` at release time.
The B run must preserve whatever real provider response metadata is available without upgrading config strings or
self-description into trusted attestation. This is not a B execution blocker; it remains relevant to the later
replacement-model/R6 gate.

## Non-consumption statement

During this release review:
- no real Resident B process/session ran;
- no real cursor-14 payload was presented to a Resident/model;
- no Resident semantic answer was generated;
- no Resident C, evaluator, C15 closure, C16 or broad P16/P17 task was entered.

## Release effect

After this record is integrated on `main`:

- `C15-RCC-RES-B-RELEASE-002 = DONE / RELEASED`
- `C15-RCC-RES-B-RERUN-002 = READY`
- `C15-RCC-RES-B-ACCEPT-002 = BLOCKED`
- Resident C / evaluator / C15 close / C16 / broad P16 / P17 remain BLOCKED.

The next window is the real Resident-B run only.
