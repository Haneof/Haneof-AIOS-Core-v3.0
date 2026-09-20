# AIOS v3.0 AI认知执行运行时宪法

## 一、定义

AI认知执行运行时是 AIOS 将多维世界、智能索引、智能推荐、上下文中控、外部能力和大模型连接成持续运行系统的执行层。

它不是第二个认知大脑。

它的职责是：

> 给 AI 一个可靠、可追溯、可继续扩展的世界驾驶舱，并允许 AI 自主观察、检索、判断、行动、写回和修正。

---

## 二、三类核心职责

### 2.1 世界

多维世界负责长期保存：

- Observation；
- Entity；
- Event；
- Evidence；
- Claim；
- Relationship；
- Summary；
- Goal；
- Task；
- Action；
- Outcome；
- AI经验；
- Conversation。

### 2.2 智能世界索引

索引负责：

> 快速找到世界。

索引返回候选锚点、总结、事件、关系和证据。

索引不得替 AI 完成最终高阶判断。

### 2.3 AI认知执行运行时

运行时负责：

- 接收当前会话 / Wake / Task；
- 调用智能推荐；
- 调用上下文中控；
- 调用模型；
- 向模型提供主动搜索能力；
- 执行动作；
- 收集 Outcome；
- 组织世界写回；
- 触发修正、总结与索引更新。

---

## 三、模型调用前的系统准备

每次模型推理前，AIOS 先执行系统级准备：

当前输入 / Wake
↓
当前会话主题状态
↓
智能记忆推荐
↓
必要时调用智能世界索引 / 全维投影
↓
模型上下文中控
↓
形成最小必要上下文包
↓
模型开始推理

系统前置推荐是加速器，不是认知结论。

---

## 四、AI 保留主动世界搜索权

系统已做前置推荐，不代表模型只能使用这些内容。

当 AI 判断：

- 信息不足；
- 存在实体歧义；
- 需要原始证据；
- 需要比较旧 Claim；
- 需要更长时间范围；
- 需要跨维观察；
- 需要查找反证；

AI必须能够继续调用：

- search_world；
- focus_entity；
- search_timeline；
- follow_relation；
- retrieve_original_observation；
- inspect_evidence；
- compare_claims；
- expand_recall；
- request_all_dimensions_projection。

---

## 五、标准能力闭环

运行时应支持以下逻辑闭环，但不得强迫模型输出固定思维步骤：

WAKE / USER INPUT
↓
SYSTEM PREPARE
↓
MODEL INTERPRET
↓
必要时 SEARCH / FOLLOW / COMPARE / PROJECT
↓
MODEL DELIBERATE
↓
RESPOND / ACT / SILENCE
↓
OUTCOME
↓
WORLD WRITEBACK
↓
REVISION / CALIBRATION
↓
SUMMARY / INDEX UPDATE
↓
WAIT

模型可以跳过、重复或重新排序搜索动作。

不得把该图实现为固定 Chain-of-Thought 模板。

---

## 六、最小上下文原则

每次模型调用只装配当前真正必要的信息。

典型组成：

- AI身份连续性；
- 当前输入；
- 最近会话必要片段；
- 当前主题；
- 当前任务 / 目标；
- 相关历史推荐；
- 当前有效 Claim / Relationship；
- 必要世界锚点；
- 可用 Capability；
- token预算。

禁止每次通读完整人生。

---

## 七、AIOS能力必须可组合

运行时向 AI 提供语义能力，而不是给每个场景写死流程。

至少应逐步具备：

observe_current_world  
search_world  
focus_entity  
search_timeline  
follow_relation  
retrieve_original_observation  
inspect_evidence  
compare_claims  
expand_recall  
request_all_dimensions_projection  
form_claim  
revise_or_retract_claim  
commit_event  
update_user_understanding  
update_relationship_understanding  
record_ai_self_reflection  
record_communication_experience  
record_operation_experience  
create_or_update_task  
execute_capability  
inspect_outcome  
respond  
silence

---

## 八、世界写回

一次模型运行结束后，不是所有生成文本都进入世界。

运行时只提交具有长期价值的世界对象候选。

事实类内容必须有真实来源。

认知类内容必须以 Claim / Understanding / Experience 等可修正形式存在。

AI不得把自己的猜测伪装成 Observation。

---

## 九、AI自身世界统一原则

AI身份、AI关系理解、AI沟通经验、AI操作经验、AI策略经验、AI错误与反思均属于统一多维世界中的 AI维度。

不得再建立一个与世界存储体系平行的独立 AI Self 真相库。

---

## 十、确定性系统与AI的边界

确定性系统可以强制：

- Schema；
- 引用；
- 幂等；
- 权限；
- 硬安全边界；
- token / latency / storage预算；
- 状态机合法性；
- 索引一致性。

确定性系统不得替 AI 判定：

- 用户是什么人；
- 用户当前心理状态；
- 两件事之间的真实因果；
- 关系亲密度应该是多少；
- 应该创建哪个高阶维度；
- 什么表达一定适合这个用户。

---

## 十一、可回放性

每次运行必须可审计：

- 为什么触发；
- 系统前置推荐了什么；
- 模型调用了哪些世界能力；
- 读取了哪些锚点；
- 执行了什么动作；
- Outcome 是什么；
- 写回了什么；
- 哪些 Claim 被修正；
- 哪些索引 / Summary 被更新。

不要求保存模型私有思维链。

---

## 十二、根定义

> **AIOS 负责把世界和能力交到 AI 手里；AI负责理解和驾驶；系统负责把运行结果可靠写回世界，使下一次 AI 面对的是已经成长过的世界。**

