# C14-RES-EVAL-001 Independent Semantic Evaluation

> Date: 2026-09-22  
> Role: Independent Semantic Evaluator / Independent Red-Team Reviewer  
> Evaluated main: `8e6f9febc5f006605116c526796fa21435b4b22e`  
> Resident A evidence: PR #75, exact head `cb9b56b7039272d932158f33bfe979eff6749c9b`, open/unmerged  
> Resident B evidence: PR #79, exact head `546449a453e6e6dff3a2eeb2b52e7cf6786927be`, open/unmerged  
> Fixture: `c14-resident-fixture-v2`, SHA256 `1fb973499664d0d71d94a7b94071e3d7210395ea6a54ec4dcbb1ba115d069253`

## 1. Scope and method

This review is semantic and evidentiary only. No Core code, fixture, Resident directive, Summary, Claim, World, or evidence artifact was modified or regenerated.

The review used the binding C14 protocol/ruling/hardening documents, evaluator-only fixture notes, the sealed fixture, exact PR heads, raw reveal/ingest/ack receipts, RuntimeSnapshots/ModelDirectives, capability results, Summary inputs/outputs, Wake/Review records, frozen World/release-state digests, handoff manifests, bridge source, and event-level evidence. Resident FINAL_REPORT files were treated only as locators and were not accepted as truth without raw corroboration.

## 2. Frozen evidence identity

### Resident A

- PR #75 exact head: `cb9b56b7039272d932158f33bfe979eff6749c9b`
- Branch: `arena/01a0c473-haneof-aios-core-v3-0`
- Phase-A final World: world revision 166 / index watermark 166
- Frozen World SHA256: `0ee338aa8f2845bb376610da3c450e09ff9cc8bec5184ca60608b2465d7ba72f`
- Frozen release-state SHA256: `e922d268fbb11364a7bb558aed60b88e7a3c075032f4fa4e1c47a84de3f765f1`
- Release boundary: cursor 24 acked, `next_sequence=25`, cursor 25 not revealed
- Claim at handoff: `clm_79df61916b8bb4c10cb3faa3@2`

Primary raw anchors:
- `reviews/internal_habitation/c14-resident/v2/runs/resident-a-restart-20260921/handoff/HANDOFF.json`
- `.../release/release_state.json`
- `.../checkpoints/decisions/wake-cognitive_derivation-wake_146f08e22bd4f1e6f33a3e12-rev1-23ec6958/round-{0,1,2}.json`
- `.../checkpoints/results/wake-cognitive_derivation-wake_146f08e22bd4f1e6f33a3e12-rev1-23ec6958/round-1.json`
- `.../checkpoints/decisions/wake-cognitive_derivation-wake_7198b085c5bc20fcee8fd8de-rev1-3b442dee/round-0.json`
- `.../checkpoints/decisions/wake-cognitive_derivation-wake_b48851c19969249b73e37156-rev1-ae18cfb7/round-{0,1}.json`
- `.../checkpoints/decisions/wake-cognitive_derivation-wake_0c29429ae3d11e1c43802888-rev1-7bb99b6e/round-{0,1}.json`

### Resident B

- PR #79 exact head: `546449a453e6e6dff3a2eeb2b52e7cf6786927be`
- Branch: `arena/01a0c517-haneof-aios-core-v3-0`
- Fresh session: `resb-20260921-282770`
- Inherited World SHA256: `0ee338aa8f2845bb376610da3c450e09ff9cc8bec5184ca60608b2465d7ba72f`
- Inherited release-state SHA256: `e922d268fbb11364a7bb558aed60b88e7a3c075032f4fa4e1c47a84de3f765f1`
- Final World SHA256: `a288fc5d11a1a73006725efdd906a7ab014d4228085c610b4a32f887cfe3d615`
- Final release-state SHA256: `9281ced5013b45445574698d53ff9a2d57d5308ac5d1221e5db178efcf0c8a4f`

Primary raw anchors:
- `reviews/internal_habitation/c14-resident/v2/runs/resident-b-20260921/evidence/MANIFEST.md`
- `.../evidence/init_phase_b.json`
- `.../bridge/log.jsonl`
- `.../bridge/io/req_16.json`
- `.../bridge/io/resp_17.json`
- `.../bridge/results/j014_turn1.json`
- `.../bridge/results/j034_wake.json`
- `.../bridge/results/j038_turn2.json`
- `.../bridge/results/j053_turn3.json`
- `.../evidence/events/cursor_026/{event.json,canonical_ingest_receipt.json,ack_receipt.json}`
- `.../evidence/events/cursor_032/{event.json,canonical_ingest_receipt.json}`
- `.../evidence/events/cursor_037/event.json`

## 3. Evidence Matrix

| Item | Verdict | Key evidence | Main risk |
|---|---|---|---|
| E1 Phase-A cross-dimensional cognition | **PARTIAL** | Claim rev1 was model-authored after explicit `search_timeline` across `dim:work_outcome`, `dim:schedule`, `dim:device_activity`, and `dim:conversation`; `clm_79df...@1` pinned 9 non-Summary Observation leaves spanning three distinct work cases. | Claim rev2 materially exceeds its pinned evidence set: the replacement text and reason assert “sleep only 5h48m”, but `obs_c14_fixture_056dddd04850d813437e8532@1` is not among the 10 evidence refs for the revision. Core hypothesis formation is genuine, but the current Phase-A durable revision is not fully evidence-closed. |
| E2 matched-negative silence | **VALID** | Cursors 14–21 create superficially similar early-wake/sleep patterns with distinct external constraints. Resident explicitly searches underlying sleep/environment/schedule reality, then chooses `silence:true`; later 10-19 sleep 8h09 directly breaks the candidate narrow-band pattern and Resident again chooses silence. | Resident mentions a self-imposed sample-size heuristic, but the actual decisions were not N-only: confounders, missing scores, and later contrary reality materially controlled the silence. No budget/error exhaustion masqueraded as silence. |
| E3 fresh-window cognition recovery | **VALID** | B starts from exact frozen A World/release digests and fresh session. Initial B RuntimeSnapshot has no prior Claim content/id in memory cards. B itself issues ordinary searches, then `search_timeline(... object_types=["claim"])`, then `inspect_world_object(clm_79df...@2)`. Periodic Review advances it to rev3; cursor26 normal retrieval surfaces `clm_79df...@3` as score-10 memory card. | No provider-side transcript exists to cryptographically prove absence of off-repo contamination; repository evidence nevertheless shows no direct Claim injection in prompt/bridge/fixture/report path. |
| E4 prior cognition materially affected later behavior | **VALID** | At cursor26 the current user fact leaves both 09:00 and 11:00 available. Before future cursors 27–29 are released, Runtime supplies Claim rev3 as top memory card. Resident creates `task_5029111ade74171bc3758e98@1` with reason_refs pinning both the current user Observation and `clm_79df...@3`, then recommends 09:00 explicitly because of the recovered historical protected-vs-interrupted writing pattern. | Later success does not prove the recommendation was optimal; E4 is about material consumption, not optimality. Consumption is observable and specifically pinned. |
| E5 later Outcome / revision behavior | **INVALID** | Cursor31 is a real `dim:work_outcome` Observation and legally completes the WORLD_EVIDENCE Task. Cursor32 support feedback causes no needless claim revision. Cursor36 new `clm_42e66b47b667be52da20ae8a@1` is grounded in the canonical user statement plus incident schedule/outcome Observations. | Rev3→rev4 is semantically overclaimed. The revise call pins real cursor27/30/31 Observations, but its replacement content asserts a 09:00–09:30 designer conversation was placed before writing and treats 10-29 as a fourth direct confirming case. No pinned reality Observation proves that 09:00 conversation occurred; evaluator fixture deliberately withholds which slot was actually used. Worse, cursor30 says drafting began 08:05, so the claim text “09:00–09:30 ... placed before writing” is inconsistent with its own pinned start fact. Confidence was raised 0.5→0.6 on this unclosed interpretation. |
| E6 integrity / contamination / pseudo-LLM | **VALID** | PR #75 has 378 changed files, all under the A run directory; PR #79 has 280 changed files, all under the B run directory. Neither PR contains hidden fixture/evaluator/PM artifacts. A bridge and B bridge are rendezvous/transport executors over real AIOS runtime, with no keyword answer table, automatic search-target selection, Claim generator, revise/retract/silence oracle, or semantic scorer observed. A stops at 24→25; B processes 25→36; `cursor_037/event.json` is empty. Canonical turn receipts show one durable user Observation reused by `run_turn`, not duplicate user ingest. | Evidence is Git-hosted post-run evidence, not independently signed provider telemetry; therefore deliberate manual post-run fabrication cannot be mathematically excluded. No internal discontinuity or artifact indicating such fabrication was found. |

## 4. E1 details — Phase-A cognition

### What is valid

The original durable cognition was not Summary self-proof.

At `wake_146f08e22bd4f1e6f33a3e12`, Resident A first selected four cross-dimensional timeline searches. The capability result exposes both Summary indexes and exact underlying Observations. The following round then pins nine Observation refs directly:

- schedule: `obs_c14_fixture_3195...@1`, `obs_c14_fixture_8a41...@1`, `obs_c14_fixture_6e08...@1`
- device: `obs_c14_fixture_7422...@1`, `obs_c14_fixture_522a...@1`
- work outcome: `obs_c14_fixture_660b...@1`, `obs_c14_fixture_35f8...@1`, `obs_c14_fixture_96ba...@1`
- conversation: `obs_c14_fixture_0ca2...@1`

That evidence is genuinely joint: schedule alone does not prove delivery, work outcome alone does not prove interruption structure, and device activity alone does not prove either. Claim rev1 is therefore a genuine cross-dimensional hypothesis rather than a copied Summary conclusion.

### Why the final Phase-A cognition is only PARTIAL

At the later rev1→rev2 revision, the Resident states that 10-08 delivery occurred “with only 5h48m sleep”. The pinned revision evidence set contains the original nine refs plus the user’s “morning was a little tired” conversation Observation, but not the 5h48 sleep Observation `obs_c14_fixture_056dddd04850d813437e8532@1`.

The fact existed in the World and had been seen earlier, but C14 requires pinned support closure for the content of the durable cognition. Remembering a true fact is not equivalent to pinning it into the revision EvidenceSet. This is a concrete evidence-closure defect, not a stylistic issue.

## 5. E2 details — matched negative

The negative-control sequence does not reduce to event count:

- 10-11 early wake coexists with a 06:25 flight / 05:52 departure.
- 10-14 early wake coexists with 06:00–06:30 building water-valve inspection.
- 10-17 early wake coexists with a 07:00 London meeting once that schedule fact is released.
- 10-19 produces an unconstrained late wake and 8h09 sleep, contradicting the tentative narrow-band interpretation.

Raw model directives show explicit search and semantic silence; the relevant C14 wake completes by `silence`, not by model/tool/capability budget exhaustion or error. The Resident’s stated “>=3” heuristic is a review risk, but the observed control behavior is context-sensitive: three superficially similar early outcomes were not converted into cognition because the external-cause evidence prevented closure, and the later contrary sample was explicitly treated as counter-evidence.

## 6. E3/E4 details — fresh recovery and behavioral use

The B inheritance is byte-identified to A’s frozen World/release state; the evidence manifest states only those two exact A files were copied into the fresh B run.

Before B discovers the Claim, the first cognitive RuntimeSnapshot contains an empty memory-card list. Its world map exposes only mechanical directory metadata, including that `dim:work_outcome` contains some `claim` object type; it does not expose the Claim id or content.

The observable search sequence is:

1. Resident-selected ordinary `search_world` queries over current 10-21 material.
2. Resident-selected `search_timeline(... object_types=["claim"])`.
3. Resident-selected `inspect_world_object` for the Claim returned by search.
4. Periodic Review later revises the recovered Claim to rev3.
5. Cursor26 normal topic retrieval independently surfaces rev3 as the highest-scoring memory card.

At cursor26, no future fixture event 27–29 has yet been released. The user supplies two available times and a deadline; neither option is mechanically ruled out. The Resident then creates a durable Task whose `reason_refs` include the current canonical user Observation and the recovered `clm_79df...@3`, and the user-facing recommendation explicitly cites the old protected/interrupted writing-block evidence. This satisfies material consumption, not merely retrieval.

## 7. E5 details — Outcome and revision blocker

### Valid subparts

- Cursor31 is a real platform work-outcome Observation: first draft completed at 12:08, core structure required no rewrite.
- The Task’s terminal transition uses pinned world evidence and succeeds through the existing WORLD_EVIDENCE completion contract.
- Cursor32’s supportive user statement does not trigger another Claim revision, avoiding confirmation churn.
- No explicit contradictory reality later requires retraction.
- Cursor36’s new user-understanding Claim is typed as `preference` after an initial invalid enum is rejected; the successful write pins the canonical user statement plus the 10-31 incident schedule and incident outcome. Its durable statement is framed as a reported user style and is sufficiently supported for that narrow meaning.

### Blocking subpart

The old Claim’s rev3→rev4 update cannot be accepted as a clean “later Outcome validates prior cognition” proof.

The model passes three real Observation refs into `revise_claim`:
- cursor27 schedule `obs_c14_fixture_2207720973263e409bd2cef2@1`
- cursor30 work start `obs_c14_fixture_3257a682fdb79b091e7d1027@1`
- cursor31 work outcome `obs_c14_fixture_a2532add6d81bd551775e8d3@1`

But the replacement content additionally asserts that the 09:00–09:30 designer sync was actually placed before writing. The fixture’s hidden design deliberately prevents later outcome events from revealing which sync slot was chosen, and none of the three pinned Observations records an actual 09:00 designer interaction. The only direct source of that slot is the Resident’s own earlier Task/response.

Additionally, cursor30 states the release-note draft started at 08:05. Therefore the same rev4 text cannot consistently say a 09:00–09:30 conversation was “before writing”. The revision turns a Resident plan into an observed treatment condition and raises confidence to 0.6. That is exactly the cognition/reality boundary C14 is intended to protect.

This defect is semantic, not mechanical: the capability correctly accepted real refs, but those refs do not support all material content of the revision.

## 8. E6 details — integrity

Independent path audit found:

- PR #75: all 378 changed files are confined to `.../runs/resident-a-restart-20260921/**`.
- PR #79: all 280 changed files are confined to `.../runs/resident-b-20260921/**`.
- No hidden `sealed_fixture`, evaluator notes, PM review, Resident-A FINAL_REPORT, or Resident-A semantic trace appears inside B’s changed file set.
- A release state ends exactly at 24→25 with no cursor25 reveal.
- B release proceeds 25→36; cursor37 event artifact is zero bytes.
- B canonical conversation turn 1 receipt and `j014_turn1` share the same `obs_conv_user_68c898d46eb08fe87b18c45c@1`; `run_turn` does not create a second user Observation.
- The bridges transport exact Runtime snapshots/directives and execute the Resident-selected capability calls; no hidden answer table, semantic score, auto-Claim, auto-revision, auto-silence, or keyword rule was observed.

The remaining anti-forgery limitation is provenance, not an observed contamination finding: Git commits attest the final evidence tree but do not independently attest the live author of every response file.

## 9. Provenance deviations

### Model identity

**Classification: evidence provenance limitation; non-blocking for the semantic findings above.**

Resident A declares GPT-5.6 Sol but the platform does not expose provider/session identity. Resident B records Arena.ai Agent Mode with no exposed underlying model id. Exact model identity therefore cannot be independently attested from repository evidence.

This weakens claims about the precise provider/model used; it does not explain or invalidate the observable AIOS durable-state behavior, and it is not used to excuse E1/E5.

### Python version

**Classification: execution-environment deviation; non-blocking for this semantic audit, but not conformant to the repository’s declared supported runtime.**

`pyproject.toml` requires Python `>=3.12`. Resident A records Python 3.11.2; Resident B also ran under 3.11.2. This means the habitation evidence is not a formal supported-environment certification.

The deviation is not treated as the cause of any semantic verdict because the audited defects are evidence-content defects, and the relevant World/runtime paths did execute durably. A separate release/runtime certification would still need the declared Python version.

### Evidence limitations

**Classification: provenance limitation, not a demonstrated semantic blocker.**

The repository can demonstrate consistent World/release digests, sequential receipts, exact Runtime snapshots, capability histories, and bridge code. It cannot cryptographically prove that a model never saw off-repo information or that a human never edited response files before commit. No positive evidence of such contamination was found.

## 10. Blocking findings

1. **E1-BLOCKER — Phase-A Claim rev2 evidence-closure overreach.**  
   `clm_79df...@2` states the 10-08 case had only 5h48 sleep, but its revision EvidenceSet does not pin `obs_c14_fixture_056dddd04850d813437e8532@1`. The core hypothesis is genuinely cross-dimensional, but the frozen cognition revision is not fully supported by its own pinned closure.

2. **E5-BLOCKER — rev4 promotes Resident plan into reality and raises confidence on an unproven treatment condition.**  
   `clm_79df...@4` says the 09:00–09:30 designer sync was placed before writing and treats the day as a fourth direct confirming case, while no pinned reality Observation proves the sync occurred. Cursor30 says drafting began at 08:05, making the “09:00 before writing” wording internally inconsistent. The later outcome therefore cannot validate the claimed arrangement as written.

No evidence of a Core/pseudo-LLM/future-leak blocker was found in this evaluator task. The blockers are semantic evidence integrity defects in the Resident-produced cognition.

## 11. Overall verdict

`C14 RESIDENT SEMANTIC EVIDENCE = NOT VALID`

Reason: E1 is PARTIAL and E5 is INVALID. Under the binding acceptance rule, any PARTIAL prevents VALID, and any INVALID must be called out explicitly.

This evaluation does **not** authorize `C14-CLOSE-001` as a PASS closure and does not authorize C15. No fix is performed here. PM must decide whether to route this to a fail-closure record or create a dedicated Resident/evidence-semantic repair task that re-validates the affected cognition chain without editing old evidence.
