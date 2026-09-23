# AIOS A01–A10 定向修复交接

日期：2026-09-24（Asia/Shanghai）

## 结论与范围

按用户授权，在 `arena/01a0cf7f-haneof-aios-core-v3-0` 实施十项 Core 缺陷的定向修复，并增加 **42 个正向 synthetic 回归用例**。本次最终运行 **507 passed in 57.98s**；日志和 JUnit XML 位于本目录。

- 修复基线：`849bfd41c623fb336b392a3e6e933cfad93620e9`。
- 既有审计的固定目标是 `2aae7a6f771276a6c2ccff212d7e5ff586804873`，相关 Core 与上述基线一致。
- 没有创建 PR、合并 PR、切换实施分支，亦没有修改 PR125 operator 工具、constitution、冻结对象契约或 production pin。
- 没有访问 private A、真实 sealed fixture/future、凭据或无关动画；没有启动真实 B/C、Resident 或真实模型。测试数据和模型响应均为人工 synthetic。
- 这不是“认知能力已满足宪法”、平台隔离验收、完整 preflight DONE/PASS 或发布批准。Resident/platform isolation 仍按既有 BLOCKED / launchable=false 处理。

## 十项修复与正向验收

| 编号 | 修复 | 对应验证 |
|---|---|---|
| A01 | 提取只读失效规划器，Claim 根修订与下游失效在同一 World CAS 事务提交；Policy 同步推进 revision/version/previous_version/rollback_pointer，不放宽模型校验器。 | Claim→CommunicationExperience→Policy 完整链；旧版本不变；Policy 后续重新评审可到 v3；SQLite 插入中途故障整批回滚；规划后并发写入被 CAS 拒绝。 |
| A02 | runtime 显式传入用户＋配对 AI-self 范围；依赖边主体和两端对象都验证范围。 | 用户 Claim 纠错使 AI-self 下游失效；伪装为本主体的跨用户边不能改写另一用户。既有“已前进的下游不覆盖”测试继续通过。 |
| A03 | Event transition 使用同一失效规划器，把根事件修订和旧精确版本的依赖失效一起提交。 | rejected Event 的 Claim、Summary 不再 CURRENT 或进入当前搜索；历史仍可读取；并发 CAS 拒绝。所有合法 transition 保守触发旧版本依赖复核，不自动生成替代认知。 |
| A04 | Policy 注册/更新/回滚验证 evidence 是当前且 active；AI 学习仍保留真实结果类型/非 assistant 输出限制。CAS 在验证前捕获。 | 三种操作分别拒绝旧版本和最新 stale 版本；失效 Policy 不进入有效值或 cockpit；硬边界/工程限制无效时抛错而非宽松回退；新鲜证据可恢复认知策略。 |
| A05 | store 增加显式 `complete_commits=True`，读满分页末尾 World commit；index 锁内读取并发布 watermark，避免并发倒退。旧 bounded rows API 默认不变。 | 小 cap、混合批次、并发 catch_up、故障回滚；实际 50,001 对象单提交完整索引；重建修复人工模拟的旧漏建投影。 |
| A06 | Summary service/scheduler 添加显式 source_subject_ids，默认仅 owner；runtime 配置用户＋AI-self，同步给 C14 证据范围。 | AI-self 维度被发现并生成用户归属 Summary 和 C14 Wake；重复调度跳过不变窗口；其他用户材料被排除。 |
| A07 | 服务入口拒绝 truncated/unbound 输入；检查 pinned source 的主体、类型、当前有效性、文本/metadata/时间和原 World cut；提交前重选窗口，防止迟到资料或伪造省略；验证与提交受 CAS 保护。扫描达到 cap 时保守标记不完整。 | 直接调用不能发布截断摘要；拒绝过期、迟到、跨主体、伪造类型/文本/metadata、缺源、伪造 cut；饱和过滤扫描不冒充完整；resolved Event 仍可作为有效描述材料。 |
| A08 | 新 Summary ID 加 owner；prepare/commit/mark-stale 使用同一所有权解析。仅复用本主体且维度/粒度/窗口匹配的旧 ID。 | 两用户同一窗口得到不同 ID；本主体 legacy ID 原链向前更新；另一主体不得覆盖或 stale 该 legacy 对象。 |
| A09 | 同一 World SQLite 中增加 durable turn admission 表，先原子占用主体/session/turn，再进入任何 turn 副作用；完成重入、输入冲突、执行中/中断分别抛类型化异常。 | 同进程与重启后 completed 重试不新增模型调用或计量；并发拒绝；模型异常、assistant 写入失败后不盲重跑；只有 user 预入库仍允许首次推理；旧 assistant 已存在也拒绝重跑。 |
| A10 | 递归 DFS 改为显式栈，保留精确版本节点和 cycle 路径。 | 1,100 节点无环链正常提交；长环仍拒绝且事务不改变 World；跨版本同 object_id 不被误判为环。 |

## 文件分组

- 失效传播：`src/aios_core/revision/{service,propagation}.py`、`events/service.py`。
- Policy：`src/aios_core/policy/service.py`，以及 runtime 有效策略上下文。
- Index：`src/aios_core/storage/sqlite_store.py`、`query/search.py`。
- Summary：`src/aios_core/summaries/{dimension_summary,scheduler}.py`。
- Turn admission：`src/aios_core/runtime/{turn_execution,turn_runtime,__init__}.py`。
- 图遍历：`src/aios_core/dependency/graph.py`。
- 新测试：`tests/integration/test_v3_audit_bugfixes.py`。
- 本目录为修复交接和测试回执，不是生产放行凭证。

## 兼容性、升级和明确限制

### 索引

1. 已由旧 bug 产生的“watermark 已当前但投影漏行”不能靠新 `catch_up()` 猜出缺失。部署方须在停止相关写入/读取、备份且获授权的维护窗口，用修复后的 `WorldSearchIndex.rebuild()` 从 World 重建派生索引。本次只对 synthetic 数据做了重建。
2. `catch_up(max_rows=...)` 中 max_rows 现在是软批量目标，单个原子 commit 可以超过它。当前方案会在内存中处理完整边界 commit；没有声称实现无限规模流式处理。
3. 并发 catch_up 已验证；破坏性 drop/rebuild 仍应离线进行，不宣称支持与业务并发重建。

### Summary

1. `DimensionSummaryInput` 新增 owner `subject_id` 和 `include_summary_sources`。历史缓存若没有 owner，必须重新 `prepare()`；不能直接重放未绑定输入。
2. 默认只读 owner；`source_subject_ids` / `propagation_subject_ids` 是受信任装配配置，不应作为任意模型传入的提权参数。本改动不声称实现共享 AI-self 主体的多租户架构隔离。
3. 新对象用主体范围 ID；已有且归属正确的 legacy ID 继续向前修订。不自动修复过去已发生的跨主体覆盖，也不改写历史。此类历史污染须独立审查后向前修复。
4. 来源窗口变化、截断或无法证明扫描完整时拒绝发布；调用方应重新 prepare/生成，不应把旧文本直接强制套入新输入。

### Policy / 失效传播

- 下游只被标为待复核，不机械生成“正确结论”。需要模型/授权主体重新审查并以有效证据向前修订。
- `list_current()` 仍可列出最新 stale 对象供审查；“最新”不等于“有效”。运行时使用 `is_effective()` / `effective_value()`，不会把 stale 值作为指令。
- 无效认知策略使用调用方默认值；无效硬边界/工程限制抛 `PermissionError`，不能借默认值静默放松限制。
- 本修复防止新失效发生后的继续使用，不声称自动清理所有旧数据库中已经污染的传递依赖链。

### 整轮重试

可从 `aios_core.runtime` 导入：

- `TurnAlreadyCompleted`：已有输出/已完成，不返回伪造的 `FusedTurnResult`；异常带 `assistant_ref`，可按引用读取已有输出。
- `TurnInputConflict`：同一已占用 turn 身份被不同 user_input/occurred_at 使用。
- `TurnExecutionInDoubt`：运行中或上次尝试中断，禁止盲重跑；可能带已有 assistant_ref。
- 公共父类 `TurnExecutionRefused` 提供 `state` 和 `assistant_ref`。

表 `runtime_turn_executions` 是同一 World SQLite 文件中的增量 runtime 状态，不修改冻结 WorldObject schema。普通数据库备份会包含它；自定义只导出 World 对象的迁移程序需额外审查此表。

这是 admission/re-entry 保护，不是完整执行结果 replay 或一般 mid-phase crash recovery。claim 后的异常不自动删除占用、不自动重试。即使异常发生在模型调用前，也可能保留保守的 uncertain 状态，需要人工/授权恢复设计。旧版本只见 assistant 输出时报告 `legacy_output_present`，不声称旧维护流程完整结束。

不保证任意文件系统故障、恢复到旧备份、复制分叉数据库或外部系统副作用的全局 exactly-once；不能以改 turn_index 或清空占用表来绕过不确定执行状态。Wake 的一般重入恢复不在此次 A09 范围。

### 冻结与 PR125

本次授权修改 Core 后，其 hash 已不同于旧冻结目标。**不得修改 pin 或绕过 production hash gate 来使旧 A/冻结包“通过”。** 正式使用前须由获授权流程独立审查、重新确定冻结版本与重新验收。

PR125 新 head `941a69742ec7d47f73298e4f1f567d2616615493` 的 operator 修改未纳入本修复或复核。旧三个 operator 问题继续按 PENDING_TARGETED_REVIEW，而不是宣称本次已修复或仍未修复。

## 验证方法与精确范围

当前分支可复现的主要命令（Python >=3.12，pytest 8、pydantic 2）：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src python -m pytest \
  tests/unit tests/runtime tests/integration -ra
```

本次最终合并运行的组成：

- 当前 checkout：367 既有 unit/runtime/integration + 42 新测试 = **409**。
- 旧固定 `2aae7a6f771276a6c2ccff212d7e5ff586804873` 的安全导出：98 个 synthetic preflight，用修改后的 checkout Core 运行兼容性回归。
- 合计 **507 passed, 0 failed, 0 skipped**，CPython 3.12.11 / pydantic 2.13.5 / pytest 8.4.2 / SQLite 3.40.1。

最终进程在运行 pytest 前明确断言 `aios_core.runtime.turn_runtime.__file__` 指向本 checkout，而不是旧 export 的 src。完整回执在 `validation.txt` 与 `results.xml`；`manifest.json` 包含修复源文件/测试/文档/回执 SHA-256。

98 个旧 preflight 不在本分支的测试树，不能只运行上述本地命令便声称重新得到 507 项。它们的通过也不能代替 PR125 新 operator 测试。没有运行 `tests/habitation`、真实 provider 或真实资源隔离实验。

## 给接手 AI

1. 只从 `arena/01a0cf7f-haneof-aios-core-v3-0` 提取包含本文件的修复提交；核对基线与 `manifest.json`，先独立审查 diff。
2. 合并/提取时保留目标分支上的 operator 新工作，不用本分支全树覆盖 PR125。建议按单个修复提交提取，而不是把审计基线当新版 operator。
3. 在目标组合上重新运行这 42 项和既有回归；若目标带新 operator，再单独跑其最新测试并复核旧三个 operator 问题。
4. 在你的工作流程中创建 PR，说明上面的新异常/API、离线索引重建、Summary legacy 行为与冻结阻断。本会话没有创建 PR，也没有给任何合并/真实试验放行。
