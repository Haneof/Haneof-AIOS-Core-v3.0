# AIOS v3.0 数据清洗与机械压缩宪法

## 一、定义

数据清洗负责：

> 在不改变事实语义的前提下，让现实数据能够长期进入和维护于 AIOS 世界。

清洗不是认知。

清洗不能回答：

- 这件事对用户意味着什么；
- 这句话是不是重要承诺；
- 用户是不是焦虑；
- 某个行为是不是诈骗；
- 用户能力是不是提升；
- 某个人是不是用户的重要关系。

这些属于后续 AI认知。

---

## 二、机械清洗

允许确定性执行的机械操作包括：

- 精确去重；
- source identity 校验；
- 时间统一；
- schema / unit / format 规范化；
- 数据质量标记；
- 明确的无效结构拒绝；
- 高频数值流机械压缩；
- 明确测量阈值的变化事件保留；
- 原始媒体 → 上游 descriptor/transcript 后的长期事实写入。

这些操作必须可复现、可审计。

---

## 三、高频数值流

IMU、心率、温度、血氧等高频机制型来源不应无差别把每个采样点长期写入世界。

可以使用显式工程 Policy：

- tolerance；
- change threshold；
- max gap；
- unit；
- adapter/source identity。

系统可以形成：

```text
稳定采样
↓
numeric segment
(mean / min / max / sample_count)

明显变化
↓
numeric change
(previous / current / delta)
```

这里的“明显变化”只表示：

> 数值跨越了显式工程阈值。

它不表示：

- 危险；
- 生病；
- 紧张；
- 兴奋；
- 情绪变化。

这些意义必须由后续机制结合 Evidence 判断。

---

## 四、阈值必须显式

禁止在清洗代码里偷偷固化认知阈值。

例如：

```text
HR > 120 → 用户焦虑
```

属于非法认知。

而：

```text
相邻采样绝对变化 >= adapter policy.change_threshold
→ 保存 numeric_change
```

属于合法机械事实保真。

---

## 五、非结构化数据

图片、语音、外部聊天、日记等无法仅靠格式规则完全整理。

上游模型/算法可以产生事实性 descriptor，例如：

- caption；
- transcript；
- object facts。

但是输出仍必须局限于可观察事实。

例如合法：

> “桌上有一台电脑和一杯水。”

非法清洗输出：

> “用户正在焦虑地加班。”

后者已经包含状态与意义判断，必须进入认知层并有 Evidence。

---

## 六、禁止旧语义提纯器回流

冻结旧实现中曾存在：

- 通过关键词把文本判成“核心证据/垃圾”；
- 根据固定词语判断诈骗、危机、关系意义；
- “第一人称 + 字数”自动判定长期价值；
- 在 ingest 层做因果/心理/健康/关系推理；
- LLM 在清洗层直接产生高阶 semantic intent。

这些机制不得迁回当前 P13 现实接入层。

其中可以择优保留的只有纯工程原语，例如：

- transient raw buffer；
- 数值压缩；
- media descriptor；
- voiceprint feature/index；
- source quality metadata；

且必须移除认知意义判断。

---

## 七、清洗后的事实仍然可追溯

机械压缩不能让来源链完全消失。

压缩对象至少保留：

- adapter；
- series；
- source record ids 或 source range；
- policy；
- 时间区间；
- sample count；
- unit；
- raw locator 或 source locator。

因此未来可以审计：

> 这个长期事实是如何由哪批现实采样产生的。

---

## 八、接入失败与世界完整性

被拒绝的数据必须可审计。

Failure Audit 不是用户认知，也不是来源事实内容本身。

它只记录：

> AIOS曾尝试接入某来源记录，但该记录没有成功进入事实世界。

这样 AI 在未来判断证据覆盖时可以知道存在数据缺口。

---

## 九、与 Summary / Cognition 的关系

机械清洗完成后：

```text
Canonical Observation
↓
WorldStore
↓
Index
↓
Dimension Summary
↓
Resident AI
↓
Event / Claim / Relationship / higher cognition
```

清洗层不得跨越这条边界直接写高阶结论。

---

## 十、根定义

> **清洗负责减少噪声成本和存储成本，但不得用“清洗”之名提前替 AI 思考。**
