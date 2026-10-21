# 身份连续性：上下文耗尽后仍然是同一个 AI

> 决策者的原话：「主要的问题是一个大模型的上下文窗口满了后，无论是换模型还是新的模型接手，能一直给人的感觉是同一个 AI。」

这份文档记录这个问题在 AIOS 3.0 里的机械成因、修法、以及"不做什么"的边界。

## 一、为什么"换厂商 key"不解决问题

换一个厂商的模型来测试"接得上"，测的是**模型可替换性**，不是**身份连续性**。任何足够强的模型都能回答"我在杭州做手环"，因为它当轮能读到这句话。

真正的问题只在一种时刻暴露：**那句话已经不在上下文里了**。此时：

- 换模型 → 新模型看到的是出厂人设 + 最近几轮 + 若干事实卡片
- 不换模型 → 同一个模型同样只看到这些

两者表现一致，都像"刚认识的 AI"。所以问题不在模型侧，在**递给模型的东西**。

## 二、实测：断在哪一层

用真实 `FusedTurnRuntime` + 真实 `ContextController` + 真实 provider（网络调用打桩），跑 10 轮：第 1 轮用户交代身份与偏好，第 2–9 轮全是无关闲聊，第 10 轮问「我们上次说到哪了？」

修复前的实际提示词（2811 字符）：

```
You are the AIOS 3.0 symbiotic mind on an ultra-compact wearable band.
CONSTITUTIONAL RULES: ...
ACTIVE COCKPIT CONTEXT:
current_topic: 我们上次说到哪了？
RECENT CONVERSATION:
[turn 7] user: 推荐一部纪录片。
[turn 8] user: 咖啡因多久代谢完？
[turn 9] user: 珠峰有多高？
AVAILABLE CAPABILITIES: ...
```

`老王`、`23cm`、`东莞`、`敬语`——全部 MISSING。与此同时，cockpit 里其实**有**这些数据，只是没递出去。

三层断点，逐层独立：

| 层 | 现象 | 根因 |
|---|---|---|
| 渲染层 | `ai_identity` 整块消失 | 提示词构造只保留标量；`ai_identity` 是 mapping，被静默丢弃 |
| 渲染层 | 轮次摘要整块消失 | `conversation_summaries` 有渲染入口但没有渲染函数，模型只能靠主动调 `list_conversation_summaries` 去捞，而规则 0 明确劝它别浪费工具轮次 |
| 写入层 | 一句话里的多件事只能记住一件 | 证据集 id 由 `(subject, dimension, member_refs, learned)` 内容寻址。同一轮、同维度、同证据的第二条 claim 推出**同一个** evs id，写入时又硬编码 `revision=1`，直接 `VERSION_CONFLICT` |

第三条最隐蔽：模型以为记住了三件事，实际只有一件落库，而且失败是静默的。

## 三、修法

### 3.1 身份锚（CONTINUITY ANCHOR）

新增一个**每轮必带、优先级最高**的段落，内容全部来自世界库或 Core 自己的计数器：

```
CONTINUITY ANCHOR (durable world-store evidence about this user and this
relationship — evidence, not a script; you still decide what it means):
- (relationship) 用户要求不用敬语、直接说结论 [clm_a9bed04f@1]
- (user) 用户在做 23cm 柔性屏手环 [clm_160c6682@1]
- (user) 供应链卡在东莞那家供应商 [clm_2d0f344a@1]
- (user) 用户叫老王 [clm_40be38ed@1]
- self-state: posture=old_friend, rapport=0.5, tier=亲和陪伴 (Old Friend)
```

数据源是既有的 `AIWorldCognition.core_context()`——它本来就只为 `user_understanding / relationship / self` 三个域、且带 `core_context` 标签的 claim 服务，设计意图正是"身份/关系连续性"。之前没有渲染器，所以这份设计从未生效。

**每条都带 `object_id@revision`**。模型拿到的不是一段"你是个温柔的朋友"的剧本，而是可追溯、可反驳、可修订的证据。

### 3.2 恒常约束（STANDING CONSTRAINTS）

`ai_self` 里本来就有 5 条伦理不变量（反爹味、反谄媚、历史不可篡改、不做题 UI、生命优先），`get_mind_summary()` 也返回了，但 `turn_runtime` 只取了 3 个标量，把这 5 条丢了。

现在它们作为独立段落紧跟角色定义，**不参与 token 预算裁剪**。一段对话再长，也不能把"我不会变成另一种 AI"挤出去。

### 3.3 已覆盖历史（WHAT WE ALREADY COVERED）

轮次摘要有了渲染器，位置在最近对话**之前**（更早、更压缩的先讲），并明确标注"这是索引不是原文，需要原话用 `drill_down_conversation`"。这守住了原设计的意图：摘要是指针，不是事实。

### 3.4 长期记忆纪律

提示词里新增一段，告诉模型什么该固化、怎么固化、以及不固化的后果：

> 任何跨越本次对话仍然成立的东西——用户是谁、长期在做的事、稳定偏好、约定的相处方式、你许下的承诺——只有用 `commit_ai_world_claim` 记下、并打 `core_context` 标签，才能在后续轮次进入你的身份锚。没有这个标签的 claim 不会出现在锚里。

同时约束频率：**首次陈述或首次变化时记一次**，不重复记锚里已有的，不把闲话升级成长期事实。

### 3.5 同一轮多事实写入

证据集改为**内容寻址复用**：id 相同且成员集合相同 → 复用已有 revision，不重复写。依赖边同理。这样"我叫老王、做 23cm 手环、别用敬语"三条能一次全部落库。

### 3.6 世界地图与本届接地

护栏测试（见 3.7）又揪出两个"每轮都构建、从未递出"的字段：

**`world_map`（L0 世界目录）** —— 模型完全不知道可检索的世界有多大、哪几个维度活跃，每次召回都从零开始。现在渲染成结构目录（`directory_only: true` / `semantic_conclusions: false`），并列出展开路线：

```
WORLD MAP (L0 directory — what exists, not what it means; open a dimension
only when the turn needs it):
3 active dimensions
- dim:user_ai_interaction: 19 objects, observation
- dim:ai_communication_experience: 9 objects, communication_experience
expand with: semantic_recall=search_world, broader_recall=expand_recall, ...
```

**`task_context` 里的两条承重项** —— 其余（`topic_state`、`cognitive_policy_context`）是 Core 自己的门控决策和策略参数，属于审计材料，不递给模型：给它看只会让它跟门控吵架。

```
THIS TURN — GROUNDING (what you can cite, and how to reach the rest of the history):
current user observation: {object_id: obs_conv_user_..., revision: 1} — cite this
  as evidence when you persist a durable claim this turn
history available: 3 verbatim turns in view, 0 round summaries; use
  list=list_conversation_summaries, search=search_conversation_summaries,
  exact words=drill_down_conversation — check before saying you do not remember
```

这两条各自解决一个真实病灶：

- `current_user_observation_ref`：模型想固化认知时**必须**引用这条证据编号。以前它拿不到，只能先搜索或猜——这是"只记录不理解"的一个机械原因，不是意愿问题。
- `conversation_continuity`：模型不知道有摘要索引和原文下钻这两条路，就会直接说"我不记得"。知道路，它就会去查。

### 3.7 护栏：提示词覆盖测试

这一整类缺陷已经复发三次（`9ce11baf` 修 2/3、`26c9c481` 补 2 个、本轮再补 2 个），每次修的都是"这次刚好被看见的字段"。所以补的不是补丁，是护栏。

`tests/runtime/test_prompt_cockpit_coverage.py` 的做法是**给每个 cockpit 字段塞一个唯一哨兵值**，断言哨兵出现在实际外发的 messages 里：

- 不依赖具体渲染格式，新增字段自动被覆盖
- 字段被丢掉时立刻红，哪怕没人想到去看它
- 第二个测试在 `ModelContextBundle` 新增字段却没登记时直接失败——缺陷在**引入的当下**被发现，而不是三轮之后

只有三个字段被豁免：`token_budget` / `estimated_tokens` / `truncated`。它们是预算算术，不是上下文；把它们塞进提示词只会浪费它们所描述的预算。

## 四、边界：刻意不做的事

1. **不让 Core 生成人设散文。** 身份锚只列证据和引用，怎么理解由模型判断。写成"你是一个温暖的老朋友"会漂移、会不可审计，也违反"Core 不替模型判断"。
2. **不每轮全量加载画像。** 锚只取每个域最近 3 条带标签的 claim，有界。
3. **不把摘要当真相。** 摘要只作索引，原话仍走 `drill_down_conversation`。
4. **不在没有证据时造连续性。** 世界库里没有 `core_context` claim 时，锚段整段不出现，而不是给一段默认人设。测试 `test_absent_identity_creates_no_continuity_block` 锁这一条。

## 五、验证

修复后同一场景（第 10 轮，第 1 轮原话早已滚出窗口）：

```
CONTINUITY CHECKS
has STANDING CONSTRAINTS           PRESENT
has CONTINUITY ANCHOR              PRESENT
knows user name 老王                 PRESENT
knows product 23cm                 PRESENT
knows supply chain 东莞              PRESENT
knows tone preference 敬语           PRESENT
anchor before recent turns         YES
```

同时断言原话确实不在窗口内（`[turn 1]` 不出现、`请记住：我叫老王` 不出现），确保测的不是"上下文没满"。

测试文件：

- `tests/runtime/test_identity_continuity_prompt.py`（7 项：渲染、顺序、不重复、不伪造、超长截断保头、端到端耗尽）
- `tests/runtime/test_prompt_cockpit_coverage.py`（12 项：9 个字段哨兵 + 字段登记 + 记账豁免 + 空接地不产段）
- `tests/integration/test_v3_multi_claim_same_turn.py`（3 项：同域多事实、跨域独立、幂等重试）

三组都做了反向验证：撤掉渲染修复红 4 项、撤掉写入修复红 1 项、撤掉世界地图/接地渲染红 2 项，报的都是原始错误。

## 六、已知未覆盖

1. **摘要链的触发粒度。** `summary_chunk_turns` 默认 12，意味着第 9–11 轮处于"最近 8 轮 + 尚无摘要"的空档。身份锚覆盖的是稳定事实，不是这段空档里的临时话题。
2. **模型是否真的会 commit。** 3.4 是提示，不是强制。真实模型会不会把"我在杭州"固化成 claim，需要真实端点取证，不能靠打桩推断。
3. **身份锚的容量上限。** 每域 3 条是当前取值。长期运行后哪些 claim 该留在锚里、哪些该下沉，需要真实的 30 天对话数据才能定，现在定是拍脑袋。
4. **C15 的验收口径没有同步。** C15 R5/R6 判 VALID 时，provider 是脚本化的，没有任何断言检查"模型实际收到的提示词内容"。本文件的修复让那条断言第一次存在（见测试），但 C15 的收据本身仍是历史记录，没有回填。补遗应由治理层决定，不应由实现方自行改写历史收据。
