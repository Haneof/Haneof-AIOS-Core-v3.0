# C15-RCC-RES-B-PREFLIGHT-002 — New-RC B Operator Preflight

Repository:

`Haneof/Haneof-AIOS-Core-v3.0`

Task:

`C15-RCC-RES-B-PREFLIGHT-002`

Role:

**Release / Test Infrastructure Engineer**
**Sealed Resident Infrastructure Designer**

You are not:
- Resident B;
- Resident A;
- Semantic Evaluator;
- cognition author;
- Core feature engineer;
- PM integrator.

Your only task is:

> Prepare and mechanically verify the exact fresh-context Resident-B handoff from the independently accepted A-002 durable lineage on the frozen RC, with strong blindness/isolation and auditable restart/provenance, without consuming any real Phase-B event.

## 1. Start gate

Fetch live latest `main`.

Read:
- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
- `AIOS_v3.0_CURRENT_CHECKPOINT.md`
- `PROJECT_MASTER_MAP.md`
- `governance/C15_RCC_RES_A_RERUN_002_ACCEPTANCE_INTEGRATION_RECEIPT_2026-09-25.md`
- `reviews/C15_RCC_RES_A_RERUN_002_INDEPENDENT_ACCEPTANCE_2026-09-25.md`
- `governance/C15_RCC_RES_B_CORRECTIVE_DECISION_2026-09-23.md` as historical B-preflight requirements
- frozen RC `reviews/internal_habitation/c15-rcc/v1/release/release_contract.md`
- frozen RC `reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_B_RUN_CONTRACT.md`

Confirm:

`C15-RCC-RES-B-PREFLIGHT-002 = READY`.

If it is not the unique legal READY task, stop.

## 2. Exact pins

Execution software remains:

`773876f92d5f8e53422f8f5a68cc651953d93052`

Expected Core tree:

`fe77f8a0706acfaf369041d0882b6d0e6de39f22`

Accepted canonical A evidence:

- PR #205
- exact evidence head:
  `d17ae972ad1d312735c355f775ac024bc4cebdf7`
- A session:
  `c15-rcc-res-a-rerun-002-2079f64af49c`
- World revision: 98
- index watermark: 98
- last ACK sequence: 13
- next sequence: 14
- pending reveal: null

Accepted freeze SHA256:

- World:
  `626c6bb32c7fdae90a068ee10dd2b4c9cdbc46b6feb2bf5b11cba9363401f6aa`
- index:
  `ecfabf4eb8261f306b5c9f8a59dae2ef8a1629ddc2823b4311d6adffc3c1e5f1`
- release-state:
  `eada20a0bf59d1cf25446c0153d1dc719b280627d9e0170364e690e1523391c8`

Recompute these from the exact #205 artifacts.
Do not trust filenames alone.

If #205 head has moved, or any accepted freeze digest fails, STOP.

## 3. Same durable lineage, new Resident context

Phase B must continue the same private durable AIOS lineage.

Prepare a new B run directory from exact accepted A-002 freeze artifacts.

Allowed continuity material:
- frozen private World;
- frozen synchronized index, or a mechanically rebuilt equivalent proven from that World;
- exact release-state receipt chain;
- only runtime/restart state that is mechanically required by frozen AIOS;
- exact software/Core identity.

Do not modify the accepted #205 source artifacts.

The future B Resident must start with:
- a new model process/context;
- a new B Resident session/process identity where required by the protocol;
- the same durable World lineage;
- no A chat transcript.

## 4. Absolutely do not hand A prose/decision history to B

Do **not** copy into the Resident-visible B packet/workspace:

- A mailbox requests/replies;
- A capability trace;
- A operator log;
- A RUN_COMPLETE report;
- A independent acceptance report;
- A checkpoints containing Resident semantic decisions;
- A event archive as a prose handoff;
- A transcript;
- A ModelDirective history;
- historical #117 outputs;
- failed B #121 outputs;
- PM/governance prose;
- evaluator notes.

These materials may be inspected by the non-blind preflight engineer when necessary for verification.

They are not B continuity.

B continuity comes only from normal durable AIOS state.

## 5. Phase boundary

Frozen release contract defines:

- Phase A = cursors 1..13
- Phase B = cursors 14..22
- Phase C = cursors 23..30

Preflight must prove the copied release state is exactly at the A→B boundary.

On a disposable copy only, it may mechanically prove that Phase-B initialization accepts the exact legal boundary and fails closed on malformed boundary states.

It must **not reveal cursor 14**.

It must not inspect the resident-visible payload of cursor 14 by any alternate path merely to prepare the packet.

It must not consume any real B event.

## 6. Resident-safe execution environment

The first A-002 attempt demonstrated that prompt-only blindness is insufficient if the Resident has filesystem access to sealed material.

Therefore this preflight must prove the future Resident-B execution environment does not expose forbidden material.

The Resident B context must not be able to browse/read/search:
- `fixture/**`;
- `evaluator/**`;
- operator-only release implementation source;
- governance/task-board/checkpoint/PM reports;
- #205 evidence package;
- #207 acceptance report;
- old Resident transcripts/reports;
- Git history/PR/CI metadata capable of exposing future fixture content;
- Phase-C material.

Preferred arrangement:
- frozen Core/runtime already installed/prepared before B context starts;
- approved Resident-safe contract available;
- allowed command interface/wrapper available;
- durable World/index/release-state mounted at explicit paths;
- sealed operator runs outside Resident model-visible filesystem/context;
- Resident receives only current reveal + normal RuntimeSnapshot/capabilities.

If the platform gives the Resident unrestricted visibility into the full repository including sealed fixture/evaluator material and no enforceable isolation arrangement exists:

**return BLOCKED / RESIDENT_ISOLATION_NOT_PROVEN.**

Do not claim isolation based only on "do not read" instructions.

## 7. Reuse existing runtime; do not build a second one

Use the frozen RC's existing:
- World store;
- search index;
- FusedTurnRuntime / CognitiveRuntime;
- canonical conversation ingest;
- Summary;
- Wake;
- Periodic Review;
- metering;
- recovery semantics;
- sequential release machinery.

Do not create:
- another World/cognition truth store;
- semantic replay engine;
- keyword-driven answer logic;
- fake RuntimeSnapshot;
- pre-authored B directives;
- alternate turn ledger.

Infrastructure may transport bytes and execute Resident-selected capabilities.
It may not decide semantics.

## 8. Mechanical preflight checks

Use only disposable synthetic/copies where needed.

At minimum verify:

1. frozen Core tree identity;
2. accepted A freeze digests;
3. World SQLite quick_check;
4. World revision = 98;
5. index quick_check;
6. index watermark = 98;
7. index lag = 0;
8. release-state:
   - Phase A completed;
   - last ACK = 13;
   - next sequence = 14;
   - pending reveal = null;
9. no cursor 14 material has been consumed;
10. legal Phase-B init accepts an exact copy;
11. malformed/skipped/dirty boundary fails closed;
12. same-World durable restart succeeds;
13. the future B resident cannot read A semantic traces or sealed fixture/evaluator material through its approved interface;
14. mailbox/request bridge can pause on a genuine model request and has no semantic default answer;
15. final freeze/evidence procedure is defined before B begins.

Do not run genuine Resident cognition.

## 9. B session and USER-turn binding

Prepare, but do not execute, the rules for Phase B USER conversation:

- fresh B model context/process;
- consistent B session ID chosen at run start;
- monotonic B turn indices for B USER events;
- canonical conversation ingest first;
- ordinary `run_turn` reuses subject/session/turn/text/time idempotently;
- no duplicate user Observation;
- no transcript handoff from A.

The durable World may contain A conversation Observations and cognition.
That is intended.
B discovers relevant continuity through normal AIOS state/capabilities.

## 10. Evidence and freeze design

Predefine the B evidence layout and exact freeze procedure.

It must preserve at least:
- World;
- index;
- release-state;
- runtime/restart checkpoint if mechanically required;
- exact software identity;
- session/process identity;
- per-cursor reveal projection;
- ingest receipts;
- ACK receipts;
- due-work checkpoints;
- mailbox requests/replies;
- capability results/errors;
- Wake/Review/Summary provenance;
- metering;
- hashes.

No hidden chain-of-thought is required or requested.

## 11. Identity evidence

Inventory trustworthy model/provider identity evidence available for:
- accepted A-002;
- planned fresh B;
- later replacement-model C.

Do not invent identity proof.
Model self-description, branch name, configured string, or operator prose is not trusted attestation.

If identity is unavailable, record UNKNOWN.
This does not block B execution-evidence continuity by itself, but remains relevant to the later replacement-model gate.

## 12. Historical evidence preservation

Do not modify:
- #205;
- #207 acceptance history;
- historical #117;
- failed/non-canonical #121;
- old B preflight/rerun evidence.

The old `C15-RCC-RES-B-PREFLIGHT-001` path is historical for the old #117/Core lineage and is not the active preflight for this RC.

## 13. Deliverables

Create a new preflight evidence root clearly named for:

`C15-RCC-RES-B-PREFLIGHT-002`

Deliver at least:

1. operator manifest;
2. exact A-002 source pins/digests;
3. copied-lineage hash manifest;
4. resident-safe packet manifest;
5. isolation proof/report;
6. exact B startup procedure;
7. exact per-cursor interaction procedure;
8. final freeze procedure;
9. mechanical positive/negative checks;
10. known limitations;
11. completion report.

Open one preflight PR.

Do not merge it yourself.

## 14. Exit verdict

Choose exactly one:

### REVIEW_READY

Only if:
- accepted A-002 lineage is reproduced exactly;
- frozen RC identity is proven;
- A→B boundary is valid;
- no B cursor was consumed;
- Resident-safe isolation is actually proven;
- transport has no semantic shortcuts;
- B startup/freeze procedure is auditable;
- blockers = 0.

### BLOCKED

If any mechanical, lineage, isolation, or provenance blocker remains.

Do not weaken blindness or consume B data to make the preflight pass.

## 15. Stop boundary

If REVIEW_READY, stop.

Do not:
- run Resident B;
- release cursor 14;
- enter B acceptance;
- run Resident C;
- enter C15 semantic evaluation;
- enter C16/broad P16/P17;
- modify Core;
- do UI/hardware.

The only next task after independent PM/release review of this preflight will be:

`C15-RCC-RES-B-RELEASE-002`
