# PM-AUDIT-C15-EVIDENCE-RECONCILIATION-001 — PM 复核任务发布

日期：2026-10-19（Asia/Shanghai）
角色：AIOS Core Delivery PM
授权依据：所有者在第一轮 PM 审核后要求“继续推进”；沿用既有 Core 完成计划的 PM 派工、治理、自审与集成权限。
**性质：治理控制与独立复核任务发布，不是新的技术验收 PASS。**

## 1. 生效与任务状态

- 本决定经普通治理 PR 合入 main 后生效；分支/PR 存在不表示已生效。
- 生效后的唯一当前任务：`PM-AUDIT-C15-EVIDENCE-RECONCILIATION-001`。
- 调度状态：`READY_FOR_ASSIGNMENT`；执行状态：`NOT_STARTED`；独立 Reviewer：`UNASSIGNED`。
- 当前 PM 不是原实验的新独立 Reviewer，也不是 fresh Resident。
- 本平台没有可调用的独立代理调度工具。本次提供可直接交给独立新窗口的完整任务包，不声称已启动其他 AI。
- 不占用或重命名既有 WINDOW 编号；先保留 Window 80/81 原始记录，由本 Task ID 明确当前控制。

## 2. 为什么现在插入复核

第一轮审核绑定 `24193afd949e39a112f873218fc98199265df7fa`。推进时远端 main 已到：

`259d035386ea203981c6247eeb4433dbfd8eed3f`

新增的 Window 80 不是治理-only：它增加 NarrativeSegmenter、DimensionCurveTracker、ToolProposalPipeline、ExperienceTracker，以及四个产品测试文件并修改 communication 导出。不能沿用第一轮的“此后无产品实现变更”作为现在的事实。

旧 C15 已关闭的**记录事实保留**，不能静默删除或改写；但以下内容需要独立核证：

1. 原 R6 合同要求可证明的不同底层模型，已提交评估脚本仅核对不同 process/session UUID。
2. 其他认知轴的已提交检查不能单独推出其全部语义结论。
3. Window 69 原始验证、实际 Resident 调用路径、历史失败处置及运行身份差异需要对账。
4. Window 80 的新 Core 代码与此前 RC/Resident 证据之间需要明确影响判定、集成与独立接受状态。

详见：
- `reviews/AIOS_PM_PROJECT_AUDIT_2026-10-19.md`（固定旧基线的第一轮报告）；
- `reviews/AIOS_PM_PROJECT_AUDIT_WINDOW80_ADDENDUM_2026-10-19.md`（此次新基线补充）。

## 3. 当前 PM 控制裁决

| 对象 | 当前处理 | 不代表什么 |
|---|---|---|
| C15 Gate 0 原关闭收据 | 保留为已存在的治理记录；状态标注 `RECORDED_CLOSED / EVIDENCE_REVIEW_OPEN` | 不自动撤销所有证据、不自动认定所有轴 INVALID |
| 新的生产就绪/跨模型通过签署 | `HOLD_PENDING_INDEPENDENT_EVIDENCE_REVIEW` | 不是已证明安全漏洞或模型伪造 |
| Window 80 代码 | 保留 main 已有成果；`IMPLEMENTED / AUTHOR_REPORTED_TESTS / INDEPENDENT_ACCEPTANCE_NOT_ESTABLISHED` | 不回滚、不重写，不把作者收据冒充本轮复现 |
| Window 81 多模型/端侧/硬件推进 | `HOLD_PENDING_EVIDENCE_AND_CORE_IMPACT` | 不清除历史计划；不永久否定未来平台适配 |
| 新 Resident A/B/C、cursor reveal、改 fixture | 本任务无授权 | 不能以复核任务名义启动实验或改写冻结包 |
| Core/UI/硬件新开发 | 本任务无授权 | PM 复核不是顺手修复或扩功能窗口 |

这是 PM 对**下一步放行权限**的管理控制，不是替独立 Reviewer 签发新的技术验收结论。

## 4. 输入与漂移控制

机器可读基线：
`reviews/PM_AUDIT_C15_EVIDENCE_RECONCILIATION_001/BASELINE.json`

输入工程候选及 Resident evidence exact heads：

| 角色 | PR | exact HEAD |
|---|---|---|
| Option B | #390 | `52d169e8fb96248b058ab3685d9dcb1f6cbce204` |
| Resident A | #392 | `2d92328205e16ec8b5317eaca8f3b666656ad09b` |
| Resident B | #393 | `302dab2565f61dd37ca57195bae7ed9337cdfede` |
| Resident C | #394 | `6cd89d6e3761347487946ca95e59bae380a3ae46` |

Reviewer 必须重新读取实时 main，核对受保护树和选定合同 blobs，不能把本文件中的 SHA 当永久 live main：
- main 仅有治理后继且受保护对象/合同一致：登记新 main，确认任务未被 supersede 后可继续。
- 受保护对象或任一候选 head 改变：`REVALIDATION_REQUIRED`，停止，不替换哈希洗绿。
- 合同变化：`PM_CONTRACT_ADJUDICATION_REQUIRED`，停止。
- 发现另一执行者或更高优先任务冲突：`OWNER_RECONCILIATION_REQUIRED`，停止。

## 5. 实际任务与完成定义

执行提示词：
`governance/prompts/PM_AUDIT_C15_EVIDENCE_RECONCILIATION_001_2026-10-19.md`

独立 Reviewer 只读取得现有证据、做静态/数据核对并给出：

1. 精确候选/运行/接受/集成身份图及角色独立性声明。
2. R1–R9 要求到具体证据的逐项矩阵；R6 缺少可信差异证明时，按原合同记录 `PARTIAL / INSUFFICIENT_EVIDENCE`。
3. 原始安全验证可获得性、实际 Resident provenance 路径及旧失败处置表。
4. B/C 身份差异的事实核对及所需勘误，不改原始包。
5. Window 80 变更影响矩阵：可沿用哪些旧证据，哪些未知，哪些需要新验证；检查是否有正常 Runtime/Capability 路径证据，而不是只看模块单测。
6. PM 审核项 `PM-AUD-01..06` 的 supported / unsupported / unknown 处置。
7. 局限、脱敏来源及校验清单。

“全部事项都关闭”不是完成本任务的必要条件。合法出口包括：
- `REVIEW_COMPLETE / EVIDENCE_SUPPORTED`：材料足够，交 PM 正式裁决；仍不得自称 release approved。
- `REVIEW_COMPLETE / GAPS_CONFIRMED`：明确缺证或合同不一致，交 PM 安排下一单任务。
- `BLOCKED / EVIDENCE_ACCESS_REQUIRED`：准确列出缺少的非秘密材料与合格提供角色。
- `REVALIDATION_REQUIRED`：身份/合同漂移或归属冲突，停止。

不得用 UNKNOWN 改成 PASS。Reviewer 无权修改 Core、重跑测试/模型/Resident、接触私钥、合并 PR，或直接进入 C16/P16/P17/平台接入。

## 6. PM 接收后的唯一后续

PM 收到耐久的独立输出后再作裁决：
- 可以补证闭合的，不重做工程、不重跑所有实验。
- 确认代码缺陷的，另开最小工程任务，再经独立验收。
- 需要新的软件 Gate/RC 影响验证或模型身份实测的，另开精确冻结、环境与权限完整的任务；本窗口不顺手执行。
- 只有证据与依赖充分闭合，才放行既有 C16 反馈链；硬件与产品层按 Core 计划单独后置。

## 7. 本次治理自审与不变量

这是普通 PM 治理，作者明示自审；**不把该自审称为独立技术验收**。

本次允许的交付仅为任务板/checkpoint/master map 的当前入口、审核/补充报告、此发布记录、提示词和公开非秘密基线清单。产品实现、产品测试、工作流、包配置、全部旧 Resident/fixture/审查原始证据零修改。HTML 不提交。

未运行测试、未派生或调用模型、未访问 Operator 凭证、未替独立 Reviewer 产出结果。最终集成与待启动状态以远端真实 PR/commit/Issue 收据为准，不从这份预集成文件推断已完成。
