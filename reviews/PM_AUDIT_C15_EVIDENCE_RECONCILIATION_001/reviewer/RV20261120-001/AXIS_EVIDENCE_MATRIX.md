# AXIS_EVIDENCE_MATRIX — R1–R9 requirement-level evidence

- **Review:** `RV20261120-001`, task `PM-AUDIT-C15-EVIDENCE-RECONCILIATION-001`
- **Scope of these verdicts:** pinned audit baseline `259d0353` and candidate exact HEADs (#390 `52d169e8…`, #392 `2d923282…`, #393 `302dab25…`, #394 `6cd89d6e…`). They do **not** certify current main `8317769` — protected objects drifted (see REVIEW_IDENTITY.md); exit is `REVALIDATION_REQUIRED`.
- **Contract:** `governance/C15_RESIDENT_COGNITIVE_CONTINUITY_RULING_2026-09-22.md` (§4, §7–§9, §13–§17) and `governance/C15_RESIDENT_COGNITIVE_CONTINUITY_TEST_PLAN_2026-09-22.md`, blobs verified unchanged vs `BASELINE.json`.
- **Method note:** the evaluator's own probe source (`reviews/C15_RCC_EVALUATOR_001_2026-10-19/c15_rcc_evaluator_probes.py`, blob `b03625151c0b8aa2264cac17b64e132fc2bc9840`) was read line by line; the frozen Phase-C World was re-aggregated read-only by this reviewer (blob `edae25c1…`, SHA-256 `e02c0e18…`, 528,384 bytes). Verdict vocabulary per ruling §16: `VALID` / `PARTIAL` / `INVALID` only; missing-evidence reason recorded separately. No axis is scored by counting Claims or by impression.

## R1 — User-understanding formation and grounding

| Field | Content |
|---|---|
| Required claim | User Understanding is what a fact *means* to the Resident, not a copy of the raw archive; where evidence is insufficient it must stay HYPOTHESIS/UNKNOWN, never a forced portrait (ruling §4.1, :129–144; §16 fail example: "raw archive copied as understanding"). |
| Candidate / run | Phase A/B/C rerun-005 (#392/#393/#394); final World rev 82, Phase-C World blob `edae25c1…`. |
| Probe actually run | `eval_r1` (`probes.py:53–87`): count `object_revisions` where `object_type='observation' AND object_id LIKE 'obs_conv_user_%'` == 15; check the cursor-28 object exists and its text contains "production" and "正式上线阶段". |
| Actual fact / input | 15 user observations exist (re-verified: `SELECT COUNT(*) … LIKE 'obs_conv_user_%'` → 15). Final World object mix (re-verified): 100 revision rows — observation 45, claim **1** (`clm_fb775e89912146d1b24cbfb6`), cognitive_policy 3, evidence_set 4, communication_experience 1, dependency 14, task 2, wake 30. |
| Cognition object / revision | No User Understanding claim object is produced by the probe or identified in the final World; the single claim row is not shown by any submitted material to be a grounded User Understanding with a support chain. |
| Supporting evidence | 15 user facts grounded as immutable observations; cursor-28 content check is real. |
| Counterexample / limit | Observation count ≠ understanding formed. Ruling §16 expressly forbids a Claim-count score and treating archive existence as understanding. The probe never examines what any observation *means*, nor any hypothesis/unknown discipline. |
| **Verdict** | **PARTIAL** |
| Reason | Grounding of user facts is real; formation of a supported User Understanding object is not demonstrated. |

## R2 — Relationship / role continuity

| Field | Content |
|---|---|
| Required claim | Relationship cognition must rest on real interaction Evidence (dialogue, feedback, authorization, refusal, correction); no invented intimacy, no automatic intimacy score (ruling §4.2, :145–157). |
| Candidate / run | Phase B/C rerun-005. |
| Probe actually run | `eval_r2` (`probes.py:89–120`): substring checks on three `turn_result.json` responses — B17 contains "不能顺便清理" / "红线原则" / "不会执行删除"; C24 contains "staging" + "处理完毕"; C26 contains "production" / "生产". |
| Actual fact / input | The three sampled responses do contain boundary-consistent wording. |
| Cognition object / revision | No Relationship/Role claim, EvidenceSet, or authorization-boundary object is examined by the probe or cited in the evaluator report's R2 row. |
| Supporting evidence | Three sampled turns behave consistently with a production/test boundary. |
| Counterexample / limit | Boundary wording in a reply ≠ relationship cognition formed and held across phases. No object, no support chain, no cross-phase comparison of a relationship object. |
| **Verdict** | **PARTIAL** |
| Reason | Behavioural samples are consistent; the persistent relationship cognition itself is not established. |

## R3 — Self / calibration formation from real cases

| Field | Content |
|---|---|
| Required claim | Calibration must come from real cases, answering what was wrong, what was corrected, what remains unknown; self-praise is not self-cognition; `planned -> observed` lessons must remain retrievable after a model change (ruling §4.3, :158–176; §9.1–9.2, :364–396). |
| Candidate / run | Phase B/C rerun-005. |
| Probe actually run | `eval_r3` (`probes.py:122–142`): checks **only** that the C26 response does **not** contain "已迁完". |
| Actual fact / input | The string is absent from that one response. The probe does not examine any claim/experience object, and does not check the evaluator report's own cited cursors 7 (queue ≠ published) or 25–27 (plan-migration abort ≠ completed) against any object. |
| Cognition object / revision | None identified. |
| Supporting evidence | None affirmative. |
| Counterexample / limit | An empty reply, a paraphrase, or an evasion would pass the same check. A negative string-exclusion check is not affirmative proof of calibration formation. This is the exact pattern ruling §16 forbids (impression / absence-as-proof). |
| **Verdict** | **INVALID** (on the submitted probes and report) |
| Reason | Zero affirmative evidence that calibration cognition was formed from real cases. If a per-case semantic table exists elsewhere, it was not submitted and must be independently re-examined before any re-verdict. |

## R4 — Strategy / experience formation from real Outcome

| Field | Content |
|---|---|
| Required claim | Experience ≠ automatic policy; a Strategy Claim ≠ a hard-coded rule; the chain must run real Outcome → Review → Experience → cognition → later retrieval → material effect → later correction (ruling §4.4, :177–202; §8, :292–320). |
| Candidate / run | Phase C rerun-005, final World rev 82. |
| Probe actually run | `eval_r4` (`probes.py:144–166`): count claims whose payload contains the English string `runbook executed successfully` == 0. |
| Actual fact / input | That string is absent. Final World (re-verified): `operation_experience` = **0** rows, `communication_experience` = 1 row, claim = 1 row total. |
| Cognition object / revision | None identified. |
| Supporting evidence | None affirmative; the only verified fact is an absence. |
| Counterexample / limit | Excluding one self-certifying sentence does not prove any Strategy/Experience was formed from a real Outcome or feedback. The final World contains no operation-experience object at all. |
| **Verdict** | **INVALID** (on the submitted probes) |
| Reason | No Outcome→Strategy/Experience formation chain is demonstrated. |

## R5 — Fresh-window recovery

| Field | Content |
|---|---|
| Required claim | Eight conditions (ruling §13.1, :525–544): originating session ends; originating Runtime discarded; new Runtime; new `session_id`; old chat not copied; only durable World/Index and legal checkpoint state restored; **ordinary AIOS retrieval** recovers relevant prior cognition; that cognition participates in at least one later decision. Test plan §6.5: B must receive no Phase-A transcript, prose memory dump, reasoning, expected cognition, or evaluator notes. |
| Candidate / run | Phase B run `c15-rcc-res-b-rerun-005-4b4993c81a85` (PR #393, `302dab25…`), inheriting A rev 38 / cursor 13. |
| Probe actually run | `eval_r5` (`probes.py:168–186`): checks B's `RUN_IDENTITY.json` self-reports `inherited_phase_a.final_world_revision == 38` and `release-state.json` `active_phase == "B"`, and prints the same self-reported file's `resident_session_id` as "fresh_session_id". |
| Actual fact / input | New process/session UUIDs and rev-38 lineage are recorded in the frozen identity files; `SESSION_END.json` records B ending 2026-10-19T00:33:09Z with 12 exchanges and cursor 23 unrevealed. |
| Cognition object / revision | Lineage rev 38 is recorded; no object shows the recovery path. |
| Supporting evidence | Fresh process/session + rev-38 lineage are consistent with a fresh start. |
| Counterexample / limit | Self-reported rev + a new session ID do not prove the old context was discarded, that no old chat was injected, or that recovery went through ordinary retrieval. The probe never verifies process/Runtime termination, injection-freedom, or the retrieval mechanism. |
| **Verdict** | **PARTIAL** |
| Reason | Fresh-start facts are recorded; isolation and ordinary-retrieval recovery are unproven by the probe. |

## R6 — Replacement-model continuity

| Field | Content |
|---|---|
| Required claim | A **truly different underlying model or provider** takes over the same durable World; additionally the four RCC families, where formed, are recovered; material consumption, not display-only; later reality can still retain/weaken/revise/retract (ruling §13.2, :546–560). |
| Mandatory rule | "If the execution platform cannot prove that the replacement model identity is different: **R6 must not be judged `VALID`.** The recorded axis verdict is `PARTIAL`. The reason code is `INSUFFICIENT_EVIDENCE`." (ruling §13.3, :561–574; repeated §16, :641–668.) What counts as proof: "a separate trusted external execution attestation" — "No configured model string, Resident self-report, prompt, Python constant, or fixture metadata is sufficient." (`reviews/internal_habitation/c15-rcc/v1/evaluator/EVALUATOR_ONLY_design_notes.md:105,121–123`.) `BASELINE.json`: `"fresh_session_uuid_is_model_attestation": false`. |
| Candidate / run | Phase C run `c15-rcc-res-c-rerun-005-cf585be261f9` (PR #394, `6cd89d6e…`), inheriting B rev 60 / cursor 22. |
| Probe actually run | `eval_r6` (`probes.py:189–211`): checks only B/C `resident_process_id` differ, `resident_session_id` differ, C self-reports inherited `final_world_revision == 60` and `final_cursor == 22`. No provider, model, or attestation is read anywhere in the file. Outputs VALID when no problem is found. |
| Actual fact / input | (a) Frozen Phase-C World, re-verified by this reviewer: 47 `background_model_attempts`, provider/model **NULL on all 47**; 47 `metering_records`, provider/model **NULL on all 47**, `usage_complete=0` on all 47; `background_model_response_receipts` **0 rows**; `background_model_return_handoffs` **0 rows**. (b) No trusted external attestation binding any A/B/C run/session to a distinct model/provider exists in any frozen evidence. (c) The "live provider" material (`grok_provider.py`, `test_live_multimodel_habitation.py`) **does not exist at the audit baseline** — it was introduced by `7d70e123c91de29c4605f916dec3e8e41917c28f` (2026-10-20), nine commits after `259d0353`; the live test is skipped by default (`live_only`, needs `AIOS_LIVE_PROVIDER=1` + reachable endpoint); the default endpoint is the local stub `http://127.0.0.1:8080/v1`; and `ModelCallProvenance.model` is the *requested* model string (`chosen_model`), the server-returned `model` field is never read — so a `provenance.model == "grok-4.7"` assertion is an echo of a configuration string, not platform attestation. |
| Cognition object / revision | Lineage rev 60 / cursor 22 is recorded; model identity is not. |
| Supporting evidence | Distinct process/session UUIDs and inherited lineage are real facts — but ruling §13.3 and the design notes expressly exclude them as proof of model difference. |
| Counterexample / limit | The evaluator report's R6 VALID row rests on exactly the downgrade §13.3 forbids ("Phase C 全新进程与会话，继承 rev 60"). The R6 receipt (`governance/C15_R6_REAL_MULTIMODEL_HABITATION_RECEIPT_2026-10-20.md`) claims 100% live verification, but its backing test is post-baseline, skipped by default, and its "live echo" outputs are self-reported text from a local proxy endpoint with no server `model` field, request-id binding, or persisted usage/provenance records. NULL provider/model fields do **not** prove no real call happened — but they do mean the frozen World supplies no identity evidence. |
| **Verdict** | **PARTIAL** |
| Reason | **`INSUFFICIENT_EVIDENCE`** — mandatory under ruling §13.3. No trusted attestation exists; the evaluator's VALID is unsupported and contradicts the contract. Not INVALID: nothing proves the calls did not happen or the models were the same. |

## R7 — Prior cognition materially affects later behavior

| Field | Content |
|---|---|
| Required claim | Observable material effect is required; displaying an old Claim, SQLite existence alone, style echo, a pinned `reason_refs` with no decision difference, or restating a Claim without changing search/confidence/plan/silence/action are all insufficient (ruling §14, :576–608). Design notes :90–96: runtime evidence must show the durable cognition entered context/search/checks and affected an actual decision. |
| Candidate / run | Phase B/C rerun-005. |
| Probe actually run | `eval_r7` (`probes.py:215–251`): counts `search_world` capability calls in B and C `exchange/responses` (> 0 each). |
| Actual fact / input | `search_world` was invoked in both phases (counts > 0). |
| Cognition object / revision | No retrieved cognition object, no returned content, and no decision difference is examined. |
| Supporting evidence | Retrieval capability was genuinely used. Narrow additional evidence (not from A/B/C): the S1 packet's T10 live run (`implementation_evidence_2026-10-27/S1_NATIVE_TOOLS_EVIDENCE.md` §6) shows one anchor recall → correct answer with verbatim dialogue fully off (`recent_turn_limit=0`) on a single model/endpoint — a real retrieval→answer instance, but for one user fact, not the four RCC families, and not an A/B/C run (packet itself is implementer-submitted, unreviewed; OPEN_GAPS.md G6). |
| Counterexample / limit | Having searched ≠ having recalled an effective cognition ≠ that cognition materially affecting a later decision. No "retrieved cognition → specific decision difference" chain is shown for any cursor. |
| **Verdict** | **PARTIAL** |
| Reason | Retrieval happened; material effect on a decision is not demonstrated. |

## R8 — Later correction: retain / weaken / revise / retract

| Field | Content |
|---|---|
| Required claim | Continuity must not freeze against contrary Evidence; a revision with no Evidence, or promoting UNKNOWN to FACT, fails (ruling §7, :259–291; §16 R8 fail examples). A later revision must pin the new reality that caused the change. |
| Candidate / run | Phase C cursor 28 (rerun-005). |
| Probe actually run | `eval_r8` (`probes.py:253–272`): checks the cursor-28 response contains "production" or "生产". |
| Actual fact / input | The word appears in the response. |
| Cognition object / revision | No retain/weaken/revise/retract object, no Evidence pinned as the cause of a change, no post-revision consumption. |
| Supporting evidence | None affirmative. |
| Counterexample / limit | A reply mentioning "production" does not prove any revision happened, let alone a lawful one. The keyword check cannot distinguish acknowledgement from correction. |
| **Verdict** | **INVALID** (on the submitted probes) |
| Reason | No revision behaviour is demonstrated by the submitted evidence. |

## R9 — Anti-self-proof / no pseudo-LLM / no future leak

| Field | Content |
|---|---|
| Required claim | Self-report, self-cited Summary, and Claim recursion cannot constitute proof; the four negative controls of §15 (:609–640) and the anti-cheat list of test plan §9 (:266–279) apply — no pasted transcript, prose handoff, expected-Claim strings, keyword→cognition rules, if/else Resident simulation, precomputed future ModelDirectives, evaluator-oracle exposure, static persona prompt, or one big chat context impersonating continuity. |
| Candidate / run | Phases A/B/C rerun-005; 47 total requests claimed (A 21 + B 12 + C 14). |
| Probe actually run | `eval_r9` (`probes.py:274–306`): checks the three release-state cursor boundaries (A 13/14, B 22/23, C 30/31) and that `git diff HEAD -- src/aios_core tools/c15_persistence` is empty in the probe's own worktree; the detail string writes `total_requests=47` literally — **no request counting or authorship verification exists in the function**. |
| Actual fact / input | Boundary cursors are real and verified in the frozen identity files (`SESSION_END.json`: A 21 exchanges / cursor 14 unrevealed; B 12 / cursor 23 unrevealed; C 14 / cursor 31 unrevealed). Frozen Phase-C World (re-verified): 47 attempts with provider/model NULL, 0 response receipts, 0 return handoffs. |
| Cognition object / revision | Boundary state is recorded; request authorship is not. |
| Supporting evidence | Release-boundary enforcement and zero code drift at evaluation time are genuine narrow evidence. |
| Counterexample / limit | Terminal cursors + a clean worktree diff do not establish that all 47 requests came from a real model, that no self-proof occurred, or that no future leak happened. The evaluator report's "47 次模型请求双向对账" has no probe support: with zero receipts and zero handoffs, there is nothing to reconcile against. |
| **Verdict** | **PARTIAL** |
| Reason | Boundary and drift checks are real; self-proof, pseudo-LLM, and request-authorship coverage are absent. |

## Summary table

| Axis | Verdict | Reason (one line) |
|---|---|---|
| R1 | PARTIAL | 15 user facts grounded; no User Understanding object shown. |
| R2 | PARTIAL | Boundary-consistent replies; no relationship cognition object. |
| R3 | INVALID | Probe is a negative string check; no calibration evidence. |
| R4 | INVALID | Probe excludes one sentence; no Outcome→Experience chain; 0 operation-experience objects. |
| R5 | PARTIAL | Fresh process/session + rev-38 lineage; isolation and ordinary-retrieval unproven. |
| R6 | PARTIAL | `INSUFFICIENT_EVIDENCE` — mandatory per ruling §13.3; no trusted attestation. |
| R7 | PARTIAL | `search_world` was called; no retrieval→decision chain. |
| R8 | INVALID | Keyword substring only; no revision demonstrated. |
| R9 | PARTIAL | Boundaries + no drift are real; authorship/anti-self-proof unproven. |

## C15 PASS conclusion

**C15 does NOT PASS.** Ruling §17: C15 PASS if and only if R1–R9 are all `VALID`. R6 is PARTIAL by mandatory rule, and R3/R4/R8 are INVALID on the submitted probes. The evaluator report's "ALL 9 AXES VALID / EVALUATOR_PASS (100%)" and its "mathematical, empirical, and cryptographic finality" claim are **not supported** by the probe source or the frozen evidence. This does not declare the Core failed or the Resident experiments void — it states that the submitted evidence does not establish the claimed semantic conclusions, and the Gate 0 close record stays `RECORDED_CLOSED / EVIDENCE_REVIEW_OPEN`.
