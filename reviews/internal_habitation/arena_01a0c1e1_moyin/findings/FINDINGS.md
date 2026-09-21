
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
