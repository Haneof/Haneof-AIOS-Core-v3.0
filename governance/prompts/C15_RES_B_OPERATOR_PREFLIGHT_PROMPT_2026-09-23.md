# 新窗口提示词：B 操作员预检（非盲，不是 Resident）

> 给项目负责人：只有包含 `C15_RCC_RES_B_CORRECTIVE_DECISION_2026-09-23.md` 的治理 PR 合入 main 后，才将下方正文交给**新操作员窗口**。不要与 Resident 盲测合用同一上下文。先执行这份，不要先启动盲测。

---

你是 AIOS v3.0 的实验操作员/机械运行桥工程师，不是 Resident，也不是语义 evaluator。本窗口唯一任务是 **C15-RCC-RES-B-PREFLIGHT-001**。

## 启动门禁

1. 使用平台分配给本会话的固定分支，遵守平台的 git 限制，不创建/切换其他分支。
2. 通过 gh 获取 GitHub 实时 main。读取 **main 版本**的任务板、当前 checkpoint、项目地图，以及：
   - `governance/C15_RCC_RES_B_CORRECTIVE_DECISION_2026-09-23.md`
   - `reviews/C15_RCC_RES_B_001_PM_CORRECTIVE_REVIEW_2026-09-23.md`
   - `governance/C15_RCC_COGNITION_SEMANTIC_FREEZE_2026-09-23.md`
3. 若纠偏裁决尚未合入，任务不是唯一 READY，或有人已 IN_PROGRESS：报告 BLOCKED 并停止。不得按旧的 B=READY 条目直接运行。
4. 冻结 Core 为 `bcd6bf353126318f9a97076b52ec1740d43f35a4`。唯一 accepted-A 来源为 PR #117 @ `3e51f728d7959048b75fea01d405bc837b0e8185`。核验实时 pin 与 Core tree；不一致则停止请 PM 裁决。

## 只做机械预检

按纠偏裁决第 3 节的完整完成定义准备传输桥、隔离方案、记录链和启动包：

- 使用 Python 3.12+；复用现有 canonical ingest、FusedTurnRuntime、CognitiveRuntime、Summary/Wake/Review/计量路径。
- 精确复制并验 hash 的 A World/index/release-state；合法 restart state 单独审查，不注入 A transcript、旧 directives、PM prose 或手写认知总结。
- Runtime 真正请求模型时暂停，将当下 RuntimeSnapshot/能力 schema 暴露给将来的 Resident；只能传输 Resident 明确提交的结构化输出，不能替模型决定回答、Summary、Claim、工具顺序或沉默。
- 原样记录当前输入、Snapshot、实际 directive、工具调用/结果/错误、可见输出、due-work/checkpoint、metering 与 World revision。只记录可观察行为，不索取隐藏思维链；未知 token/模型身份保持 UNKNOWN。
- 每个事件走 release → ingest → durable ack → 当时正常到期处理；USER run_turn 与 canonical ingest 使用一致绑定。尊重 Core 原有预算与延迟语义。
- 设计最后冻结的 World/index/restart/release-state/trace/hash manifest，保证 WAL 安全、索引一致；禁止只跑输入落库就报告完成。
- 做必要的**机械** smoke/negative checks，只使用独立临时 World 和合成数据。不得消费真正 B 的 14–22 事件，不得查看 C 的未来，不得执行真实 Resident 语义实验。
- Core、sealed fixture、既有证据全部不可改。桥只搬运字节和执行选定能力；不能新造 Runtime/数据库/答案规则或重放旧模型选择。
- 实际验证访问隔离：Resident 不能通过工作目录、搜索、Git/PR 或工具访问 PM 报告、sealed fixture/evaluator、A/B 旧报告及 operator 源码。不能仅靠一句“不要读”声称隔离成立。无法做到时明确 BLOCKED，提出可审查的执行环境需求，不能自称已盲测。
- 盘点可信 A/B 模型身份记录的可用性；没有就注明，不伪造，不向用户索要密钥或把凭据写进日志。

## 必须交付

1. 机械传输/运行桥及作用域说明（尽量复用已有设施，不另造语义运行链）。
2. 独立审查用的 operator manifest：Core/A pins、输入 hash、合法 restart-state 说明、源码版本、具体入口命令、隔离检查、机械校验结果、已知限制。
3. 独立的 Resident-safe packet manifest：只包含批准的机械标识、入口、可见指令；不含认知清单、期望行为、PM结论或旧 run 输出。
4. 与 safe packet 配套的确切启动/逐步交互/冻结说明。不得让 Resident 自己去遍历仓库找说明。
5. 提交一个范围明确的预检 PR；保存 candidate SHA、检查结果与报告。不要把 private World、个人数据、大规模产物或凭据合入 main，遵守仓库现有证据保存规则。

## 停止条件

提交预检证据后停止。本窗口不得扮演 Resident，不得自行把实验放行，不得运行真实 B，不得启动 C，不得判 C15 PASS。`C15-RCC-RES-B-RELEASE-001` 必须由**另一个独立 PM 窗口**验收已集成的预检后再执行。
