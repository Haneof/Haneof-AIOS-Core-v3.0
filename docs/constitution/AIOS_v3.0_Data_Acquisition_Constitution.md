# AIOS v3.0 数据获取机制宪法

## 一、定义

数据获取机制负责：

> 把现实世界与数字世界已经发生的事实，以可追溯、可去重、统一时间化的形式送入 AIOS 世界。

获取层只负责“发生了什么”。

它不负责：

- 用户是什么；
- 这件事意味着什么；
- 用户为什么这样做；
- 某个人与用户是什么关系；
- 是否应该形成新的高阶认知维度。

---

## 二、统一 Source Adapter

所有现实来源通过 Source Adapter 接入。

Adapter 至少必须固定声明：

- adapter_id；
- source_kind；
- source dimension；
- source class；
- schema version；
- default modality。

其中 source dimension 必须显式声明。

例如：

```text
支付来源  → dim:payment
订单来源  → dim:order
摄像头描述 → dim:camera_visual
MIC转写   → dim:mic_audio
心率来源  → dim:heart_rate
```

禁止 Adapter 根据内容语义临时决定高阶维度。

---

## 三、Canonical Observation

普通现实记录进入世界时默认规范化为 Observation。

每条 Observation 必须保留：

- source_kind；
- modality；
- occurred time；
- learned / recorded time；
- source locator；
- external record identity；
- adapter identity；
- schema version；
- data quality；
- provenance；
- dimension。

外部来源 ID 用于确定性去重，不替代 AIOS object_id。

---

## 四、统一时间轴

外部来源可以使用任意时区。

进入 AIOS 世界前必须转换到统一 UTC 时间坐标，同时保留必要的原始时间表示用于审计。

时间归一只改变表示，不改变事实发生顺序和事实语义。

---

## 五、去重与来源冲突

同一个：

```text
adapter_id
+ external_record_id
+ external_revision
```

只能对应一个确定事实。

完全相同记录重放：

> 幂等复用，不重复写世界。

相同来源身份却出现不同内容：

> 必须报告 identity conflict，不得静默覆盖旧事实。

如果外部系统正式修正记录，应使用新的外部 revision / source identity，并保留来源修正关系。

---

## 六、媒体来源

AIOS 长期世界不要求复制原始图片和录音二进制。

允许的长期事实表示包括：

- 图片 caption；
- 图像中可直接观察的 object facts；
- 录音 transcript；
- speaker / voiceprint 引用；
- media locator；
- 时间与数据质量。

原始媒体可以由设备/App在其原本位置管理。

AIOS只保存定位引用与长期事实表示。

禁止把未经必要性判断的整套相册、录音库复制进 AIOS WorldStore。

---

## 七、结构化 App 数据

日历、便签、支付、订单、文件、App行为等可以以结构化 value 进入 Observation。

来源边界必须保持。

尤其：

> 支付事实与订单事实不是同一个维度。

后续 AI 可以跨维观察二者，但 Adapter 不得在接入阶段替 AI 合并意义。

---

## 八、接入失败

数据接入失败不得静默消失。

对于无法进入世界的来源记录，系统必须至少留下不包含原始敏感二进制的机械审计事实，包括：

- adapter_id；
- external record id；
- error type；
- 失败字段位置；
- source locator；
- 时间。

因此 AIOS 可以知道：

> 某个来源在某段时间存在接入缺口。

不得把“没有成功接入”误当成“现实中没有发生”。

---

## 九、禁止事项

禁止：

1. Source Adapter 生成心理、关系、能力、价值观等 Claim；
2. 根据关键词自动把普通事实升级为重大事件；
3. 用内容关键词决定“这个人可信/不可信”；
4. 原始图片/录音二进制直接进入长期 WorldStore；
5. 相同 source identity 静默覆盖；
6. 支付/订单等不同来源被接入层强行合并；
7. 无 provenance 的长期 Observation；
8. 接入失败后没有任何审计痕迹。

---

## 十、根定义

> **数据获取层负责把现实准确送进世界，不负责替 AI 解释现实。**
