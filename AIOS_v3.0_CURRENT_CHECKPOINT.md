# AIOS v3.0 当前工程断点

> 用途：新会话 / 新模型 / 新工程师进入仓库后的第一现场状态文件  
> 更新规则：每完成一个可验证节点立即更新；不得靠聊天记忆代替本文件  
> 仓库：`Haneof/Haneof-AIOS-Core-v3.0`  
> 分支：`main`

## 2026-09-21 单窗口执行控制

跨窗口施工的“下一任务”唯一来源：

`governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`

规则：一个窗口只执行一个 Task ID；完成后必须写回 task board + 本 checkpoint，然后停止。不得根据下方历史“下一动作”重复施工。


## 当前工程断点 — B candidate 未通过；纠偏治理 GATE，实验不得启动

> PM / operator only。盲测 Resident 不得读取本 checkpoint；只读独立获准的安全启动包。下方所有“历史工程断点”的 READY/下一动作只记录当时状态，不再作为当前任务授权。

- 2026-09-23 reviewed main：`ed07b5890909ae09cb2a0849729662b4235c1e3b`。
- Canonical frozen Core：`bcd6bf353126318f9a97076b52ec1740d43f35a4`；语义 freeze ACTIVE；该 exact Core 的 19 个 push workflows 均 SUCCESS（历史 GitHub 结果，本窗口未跑测试）。
- C14 既有闭环 PASS；canonical A #117 @ `3e51f728d7959048b75fea01d405bc837b0e8185` 接受状态和原始 hash 不变。
- Reviewed B #121 @ `b6e5ac939bef83615292bcf9b9099d76737d82b0`：NOT ACCEPTED。World 97 / index 88；新增 9 条均为输入 Observation；无 B session 计量、原始模型/能力调用轨迹或 restart checkpoint。报告自评 PASS 不替代独立验收。
- 新 Claim 数量不是 Gate；不足是运行证据与索引交付，而非要求模型制造认知。不据此修改 frozen Core。
- 处置随纠偏 PR 合入生效：旧 B task FAILED（candidate acceptance），#121 保持 OPEN / UNMERGED / PINNED / NON-CANONICAL；不回填、不覆盖、不传给 C。
- `C15-RCC-RES-B-CORRECTIVE-001 = GATE / PENDING_MAIN_INTEGRATION`。独立集成 PM 审查治理/CI，实际合入并写回 DONE 后，唯一下一 READY 为 `C15-RCC-RES-B-PREFLIGHT-001`；当前无获准启动的 Resident 实验。
- 后续：operator preflight → 独立环境放行 → fresh B → 独立执行证据验收 → 模型身份证明 → C → EVAL → CLOSE；其余均 BLOCKED。
- R6 可信身份仍不足；PR #120 的 zero-Core-diff 检查 exit 128 仍待 disposition；规模与历史 Issue 状态只登记风险，不形成第二施工队列。
- 裁决：`governance/C15_RCC_RES_B_CORRECTIVE_DECISION_2026-09-23.md`。
- 审查：`reviews/C15_RCC_RES_B_001_PM_CORRECTIVE_REVIEW_2026-09-23.md`。
- PM 风险：`governance/C15_PM_RISK_REGISTER_2026-09-23.md`。
- 下一窗口分角色说明：`governance/prompts/`。Blind Resident 只接收被独立 release pin 的安全包，不接收这些 PM 提示词或审查结论。
- 治理 PR：[#122](https://github.com/Haneof/Haneof-AIOS-Core-v3.0/pull/122)，OPEN / 待独立集成。真实 merge SHA 与新 CI 由集成 PM 从 GitHub 记录；未合并前不得声称 main 已更新。本窗口没有执行 preflight 或实验。

## 历史工程断点 — C15 Resident A canonical PASS；唯一下一 READY = C15-RCC-RES-B-001

- 2026-09-23：`C15-RCC-RES-A-RERUN-001 = DONE / ACCEPTED`。
- Canonical frozen Core anchor：`bcd6bf353126318f9a97076b52ec1740d43f35a4`。
- Reviewed main before governance close：`6abfd4d19d03a60a81b7ca336efbe3c9c726b3bb`；该提交只是 anchor 的治理 handoff 子提交，`src/aios_core/**` diff 为 0。
- Canonical evidence：PR #117 @ `3e51f728d7959048b75fea01d405bc837b0e8185`，保持 **OPEN / UNMERGED / PINNED**。
- `30e0dca1f08c49ed9bacc66b49313ac536d512af` 已裁决为 metadata-only 错标：GitHub 不存在可解析 commit/ref；PR #117 的父基线为 `6abfd4d19d03a60a81b7ca336efbe3c9c726b3bb`，其 Core tree 与冻结 anchor 相同。仅修正 manifest/report/PR 描述并新增 anchor proof，World/cognition 等冻结字节未改。
- Execution PASS：cursor 1..13、13 条唯一 durable ack、`next_sequence=14`、无 pending reveal；final World/index = `88/88`。
- Freshness PASS：fresh World + session `resident-a-final-rerun-20260923-001`；未复用 PR #101 session、Claim IDs、transcript 或 World。
- Cognition / revision PASS：UU rev1→rev5、Relationship rev1→rev3、Strategy rev1→rev3、Communication Experience 与 Operation Experience 均有 pinned evidence；所有 revision 为 forward-only old→new 且生成新 EvidenceSet。
- UNKNOWN PASS：READY_FOR_UPLOAD/queued 未提升为 completed；checksum mismatch 被保持为 rejected；仅在 tag+digest+PUBLISHED 完成记录出现后确认 completed；DRAFT runbook 未提升为 reviewed/accepted/executed。
- Durable handoff：
  - World `sha256:9ff2b13cc1ec6e4d61a7910b4177ed3e1f25cfc47df8e18481a0199dd1aad395`
  - Index `sha256:55282a61d714f732f1b10fa6b450853f8425b5c9f741090fcaad0f1e673a6643`
  - release-state `sha256:b626cdd7d8ee16bcc9123ef8641bb05637d73d713023a471a74d7f6a392e052e`
- `C15-RCC-RES-B-001 = READY`；B 必须是新模型进程/会话，只恢复 durable AIOS lineage，不得读取或注入 A transcript/report/decision/checkpoint/out-of-band summary，合法范围仅 cursor 14..22。
- `C15-RCC-RES-C-001`、`C15-RCC-EVAL-001`、`C15-RCC-CLOSE-001` 继续 BLOCKED。
- Final decision：`governance/C15_FINAL_RELEASE_DECISION_2026-09-23.md`。
- **Next unique READY：`C15-RCC-RES-B-001`。**

## 历史工程断点 — C15 Resident A historical repair 已拒绝：该 rerun handoff 已完成

- 2026-09-22：`C15-RCC-RES-A-REPAIR-DECISION-001 = DONE`。
- Decision: **`PATH A = REJECTED` / `PATH B = REQUIRED`**。
- Reviewed main anchor: `4fbfe16ea0c500fcd30f049f0a4b6d662dbe624a`；fixed Core merge `fd9ba5de329abb025f52de76f1ab658cdafb4897`；exact Core implementation `41f2a5da2153c55b137741fdd71983eea2a011f7`。
- PR #101 @ `bfbfa059e2ac616326eecdfe3ffa7a927bdc7ce2` remains **OPEN / UNMERGED / PINNED / IMMUTABLE** and is now permanently classified **PRE-FIX DIAGNOSTIC / SUPERSEDED RESIDENT A RUN**. It is not a canonical RCC A World.
- Provenance verified:
  - cursor 9 executed on `wake_3df17e4ced76971ebbf90c05@2`, completed as `@3`;
  - cursor 11 executed on `wake_c9ebc3c1cf7b2a3f1b9b953a@2`, completed as `@3`.
- Fixed-Core deterministic delivery facts would be:
  - `obs_wake_ai_2f90e34a8f88bd517552bfcf@1` at `2026-11-04T22:17:00Z`;
  - `obs_wake_ai_dee8e0cd2712ed78f3bf05da@1` at `2026-11-04T23:02:00Z`.
- `sum0011` (`dim:user_ai_interaction`, day `2026-11-04`) was actually Resident-authored during Phase A. Original source set = **6**; corrected-world mechanical source set = **8**. Therefore the old summary semantic output is not historical-equivalent to the corrected execution.
- Cursor-13 Periodic Review also changes mechanically: original **9 Observation / 18 total anchors**; corrected history necessarily adds both delivery Observations, producing **11 Observation / 20 total anchors** under current review limits. The review Wake identity and Resident-visible review input therefore differ.
- Because actual Phase A model-visible inputs differ, post-hoc persistence cannot reconstruct the semantic execution that should have occurred. No historical backfill task is authorized.
- `C15-RCC-RES-A-001 = BLOCKED / SUPERSEDED`.
- `C15-RCC-RES-A-RERUN-001 = READY`: same frozen fixture, fixed Core, **fresh private World**, fresh session/window, sequential release, no old transcript/semantic decisions/Claims, no requirement to reproduce old cognition.
- `C15-RCC-RES-B-001 = BLOCKED`; `C15-RCC-RES-C-001 = BLOCKED`; `C15-RCC-EVAL-001 = BLOCKED`; `C15-RCC-CLOSE-001 = BLOCKED`.
- Decision report: `reviews/C15_RCC_RES_A_REPAIR_DECISION_2026-09-22.md`.
- **Next unique READY: `C15-RCC-RES-A-RERUN-001`.**

## 历史工程断点 — C15 Wake user-delivery Core fix 已完成：该 repair-decision READY handoff 已完成


- 2026-09-22：`C15-RCC-WAKE-DELIVERY-FIX-001 = DONE`；Core PR #104 已 merge 到 `main@fd9ba5de329abb025f52de76f1ab658cdafb4897`。
- Exact final Core candidate: `41f2a5da2153c55b137741fdd71983eea2a011f7`；最终 PR-head targeted/full Gates GREEN。
- Core 现在对真实允许并实际返回用户的 non-conversation Wake assistant response 使用统一 `dim:user_ai_interaction` durable assistant-only fact；保存 exact Wake provenance，并以稳定 identity / idempotent recovery 收敛到 exactly once。
- Wake delivery 不创建 synthetic/empty/system USER Observation；suppressed / delivery-denied / cognitive-derivation internal text / periodic-review internal text / silence 均不写 user-interaction output。
- Fresh Runtime + rebuilt index 可恢复 proactive assistant delivery；ordinary `run_turn()` USER + assistant canonical semantics 未改变。
- Completion evidence: `reviews/C15_RCC_WAKE_DELIVERY_FIX_001_COMPLETION_EVIDENCE_2026-09-22.md`。
- PR #101 @ `bfbfa059e2ac616326eecdfe3ffa7a927bdc7ce2` 仍为 **OPEN / UNMERGED / PINNED / PRE-FIX DIAGNOSTIC**；本 Core 修复没有修改、补录或重跑 Resident A evidence。
- `C15-RCC-RES-A-001 = BLOCKED`；`C15-RCC-RES-B-001 = BLOCKED`；`C15-RCC-RES-C-001 = BLOCKED`；`C15-RCC-EVAL-001 = BLOCKED`。
- `C15-RCC-RES-A-REPAIR-DECISION-001 = READY`。下一独立 PM 只能决定：若 immutable exact Wake artifacts 可证明 semantics-free / provenance-preserving / exactly-once historical persistence，则可选 Path A；否则选 Path B fresh World rerun。此 Core 窗口不作该判断。
- **Next unique READY: `C15-RCC-RES-A-REPAIR-DECISION-001`.**

## 历史工程断点 — C15 Wake user-delivery persistence 纠偏：该 Core-fix READY handoff 已完成


- 2026-09-22 corrective governance：PR #102 对 cursor 9 / 11 的 `non-conversation Wake delivery boundary` 解释不足；两次均为 `watch_match` / `interrupt`，`delivery_allowed=true`、Resident response 非空、`termination=responded`、`delivery_response` 非空、`delivery_suppressed=false`，但 PR #101 durable World 没有对应 assistant interaction Observation。
- Constitution: `docs/constitution/AIOS_v3.0_User_AI_Interaction_Dimension_Constitution.md` 要求用户-AI交流本身作为世界事实保存，并记录用户输入、AI输出、时间与对话关系。Wake 不应伪造 USER input，但真实 delivered assistant output 仍是 interaction World fact。
- Current-main mechanism verdict: **`WAKE USER-DELIVERED ASSISTANT OUTPUT PERSISTENCE = MECHANISM_GAP`**。普通 `run_turn()` 调用 `ConversationIngestor.commit_assistant_output(...)`；当前 `run_wake()` 只产生 `delivery_response`，没有 durable assistant-interaction commit。
- `C15-RCC-RES-A-001 = BLOCKED` — evidence run complete, acceptance deferred by Wake-delivery persistence gap。
- `C15-RCC-RES-B-001 = BLOCKED`；`C15-RCC-RES-C-001 = BLOCKED`；`C15-RCC-EVAL-001 = BLOCKED`；`C15-RCC-CLOSE-001 = BLOCKED`。
- PR #101 @ `bfbfa059e2ac616326eecdfe3ffa7a927bdc7ce2` 保持 **OPEN / UNMERGED / PINNED**，重新定义为 **PRE-FIX / DIAGNOSTIC RESIDENT A EVIDENCE**；禁止 post-hoc 修改其 private World。
- `C15-RCC-WAKE-DELIVERY-FIX-001 = READY`：唯一允许的下一工程任务是最小 Core 修复；真实 delivered Wake assistant output exactly-once 写入统一 interaction World，suppressed/denied/internal/silence 不写，且绝不伪造 USER Observation。
- `C15-RCC-RES-A-REPAIR-DECISION-001 = BLOCKED` on Core fix。修复完成后由新的独立 PM 决定 pure mechanical historical persistence 或 fresh World rerun；本纠偏窗口不决定 Path A/B。
- Corrective review: `reviews/C15_RCC_RES_A_WAKE_DELIVERY_CORRECTIVE_REVIEW_2026-09-22.md`。
- **Next unique READY: `C15-RCC-WAKE-DELIVERY-FIX-001`.**

## 历史工程断点 — C15-RCC-RES-A-001 曾由 PR #102 验收：该 B handoff 已被 Wake-delivery corrective governance supersede


- 2026-09-22 更新：`C15-RCC-RES-A-001 = DONE`；`C15-RCC-RES-B-001 = READY`；`C15-RCC-RES-C-001 = BLOCKED`；`C15-RCC-EVAL-001 = BLOCKED`；`C15-RCC-CLOSE-001 = BLOCKED`。
- Canonical Resident A evidence: PR #101 @ `bfbfa059e2ac616326eecdfe3ffa7a927bdc7ce2`，保持 **OPEN / UNMERGED / PINNED**；session `resident-a-c15-rcc-20260922`。
- Mechanical freeze: cursor `1..13` complete；cursor 14 not revealed；Phase B not initialized；World revision `90`；Index watermark `90`；lag `0`。
- Digests: World `ea9ea2384bc10e7fbe12c2015074f25193ada134530882cf5b3276d9201df15a`；Index `0d73069608a0293f938a8bb711096273cbad81dd9e6117118d9517e5791ffc80`；release-state `3ca82ff1454deaa9c703c7a0d8e2d7a01b581751bac52286ae390728651591b0`。
- Resident A Phase A frozen and accepted.
- Resident B must recover only durable AIOS state from PR #101 exact head.
- B legal recovery inputs are limited to accepted private World bytes, rebuildable index, runtime/checkpoint state, release state, mechanical digests, the B-safe run contract, and normal RuntimeSnapshot/capabilities. Do not provide A transcript, A run report, PM semantic summary, checkpoint prose dump, expected cognition, or evaluator notes.
- PM acceptance: `reviews/C15_RCC_RES_A_001_PM_ACCEPTANCE_REVIEW_2026-09-22.md`.
- **Next unique READY: `C15-RCC-RES-B-001`.**

## 历史工程断点 — C15-RCC-FIXTURE-001 已完成：sealed RCC life 已冻结，唯一下一 READY = C15-RCC-RES-A-001

- 2026-09-22 更新：`C15-RCC-FIXTURE-001 = DONE`；`C15-RCC-RES-A-001 = READY`；`C15-RCC-RES-B-001 = BLOCKED`；`C15-RCC-RES-C-001 = BLOCKED`；`C15-RCC-EVAL-001 = BLOCKED`。
- Starting main: `d65a7b24366cb612d042a3feedb92f0a3d90b02c`。
- Initial fixture branch: `test/c15-rcc-fixture-001-20260922-sol`。
- Initial PR: #99。
- Corrective mechanical branch: `test/c15-rcc-fixture-001-duplicate-reveal-fix-20260922-sol`。
- Corrective PR: #100。
- Fixture: `reviews/internal_habitation/c15-rcc/v1/fixture/sealed_fixture.json`。
- Fixture SHA256: `7ccb309d207cb6ee240fbc008ee4f535e25571f04ba7ca1b7c95bf9afb5ebf46`。
- Event count/time: 30 events；`2026-11-02T09:05:00-08:00` -> `2026-11-20T16:18:00-08:00`。
- Boundaries: A=1..13；B=14..22；C=23..30；每次 phase transition 必须以同一 durable World 的 exact ack boundary 为前提。
- Release infrastructure: thin three-phase binding over frozen C14 v2 exact SQLite ack / receipt-chain / canonical ConversationIngestor mechanics；未创建第二套语义 release engine；pending event 存在时 duplicate reveal 与 duplicate ack 均 fail closed。
- Resident access: A/B/C 各自只有独立 safe run contract；A 不得获知 B/C；B 不得获得 A transcript/prose handoff，也不得获知后续阶段；C 不得获得 A/B transcript/prose handoff。
- Cognition opportunities: scoped User Understanding；持续执行/核验但保留高影响授权的 Relationship/Role；queued/planned vs actually-complete 的真实 Self/Calibration mistake opportunity；低风险自主执行 + real Outcome + user feedback 的 Strategy/Experience opportunity。
- Controls: third-party outage external failure；lunch-choice irrelevant cognition；formal-launch changed-user/stage evidence；draft-only unsupported-self。
- Fresh-B material consumption: low-risk staging 与 production-delete shorthand 两类正常现实要求旧 durable cognition 真正影响 later behavior，而非仅被找到。
- Replacement-C: same durable World lineage；低风险 staging、scheduled-vs-observed migration、later changed-user evidence 与 draft-only self-proof control。
- P12 replacement-model identity attestation remains **UNRESOLVED / INSUFFICIENT_EVIDENCE at fixture time**. Phase C requires trusted external execution evidence outside Resident control; if unavailable or insufficient, **R6 cannot be VALID**. Fixture fields remain null and cannot manufacture proof.
- Initial pre-governance exact candidate: `74ff20d06b30847557c25c08e4deabd9d4578c84`。
- Corrective exact candidate: `629cf587f37f7cea25595e456d5e4de4c03fa7d5`。
- Gate runs `35701591095` and `35702939513`: SUCCESS；C15 mechanical 35/35 PASS；duplicate reveal/ack fail closed；mature C14 sealed gate 25/25 PASS；subject-isolation/fused runtime/canonical conversation regressions PASS；`src/aios_core/** = 0`。
- Completion evidence: `reviews/internal_habitation/c15-rcc/v1/C15_RCC_FIXTURE_001_COMPLETION_EVIDENCE_2026-09-22.md`。
- **Next unique READY: `C15-RCC-RES-A-001`（必须由新的真实 Resident 窗口执行）。本 fixture 窗口禁止运行 Resident A。**


## 历史工程断点 — C15-RCC-MECH-FIX-001 已完成：Subject/User isolation 已封闭，当时唯一下一 READY = C15-RCC-FIXTURE-001

- 2026-09-22 更新：`C15-RCC-MECH-FIX-001 = DONE`；`C15-RCC-FIXTURE-001 = READY`；`C15-RCC-RES-A-001 = BLOCKED`。
- Starting main: `a6e2adf5d5676f765e40150aa3e21d145d4aef30`。
- Engineering branch: `fix/c15-rcc-mech-fix-001-20260922-sol`。
- PR: #98。
- Exact gated implementation candidate: `de65572d2ce31cc53d5daadc252fe91e94e045d2`。
- Completion evidence: `reviews/C15_RCC_MECH_FIX_001_COMPLETION_EVIDENCE_2026-09-22.md`。
- Before-fix reproduction: test-only head `9cfe55d6ca920441b37799e51ed1330e8c26ca08` kept Core identical to starting main; `p10-ai-world` run `35698757405` failed 9/27 and `fused-turn-runtime` run `35698757513` failed 1/26, proving User A user-scoped AI-world cognition leaked through User B typed reads/runtime and typed mutation did not fail closed.
- Root cause: `AIWorldCognitionService.current()` did not enforce the domain-derived subject; `revise()/retract()` trusted `payload["subject_id"]` as revision authorization.
- Fix: `current()` now filters on `expected_subject = _subject_for(domain)`; `core_context()` / `snapshot()` continue to reuse `current()`; typed mutation validates `ai_world=True`, valid `AIWorldDomain`, and target subject equality with the domain-derived expected subject before constructing `CognitionRevisionService`.
- Ownership semantics unchanged: User Understanding / Relationship / Strategy remain current-user scoped; Self / Calibration / Intent / Cognitive Boundary / Personality remain `ai_agent_self` scoped. No global Strategy scope, inheritance policy, second DB, second Runtime or semantic inference was added.
- AI-self continuity non-regression: Self and Calibration remain readable across User A/User B service contexts and legitimate AI-self revision remains legal.
- Exact-candidate Gates: `p10-ai-world 35698883015 SUCCESS (31 passed)`; `fused-turn-runtime 35698882956 SUCCESS (26 passed)`; `p9-revision-gate 35698883322 SUCCESS (54 passed)`; `p10-ai-world-gate 35698883102 SUCCESS`; `p11-dimension-gate 35698882916 SUCCESS`; `p12-execution-gate 35698883026 SUCCESS`; `constitutional-cognition-closure 35698882994 SUCCESS`; `c14-cognitive-derivation-runtime 35698883045 SUCCESS`; `c14-cognitive-derivation-loop 35698882999 SUCCESS`。
- Full Core regression: `p16-convergence-gate 35698883072 SUCCESS`; exact run's `pytest -q` progress contained 431 tests and reached 100%。
- Ordinary `search_world`, timeline, recommendation and direct `inspect_world_object` paths were not refactored and remained GREEN through related C14/P16 regressions.
- P12 replacement-model identity attestation remains **INSUFFICIENT_EVIDENCE**. This task did not add model-name signatures, trust configured/declared model identity, modify provider harness to fabricate attestation, or create a model identity DB. R6 must remain non-VALID until the later execution/evidence environment provides trusted replacement-model identity evidence.
- Next unique READY: **`C15-RCC-FIXTURE-001`**（必须由新窗口执行）。本窗口禁止开始 fixture、Resident、semantic evaluation、replacement-model test、C16/P16。



## 历史工程断点 — C15-RCC-PREFLIGHT-001 已完成：P11 = MECHANISM_GAP，当时下一 READY = C15-RCC-MECH-FIX-001

- 2026-09-22 更新：`C15-RCC-PREFLIGHT-001 = DONE`；`C15-RCC-MECH-FIX-001 = READY`；`C15-RCC-FIXTURE-001 = BLOCKED`。
- Reviewed main: `fb7921df2231ac8fb6af85f29d6e9eff64272245`。
- Audit branch: `audit/c15-rcc-preflight-20260922-sol`。
- Audit PR: #97。
- Canonical preflight report: `reviews/C15_RCC_PREFLIGHT_001_MECHANISM_AUDIT_2026-09-22.md`。
- Core diff in preflight: `src/aios_core/** = 0`。
- P1–P13: P1/P2/P3/P4/P5/P6/P7/P8/P9/P10/P13 = **ALREADY_IMPLEMENTED**；P11 = **MECHANISM_GAP**；P12 = **INSUFFICIENT_EVIDENCE**。
- Subject-isolation verdict: ordinary `search_world`, timeline, recommendation and direct `inspect_world_object` already enforce runtime subject scope；但 `AIWorldCognitionService.current()/core_context()/snapshot()` 未按 AI-world domain 派生并过滤合法 subject，typed `revise/retract` 又从 target payload 自身采用 subject，因此 shared WorldStore 中 User A 的 user-scoped AI-world cognition 可能进入/被 User B typed facade 读取或修改。此为真实机械 fail-closed 缺口。
- Replacement-model identity attestation verdict: **INSUFFICIENT_EVIDENCE**。当前 provider harness 保存 configured/declared `provider/model`、config fingerprint 与 provider response/request id；`ModelCallProvenance.model` 仍来自配置值，并非独立不可篡改的平台/provider model binding。R6 在未来 Resident-C 执行时若无 trusted external attestation，必须保持未 VALID。
- Existing mechanisms accepted: unified World Claim/EvidenceSet/Dependency/Revision/Experience；User Understanding / Relationship / Self / Calibration / Strategy writeback；OperationExperience / CommunicationExperience real-case lineage；WorldSearchIndex；bounded relevant context；fresh Runtime SQLite reopen + index rebuild + ordinary retrieval；retain/revise/retract；C14 anti-self-proof mechanical closure；same Resident CognitiveRuntime / no second cognition DB。
- Fresh-runtime evidence reused: `test_loop_new_runtime_recovers_exact_durable_ai_world_cognition` 已执行过 SQLite reopen → Index rebuild → new FusedTurnRuntime/new session → `read_ai_world -> search_world -> inspect_world_object` exact durable Claim recovery。
- Core implementation decision: **YES, exactly one narrow fix task**。只允许修 `AIWorldCognitionService` domain-derived subject authorization，primary target `src/aios_core/ai_world/cognition.py`；不得新建 identity/personality DB、第二 Runtime、hidden handoff，且不得把 R6 identity attestation 伪装成 Core semantic logic。
- Next unique READY: **`C15-RCC-MECH-FIX-001`**。完成并 Gate 后才可释放 fixture；本 preflight 窗口禁止开始该实现。

## 历史工程断点 — C15-RCC-RULE-001 已冻结：NO CONSTITUTION CHANGE REQUIRED，唯一下一 READY = C15-RCC-PREFLIGHT-001

- 2026-09-22 更新：`C15-RCC-RULE-001 = DONE`（RCC 正式语义边界与验收定义已冻结）；**`NO CONSTITUTION CHANGE REQUIRED`**；`C15-RCC-PREFLIGHT-001 = READY`；`C15-RCC-FIXTURE-001` 保持 **BLOCKED**（禁止本窗口或下一窗口顺手做 fixture / Resident / evaluator）。
- Started / reviewed main: `623f8471cdd6ac2d756c15231f65f311e662f9d9`（C14-CLOSE-001 squash merge `#95`）。
- Authoritative ruling: `governance/C15_RESIDENT_COGNITIVE_CONTINUITY_RULING_2026-09-22.md`。
- Core diff: `src/aios_core/**` = 0 文件变更。
- Constitution / registry changes: **NONE**。现有 User Understanding / Relationship / Self / Calibration / Strategy / Periodic Review / Cognitive Runtime / AI Dimension / Cognitive Boundary / Adaptive Cognitive Policy 已足够支撑 RCC；本窗口只做法统解释，不重写主宪法。
- 根定义：`model can change; Resident cognition must not silently reset`。
- 同一个 Resident：同一条 durable cognition lineage 在新 Runtime / 新模型中可通过合法 AIOS 能力恢复、被实际消费、并继续被现实修正。不要求同措辞 / 同文风 / 同 reasoning path。
- 四类长期认知：User Understanding；Relationship / Role；Self / Calibration；Strategy / Experience。
- 三层分离：User World（发生了什么） / Resident Cognitive World（这些事实对我意味着什么） / Current Model Runtime（可替换执行引擎）。
- Replacement-model：允许能力、表达、检索顺序变化及有 Evidence 的纠错；禁止无 Evidence 地忘记已成立 cognition、把 UNKNOWN 当 FACT、或完全不检索已有 Calibration 防线。
- Continuity ≠ freezing：retain / strengthen / weaken / revise / retract / silence 必须有新现实 Evidence。
- Anti-self-proof：AI 自述不得终止证明；错误经验必须可长期检索；UNKNOWN 是合法 durable cognition。
- 禁止第二身份数据库、persona prompt 替代认知、hidden transcript/scratchpad/evaluator-notes handoff。
- Evaluator matrix R1–R9；C15 PASS 当且仅当全部 VALID。无法证明模型身份不同时 R6 不得 VALID，只能 PARTIAL（reason `INSUFFICIENT_EVIDENCE`）。
- 与 C14：C14 已 PASS 机制闭环；C15 不重证 C14，只把 cognition 内容提升到 Resident 身份/成长门。
- 与 C16 / P16：本窗口不启动系统反馈闭环、不启动年度入住。
- 下一步：**唯一 READY = `C15-RCC-PREFLIGHT-001`**（新独立窗口）。只审计 current main 机制是否 `ALREADY_IMPLEMENTED` / `MECHANISM_GAP` / `INSUFFICIENT_EVIDENCE`。禁止创建第二认知库；禁止本窗口未完成事项被下一窗口跳过。

## 历史工程断点 — C14-CLOSE-001 已收口：C14 CLOSURE = PASS，当时下一 READY = C15-RCC-RULE-001

- 2026-09-22 更新：`C14-CLOSE-001 = DONE`（独立总收口完成）；**`C14 CLOSURE = PASS`**；`C15-RCC-RULE-001 = READY`；`C15-RCC-PREFLIGHT-001` 保持 **BLOCKED**（直到 RCC-RULE 完成，禁止直接设 READY）。
- Reviewed main anchor: `f5866974726c6327ab5a33236eed8912178d0c33`；Core diff: `src/aios_core/**` = 0 文件变更。
- Deterministic Gates: 341/341 passed (100% GREEN)；包含 C14 scheduler、runtime、loop、writeback、revision、AI-world、Periodic Review、habitation harness 及 25 项 semantic-repair mechanical gate。
- 历史 Evidence PRs 状态再核查：全部保持 **OPEN / UNMERGED / PINNED**（严禁 merge）：
  - PR #75 @ `cb9b56b7039272d932158f33bfe979eff6749c9b` (Resident A)
  - PR #79 @ `546449a453e6e6dff3a2eeb2b52e7cf6786927be` (Resident B)
  - PR #92 @ `9e870514b57bf07c00018d7dcf7435f2702f8730` (Semantic Repair Resident)
- 最终组合语义证据矩阵：
  - E1 (Cross-dimensional cognition): **VALID** (PR #92 替换证据)
  - E2 (Matched-negative silence): **VALID** (PR #75 原始证据)
  - E3 (Fresh-window cognition recovery): **VALID** (PR #79 原始证据)
  - E4 (Cognition materially affects behavior): **VALID** (PR #79 原始证据)
  - E5 (Later outcome / revision): **VALID** (PR #92 替换证据)
  - E6 (Integrity / no pseudo-LLM / no future leak): **VALID** (无污染再核)
- 权威正式结论声明：
  «AIOS 已证明：durable User/World reality 可触发真实 Resident 高阶认知机会；Resident 能跨维检查真实证据形成或修正 cognition；该 cognition 能跨 fresh runtime/session 恢复并实际影响后续行为；后续真实世界证据能够修正或保留 cognition；整个过程不依赖 Summary 自证、pseudo-LLM、future leak 或 deterministic semantic inference。»
- 收口审计报告：`reviews/C14_CLOSE_001_FINAL_CLOSURE_REVIEW_2026-09-22.md`。
- 下一步：`C15-RCC-RULE-001`（新独立窗口），冻结 Resident Cognitive Continuity 语义。

## 历史工程断点 — C14-SEM-REPAIR-EVAL-001 已完成：C14 RESIDENT SEMANTIC EVIDENCE = VALID，唯一下一 READY = C14-CLOSE-001

- 2026-09-22 更新：`C14-SEM-REPAIR-EVAL-001 = DONE`（独立语义评估完成）；`C14-CLOSE-001 = READY`；`C15-RCC-RULE-001` 保持 **BLOCKED**（直到 C14-CLOSE 真正完成）。
- Evaluated live main: `655e1d48c2b53dd4f5a10485a9d530ed13ca69a3`；run's declared evaluated main: `7611fa5059f5dc8a20835cab5b312be2f43d11e8`。
- Canonical evidence: **PR #92 @ exact head `9e870514b57bf07c00018d7dcf7435f2702f8730` ONLY（保持 OPEN / UNMERGED / PINNED，永远禁止 merge）**；试运行 PR #84–#91 未被使用。
- 独立重算并匹配：World SHA256 `a7a7cd9f9166eb41d3b93d85820a9c7a4ab0aa57b81787d89f395482742bae57`；release-state SHA256 `4f41d709a76e0f40ce5b0093f540cc286dde84a1906a575019199cc7a7970081`；index SHA256 `ae296ee44a000eb7ea5bf122184bfb9dd65c80f14f9e94e9fb64fce039658caf`；fixture SHA256 `1095d5aef52061753db7d9dab558af1361b92976f2ded0e6956d70afe3e6527f`（与 main 逐字节一致）。
- **E1 = VALID**：`clm_b4df2179bb8ffec020a39ede` rev1@wr20 → rev2@wr44 → rev3@wr77；EvidenceSet 3/6/12 个 pinned 非 Summary 叶子逐一闭合每条 material fact；hypothesis 纪律保持；confidence 0.65→0.70→0.78 均由新增真实叶子支撑。
- **E5 = VALID**：cp0007–cp0009（仅计划窗口）未把 11-10 会议写成已发生；rev3 仅在 cursor 10/11/12 真实证据到达后以 Plan/Observed/Outcome 显式分层升级；external-failure（cursor 13–15）期间无 self-blame、无无关 Claim 修改、wr78 后零语义写入。
- Repair contamination 审计：无 pseudo-LLM / keyword→Claim / oracle / future leak；`src/aios_core/**` diff = 0；`reviews/internal_habitation/c14-resident/v2/**` diff = 0；PR #75（`cb9b56b7…`）/ PR #79（`546449a4…`）head 未动；fixture/evaluator/release 目录与 main 逐字节一致。
- Combined matrix：E1 VALID / E2 VALID / E3 VALID / E4 VALID / E5 VALID / E6 VALID → **`C14 RESIDENT SEMANTIC EVIDENCE = VALID`**。
- Evaluator report: `reviews/C14_SEM_REPAIR_EVAL_001_INDEPENDENT_SEMANTIC_EVALUATION_2026-09-22.md`（含 limitations：provenance 无法密码学证明、run-end 两个 pending trigger（wr81/wr83）未派发、若干非阻断措辞观察）。
- 本窗口未修改 Core、fixture、Claim、EvidenceSet、World、Resident run；未创建“正确答案”。
- 下一步：`C14-CLOSE-001`（新独立窗口）只做收口审计，不得写新 Core 功能；收口必须保留 PR #75/#79/#92 OPEN/UNMERGED/PINNED。

## 历史工程断点 — C14-SEM-REPAIR-RES-001 证据已由 PM 正式接受，唯一下一 READY = C14-SEM-REPAIR-EVAL-001

- 2026-09-22 更新：`C14-SEM-REPAIR-RES-001 = DONE`（PM evidence acceptance 完成）；`C14-SEM-REPAIR-EVAL-001 = READY`。
- Starting / evaluated main: `7611fa5059f5dc8a20835cab5b312be2f43d11e8`
- **Canonical evidence PR: #92（OPEN / UNMERGED / PINNED — 禁止 merge；private World 不得进入 main）**
- **Exact canonical evidence head: `9e870514b57bf07c00018d7dcf7435f2702f8730`（evaluator 只能使用该 head）**
- Resident branch: `arena/01a0c773-haneof-aios-core-v3-0`
- Resident session: `resident-sem-repair-20260922`; Run ID: `resident-repair-20260922`
- Run directory: `reviews/internal_habitation/c14-resident/semantic-repair-v1/runs/resident-repair-20260922/`
- Cursors: 15/15 顺序释放（Phase A = 1..6, Phase B = 7..15），全部 durable SQLite ack，PM 独立重验。
- Semantic checkpoints: 16；Resident-authored summaries: 20；capability calls: 18（15 inspect_world_object / 1 commit_claim / 2 revise_claim）；silence 8；response 1。
- Final current Claim: `clm_b4df2179bb8ffec020a39ede@3`（active, confidence 0.78；durable revision chain rev1@wr20 → rev2@wr44 → rev3@wr77，support evidence sets 逐级解析到 pinned leaf Observations）。
- Final World revision: 83；Final World SHA256: `a7a7cd9f9166eb41d3b93d85820a9c7a4ab0aa57b81787d89f395482742bae57`
- Release-state SHA256: `4f41d709a76e0f40ce5b0093f540cc286dde84a1906a575019199cc7a7970081`; Index SHA256: `ae296ee44a000eb7ea5bf122184bfb9dd65c80f14f9e94e9fb64fce039658caf`
- PM audit 结论（仅完整性/出处）：bridge transport-only、无 pseudo-LLM / keyword→Claim / 预设答案；16 snapshots + 20 summary requests 零 future leak；`src/aios_core/** = 0`；`reviews/internal_habitation/c14-resident/v2/** = 0`，PR #75（`cb9b56b7…`）/ PR #79（`546449a4…`）历史证据未动。
- 试运行 PR disposition：#84/#85 ABORTED·NON-CANONICAL（已关闭）；#86/#87/#91 SCAFFOLD ONLY（已关闭；#91 提交是 canonical head 的祖先）；#88 NON-CANONICAL 并行 r8 run——DO NOT EVALUATE（已关闭）；#89/#90 ABORTED（保持关闭）。
- PM acceptance report: `reviews/C14_SEM_REPAIR_RES_001_PM_ACCEPTANCE_REVIEW_2026-09-22.md`
- **E1/E5 语义裁决 = NOT PERFORMED**，只能由新独立 evaluator 窗口在 `C14-SEM-REPAIR-EVAL-001` 执行；只审计 PR #92 @ `9e870514…`，禁止使用 #84–#91。
- `C14-CLOSE-001` 保持 **BLOCKED**；`C15-RCC-RULE-001` 保持 **BLOCKED**。
- Evidence branch 末提交（`9e87051`）内含 Resident 窗口自记的 task board/checkpoint 文本，已被本 PM 写回取代；不影响任何 run artifact。


## 历史工程断点 — C14-SEM-REPAIR-FIX-001 已完成并合入 main

- Task: `C14-SEM-REPAIR-FIX-001 = DONE`
- Evaluated / starting main: `1c20e548822b7aa6b5cb980995ff5de7902e3ac9`
- Branch: `c14/semantic-repair-fixture-20260922-sol`
- Mechanical fixture candidate: `077348619a6e827a34f464fccc4c189edd7d1f1c`
- Final PR candidate: `11ee54c0ecaca3462fd526f27c2a5b526a6e8295`
- PR: #83
- Merge SHA: `aacf70e381a78b5955304e894ebce445ce3ffe49`
- Fixture: `reviews/internal_habitation/c14-resident/semantic-repair-v1/fixture/sealed_fixture.json`
- Fixture SHA256: `1095d5aef52061753db7d9dab558af1361b92976f2ded0e6956d70afe3e6527f`
- Event count: 15
- Time range: `2026-11-03T07:06:00-08:00` -> `2026-11-13T11:23:00-08:00`
- Phase boundary: R-A cursors 1..6; R-B cursors 7..15; ack 6 -> next 7; Phase A cannot reveal cursor 7.
- E1 opportunity: sleep + actual device/collaboration activity + work outcome are separately durable; no single dimension is sufficient; every concrete material fact is available as an exact leaf; silence remains legal.
- E5 opportunity: cursor 8 is PLANNED only; cursor 10 is the first proof the meeting OBSERVED/OCCURRED; cursor 11 is a real work Outcome; cursor 12 is separate canonical USER feedback.
- External-failure control: cursors 13..15 record a third-party document-service outage before a late work Outcome, preventing automatic self-blame from being treated as valid evidence.
- Mechanical Gate: pre-governance run `35678533993` = **SUCCESS**; final exact-candidate run `35678649521` = **SUCCESS**; workflow `c14-semantic-repair-fixture`; Python 3.12.14; dedicated gate **25/25 PASS**; existing canonical conversation + fused-runtime regressions **16/16 PASS**; exact fixture SHA proof PASS.
- Release semantics: thin bindings reuse frozen C14 v2/v4 release operator, durable World ack and canonical ConversationIngestor; no second semantic release engine.
- Core diff: `src/aios_core/** = 0`.
- Historical evidence diff: `reviews/internal_habitation/c14-resident/v2/** = 0`; PR #75/#79 evidence was not edited.
- Resident semantic execution: 0.
- Completion evidence: `reviews/internal_habitation/c14-resident/semantic-repair-v1/C14_SEM_REPAIR_FIX_001_COMPLETION_EVIDENCE_2026-09-22.md`
- Current next READY: `C14-SEM-REPAIR-RES-001`.
- This window stops after fixture/governance closure and does not run the Resident repair.

## 历史工程断点 — Resident Cognitive Continuity 路线已冻结，先执行 C14 最小语义修复

- Governance planning baseline: `main@426f049d890d82121388ed5d52eecf66e48856f8`.
- Canonical C15 plan: `governance/C15_RESIDENT_COGNITIVE_CONTINUITY_TEST_PLAN_2026-09-22.md`.
- C15 root gate renamed/reframed as **Resident Cognitive Continuity (RCC)**: bottom model may change; durable User Understanding / Relationship-Role / Self-Calibration / Strategy-Experience must not silently reset.
- Existing P15/C14 mechanisms remain authoritative. C15 begins with `C15-RCC-PREFLIGHT-001`; it must mark existing capabilities `ALREADY_IMPLEMENTED` instead of rebuilding them.
- Replacement-model continuity is now mandatory for full C15 VALID. Same wording/style is not required; durable cognition recovery and material behavioral continuity are.
- Historical C14 evaluator remains authoritative: E1 PARTIAL / E2 VALID / E3 VALID / E4 VALID / E5 INVALID / E6 VALID.
- C14 historical PR #75 / PR #79 evidence remains frozen and must not be edited to make the test pass.
- A minimal repair chain is inserted:
  - `C14-SEM-REPAIR-FIX-001 = READY`
  - `C14-SEM-REPAIR-RES-001 = BLOCKED`
  - `C14-SEM-REPAIR-EVAL-001 = BLOCKED`
  - `C14-CLOSE-001 = BLOCKED`
- Repair scope is only the two failed semantic axes: exact leaf support for every material Claim fact, and strict planned / observed / Outcome separation during later revision.
- C15, C16 and broad P16 remain blocked until their declared dependencies close.
- **Current first READY task after this governance merge: `C14-SEM-REPAIR-FIX-001`.**

## 历史工程断点 — C14-RES-EVAL-001 已完成

- `C14-RES-EVAL-001 = DONE`
- Evaluated main: `8e6f9febc5f006605116c526796fa21435b4b22e`
- A evidence: PR #75 @ `cb9b56b7039272d932158f33bfe979eff6749c9b`
- B evidence: PR #79 @ `546449a453e6e6dff3a2eeb2b52e7cf6786927be`
- Report: `reviews/C14_RES_EVAL_001_INDEPENDENT_SEMANTIC_EVALUATION_2026-09-22.md`
- Matrix: E1 **PARTIAL** / E2 **VALID** / E3 **VALID** / E4 **VALID** / E5 **INVALID** / E6 **VALID**.
- Overall: `C14 RESIDENT SEMANTIC EVIDENCE = NOT VALID`.
- Blocking findings: Phase-A Claim rev2 contains a material sleep fact not pinned by its EvidenceSet; Phase-B rev4 treats the Resident's earlier 09:00 designer plan as observed reality although the pinned later Observations do not prove that treatment and cursor30 records drafting already began at 08:05.
- `C14-CLOSE-001` remains **BLOCKED**. C15 remains **BLOCKED**.
- Next action: PM must choose fail-closure recording or a dedicated Resident/evidence-semantic repair task. This evaluator did not repair Core or evidence.



## 历史工程断点 — C14-RES-B-001 已完成，等待独立语义评估

最近完成任务：`C14-RES-B-001` — **DONE / RUN COMPLETE / EVIDENCE ACCEPTED FOR EVALUATION**。

- Evaluated main：`9578d990fc47943b69c77b12d126255f6691a6dc`
- Evidence PR：#79（**保持 open / unmerged**）
- Exact evidence head：`546449a453e6e6dff3a2eeb2b52e7cf6786927be`
- Resident-B branch：`arena/01a0c517-haneof-aios-core-v3-0`
- PM review：`reviews/C14_RES_B_001_PM_ACCEPTANCE_REVIEW_2026-09-21.md`
- Phase B：cursor 25..36 完成；9 mechanical + 3 canonical USER conversation。
- Fresh runtime 首个认知 wake 通过正常 `search_timeline(object_types=["claim"])` 找回 A 的 `clm_79df...@2`，随后 inspect。
- Cursor 26 正常 Runtime 自动将其 rev3 作为 score-10 memory card 带入；Resident 创建的新 Task 的 `reason_refs` 明确包含 Claim rev3。
- Cursor 31 后续真实 work_outcome 推动该 Claim rev3→rev4；cursor 32 支持性用户反馈保持 rev4。
- Final World SHA256：`a288fc5d11a1a73006725efdd906a7ab014d4228085c610b4a32f887cfe3d615`
- Final release-state SHA256：`9281ced5013b45445574698d53ff9a2d57d5308ac5d1221e5db178efcf0c8a4f`
- PR #79 全部 280 个变更文件只位于 Resident-B evidence run 目录；Core/governance diff 0。
- `cursor_037/event.json` 为空；未见 future payload 泄露。
- Bridge 为同步机械桥；未见关键词规则/预期答案/Claim 自动决策/pseudo-LLM。
- Provenance caveats：底层模型身份未暴露；Resident 环境 Python 3.11.2；仓库证据只能支持“未发现污染证据”，不能数学证明模型绝未读取外部材料。
- 本 PM 仅接受 B run 完整性与可审计性；**不裁决 C14 semantic PASS**。

当前第一个 READY：`C14-RES-EVAL-001`。必须由新的独立 evaluator 窗口执行，不修 Core。

## 历史工程断点 — C14-RES-B-FIX-001 已收口

最近完成任务：`C14-RES-B-FIX-001` — **DONE / CANONICAL PHASE-B CONVERSATION RELEASE VERIFIED**。

- Started main：`08ceb9ab3f68d5d3ececaaa26832912323d73851`
- Work branch：`c14/res-b-canonical-conversation-ingest-20260921-sol`
- Exact candidate：`cb3a417f3c29b29d6aa2bf364386aec12b17e623`
- PR：#78
- Squash merge：`1c7a8c1466911f8617ed39348a50ac8041f23715`
- Completion evidence：`reviews/internal_habitation/c14-resident/v2/C14_RES_B_FIX_001_COMPLETION_EVIDENCE_2026-09-21.md`
- Formal Python：`3.12.14`
- Exact-candidate workflow：`35631789929` — **SUCCESS**
- Pre-evidence GREEN：`35631613259` — **SUCCESS**
- Generic blind-release regressions：**30/30 PASS**
- Canonical conversation release/idempotency regressions：**15/15 PASS**
- Existing conversation + fused-runtime regressions：**16/16 PASS**
- Canonical adapter：`reviews/internal_habitation/c14-resident/v2/release/canonical_conversation_ingest.py`
- Release operator：`c14-blind-release-operator-v4`
- Phase-B USER conversation 不再允许 generic fixture Observation；generic adapter 对该 envelope fail closed。
- Specialized ack 必须机械验证 exact canonical user Observation：exact revision / subject / durable USER authority / Observation / `user_ai_interaction` / text / role=user / exact session / exact turn / exact text / exact occurred_at。
- Exact idempotency proof：先由 `ConversationIngestor.commit_user_input()` 写入 canonical user Observation，再由 fresh `FusedTurnRuntime.run_turn()` 以完全相同 subject/session/turn/text/time 调用；内部 user commit 返回 `idempotent_replay=True`，World 中该 turn 仍只有 1 条 canonical user Observation，assistant 形成独立正常 Observation。
- Fail-closed：generic fixture masquerade / missing canonical fields / wrong session / turn / text / timestamp / subject / assistant role / AI_COGNITION authority / other conversation event / nonexistent ref or revision / repeat / skip / reorder / boundary 均拒绝。
- Resident-A v3 state 只允许在 exact A 24→25 handoff 的 `init --phase B` test-copy 升级到 v4；PR #75 冻结 evidence/World/state 未修改。
- Frozen fixture SHA256 before/after：`1fb973499664d0d71d94a7b94071e3d7210395ea6a54ec4dcbb1ba115d069253` / unchanged。
- Core diff：`src/aios_core/** = 0`。
- Resident-A evidence diff：0。
- Resident-B semantic execution：**0**。
- 当前第一个 READY：`C14-RES-B-001`，必须在新的真实 Resident 模型窗口执行。
- Resident B release 规则：non-conversation 继续 `reveal -> mechanical_ingest_adapter -> ack`；USER conversation 必须 `reveal -> canonical_conversation_ingest -> canonical ack -> run_turn(same subject/session/turn/text/time)`。不得先 generic ingest 再 run_turn。

以下 C14-RES-FIX-003 及更早段落为历史快照；下一任务只以 Task Board 和本段为准。

## 历史工程断点 — C14-RES-FIX-003 已收口

最近完成任务：`C14-RES-FIX-003` — **DONE / DURABLE WORLD ACK VERIFIED**。

- Started from main：`0ec8d8bc16c2b0e572a9ae1de5cdc89c0416ea70`
- Work branch：`c14/res-fixture-v3-durable-ack-20260921-sol`
- Exact candidate：`17bd54ed0b64131ded0b70d853cac205d055bdcb`
- PR：#72
- Squash merge：`e5c7fefce82a49735575c423da310ca3d9441ab4`
- Completion evidence：`reviews/internal_habitation/c14-resident/v2/C14_RES_FIX_003_COMPLETION_EVIDENCE_2026-09-21.md`
- Formal fixture v2：`reviews/internal_habitation/c14-resident/v2/fixture/sealed_fixture.json`
- Frozen fixture SHA256 before/after：`1fb973499664d0d71d94a7b94071e3d7210395ea6a54ec4dcbb1ba115d069253` / **unchanged**
- Frozen fixture Git blob before/candidate：`7bd1935c9855ee5a71cd74b45bc693e01d21ca1b` / identical.
- Release operator：`c14-blind-release-operator-v3` at `reviews/internal_habitation/c14-resident/v2/release/release_operator.py`
- Mechanical ingest adapter：`c14-mechanical-ingest-adapter-v1` at `reviews/internal_habitation/c14-resident/v2/release/mechanical_ingest_adapter.py`
- Durable World verification：ack 强制 `--world-db`；通过正式 `SQLiteWorldStore.object_revision_record(object_id, revision=N)` + `get_payload(object_id, revision=N)` 回读 exact durable revision；commit `source_class` 从现有 `world_commits` provenance 读取，不信任调用方字符串。
- Exact binding：subject / Observation type / exact object revision / event id / sequence / occurred_at / dimension / source_kind / durable source_class / modality / payload / fixture version+digest+binding version / payload SHA256 / projection SHA256。
- Receipt chain：已有 receipt 会在每次 ack 前从同一个 supplied private World 重新验证；换错 World 且缺少历史 exact revisions 会 fail closed。
- Receipt：保存 exact ingest object id / revision / world revision / durable source class / payload+projection digest，可供后续 Evaluator 逐条回放。
- Exact-candidate Gate：GitHub Actions run `35598216907` — **SUCCESS**；30/30 real SQLiteWorldStore tests PASS；frozen fixture SHA proof PASS；no-Core-diff PASS。
- Pre-candidate GREEN：run `35598032585` — **SUCCESS**；同样 30/30 PASS。
- Candidate iteration failures 保留为证据：`35597626462` 是 test-copy path bootstrap 问题；`35597785208` 已到 durable logic 27/29，通过后仅两条测试误绑错误文案，均在最终 candidate 前修正。
- Core diff：`src/aios_core/** = 0`。
- Resident runs：**0**；未运行 pseudo-LLM / semantic oracle / Claim/revise/retract。
- 当前第一个 READY：`C14-RES-A-001`，必须由新的真实 Resident 模型窗口执行。
- Resident A 正式流程只认 fixture v2：不得打开 sealed fixture / manifest / evaluator notes；只能逐条 `reveal -> mechanical_ingest_adapter --world-db -> ack --world-db exact-ref`；cursor 1..24；ack 24 后永久停止，绝对不得 reveal 25。

以下 `C14-RES-FIX-002` 及更早段落均为历史快照；下一任务只以 Task Board 和本段为准。

## 历史工程断点 — C14-RES-FIX-002 已收口

最近完成任务：`C14-RES-FIX-002` — **DONE / RESIDENT FIXTURE V2 HARDENED**。

- Started from main：`075685b5b9b632988baa4e2de61c6d05aa469d32`
- Work branch：`c14/res-fixture-v2-hardening-20260921-sol`
- Exact candidate：`aacee04cfa5390f2a63d0a5606acb909291849b6`
- PR：#70
- Squash merge：`510290d3b9578cd9425079a22050eb679ddb528a`
- Completion evidence：`reviews/internal_habitation/c14-resident/v2/C14_RES_FIX_002_COMPLETION_EVIDENCE_2026-09-21.md`
- Formal fixture v2：`reviews/internal_habitation/c14-resident/v2/fixture/sealed_fixture.json`
- Manifest v2：`reviews/internal_habitation/c14-resident/v2/fixture/fixture_manifest.json`
- Release contract v2：`reviews/internal_habitation/c14-resident/v2/release/release_contract.md`
- Blind release operator：`reviews/internal_habitation/c14-resident/v2/release/release_operator.py`
- Evaluator-only notes：`reviews/internal_habitation/c14-resident/v2/evaluator/EVALUATOR_ONLY_design_notes.md`
- Fixture v2 SHA256：`1fb973499664d0d71d94a7b94071e3d7210395ea6a54ec4dcbb1ba115d069253`
- 时间轴：`2026-10-01T07:12:00-07:00` → `2026-10-31T12:03:00-07:00`，timezone `America/Los_Angeles`。
- 事件数：36；Phase A = 24；Phase B = 12；handoff = ack cursor 24 后 next=25，Resident A 必须停止。
- v1：完整保留为历史审查证据；**不得**再作为正式 C14 Resident 输入。
- Single-dimension leakage audit：**PASS**。Phase-A positive design 中 schedule / sleep / work_outcome / device_activity / conversation 任一单维都不足以独立建立高阶 longitudinal cognition；conversation 只保留局部当日事实。
- Phase-B underdetermination audit：**PASS**。09:00 提前澄清与 11:00 保护初始连续工作均由当前事实支持；deadline arithmetic 不会机械排除任一方案；fixture 不规定正确选项。
- Blind release：可执行 `init / reveal / ack`；reveal 只输出当前 event projection 且不推进；durable ingest ref + exact ack 后才推进；A 禁止 cursor 25；B 只能从 exact 24→25 handoff 启动。
- Exact-byte mechanical audit：**19/19 PASS**，包含 digest/version/skip/repeat/wrong-event/no-ingest-ref fail-closed、24/25 boundary、stdout future isolation。
- GitHub Actions：已提交可复现 v2 mechanical workflow；本窗口 GitHub workflow/status API 未产生 app-authored PR head 的 run record，因此没有伪报 CI GREEN。
- Core diff：`src/aios_core/** = 0`；fixture-v1 mutations = 0。
- 本窗口没有运行 Resident、pseudo-LLM、semantic oracle，也没有启动 `C14-RES-A-001` / B / EVAL / P16。
- 当前第一个 READY：`C14-RES-A-001`。必须在**新的真实 Resident 模型窗口**执行。
- Resident A 正式输入只认 v2：不得直接打开 sealed fixture / manifest / evaluator notes；只能调用 v2 `release_operator.py` 逐条获得 cursor 1..24；每条 event durable ingest 后才 ack；ack 24 后永久停止，绝对不得 reveal 25。

以下 `C14-RES-FIX-001` / v1 及更早段落均为历史快照；下一任务只以 task board 和本段为准。

## 历史工程断点 — C14-RES-FIX-001 已收口

最近完成任务：`C14-RES-FIX-001` — **DONE / SEALED RESIDENT FIXTURE READY**。

- Started from main：`01ad300bfd8a102e8b2fd5fc9bfbfb6fd5e4ff29`
- Work branch：`c14/res-fixture-20260921-sol`
- Candidate：`e174a016c25d34c05ef096129d1c537ca5b19de8`
- PR：#68
- Squash merge：`796d9c357bb08f3042f103bc66260fdb3cdcd88c`
- Completion evidence：`reviews/internal_habitation/c14-resident/C14_RES_FIX_001_COMPLETION_EVIDENCE_2026-09-21.md`
- Fixture：`reviews/internal_habitation/c14-resident/fixture/sealed_fixture.json`
- Manifest：`reviews/internal_habitation/c14-resident/fixture/fixture_manifest.json`
- Release contract：`reviews/internal_habitation/c14-resident/release/release_contract.md`
- Evaluator-only notes：`reviews/internal_habitation/c14-resident/evaluator/EVALUATOR_ONLY_design_notes.md`
- Fixture SHA256：`a0f9dfd0985560ce80f568b6cd11d46b13f5dc352a664c005fcb165ea5a67485`
- 时间轴：`2026-10-01T07:15:00-07:00` → `2026-10-29T18:40:00-07:00`，timezone `America/Los_Angeles`。
- 事件数：36；Phase A = 24；Phase B = 12；handoff = cursor 24 完成后停止，cursor 25 保持未释放。
- 机械 Gate：parse / unique ids / 1..36 连续序列 / 严格单调时间 / 唯一 A-B boundary / manifest digest / 逐 cursor release simulation / Resident-visible leak scan 全部 PASS。
- Core diff：`src/aios_core/** = 0`。
- 本窗口未运行任何 Resident 语义，未开始 `C14-RES-A-001`、`C14-RES-B-001`、`C14-RES-EVAL-001` 或 P16。
- 当前第一个 READY：`C14-RES-A-001`。必须由**新的真实 Resident 模型窗口**执行；只能按 release contract 逐事件获得 cursor 1..24，禁止读取 sealed fixture / manifest / evaluator notes / 未来事件；到 cursor 24 后必须永久停止，不得释放 cursor 25。

以下 `C14-LOOP-001` 及更早段落均为历史完成快照；下一任务只以 task board 和本段为准。

## 历史工程断点 — C14-LOOP-001 已收口

最近完成任务：`C14-LOOP-001` — **DONE / CONTINUOUS COGNITIVE DERIVATION LOOP HARDENED**。

- Started from main：`c4689fd595fc9308e71332e0c0dda17e49cffb95`
- Work branch：`c14/loop-hardening-20260921-sol`
- Exact candidate：`f48c3c9cfa8a24fa2e0e0220d7fe20bcda1be34d`
- PR：#65
- Squash merge：`a385f7b3fcc71982aae0611a382502c9a37ba71e`
- Completion evidence：`reviews/C14_LOOP_001_COMPLETION_EVIDENCE_2026-09-21.md`
- Task-board closure commit：`cf6b059ceaa5eaf7403ee2f742ba17d17804d139`
- Exact-candidate Gates：14/14 workflows SUCCESS，包括 C14 loop/runtime/scheduler、P16 full convergence、constitutional cognition closure、P15、P14、P12、C09、Fused、Dimension Summary、P11/P10/P9。
- Burst：10+ sibling C14 opportunities 复用现有 AttentionBundle，按 homogeneous execution contract 合并；Bundle 本体仍是 routing object，但 Runtime 验证 pinned members 后恢复 effective `COGNITIVE_DERIVATION`。
- Authorization：C14 Bundle 继续只允许 `commit_claim / commit_ai_world_claim / revise_claim / retract_claim` 四类 cognition writes；其他 side effects default-deny；read/search/inspect 保留；后台结果不直接投放用户。
- Exhaustion：model/tool/capability budget exhaustion 不再误标 semantic completion，而是 durable `QUEUED + runtime_incomplete`，SQLite restart 可恢复。
- Partial write：已成功写入的 Claim 在 exhaustion/restart 后保持 durable/idempotent；runtime-incomplete individual Wake 不再重新组成新 Bundle，从而不改变 semantic execution identity。
- Budget truth：QUEUED unfinished spend 对其他 background Wake 可见；最终完成后的 retry chain 继续以 C13 Metering Ledger 所有 provider response 为模型调用真值。
- Self-excitation：即时 C14 scheduling 除 REALITY/MIXED 外，还要求至少一条不经旧 AI semantic assertion 阻断的 `grounding_leaf_ref`；old AI Claim -> AI Summary 不再自动再造 C14 Wake；新 direct reality + old cognition 的 mixed case 仍合法。
- Review：Periodic Review 与 C14 各自保持独立生命周期/权限。
- New Runtime：新 SQLite reopen + 新 Index + 新 `FusedTurnRuntime` + 新 session，在不注入旧对话的情况下，通过 `read_ai_world -> search_world -> inspect_world_object` 找回 exact durable cognition revision。
- Reconcile：support Dependency graph 改为每次 reconciliation pass 构建一次；200 Summary scale 回归不再出现 Summary×Dependency 重复全图扫描。
- Merge-tree：candidate 与 squash merge 的 8 个变更文件 blob 全部一致。
- 本窗口明确未开始：`C14-RES-001`、`C14-CLOSE-001`、`P16-TRIAGE-001`、Resident habitation。
- 当前第一个 READY：`C14-RES-001`。必须由新窗口作为真实 Resident 模型执行，不得用 pseudo-LLM / Python 关键词答案 / 预计算 oracle 代替模型本人逐次语义判断。

以下内容均为历史完成快照；下一任务只以 task board 和本段为准。

历史 T35 功能合并锚点：`141dc177be895f9894a05227cbb132207ebf784d`。  
T35 task-board 收口提交：`4f8d291b00f885542793a0c7f6139da5420ef78b`。

历史完成任务快照：`T35-IMPL-001` — **DONE / NON-ACTION TASK COMPLETION EVIDENCE CLOSED**。

- Started from main：`eeb982162e0e553a34039134bde3595abd2f3607`
- Work branch：`task/t35-impl-001-completion-evidence-20260921`
- Candidate：`07617df8ab87550289c1498cf3df387626d55e40`
- PR：#55
- Squash merge：`141dc177be895f9894a05227cbb132207ebf784d`
- 实现依据：`governance/T35_NON_ACTION_TASK_COMPLETION_EVIDENCE_RULING_2026-09-21.md`
- Completion contract：复用现有 `Task.completion_condition`，显式支持 `world_evidence / action_outcome / mixed`；不新增第二套 Task/Outcome，不从自然语言标题/原因推断执行类型。
- Legacy fail-closed：模糊旧 Task 继续按 `ACTION_OUTCOME`；仅 legacy `VERIFICATION / OBSERVATION` 在无 Action lineage 时采用窄机械 `WORLD_EVIDENCE` 兼容。
- WORLD_EVIDENCE：终态必须由 pinned、current、same-subject、durable evidence 支撑；assistant raw dialogue、Task/Goal 自引用、unsupported Claim、stale/retracted evidence、synthetic Outcome、OperationExperience 原始闭环均不能充当完成真值。
- ACTION_OUTCOME：外部执行仍保持 `Task -> Action -> authorization -> execution -> Outcome -> Task`；Outcome 必须来自真实 platform-result 路径，绑定该 Task 的已授权终态 Action 与 durable `outcome_reports_action` 依赖。
- MIXED：World evidence 与 Action-linked Outcome 两侧都必须满足。
- COMPLETED / FAILED：共享同一真实 evidence 边界；无证据、timeout、模型自述不能把 Task 随意推成 FAILED。
- Terminal provenance：Task 新 revision 记录 completion mode、精确 evidence/execution/outcome refs，并生成 typed Dependency edges；历史 revision 不改写。
- Retry/restart：相同 terminal request 在 Task revision 已前进后可幂等返回，不增加 `world_revision`；SQLite restart 后同样成立。
- Resident runtime：`create_task` capability 已暴露结构化 `completion_condition`；`transition_task` 不再错误宣称所有 COMPLETED/FAILED 都必须有 Outcome。
- T34 保持：parent Task cancellation、PROPOSED Action forward invalidation、stale Action rejection、restart retry、cancel/authorize race fail-closed 全部仍由原 P12 回归覆盖并 GREEN。
- Candidate required Gates：p12-execution-gate `35569370381 / SUCCESS`（76 passed）；p12-execution-world `35569370483 / SUCCESS`；p15-periodic-review `35569370484 / SUCCESS`；fused-turn-runtime `35569370409 / SUCCESS`；c09-wake-dispatch `35569370452 / SUCCESS`；p16-convergence-gate `35569370331 / SUCCESS`（330 passed）。
- P16 habitation：candidate-derived gate-only run `35569485261 / SUCCESS`（92 passed）；运行分支只加临时文档触发标记，代码 parent 为 candidate `07617df8...`，完成后已把 gate 分支 reset 回 candidate，不向 main 带入 P16 语义改动。
- Merge-result Gates：p12-execution-world `35569585991 / SUCCESS`；p12-execution-gate `35569586060 / SUCCESS`；p15-periodic-review `35569585969 / SUCCESS`；fused-turn-runtime `35569586033 / SUCCESS`；c09-wake-dispatch `35569586006 / SUCCESS`；p16-convergence-gate `35569586008 / SUCCESS`。
- Affected files：`src/aios_core/execution/service.py`；`src/aios_core/runtime/turn_runtime.py`；`tests/integration/test_v3_execution_world.py`。
- Deferred：本窗口未执行 `P16-TRIAGE-001`、`P16-CAMPAIGN-001` 或 Resident habitation。
- 当时第一个 READY：`P16-TRIAGE-001`；后续 C14 PM reprioritization 已覆盖此历史状态。

以下 T28/T34/T35-RULE/AUDIT 等段落保留为历史完成快照，不再代表当前 READY 状态。

历史完成任务快照：`T28-REC-001` — **DONE / ASSISTANT RAW PROACTIVE MEMORY BOUNDARY CLOSED**。

- Started from main：`f8a2f8e4cf53de579bd0bc69cfd85421d109d65b`
- Final functional-base revalidation：`48f5e29ad564ef7c1687b5a0d81cede1452e82e8`（已包含 T34-EXEC-001 Core 修复；其后至 merge 前主线仅有 T34 governance/checkpoint 文本更新）
- Work branch：`fix/t28-rec-assistant-dialogue-20260921`
- Pre-fix test-only SHA：`6f5d6e1b95b16123a936defe9d5c948238430084`
- Current-main reproduction：memory-recommendation run `35566383722 / FAILURE`；`test_assistant_raw_dialogue_is_not_ordinary_proactive_user_memory` 实际泄漏 assistant MemoryCard excerpt=`索引是公共能力，推荐只是调用方。`
- Candidate：`2a16d1ffaaec877356f4f281e82d884e6ac97ab5`
- PR：#49
- Squash merge：`e159ab30a12b819ca053085d5103460e66ef9f16`
- Task-board completion metadata commit：`3cd793e3d9325c316d1bcf4beb29a0ab02c195fd`
- Final required Gates：memory-recommendation `35567154409 / SUCCESS`；fused-turn-runtime `35567154468 / SUCCESS`；p14-long-context `35567154469 / SUCCESS`；world-index `35567154562 / SUCCESS`；p16-habitation-harness `35567154411 / SUCCESS`；p16-convergence-gate `35567154443 / SUCCESS`
- 修复语义：普通 proactive 与 antecedent recommendation 均在候选来源边界排除 assistant-role raw conversation Observation；AI 自己过去说过的话不再仅凭文本命中被重新包装成用户/世界事实主动注入未来模型。
- 保留语义：assistant raw dialogue 没有删除、改写或移出 World；same-session continuity、WorldSearchIndex、显式 `search_world`、conversation drill-down 仍可读取原始 assistant 文本。
- 未退化：用户 raw dialogue、PLATFORM/external reality fact、evidence-grounded Claim 仍可作为合格 proactive candidate；无相关历史时 recommendation 可为 0。
- Affected files：`src/aios_core/recommendation/proactive.py`；`tests/integration/test_v3_memory_recommendation.py`；`tests/integration/test_v3_fused_turn_runtime.py`；`tests/integration/test_v3_long_context_continuity.py`；`tests/integration/test_m0_prime_store_delta_and_search.py`；`tests/habitation/test_t28_proactive_memory_boundary.py`
- Deferred：本窗口没有执行或修改 `T33-RECALL-001`、`T36-SEARCH-001`、`T35-IMPL-001`；没有 TopicState 重构、Claim/Summary 语义改造、raw dialogue 删除或第二套 recommendation engine。
- 当前第一个 READY：`T36-SEARCH-001`；必须由新窗口执行，本 T28 窗口在 checkpoint 写回后停止。

上一完成任务：`T34-EXEC-001` — **DONE / CORE EXECUTION RACE CLOSED**。

- Started from main：`f8a2f8e4cf53de579bd0bc69cfd85421d109d65b`
- Final clean sync base：`04f3170f5e09c7ab00ffd4233465560c78dc2423`
- Reproduction/WIP branch：`fix/t34-exec-001-cancel-authorize-20260921`
- Final work branch：`fix/t34-exec-001-final-20260921`
- Pre-fix test-only SHA：`d622958dc286bfae816fd4f2e36d9fb063d8252e`
- Current-main reproduction：Actions run `35566808198 / SUCCESS`；pre-fix 两个 T34 用例均真实出现 `Failed: DID NOT RAISE <class 'ValueError'>`，marker=`T34_REPRO_RESULT=BUG_REPRODUCED`
- Candidate：`da14638fc0f8cf14bad6b5315988d7c7db691ac8`
- PR：#54
- Squash merge：`48f5e29ad564ef7c1687b5a0d81cede1452e82e8`
- Exact-candidate Gate：run `35566890602 / SUCCESS`；T34 targeted、P12、fused-turn-runtime、C09、P15、P16 habitation、P16 convergence 全部 GREEN
- Merge-result Gates：p12-execution-gate `35567021266 / SUCCESS`；p12-execution-world `35567021273 / SUCCESS`；p16-convergence-gate `35567021258 / SUCCESS`
- Task-board completion metadata commit：`fe802801fd2f23081ef605b489f73ea831b577ef`
- 修复语义：authorize 前后都要求父 Task 仍为同一 current RUNNING revision；Task CANCELLED 时在同一提交中把仍为 PROPOSED 的子 Action 前向修订为 CANCELLED；历史 Action revision 不删除、不覆写。
- 竞态语义：final eligibility revalidation 后冻结 `expected_world_revision`；其后的并发 World 写入由 WorldStore `VERSION_CONFLICT` fail closed，不能吸收 Task cancel 后继续生成 dispatch envelope。
- restart/retry：新 SQLite store reopen 及 pre-T34 已持久化“Task cancelled / Action proposed”坏世界均被拒绝；拒绝发生在 authorizer 调用前且不增加 world revision。
- normal path：RUNNING Task 的正常 Action authorize 仍通过既有与新增 P12/P16 回归。
- 当前第一个 READY：`T36-SEARCH-001`。
- `T35-IMPL-001` 的 T35-RULE + T34 两个 dependency 现已满足，task board 状态为 READY；必须另开窗口执行，本窗口没有进入 T35 实现。
- `T28-REC-001`、`T33-RECALL-001` 仍为独立 READY；`P16-TRIAGE-001` 继续等待本轮 activated blockers 全部解决。

再上一完成任务：`T35-RULE-001` — **DONE / GOVERNANCE CONTRACT ONLY**。

- Started from main：`f8a2f8e4cf53de579bd0bc69cfd85421d109d65b`
- Governance claim commit：`f83438729b7ef0a0ba58b0c3302e1deb5f4ca6bd`
- Work branch：`governance/t35-rule-non-action-completion-20260921`
- Semantic candidate：`b58bbb31a04a119897890452e76461f14fd46288`
- PR：#53
- Merge SHA：`6fcb51d6e2ecf6e2ab8ff0fa62013f094b32f21c`
- Final task-board merge-metadata commit：`f55c47bd892d738852d80f6cb783768659c02b90`
- 正式裁决：`governance/T35_NON_ACTION_TASK_COMPLETION_EVIDENCE_RULING_2026-09-21.md`
- 裁决核心：所有 Task 终态都必须由 pinned durable evidence 支撑；只有需要 AIOS 外部执行的 Task 才强制 `Action → Outcome`；纯验证/分析/Review/内部工作产物不得伪造 Action/Outcome。
- `TaskType` 不承担外部授权分类；完成证据模式与 TaskType 正交，裁决定义 `WORLD_EVIDENCE / ACTION_OUTCOME / MIXED` 三种 completion contract。
- assistant raw response、unsupported Claim、Task/Goal 自引用、AI 自述“完成”、synthetic Outcome、循环 OperationExperience、world_revision 单独存在均不得作为完成凭据。
- 本任务未修改 Runtime/Core/schema/state machine；因此不伪跑无关 Core Gate，只做法源/源码/审计证据复核与 diff-scope 验证。
- `T35-IMPL-001` 在 T35-RULE-001 完成当时保持 **BLOCKED**；现 T34-EXEC-001 已完成，实时状态以 task board 的 **READY** 为准，仍必须另开窗口/PR。

更早完成任务：`AUDIT-001` — **DONE / AUDIT ONLY**。

- 证据矩阵：`reviews/AUDIT-001_ISSUE30_CURRENT_MAIN_EVIDENCE_MATRIX_2026-09-21.md`
- PR #48 / squash merge：`0ecacd8204414fd41e7ebda8e8b4521406154d3f`
- final governance metadata commit：`05fc6b81ed78a0903915432afe1835e5537a96c7`
- T34 / #34：`STILL_OPEN`
- T36 / #36：`STILL_OPEN`
- T28 / #28：`STILL_OPEN`
- T35 / #35：`STILL_OPEN`
- T33 / #33：`STILL_OPEN`
- AUDIT-001 未修改任何 Core/runtime/test 实现。
- PR #37 仍是旧基线上的历史中央分流证据，不能作为当前 main 的修复证明。
- 当前第一个 READY：`T36-SEARCH-001`。
- 其他已激活 READY：`T28-REC-001`、`T35-IMPL-001`、`T33-RECALL-001`。
- `T35-IMPL-001` 的 `T35-RULE-001` 与 `T34-EXEC-001` 前置均已满足，现为 READY；仍必须独立新窗口执行。
- `P16-TRIAGE-001` 继续 BLOCKED，直到本轮激活缺陷全部解决。

历史段落继续保留为工程证据。任何下方“当前 blocker=0 / 下一动作 / 唯一 blocker”表述若与本节或 task board 冲突，均视为历史快照，以本节 + task board + 最新 main 为准。

## 2026-09-21 C13-MTR-001 — non-world Metering Ledger CLOSED

- MeteringRecord / Metering Ledger 位于 operations-side SQLite table，不是 WorldObject；meter write 不推进 `world_revision`、不进入 World Index、不产生 Wake。
- 模型每轮真实返回后、capability 执行与 Wake/Review completion 前立即持久化 metering。
- Background Budget 的 token 真值来自 Metering Ledger，不再依赖 Wake World metadata。
- provider usage 缺失时记录 unknown（NULL），不伪造 0；OpenAI / Anthropic / Gemini 的 provider/model/response id provenance 可审计。
- 相同 provider response id 重放幂等；冲突重放 fail closed。
- Periodic Review 恢复时保留原 cognition/write `started_at`，实际 provider 调用按恢复当天 `recorded_at` 计费，两个时间轴明确分离。
- Safety Wake 继续绕过 BACKGROUND_DAY budget；既有安全预算语义未退化。
- PR #47 已 squash merge：`f9baacd5ac7be1646036a4e878934e77965c6640`。
- 下一任务仅为新窗口 `AUDIT-001`；本窗口停止。

## 历史基线快照（非当前任务授权）

- 时间：2026-09-20
- 最后已验证功能代码锚点：`8ddb7a606fda375aad98a0b2545a992c2497d828`
- 验证 Gate：PR #20 accepted head `b8fa56df92fdb928e2168da2054364f6a91161fd` 的 **16 个 workflow 全部 success**；其中 `constitutional-cognition-closure` run `35508439330`、`p16-habitation-harness` run `35508439464`、`p16-convergence-gate` run `35508439468`。
- 当前项目阶段：**P16 多模型独立长期入住测试 / 真实 provider 证据阶段**
- 当前主干状态：**P0-P15 主链 + 2026-09-20 宪法认知代码收口已闭环。Adaptive Cognitive Policy、Event Dimension、CommunicationExperience、Core-owned Topic State、九档模型生成 Summary 调度、深层世界导航、Goal/Task 相关上下文和 PLATFORM provenance 已进入 main。**
- 当前 blocker：**2026-09-20 第二轮完整性复审重新发现代码级 blocker：跨 subject 隔离未统一强制、CognitivePolicy 尚未形成真实运行策略闭环、P6 多尺度 Summary 尚未接入真实 Current-Core 长期调度。另有 stable-ID 编码、fail-open broad exception、Entity/Relation 运行闭环、Event 状态机与 P16 fixture 覆盖等 HIGH 问题。真实 provider artifacts 仍缺，但已不再是唯一 blocker。**
- 下一主任务：**先按 `reviews/AIOS_V3_CODE_COMPLETENESS_REAUDIT_2026-09-20.md` 关闭第二轮代码 blocker，再扩展 P16 sealed-life 覆盖；代码闭环重新通过后才执行付费 provider cognition evidence。P17 继续禁止启动。**

## P13 已完成并通过 Gate

- 通用 SourceAdapterSpec：GREEN
- explicit source dimension：GREEN
- USER / SENSOR reality source boundary：GREEN
- Canonical Observation：GREEN
- 时区统一为 UTC，并保留原始时间表示：GREEN
- adapter_id + external_record_id + external_revision 精确幂等：GREEN
- source identity 内容冲突 fail closed：GREEN
- Payment / Order 保持独立来源维度：GREEN
- 图片/录音长期入口为 descriptor / transcript，不保存 raw binary：GREEN
- raw binary 输入会被拒绝并留下 ingest failure audit：GREEN
- 高频数值流按显式 tolerance/change-threshold 机械压缩：GREEN
- numeric change 只表示数值变化，不生成健康/心理意义：GREEN
- 旧 semantic purifier / keyword evidence classifier 明确禁止迁回：GREEN
- P13 聚合 Gate：GREEN

## P13 Post-Gate 红队加固

P13 完成后又做了一轮独立正确性审计，并通过 PR #3 合入主线：

- stable ID 改为结构化 canonical JSON 哈希，消除分隔符边界碰撞：GREEN
- Reality / failure audit / numeric 对象身份加入 `subject_id`，消除跨用户对象碰撞：GREEN
- adapter / external_record / revision 身份文本统一规范化：GREEN
- source digest 覆盖 dimension / source_class / schema / locator / interval，adapter 语义漂移 fail closed：GREEN
- durable read 只把明确 `NOT_FOUND` 当不存在；存储损坏/不可用不再被吞掉：GREEN
- Reality commit 使用确定性 operation identity，竞态窗口 exact retry 可走 WorldStore idempotency：GREEN
- numeric series 对既有对象校验 source digest，偷改 sample / policy / unit / locator 会拒绝：GREEN
- `series_id` 明确定义为一个不可变 compression batch/window 的身份：GREEN
- NaN / Infinity 在 numeric contract 边界拒绝：GREEN
- 通用 RealityRecord 支持时间区间，不再强制把日历/睡眠等区间压成时间点：GREEN
- reused existing 路径也执行 index catch-up，可修复前次提交后投影滞后：GREEN
- 原并行 PR #2 已关闭，禁止形成第二套 reality-ingest 实现：DONE
- 公共 ingest 边界重新验证 Pydantic frozen models，防止 `model_copy(update=...)` 绕过 SourceAdapter / RealityRecord / Numeric Policy 约束：GREEN
- Failure Audit 身份加入 external revision、adapter semantics、locator 与 failure digest，避免不同来源修订/Schema 漂移被错误折叠成同一个失败事件：GREEN
- numeric change 不再跨 `max_gap_seconds` 观测空洞伪造瞬时变化事件：GREEN
- numeric segment provenance 改为 range + digest，避免高频长区间把全部 source ids / locators 再复制一遍而抵消压缩收益：GREEN
- nested binary 检测支持 BaseModel/dataclass/cyclic container，防止二进制通过包装对象绕过长期事实边界或造成递归崩溃：GREEN
- 合并提交：`f21960967431d8a96e3f37de75bdcd2a3b8e81dc`
- 合并后 P13 聚合 Gate：run `35498395468` **success**
- 合并后 P13 reality Gate：run `35498395508` **success**

以上是 P13 的 post-gate hardening，不改变当前主阶段 **P14**。

## P14 已完成并通过 Gate

- `recent_turns` 不再依赖调用方维护，非空外部注入会被拒绝：GREEN
- 当前 session 的最近完整轮次从统一 WorldStore 重建：GREEN
- Conversation identity 纳入 subject，跨用户同 session/turn 不再碰撞：GREEN
- deterministic scheduler 负责选择需要总结的闭合 turn range：GREEN
- summary 内容由注入的真实模型 handler 生成，系统不写固定“认知总结”：GREEN
- round summary 以 Summary 世界对象持久化，并 pin 每条 raw user/assistant Observation：GREEN
- raw dialogue 永久保留，summary 仅作为 continuity index：GREEN
- `drill_down_conversation` 可由 summary source refs 回捞 exact raw dialogue：GREEN
- token budget 裁掉 summary 内容时仍可通过 `list_conversation_summaries` → raw drill-down 恢复：GREEN
- summary 模型失败不阻断当前用户回复，raw facts 保留；重启后待总结区间可重新发现：GREEN
- 新 session 不自动灌入旧 session summaries；跨 session 仍走 recommendation/index：GREEN
- 18 轮长会话回归：1-4 / 5-8 / 9-12 / 13-16 形成顺序 summary windows，17-18 保留 recent raw，36 条原始对话零删除：GREEN
- P14 合并 PR：#4
- P14 功能合并 SHA：`76d179d48d1bb222c3d18eb5c435dd6f0c9ba212`
- 合并后 P14 Gate：run `35499189697` **success**
- 合并后 fused runtime：run `35499189641` **success**
- P9 / P10 / P11 / P12 / P13 / conversation-world 合并后回归：**all success**

## 当前可运行数据链

```text
Phone / App / Sensor / Media
↓
SourceAdapterSpec
↓
RealityRecord / MediaDescriptor / NumericSample
↓
dedupe + UTC normalize + provenance
↓
Canonical Observation
或
mechanical numeric segment/change
↓
WorldStore
↓
WorldSearchIndex / Summary
↓
Resident AI later forms cognition
```

## P14 机制说明（已完成）

解决一个真实模型在单个长会话中超过上下文窗口后“前面聊过什么不知道”的问题。

必须保持：

```text
Raw User/AI Dialogue 永久在 World
↓
当前会话 rolling state
↓
达到 token / turn 阈值
↓
模型生成 round summary
↓
summary 作为快速 continuity index
↓
后续模型默认看：
- 最近原始轮次
- 较早 round summaries
↓
用户引用旧内容时
↓
先命中 summary
↓
再按 summary source refs / session range
   drill-down 到 exact raw dialogue
```

## P14 关键边界

1. 轮总结只服务同一长会话的 context continuity。
2. 轮总结不等于 AI对用户的认知。
3. raw dialogue 永久保留，不因“已经总结”而删除。
4. 总结由模型生成；系统负责何时要求总结、哪些轮次进入窗口、token预算。
5. 不允许 summary 用新的意义覆盖原始用户/AI原话。
6. summary 必须 pin 它覆盖的 raw conversation Observation refs。
7. 多轮总结可以进一步做 session-level summary，但仍只是 continuity index。
8. 当前会话回捞优先按 session_id / turn range 精确定位，再用文本语义辅助。
9. 新会话不自动加载旧会话全部 round summaries；跨会话仍走智能推荐/世界索引。
10. recent_turns 不应继续依赖外部调用方手工维护。

## P14 首批必读

1. `docs/constitution/AIOS_v3.0_Long_Context_Continuity_Constitution.md`
2. `docs/constitution/AIOS_v3.0_User_AI_Interaction_Dimension_Constitution.md`
3. `src/aios_core/ingest/conversation.py`
4. `src/aios_core/context/controller.py`
5. `src/aios_core/runtime/turn_runtime.py`
6. `src/aios_core/summaries/dimension_summary.py`
7. `src/aios_core/query/search.py`

## P14 禁止事项

- 不删除 raw dialogue 来解决 token 限制。
- 不把 round summary 写成 User Understanding Claim。
- 不让系统用固定模板生成“认知总结”。
- 不跨 session 默认灌入所有历史。
- 不把 long-context continuity 与智能推荐重新混成一个机制。
- 不把 summary 当 source of truth。
- 不因 context budget 截断而静默丢失可回捞路径。

## P15 已完成并通过 Gate

- deterministic scheduler 只决定 review 时间与 bounded candidate window：GREEN
- review anchor 全部使用 pinned world refs：GREEN
- Review Wake 生命周期 NEW → RUNNING → COMPLETED：GREEN
- crash 后 RUNNING review 可在重启后恢复：GREEN
- 无新 world changes 时写 SUPPRESSED marker，不调用模型：GREEN
- 完成边界使用 exclusive-start，review 自己的同刻 writeback 不机械触发下一轮：GREEN
- Periodic Review 复用同一个 Resident Cognitive Runtime 与 CapabilityRegistry：GREEN
- review instruction 不伪造成用户 Conversation Observation：GREEN
- review anchors 通过分页能力按需读取，不把完整世界塞进固定 cockpit：GREEN
- Resident AI 可在 review 中 revise / retract 旧 Claim：GREEN
- Resident AI 可形成 Calibration / Strategy / Self 等 evidence-grounded cognition：GREEN
- OperationExperience 必须引用至少一个 pinned real case：GREEN
- OperationExperience 与 CommunicationExperience 进入统一世界索引：GREEN
- scheduler 本身不生成“用户成长/AI成长/策略更好”等语义结论：GREEN
- P15 宪法：`docs/constitution/AIOS_v3.0_Periodic_Review_Growth_Constitution.md`
- P15 功能锚点：`3261eae4967632ea4ef72669ef53ef3dfe5199a7`
- P15 Gate：run `35499766871` / **success**

## P16 入住测试发现并关闭：C09 Wake 调度闭环

2026-09-20 的严格顺序 blind self-resident habitation 暴露出一个实现缺口；回查旧仓 `Haneof/fantonghui@aios-2.0` 的 v3.0 正式法统后确认：

- Observation **默认只写入世界，不直接唤醒 AI**；
- 第 77~83 条要求机械触发只负责“是否值得叫醒 AI”，不得替 AI 形成语义结论；
- ADJ-003 要求机械命中统一经过 Wake 去重 / 合并 / 冷却；
- Wake Reason 是任务第一指针，不是认知结论；
- Task 到期与 periodic review 都是合法 Wake 来源；
- Step-0 负责确定性安全 / 方便度 / 信道 / 预算门禁。

因此原实验中“RealityIngest 不直接唤醒 AI”不是 bug。真正缺口是 **机械 Trigger → Wake Bus → Step-0 → 通用 Wake Dispatcher → 同一 Resident Runtime** 的中央接线。

现已通过 PR #7 合入：

- 初始闭环 SHA：`6f1e20307cd1ce47aefff281f652da16af635992`
- 当前加固功能 SHA：`02b3f006d77c6396e3f8575e8547a5363582738f`
- `WakeBus`：GREEN
- exact trigger retry 幂等：GREEN
- 连续命中合并：GREEN
- cooldown suppression：GREEN
- Step-0 `OK / QUIET / HARD_BLOCK`：GREEN
- model 暂不可调用时 Wake 保留为 `QUEUED`：GREEN
- 注册 Observation 机械规则：GREEN
- P13 `numeric_change + mechanical_threshold_event` → 注册规则 → Wake：GREEN
- 通用 `FusedTurnRuntime.run_wake()`：GREEN
- `TASK_DUE Wake` → 同一 Resident CognitiveRuntime → Task 后续状态：GREEN
- QUIET 时允许后台认知但禁止对外投放：GREEN
- background Wake 不伪造 Conversation Observation：GREEN
- P15 Review → Task → P12 TASK_DUE → C09 Resident Dispatch 跨阶段闭环：GREEN
- P12 / P14 / P15 / fused runtime / P9-P11 / world kernel/index 回归：全部 GREEN
- 合并后初始 main 验证：`c09-wake-dispatch` run `35501126516` / **success**
- Wake dedupe identity hardening：`wake_source + rule_id + dedupe_key` 共同定义合并作用域；延迟 exact retry 仍幂等；新 out-of-order hit fail closed：Gate run `35501301595` / **success**

实验 PR #5 与旧基线 PR #6 已关闭，仅保留历史证据；不得合入。

## P16 Long-Horizon Habitation Hardening 已完成

- PR #10：squash merge
- 合并 SHA：`1fc7b9f5c69b01f01dac8097efd29973bc4dbf4c`
- merge-result Gate：`p16-habitation-harness` run `35503797730` / **success**
- 虚拟时钟按真实中间时间点执行 Task due / C09 Wake / Periodic Review：GREEN
- `end_at` 最终 horizon：GREEN
- P13 `MediaDescriptorRecord` / `NumericSample` 路径：GREEN
- 注册 mechanical marker → C09 Wake：GREEN
- 每个模型 fresh private SQLite World：GREEN
- visible-life fingerprint 不受 evaluator scenario id/version/seed 污染：GREEN
- sensor numeric future sample leak fail closed：GREEN
- 现有 fixture bundle 身份与路径隔离规则保留：GREEN

## P16 当前目标

用多个真实模型、隐藏虚拟人生和长时间跨度数据测试：

> AIOS 中的模型是否真的依靠世界、索引、Summary、认知修正、Goal/Action/Outcome 与周期 Review 逐渐形成连续理解，而不是靠测试脚本偷做认知。

P16 benchmark foundation 已合入 main：

- PR #1：已 squash merge，主线合并 SHA `3e8c9a1ac5da5d342966807cbc3602a48888443d`
- Current-Core adapter：`tests/habitation/current_core.py`
- Harness / fixture / evaluator：`tests/habitation/**`
- 主线 P16 Gate：run `35503409815` / **success**
- PR #5：历史实验证据已关闭，不合并

P16 必须重点验证：

```text
隐藏人生事件流
↓
Reality / Conversation 进入 World
↓
真实 Resident Model 多轮入住
↓
模型自主形成 / 修正 cognition
↓
Goal / Task / Action / Outcome
↓
Periodic Review
↓
跨天 / 跨阶段继续运行
↓
评价：
- 是否记住真正相关历史
- 是否会找错记忆
- 是否会形成错误高阶理解
- 是否会自我强化错误
- 是否会根据新证据翻案
- 是否会创建无意义维度
- 是否会把 summary 当事实
- 是否会在没有 Outcome 时伪造经验
- 是否能在重启/换模型后继续生活在同一个 World
```

## P16 禁止事项

- 不把 expected answer 写进模型可见输入。
- 不用数万道固定题让程序几秒钟字符串匹配“通过”。
- 不写小程序替 Resident AI 做总结、认知、因果或人格判断。
- 测试 harness 可以机械计分事实可追溯性、引用正确性、状态机与泄漏，但不能替模型完成认知任务。
- 隐藏 ground truth 只能用于 reviewer 评分，Resident Model 不得看到。
- 多 Agent 是多个模型分别入住/测试同一套 AIOS 机制，不是让一堆 Agent 在世界里互相协作完成固定答案。
- P16 分支不得重新造第二套 World、Index、Recommendation、Runtime 或 Review 系统。

## 历史工程断点（非当前任务授权）

- 时间：2026-09-20 17:40 +08:00
- 最后已验证功能代码锚点：`6b68cb2953d7747a784c1a5a737c66f9de101f29`
- 最近 Green Gate：`p16-habitation-harness` run `35503409815` / **success**
- 当前阶段：**P16 多模型独立长期入住测试**
- 已完成：**PR #1 对齐/审计/合并；Current-Core target；private world isolation；strict resident/oracle bundle identity validation；main 分支 P16 CI**
- 当前 blocker：**真实 provider model 尚未接入 benchmark runner，因此目前只能证明 harness/隔离/AIOS 接线正确，不能声称长期认知能力已通过。**
- 下一动作：**实现/接入 provider-backed ModelHandler 与 RoundSummaryHandler，运行多个真实模型各自独立入住同一隐藏人生，并保存可审计 artifacts；随后做 evaluator-only 评估。**

## 当前不可推翻的已决事项

- 世界唯一、索引公共。
- 推荐负责“当前要不要给哪些历史”；索引负责“到哪里找”。
- 同一长会话 continuity 是独立机制，不替代跨会话推荐。
- 原始对话是事实，轮总结只是索引。
- 模型负责总结内容，系统负责调度。
- AI认知必须另走 Claim / Evidence / Revision。

## 恢复现场规则

接手时先获取 GitHub `main` 实时 HEAD，并审查本文件功能锚点之后的 commits / CI。纯地图/checkpoint文档提交可越过；功能代码必须先确认 Gate 与边界再继续。


## P16 收口控制（2026-09-20）

- 收口控制文件：`governance/P16_CONVERGENCE_CONTROL_2026-09-20.md`
- 当前唯一允许继续施工的目标：**provider-backed real-model habitation**。
- 当前 GitHub open PR：**0**；历史 merge/superseded/experiment 分支全部冻结为证据，不得恢复后直接合入。
- 隔离审查分支：`p15/periodic-review-growth-20260920`、`p16/habitation-integration-20260920`、`hardening/p15-review-growth-redteam-20260920`。这些分支只允许读取以恢复“当前 main 确实缺失”的测试/缺陷证据，禁止整分支 merge/rebase 后继续开发。
- P17 暂停启动，直到 P16 完成真实 provider 入住、可审计 artifacts 与 evaluator-only 红队评估。
- 新施工必须从最新 `main` 创建单一 P16 provider 分支，不得重造 World / Index / CognitiveRuntime / Review。


## P16 Provider / Evaluator 基础设施闭环（2026-09-20）

- 当前 main 功能锚点：`d4e467620fe67e2af681a641176c3773a701e42f`
- 当前 GitHub open PR：**0**
- 唯一 P16 施工分支：`p16/provider-backed-habitation-20260920`；已同步到 main，**ahead=0**。

本轮已完成并进入 main：

1. **P15 correctness hardening**
   - PR #12 / merge `a9a84670a18972e70f0e14f1d09d1a1e685e4bb4`
   - OperationExperience 真实结果/subject 边界；
   - assistant 自己的 Observation 不得作为真实结果；
   - Review backlog 分页，禁止 truncation 永久漏证据；
   - budget exhaustion 保持 RUNNING / resumable；
   - OperationExperience 完整 canonical identity。

2. **restart / model handoff**
   - PR #13 / merge `ffa7fd8f6a46189e8fb38eb908924e2826674cc2`
   - 可重新打开同一个 SQLite World；
   - session turn cursor 从 World 恢复；
   - 周期 Review 调度从 durable Wake / World 恢复；
   - replacement resident model 可继续同一 World；
   - run model identity 与 target model identity 强绑定。

3. **versioned oracle / evaluator contract**
   - PR #14 / merge `63a078521125ca8e011337b83495e6e629e47b7f`
   - `aios.p16.oracle.v1`；
   - evaluator 必须精确覆盖全部 criteria；
   - evaluator provider/model/version/config provenance 进入报告；
   - comparison 不允许混用不同 evaluator provenance。

4. **provider-backed resident protocol adapters**
   - PR #15 / merge `ad77187b8c98c3d29b910889b0c9adcbf1ae2813`
   - OpenAI Responses；
   - Anthropic Messages tool use；
   - Gemini Interactions function calling；
   - AIOS capability shorthand 单向翻译为 JSON Schema；
   - provider-backed RoundSummaryHandler；
   - provider/model/config/request/usage/error provenance；
   - API key 不得进入 artifact。

5. **oracle-free real-provider resident runner**
   - PR #16 / merge `9e6d4979749c8b9316317cfdd621300cbc4cb469`
   - resident runner 只加载 manifest + resident stream；
   - resident 进程不打开 oracle；
   - 输出 `launch.json` / `world.sqlite` / `run.json`；
   - 失败输出 `failure.json`；
   - manual-only Actions workflow，确定性 CI 不自动产生 provider 费用。

6. **separate post-run provider evaluator**
   - PR #17 / merge `7676ad51b2b335178b2f98911775709240dbc979`
   - 独立 evaluator CLI / workflow；
   - 先核对 scenario id / version / resident-visible fingerprint；
   - 只有核对通过后才加载 hidden oracle；
   - evaluator 不重新运行、不修改 resident World。

7. **offline multi-model evidence comparison**
   - PR #19 / merge `d4e467620fe67e2af681a641176c3773a701e42f`
   - 严格加载 provider evaluation artifacts；
   - 拒绝不同 visible-life fingerprint；
   - 拒绝 resident model identity 篡改；
   - 要求相同 evaluator provenance；
   - 只输出 criterion-by-model matrix；
   - 禁止 aggregate score / ranking / winner。

最新 comparison head 的 Gate：

- `p16-habitation-harness` run `35506311307` / **success**
- `p16-convergence-gate` run `35506311297` / **success**

### 当前唯一剩余 P16 blocker

**尚未产生真实付费 provider 的入住 artifacts。**

代码基础设施已经具备从：

`resident-only sealed life -> real provider resident -> private World -> run artifact -> separate oracle evaluator -> offline multi-model comparison`

的完整链路。

P16 仍然是 **CONTINUE / NOT PASS**，因为机械/协议/隔离测试通过不能替代真实 resident cognition 证据。

下一动作不再是写新的 Core 或 benchmark 框架，而是：

1. 为至少两个真实 provider/model 配置 API secret；
2. 对同一 sealed life 分别手动运行 resident workflow；
3. 核对所有候选的 `scenario_public_fingerprint` 完全一致；
4. 保存 provider/run provenance 和 World artifacts；
5. 用同一个 evaluator configuration 分别做 post-run oracle evaluation；
6. 离线 comparison；
7. 独立红队审查实际 cognition：错误记忆、自我强化、revision、summary misuse、dimension spam、无 Outcome 伪经验；
8. 证据成立后才允许宣布 P16 PASS 并进入 P17。


## 2026-09-20 宪法认知代码收口 — 已合入 main

历史审查：

- `reviews/AIOS_V3_CONSTITUTION_CODE_ALIGNMENT_AUDIT_2026-09-20.md`

收口报告：

- `reviews/AIOS_V3_CONSTITUTION_CODE_ALIGNMENT_CLOSURE_2026-09-20.md`

合并：

- PR #20：`core: close remaining constitutional cognition gaps`
- accepted head：`b8fa56df92fdb928e2168da2054364f6a91161fd`
- squash merge：`8ddb7a606fda375aad98a0b2545a992c2497d828`

本轮正式关闭旧审查中确认的代码缺口：

1. **Adaptive Cognitive Policy**
   - 进入统一 WorldStore；
   - 版本 / evidence / mutable_by_ai / evaluation_window / rollback_pointer；
   - hard boundary / engineering parameter 不可由普通 AI 更新放宽；
   - rollback 为 forward revision，不改写历史。

2. **Event Dimension**
   - Resident 可 `form_event`；
   - pinned evidence；
   - revise / resolve / reject / merge / split；
   - EvidenceSet / Dependency 同世界持久化。

3. **Generic Multi-Scale Summary**
   - 日 / 周 / 月 / 季 / 半年 / 年 / 3年 / 5年 / 10年九档；
   - deterministic code 只调度窗口/来源；
   - semantic summary 必须由注入模型生成；
   - raw facts 不改写，Summary 仍是 index。

4. **Topic State / Need-History**
   - TopicStateService 进入 Core；
   - 当前输入 + canonical recent turns 可维持“这个/那个/继续”类主题；
   - topic existence 与 history_may_help 分离；
   - P16 adapter 不再替 Core 注入 topic label。

5. **CommunicationExperience**
   - Resident runtime 正式 writeback；
   - 必须有真实 user/world feedback；
   - assistant 自己输出不能单独充当反馈；
   - 只记录 experience，不由 deterministic code 选择未来话术。

6. **World Navigation**
   - `focus_entity`
   - `search_timeline`
   - `follow_relation`
   - `compare_claims`
   - `retrieve_original_observation`
   - `expand_recall`
   - `inspect_outcome`

7. **Execution context**
   - 普通用户轮次自动带入 bounded relevant Goal / Task / Action / Outcome anchors；
   - 不再要求调用方把整个 execution world 手工塞给模型。

8. **Platform provenance**
   - 新增 `SourceClass.PLATFORM`；
   - trusted platform authorization / real Outcome 不再误标为 `AI_COGNITION`；
   - 旧 SQLite World 通过 lossless CHECK-constraint migration 前向兼容。

9. **Context-budget regression hardening**
   - full provider tool schema 不再在 cockpit 内重复占 token；
   - cockpit 只保留 capability name/kind/side-effecting awareness；
   - P14 long context / P16 habitation 回归保持 GREEN。

最终 accepted head 的 16 个 Gate：**全部 SUCCESS**。

### 当前唯一项目级 blocker

现在不再是“缺 Core 认知机制代码”，而是：

**P16 尚无真实模型长期入住证据。**

因此：

- 宪法代码对齐：**PASS for audited findings**
- P16：**CONTINUE / NOT PASS**
- P17：**仍禁止启动**


## 2026-09-20 第二轮代码完整性复审 — REOPENED BLOCKERS

复审报告：

- `reviews/AIOS_V3_CODE_COMPLETENESS_REAUDIT_2026-09-20.md`
- 报告提交：`5a2f569040ab0160923cbd805b2ebcdeaeb3b65b`

本轮不是否定 PR #20；PR #20 确实关闭了第一轮审查明确列出的机制缺口，16 个 Gate 也是真实 green。

但第二轮从 WorldObject 全表、subject isolation、stable identity、真实 P16 Current-Core 接线、Policy consumer/evaluation、Summary backlog、Entity/Relation 生产路径和 fixture coverage 反向审查，发现更深层问题。

### BLOCKER

1. **跨 subject 隔离未形成统一硬边界**
   - WorldStore reference validation 不校验 subject；
   - Claim / Revision / Event / Dimension / Goal / Policy / Communication refs 多数只校验存在；
   - `search_mind()` 无 subject 参数；
   - timeline/entity search、query-less ALL_DIMENSIONS、DimensionSummary 可跨 subject 读入数据。

2. **CognitivePolicy 仍是可版本化账本，不是完整自适应运行策略**
   - Resident 无 propose/register policy；
   - Current-Core / P16 不预注册 policy；
   - active policy 没有 resolver/consumer 真正改变 recommendation/search/communication/review 等行为；
   - evaluation_window 未调度；
   - Periodic Review 不把 CognitivePolicy 作为 review anchor；
   - AI policy update evidence 目前只校验存在，可引用 AI 自己 Claim 或其他 subject。

3. **P6 多尺度 Summary 未接入真实长期运行链**
   - P16 Current-Core 没有 dimension_summary_handler；
   - advance_to() 不运行 `run_due_dimension_summaries()`；
   - 无 missed-window durable backlog；
   - >max_source_objects 时可提交 truncated CURRENT Summary；
   - late data 不会自动重建旧窗口；
   - active_dimensions() 未按 dimension lifecycle 过滤。

### HIGH

- P4 TopicState/Need-History 仍使用固定词表 + `len(topic)>=4` 决定历史价值，过度机械；
- Entity/Relation 没有 Resident 正式创建/维护 capability，图索引主要依赖手工 seed；
- P6/P8/P9/P11/P12 仍有 delimiter-joined stable ID，和 P13 已修的碰撞问题不一致；
- Claim/Summary/Recommendation/ALL_DIMENSIONS 等 durable truth path 仍有 broad `except Exception` 吞存储错误；
- Event service 声称合法 forward lifecycle，但没有 previous->new transition matrix；
- P16 当前四个 sealed lives 每个仅 4-5 个显式事件，未覆盖 Policy / CommunicationExperience / Event lifecycle / Entity-Relation / P6 Summary / 完整 Dimension lifecycle。

### 当前项目裁决

- Architecture direction：**PASS**
- Core spine：**STRONG**
- PR #20 first-order closure：**VALID**
- Second-order code completeness：**NOT PASS**
- P16 paid provider execution：**应等待上述 blocker 收口后再作为 release evidence**
- P17：**BLOCKED**



## 2026-09-20 第二轮代码完整性收口 — CLOSED

第二轮复审：

- `reviews/AIOS_V3_CODE_COMPLETENESS_REAUDIT_2026-09-20.md`
- audit commit：`5a2f569040ab0160923cbd805b2ebcdeaeb3b65b`

正式收口：

- `reviews/AIOS_V3_CODE_COMPLETENESS_CLOSURE_2026-09-20.md`
- PR #21：`core: close second-pass code completeness blockers`
- accepted head：`029d8f6849cdb08e2c784cd3bded0b025d1e03e6`
- squash merge / 当前功能代码锚点：`9d9fb9d82ef42b631d032c488617316c5a2a244c`

PR #21 accepted head 触发的 **20 个 workflow 全部 SUCCESS**，包括：

- constitutional-cognition-closure
- p16-convergence-gate / full-core-regression
- p16-habitation-harness
- p15-periodic-review
- c09-wake-dispatch
- fused-turn-runtime
- world-index
- memory-recommendation
- dimension-summary
- all-dimensions-projection
- cognition-writeback / cognition-revision
- P9 / P10 / P11 / P12
- P14 long-context

本轮关闭：

1. **private-world subject isolation**
   - search / timeline / entity / ALL_DIMENSIONS / Summary 均 subject scoped；
   - direct object-id Runtime 读取也受私有世界边界约束；
   - Claim / Revision / Event / Dimension / Execution / Policy / Communication / Entity / Relation refs 受 scope 校验；
   - AI-self 只通过显式 user + AI-self 例外读取同一私有世界证据，不允许跨其他用户。

2. **CognitivePolicy 真实运行闭环**
   - Resident 可 propose policy；
   - AI policy create/update/rollback 必须是真实结果证据；
   - AI Claim / assistant 自己输出不能递归训练 policy；
   - evaluation_window 变成真实 due time；
   - 到期 policy 进入 Periodic Review；
   - Runtime 已有真实 consumer，不再只是 ledger。

3. **P6 MultiScale Summary 长期调度**
   - P16 Current-Core 已接 dimension summary handler；
   - habitation clock 实际运行多尺度 Summary；
   - durable World 反推已关闭窗口，停机不永久漏窗；
   - late data 重开旧窗口；
   - terminal Dimension 不继续维护；
   - source truncation 不提交 CURRENT；
   - 旧 CURRENT Summary 在后来发现窗口不完整时会 forward-mark STALE。

4. **第二轮 HIGH 项**
   - TopicState 移除 `len(topic)>=4`；
   - Entity / Relation Resident 生产闭环；
   - stable ID 使用 canonical structured hashing；
   - durable truth path fail-closed；
   - Event lifecycle transition matrix；
   - P16 新增 cognition-system-closure 长人生 fixture，覆盖 Policy / CommunicationExperience / Entity-Relation / Event / Summary / 多线程长期变化。

### 当前正式项目状态

- Architecture direction：**PASS**
- Core spine：**STRONG**
- PR #20 first-order closure：**PASS**
- PR #21 second-order code completeness closure：**PASS**
- 当前已知 audited Core code blockers：**0**
- P16：**CONTINUE / NOT PASS**
- P17：**BLOCKED**

### 当前唯一项目级 blocker

再次恢复为：

**缺少真实 provider/model 的长期入住认知证据。**

下一动作：

1. 至少两个真实 provider/model 分别入住同一 sealed life；
2. fresh private World；
3. resident-visible fingerprint 必须一致；
4. 保存 provider / run / World provenance；
5. 用同一 evaluator configuration 做 separate hidden-oracle evaluation；
6. offline criterion-by-model comparison；
7. 独立红队审查错误记忆、自我强化、revision、summary misuse、dimension spam、无 Outcome 伪经验；
8. 证据成立后才允许 P16 PASS / P17。

> 注意：确定性 Gate 只证明机制、隔离、持久化、状态机和接线正确，不能替代真实模型长期认知质量证明。


---

## 2026-09-21 — T33-RECALL-001 DONE

- Task ID: `T33-RECALL-001`
- Status: **DONE**
- Started from main: `f8a2f8e4cf53de579bd0bc69cfd85421d109d65b`
- Work branch: `fix/t33-recall-antecedent-gate-20260921`
- Final candidate: `91f1eecc1eb1a5aeb3dd2fa4566f045b6abea796`
- PR: #51
- Squash merge: `cb8eab12e9747bece41b14d183840e2cf13bd183`
- Task-board close commit: `f022fafde2f281fa35dd2492bdcb31aaad855214`

### Current-main reproduction

Pre-fix regression commit `e962585a346949dd884e202ffc7cabb5e306161c` triggered
`p16-convergence-gate` run `35566569236` and failed exactly on Case A:
a self-contained fresh-session input containing a local demonstrative opened
`antecedent_recall_needed=True`.

### Accepted behavior

1. Self-contained current expression does not open cross-session antecedent recall merely
   because a demonstrative/continuation word appears as an arbitrary substring.
2. True discourse-level cross-session omission/deixis may expose bounded historical
   candidates; deterministic Core does not select the antecedent identity.
3. No credible historical candidate means zero fabricated candidate.
4. Same-session continuity now reads the canonical P14 `user.text` turn shape.
   Assistant raw dialogue is never used as the same-session antecedent source.
5. Embedded `继续` no longer independently opens the history gate, while discourse-level
   `继续。` remains supported.
6. Resident `search_world`, summary/raw drill-down, proactive relevant memory, and subject
   isolation remain unchanged.

### Final Gate evidence

- `memory-recommendation` — run `35567409150` — **SUCCESS**
- `p14-long-context` — run `35567409136` — **SUCCESS**
- `fused-turn-runtime` — run `35567409167` — **SUCCESS**
- `p16-habitation-harness` — run `35567409218` — **SUCCESS**
- `p16-convergence-gate` — run `35567409187` — **SUCCESS**
- `constitutional-cognition-closure` — run `35567409138` — **SUCCESS**
- `p9-revision-gate` — run `35567409173` — **SUCCESS**
- `p10-ai-world-gate` — run `35567409295` — **SUCCESS**
- `p11-dimension-gate` — run `35567409158` — **SUCCESS**
- `p12-execution-gate` — run `35567409155` — **SUCCESS**

The final green merge-ref combined candidate `91f1eecc...` with
`main@3cd793e3d9325c316d1bcf4beb29a0ab02c195fd`. Before the squash merge,
the only later main delta was checkpoint documentation; no Runtime/Core/Test code changed.

### Deferred / handoff

- No WorldSearchIndex/query code was changed, so world-index was outside the T33 impact scope.
- `T36-SEARCH-001` and `T35-IMPL-001` were not executed in this window.
- Next READY by task-board ordering: **T36-SEARCH-001**.
- This window stops here.


---

## 2026-09-21 — T36-SEARCH-001 DONE

- Task ID: `T36-SEARCH-001`
- Status: **DONE**
- Started from main: `f8a2f8e4cf53de579bd0bc69cfd85421d109d65b`
- Final synchronization base: `56cf9a5daa2f6873744590c379acb3dff0deb705`
- Work branch: `task/t36-search-001-structured-scalar-20260921`
- Candidate SHA: `afc62009340f4451d15400c4860ee880296d9c7c`
- PR: #52
- Squash merge SHA: `07965029285cf3dfc0fdb5e506a65add60c76c29`
- Task-board close commit: `a0b9834e39168fa3f9bca09c5cf0ba756ef3f71d`

### Reproduction evidence

Test-only pre-fix run `35566751016` reproduced Issue #36 on then-current main semantics:
a nested structured Observation with `value.vendor="North Mill"` was durable in World but
`recall_candidates("North Mill")` returned zero matching Observation hits. Subject-scoped
structured scalar retrieval failed for the same reason. The defect was the string-only
`_index_row()` text-field projection.

### Accepted repair

`WorldSearchIndex` now mechanically expands only structured `Observation.value` into the
rebuildable derived search projection. Mapping keys are deterministic, list order is stable,
and string/number/bool/null scalars are searchable. The durable typed Observation is not
rewritten, no semantic Claim/Summary is generated, and the indexer performs no interpretation.

The accepted regressions cover nested dict/list/mixed scalars, numeric/boolean/null retrieval,
incremental indexing, full rebuild, projection rebuild upgrade, rebuild/incremental parity,
subject isolation, current-version filtering, inactive/retracted/stale/tombstone behavior,
legacy text Observation retrieval, P16 habitation invoice retrieval, and preservation of the
T28/T33 main regressions.

### Gate runs

- `world-index` — `35568085113` — **SUCCESS**
- `memory-recommendation` — `35568085081` — **SUCCESS**
- `p16-habitation-harness` — `35568085280` — **SUCCESS**
- `p16-convergence-gate` — `35568085170` — **SUCCESS**
- `p9-revision-gate` — `35568085180` — **SUCCESS**
- `dimension-summary` — `35568085143` — **SUCCESS**
- `constitutional-cognition-closure` — `35568085182` — **SUCCESS**
- fused-turn equivalent regression — `35568044160` — **SUCCESS**; temporary branch-only
  workflow removed before final candidate, so it is absent from the merged diff.

### Deferred / next

- Deferred issues: none inside T36 scope.
- T33/T28/T34/T35 semantics were not changed by T36.
- Next READY task: **T35-IMPL-001**.
- Per single-window rule, this T36 window stops here and must not execute the next task.


---

## 2026-09-21 — C14 Continuous Cognitive Derivation PM Reprioritization

- Planning baseline: `main@96d62819de32b3f45b1e774329e295241e015f6a`
- Planning branch: `governance/c14-continuous-cognitive-derivation-20260921`
- Canonical plan: `governance/C14_CONTINUOUS_COGNITIVE_DERIVATION_IMPLEMENTATION_PLAN_2026-09-21.md`
- New first READY task: **C14-RULE-001**
- P16-TRIAGE / long campaign continuation: **PAUSED / BLOCKED on C14-CLOSE-001**

### New blocker

Long-habitation evidence now shows a mechanism-level gap that was not visible from deterministic closure alone:

- user/world facts and Dimension Summary are durable and searchable;
- AI-world Claim/Strategy/Calibration/Experience machinery exists;
- the shared CognitiveRuntime and Periodic Review exist;
- but a newly created/revised Summary does not currently guarantee a durable opportunity for the Resident to decide whether that new temporal structure should change AI-world cognition.

This is **not** a Claim-count target and does not invalidate the multi-dimensional world model.

The missing bridge is:

```text
eligible changed Summary
  -> durable background cognition opportunity
  -> same Resident CognitiveRuntime
  -> inspect/search/compare evidence
  -> form/revise/retract cognition OR silence
```

### Frozen implementation constraints

1. Summary remains descriptive and must not become Claim.
2. Deterministic Core may schedule an opportunity but may not infer semantic meaning.
3. No keyword-to-Claim logic, fixed psychological labels, fixed semantic importance threshold, or "N occurrences = preference" rule.
4. No second AI database and no second cognition model/runtime.
5. Reuse Wake, Background Budget, Attention Bundle, CognitiveRuntime, AIWorldCognitionService, and Periodic Review.
6. Pure AI-cognition Summary must not recursively create an unbounded self-derivation loop.
7. Crash/restart must not permanently lose a Summary-derived cognition opportunity.
8. Silence/no cognition write is a valid Resident outcome.
9. C14 semantic PASS requires real Resident evidence; deterministic GREEN alone is insufficient.

### Task chain

```text
C14-RULE-001
  -> C14-SCHED-001
  -> C14-RUNTIME-001
  -> C14-LOOP-001
  -> C14-RES-001
  -> C14-CLOSE-001
  -> resume P16-TRIAGE / Campaign
```

This planning window changes governance/prioritization only. It does **not** execute C14-RULE-001 or modify Runtime/Core semantics.


---

## 2026-09-21 — C14 PM hardening accepted

The C14 implementation plan has been hardened before `C14-RULE-001` starts.

Mandatory requirements are now recorded at:

- `governance/C14_COGNITIVE_DERIVATION_PM_HARDENING_REQUIREMENTS_2026-09-21.md`

The accepted additional blockers are:

1. Summary may trigger/navigate cognition but cannot be the sole terminal proof for durable high-level cognition; evidence closure must reach qualifying non-Summary leaf-world sources.
2. C14 semantic validation must include a genuinely cross-dimensional case where no single dimension alone is sufficient.
3. At least one cognition must survive session/runtime replacement and later be recovered through normal AIOS World/Index mechanisms to materially affect a new independent decision.
4. Real Resident validation must include both a positive cognition case and a matched negative control where similar repetition exists but the correct result is silence/UNKNOWN/no unsupported cognition.
5. Derivation eligibility/provenance must be mechanically computed from existing SourceClass plus transitive pinned source/dependency lineage, not a second semantic source database.

Governance interpretation:

- prefer an authoritative C14 runtime/semantic ruling;
- do not rewrite the primary constitution unless C14-RULE-001 proves an actual unresolved normative gap;
- do not create a second FINAL/amendment/registry authority chain.

C14 completion is now explicitly behavior-based, not Claim-count based.


---

## 2026-09-21 — C14-RULE-001 authoritative semantic ruling

- Task: `C14-RULE-001`
- Status: **DONE / GOVERNANCE SEMANTICS FROZEN**
- Started from main: `eae9f6e74f5a51b3869b2151f56ca8875e5c8372`
- Work branch: `governance/c14-rule-001-20260921-sol`
- Candidate: `33effe8a86af3d5a34a6b227618db82caf519c37`
- Ruling commit: `57d8e7f854cbcc8f90263977b3c01599e786cf1f`
- PR: #58
- Squash merge: `f9438cce087a422ad6d2394b8f0c2a22307fe283`
- Ruling: `governance/C14_CONTINUOUS_COGNITIVE_DERIVATION_RULING_2026-09-21.md`
- Constitution / registry changes: **NONE**. Existing Fused Baseline, Dimension Summary, AI Dimension, Cognitive Runtime, and Periodic Review rules were sufficient; C14 required an authoritative implementation-level interpretation, not a new law chain.
- Frozen boundary: Summary is trigger/navigation/compression and may participate in EvidenceSet, but C14 durable high-level cognition cannot terminate support in Summary/AI-cognition/maintenance recursion. Support provenance closure must reach proposition-appropriate non-Summary case evidence.
- Derived lineage: `REALITY / AI_COGNITION_ONLY / MAINTENANCE_ONLY / MIXED / UNKNOWN`, mechanically recomputed from existing SourceClass plus exact pinned source/dependency lineage. A Summary's own maintenance commit does not determine its content lineage.
- Cross-dimensional rule: Resident keeps search/inspect/compare/ALL_DIMENSIONS/counter-evidence autonomy; no dimension-count or occurrence-count semantics.
- Silence: fully valid completion with no fake Claim/Experience/Outcome.
- Behavioral acceptance: C14 requires later new-session/new-runtime recovery through durable World/Index and observable cognition use, then Outcome/new-evidence revision or grounded retention.
- Resident validation: matched positive + negative-silence controls are mandatory.
- Periodic Review remains the longer-window consolidation/backstop and is not replaced by Continuous Derivation.
- Next READY task after this merge: **C14-SCHED-001**.
- This window must stop after C14-RULE-001 and must not execute C14-SCHED-001.


---

## 2026-09-21 — C14-SCHED-001 DONE

- Status: **DONE / MERGED**
- Started from main: `26d406314850327e4965bd2d4c7e84cf7431372b`
- Work branch: `c14/sched-cognitive-derivation-20260921`
- Candidate: `5389118b9e37b8f0b33552099e39d5c8a31eaffb`
- PR: #59
- Squash merge: `f0b24cda3c76d5170f5f27fb5a94107036e2f2c4`

### Accepted scheduler boundary

C14 now has a durable deterministic bridge from an eligible Dimension Summary revision to a
Resident cognition **opportunity**, without performing cognition in Core.

- dedicated `WakeSource.COGNITIVE_DERIVATION`;
- routing is `BACKGROUND`, through the existing WakeBus / AttentionRouter / Background Budget;
- Wake contains exact Summary ref, summary dimension/window/granularity and mechanical lineage audit only;
- Wake carries no meaning/Claim/preference/personality conclusion;
- no `CognitionCandidate` table, second scheduler database, second World, second model, or deterministic Claim conversion was added.

### Mechanical provenance

The runtime view is recomputed from existing durable World truth only:

`REALITY / AI_COGNITION_ONLY / MAINTENANCE_ONLY / MIXED / UNKNOWN`.

Traversal recursively follows exact pinned SourceRefs, EvidenceSet refs and registered support/source
Dependency edges to leaf revisions. Exact revision SourceClass is read from the existing
`object_revisions -> world_commits` ledger. Summary's own MAINTENANCE commit is scaffolding and is
not treated as content provenance. Unpinned/missing/corrupt/cyclic/cross-subject lineage fails closed
to UNKNOWN. Legacy combined conversation turns use the already-durable Observation `metadata.role`
to prevent assistant raw dialogue from inheriting the shared USER commit class.

Eligibility is limited to latest content revision + `CURRENT` + active + non-truncated Summary.
REALITY and MIXED may schedule; AI_COGNITION_ONLY, MAINTENANCE_ONLY and UNKNOWN do not immediate
self-derive. Periodic Review remains the backstop.

### Identity and crash recovery

Wake identity is deterministic per Summary revision through
`c14:cognitive-derivation:<summary_id>:<revision>`, with durable Summary `recorded_at` as the
signal timestamp. Exact retries return the same Wake; revision N+1 creates a distinct Wake.

`MultiScaleSummaryScheduler` reconciles current durable summaries before each new scheduling pass,
and performs post-commit ensure after a new Summary commit. Therefore the hard crash gap

`Summary commit -> process crash -> Wake missing -> restart -> reconcile`

is closed using World + Summary revision + Wake lifecycle only, with no extra scheduler ledger.

### Self-loop hardening

C14 Wake audit stores `summary_dimension` rather than generic `metadata.dimension`, preventing the
mechanical Wake from being rediscovered as same-dimension source material by a later Dimension
Summary. AI-only/maintenance-only lineage is also non-immediate, preventing the direct
AI Claim -> AI Summary -> Derivation Wake -> AI Claim loop at scheduler level.

### Gate evidence

- `c14-cognitive-derivation-scheduler` — run `35579489466` — **SUCCESS**
  - C14 scheduler targeted, dimension-summary, world-index, C09 wake dispatch,
    cognitive-runtime, fused-turn-runtime, P15 periodic review, C13 metering,
    P14 long-context, memory/T28, P16 habitation, P16 convergence: all **SUCCESS**
- `c09-wake-dispatch` — run `35579489436` — **SUCCESS**
- `dimension-summary` — run `35579489555` — **SUCCESS**
- `world-index` — run `35579489460` — **SUCCESS**
- `constitutional-cognition-closure` — run `35579489456` — **SUCCESS**
- `p16-habitation-harness` — run `35579489564` — **SUCCESS**
- `p16-convergence-gate` — run `35579489485` — **SUCCESS**
- additional: `world-kernel` `35579489440` SUCCESS; `p9-revision-gate` `35579489464` SUCCESS

### Bugs found / fixed during acceptance

1. C14 Wake's dimension audit field initially used generic `metadata.dimension`; because the World
   search projection mechanically derives dimensions from that field, the Wake could have become a
   source in a later Summary window. It was changed to `summary_dimension` before acceptance.
2. The required habitation regression exposed an adapter bug: it snapshotted all pending Wakes, then
   the first dispatch could merge sibling BACKGROUND Wakes and leave stale MERGED children in the
   snapshot. The adapter now re-reads current durable Wake state before dispatch and skips terminal
   merged children. No Resident semantic behavior or C14-RUNTIME implementation was added.

### Deferred / handoff

- **C14-RUNTIME-001 = READY**.
- Resident semantic interpretation/form-revise-retract/silence behavior is intentionally not
  implemented in this task.
- C14-LOOP-001 and Resident validation remain blocked on the runtime task.
- This C14-SCHED window stops here and must not execute C14-RUNTIME-001.


---

## 2026-09-21 — C14-SCHED PM acceptance follow-up

C14-SCHED-001 correctness is accepted.

Non-blocking item deferred to `C14-LOOP-001`:

Current reconciliation rebuilds the support Dependency view during each per-Summary lineage derivation. That is correct but may cause unnecessary repeated whole-graph scans as long-term Summary/Dependency volume grows.

C14-LOOP must add a bounded long-horizon reconciliation strategy (for example, one support graph build per reconciliation pass, safe cache, or incremental equivalent) without creating a second provenance truth or semantic importance index.

This does not block `C14-RUNTIME-001`.

---

## 2026-09-21 — C14-RUNTIME-001 DONE

- Status: **DONE / MERGED**
- Started from main: `461a2289247eeb0cbbc39bbcfbe613022c885311`
- Work branch: `c14/runtime-cognitive-derivation-20260921`
- Candidate: `75cc62ca13169c6ba8752e0562224705fe6f9ac2`
- PR: **#61**
- Squash merge: `a887ba537e9797d4bf5a7b7fb482fa4a55f47df7`

### Runtime closure

`WakeSource.COGNITIVE_DERIVATION` now enters the **same existing Resident runtime**:

```text
WakeBus
  -> FusedTurnRuntime.run_wake()
  -> existing CognitiveRuntime
  -> existing model_handler / capability loop / termination semantics
  -> existing C13 non-world ModelMeteringLedger
```

No second Resident, second ModelHandler, cognition compiler, hidden semantic engine, second World, second provenance database or CognitionCandidate store was introduced.

For a derivation Wake, the Resident cockpit now receives:

- exact running Wake ref;
- exact pinned Summary ref/revision;
- Summary dimension, granularity and time window;
- scheduler-computed derived lineage audit;
- runtime-recomputed derived lineage audit, including `leaf_refs`, `grounding_leaf_refs`, unresolved refs and issues;
- bounded current AI-world context;
- the normal Resident capability catalog;
- Step-0 and background-budget context.

The instruction explicitly states that Summary is a **temporal/navigation anchor only**. It is not a Claim, semantic conclusion, or sufficient proof. The Resident retains search/inspect/timeline/compare/recall/ALL_DIMENSIONS/Outcome inspection autonomy and may form, revise, retract, or correctly remain silent.

### Leaf-grounded cognition boundary

C14 Runtime does not create a second provenance algorithm. The existing C14 scheduler walker was minimally extended into a shared exact-pinned resolver used by both scheduling and derivation writeback validation.

During `COGNITIVE_DERIVATION`, the following Resident cognition paths all pass the same closure:

- `commit_claim`
- `commit_ai_world_claim`
- `revise_claim`
- `retract_claim`

The guard requires a mechanically valid REALITY/MIXED closure with no unresolved/corrupt/cross-subject/cyclic branch and at least one qualifying `grounding_leaf_ref`.

Important ruling-preserving distinction:

- a bare Summary or Summary chain with no qualifying non-Summary leaf is rejected;
- a Summary ref is legal when its **transitive pinned closure** reaches proposition-appropriate reality/case evidence;
- an old AI semantic assertion cannot certify a new Claim merely because the old assertion was historically grounded;
- real operation/case lineage such as `OperationExperience -> Outcome -> world/user evidence` remains legal for AI-self / Strategy / Calibration learning.

No Claim prose, keyword, count threshold, confidence threshold, emotion/personality classifier or semantic score participates in this enforcement.

### T28 / assistant-raw regression

A dedicated negative/positive control is now covered:

- assistant raw dialogue -> Conversation Summary -> derivation attempt to assert a user fact: **rejected** when no qualifying user/reality leaf exists;
- user raw dialogue -> Summary -> drill down exact user Observation -> grounded cognition: **accepted**.

Conversation Summary itself was not globally disabled.

### Silence and user delivery

Silence is a first-class successful Resident result:

- Wake completes normally;
- no Claim is required;
- no fake OperationExperience/Outcome/Review is generated;
- the silence regression proves zero semantic write.

Even if a derivation model returns response text, C14 forces background delivery off. The internal response can participate in runtime termination bookkeeping but is not directly delivered to the user.

### C13 metering

C14 reuses the existing non-world `ModelMeteringLedger`. Provider/model/token usage is recorded through the same model-call recorder and does not become World/Wake economic truth.

### Candidate Gate evidence

- `c14-cognitive-derivation-runtime` — `35582197711` — **SUCCESS**
- `c14-cognitive-derivation-scheduler` — `35582197425` — **SUCCESS**
- `constitutional-cognition-closure` — `35582197542` — **SUCCESS**
- `p16-convergence-gate` — `35582198031` — **SUCCESS**
- `p15-periodic-review` — `35582197360` — **SUCCESS**
- `dimension-summary` — `35582197498` — **SUCCESS**
- `p14-long-context` — `35582197567` — **SUCCESS**
- `c09-wake-dispatch` — `35582197629` — **SUCCESS**
- `p10-ai-world-gate` — `35582197450` — **SUCCESS**
- `p9-revision-gate` — `35582197446` — **SUCCESS**
- `p12-execution-gate` — `35582197586` — **SUCCESS**
- `fused-turn-runtime` — `35582197662` — **SUCCESS**
- `p11-dimension-gate` — `35582197613` — **SUCCESS**

The dedicated C14 Runtime workflow includes all seven required jobs: targeted scheduler/runtime, cognition closure, runtime/Wake/Fused, dimension/index/execution, P15/C13/P14/T28, P16 habitation harness and full P16 convergence.

### Merge-result main Gate evidence

On `main@a887ba537e9797d4bf5a7b7fb482fa4a55f47df7`:

- `c14-cognitive-derivation-runtime` — `35582457482` — **SUCCESS**
- `c14-cognitive-derivation-scheduler` — `35582457687` — **SUCCESS**
- `p16-convergence-gate` — `35582457558` — **SUCCESS**
- `p15-periodic-review` — `35582457662` — **SUCCESS**
- `p10-ai-world-gate` — `35582457462` — **SUCCESS**
- `dimension-summary` — `35582457614` — **SUCCESS**
- `c09-wake-dispatch` — `35582457569` — **SUCCESS**
- `p11-dimension-gate` — `35582457737` — **SUCCESS**
- `p9-revision-gate` — `35582457356` — **SUCCESS**
- `fused-turn-runtime` — `35582457578` — **SUCCESS**
- `all-dimensions-projection` — `35582457352` — **SUCCESS**
- `p12-execution-gate` — `35582457490` — **SUCCESS**
- `p14-long-context` — `35582457564` — **SUCCESS**

### Changed implementation / evidence files

Core:

- `src/aios_core/runtime/turn_runtime.py`
- `src/aios_core/summaries/cognitive_derivation.py`

Test / Gate:

- `tests/integration/test_v3_c14_cognitive_derivation_runtime.py`
- `.github/workflows/c14-cognitive-derivation-runtime.yml`

### Bugs closed in this task

1. Derivation Wake previously used only the generic Wake instruction/cockpit and could be folded through generic BACKGROUND bundling rather than retaining the exact dedicated Summary inspection contract.
2. Summary/AI-cognition support closure was not enforced at Resident durable cognition create/revise/retract boundaries.
3. Protecting only `commit_claim` would have left `commit_ai_world_claim`, revision and retraction as bypasses; all four are now under the same closure.
4. Alternate experience/policy cognition writers are not allowed to become C14 derivation bypasses.

### Deferred / handoff

- **C14-LOOP-001 = READY**.
- Its scope remains burst/budget/coalescing/defer/restart hardening, Periodic Review coexistence, new-runtime World/Index recovery + behavioral consumption, and the previously accepted bounded provenance-reconcile scale improvement.
- **C14-RES-001 remains BLOCKED** on LOOP.
- P16 campaign remains blocked until the full C14 chain closes.
- This window does **not** start C14-LOOP-001.



---

## 2026-09-21 — C14-RUNTIME-001 PM acceptance found side-effect escape blocker

Reviewed main: `97554b041768d93a6ab9f83d80e87f27972eeaf0`

PR #61 correctly closed the intended Claim paths:

- same Resident CognitiveRuntime;
- exact derivation cockpit;
- shared provenance resolver;
- Summary-only / old-AI-Claim recursive support rejected;
- user/Outcome grounding preserved;
- T28 protected;
- silence valid;
- BACKGROUND delivery suppressed;
- C13 non-world metering preserved.

However PM side-effect audit found that `COGNITIVE_DERIVATION` still falls through to the general durable-write allowlist after denying Experience/Policy writers.

As a result it can still request writes such as Event, Entity/Relation, Dimension, Goal/Task/Action, and AttentionWatch. Those handlers do not uniformly invoke the C14 leaf-grounding validator; Event and Dimension paths were specifically verified to enforce ordinary pinned/scope rules rather than the C14 support-provenance closure.

This creates a route around the intended "leaf-grounded cognition OR silence" contract and can also create background semantic/execution spam.

Canonical review:

`governance/C14_RUNTIME_PM_ACCEPTANCE_REVIEW_2026-09-21.md`

Next action:

`C14-RUNTIME-HARDEN-001`

Preferred minimal fix: for `COGNITIVE_DERIVATION`, authorize only `commit_claim`, `commit_ai_world_claim`, `revise_claim`, and `retract_claim` as side-effecting capabilities. Keep all legitimate read capabilities. Do not change normal user-turn or Periodic Review write semantics.

`C14-LOOP-001` is blocked until this hardening task is merged and independently accepted.


---

## 2026-09-21 — C14-RUNTIME-HARDEN-001 DONE

- Status: **DONE / MERGED**
- Started main: `646c5a3d0cf22cfa99c70667925ad240ea53f663`
- Work branch: `c14/runtime-hardening-side-effects-20260921`
- Candidate: `3accaeebe8ee1b3d420d2dfa3528ecb5e7388d86`
- PR: **#63**
- Core squash merge: `09002ddf8fd1fd4af08f54ac5b190d4c39c9e25b`
- Evidence: `reviews/C14_RUNTIME_HARDEN_001_COMPLETION_EVIDENCE_2026-09-21.md`

### Accepted authorization boundary

For `WakeSource.COGNITIVE_DERIVATION`, the side-effect authorizer is now
default-deny. The only authorized persistent cognition writes are:

- `commit_claim`
- `commit_ai_world_claim`
- `revise_claim`
- `retract_claim`

All four continue through `_validate_c14_cognition_grounding()`. All other current
or future side-effecting capabilities are denied for this Wake source. Read
capabilities remain available.

The denial is scoped only to `COGNITIVE_DERIVATION`; ordinary user interaction,
Periodic Review, and other Wake sources retain existing write semantics.

### Escape regressions

Entity, Relation, Dimension, Goal, Task, AttentionWatch, Action, Event,
Operation/Communication Experience, and CognitivePolicy write paths are denied
before handler execution. The regression captures `world_revision` across the
rejected call and proves no durable world write occurs.

A synthetic future side-effecting capability is also denied, preventing future
registry additions from silently reopening the C14 boundary.

### Gate evidence

- `c14-cognitive-derivation-runtime` `35586168903` — **SUCCESS** (7/7 aggregate jobs)
- `constitutional-cognition-closure` `35586168941` — **SUCCESS**
- `p16-convergence-gate` `35586168937` — **SUCCESS**
- `p15-periodic-review` `35586168873` — **SUCCESS**
- `fused-turn-runtime` `35586168861` — **SUCCESS**
- `c09-wake-dispatch` `35586168846` — **SUCCESS**
- `p11-dimension-gate` `35586168851` — **SUCCESS**
- `p10-ai-world-gate` `35586168898` — **SUCCESS**
- `p9-revision-gate` `35586168883` — **SUCCESS**
- `p12-execution-gate` `35586168915` — **SUCCESS**
- `p14-long-context` `35586168872` — **SUCCESS**

The C14 aggregate run includes scheduler/runtime targeted tests, cognitive-runtime,
cognition writeback/revision, AI-world, constitutional closure, Dimension Summary,
World Index, C13 metering, T28, P16 habitation harness, and full P16 convergence.

The tested candidate and squash merge use identical blobs for both changed
implementation/test files.

### Handoff

- `C14-RUNTIME-HARDEN-001 = DONE`
- `C14-LOOP-001 = READY`
- `C14-RES-001` remains blocked on LOOP
- P16 remains blocked on the full C14 chain
- this window does **not** start `C14-LOOP-001`


---

## 2026-09-21 — C14-RUNTIME-HARDEN PM acceptance / C14-LOOP preflight

`C14-RUNTIME-HARDEN-001 = PASS` after independent verification of PR #63, candidate Gates, exact merged blobs, capability side-effect marking, and pre-handler authorization.

Current durable main at review: `c12b9418bf68f3885713819432ac77bb585172ff`.

Before C14-RES, `C14-LOOP-001` must additionally close two concrete runtime gaps identified in preflight:

1. **Contract-preserving C14 coalescing.** Current `run_wake()` excludes `COGNITIVE_DERIVATION` from AttentionBundle. LOOP must permit mechanical sibling C14 coalescing without converting the effective execution contract into ordinary `ATTENTION_BUNDLE` semantics. C14 allowlist, cockpit/evidence semantics, no-delivery, and pinned member refs must survive bundling. Do not mix C14 work into a broader-write background bundle.
2. **Budget exhaustion is resumable, not complete.** Current ordinary Wake completion path can mark a model/tool/capability-budget exhausted run complete. C14 derivation must retain durable unresolved work and resume/retry safely across restart; only semantic terminal outcomes close the opportunity.

Also retain:
- AI cognition self-loop prevention;
- Periodic Review coexistence;
- new-runtime durable cognition retrieval;
- bounded provenance reconcile complexity.

Canonical detail: `governance/C14_LOOP_PM_PREFLIGHT_2026-09-21.md`.


---

## 2026-09-21 — C14 real Resident validation split

Independent PM acceptance confirmed `C14-LOOP-001 = PASS`.

However, the previous single-window `C14-RES-001` methodology was not sufficient to prove the strongest C14 requirement:

> prior cognition must survive the end of the original model session and later affect behavior in a genuinely fresh model context using only durable AIOS state.

Destroying/recreating only `FusedTurnRuntime` inside the same ChatGPT/agent conversation does not eliminate residual chat/model context.

Therefore C14 Resident validation is now split into:

1. `C14-RES-FIX-001` — Life Director sealed fixture / sequential release contract;
2. `C14-RES-A-001` — first real Resident window, stop at sealed handoff boundary;
3. `C14-RES-B-001` — completely new model window, restore only durable AIOS World/checkpoint and continue;
4. `C14-RES-EVAL-001` — independent semantic evaluator;
5. then `C14-CLOSE-001`.

Canonical protocol:

`governance/C14_REAL_RESIDENT_VALIDATION_PROTOCOL_2026-09-21.md`

This is test-method hardening only; no Core/runtime semantics are changed.

Next READY task:

`C14-RES-FIX-001`.


---

## 2026-09-21 — C14 fixture v1 PM semantic-design blocker

Independent PM review accepts the mechanical integrity of `C14-RES-FIX-001` v1 but does not accept it for formal Resident semantic validation.

Three blockers were found:

1. Phase-A `dim:conversation` events themselves substantially disclose the intended solo-writing/focus synthesis, so the positive case does not force genuinely cross-dimensional cognition.
2. Phase-B 09:00 vs 11:30 synchronization is strongly decided by current duration/deadline facts, so a correct-looking choice would not demonstrate that prior durable cognition materially changed behavior.
3. The repository contains a release contract but no executable blind release operator that can reveal only the current cursor without the Resident opening the sealed fixture.

Canonical review:

`reviews/C14_RES_FIX_001_PM_REVIEW_2026-09-21.md`

Next task:

`C14-RES-FIX-002`

Required outcome: sealed fixture v2 + new digest + improved hidden design + executable mechanical release helper. No Core changes and no Resident run.

`C14-RES-A-001` is blocked until v2 independently passes.


---

## 2026-09-21 — C14 fixture v2 semantic PASS / release-ack durability blocker

Independent PM review confirms that fixture v2 closes the v1 semantic-design blockers:

- the positive case is genuinely cross-dimensional;
- Phase-B planning is underdetermined from current facts;
- blind reveal hides future/evaluator material and enforces the 24/25 phase boundary.

One mechanical blocker remains before real Resident execution:

Current `release_operator.py ack` accepts any syntactically valid `object_id@revision` and does not prove that the exact revision exists in durable AIOS storage or is bound to the currently revealed event.

Therefore a fabricated value such as `fake_object@1` can satisfy the current ack format check and advance the release cursor.

Canonical review:

`reviews/C14_RES_FIX_002_PM_REVIEW_2026-09-21.md`

Next task:

`C14-RES-FIX-003`

Requirements:
- keep fixture v2 bytes/digest frozen;
- verify ack against actual durable AIOS World or an equivalently trusted World-derived ingest receipt;
- bind exact durable ref to current released event using mechanical, non-semantic fields;
- no Core changes and no Resident run.

`C14-RES-A-001` remains blocked until this passes.


---

## 2026-09-21 — C14-RES-FIX-003 PM acceptance

Independent PM review confirms `C14-RES-FIX-003 = PASS`.

Formal exact candidate:
`17bd54ed0b64131ded0b70d853cac205d055bdcb`

Formal exact-candidate Gate:
`35598216907 = SUCCESS`

The earlier successful run `35598032585` belongs to a pre-final candidate and is retained only as iteration history.

The durable release chain now proves:

`blind reveal -> real SQLiteWorldStore exact Observation revision -> mechanical event binding -> World-verified ack -> cursor advance`.

Fixture v2 content remains frozen.

Resident A is released under:

`reviews/internal_habitation/c14-resident/v2/release/RESIDENT_A_RUN_CONTRACT.md`

Resident A must remain semantically blind to fixture/evaluator/FIX completion/PM review material and personally author every model semantic checkpoint from current RuntimeSnapshot only.


---

## 2026-09-21 — C14 Resident A accepted; Resident B conversation preflight required

Independent PM review accepts `C14-RES-A-001`.

Evidence is pinned at PR #75 head:

`cb9b56b7039272d932158f33bfe979eff6749c9b`

Accepted sealed handoff:

- Phase A cursors: 1..24
- cursor 25 revealed: NO
- World revision/index watermark: 166 / 166
- World SHA256: `0ee338aa8f2845bb376610da3c450e09ff9cc8bec5184ca60608b2465d7ba72f`
- release-state SHA256: `e922d268fbb11364a7bb558aed60b88e7a3c075032f4fa4e1c47a84de3f765f1`
- durable cognition: one current hypothesis Claim at revision 2
- future leak / pseudo-LLM / Core modifications: not found.

Non-blocking provenance notes:

- Arena runtime used Python 3.11.2 although repository support declares >=3.12; B should use 3.12+.
- exact provider/session model identity was not platform-attested, so cross-model claims must not rely only on the declared model string.

Before Resident B, PM found a transport-layer ambiguity: the generic blind fixture adapter already stores a conversation Observation, while ordinary `FusedTurnRuntime.run_turn` must store a canonical `user_ai_interaction` Observation. Running both naively duplicates the same user utterance.

Next READY task:

`C14-RES-B-FIX-001`

Canonical scope:

`governance/C14_RES_B_CONVERSATION_INGEST_PREFLIGHT_2026-09-21.md`

No Core change and no Resident-B semantics are allowed in that preflight.
