# AIOS 总结机制验证报告（v2：修复后 + 今日总览基础维度）

- 日期：2026-10-30
- 数据：`experiments/cleaning_ab/sim_realtime.py`，3 天 × 9 维度 + 连续心率流（约 119 条文本 + 3 条心率流）
- 模型：NVIDIA `integrate.api.nvidia.com` / `minimax-m3.1-flash`（同端点备用 `z-ai/glm-5.3-flash`）
- 脚本：`experiments/summary_verify/verify_summary.py`、`run_echo_driver.py`、`resume_digest_analysis.py`、`probe_digest.py`
- 代码：`src/aios_core/summaries/`（`dimension_summary.py` / `scheduler.py` / `daily_digest.py`）

> v1 报告见 git 历史（commit 8eae6b3 之前的版本）。本版包含 v1 提出的两个修复 + 今日总览维度 + 机制加固。

---

## 一、本轮改了什么

| 项 | 改动 | 文件 |
| --- | --- | --- |
| ① 总结吃清洗标签 | `DimensionSummaryService.source_admission`：构造级注入准入谓词，prepare/commit 两侧同一策略；清洗判定 `cleaning_decision=DROP` 的记录不进入任何总结源 | `dimension_summary.py` |
| ② 高基数维度周聚合 | `prepare(..., max_source_objects=)` 覆盖并记入 input（commit 内部复检同值）；scheduler 加 `dimension_source_caps`（heart_rate=1200） | `dimension_summary.py` / `scheduler.py` |
| ③ 今日总览基础维度 | 新增 `dim:daily_digest` + `DailyDigestService`：源=当天各维度 DAY 总结，独立 prepare/校验/幂等，不经 index；scheduler 全量 sweep 自动触发，`active_dimensions()` 排除自身防自递归 | `daily_digest.py` / `scheduler.py` |
| ④ 机制加固 | `run_due` fail-soft：单个 handler 失败（网关 504 / CAS 冲突）记入 `failed` 且不中断整轮，下一轮自动重试 | `scheduler.py` |

设计要点：`commit()` 内部会重新 `prepare()` 复检（CAS 一致性），所以准入与源上限必须构造级注入、两侧同值，否则会出现"prepare 通过、commit 拒绝"的假失败。

## 二、机制层结果（stub handler，确定性，无模型噪声）

| 指标 | v1（修复前） | v2（修复后） | 判定 |
| --- | --- | --- | --- |
| 维度覆盖 | 9/9 | 9/9 | ✅ |
| DAY 总结 | 27（9×3） | 27 + **digest 3** | ✅ |
| 今日总览 | 无 | 3 条，每条源=9 个维度 DAY 总结 | ✅ |
| 幂等（重跑） | 0 提交 / 27 跳过 | **0 提交 / 30 跳过**（27 维度 + 3 总览） | ✅ |
| WEEK 提交 | 8/9（heart_rate fail-closed） | **9/9**（源上限按维度放宽到 1200） | ✅ 修复生效 |
| WEEK 自底向上 | 无同/更高尺度源 | 无同/更高尺度源 | ✅ |
| 总结源含噪声 | 11 条噪声 | **0 条**（admission 生效） | ✅ 修复生效 |
| 窗口边界 | UTC 稳定 | UTC 稳定 | ✅ |

## 三、内容保真（真实模型，DAY1 重跑）

| 指标 | v1 | v2（含 admission） |
| --- | --- | --- |
| 跨维度总覆盖（7 条 ground-truth） | 7/7 | **7/7** |
| 逐维度归属回声 | mic 5/5、note 2/2、calendar 1/1 | mic 5/5、note 2/2、payment 1/1、external_chat 1/1、calendar 1/1 |
| **噪声污染** | DAY1：external_chat「在吗」、mic「睡了」 | **无污染（0）** |
| 今日总览（新增） | 不存在 | **7/7**，282 字覆盖全部关键事实 |

总览正文（模型原样输出）：

> 今天得知妈妈昨晚住进市第二人民医院心内科；与小李因项目分工吵架，小李不愿接测试。小王转述李总：合同周三须到，否则重谈；我答应张总周三前发初稿，交付周期30天、违约金5%。定下本月减重五斤、今晚起不吃饭；缴住院预缴金12000元。下午头晕，用文档App 47分钟；15:36心率骤升至124，15:40、15:47达131–132，站不稳、扶桌时面色苍白，15:51回落基线。提醒带医保卡和身份证；18:20到医院，医生告知妈妈需造影，明日上午出结果。周四10:00项目周会、周五15:00公司年度体检；订护颈枕×1，预计周四送达。阿强约周末钓鱼，未记录答复或成行。

已知口径问题（非机制缺陷）：`camera_visual` 0/1——事实「头晕」被模型表述为「站不稳/扶桌」，关键词口径过严。

## 四、剩余缺口（诚实记录）

1. **504 是模型端点（基础设施）问题**：NVIDIA 网关对 ~250s 级别的生成不稳定。总览单次负载最大（9 维度整段合成），最易触发。实测 token 预算甜点：2500/4500 → 思考耗尽、空正文；6000 → 频繁 504；**4000（紧凑提示词，思考收敛 ~3400 tokens）**稳定。同一调用在几小时内可成功可 504，属网关负载波动。
2. **总览应支持两阶段压缩**（先每维度压成要点再合成），把单次负载降一个数量级——已记录，未实现。
3. **DAY2 / DAY3 的 echo 未用新机制重跑**（本轮只重跑 DAY1；DAY2 复跑进行中），旧数据不含 admission。
4. 采集层仍是模拟数据，真实设备无感接入未接；AI 自我认知（`dim:ai_self`）随世界修订的自动更新闭环仍在早期。

## 五、测试

`tests/integration/test_v3_daily_digest.py`（5 项）：总览是一等基础维度 / 幂等且不自递归 / 清洗准入拒入噪声源 / 按维度源上限覆盖 / handler 失败 fail-soft 且下轮重试。
全量回归 `python3 -m pytest tests -q --ignore=tests/agent_gateway` 通过。
