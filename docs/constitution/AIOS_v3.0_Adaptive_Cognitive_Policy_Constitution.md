# AIOS v3.0 自适应认知策略宪法

## 一、定义

AIOS 中的规则、阈值和参数必须区分“系统硬边界”与“认知策略”。

规则不能消失，但规则不得偷偷成为第二个 AI 大脑。

---

## 二、三类规则

### 2.1 Hard Boundary

确定性硬边界，包括：

- Schema与协议；
- 事实历史不可静默篡改；
- 权限；
- 身份与引用完整性；
- 原子事务；
- 幂等；
- 必要安全边界；
- 物理设备约束；
- 审计完整性。

AI不得通过普通策略学习关闭硬边界。

### 2.2 Engineering Parameter

工程参数，包括：

- timeout；
- retry；
- batch；
- cache；
- watermark；
- token预算；
- latency预算；
- storage预算；
- 查询fanout。

它们服务性能与稳定性，不表达“用户是什么”。

### 2.3 Cognitive Policy

认知策略，包括：

- 召回阈值；
- 候选扩展策略；
- 停止检索策略；
- 推荐排序偏好；
- 主动介入策略；
- 沟通方式；
- 详略偏好；
- 关系表达方式；
- 反思触发策略；
- 新维度候选评估策略。

认知策略是可学习操作习惯，不是永恒真理。

---

## 三、策略必须结果驱动

合法策略学习：

当前策略
↓
真实交互 / 查询 / 行动
↓
Outcome / 用户反馈 / 检索命中质量 / 误触 / 无效行动
↓
AI形成调整理由
↓
产生新策略候选
↓
版本化
↓
evaluation window
↓
保留 / 再调整 / 回滚

不得因为模型“感觉这个阈值更好”就永久修改。

---

## 四、最小策略记录

正式认知策略至少应包含：

- policy_id；
- scope；
- class；
- default_value；
- current_value；
- allowed_range_or_choices；
- mutable_by_ai；
- reason；
- evidence_refs；
- changed_by；
- changed_at；
- version；
- previous_version；
- rollback_pointer；
- evaluation_window。

---

## 五、作用域

策略可以分别存在：

- global default；
- per-user；
- per-situation；
- per-capability；
- session temporary override。

一次偶发体验不得自动修改全局策略。

---

## 六、与智能推荐和索引的关系

智能推荐和智能索引中涉及：

- Top-K；
- 扩展深度；
- 语义召回阈值；
- 图扩散范围；
- 推荐置信门；
- 是否继续检索；

若属于认知取舍，则应作为 Cognitive Policy 管理，而不是散落为不可解释的 Python 常量。

---

## 七、与AI关系和沟通经验的关系

AI对某个用户逐渐学会：

- 什么时候少说；
- 什么时候展开；
- 哪些提醒方式有效；
- 哪些表达容易引起反感；
- 什么关系距离更符合真实互动；

这些变化必须来自长期真实反馈，而不是固定人格模板。

---

## 八、禁止事项

禁止：

1. 把认知阈值写进代码后宣布永久有效；
2. 用固定关系分数决定说话方式；
3. 用一次用户反应重写全局策略；
4. 无证据修改长期策略；
5. 策略更新不可回滚；
6. AI自行扩大权限或关闭硬边界；
7. benchmark-specific 策略进入正式运行时。

---

## 九、根定义

> **硬边界守住系统，工程参数控制资源，认知策略随着真实经验学习；规则提供道路和仪表，AI仍然是驾驶员。**

