# Window80 G-1/G-2 修复独立验收报告

- **任务**：`PM-WINDOW80-GAPS-G1G2-ACCEPTANCE-001`
- **验收员**：独立验收窗口（全新窗口，与 G-1/G-2 的实现、PM 审核、两次复核 RV20261120-001 / RV20261120-002、Window80 接线验收、Operator、Core 修复、合并无任何既往参与）
- **验收对象**：提交 `e52878e`（`fix(search,runtime): close Window80 gaps G-1 and G-2`，`Haneof/Haneof-AIOS-Core-v3.0`）
- **验收执行树**：本地 `cc42c1a`（2026-11-20 PM 裁决治理提交，本地未推远端；远端 main 仍在 `8317769`）
- **日期**：2026-11-20（UTC）
- **总体出口**：**ACCEPTED**（两处缺口均已修复并独立复现验证；仅余 2 项既有小问题，均不阻塞，见 §5）

## 0. 独立性声明与基线确认

本验收员与 G-1/G-2 缺口的发现、修复实现、PM 裁决、两次复核、Window80 接线验收无任何既往参与；本次验收只读被验收提交与代码，不改任何代码与已有文件，未提交、未 push、未开 PR，未碰 `reviews/` 下的冻结证据与复核输出，未碰凭证，未调外部模型，未启动 Resident。

基线确认：

- `git log`：本地 HEAD `cc42c1a`，其下 `e52878e`（修复提交），父提交 `1bd723f`（PM 裁决治理提交）。
- `git show --stat e52878e`：3 个文件，178 行新增、1 行删除——`src/aios_core/query/search.py`（+3）、`src/aios_core/runtime/turn_runtime.py`（+18/−1）、`tests/runtime/test_window80_gaps_g1g2.py`（新建，158 行）。
- Trailer：`Authorized-Task: PM-WINDOW80-GAPS-G1G2-001`，与 `governance/baseline.json` 登记的任务一致。
- `git diff 8317769..e52878e --stat`：10 个文件，其中 7 个是 PM 裁决治理提交（`1bd723f`）的治理/文档/复核文件，代码改动只有上述 3 个修复文件——修复提交本身未顺带改别的东西。
- 验收期间工作区无未提交改动（除 `reviews/` 下的既有未追踪复核/验收目录外）。

## 1. 逐项结论

| # | 验收项 | 结论 | 一句话证据 |
|---|---|---|---|
| 1 | G-1 修复：三类产物可关键词检索 | **PASS** | 独立复现 5/5 关键词命中（与 shipped 测试不同的 fixture 与关键词）；未修树上 0/5 |
| 2 | G-2 修复：写入失败可观测、整轮不中断、正常写入不变 | **PASS** | 独立复现：失败时计数 1、warning 带 exc_info、不抛错；正常写入计数 0、无 warning、经验落库 1 条；未修树上无计数器属性 |
| 3 | 回归测试：2 个新测试通过且为真回归测试 | **PASS** | 修复树 2/2 通过；未修 worktree（`e52878e^`）上 2/2 失败 |
| 4 | 改动范围：仅 3 文件、带 trailer、无顺带改动 | **PASS** | `git show --stat` 与 trailer 核对一致 |
| 5 | 全量快检：`tools/check.py --quick` 通过 | **PASS** | 552 passed、3 skipped（live provider）、治理 PASS、VERDICT: PASS |

## 2. 逐项证据

### 2.1 G-1 修复（PASS）

修复内容（`git show e52878e -- src/aios_core/query/search.py`）：`_TEXT_FIELDS` 白名单补了三行——`narrative_segment: ("title", "description")`、`dimension_curve_point: ("anomaly_description",)`、`tool_proposal: ("capability_gap", "expected_benefit", "validation_plan")`。

独立复现（验收员自写脚本 `/tmp/repro_g1.py`，fixture 与关键词均与 shipped 测试不同）：

- 白名单检查：三类键均存在，字段与修复内容一致。
- 种子数据：`nsg_harbor_lighthouse`（标题 "Harbor Lighthouse Log"、描述 "night watch beacon calibration"）、`dcp_sensor_drift`（异常描述 "sensor drift after heat wave"）、`tpr_offline_export`（缺口 "no offline export"、收益 "faster field sync"、验证计划 "pilot with two crews"）。
- 修复树结果：`co_search(["lighthouse"])`、`["beacon"]`、`["drift"]`、`["offline"]`、`["pilot"]` 全部命中目标对象，**5/5**。
- 未修树结果（`git worktree` 建于 `e52878e^` = `1bd723f`，shipped 测试文件复制进去跑）：白名单三类键全缺失，5 个关键词 **0/5** 命中。唯一相关命中是 `["drift"]` 命中了 `dim_sensor_health`（DimensionDefinition 的描述含 "drift"，该类型早已在白名单内）——曲线点本身未命中，符合预期。

### 2.2 G-2 修复（PASS）

修复内容（`git show e52878e -- src/aios_core/runtime/turn_runtime.py`）：第 12 行加 `import logging`；第 182 行加 `_LOGGER = logging.getLogger(__name__)`（与 `context/controller.py`、`runtime/resilient_handler.py` 的仓内惯例一致）；`__init__` 第 464 行加计数器 `self.experience_record_failures = 0`；`_record_turn_experience` 第 3037–3046 行把裸 `except Exception: pass` 改为计数 +1 并记一条带 `exc_info=True` 的 warning 日志（`"failed to record turn experience (style=%s, reaction=%s)"`），整轮仍正常完成。

独立复现（验收员自写脚本 `/tmp/repro_g2.py`，用与 shipped 测试不同的失败替身 `ValueError("independent repro failure")` 与不同的输入）：

- 正常写入（真实 tracker）：计数保持 0、无 warning、store 内新增 `CommunicationExperience` 1 条——**正常行为未变**。
- 失败写入（替身恒抛错）：无异常上抛、计数变为 1、新增 warning 恰好 1 条、文本含 `failed to record turn experience`、且 `exc_info` 非空。
- 复现中途一度出现真实 tracker 写入失败（计数 1、warning 1）：原因是验收脚本初版把 observation 种子放在 `user_9`，而 runtime 默认 `subject_id='user_1'`，`CommunicationExperienceService._validate_real_feedback`（`service.py:85`）按 subject 域校验拒绝，报 `ValueError: communication feedback crosses the runtime subject scope`。这是脚本自身的 subject 错配，不是修复的问题；修正 subject 后正常写入通过。附带证明：修复后的机制能把一次真实的校验失败变成可观测的日志 + 计数，而不是静默吞掉。
- 未修树结果：`FusedTurnRuntime` 无 `experience_record_failures` 属性（`AttributeError`），失败写入不可观测。

### 2.3 回归测试（PASS）

- 修复树：`pytest tests/runtime/test_window80_gaps_g1g2.py -q` → `..`，**2/2 通过**。
- 未修树（`/tmp/aios-g1g2-unpatched` worktree，`e52878e^`）：同一测试文件 **2/2 失败**——G-1 无关键词命中；G-2 在 `assert runtime.experience_record_failures == 0` 处报 `AttributeError`。是真回归测试。
- 验收员的独立复现脚本（`/tmp/repro_g1.py`、`/tmp/repro_g2.py`）在修复树上全部通过、在未修树上全部失败，与 shipped 测试结论一致。

### 2.4 改动范围（PASS）

- `e52878e` 只改 3 个文件（见 §0），无 `reviews/`、无治理文件、无其他源码改动。
- 提交信息带 `Authorized-Task: PM-WINDOW80-GAPS-G1G2-001` trailer；`check_baseline.py` 由 PM 侧复核为 PASS（验收员复核快检时治理亦 PASS，见 §2.5）。

### 2.5 全量快检（PASS）

验收员在本地 HEAD（`cc42c1a`）上用仓库自带 venv（`~/workspace/aios/.venv`）跑 `tools/check.py --quick`：

- `tests: 552 passed, 3 skipped`（3 个跳过均为 live provider 测试，需真实端点）
- `governance: PASS`
- `VERDICT: PASS`

与实现方报告的数字（552 passed / 3 skipped）一致；相对修复前基线 550 passed，+2 正好是两个新回归测试。

## 3. 测试记录汇总

| 测试 | 修复树 | 未修树（`e52878e^` worktree） |
|---|---|---|
| shipped 回归测试 `test_window80_gaps_g1g2.py` | 2/2 通过 | 2/2 失败（G-1 无命中；G-2 `AttributeError`） |
| 验收员独立复现 G-1（`/tmp/repro_g1.py`，5 关键词） | 5/5 命中 | 0/5 命中 |
| 验收员独立复现 G-2（`/tmp/repro_g2.py`，正常 + 失败） | 正常：计数 0、无 warning、落库 1 条；失败：计数 1、warning 1 带 exc_info、不抛错 | 无 `experience_record_failures` 属性 |
| `tools/check.py --quick` | 552 passed、3 skipped、治理 PASS、VERDICT: PASS | 未跑（快检针对当前树；未修树回归已由上两行覆盖） |

未跑：全量 `pytest tests`（太慢）、live provider 测试、模型调用、Resident 启动、live 重启探针（G-3，另有安排）。

## 4. 新发现的问题

无 FAIL 级问题。2 项既有小问题（实现方已报告，验收员独立确认，均不阻塞本次出口）：

- **N-1（小）**：`_TEXT_FIELDS` 里 `communication_experience` 键重复出现两次（修复树 `search.py` 约第 59 行与第 71 行，值完全相同）。验收员在未修 worktree 上同样查到两处（第 59、71 行）——是**修复前就存在的问题**，本次修复未引入，dict 去重后无害。
- **N-2（设计边界，非本次任务）**：工具提案的 `use_cases` / `current_limitations` 与叙事段的 `theme_tags` 是 list 字段，`_index_row` 只取 str 值，故仍不在关键词索引内。如需覆盖要另立任务改索引器。

## 5. 裁决建议

1. **接受本次修复验收（ACCEPTED）**：G-1、G-2 均已修复并经独立复现验证，改动范围干净，测试与治理全过。
2. N-1、N-2 不阻塞：N-1 可在下一次顺手改动 `search.py` 时顺带去重（或单独立一个最小清理任务）；N-2 需另立索引器任务，不属于本次缺口。
3. 下一步由 PM 安排发布：`e52878e` 的 push 会触及 `src/aios_core/**`，将触发 `p16-convergence-gate` 在 main 上运行——合入后核对该 CI 运行结果。
4. 不建议因此重开审计基线——本验收只验证两处缺口修复，不涉及 R1–R9 语义证据；审计出口仍以 RV20261120-001 / RV20261120-002 的裁决为准。

## 6. 交付物

- `ACCEPTANCE_REPORT.md`（本文件）
- `SHA256SUMS`（已生成并自验通过）

验收员未改任何代码与已有文件，未提交、未 push、未开 PR，未碰凭证，未调外部模型，未启动 Resident。独立复现脚本在 `/tmp/repro_g1.py`、`/tmp/repro_g2.py`（验收员自有工作文件，不在仓库内）；未修树对照用的 worktree 在 `/tmp/aios-g1g2-unpatched`（验收后由 PM 侧清理）。
