
## F-001 代词/指示语开场不触发先行词召回

- 分类（初判）: MECHANISM GAP
- 严重度: MEDIUM
- 模拟时间: 2026-10-02T09:58+08:00
- 证据: checkpoint `segment_001-s0012-ev-s1-0006#cp00`, input_fingerprint `223f49d5f8e441c18981f784612930d03b835aa02fd372c8a6004b341934b6ef`, world_revision_before=11
- 用户输入: 「她到了 一个人 拎个铁皮饼干盒」（纯第三人称代词，无本句内先行词）
- 期望机制: TopicState 识别无先行词代词 → `antecedent_recall_needed=true`，或推荐器回退到"当前未闭合的日程/约定"
- 观察机制: `topic_state = {antecedent_recall_needed: false, history_may_help: false, reason: "current_utterance_topic:history_not_needed"}`；`memory_cards = []`
- 影响: 本次先行词恰好还在 `recent_turns`（昨夜"明天上午十点有个客户来看东西"）内，Resident 可自行解析；一旦先行词超出 `recent_turn_limit`/已被 Summary 压缩，Resident 将拿不到任何线索，而 08:12 已入库的日历 Observation（含客户姓名）也未被召回
- 最小复现: 同一 session 第 1 天说「明天上午十点有个客户来看东西」，第 2 天说「她到了」；将 `recent_turn_limit` 调小到不含第 1 天该轮，观察 memory_cards 是否仍为空

## F-002 capability catalog 未披露 entity_key 前缀约束

- 分类: BUG（契约面自相矛盾）
- 严重度: LOW（可自愈，但每次都浪费一个 tool round）
- 模拟时间: 2026-10-02T11:41+08:00
- 证据: checkpoint `segment_001-s0014-ev-s1-0007#cp01`，capability_history 返回
  `CAPABILITY_EXECUTION_ERROR: entity_key must start with 'entity:'`
- 期望: `propose_entity.input_schema.entity_key` 应像 `propose_dimension.input_schema.dimension_key`
  一样写成 `"string starting entity:"`，因为 catalog 是 Resident 唯一可见的调用契约
- 观察: 写成 `"string"`，约束只藏在 `EntityProposalRequest` 的 pydantic 校验里
- 对照: `propose_dimension.dimension_key = "string starting dim:"`（已正确披露）
- 影响: 任何首次建立 Entity 的 Resident 都会先吃一次执行错误；在 `max_total_capability_calls`
  预算紧张的长回合里，这类无效调用会挤掉真正的语义调用
- 最小复现: 任一 turn 中调用 `propose_entity(entity_key="person:x", ...)`
- 补充实例（2026-10-02T11:44+08:00, checkpoint `segment_001-s0016-ev-s1-0008#cp00`）:
  用户说「她一直在说她哥 说这本是她哥留下的 没提钱」，其中「这本」明确指代上一轮刚建立的
  Entity《周氏族谱》(entity_5aeb17d17c30f7c7705601c1)，但 `memory_cards` 仍为 `[]`，
  `topic_state.reason` 仍是 `current_utterance_topic:history_not_needed`。
  说明该缺口不只影响人称代词，也影响指示代词（这本/那个/上回那卷）。

## F-003 无法建立「尚不知姓名」的身份锚点

- 分类: MECHANISM GAP
- 严重度: LOW
- 模拟时间: 2026-10-02T14:22+08:00
- 证据: checkpoint `segment_001-s0020-ev-s1-0010#cp02`，
  `CAPABILITY_EXECUTION_ERROR: entity requires canonical_name or at least one alias`
- 场景: 用户从未自报姓名。Resident 想为「用户本人」建一个身份锚点以便挂载 Relation，
  但 `propose_entity` 要求 canonical_name 或至少一个 alias。
- 后果: Resident 只有两条路——(a) 编一个名字/称号（污染世界模型，且日后 revise 成本高）；
  (b) 放弃 Entity，把关系降级成 Claim（丢失 Relation 图结构）。本次选择 (b)。
- 期望机制: 允许 `canonical_name=null` 的匿名锚点，用 `entity_key` 承载身份，
  等真实姓名到达后再走 `revise_entity` 补名（这条路径本身已存在）
- 最小复现: `propose_entity(entity_key="entity:person:x", entity_kind="person",
  canonical_name=null, aliases=[], evidence_refs=[...])`

## F-004 字面共现召回把无关旧记忆塞进当前语境

- 分类: MECHANISM GAP
- 严重度: MEDIUM
- 模拟时间: 2026-10-02T20:14+08:00
- 证据: checkpoint `segment_001-s0024-ev-s1-0012#cp00`，input_fingerprint
  `5e75cc87794c671eeb2a26991c8b7f2273dfc27ed092d607fe5a4bfb7e559be0`
- 用户输入: 「回过去了 我爸说没事 就是问我十一回不回无锡 我说看情况」（家庭话题）
- 召回结果: 唯一一张 memory_card 是 `clm_2dea16c4cd2c903dc69ad677`
  「《周氏族谱》为民国十九年（1930）**无锡**刻本…」，`match_reason=current_topic_index_overlap`，score=1
- 问题: 两个「无锡」语义完全不同（刻本产地 vs 父亲所在城市），却因字面共现被推入家庭对话上下文
- 同时: 真正相关的前因（19:31 三通未接来电）未被召回 —— 见 F-005
- 影响: 长期生活里这类假相关会持续占用 token 预算并把 Resident 的注意力带偏
- 建议方向: 召回排序引入维度/主题一致性惩罚；对 score=1 的单字面共现降级为"仅在无其他候选时补位"

## F-005 structured_record 的 dict value 完全不进索引，整条记录永久不可召回

- 分类: BUG
- 严重度: HIGH
- 模拟时间: 2026-10-02T19:31+08:00 入库，20:14 暴露
- 证据链:
  - Observation `obs_src_717e0b225c89a415a57cf094` rev1 存在，`source_kind=call_log`，
    `modality=structured_record`，
    `value={"attempts":["18:02","18:20","18:47"],"caller":"沈守拙","missed":3,"relation_hint":"contact"}`
  - Resident 侧: `search_world(query="来电 未接 电话 爸")` → `[]`；
    `search_timeline(query="电话", window=2026-10-02T00:00~20:20+08)` → `[]`
  - 直接审计索引: `co_search(["沈守拙"]) → 0 hits`，`co_search(["电话"]) → 0`，
    `co_search(["caller"]) → 0`，`co_search(["contact"]) → 0`
  - 对照: 同一 World 内 `co_search(["周慕青"]) → 7 hits`、`co_search(["族谱"]) → 9 hits`，
    这些都是 **字符串** payload 的 reality 记录
- 根因: `src/aios_core/query/search.py:387-390`
  ```python
  for name in _TEXT_FIELDS.get(object_type, ()):
      value = payload.get(name)
      if isinstance(value, str) and value.strip():
          texts.append(value.strip())
  ```
  `_TEXT_FIELDS["observation"] = ("value",)`，但 value 是 dict 时被静默跳过：
  没有 token、没有 excerpt、没有 haystack，也不报任何告警
- 影响: 所有以结构化 payload 进入世界的现实输入（通话记录、支付单、带字段的日历、
  订单、设备事件…）对 `search_world` / `search_timeline` / 主动推荐 **完全不可见**。
  这是长期记忆的一个静默黑洞，而且不产生任何 lag/stale 信号，Resident 无从察觉
- 最小复现:
  ```python
  reality.ingest_record(spec_with_default_modality="structured_record",
      RealityRecord(external_record_id="x", occurred_at=t, received_at=t,
                    value={"caller": "沈守拙", "missed": 3}, modality=None, ...))
  index.catch_up()
  assert index.co_search(["沈守拙"]).hits == []   # 观察到的行为
  ```
- 建议方向: 对 dict/list value 做白名单键的可控展平（或对叶子字符串取 token），
  并在索引水位里记录"因结构被跳过的文本字段数"，让缺口可见而不是静默

## F-006 create_task 默认 draft，导致 next_wake_at 静默失效

- 分类: BUG
- 严重度: HIGH
- 模拟时间: 2026-10-02T20:14+08:00
- 证据:
  - `create_task(title="确认十一是否回无锡看父亲", next_wake_at="2026-10-04T21:00+08:00",
    deadline="2026-10-07T23:59+08:00", ...)` → 返回 `state="draft"`（未传 initial_state）
  - `src/aios_core/runtime/turn_runtime.py:1162` → `initial_state: str = "draft"`
  - `src/aios_core/execution/service.py:997` → `wake_due_tasks` 中
    `if task.task_state is not TaskState.WAITING_TIME: continue`
  - capability catalog 里 `initial_state` 只标注 `"string?"`，既无默认值也无合法取值枚举
- 后果: Resident 只要不显式传 `initial_state="waiting_time"`，它建立的定时提醒就永远不会
  触发 Wake，而且没有任何错误、告警或 stale 信号。Task 生命周期看起来"建立成功"，
  实际是死件。
- 影响面: 「Task due → Wake → Resident continuation」是宪法要求的闭环之一；
  该缺陷会让这一闭环在最自然的调用方式下静默断开
- 建议方向: 二选一 —— (a) 传了 `next_wake_at` 而未传 `initial_state` 时默认 `waiting_time`；
  (b) 保持 draft 默认但在 catalog 里披露默认值+合法枚举，并在返回体里给出
  `"wake_armed": false` 之类的显式提示
- 补充对照（2026-10-03 09:15，`dim:social` 日 Summary 请求）: 同一条 structured_record
  通话记录 `obs_src_717e0b225c89a415a57cf094` 出现在 Summary 的 sources 里（excerpt 为
  `str(value)`），也在 Periodic Review 的 anchor 列表里出现。
  也就是说：**枚举式路径（Summary 调度、Review anchor）能看到它，检索式路径
  （search_world / search_timeline / 主动推荐）完全看不到它**。
  缺口因此更精确：不是"结构化记录不可见"，而是"结构化记录不可检索"——
  Resident 只有恰好被枚举到时才知道它存在。
- 补充实例（2026-10-03T10:40+08:00, checkpoint `segment_002-s0003-ev-s2-0002#cp01`）:
  `transition_event(new_status="resolved")` 对一个 `candidate` Event 返回
  `ValueError: illegal Event transition: candidate->resolved`。
  状态机本身可能是对的（candidate 必须先 active 才能 resolved），但
  (a) catalog 里 `new_status` 只列出取值枚举，没有给出**每个状态允许的迁移边**；
  (b) 错误信息只说"非法"，不回传该状态的合法后继集合。
  Resident 只能靠试错消耗 tool round。建议错误里带上 `allowed_from_current: [...]`。

## F-007 Task / Event 状态机对 Resident 不可发现

- 分类: MECHANISM GAP
- 严重度: MEDIUM
- 证据（同一 run 内三次）:
  - `transition_task(new_state="waiting_time")` 对 draft Task：首次因缺 `next_wake_at` 被拒
    （`WAITING_TIME transition requires next_wake_at`），即使 Task 上已存有该字段
  - `transition_event(new_status="resolved")` 对 candidate Event：
    `illegal Event transition: candidate->resolved`（2026-10-03T10:40+08:00）
  - `transition_task(new_state="waiting_time")` 对已在 waiting_time 的 Task（想原地改期）：
    `illegal task transition: waiting_time -> waiting_time`（2026-10-03T11:02+08:00）
- 共同问题: catalog 只给状态取值枚举，不给**合法迁移边**；错误信息只说"非法"，
  不回传当前状态的合法后继集合。Resident 只能试错，每次都消耗一个 tool round
  （`max_tool_rounds` 是有限的）。
- 派生的语义缺口: 「给一个已排期的 Task 改期」这个极其常见的意图，在状态机里没有直接边。
  我最终的绕法是等原 Wake 自然触发后再改，但这依赖 Wake 已经排定；
  如果只是想推迟一个提醒，Resident 没有干净的表达方式。
- 建议方向: (a) 错误里带 `allowed_from_current`；(b) catalog 里给出迁移表；
  (c) 为 waiting_time 增加一条自环边或一个显式的 `reschedule` 语义

## F-008 历史 Summary 窗口被反复重开，重述成本与内容变化不成比例

- 分类: OPTIMIZATION
- 严重度: MEDIUM
- 证据（同一窗口 `dim:craft` / day / 2026-10-02T00:00Z→23:59Z）:
  1. 2026-10-03T01:15Z 首次要求撰写 → 产出 `sum_e26bb7cefd352dd9fe436c87` rev1
  2. 2026-10-03T02:40Z 因 `event_ca6a4598…` 升到 rev3（其 occurred 仍在 10-02）→ 再次要求撰写 → rev2
  3. 2026-10-03T03:02Z 因 `clm_e48da537…` 升到 rev2（revise_claim 产生）→ 第三次要求撰写
- 观察: 只要该维度下任一历史对象产生新 revision，其所在历史日窗就被重开并要求 Resident
  重新撰写整窗 Summary；`skipped_unchanged` 基于 source 集合摘要，任何 revision 都会让它失效
- 影响: 长期生活里核心对象（例如本项目里的族谱相关 Claim）会被反复修订，
  每次修订都强制重写它所在的**每一个**历史窗口。一年下来这是可观的模型 token 成本，
  而且 Summary 会频繁抖动，削弱"Summary 作为稳定索引"的价值
- 建议方向: (a) 对重开的窗口先做语义差异检测，只有当摘要要点确实变化时才请求模型；
  (b) 给历史窗口设定"重开预算"或按 revision 次数衰减；
  (c) 允许 Resident 返回"本窗无需更新"作为一种合法输出（当前只有撰写一条路）

## F-009 会话入库没有说话人身份，第三方发给用户的消息被当成 user_input 推给 Resident

- 分类: MECHANISM GAP
- 严重度: MEDIUM
- 模拟时间: 2026-10-03T18:20+08:00
- 证据: checkpoint `segment_002-s0011-ev-s2-0006#cp00`，session `wx_zhiwei`，
  `USER_INPUT: 妈 我这周不回来了 集训 老师说这次很重要`，`wake_reason=user_interaction`
- 事实: 这是用户的女儿发给用户的消息，不是用户发给助手的消息。
  `ConversationIngestor.commit_user_input` 把它记为 role=user 的一轮，
  并驱动一次完整的 Resident turn（含 8 个 tool round 预算）。
- 风险:
  1) Resident 可能对一条根本不是问它的话作答，产出会被写成 role=assistant 的对话轮，
     污染该会话的原始对话记录与后续 Summary；
  2) 长期看，用户与他人的聊天会被系统性地吸收成"用户对我说的话"，
     直接腐蚀 user-understanding 维度（把女儿的话当成用户的自我陈述）；
  3) 本次我选择 silence 才避免污染，但这个判断完全依赖 Resident 自己识破，
     Core 没有提供任何说话人/收件人字段可供依据。
- 本次处置: silence + 仅写一条明确标注"孩子告知"的 Claim，不把它记成用户的陈述
- 建议方向: 会话入库增加 speaker/addressee 身份位（至少区分 principal / third_party / assistant），
  并在 cockpit 里暴露；对 third_party 输入默认不驱动回复回合，只做事实入库

## F-010 后台 Wake / Review 的 cockpit 固定部分就超预算，truncated 恒为 True

- 分类: OPTIMIZATION（并含一处语义误导）
- 严重度: MEDIUM
- 证据:
  - 2026-10-02T22:58+08:00 periodic_review：`token_budget=3400, estimated_tokens=4321, truncated=True`
  - 2026-10-03T20:30+08:00 task_due wake：`token_budget=3400, estimated_tokens=4305, truncated=True`
- 观察: 这两类后台回合的 `recent_turns` / `conversation_summaries` / `memory_cards` 本来就为空
  （review 与 wake 设计上不注入主动记忆），却仍然报 `truncated=True`。
  原因是 `ContextController.assemble` 先计入固定部分
  （user_input + task_context + capability_catalog + ai_identity），
  固定部分本身已超过 budget，`truncated` 只是 `used > budget` 的结果，
  并没有任何条目真的被裁掉。
- 影响:
  1) `truncated` 这个信号对 Resident 是误导的——它暗示"有东西被裁了，你可能缺信息"，
     而实际是"固定开销超了，裁无可裁"；
  2) 后台回合的真实上下文开销长期高于名义预算，token 成本不可控；
  3) capability_catalog（39 项）在每个后台回合都全量重复计入。
- 建议方向: 区分 `over_budget_fixed` 与 `truncated_items`；后台回合按 wake 类型裁剪 catalog
  （例如 review 不需要 propose_action 的 schema）

## F-011 Wake 触发会清空 Task 的 next_wake_at，提醒一次性失效

- 分类: BUG（或至少是未披露的强不变量）
- 严重度: HIGH
- 模拟时间: 2026-10-03T20:30+08:00
- 证据:
  - Wake `wake_920d7a21b9ac4e5f7b5e377e`（`rule_id=task.next_wake_at`，
    `dedupe_key=task_due:task_7c01815e267f78f4b5de80d2:1:2026-10-03T20:30:00+08:00`）正常触发
  - 触发后 `read_execution_world` 显示该 Task：`rev 2, state=ready, next_wake_at=None`
  - 我原先 pin 的 rev1 被拒：`task reference is not current: task_7c01815e267f78f4b5de80d2@1`
- 问题链:
  1) `wake_due_tasks` 在造 Wake 时把 Task 从 `waiting_time` 推到 `ready`，并清掉 `next_wake_at`；
  2) Wake 的 `evidence_refs` 仍 pin 旧 revision，Resident 拿到的 ref 一上手就是过期的；
  3) 于是"每周提醒一次""到期前再提醒"这类最常见的循环/多次提醒，
     在没有 Resident 显式重排的情况下会**静默地只响一次**；
  4) 而重排本身又受 F-007 限制（没有 waiting_time 自环边），只能走 ready→waiting_time。
- 影响: 长期生活里，任何跨月的跟进事项都会在第一次提醒后悄悄消失，
  而 Resident 从 cockpit 上看不出任何异常——这与 F-006 一起构成
  "Task 生命周期看起来成功、实际断链"的完整失败模式
- 建议方向: (a) Wake 触发时保留 next_wake_at 或写入 `next_wake_at_planned`；
  (b) Wake 的 evidence_refs 在派发时刷新到当前 revision；
  (c) 支持显式的重复调度（rrule 或 interval），不要依赖 Resident 每次手工重排

## F-012 Periodic Review 的 backlog 分页会把「上一次 review 自己写的东西」当成新 anchor 回放

- 分类: MECHANISM GAP
- 严重度: MEDIUM（含自我强化风险）
- 模拟时间: 2026-10-03T20:00+08:00（第 2 次 review）
- 证据（直接读 Wake 对象）:
  ```
  wake_review_2860fee75f5a3b7e7e4c68bd rev3 completed periodic_review
     window 2026-09-29T14:40Z -> 2026-10-02T14:40Z | truncated=True | anchors=26
  wake_review_c2c7b7a78744bdf42e2c399a rev2 running  periodic_review
     window 2026-09-29T14:40Z -> 2026-10-02T14:40Z | truncated=False | anchors=3
     reason="periodic review backlog page due"
  ```
  第 2 次 review 的 3 个 anchor 是：
  1. `obs_conv_ai_6d1b8a40`「在。」（我人生第一句回复）
  2. `clm_d2204682140487db`「沈守拙是用户的父亲…」**← 我在上一次 review 里亲手写的 Claim**
  3. `task_146ace8beb7ea70` rev2 **← 我在上一次 review 里亲手 transition 的 Task**
- 机理: `prepare_due_review` 的 backlog 分支
  （`review/periodic.py:551-566`）在上一次 review `completed && truncated` 时，
  用**同一个窗口**重新取页，排除已 review 过的 refs。
  而 Resident 在 review 过程中写入的 Claim/Task，其 `recorded_at` 恰好落在窗口末端，
  下一轮就作为"新证据"被端回来。
- 风险: 这正是 P16 要求探测的「弱 Claim 通过 Review 自我强化」通道——
  我自己写的判断，隔天以"世界证据"的身份重新出现在我面前，
  如果我不识破，就会把它当成外部佐证再确认一次。
- 本次处置: 我识别出 3 个 anchor 全部源自我自己（或无信息量的寒暄），
  明确不做任何 confirm / revise / policy 变更，以 silence 结束。
- 附带发现: `truncated=True` 在只有 26 个 anchor 时就触发，
  因为 `ReviewSchedulePolicy.max_per_object_type=20` 卡在 observation 桶上。
  对话密集型用户会持续触发 backlog，使 review 游标滞后（本次滞后约 1 天），
  当天真实发生的事（阿桐和解、送检、知微）在当天 review 中完全不可见。
- 建议方向: (a) 把 review 自身的 writeback（claim/task/policy/experience）排除出后续
  review 的候选池，或至少标注 `origin=resident_review_writeback`；
  (b) per-object-type 上限触发 truncated 时，优先保证"新到内容"进入首页，
  而不是让历史 backlog 独占分页；(c) 在 anchor 上暴露 created_by，让 Resident 能自行识别自我回声

## F-013 维度日窗按 occurred 分组，导致「修订日」的窗口只剩结构对象却仍强制写 Summary

- 分类: MECHANISM GAP
- 严重度: MEDIUM
- 模拟时间: 2026-10-04T11:30+08:00 请求 `dim:craft` / day / 2026-10-03T00:00Z→23:59Z
- 证据: 该窗 sources 只有 3 个 `evidence_set`
  （`evs_event_74cb348d…`、`evs_event_ad4f27ab…`、`evs_revision_6b46c…`），
  没有任何 observation / claim / event 本体
- 机理: 10-03 我对 `event_ca6a4598…`（occurred 10-02）和 `clm_e48da537…`（occurred 10-02）
  做了 transition / revise，产生的新 revision 与其 EvidenceSet 的 recorded_at 是 10-03，
  但对象本身的 occurred 仍在 10-02。于是 10-03 窗只捞到新建的 EvidenceSet 容器。
- 后果:
  1) 这一窗没有任何真实生活内容，却仍要求 Resident 撰写一篇 Summary（模型成本 + 噪声对象）；
  2) `skipped_empty` 机制救不了它——窗口不是空的，只是内容全是结构容器；
  3) 长期看，每次修订历史对象都会额外产生一个"空壳日 Summary"，Summary 数量虚高，
     索引里的 Summary 信噪比持续下降。
- 建议方向: (a) 判定"窗口内是否含一级内容对象"，无则跳过；
  (b) 修订类 revision 归入其 recorded_at 所在窗口；
  (c) 允许 Resident 显式返回"本窗无可摘要内容"（与 F-008 同一诉求）

## F-014 「问清楚一件事」型 Task 无法被 Resident 正常收尾

- 分类: MECHANISM GAP
- 严重度: MEDIUM
- 模拟时间: 2026-10-04T21:35+08:00
- 场景: Task「确认十一是否回无锡看父亲」的目的就是问出一个答案。
  21:00 Wake 触发 → 我提醒 → 21:35 用户给出明确答案（不去，妹妹先看着）。
  此时该 Task 的目标已达成。
- 阻塞点:
  - `TaskState.COMPLETED` / `FAILED` 在 catalog 中明确标注「requires real Outcome refs」
  - 但 capability catalog 中**没有任何创建 Outcome 的能力**，只有只读的 `inspect_outcome`；
    `propose_action` 只创建 Action，且「never executes the side effect」
  - 于是这条 Task 只能：留在 `waiting_user`（永远挂着）、或被错误地标成 `cancelled`
    （语义上它没有被取消，它成功了）
- 影响: 长期生活里绝大多数 Task 都是"确认/跟进/问清楚"型，
  它们全都会在完成后变成僵尸 Task，`read_execution_world` 会越来越脏，
  而 Resident 无法区分"还在等"和"其实早就有答案了"
- 本次处置: 不谎报状态。Task 保留在 `waiting_user`，答案以 Claim 形式落库，
  并在 next_step 里说明它已被回答（下一次能碰到它时再处理）
- 建议方向: (a) 提供一个 `record_outcome` capability（Outcome 由 Resident 依据 pinned
  证据撰写，仍不授予外部执行权）；(b) 或允许 `waiting_user → completed`
  在附带 pinned 用户答复 Observation 时成立

## F-015 World 产物摘要基于文件字节，无法验证跨机器逻辑等价

- 分类: **TEST ARTIFACT**（缺陷在我自己的 harness，不在 Core）
- 严重度: LOW
- 位置: `harness/driver.py:680`（从 `world_copy` gzip）、`:702`（`sha256_file(world_gz)`）
- 现象: 冻结的 `segments/segment_002/world.sqlite.gz` 与在跑的 `run/world.sqlite`
  逻辑完全相同（`world_revision=95`、`object_revisions` 262 行、
  `task_7c01815e…` rev3 / `task_146ace8beb…` rev4 / `clm_8522f237…` rev1 全部一致），
  但 sha256 不同：
  - gz 解压后: `161180711863ef8b15bfb14142dca3d100f4c1cd8fe1cfd70229ccf4ca171b4e`
  - live:       `433a890dce4ddd9b61e2191a14d81e230879a762e318379a601c8adffa8eae08`
  差异来自 SQLite 页级非确定性。
- 后果: `checkpoint.json` 的 `world_artifact_sha256`（= gz 字节摘要，已核对相符）
  **不能**用来证明两次冻结的 World 等价。要证明等价必须比对逻辑内容。
- 建议: 摘要改为基于 `object_revisions` 的规范化序列化 dump；
  P16 协议中相应字段也应说明"逻辑摘要"而非"文件摘要"。

## F-016 粒度级联把 Resident 自己的写回造成「世界变化」，进而再触发 Periodic Review

- 分类: MECHANISM GAP
- 严重度: **HIGH**
- 模拟时间: 2026-10-05T01:10Z 与 2026-10-05T20:00Z（同一步内）
- 机制链（每一环都有本次运行的实测数据）:
  1. `_SUMMARY_SCALE_RANK`（`src/aios_core/summaries/dimension_summary.py:120-131`）定义 8 级粒度：
     day / week / month / quarter / half_year / year / multi_year / decade。
  2. Summary 聚合是自下而上的：低粒度 Summary 会成为高粒度 Summary 的 source。
  3. 生活从 2026-10-01 开始时，周窗 09-28→10-04 跨进九月、跨进 Q3，
     于是「我刚写的周 Summary」落进了 month 窗和 quarter 窗，成为它们唯一的 source。
  4. 实测（daemon 日志原始数字）：`segment_003-s0000-advance` 单个 advance 步
     `checkpoints: 33`、`attempted_jobs: 46`、`commits: 31`、`skipped_empty: 0`。
     33 = 2（Periodic Review 的 2 个 turn_directive round）+ 31 个 dimension_summary。
     31 = day 4 + week 9 + month 9 + quarter 9。
     其中 **18 个（month 9 + quarter 9）是纯空转**——素材只有我自己的写回，
     窗口内没有任何一级事实；day 与 week 的 13 个有真实内容。
     `skipped_empty` 在这一步是 **0**，即一个都没跳过。
     级联在 quarter 停止（half_year 窗 01-01→06-30 不重叠），这点是好的。
  5. 更严重的是第 6 环：这批自我复述随后被 Periodic Review 当成「世界变化」。
     `segment_003-s0006-advance` 的 review #4 返回 20 个 anchor，
     **18 个（90%）是我在 01:10Z–07:00Z 之间自己写的 Summary**，
     时间跨度完全落在那 6 小时内。
- 后果: 一条**自持回路**——被级联逼写的 Summary → 制造 eligible world changes →
  触发新的 Periodic Review → review 的 anchor 90% 是自己 →
  若 Resident 顺从地「据此形成 Experience」，就是纯自我强化。
  长期运行下，这会持续消耗 Resident 的认知预算与 Resident 的 tool round 预算，
  而产出为零。
- 本次处置: review #4 选择沉默，明确拒绝把自己的输出当作训练信号。
  27 个空转 Summary 我如实写成「X 月无数据」而非编造内容——
  这也是为什么本报告里有一批内容极短的 Summary，它们不是偷懒，是唯一诚实的写法。
- 建议方向:
  (a) 当某窗口的 source **全部**是同 subject 自己写的 Summary 时，应允许 `skipped_self_only`，
      不要强制 Resident 产出内容（目前 `skipped_empty` 因为「窗口里有东西」而无法触发，见 F-013）；
  (b) Periodic Review 的 anchor 选择应把「本 review 周期内由 Resident 自己创建的对象」
      降权或排除，否则 review 的信息量会随运行时长单调衰减；
  (c) 生活起点落在某个粒度窗口中段时，应为尚未开始的时段直接生成空窗标记，
      而不是等 Resident 事后逐个补写。

## F-017 review metadata 的 anchor_count 与实际下发给 Resident 的数量不一致

- 分类: BUG
- 严重度: MEDIUM
- 实测（同一次运行，两处对照）:
  | review | metadata.anchor_count | `read_periodic_review_anchors` 实际返回 |
  |---|---|---|
  | `wake_review_bcdfb3b9d72fd283f551adf4`（#3） | **38** | **20** |
  | `wake_review_253431f21978c09eb91f0cfa`（#4） | **26** | **20** |
- 两次都恰好返回 20，说明存在一个未在任何 schema/metadata 中披露的 20 条硬上限；
  而 metadata 报告的是分页前的候选数。
- 影响: Resident 无法判断自己看到的是全量还是被截断的一页。
  #4 的窗口是 10-04T14:40Z→10-05T14:40Z，窗内确有 26 个候选，我只拿到 20 个，
  却没有任何字段告诉我「还有 6 个没给你」。两次 review 的 `truncated` 字段都是 False。
- 与 F-016 的关系: 这个静默截断恰好掩盖了级联的规模——
  被丢弃的候选里可能正包含真正的外部新事实。
- 建议: 在 anchor 返回体中显式给出 `delivered` / `eligible` / `truncated` 三元组，
  或让 `truncated` 真实反映 `len(page) < eligible_count`。

### F-016 补强数据点（2026-10-06T20:00Z，review #5）

第三次观测，比例进一步恶化：

| review | 窗口 | anchor 总数 | 我自己的写回 | 外部对象 |
|---|---|---|---|---|
| #3 `bcdfb3b9` | 10-02T14:40Z→10-04T14:40Z | 20 | 13（65%） | 7 |
| #4 `253431f2` | 10-04T14:40Z→10-05T14:40Z | 20 | 18（90%） | 2 |
| #5 `cadac1bf` | 10-04T14:40Z→10-05T14:40Z | **11** | **11（100%）** | **0** |

review #5 的 11 个 anchor 里，有 4 条正文就是我自己写的「九月无数据」「Q3 无数据」。
即 review 正在要求 Resident 审阅它自己声明过的「这里什么都没有」。

同时，review #5 返回的 11 个 anchor 里没有任何外部对象。

**【订正】我最初据此写下的推论是错的。** 我说过「招标公告在 review #5 的窗口内却被
F-017 截断挤掉，因此延迟了一个 review 周期」。查 daemon 日志的原始 metadata 后：

| review | wake | 窗口（日志原文） | anchor_count | 实际下发 |
|---|---|---|---|---|
| #3 | `bcdfb3b9` | 10-02T14:40Z → 10-04T14:40Z | 38 | 20 |
| #4 | `253431f2` | 10-04T14:40Z → 10-05T14:40Z | 26 | 20 |
| #5 | `cadac1bf` | **10-04T14:40Z → 10-05T14:40Z** | 11 | 11 |
| #6 | `f460e79b` | 10-05T14:40Z → 10-07T14:40Z | 11 | 11 |

招标公告发生在 10-06T03:00Z，**不在 review #5 的窗口内**（该窗口止于 10-05T14:40Z）。
它出现在 review #6，也就是**第一个真正包含它的 review**——没有延迟。
所以「自我写回排挤真实证据、导致外部事实延迟」这个因果我**没有证据**，撤回。

仍然成立的部分：
- review #5 的 11 个 anchor 100% 是我自己的 Summary，这一点是实测；
- review #3 与 #4 的 `anchor_count`（38 / 26）确实大于实际下发（20 / 20），F-017 的截断事实成立；
- 但**截断是否造成过真实证据丢失，本次运行没有证据**。要证明需要一次
  「窗内确有 >20 个候选、且被丢弃的候选里包含外部新事实」的观测，我没有拿到。
  这一条按 **INSUFFICIENT EVIDENCE** 处理，不作为结论。

另记一条与 F-016 无关但同批发现的机制事实：review 窗口并非固定 24 小时，
而是 `window_start = 上一次 review 的 window_end`。#6 的窗口因此是 48 小时。

## F-018 Wake 投递出去的 Resident 回复不落 World，无法被自己检索或引用

- 分类: MECHANISM GAP
- 严重度: **HIGH**
- 场景: 2026-10-04 21:00，Task wake `wake_67e74ffbcc3bd0b845768d0c` 触发，
  我投递了提醒「你爸问的十一回不回无锡，你还没定。明天就六号了，再拖票更难买。真不去也早点跟他说一声。」
  daemon 日志里 `delivery_response` 完整记录，用户 35 分钟后作出决定。
- 实测: 在 `run/world.sqlite` 的 `object_revisions.payload_json` 里
  `LIKE '%再拖票更难买%'` 与 `LIKE '%你爸问的%'` **均返回 0 行**。
  对照：普通对话轮里我说过的「让你有个准备」能查到
  `obs_conv_ai_85849e2ab600b8c6e2dc0b9b` 与 `obs_conv_ai_3f8c4c592101d04b5d3a889d`。
  即：**普通对话轮的 AI 回复会落库，Task/Review wake 投递的 AI 回复不会。**
- 后果（对本次 Review 的实际影响）:
  1. 这是我在这段生活里最有效的一次干预，但它对我自己的记忆**不可见**；
  2. 我因此无法为「带时间锚点 + 给退出选项 → 用户 35 分钟内决定」这条
     真实成立且极有价值的沟通模式记录 CommunicationExperience——
     `record_communication_experience` 要求 `evidence_refs` 指向真实对象，而正面案例无对象可指；
  3. 下一次 review 也不会把这次干预当成 anchor，于是我无法评估它是否可复制。
  这等于**系统性地丢弃了 Resident 主动行为的效果证据**，只保留被动应答的证据。
- 建议: wake 投递的 response 应与普通轮一致地生成 `obs_conv_ai_*` Observation，
  并在其 metadata 上标注 `origin=wake_delivery` 以便区分。

## F-019 MODEL BEHAVIOR：我把一条 Claim 的证据钉到了无关的 Observation 上

- 分类: **MODEL BEHAVIOR**（我的错误，不是 Core 缺陷）
- 严重度: MEDIUM（已自行发现并修复）
- 事实: `clm_8522f237c4a2aaebb8d9145b`（用户决定十一不回无锡）在 2026-10-04 创建时，
  我传的 `evidence_refs` 是 `obs_conv_user_c9c33cd97466e8264d6bfb75`。
  该对象的正文实为「老许来了 说这房子明年可能要卖 让我有个准备 没说要赶我走」——房东条线。
  真正出处是 `obs_conv_user_caa9f3e49dba2624487447d1`（「无锡我不去了 让我妹先看着 我这边走不开」）。
- 成因: 两条 Observation 同在 2026-10-04、同为 `obs_conv_user_*`，
  我在写决策时凭记忆引用了 id 而没有回读正文。id 是 24 位十六进制，肉眼无法校验。
- 为什么值得记: 这类错误**不会报错**。Core 接受任何存在且未过期的 ObjectRef，
  不做语义一致性检查（这是合理的设计边界——语义判断本就该由 Resident 负责）。
  所以它只能靠 Resident 自己复核发现。
- 修复: 2026-10-07 review #6 中 `revise_claim` → rev2，换正确证据，
  并在正文里写明修订原因是证据订正而非结论变更。
- 给自己的规程（已写入 OperationExperience 的适用范围思考）:
  **引用任何 Observation id 之前，先用 `inspect_world_object` 回读一次正文。**
  成本一个 tool round，收益是整条推断链不建立在错证据上。

## F-020 MODEL BEHAVIOR：我从单次观测外推出了不成立的因果，并当场撤回

- 分类: **MODEL BEHAVIOR**
- 严重度: LOW（未污染任何 World 对象，仅进入过 findings 草稿）
- 事实: 我在 F-016 的补强段落里写过——「招标公告在 review #5 的窗口内，
  却被静默截断挤掉，因此延迟了一个 review 周期才被我看到」，
  并据此推出「自我写回正在排挤真实证据」。
- 错在哪: 我没有核对 review #5 的窗口边界就下了因果。
  日志显示 #5 的窗口是 10-04T14:40Z→10-05T14:40Z，
  而招标公告发生在 10-06T03:00Z，**根本不在窗内**。
  它出现在 #6，即第一个真正包含它的 review。没有延迟，也就没有排挤。
- 与 F-019 同属一类错误: 都是**在 id / 时间戳这类不可肉眼校验的量上凭记忆断言**。
  F-019 是记错了 Observation 的正文，F-020 是记错了窗口边界。
- 处置: 已在 F-016 补强段落中原地订正并标注撤回，
  「截断是否造成真实证据丢失」降级为 INSUFFICIENT EVIDENCE。
- 规程: 任何关于「谁在谁的窗口内 / 谁先于谁」的因果陈述，
  必须先打印两侧的原始时间戳再写，不得凭记忆。
