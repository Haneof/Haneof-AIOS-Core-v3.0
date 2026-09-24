# AIOS 3.0 Core 完成阶段计划与 PM 移交

日期：2026-09-24。所有者本轮指令：先完成 AIOS 核心开发，UI 不进行开发；将阶段任务写入 Git，由接任 PM 安排其他 AI 实施与验收。

本计划是范围和完成定义；唯一状态/派工队列仍为 `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`。本治理变更合入 main 后生效；分支或 PR 存在不代表下游已放行。宪法仍以 `docs/constitution/AIOS_v3.0_Fused_Baseline_Registry.md` 为入口，不由本计划改写。

## 1. 最终交付与排除项

目标是可独立安装、启动、停止、重启恢复、接入模型和事实输入、持续处理到期工作、持久化和修正认知的 **headless AIOS Core**。用户交互可经最小 CLI/服务接口完成，接口复用当前 FusedTurnRuntime/CognitiveRuntime，不另造第二个 runtime 或世界数据库。

明确不开发：网页/App UI、Launcher、数字人、动画、视觉设计、手环硬件、Android ROM 或设备专用适配。P18/P19 保持后置。为验证 Core 所需的最小文本命令、模型适配、运行配置和进程生命周期属于 Core 交付，不属于 UI。

完成必须同时有：代码/安装运行证据、真实模型语义证据、持久化与恢复证据、资源边界、发布说明。不能用阶段数量、测试数量、模拟天数替代实际完成判定。

## 2. 接手现场：已做成果不得重做

审查 main：`6924d8b50cf08eb632f9cfa513a3cc49faad0c72`。接任者必须重新 fetch，不把本 SHA 当永久施工基线。

- 全分支盘点快照：153 branches，2,086 个分支可达去重 commits，main 452 commits；117 PR：83 merged、18 open、16 closed-unmerged。此为提交/范围盘点，不是每个历史提交的逐行代码认证。
- P0–P15 机制已有实现与历史 Gate；C13/C14 已有收口记录。先确认现存实现，再对真实缺口开任务。
- #110/#111/#113 加固通过 #115 集成；`8ff756c5` 与 `bcd6bf3` 的 src/tests 相同。开放 PR 不等于功能缺失。
- #127 已独立合入十项 Core 修复；#126 head `8e31deca` 与 main 的 Core tree 同为 `7db4f72e7b3c29c74082f9984141159f8f1d6071`。#126 剩余工具/CI 差异单独裁决，不整包再次合入。
- #127 合后证据：`168a09c8569cd1bc176bbccf7dc81ee97c59b3f4:reviews/AIOS_MAIN_ACCEPTANCE_2026-09-24/`；不能因证据未在 main 而重复实现修复。
- #125 head `b14b5d84b6a4c843dc7dc38cde51f08a92fac86b`：41 个独有提交、64 个变更文件，Core 仍为历史 `bcd6bf3` 的 tree `eed27d58041dbaf2ceb0a65c1305bb332aef082e`。现状是已有工程成果且回归失败，不是未开始。
- #125 exact-head workflow 35952205324：128 passed / 3 failed。失败为中间到期 Review、旧 Wake 看见未来输入、预算延迟调度；35952205318 full regression 同三项失败。已读取原始 job logs 107482934617/107482934372。不得用旧绿灯覆盖。
- `b14b5d84` 提交说明记载 B14 释放/ACK/等待 Summary 的尝试；只证明存在该陈述，不代替 contemporaneous trace、World、授权和完整性验收。不得写“从未启动”，也不得写“B 已通过”。
- canonical A #117 保持历史已接受身份；旧 B #121 仍 FAILED / NON-CANONICAL。新 Core 不自动继承旧实验的全部语义结论。
- #125 `PROTOCOL_REVISION.md` 记载所有者选用“规则约束＋过程审计”。接手时统一该协议与正式治理；不再额外强求硬隔离，但不得声称已证明硬隔离或没有日志就证明无污染。PM/工程上下文不能扮演 fresh Resident。
- 长期线有 46 天、229 天等分支自报与大量 trace；`659d1851` 分流报告尚未合入，其 14 天/68-call 裁决是待处理来源，不直接当当前正式验收。不同 World/人生不能加总。
- 四条鹈鹕动画分支排除 Core 路线；保留，不在本计划中删除分支或历史。

## 3. 阶段与可派发任务

每一工程任务由一个执行窗口负责；PM 可跨任务持续协调。表中 BLOCKED 是依赖状态，不能自行跳过 Gate。缺陷工程允许在发现后进入最小修复→独立复核，不为开新阶段重复重构。

| 阶段 / Task ID | 负责人 | 范围及依赖 | 交付与验收出口 |
|---|---|---|---|
| S0 `CORE-BASELINE-001` | Release PM / Architect | 本治理集成后唯一 READY；盘点 live main、#125/#126 最新 heads、已尝试 B 的可用现场与任务所有权 | 将开发 main、历史实验 pin、拟新实验基线分开登记；形成变更影响矩阵；明确 A 原包是否只能历史保留、是否需要 fresh A；固定一条集成路线；同步板/checkpoint/map。不得仅替换 hash 来放行旧包，不执行 Resident |
| S1 `CORE-OPERATOR-001` | Test Infrastructure Engineer，独立 reviewer 验收 | S0 后，从 #125 已有成果定向收口，复用原 B-PREFLIGHT 任务，不创建第二桥 | 先在固定候选复现三项已知失败，再修时钟/到期工作/入库/ACK/恢复阶段；中间 tick 不丢，旧 Wake 不见未来，合法预算延迟保留；断点不推断模型已执行；旧 trace 不覆盖；fixture/pin 错误拒绝；零释放检查与真实运行分离；截止 22、时钟与会话绑定一致；当前候选专项及相关回归通过，原始证据保全 |
| S1 `CORE-GAP-AUDIT-001` | Independent Core Architect | S0；只读当前 Core、迁移矩阵、历史发现和实测证据 | 输出宪法要求→实现→现有测试→实际剩余缺口矩阵；逐项 STILL_OPEN / ALREADY_FIXED / NOT_REPRODUCED / OUT_OF_SCOPE。覆盖 World/Index/Context/Summary/Evidence/Revision/Policy/Goal-Task-Action-Outcome/Wake/Review/Metering；不借旧报告批量重做 |
| S2 `CORE-GAP-FIX-NNN` | Core Engineer + 独立 reviewer | 仅由上一审计或合法新复现激活，每项单独任务 | 复现、最小修复、针对性回归、相关 Gate、合后验证；无缺口则记录 NOT_REQUIRED，不制造代码工作。涉及 Core 语义变更时更新影响范围和实验重验要求 |
| S2 `CORE-HEADLESS-001` | Runtime Integration Engineer | S0、缺口审计；先盘点已有入口，复用 P16 model adapters 的适用部分 | 最小安装/配置/CLI 或服务入口；用户输入/外部事实走现有 ingest，模型仅走正常能力；服务处理时钟/到期队列，进程退出与重启、single-writer、日志、错误、计量可核对；不写 UI；不在此阶段消费真实 sealed C15 fixture |
| S2 `CORE-RECOVERY-001` | Storage / Runtime Engineer + reviewer | S2 功能候选 | 对新 turn admission、未知执行状态、World/index/WAL、模型超时、写入失败、重启、备份恢复和 schema 升级作故障验证；明确自动恢复/拒绝/人工恢复边界，不能清表或换 turn_id 绕过；旧漏索引需可审计离线重建，历史 World 不改写 |
| S2 `CORE-SCALE-001` | Performance Engineer | S2 功能候选；#112 仅为历史线索 | 当前候选可复现实测：分层规模、数据分布、机器/内存、冷热启动、p50/p95、RSS、SQL 数、摘要/Wake积压与 token/cost（未知保持未知）；测量前冻结预算/目标规模，不事后移动门槛；超预算开最小任务，不擅自改认知算法 |
| S2 `CORE-RC-FREEZE-001` | Release PM + independent reviewer | 所有激活缺口、HEADLESS、RECOVERY、SCALE 已接受 | 冻结精确 Core tree、operator/packet、依赖与运行配置；全软件回归和 clean-install headless smoke；保存 source/构建/测试 manifest；明确旧 A 使用裁决与必要 fresh A/fixture 任务。只冻结，不运行 Resident |
| S3 既有 C15 链 | operator、fresh A/B/C、独立验收及 evaluator | RC freeze；必要 A 任务先插入正式队列 | 复用 B-RELEASE→B-RERUN→B-ACCEPT→MODEL-ATTEST→C→EVAL→CLOSE；A 是否重跑以影响裁决为准；R1–R9 分项证据，真实模型逐次判断，不设 Claim 配额；身份不足不得假称跨模型通过；任何运行中 Core/桥变更需影响复核 |
| S4 既有 C16 链 | PM / feedback engineer / Resident / reviewer | C15 PASS | RULE→IMPL→RES→PM→ENG-PILOT→CLOSE；系统改进提案留在 non-world，不污染用户世界；真实反馈→独立复现→工程修复→Gate→Resident 再验证；不让 Resident 自改自验 Core |
| S5 既有 P16 链 | Campaign PM / fresh Residents / evaluator / red team | C16 PASS，pilot 修复后的候选重新验收 | TRIAGE→CAMPAIGN→逐 segment→YEAR-AUDIT + provider runs→EVAL→REDTEAM→CLOSE；已有证据按 exact head 裁决，避免重复；沿用现行协议年度门槛，不用虚拟日期跳跃/脚本回答冒充；缺陷回流后只重验受影响证据，保留全部历史 |
| S6 `P17-ENTRY-001` / Core release closure | Release Engineer + independent reviewer + PM | P16 PASS，发布候选固定 | 可复现构建、依赖锁定、clean install、公开文档、配置示例、模型/输入适配说明、启动停止、数据路径、备份/恢复/迁移与回滚限制、资源预算、已知限制、完整 CI 及端到端真实模型证据；审查后形成 Core release verdict。发布/tag 等按仓库权限与明确授权执行；无 UI |

S2 工程完成只是 SOFTWARE_RC，不称 CORE_COMPLETE。只有 S3–S6 的适用证据全部接受，P17 裁决 PASS，才可称本轮 Core 完成。现有 C15/C16/P16 的语义要求不因本计划取消。

## 4. 调度、隔离与验收规则

- 唯一派工表继续使用原 task board；本计划不能成为第二 READY 队列。历史单窗口限制保留给执行 AI；**接任 PM 可跨阶段连续分派、验收、更新治理，不要求每安排一个任务就新开 PM 窗口**。
- 当前先 S0；之后可并行只读 GAP-AUDIT 与 operator 修复。并行工作必须有不同 owner/分支/路径，所有集成只有一位 PM，禁止多个 Resident 同时写同一个 World。
- 若平台允许子代理，PM 可以实际调度工程/审查代理；fresh Resident 必须新上下文并只给安全包，不能继承 PM 报告、未来 fixture 或旧答案。无可调用调度功能时输出可直接转交的单任务提示词，写明未启动，不能假称已派发。
- PM 负责计划、范围、依赖、治理集成和完成裁决；通常不代替工程 AI 写 Core，不代替 fresh Resident 生活。工程作者不作为其任务的独立 reviewer；普通治理文档可由 PM 明示自审，不发明额外批准环节。
- 任务派发至少含：Task ID、职责/禁任角色、live-main 查验、准确输入分支/head、依赖、范围/禁区、先复现、交付路径、Gate、证据、停止条件、谁验收。固定分支平台允许在该窗口分支落库，但不得混用他人 WIP；按审查过的提交定向集成。
- 工程 DONE：已合 main + 精确候选及合后证据 + task board/checkpoint 更新。故意不合 main 的 private World/evidence PR：按既有 evidence-only 协议固定 head 并完成验收治理即可，不强制合入数据。
- 失败与 skipped 分别报告；缺测不写 PASS；真实 provider/token/模型身份未知时 UNKNOWN。原始 CI、模型请求/输出、能力结果与错误保留，不索取隐藏思维链。
- 禁止批量 merge/close/delete 分支；历史重复实现可登记 SUPERSEDED，但删除/关闭不是本计划授权。不得自动触发公开 CI 读取真实 A、私有 World 或真实 future fixture。
- PM 每次汇报只写：已完成及证据、唯一当前任务、具体阻塞、下一验收出口。遇到真实权限/资源阻塞才向所有者提出最小具体问题，不反复请求已授权的常规推进。

## 5. Core 最终完成清单

1. 统一事实/认知/证据/修订链在实际运行中闭环，无第二真相库；旧证据可追溯。
2. 普通对话、Summary、Wake、Review 使用同一 runtime；合法沉默、用户投放与后台副作用边界正确。
3. Task 完成有真实凭据，外部 Action 仍需授权与 Outcome；重试/崩溃不伪造 exactly-once。
4. 上下文/跨会话/换模型的有效认知恢复、消费和纠错由独立真实实验验证。
5. headless 入口可安装运行，故障恢复和规模范围有证据、限制明确。
6. C16/P16/P17 达到各自完成定义，项目板与发布证据一致；P18/P19/UI 未被混入。

接任提示词：`governance/prompts/AIOS_CORE_PM_HANDOFF_2026-09-24.md`。
