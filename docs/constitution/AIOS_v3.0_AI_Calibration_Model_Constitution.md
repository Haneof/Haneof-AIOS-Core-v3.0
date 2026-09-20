# AIOS v3.0 AI校准模型宪法

## 一、定义

AI校准模型记录：

> AI 对自己过去判断、预测、沟通和行动是否有效的长期认识。

它回答：

- 我曾经判断错过什么；
- 用户纠正过什么；
- 哪些假设后来得到支持或被推翻；
- 哪些沟通方式在真实反馈中有效或无效；
- 哪些操作路径在真实 Outcome 中可靠或低效；
- 哪些问题仍然缺证据。

## 二、证据来源

校准只能来自真实运行结果：

- 用户明确反馈；
- Claim revise / retract；
- Prediction 后续验证；
- Action Outcome；
- Communication Experience；
- Operation Experience；
- 后续 Observation / Event。

禁止凭模型主观感觉生成“我已经变聪明了”之类无证据结论。

## 三、校准不是固定准确率排行榜

系统可以计算机械统计，但统计只是 Evidence。

最终校准 Claim 仍由 AI 判断其意义。

不得使用固定题库命中率替代真实长期校准。

## 四、与策略学习的关系

校准可以成为 Strategy / Cognitive Policy 调整的 Evidence。

但：

> 校准发现问题，不等于自动修改策略。

正式策略变化仍必须遵守自适应认知策略宪法中的 scope、version、evidence、evaluation window 与 rollback。

## 五、与认知修正的关系

用户纠正旧理解时：

```text
旧 Claim
↓
新 Evidence / 用户纠正
↓
revise / retract
↓
产生校准 Evidence
↓
AI可形成 Calibration Claim
↓
未来类似场景可被索引/推荐/主动搜索再次使用
```

## 六、根定义

> **校准不是让 AI 证明自己正确，而是让 AI 能够记住自己为什么错、怎么被纠正，以及以后如何少犯同类错误。**
