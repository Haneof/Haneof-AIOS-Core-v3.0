# AIOS v3.0 证据与认知修正宪法

## 一、定义

AIOS 的世界允许认知改变，但不允许历史事实被倒写。

修正机制负责处理：

> 新 Evidence 出现后，旧 Claim 如何 revise / retract，以及依赖旧认知的下游对象如何停止继续被当作当前有效结论。

---

## 二、事实不可回写

以下对象一旦作为历史事实写入，不得因为后来的理解变化而修改其原始含义：

- Observation；
- 用户原话；
- AI 当时实际说过的话；
- 当时已经发生的 Action / Outcome；
- 已经形成过的历史 Claim revision。

修正必须向前追加。

例如：

```text
T1
Observation：用户说“我最近每天喝茶”
↓
Claim A@1：用户当前偏好喝茶

T2
Observation：用户说“现在已经改成每天喝咖啡”
↓
Claim A@2：用户当前偏好喝咖啡
```

A@1 仍然存在，用于回答“AI 当时为什么这样理解”。

当前世界则以 A@2 为当前 revision。

---

## 三、Claim 修正有两种基本形式

### 3.1 Revise

旧理解仍属于同一个认知对象，但内容需要更新。

```text
Claim A@1
↓
新 Evidence
↓
Claim A@2
status = active
metadata.supersedes_revision = 1
```

### 3.2 Retract

AI 认为旧 Claim 不应继续作为当前有效结论。

```text
Claim A@1
↓
反证 / 用户纠正
↓
Claim A@2
status = retracted
```

Retract 不删除 A@1。

---

## 四、Evidence 是修正的前提

正式 revise / retract 必须引用 pinned Evidence。

禁止：

- 仅因为模型突然改变想法而改历史认知；
- 没有证据直接删除旧 Claim；
- 用新的 Summary 反向覆盖 Observation；
- 把模型输出本身伪装成新事实。

修正 Evidence 可以来自：

- 新 Observation；
- 新 Event；
- 用户明确纠正；
- 新 Outcome；
- 新 Claim；
- 经验证的外部事实。

---

## 五、Dependency 传播

AIOS 使用显式 Dependency 记录认知依赖。

例如：

```text
Observation O1
↓
EvidenceSet E1
↓
Claim A

Claim A
↓
EvidenceSet E2
↓
Claim B

Claim A / Claim B
↓
Summary S
```

当 A 的某个 pinned revision 被 revise / retract 后，系统确定性地反向找到仍依赖该旧 revision 的对象。

---

## 六、传播只标记“需要重新判断”

确定性系统可以自动做：

- reverse dependency lookup；
- 标记 EvidenceSet stale；
- 标记 Summary stale；
- 标记 dependent Claim / Relation / cognition object 为 stale_review_required；
- 当前索引隐藏这些失效认知；
- 把受影响对象返回给 Cognitive Runtime。

确定性系统不得自动做：

- 替 AI 重新写新的用户理解；
- 根据旧规则自动生成新的因果结论；
- 机械地把所有下游文字替换；
- 通过关键词决定新的认知答案。

根原则：

> **系统负责发现“哪些理解可能已经不可靠”，AI 负责重新理解。**

---

## 七、已经前进的下游对象不得被旧依赖倒退覆盖

Dependency 指向精确 revision。

如果：

```text
B@1 依赖 A@1
```

后来 B 已经独立前进为 B@2，而此时 A@1 才被修正，则传播机制不得把 B@2 强制覆盖成 stale。

系统只能说明：

> B@1 曾经依赖 A@1。

如果当前 B 已有新 revision，必须尊重当前 B。

---

## 八、stale_review_required

当一个当前认知仍依赖已失效上游时，系统产生新的当前 revision：

```text
B@1 active
↓
A@1 被 revise
↓
B@2 stale_review_required
```

B@1 保留历史。

B@2 表示：

> 当前 AIOS 已经知道这个认知需要重新判断，但还没有替 AI 做新的结论。

Resident AI 可以随后：

- inspect；
- search；
- 看新 Evidence；
- revise B@2 → B@3 active；
- 或 retract B@2 → B@3 retracted。

---

## 九、Summary 的修正

Summary 不是永久真相。

每个 Summary 必须保留其 source refs / dependencies。

如果其来源 Claim / Event / Evidence 当前失效，则：

```text
Summary S@1 current
↓
source Claim 被 revise
↓
Summary S@2 stale
↓
重新收集该时间窗当前有效来源
↓
由模型生成新 Summary
↓
Summary S@3 current
```

旧 Summary 保留，用于历史认知回放。

---

## 十、索引的当前视图

智能世界索引仍然保留历史 revision 的可追溯能力。

但默认 current retrieval 不得主动返回：

- retracted；
- stale_review_required；
- stale Summary；
- stale EvidenceSet；
- 已经存在更高 revision 的旧对象版本。

历史调查仍可通过 pinned revision / historical view 显式读取旧版本。

因此：

> **历史不能消失，但历史错误也不能继续伪装成当前真相。**

---

## 十一、与智能推荐的关系

智能推荐只使用当前有效世界视图。

如果某个用户理解已进入：

`stale_review_required`

则它不得继续作为“用户当前画像”主动塞给模型。

必要时模型可以主动查看：

- 它为什么 stale；
- 原 Claim；
- 新 Evidence；
- 当前 dependency graph；

然后重新形成认知。

---

## 十二、与 AI 用户理解 / AI 自我 / 关系 / 策略的关系

后续所有长期认知模块都必须使用同一修正机制。

包括：

- AI User Understanding；
- AI Relationship；
- AI Self；
- Cognitive Boundary；
- Strategy；
- Personality-derived cognition；
- Communication Experience；
- Operation Experience。

不得为每个模块另造一套“修改数据库”。

---

## 十三、禁止事项

禁止：

1. 删除旧事实来解决认知错误；
2. 修改 Observation 原文；
3. 新 Evidence 出现后仍让失效 Claim 默认参与推荐；
4. 机械级联自动重写所有下游认知；
5. Dependency 不 pin revision；
6. 旧依赖传播覆盖已经独立前进的新 revision；
7. Summary 无来源依赖；
8. 将 stale 当作 falsified；stale 只代表“需要重新判断”；
9. 因为一次修正就重建整个世界；
10. 为 benchmark 写专属翻案逻辑。

---

## 十四、标准闭环

```text
新 Evidence
↓
Resident AI 判断旧 Claim 需要 revise / retract
↓
创建 Claim 新 revision
↓
保留旧 revision
↓
Dependency reverse propagation
↓
下游当前认知 / Summary / EvidenceSet 标记 stale
↓
当前索引隐藏 stale cognition
↓
Resident AI 逐项重新判断
↓
产生新的 active revisions
↓
Summary rebuild
↓
Index catch-up
↓
下一次推荐使用新的当前世界
```

---

## 十五、根定义

> **AIOS 不要求 AI 永远正确；AIOS 要求 AI 的错误有历史、有证据、有传播路径，并且能够真正改正。**
