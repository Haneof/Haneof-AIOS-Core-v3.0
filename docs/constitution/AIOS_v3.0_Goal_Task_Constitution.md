# AIOS v3.0 目标与任务机制宪法

## 一、定义

Goal 与 Task 负责把 AIOS 的世界理解延伸到未来。

Goal 回答：

> 想长期实现什么结果？

Task 回答：

> 为这个目标，下一件具体需要做的事情是什么？

Goal 与 Task 必须分离。

---

## 二、Goal

Goal 是长期方向，不是一次动作。

Goal 必须具有：

- 来源；
- 标题与说明；
- Evidence；
- 当前状态；
- 可理解的成功标准；
- 置信度；
- revision 历史。

Goal 来源可以包括：

- 用户明确提出；
- AI 基于用户世界推断；
- AI 自身运行目标；
- App / 外部系统输入。

来源不同不代表自动授权等级相同。

尤其：

> **AI推断出一个 Goal，不等于用户授权了任何外部副作用。**

---

## 三、Goal 生命周期

允许的基本状态：

```text
Proposed
↓
Active
↔
Paused

Active
↓
Achieved / Abandoned / Unknown
```

每次状态变化都向前创建新 revision。

旧 Goal revision 永久保留。

Goal 的状态改变必须有 pinned Evidence 和原因。

---

## 四、Task

Task 是可以被调度、等待、执行和结束的具体工作对象。

Task 至少包含：

- task type；
- 当前 state；
- title；
- reason refs；
- 可选 Goal ref；
- priority；
- 可选时间条件；
- dependency refs；
- next step；
- completion / cancel condition；
- execution refs；
- outcome refs。

Task 不是聊天 TODO 字符串。

---

## 五、Task 状态

典型状态包括：

```text
Draft
↓
Ready
↓
Running
↓
Waiting Time / Waiting Evidence / Waiting User / Waiting Result / Blocked
↓
Ready / Running
↓
Completed / Failed / Expired / Cancelled
```

状态变化必须使用同一 task object_id 的新 revision。

终态不删除历史。

---

## 六、Task 完成必须有真实 Outcome

AI 不得仅通过一句：

“任务完成了”

就把现实任务改成 Completed。

当 Task 涉及现实执行结果时：

```text
Action
↓
Outcome
↓
Task Completed / Failed
```

Completed / Failed 必须引用实际 Outcome。

这样 AIOS 能回答：

- 为什么认为任务完成；
- 哪个 Action 执行了；
- 平台返回了什么结果；
- 后来为什么又发现失败。

---

## 七、当前用户输入先进入世界

用户本轮输入属于世界事实。

在 Resident Model 开始本轮推理前，当前用户输入必须先作为 Observation 写入统一世界，并获得 pinned ref。

因此同一轮可以形成：

```text
用户说：
“明天下午提醒我发周报”
↓
Observation@1
↓
Resident AI
↓
Goal / Task
     Evidence = 当前用户 Observation@1
```

禁止让本轮新 Goal / Task 只能引用“上一轮历史”，从而失去当前请求的直接证据。

AI回复在模型完成后再作为对应 Assistant Observation 写入。

---

## 八、Scheduler 的边界

Scheduler 是确定性基础设施。

Scheduler 可以：

- 判断时间是否到达；
- 判断 Task deadline 是否已经过期；
- 生成 Wake；
- 把 WAITING_TIME Task 唤醒为 READY；
- 做去重与幂等；
- 记录 wake 原因。

Scheduler 不可以：

- 自己发明新 Goal；
- 因时间到达自动生成高阶用户意图；
- 替 AI 判断任务“有没有意义”；
- 替用户批准外部副作用。

根原则：

> **AI决定为什么做；Scheduler只负责什么时候该重新看这件事。**

---

## 九、统一世界原则

Goal、Task、Wake、Action、Outcome 都是 WorldObject。

禁止建立独立 TODO 数据库作为第二真相源。

工作队列或调度索引可以存在，但只能是可重建投影。

---

## 十、与 AI认知的关系

Goal / Task 可以引用：

- 用户事实；
- Event；
- Claim；
- AI User Understanding；
- Relationship；
- Cognitive Boundary；
- Summary。

Outcome 又可以反向成为：

- User Understanding；
- Strategy；
- Calibration；
- Relationship；
- AI Self；

的新 Evidence。

因此未来行为与长期认知共享同一个世界。

---

## 十一、禁止事项

禁止：

1. 把 Goal 与 Task 合成一个 TODO 文本；
2. 无 Evidence 创建长期目标；
3. 任务终态删除旧 revision；
4. Scheduled Task 通过模型不停轮询时间；
5. Scheduler 自动生成用户心理结论；
6. 现实任务没有 Outcome 就宣布 Completed；
7. 用独立任务数据库绕开 WorldStore；
8. 把 AI推断 Goal 解释成用户外部授权。

---

## 十二、根定义

> **Goal 管方向，Task 管可执行未来；二者都属于世界，但现实是否真的完成，最终由 Outcome 说话。**
