# AIOS 总结机制验证报告

- 日期：2026-10-30
- 数据：复用 `experiments/cleaning_ab/sim_realtime.py`，3 天 × 9 维度 + 连续心率流（约 119 条文本 + 3 条心率流）
- 方法：本地机制模式（stub handler，不联网）+ 真实模型 echo 模式（NVIDIA 端点，逐维度）；3 个并行子 agent 各跑一天
- 脚本：`experiments/summary_verify/verify_summary.py`（`--mode mechanism` / `--mode echo --day N`）

---

## 一、结论速览

| 验证项 | 结果 | 判定 |
|---|---|---|
| 全维度覆盖 | active_dimensions = **9/9** | ✅ |
| 自动 draining / DAY 总结 | **27 条**（9 维度 × 3 天，每维度每天 1 条） | ✅ |
| 幂等（重跑） | 0 新提交 / **27 skipped_unchanged** | ✅ |
| 多尺度窗口（UTC 稳定） | DAY/WEEK/MONTH 边界正确 | ✅ |
| 多尺度自底向上（WEEK） | 含 day 总结源、**无同/更高尺度环** | ✅ |
| WEEK 完整性保护 | 8/9，缺 heart_rate（见 §2.5，fail-closed 正确） | ✅ |
| 内容保真（跨维度） | **21/21**（7/7 × 3 天） | ✅ |
| 清洗协同（噪声过滤） | 总结源含噪声、偶发漏进正文 | ❌ 缺口 |

**一句话**：总结机制的机械层完备可靠（全维度、自动、幂等、多尺度自底向上、内容保真高）；两处待补——**① 总结不吃清洗标签（噪声偶发污染）；② 高基数数值维度周聚合受 500 源上限（按维度调高或分层聚合即可）。**

---

## 二、机制层验证（本地、stub、确定性）

### 2.1 全维度覆盖
`active_dimensions()` 发现世界中出现过的全部 9 个维度：
`dim:app_usage / dim:calendar / dim:camera_visual / dim:external_chat / dim:heart_rate / dim:mic_audio / dim:note / dim:order / dim:payment`

### 2.2 自动逐维度出 DAY 总结
`run_due(scales=(DAY,))` 一次性为 3 天 × 9 维度产出 **27 条** DAY 总结（`day_commits_per_dimension` 每维度均为 3）。证明机制会**穷举所有已闭合窗口 × 所有维度**，不漏维度、不漏天。

### 2.3 幂等
同一批窗口重跑：`rerun_commits = 0`、`rerun_skipped_unchanged = 27`。`_unchanged()` 靠"源身份（object_id+revision）不变"判定，重跑零重复、零漂移。

### 2.4 多尺度窗口边界（UTC）
| 尺度 | 窗口 |
|---|---|
| DAY | 2026-10-28 00:00:00 → 23:59:59.999999 |
| WEEK | 2026-10-26（周一）→ 2026-11-01 23:59:59 |
| MONTH | 2026-10-01 → 2026-10-31 23:59:59 |

均以 UTC 对齐、边界稳定，符合 `test_all_constitutional_summary_scales_have_stable_utc_windows`。

### 2.5 多尺度自底向上（关键不变量）
WEEK 聚合的源 = **原始 observation + 更低尺度的 day 总结**（`week_includes_day_summary_source=true`、`week_has_raw_observation_source=true`），**不出现同/更高尺度的总结**（`week_has_equal_or_higher_summary_source=false`）——即不会形成自依赖或跨尺度环，符合 `DimensionSummaryService` 的 bottom-up 约束。

> **WEEK 8/9 说明**：缺的是 `dim:heart_rate`。其原始数值段 288 段/天 × 3 天 ≈ **864 条 > 500 源上限**（`max_source_objects=500`），`prepare` 判 `truncated=True` → 按设计 **fail-closed**、不发布不完整的周总结。这是正确行为（对应既有测试 `test_summary_source_cap_fails_closed_instead_of_publishing_partial_current`），不是 bug。其余 8 个维度源数均 < 60，正常发布。

---

## 三、内容保真验证（真实模型 echo）

### 3.1 跨维度覆盖 = 21/21（3 天全部 7/7）
把每天的 7 条 ground-truth 事实按"源记录所属维度"分摊，再检查**该维度总结**是否写出。三天结果：**每天 7/7 全部覆盖**。

> 说明：此前用"单维度 mic_audio 总结 vs 全部 7 条"错配了口径（体检/聚餐/医保卡/衣服本就属于 calendar/note 维度），故单维度看似 5/7、6/7；按维度归属后 7/7，才是"今天发生了什么"的真实口径。

### 3.2 逐维度归属命中率（近 100%）
| 维度（承担的事实） | DAY1 | DAY2 | DAY3 |
|---|---|---|---|
| calendar | 1/1 | 2/2 | 2/2 |
| note | 2/2 | 2/2 | 2/2 |
| mic_audio | 5/5 | 4/4 | 6/6 |
| external_chat / payment / order / app_usage | 1/1 各 | 1/1 各 | 1/1 各 |
| camera_visual | 0/1* | 1/1 | 1/1 |

\* DAY1 camera_visual 的 0/1 是**关键词口径**问题：画面总结写"站立不稳、面色苍白"未用"头晕/晕"字样，语义其实命中（该画面正是头晕的人）。非模型漏检。

### 3.3 事实保真示例（原文）
- DAY1 calendar：「当天日程包括两项：周四10:00项目周会；周五15:00公司年度体检。」
- DAY1 note：「17:55，提醒自己记得给妈妈带医保卡和身份证。」
- DAY2 calendar：「当天日程要点：10月31日个税汇算清缴截止；明晚（10月30日）有家庭聚餐。」
- DAY3 note：「19:30，提到给孩子带话剧演出的衣服。」

模型对**本维度事实抓取准确、按时间组织、基本不编造**。

---

## 四、清洗协同缺口（本次实证，需后续补）

1. **总结源不做 relevance 过滤**：`dim:mic_audio` DAY1 的 18 条源里，**11 条是 ground-truth 标注的噪声**（m01/m02/m03/m05/m07/m09/m10/m12/m15/m17/m18）。`DimensionSummaryService.prepare()` 只按"维度+时间窗"取源，**完全不读清洗层产出的 `decision/relevance` 标签**。
2. **噪声偶发漏进总结正文**：
   - DAY1 external_chat 总结写入了「在吗」
   - DAY3 external_chat 「在吗」、mic_audio 「睡了」
   - （DAY2 本轮全维度零污染——模型温度导致的方差；上一轮曾把"算了不说了"当事件写入）
3. **结论**：清洗层（v5：机制全量存真 + AI 只标注 + 二次门禁）产出的降权标签，**目前没有被总结机制消费**。要让"总结更干净"，需在 `prepare()` 取源时按 `relevance` 降权/过滤，或让 summary prompt 显式收到每条源的 keep/drop 标签。

---

## 五、架构发现：总结是"单维度"的，没有跨维度"今日全貌"

`DimensionSummaryService` 的 `summary_kind = single_dimension_temporal`——**每个维度各自一份时间窗总结**，系统不生成"把 9 个维度合成一篇今日综述"的单条总结。因此"今天发生了什么"的完整图景 = **各维度总结的聚合**（本次 21/21 正是聚合后才覆盖全）。若产品需要单条"今日总览"，需另做跨维度聚合层（现有机制不含）。

---

## 六、局限

- n=3 天、单模型（NVIDIA minimax-m3.1-flash）；ground truth 由作者自标。
- 关键词回声对语义改写敏感（camera_visual 典型案例），实际保真高于关键词数字。
- 真实模型单次 120–430 秒，期间多次 429/504 由内置退避重试恢复；未做跨模型稳健性。
- WEEK/MONTH 目前只验了"单周"；未验超长跨度（季度/年）与多周连续聚合。

---

## 七、建议下一步

1. **让总结吃清洗标签**（最高价值）：`prepare()` 按 `relevance` 降权或过滤 `decision=drop` 的源；或 summary prompt 带每条的 keep/drop。可复用 v5 的标注。
2. **高基数维度（心率）周/月聚合**：按维度调高 `max_source_objects`，或先聚合数值段再总结（分层），避免长期 fail-closed 不出周总结。
3. **跨模型稳健性**：换 1–2 个模型重跑 echo，确认 7/7 稳定。
4. 若需"今日全貌"：新增跨维度聚合层。
