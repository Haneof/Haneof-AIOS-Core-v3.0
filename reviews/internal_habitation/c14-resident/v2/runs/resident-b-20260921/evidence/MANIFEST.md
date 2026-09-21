# C14-RES-B-001 Resident-B Evidence Manifest

Run directory: `reviews/internal_habitation/c14-resident/v2/runs/resident-b-20260921/`
Run date: 2026-09-21 (UTC, wall clock) / simulated life span 2026-10-23T07:08 → 2026-10-31T12:03 (America/Los_Angeles)

## 0. 身份与基线

| 项 | 值 |
|---|---|
| evaluated main SHA | `9578d990fc47943b69c77b12d126255f6691a6dc`（git fetch 后实时 origin/main HEAD） |
| pinned Resident-A evidence head（冻结源） | `cb9b56b7039272d932158f33bfe979eff6749c9b`（仅取 2 个 exact 文件） |
| Resident-B branch | `arena/01a0c517-haneof-aios-core-v3-0` |
| 实际模型身份 | Arena.ai Agent Mode（平台未暴露底层模型；无伪造 usage/provenance，ModelDirective.usage=None） |
| fresh Resident-B session id | `resb-20260921-282770`（secrets.token_hex 生成） |
| 私有 working World | `world/aios_world.db` |
| inherited World SHA256（初始） | `0ee338aa8f2845bb376610da3c450e09ff9cc8bec5184ca60608b2465d7ba72f`（与要求一致 ✓） |
| inherited release-state SHA256（初始） | `e922d268fbb11364a7bb558aed60b88e7a3c075032f4fa4e1c47a84de3f765f1`（与要求一致 ✓） |
| 冻结原件 | `frozen/aios_world.db`、`frozen/release_state.json`（chmod 444，不可变副本） |
| init --phase B | `evidence/init_phase_b.json`（operator v4 升级成功，next_sequence=25） |

## 1. 事件处理（cursors 25–36，全部 reveal→ingest→ack→lifecycle）

每 cursor 目录：`evidence/events/cursor_0NN/`（event.json / ingest 或 canonical_ingest receipt / ack receipt / lifecycle.md）

| cursor | event_id | 时间 (PDT) | envelope | 路径 | ingest ref |
|---|---|---|---|---|---|
| 25 | c14resv2-025 | 10-23 07:08 | dim:sleep/wearable/SENSOR | 机械 | obs_c14_fixture_075eab7c98ac9ee6ee87e07d@1 |
| 26 | c14resv2-026 | 10-23 08:02 | dim:conversation/USER/text | **canonical turn 1** | obs_conv_user_68c898d46eb08fe87b18c45c@1 |
| 27 | c14resv2-027 | 10-23 08:04 | dim:schedule/calendar/PLATFORM | 机械 | obs_c14_fixture_2207720973263e409bd2cef2@1 |
| 28 | c14resv2-028 | 10-23 08:06 | dim:work/task_tracker/PLATFORM | 机械 | obs_c14_fixture_b52acdba6fd407971c7887b7@1 |
| 29 | c14resv2-029 | 10-23 08:08 | dim:collaboration/team_message/PLATFORM | 机械 | obs_c14_fixture_a4ab6046c6c7c1e0bfffcfa7@1 |
| 30 | c14resv2-030 | 10-29 08:07 | dim:work/task_tracker/PLATFORM | 机械 | obs_c14_fixture_3257a682fdb79b091e7d1027@1 |
| 31 | c14resv2-031 | 10-29 12:14 | dim:work_outcome/task_tracker/PLATFORM | 机械 | obs_c14_fixture_a2532add6d81bd551775e8d3@1 |
| 32 | c14resv2-032 | 10-29 12:26 | dim:conversation/USER/text | **canonical turn 2** | obs_conv_user_dea25617f685204d460139b9@1 |
| 33 | c14resv2-033 | 10-29 12:32 | dim:collaboration_outcome/PLATFORM | 机械 | obs_c14_fixture_6edc33829384066e33f98fdd@1 |
| 34 | c14resv2-034 | 10-31 08:37 | dim:schedule/calendar/PLATFORM | 机械 | obs_c14_fixture_3eb25da1e72cb9fb2600dc2a@1 |
| 35 | c14resv2-035 | 10-31 09:24 | dim:incident_outcome/PLATFORM | 机械 | obs_c14_fixture_830181aff1f939fba1a78e1f@1 |
| 36 | c14resv2-036 | 10-31 12:03 | dim:conversation/USER/text | **canonical turn 3** | obs_conv_user_29525f7972266b81f43cf289@1 |

- 机械 ingest 数：9；canonical conversation ingest 数：3（turn 1/2/3，均 canonical durable ack ✓）
- 每 turn 的 run_turn 均复用 canonical user Observation（user_observation_id 与 canonical ingest 完全一致；无第二份 user Observation）
- assistant Observations：obs_conv_ai_30e47e67b81efdb7e5c54efe@1（t1）、obs_conv_ai_317d3ffead372f9e92101083@1（t2）、obs_conv_ai_69957acfbbcdba0995a132de@1（t3）
- 处理 cursor 范围：25→36；release endpoint 完成后 operator 报 "fixture release already complete"（next_sequence=37）

## 2. 交互桥与决策记录

- `bridge/bridge_server.py`：薄同步桥（仅 instantiate real AIOS / serialize / pause / receive / execute / save；无语义规则；未修改 src/aios_core/**）
- `bridge/log.jsonl`：append-only 运行日志（每次 job/model_request/model_response）
- `bridge/io/req_N.json`（N=1..49）：每个 exact RuntimeSnapshot（含 cockpit、capability catalog/history）或 Summary input
- `bridge/io/resp_N.json`：本人实际输出的 ModelDirective（capability_calls/response/silence）或 Summary 文本
- `bridge/results/j*.json`：job 结果（含 capability call results、wake refs、review refs、world revision/watermark）
- `bridge/jobs/j*.json`：job 输入

### 决策单元统计

| 类别 | 数量 |
|---|---|
| model directive 决策（runtime checkpoints） | 25 |
| dimension summary 撰写 | 24（20 个新窗口 + 2 个 stale 重生×2） |
| round summary 撰写 | 0（3 turns 未触发 chunk/token 阈值） |
| 合计决策单元 | 49（io req/resp 1..49） |
| respond 终止 | 4（turn 1/2/3 + task wake 送达） |
| silence 终止 | 8（5 个 C14 bundle wake + 3 个 periodic review） |

## 3. Wake / Periodic Review

| 类型 | ref | 时间 | 结果 |
|---|---|---|---|
| C14 bundle（3 members） | wake_bundle_6068c3523c9579e0e8f30047 | 10-23 07:09 | silence（5 rounds：检索耗尽轮次，无认知写入） |
| C14 bundle（2 members） | wake_bundle_9a69611a0313d2f2c1e339e1 | 10-23 07:10 | silence（1 round） |
| C14 bundle（13 members） | wake_bundle_09c6a8306d8ca735efd6a667 | 10-29 08:08 | silence（1 round） |
| C14 bundle（2 members） | wake_bundle_55ad51af39f63e6846adb5c7 | 10-29 12:15 | silence（1 round） |
| C14 bundle（4 members） | wake_bundle_893374463c8ad52df4581db5 | 10-31 08:38 | silence（1 round） |
| TASK_DUE（interrupt） | wake_6596ecf663244460c672c441 | 10-29 12:14 | responded + 送达（2 rounds） |
| Periodic Review | wake_review_a84750cb6936db9854ff695a | 10-23 07:09 | silence（4 rounds；含 claim rev 3 修订） |
| Periodic Review | （见 bridge/results/j031_review.json） | 10-29 08:08 | silence（2 rounds） |
| Periodic Review | （见 bridge/results/j049_review.json） | 10-31 08:38 | silence（2 rounds） |

## 4. Cognition 变更（durable refs）

| 操作 | ref | 内容摘要 |
|---|---|---|
| revise（10-23） | clm_79df61916b8bb4c10cb3faa3 @2→@3 | 写作块 Claim 并入 10-21"方案修改"相邻弱支持观察；evidence_set evs_revision_c6f1fef22df4183ea7df1eb5；confidence 保持 0.5 |
| revise（10-29） | clm_79df61916b8bb4c10cb3faa3 @3→@4 | 并入 10-29 发布说明直接观察（12:08 提前交付）；evidence_set evs_revision_0e05b5ab8b79d4c807e198b8；confidence 0.5→0.6 |
| create（10-31） | clm_42e66b47b667be52da20ae8a @1 | AI-world user_understanding："先协同后专注"故障处理风格（reported/preference/0.6）；evidence_set evs_b5c274c8e052bfdfecbb6a06 |
| retract | 无 | — |
| task | task_5029111ade74171bc3758e98 @1→@4 | create（waiting_time）→ wake materialization ready@2 → running@3 → completed@4（world_evidence） |

旧认知参与后续判断的证据链（可审计）：search/timeline 检索 → clm_79df…@2（cursor 25 wake）→ rev 3 → memory card 带入 cursor 26 turn（retrieval_score 10）→ 9:00 推荐与 task 创建 → 10-29 结果 → rev 4 → cursor 32 用户反馈确认（保持）。

## 5. World / index 终态

| 项 | 值 |
|---|---|
| 初始 world_revision（继承） | 166 / watermark 166 |
| 最终 world_revision | 262 / index watermark 262（完全追平） |
| 对象计数 | observation 39、wake 93、dependency 185、summary 63、evidence_set 5、claim 2、task 1 |
| **final World SHA256** | `a288fc5d11a1a73006725efdd906a7ab014d4228085c610b4a32f887cfe3d615`（final/aios_world.db，WAL 已合并） |
| **final release-state SHA256** | `9281ced5013b45445574698d53ff9a2d57d5308ac5d1221e5db178efcf0c8a4f`（final/release_state.json） |
| final release state | active_phase=B、last_acked=36（c14resv2-036）、next=37、pending=None、36 receipts（33 fixture_observation + 3 canonical_user_turn）、operator v4 |

## 6. Retries / errors（全部已恢复或放弃并记录）

1. 10-23 review：commit_operation_experience 被 Core 拒绝（"operation experience requires real result evidence: Observation, Outcome or CommunicationExperience"；Wake ref 不合格）——合法约束，放弃该写入。
2. 10-29 task wake：transition_task waiting_time→ready 因 task@1 已被 wake materialization 推进而非 current——随后 @2→running、@3→completed 成功。
3. 10-31 turn 3：commit_ai_world_claim 第一次 claim_type="user_stated_preference" 非法枚举被拒——改为 "preference" 成功。
4. 环境问题（非 World 影响）：sandbox 无 python3.12（repo 要求 ≥3.12），用 3.11.2 venv + pydantic 2.13.5 全量编译通过并运行；一次 bash 工具参数笔误导致超时（无副作用）。

## 7. 系统问题记录（未修复，按任务要求只记录）

- 无 Core 修改；`src/aios_core/**`、fixture、release contract、task board 均未改动（git diff 为证）。
- 机械 ingest 路径（mechanical_ingest_adapter）不经过 RealityIngestService 的 observation_listener，因此 attention watch 不会因 fixture 事件触发——本 run 未注册 watch，无实际影响；仅记录。

## 8. 隔离与污染

- 本窗口为 fresh runtime；未使用任何模型侧聊天记忆。
- 全程未打开：sealed_fixture.json、fixture_manifest.json、evaluator/**、Resident A 聊天记录/FINAL_REPORT/SEMANTIC_TRACE/Summary 文本/ModelDirective 证据/capability history/handoff prose/PM review、C14 evaluator design notes、PR #75 目录列表。
- 唯一继承：frozen World + release state（SHA 验证一致），经 init --phase B 正式升级。
- **Contamination status: NONE（无 RUN CONTAMINATED 事件）**

## 9. 结论状态

**PHASE_B_COMPLETE / AWAITING_INDEPENDENT_EVALUATION**
（不判断 C14 是否 PASS；语义裁决属于 C14-RES-EVAL-001）

## 10. Git 状态（2026-09-21 运行结束时）

- 本地 commit：`de25b7c`（branch `arena/01a0c517-haneof-aios-core-v3-0`，基于 main `9578d99`）
- push / evidence PR：**未完成**——sandbox 内 GitHub token 失效（`gh auth status`: authentication failed）。evidence 已完整保存在本分支 commit 中；GitHub 重连后重试 `git push origin arena/01a0c517-haneof-aios-core-v3-0` 即可。不合并任何 evidence PR；C14-RES-B-001 保持 READY/未写 DONE。
