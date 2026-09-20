# AIOS v3.0 周期复盘与AI成长机制宪法

## 一、定义

周期复盘机制负责：

> 在没有用户主动发起新对话的情况下，让 Resident AI 按明确的调度边界重新观察已经发生的世界，并判断过去的理解、行动、策略和经验是否需要修正或沉淀。

它不是第二个 AI。

它也不是一套程序化“成长评分器”。

---

## 二、核心闭环

```text
统一 World
├─ Observation / Event / Summary
├─ Claim / AI认知
├─ Goal / Task
├─ Action / Outcome
└─ Experience / Prediction
        ↓
确定性 Review Scheduler
只判断：现在是否到复盘时间
        ↓
选择有限的 pinned world anchors
        ↓
同一个 Resident Cognitive Runtime
        ↓
Resident AI 自己观察 / 搜索 / 比较 / 判断
        ↓
可选择：
- 什么都不改
- revise / retract 旧 Claim
- 写新的 evidence-grounded Claim
- 写 Calibration / Strategy / Self cognition
- 沉淀 OperationExperience
        ↓
Evidence + Dependency + Revision
        ↓
同一个 World 继续增长
```

---

## 三、Scheduler 的职责边界

Scheduler 可以确定性决定：

- review interval；
- lookback window；
- 每次最多给多少候选；
- 每种 object type 的机械数量上限；
- 当前 review 是否已经被领取；
- review 是否已经完成；
- crash 后是否需要恢复未完成 review。

这些属于 Engineering Parameter。

Scheduler 不得决定：

- 用户成长了多少；
- AI成长了多少；
- 某个策略更好；
- 某个 Outcome 意味着什么；
- 某个旧 Claim 一定错误；
- 是否应该改变人格或关系；
- 是否应该修改 Cognitive Policy。

这些判断属于 Resident AI。

---

## 四、Review Wake

每次周期复盘必须有世界内的 Wake 作为审计锚点。

基本生命周期：

```text
NEW
↓
RUNNING
↓
COMPLETED
```

如果本周期没有任何可复盘的新世界变化：

```text
SUPPRESSED
```

SUPPRESSED 表示：

> 调度器检查过，但没有必要调用模型。

不得为了维持“AI一直在思考”的幻觉而空转模型。

---

## 五、Crash Recovery

Review 在调用模型前必须先从 NEW 原子推进到 RUNNING。

RUNNING review 是可恢复的。

如果进程在模型执行期间崩溃：

- 不创建第二套 review；
- 不丢失原 review；
- 重启后从同一个 Wake revision 恢复；
- 最终完成后再推进到 COMPLETED。

这样避免两个 worker 同时复盘同一个窗口。

---

## 六、Review Input

Review 输入由 pinned world anchors 组成。

允许包含：

- Observation；
- Summary；
- Claim；
- Goal；
- Task；
- Action；
- Outcome；
- OperationExperience；
- CommunicationExperience；
- Prediction。

Scheduler 只做：

> “这些对象在本窗口内发生或更新过。”

它不做语义排序。

---

## 七、上下文预算

Review 不得把整个世界直接塞进模型上下文。

主上下文只提供：

- review id；
- window；
- anchor count；
- review instruction；
- 读取 anchor 的公共能力入口。

Resident AI 按需分页读取 anchors，再使用：

- search_world；
- inspect_world_object；
- ALL_DIMENSIONS；
- AI World；
- 其他公共世界能力；

继续深入。

因此：

> **复盘共享智能索引和同一个 Cognitive Runtime，不建立专用 review 大脑或专用记忆库。**

---

## 八、OperationExperience

OperationExperience 用于保存：

> AI 对真实操作案例形成的、未来可能复用的方法经验。

最小要求：

- problem type；
- method path；
- result summary；
- 至少一个 pinned real case ref；
- positive / negative cases；
- applicability；
- 可选 cost；
- misses；
- experience state。

经验不能凭空产生。

合法：

```text
真实 Action
↓
真实 Outcome
↓
AI复盘
↓
OperationExperience
```

也允许对检索、沟通、认知操作等非外部 Action 方法形成经验，但仍必须引用真实案例对象。

---

## 九、Outcome 与经验

外部行动经验不得用模型自述代替真实 Outcome。

如果 AI 声称：

> “这个外部行动方式有效。”

其 Evidence 必须能回到真实世界结果。

Outcome unknown 不能伪装成 completed。

失败 Outcome 同样可以形成 valuable experience。

---

## 十、Calibration

周期复盘可以促使 AI 形成 Calibration cognition。

例如：

```text
旧判断
↓
后续真实事实 / Outcome
↓
发现偏差
↓
revise / retract
↓
Calibration Claim
↓
未来相似问题重新使用
```

Calibration 不等于固定准确率排行榜。

机械统计只能作为 Evidence。

---

## 十一、Strategy

周期复盘可以发现某种方法在真实结果中更有效。

但：

> Strategy Claim ≠ 自动修改系统运行参数。

真正修改 Cognitive Policy 时，仍必须遵守：

- scope；
- version；
- evidence；
- evaluation window；
- rollback；
- Hard Boundary 不可修改。

---

## 十二、禁止自我复盘死循环

Review 自己产生的 Wake、维护对象和同一完成时刻的 review writeback，不得机械触发下一次立即 review。

系统至少必须保证：

- review interval；
- 完成边界后的新变化才进入下一 window；
- 没有新 world changes 时不调用模型；
- maintenance write 不制造无限 maintenance wake loop。

AI可以在未来有新 Evidence 时重新审视过去经验。

但程序不得因为“刚复盘过”就立刻再复盘一次。

---

## 十三、与用户对话分离

Periodic Review 不是用户对话。

因此 review scheduler 的内部 instruction：

- 不写入用户/AI对话 Observation；
- 不伪造成用户说过的话；
- 不进入当前 conversation turn index。

Review 的审计事实由：

- Wake；
- capability history；
- Claim / Experience writeback；
- world revision；

承担。

---

## 十四、与 P16 多Agent入住测试的关系

P15 的确定性 pytest 只能证明：

- 调度正确；
- Evidence pinned；
- Runtime 接线正确；
- revision 正确；
- crash 可恢复；
- 无循环；
- 无第二数据库。

它不能证明：

> AI真的会从一段人生中形成好的复盘和成长。

真正的认知质量必须进入 P16：

```text
隐藏虚拟人生
↓
多个真实模型长期入住
↓
自然形成事实 / 认知 / Goal / Action / Outcome
↓
周期 Review
↓
观察模型是否自主发现错误、修正理解、沉淀经验
↓
找机制 bug / 认知 bug / 过拟合 / 自我强化问题
```

禁止把“expected answer = 某句固定文字”当成 AI 成长 Gate。

---

## 十五、根定义

> **Scheduler 只决定什么时候回头看；世界提供真实经历；Resident AI 决定这些经历意味着什么；所有成长必须重新写回同一个可追溯、可修正的世界。**
