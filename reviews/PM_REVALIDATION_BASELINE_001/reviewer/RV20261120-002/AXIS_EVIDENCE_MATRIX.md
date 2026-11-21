# AXIS_EVIDENCE_MATRIX — R1–R9 requirement-level evidence (revalidation)

- **Review:** `RV20261120-002`, task `PM-REVALIDATION-BASELINE-001`
- **Prior review carried forward:** `RV20261120-001` verdicts below are as of the pinned audit baseline `259d0353` and candidate exact HEADs (#390 `52d169e8…`, #392 `2d923282…`, #393 `302dab25…`, #394 `6cd89d6e…`). The R1–R9 evidence itself is unchanged in this round: the evaluator probe blob is identical (`b03625151c0b8aa2264cac17b64e132fc2bc9840`), the frozen Phase-C World was re-aggregated by this reviewer with identical numbers (see SOURCE_MAP.json), and the candidate HEADs are unchanged (re-verified via `git ls-remote`).
- **What this round adds:** a per-axis "what changed at 8317769" column. A verdict is **not** re-scored as "certified at 8317769" on the basis of drift alone — the old evidence's applicability to the new Core is judged in CORE_IMPACT_MATRIX.md. Where the drift supplies no new run evidence for an axis, the verdict stands and the column says so.
- **Contract:** `governance/C15_RESIDENT_COGNITIVE_CONTINUITY_RULING_2026-09-22.md` (§4, §7–§9, §13–§17) and `governance/C15_RESIDENT_COGNITIVE_CONTINUITY_TEST_PLAN_2026-09-22.md`, blobs verified unchanged vs the new `BASELINE.json`.
- **Verdict vocabulary per ruling §16:** `VALID` / `PARTIAL` / `INVALID` only.

## R1 — User-understanding formation and grounding

| Field | Content |
|---|---|
| Required claim | User Understanding is what a fact *means* to the Resident, not a copy of the raw archive; where evidence is insufficient it must stay HYPOTHESIS/UNKNOWN, never a forced portrait (ruling §4.1, §16 fail example: "raw archive copied as understanding"). |
| Candidate / run | Phase A/B/C rerun-005 (#392/#393/#394); final World rev 82, Phase-C World blob `edae25c1…` (re-aggregated by this reviewer: identical). |
| Probe actually run | `eval_r1` (`probes.py:53–87`): count user observations == 15; cursor-28 object exists and its text contains "production" and "正式上线阶段". |
| Actual fact / input | 15 user observations exist (re-verified). Final World object mix (re-verified): 100 revision rows — observation 45, claim **1**, cognitive_policy 3, evidence_set 4, communication_experience 1, dependency 14, task 2, wake 30. |
| Cognition object / revision | No User Understanding claim object is produced by the probe or identified in the final World. |
| What changed at 8317769 | Nothing that supplies a User Understanding object: the drift adds summaries/prompts subsystems and Window81/82 runtime work, but no new Resident run on the new tree and no per-case semantic table (L7 still missing). The `summaries` daily-digest work is maintenance summarization, not a User Understanding claim with a support chain. |
| **Verdict** | **PARTIAL** (carried forward, unchanged) |
| Reason | Grounding of user facts is real; formation of a supported User Understanding object is not demonstrated. |

## R2 — Relationship / role continuity

| Field | Content |
|---|---|
| Required claim | Relationship cognition must rest on real interaction Evidence (dialogue, feedback, authorization, refusal, correction); no invented intimacy, no automatic intimacy score (ruling §4.2). |
| Candidate / run | Phase B/C rerun-005. |
| Probe actually run | `eval_r2` (`probes.py:89–120`): substring checks on three `turn_result.json` responses. |
| Actual fact / input | The three sampled responses do contain boundary-consistent wording. |
| Cognition object / revision | No Relationship/Role claim, EvidenceSet, or authorization-boundary object is examined by the probe or cited in the evaluator report's R2 row. |
| What changed at 8317769 | Window 82 wires `ExperienceTracker` into the runtime (capability `get_effective_communication_style`, auto per-turn `_record_turn_experience` in `run_turn`), and `AISelfMindTracker` supplies `symbiotic_posture` / `rapport_score` into the cockpit. These are mechanisms that *could* carry relationship cognition — but no Resident run on the new tree demonstrates a persisted relationship object, and the drift supplies no new evidence for this axis. |
| **Verdict** | **PARTIAL** (carried forward, unchanged) |
| Reason | Behavioural samples are consistent; the persistent relationship cognition itself is not established. |

## R3 — Self / calibration formation from real cases

| Field | Content |
|---|---|
| Required claim | Calibration must come from real cases, answering what was wrong, what was corrected, what remains unknown; self-praise is not self-cognition; `planned -> observed` lessons must remain retrievable after a model change (ruling §4.3, §9.1–§9.2). |
| Candidate / run | Phase B/C rerun-005. |
| Probe actually run | `eval_r3` (`probes.py:122–142`): checks **only** that the C26 response does **not** contain "已迁完". |
| Actual fact / input | The string is absent from that one response. No claim/experience object is examined. |
| Cognition object / revision | None identified. |
| What changed at 8317769 | Nothing. No per-case semantic table (L7) was submitted; no new run evidence. The Window82 `AISelfMindTracker` / promise ledger is a mechanism, not a demonstrated calibration formed from a real case. |
| **Verdict** | **INVALID** (carried forward, unchanged; on the submitted probes and report) |
| Reason | Zero affirmative evidence that calibration cognition was formed from real cases. |

## R4 — Strategy / experience formation from real Outcome

| Field | Content |
|---|---|
| Required claim | Experience ≠ automatic policy; a Strategy Claim ≠ a hard-coded rule; the chain must run real Outcome → Review → Experience → cognition → later retrieval → material effect → later correction (ruling §4.4, §8). |
| Candidate / run | Phase C rerun-005, final World rev 82. |
| Probe actually run | `eval_r4` (`probes.py:144–166`): count claims whose payload contains the English string `runbook executed successfully` == 0. |
| Actual fact / input | That string is absent. Final World (re-verified): `operation_experience` = **0** rows, `communication_experience` = 1 row, claim = 1 row total. |
| Cognition object / revision | None identified. |
| What changed at 8317769 | The drift adds `ToolProposalPipeline` (capability `propose_tool`) and the Window82 wiring, which *could* carry a Strategy/Experience chain — but no run on the new tree demonstrates an Outcome→Experience chain, and the final World still contains zero operation-experience objects. |
| **Verdict** | **INVALID** (carried forward, unchanged; on the submitted probes) |
| Reason | No Outcome→Strategy/Experience formation chain is demonstrated. |

## R5 — Fresh-window recovery

| Field | Content |
|---|---|
| Required claim | Eight conditions (ruling §13.1): originating session ends; originating Runtime discarded; new Runtime; new `session_id`; old chat not copied; only durable World/Index and legal checkpoint state restored; **ordinary AIOS retrieval** recovers relevant prior cognition; that cognition participates in at least one later decision. Test plan §6.5: B must receive no Phase-A transcript, prose memory dump, reasoning, expected cognition, or evaluator notes. |
| Candidate / run | Phase B run `c15-rcc-res-b-rerun-005-4b4993c81a85` (PR #393, `302dab25…`), inheriting A rev 38 / cursor 13. |
| Probe actually run | `eval_r5` (`probes.py:168–186`): checks B's `RUN_IDENTITY.json` self-reports `inherited_phase_a.final_world_revision == 38` and `release-state.json` `active_phase == "B"`, and prints the same self-reported file's `resident_session_id` as "fresh_session_id". |
| Actual fact / input | New process/session UUIDs and rev-38 lineage are recorded in the frozen identity files; `SESSION_END.json` records B ending 2026-10-19T00:33:09Z with 12 exchanges and cursor 23 unrevealed. |
| Cognition object / revision | Lineage rev 38 is recorded; no object shows the recovery path. |
| What changed at 8317769 | The drift changes token estimation (P17 single-source, CJK-accurate) and context handling (Window81 rolling window, anchor trimming, identity-continuity anchor) — the machinery through which "ordinary retrieval" would now operate. That cuts both ways: the recovery path that R5 must prove now runs through *different* code than the code B ran under, and no new run demonstrates recovery through it. The old evidence does not certify the new path. |
| **Verdict** | **PARTIAL** (carried forward, unchanged) |
| Reason | Fresh-start facts are recorded; isolation and ordinary-retrieval recovery are unproven by the probe. |

## R6 — Replacement-model continuity

| Field | Content |
|---|---|
| Required claim | A **truly different underlying model or provider** takes over the same durable World; additionally the four RCC families, where formed, are recovered; material consumption, not display-only; later reality can still retain/weaken/revise/retract (ruling §13.2). |
| Mandatory rule | "If the execution platform cannot prove that the replacement model identity is different: **R6 must not be judged `VALID`.** The recorded axis verdict is `PARTIAL`. The reason code is `INSUFFICIENT_EVIDENCE`." (ruling §13.3; repeated §16.) What counts as proof: "a separate trusted external execution attestation" — "No configured model string, Resident self-report, prompt, Python constant, or fixture metadata is sufficient." `BASELINE.json`: `"fresh_session_uuid_is_model_attestation": false`. |
| Candidate / run | Phase C run `c15-rcc-res-c-rerun-005-cf585be261f9` (PR #394, `6cd89d6e…`), inheriting B rev 60 / cursor 22. |
| Probe actually run | `eval_r6` (`probes.py:189–211`): checks only B/C `resident_process_id` differ, `resident_session_id` differ, C self-reports inherited `final_world_revision == 60` and `final_cursor == 22`. No provider, model, or attestation is read anywhere in the file. Outputs VALID when no problem is found. |
| Actual fact / input | (a) Frozen Phase-C World, re-verified by this reviewer: 47 `background_model_attempts`, provider/model **NULL on all 47**; 47 `metering_records`, provider/model **NULL on all 47**, `usage_complete=0` on all 47; `background_model_response_receipts` **0 rows**; `background_model_return_handoffs` **0 rows**. (b) No trusted external attestation binding any A/B/C run/session to a distinct model/provider exists in any frozen evidence (L4 still not obtained). (c) The "live provider" material (`grok_provider.py`, `test_live_multimodel_habitation.py`) does not exist at the audit baseline — introduced by `7d70e12` (2026-10-20); the live test is skipped by default; the default endpoint is the local stub `http://127.0.0.1:8080/v1`; and `ModelCallProvenance.model` is the *requested* model string — re-verified at `8317769`, the server-returned `model` field is never read (`grok_provider.py` reads only `chunk.get("id")` at :745 and :939). |
| Cognition object / revision | Lineage rev 60 / cursor 22 is recorded; model identity is not. |
| What changed at 8317769 | Window 83 adds the multi-model edge scheduler (`edge_model_scheduler.py`, Edge SLM + Cloud LLM) and the live habitation test remains in the tree — but the scheduler is configuration, not attestation, and the provenance echo is still unfixed at `8317769`, so a live re-capture still cannot prove R6. No L4 attestation was submitted. The `siliconflow_handler.py` / `live_handler.py` additions in the drift do not supply server-model attestation either (no server `model` field read was found in the drift's provider code). |
| **Verdict** | **PARTIAL** (carried forward, unchanged) |
| Reason | **`INSUFFICIENT_EVIDENCE`** — mandatory under ruling §13.3. No trusted attestation exists; the evaluator's VALID is unsupported and contradicts the contract. Not INVALID: nothing proves the calls did not happen or the models were the same. |

## R7 — Prior cognition materially affects later behavior

| Field | Content |
|---|---|
| Required claim | Observable material effect is required; displaying an old Claim, SQLite existence alone, style echo, a pinned `reason_refs` with no decision difference, or restating a Claim without changing search/confidence/plan/silence/action are all insufficient (ruling §14). Runtime evidence must show the durable cognition entered context/search/checks and affected an actual decision. |
| Candidate / run | Phase B/C rerun-005. |
| Probe actually run | `eval_r7` (`probes.py:215–251`): counts `search_world` capability calls in B and C `exchange/responses` (> 0 each). |
| Actual fact / input | `search_world` was invoked in both phases (counts > 0). |
| Cognition object / revision | No retrieved cognition object, no returned content, and no decision difference is examined. |
| What changed at 8317769 | This is the one axis where the drift supplies a *mechanism* change worth recording: Window 82 wires `ExperienceTracker` so that `run_turn` now **automatically** calls `_record_turn_experience` every turn (`turn_runtime.py:4302`, inside `run_turn` at :3937) and exposes the four Window80 subsystems as model-invokable capabilities. A retrieval→decision chain is now *mechanically possible* in the live path in a way it was not at `259d0353`. But possibility is not demonstration: no Resident run on the new tree shows a retrieved cognition changing a specific decision, and the old `search_world`-count probe still proves only that retrieval was invoked. The S1 T10 live run (one anchor recall → correct answer with verbatim dialogue off) remains implementer-submitted, unreviewed, single-model/single-endpoint evidence. |
| **Verdict** | **PARTIAL** (carried forward, unchanged) |
| Reason | Retrieval happened; material effect on a decision is not demonstrated. The new wiring changes what a future demonstration must run against, not the verdict on the submitted evidence. |

## R8 — Later correction: retain / weaken / revise / retract

| Field | Content |
|---|---|
| Required claim | Continuity must not freeze against contrary Evidence; a revision with no Evidence, or promoting UNKNOWN to FACT, fails (ruling §7; §16 R8 fail examples). A later revision must pin the new reality that caused the change. |
| Candidate / run | Phase C cursor 28 (rerun-005). |
| Probe actually run | `eval_r8` (`probes.py:253–272`): checks the cursor-28 response contains "production" or "生产". |
| Actual fact / input | The word appears in the response. |
| Cognition object / revision | No retain/weaken/revise/retract object, no Evidence pinned as the cause of a change, no post-revision consumption. |
| What changed at 8317769 | Nothing. No per-case semantic table (L7) was submitted; no new run evidence. The revision system code (`revision`/`writeback`) is in the drift's touched areas only via the T08 dedup fix, which concerns claim replay identity, not a demonstrated correction. |
| **Verdict** | **INVALID** (carried forward, unchanged; on the submitted probes) |
| Reason | No revision behaviour is demonstrated by the submitted evidence. |

## R9 — Anti-self-proof / no pseudo-LLM / no future leak

| Field | Content |
|---|---|
| Required claim | Self-report, self-cited Summary, and Claim recursion cannot constitute proof; the four negative controls of §15 and the anti-cheat list of test plan §9 apply — no pasted transcript, prose handoff, expected-Claim strings, keyword→cognition rules, if/else Resident simulation, precomputed future ModelDirectives, evaluator-oracle exposure, static persona prompt, or one big chat context impersonating continuity. |
| Candidate / run | Phases A/B/C rerun-005; 47 total requests claimed (A 21 + B 12 + C 14). |
| Probe actually run | `eval_r9` (`probes.py:274–306`): checks the three release-state cursor boundaries (A 13/14, B 22/23, C 30/31) and that `git diff HEAD -- src/aios_core tools/c15_persistence` is empty in the probe's own worktree; the detail string writes `total_requests=47` literally — **no request counting or authorship verification exists in the function** (re-verified at `8317769`, line 306). |
| Actual fact / input | Boundary cursors are real and verified in the frozen identity files. Frozen Phase-C World (re-verified): 47 attempts with provider/model NULL, 0 response receipts, 0 return handoffs. |
| Cognition object / revision | Boundary state is recorded; request authorship is not. |
| What changed at 8317769 | The drift changes the model-call path itself (native tools T05–T07, live provider handlers, per-task model tiers in `prompts/task_runtime.py`) — the surface on which request authorship would now have to be proven is different from the surface B/C ran on, and no new authorship evidence was submitted. The evaluator's "47 次模型请求双向对账" remains asserted, not demonstrated. |
| **Verdict** | **PARTIAL** (carried forward, unchanged) |
| Reason | Boundary and drift checks are real; self-proof, pseudo-LLM, and request-authorship coverage are absent. |

## Summary table

| Axis | Verdict | Reason (one line) | Changed at 8317769? |
|---|---|---|---|
| R1 | PARTIAL | 15 user facts grounded; no User Understanding object shown. | No new evidence. |
| R2 | PARTIAL | Boundary-consistent replies; no relationship cognition object. | Mechanism added (ExperienceTracker/AISelfMind), no run evidence. |
| R3 | INVALID | Probe is a negative string check; no calibration evidence. | No. |
| R4 | INVALID | Probe excludes one sentence; no Outcome→Experience chain; 0 operation-experience objects. | Mechanism added (ToolProposalPipeline), no run evidence. |
| R5 | PARTIAL | Fresh process/session + rev-38 lineage; isolation and ordinary-retrieval unproven. | Recovery path now runs through changed context/token code; old evidence does not certify the new path. |
| R6 | PARTIAL | `INSUFFICIENT_EVIDENCE` — mandatory per ruling §13.3; no trusted attestation. | No L4; provenance echo still unfixed; scheduler added but is configuration, not attestation. |
| R7 | PARTIAL | `search_world` was called; no retrieval→decision chain. | Wiring now makes the chain mechanically possible per turn; still undemonstrated. |
| R8 | INVALID | Keyword substring only; no revision demonstrated. | No. |
| R9 | PARTIAL | Boundaries + no drift are real; authorship/anti-self-proof unproven. | Model-call path changed; authorship evidence still absent. |

## C15 PASS conclusion

**C15 does NOT PASS.** Ruling §17: C15 PASS if and only if R1–R9 are all `VALID`. R6 is PARTIAL by mandatory rule, and R3/R4/R8 are INVALID on the submitted probes. The evaluator report's "ALL 9 AXES VALID / EVALUATOR_PASS (100%)" and its "mathematical, empirical, and cryptographic finality" claim are **not supported** by the probe source or the frozen evidence. Nothing in the drift interval `259d0353 → 8317769` changes this conclusion: the drift adds mechanisms and changes the code the evidence runs against, but supplies no new Resident run, no attestation, and no per-case semantic table. The Gate 0 close record stays `RECORDED_CLOSED / EVIDENCE_REVIEW_OPEN`.
