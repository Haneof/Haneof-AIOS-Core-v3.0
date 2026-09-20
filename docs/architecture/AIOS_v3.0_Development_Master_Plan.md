# AIOS v3.0 融合后开发主计划

## 一、开发目标

第一目标不是一次性把 AIOS 做到完美。

第一目标是：

> 用融合后的 v3.0 先跑通一个真实大模型能够长期入住、能够记住、能够检索、能够形成认知、能够修正、能够把经验带到下一次交互中的最小完整系统。

跑通后再逐步优化速度、成本、硬件接入和高级能力。

---

## 二、开发纪律

### 2.1 先竖向跑通，再横向扩展

禁止先把几十个模块全部写完再第一次集成。

每一个阶段都必须形成可运行闭环。

### 2.2 旧代码择优迁移，不整仓复制

旧仓代码分为：

- 直接保留；
- 改造迁移；
- 合并；
- 废弃。

不得把历史硬编码认知一起搬进新仓。

### 2.3 确定性测试与认知测试分开

pytest负责：

- Schema；
- 存储；
- 版本；
- 幂等；
- 引用；
- 索引一致性；
- 状态机；
- 性能。

真实大模型入住测试负责：

- 用户理解；
- AI自我成长；
- 跨维认知；
- 新维度发现；
- 推荐质量；
- 长期策略学习；
- 关系演化；
- 行动是否越来越合适。

---

# 三、阶段 0：融合冻结与迁移矩阵

## 目标

在开始搬代码前完成：

1. 双仓机制对照；
2. 旧代码保留/改造/废弃矩阵；
3. 新仓目录骨架；
4. 世界对象最小集合；
5. Runtime 最小接口；
6. 多Agent测试接口。

## 输出

- Fused Baseline Registry；
- 迁移矩阵；
- 最小运行流程；
- 测试基线。

## Gate

不能再出现：

- 一个机制两套相互冲突定义；
- 旧 FINAL 和新 FINAL 同时声称唯一最高；
- 程序员不知道某段旧代码该留还是该删。

---

# 四、阶段 1：世界内核迁移

## 优先迁移旧仓

- `contracts/`
- `storage/sqlite_store.py`
- 时间与 ObjectRef；
- revision；
- idempotency；
- Evidence / Claim / Event / Entity / Relation；
- Dependency基础结构。

## 改造原则

保留物理可靠性，移除历史命名耦合。

AI Self 不另建平行真相库。

## 最小验收

可以真实执行：

```text
Observation
→ commit
→ world_revision +1
→ query by id / revision / time
→ restart
→ 数据仍然一致
```

---

# 五、阶段 2：最小输入与会话世界

## 只接两类输入

第一版只需要：

1. 用户与 AI 对话；
2. 虚拟人生事件流。

虚拟事件可以模拟：

- 日历；
- 支付；
- 订单；
- MIC文本；
- GPS地点变化；
- 睡眠；
- 心率摘要；
- 他人对话；
- 工作事件。

暂时不接真实手机硬件。

## 验收

连续 7 天虚拟人生进入统一世界，所有记录共享统一时间轴。

---

# 六、阶段 3：单维总结 + ALL_DIMENSIONS

## 单维总结

先实现：

- 日；
- 周；
- 月。

语义总结必须由真实模型完成。

系统只提供窗口、来源和调度。

## ALL_DIMENSIONS

实现时间窗跨维对齐。

第一版只需要：

- 选择时间窗；
- 选择相关维度；
- 返回每个维度 Summary + Event Anchor；
- 保留来源。

不做自动因果结论。

## 验收

给定一个月虚拟人生：

AI可以快速看到：

- 工作发生了什么；
- 睡眠发生了什么；
- 社交发生了什么；
- 财务发生了什么；

并自行判断它们是否可能相关。

---

# 七、阶段 4：统一智能世界索引

## 第一版先做简单、可靠的多路索引

优先迁移或重构：

- CJK / FTS；
- Entity / Alias；
- Time；
- Dimension；
- Event Anchor；
- Summary；
- Relation；
- Conversation。

第二版再加入：

- embedding；
- rerank；
- graph diffusion；
- hot workset。

## 必须同时实现索引维护

World Commit
↓
world_revision
↓
index catch-up
↓
watermark
↓
stale detection

## 验收

任何新世界对象写入后，不需要重建整库即可被检索。

---

# 八、阶段 5：智能推荐 + 上下文中控 + Cognitive Runtime

这是 AIOS 第一次真正“入住模型”的关键阶段。

## 智能推荐

当前会话
↓
主题门
↓
无主题 → 0
↓
有主题 → 调用智能索引
↓
少量候选

## 上下文中控

装配：

- 当前输入；
- 最近会话；
- 当前主题；
- AI身份连续性；
- 推荐记忆；
- 任务；
- Capability；
- token预算。

## Cognitive Runtime

模型可以：

- 直接回答；
- 继续 Search；
- Follow Relation；
- 看 Evidence；
- 请求 ALL_DIMENSIONS；
- 沉默。

## 验收

必须出现真实例子：

用户第二周重新提到第一周的人和事时，模型无需用户重复背景即可正确续上；

推荐错了时，模型能忽略并主动换路搜索。

---

# 九、阶段 6：世界写回 + 用户理解 + AI自身世界 + 修正

## 世界写回

模型运行后形成候选：

- Event；
- Claim；
- User Understanding；
- Relationship Understanding；
- AI Reflection；
- Communication Experience；
- Operation Experience。

写回前由类型和证据边界校验。

## 认知修正

实现：

旧 Claim
↓
新 Evidence
↓
retract / revise
↓
Dependency查影响范围
↓
当前认知失效或重算
↓
Summary / Index 更新

## 验收

虚拟用户故意在第 20 天纠正第 3 天的误解：

- 第 3 天原话仍存在；
- 旧 Claim 可追溯；
- 当前 Claim 已修正；
- 后续推荐不再继续把错误认知当真。

---

# 十、阶段 7：目标、任务、行动、Outcome 与策略学习

迁移旧仓：

- Goal；
- Task；
- Action；
- Outcome；
- conditional scheduler 中确定性有价值部分。

补齐：

Action
↓
Outcome
↓
Goal/Task进度
↓
用户反馈
↓
Strategy / Communication Experience
↓
下一次策略变化

## 验收

同一类场景重复出现时，AI能够因为之前的真实反馈改变沟通或行动方式，而不是每次重新开始。

---

# 十一、阶段 8：多Agent长期入住测试

从阶段 2 开始就接入小规模入住测试。

阶段 8 做大规模：

- 30天；
- 180天；
- 1年/2年加速人生；
- 数十到数百虚拟用户；
- 多种大模型入住；
- 对抗性世界变化；
- 关系变化；
- 延迟纠错；
- 同名实体；
- 长会话；
- 旧事突然重提；
- 新维度形成；
- 无事可做时保持沉默。

详细规则见：

`AIOS_v3.0_Multi_Agent_Habitation_Test_Plan.md`

---

# 十二、阶段 9：优化，而不是重构灵魂

系统跑通后再做：

- FTS + Vector + Graph融合；
- PPR / rerank；
- Summary多尺度加速；
- 推荐排序学习；
- token压缩；
- 缓存；
- 并行索引；
- 大规模SQLite或新存储评估；
- Android/Linux适配；
- 真实摄像头/MIC/IMU/App数据接入。

优化必须保持：

> 世界语义不因底层技术替换而改变。

---

# 十三、第一版真正要跑通的最小范围

不要一开始就做完整人生OS。

第一版必须只做：

1. Conversation；
2. 虚拟生活事件；
3. WorldObject；
4. SQLiteWorldStore；
5. 日/周/月 Summary；
6. 智能索引；
7. 会话主题推荐；
8. 上下文中控；
9. Cognitive Runtime；
10. Claim / User Understanding / AI Experience 写回；
11. 修正；
12. 下一轮能使用这些历史。

如果这 12 项在 30 天连续虚拟人生里真正跑通，就进入下一阶段。

---

# 十四、最终判断标准

AIOS 不以“跑了多少测试题”判断是否成功。

真正的标准是：

> 同一个虚拟用户活得越久，AI 是否因为自己的真实经历、世界、错误、反馈和修正，越来越了解这个用户，也越来越会使用这个世界。

