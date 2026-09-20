# AIOS v3.0 维度注册与生命周期宪法

## 一、定义

维度是 AIOS 多维世界中的独立观察轴。

所有维度平级存在，不形成数据库父子层级。

维度可以来自：

- 现实来源型事实；
- 长期事件结构；
- AI对用户的长期理解；
- AI自身认知；
- 多维世界长期运行后形成的新观察需求。

维度不是“标签越多越好”。

维度存在的目的只有一个：

> 为 AI 增加长期、有价值、可持续维护的世界观察能力。

---

## 二、谁决定新维度的意义

新维度的语义必要性由 Resident AI 判断。

系统不得使用固定代码回答：

- 这个模式是不是“心理维度”；
- 两个来源是否足够；
- 三天是否足够；
- 30天是否应该晋级；
- 70%准确率是否自动等于有效维度。

旧实验中的：

- 2 domains；
- 3 days；
- 30 day trial；
- 70%；
- 固定心理维度白名单；

均不得作为当前认知真理。

这些历史参数如未来有工程价值，只能作为可审计 Cognitive Policy 候选，不能替 AI 判断维度意义。

---

## 三、系统负责什么

系统只负责确定性注册机制：

- Schema；
- Evidence refs 必须存在且 pin revision；
- dimension_key 精确唯一；
- 对象版本；
- 生命周期状态机合法；
- 原子事务；
- 幂等；
- 资源与权限硬边界；
- 索引同步；
- 历史不可静默删除。

系统可以拒绝结构非法提案。

系统不能因为自己“觉得这个维度没意义”而替 AI 做语义否决。

---

## 四、AI提出候选维度时必须说明

Dimension Proposal 至少包含：

- dimension_key；
- 名称；
- 描述；
- 预期数据形态；
- Evidence；
- 为什么现有维度不足；
- 为什么该观察轴具有时间连续性；
- 对用户有什么帮助价值；
- 维护成本为什么值得；
- 当前置信度；
- 未来如何更新。

这些字段不是固定评分公式。

它们是为了让 AI 的决定可审计、可回看、可修正。

---

## 五、Candidate 不等于“已经证明”

系统接受 Candidate 只代表：

> AI 提出了一个有 Evidence、结构完整的新观察轴候选。

Candidate 本身不证明该维度有长期价值。

真正价值必须通过后续真实世界运行继续验证。

因此单个 Evidence 也可以合法形成 Candidate，只要 AI 明确承认当前只是候选。

这与“单个 Evidence 自动成为 Active”完全不同。

---

## 六、生命周期

统一生命周期允许：

```text
Candidate
↓
Trial
↓
Active
↓
Low Activity / Dormant
↓
Reactivated / Active

Active / Low Activity / Dormant
↓
Merged / Split / Revised / Archived

Candidate / Trial
↓
Rejected
```

生命周期状态用于管理世界，不用于给 AI 写死认知答案。

---

## 七、状态变化必须有 Evidence

任何重要生命周期变化都必须记录：

- 前一状态；
- 新状态；
- AI给出的原因；
- pinned Evidence；
- 时间；
- 相关维度（merge / split 时）。

例如：

```text
dim:learning_ability@1  Candidate
↓
真实运行证据
↓
dim:learning_ability@2  Trial
↓
更多 Evidence / Outcome
↓
dim:learning_ability@3  Active
```

旧 revision 永久保留。

---

## 八、已有维度检查

AI在提出新维度前应首先检查现有 Dimension Definitions。

这一步的目的不是让系统做语义相似度裁决，而是让 AI 自己回答：

> 现有观察轴是否已经足够表达我想长期观察的内容？

系统只做精确 dimension_key 冲突检查。

语义上“看起来像重复”不能由字符串算法直接否决。

---

## 九、Merge / Split

### Merge

当 AI 认为多个维度长期观察后实际表达的是同一个更合适的观察轴，可以提出 merge。

历史维度不得删除。

新世界必须保留：

- 被 merge 的维度；
- merge 时间；
- Evidence；
- 目标维度；
- 旧 Summary / Claim / Membership 历史。

### Split

当一个维度长期运行后被证明混合了多个应独立观察的概念，可以 split。

同样必须保留历史来源与 Evidence。

---

## 十、Dormant 与 Archived

Dormant 表示：

> 当前暂时不值得持续高频维护，但未来仍可能重新激活。

Archived 表示：

> AI认为该维度已经不值得继续作为当前活动观察轴。

Archive 不删除历史。

历史世界仍然可以回答：

- 这个维度为什么曾被创建；
- 当时依据是什么；
- 为什么后来停止维护。

---

## 十一、与统一世界的关系

DimensionDefinition、DimensionDerivation、DimensionMembership、EvidenceSet 和 Dependency 都属于同一个 WorldStore。

禁止再建独立 dimension registry 真相数据库。

维度定义同样拥有：

- revision；
- source refs；
- Dependency；
- search index；
- current view；
- historical view。

---

## 十二、与AI认知的关系

新高阶维度通常承载长期 Claim / Summary。

例如：

```text
学习事实
↓
Event / Claim / Summary
↓
AI长期观察
↓
Dimension Proposal: dim:learning_ability
↓
Trial
↓
Active
↓
未来新的能力 Claim 持续进入该观察轴
```

创建新维度不能反向修改原始学习事实。

---

## 十三、多Agent测试要求

正式验证“AI会不会创建正确维度”时，不允许给 Resident AI 一个：

`expected_new_dimension = learning_ability`

然后做字符串匹配。

必须在隐藏虚拟人生中观察：

- AI是否在真实长期世界中自主发现观察需求；
- 是否先检查已有维度；
- 是否有充分 Evidence；
- 是否知道 Candidate 只是待验证；
- 后续是否会 activate / revise / reject / merge / archive；
- 新维度是否真的提高未来理解和帮助质量。

确定性 pytest 只验证注册机制，不证明 AI 的维度认知能力。

---

## 十四、根定义

> **AI决定“值不值得多一条观察世界的轴”；系统只负责让这条轴有证据、有身份、有生命周期、有历史，并且不会把世界弄乱。**
