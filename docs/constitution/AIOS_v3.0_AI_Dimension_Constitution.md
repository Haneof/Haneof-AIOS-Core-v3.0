# AIOS v3.0 AI维度宪法（入口）

## 一、定义

AI维度记录 AI 在统一 AIOS 世界中形成的长期认知。

AI维度与用户事实维度、事件维度等平级存在。

用户世界提供现实事实；AI维度保存：

> AI 对用户、关系、自身、未知、策略、人格与过去表现形成的可修正理解。

AI维度不是第二套数据库。

---

## 二、统一世界实现

AI维度默认使用与整个 AIOS 相同的世界对象：

- EvidenceSet：认知依据；
- Claim：当前理解；
- Dependency：依赖关系；
- Summary：某 AI维度一段时间发生了什么；
- Revision / Retraction：理解修正。

所有 AI维度认知必须进入统一 WorldStore、统一时间轴、统一索引和统一修正机制。

禁止恢复独立 `AI Self DB`、独立用户画像真相库或独立关系数据库。

---

## 三、AI维度模块

1. AI用户理解模型  
   文件：`AIOS_v3.0_AI_User_Understanding_Model_Constitution.md`

2. AI关系模型  
   文件：`AIOS_v3.0_AI_Relationship_Model_Constitution.md`

3. AI自我模型  
   文件：`AIOS_v3.0_AI_Self_Model_Constitution.md`

4. AI主动意图模型  
   文件：`AIOS_v3.0_AI_Intent_Model_Constitution.md`

5. AI策略模型  
   文件：`AIOS_v3.0_AI_Strategy_Model_Constitution.md`

6. AI认知边界模型  
   文件：`AIOS_v3.0_AI_Cognitive_Boundary_Model_Constitution.md`

7. AI人格模型  
   文件：`AIOS_v3.0_AI_Personality_Model_Constitution.md`

8. AI校准模型  
   文件：`AIOS_v3.0_AI_Calibration_Model_Constitution.md`

---

## 四、证据与未知

AI维度允许：

- INFERRED；
- HYPOTHESIS；
- UNKNOWN；
- CONFLICT。

AI不知道时，记录“不知道/待验证”比制造确定答案更合法。

所有长期认知必须能够追溯到 Evidence。

---

## 五、演化原则

AI认知变化必须向前演化：

```text
Evidence
↓
Claim@1
↓
新 Evidence / 用户反馈 / Outcome
↓
revise / retract
↓
Claim@2
↓
Dependency propagation
↓
下游认知重新判断
```

旧认知 revision 保留，用于理解 AI 当时为什么这样判断。

---

## 六、模块治理原则

AI维度入口只定义整体关系。

具体机制由独立模块文件负责。

禁止：

- 在入口文件重复所有子模块规则；
- 用固定心理标签替代模型理解；
- 用次数、时长、分数自动生成关系或人格；
- 让 AI维度覆盖或修改用户世界原始事实。

---

## 七、根定义

> **AI维度不是 AI 的另一套记忆库，而是 AI 在同一个世界里对用户、自己以及双方共同经历形成的可修正认知。**
