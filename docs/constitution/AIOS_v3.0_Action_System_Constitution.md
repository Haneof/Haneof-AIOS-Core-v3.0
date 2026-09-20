# AIOS v3.0 行动机制宪法

## 一、行动定义

Action 是 AI 基于世界理解和 Task，对现实产生影响的一次具体副作用提案与执行记录。

Action 不是事实输入，也不是 Claim。

例如：

- 发消息；
- 发邮件；
- 创建日历事件；
- 控制设备；
- 提交订单；
- 修改外部系统；
- 调用具有现实副作用的 App 能力。

---

## 二、核心分层

AIOS 必须把三件事分开：

```text
Resident AI
↓
Action Proposal

独立授权层
↓
Authorized Dispatch Envelope

平台 / Connector
↓
真实副作用
↓
Outcome
```

Resident AI 能提出 Action。

Resident AI 不能给自己授权。

AIOS Core 也不直接假装已经执行外部动作。

---

## 三、Action Proposal

Action Proposal 必须引用：

- 当前 RUNNING Task；
- pinned Evidence；
- action type；
- payload；
- 可选 expected outcome。

初始状态：

`PROPOSED`

Proposal 进入统一 WorldStore。

它表达：

> AI认为这一步值得做。

它不表达：

> 这一步已经得到用户/平台授权。

---

## 四、独立授权

外部副作用必须经过 capability-specific authorization。

授权必须：

- 针对精确 Action revision；
- 引用 pinned authorization Evidence；
- 记录 authorized_by；
- 记录 authorization time；
- 由 Resident Model 之外的可信边界确认。

授权成功后产生新的 Action revision：

```text
Action@1 PROPOSED
↓
Permission Gate
↓
Action@2 SUBMITTED
```

同时向平台输出 Dispatch Envelope：

- execution_id；
- action type；
- payload；
- expected outcome；
- authorization refs。

---

## 五、execution_id

每个外部 Action 必须有稳定 execution_id。

平台 Connector 应将 execution_id 作为外部幂等键。

AIOS Core 不得因为：

- 超时；
- 进程重启；
- 模型再次请求；

就自动重复执行已经 SUBMITTED 的 Action。

如果 Action 已经进入 SUBMITTED，而结果未知：

> 默认等待 / reconcile，而不是盲目重试现实副作用。

---

## 六、Core 与平台的边界

Core 负责：

- Action Proposal；
- authorization state；
- dispatch envelope；
- execution identity；
- Outcome 接收；
- 世界写回；
- Dependency；
- Task / cognition 后续更新。

平台负责：

- 真正调用 Gmail / Slack / Calendar / App / Device / OS；
- 外部 API 权限；
- provider-specific idempotency；
- 获取真实 provider result。

因此 Core 保持平台无关。

---

## 七、Outcome

真实执行结束后，平台必须把结果写回 Outcome。

Outcome 至少记录：

- action_ref；
- outcome_state；
- payload；
- 可选外部 Evidence；
- execution_id；
- 时间。

基本结果：

- completed；
- failed；
- outcome_unknown。

失败同样必须进入世界。

结果未知也必须诚实记录，不得伪装成功。

---

## 八、Action revision

典型链：

```text
Action@1  PROPOSED
↓
独立授权
↓
Action@2  SUBMITTED
↓
平台执行
↓
Action@3  COMPLETED / FAILED / OUTCOME_UNKNOWN
↓
Outcome@1
```

旧 revision 永久保留。

---

## 九、与 Task 的关系

Action 必须属于当前 Task。

Task 不因为 Action 被提出就自动完成。

Task 只有在看到实际 Outcome 后，才能进一步由 AI / workflow 判断：

- Completed；
- Failed；
- Waiting Result；
- Ready for next step。

---

## 十、与认知学习的关系

Outcome 可以作为长期认知 Evidence。

例如：

```text
Action：主动提醒用户
↓
Outcome：用户明确表示这种提醒有帮助
↓
Communication / Strategy / Calibration Evidence
↓
未来 Strategy Claim
```

反之，失败 Outcome 也必须被学习。

---

## 十一、禁止事项

禁止：

1. Resident Model 直接拥有通用 external execute 权限；
2. Action Proposal 自动等于授权；
3. 用“模型说执行成功了”代替 Outcome；
4. SUBMITTED Action 无幂等保护自动重试；
5. 执行失败静默丢弃；
6. outcome_unknown 被当作 completed；
7. 平台结果只写运行日志、不写世界；
8. 为每个 App 建第二套行动真相库；
9. 让 Scheduler 替 AI 决定行动意义；
10. 用测试 fake executor 冒充生产授权机制。

---

## 十二、根定义

> **AI负责提出值得做的事；授权层决定能不能做；平台真正去做；Outcome告诉世界到底发生了什么。**
