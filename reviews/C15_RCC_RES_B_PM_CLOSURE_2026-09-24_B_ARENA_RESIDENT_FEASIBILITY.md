# B. Arena直接入住的数据流、权限边界和具体缺项 (PM收口 2026-09-24)

参考头: 5b5e2306c39b5b09b260de787403567a31d0efbd
真实Resident必须是新Arena窗口里的AI本人，不接外部LLM API，不要求用户提供endpoint/API Key。
已有通用传输保留，不标为已接通。HTTP作为AIOS工具接口可评估，HTTP调用外部模型不是本轮批准路线。

## 一页表格回答

| # | 问题 | 现状核实 | 哪些确实被阻止 / 哪些只是提示词约束或尚未验证 | 缺项归属 |
|---|------|----------|-----------------------------------------------|----------|
| 1 | 新Arena Resident窗口从哪里启动？是否连接仓库，初始工作区具体有什么？ | Arena Agent Mode 每个会话固定分支 `arena/<id>`，工作区根 `/home/user/Haneof-AIOS-Core-v3.0`，含完整仓库、.git、reviews/、governance/、src/、tools/ 等。`bash` 工具根在仓库根，可 `ls` 任意文件。`git` `gh` 已认证可用。`start_process` 可绑定 0.0.0.0 暴露 LIVE PREVIEW。无按窗口隔离的文件视图配置。 | **未阻止**: 仓库、PM材料、旧答案、未来fixture 均可读。仅靠提示词“不要读”属于自律，非隔离。 | 必须由Arena平台提供：per-window chroot / mount namespace / 工作区视图限制。当前无依据证明可用。 |
| 2 | Arena AI如何收到真实RuntimeSnapshot，又如何将本人生成的directive交回正常Runtime？不能由脚本生成、改写或补齐认知输出。 | 期望：Operator Driver -> RuntimeRecorder -> RuntimeSnapshot(plain) -> 安全包文件 `/tmp/resident_packet/<id>.json` (仅批准字段 user_input/wake_reason/cockpit/capability_catalog/capability_history/round_index/remaining_tool_rounds) -> Resident新Arena窗口读取 -> 本人真实逐次输出 ModelDirective JSON -> `/tmp/resident_response/<id>.json` (含 request_id/kind/input_sha256/output 绑定) -> Operator `directive()` 验证 -> Runtime 执行合法能力调用 -> trace.jsonl 记录。**当前**: 合成测试用 `ResidentBroker` HTTP POST 到 `SyntheticModelEndpoint`，返回静态 JSON，非真实认知。真实Arena窗口未启动，未验证真实Snapshot到Directive的往返。 | **脚本生成问题**: 现有合成端点是脚本代替认知，不符合“必须来自Arena AI真实逐次输出”。需新Arena窗口AI本人生成，但平台未提供该窗口的受限启动方式。 | 现有代码可完成：plain(snapshot)序列化、边界检查、directive验证、trace记录。必须由Arena平台提供：新窗口受限启动、仅暴露批准入口、安全包/响应文件管道、保证输出来自AI本人而非脚本。 |
| 3 | 它能使用哪些平台工具？对仓库、PM材料、旧答案、未来fixture的访问，哪些确实被阻止，哪些只是提示词约束或尚未验证？ | Arena工具：`bash`, `read_file`, `write_file`, `edit_file`, `start_process`, `stop_process`, `get_process_output`, `web_search`, `fetch_page`, `image_search`, `generate_image`, `add_voice`, `generate_speech` 等，所有窗口相同，无 allowlist。实测：`read_file reviews/internal_habitation/...` 成功，`bash git log` 成功，`gh pr view` 成功。`isolation_probe.py` 尝试 `unshare --user --map-root-user --mount --net --pid --fork` + `mount --bind` + `chroot` + `setpriv --no-new-privs`，在 GitHub runner 与 Arena 沙箱均报 `Operation not permitted`，返回 INCONCLUSIVE。 | **确实被阻止**: 无。**提示词约束**: “不要读PM报告、sealed fixture、旧报告、operator源码”等仅提示词，未验证。**尚未验证**: 无OS级阻止。合成 canary 探针可 PASS 于特权环境，但真实资源 `pm/operator/git_metadata/private_a/sealed_future/git_credentials/gh_credentials` 设计为 NOT_TESTED，`resident_arena_isolation BLOCKED`。 | 必须由Arena平台提供：per-window 文件系统、git/gh、env、工具 allowlist 限制，以及 unshare/mount/chroot 特权或替代隔离机制。当前无依据证明可用。 |
| 4 | 能否只提供批准的AIOS交互入口，保留Core合法能力调用，但不暴露额外operator材料？ | 期望：仅提供安全包入口，保留Core合法能力调用 (如 `FusedTurnRuntime` 能力执行) 经 Runtime 执行，不暴露 operator 私有 checkpoint、凭据、治理材料。现有代码：`_check_packet_boundary` 基于批准结构，禁止 `world_revision/index_watermark/release_sha256/driver_state/session/clock/private_world/world_index/release_state/operator/git_metadata/private_a` 等进入模型输入，禁止 governance 材料，凭据留 HTTP 鉴权层。**但**：该边界仅在 Operator 进程内检查，若 Resident 窗口本身可直接读仓库，则可绕过。 | **代码层面**: 结构边界检查可完成。**平台层面**: 无法保证 Resident 窗口不直接读仓库获取额外材料，因无文件系统隔离。 | 现有代码可完成：批准结构检查、凭据分层、合法能力保留。必须由Arena平台提供：保证 Resident 窗口仅能通过批准入口交互，无法直接访问仓库/PM材料/旧答案/未来fixture。当前缺失。 |
| 5 | 哪些条件可以由现有代码完成，哪些必须由Arena平台提供，哪些当前没有依据证明可用？ | **现有代码可完成**: - plain(RuntimeSnapshot) 序列化 - 批准字段边界检查 (user_input等7字段) - 禁止 operator 私有 checkpoint/凭据/governance - request_id/kind/input_sha256 绑定验证 - directive() 验证、错误传播、fail-closed - trace.jsonl 记录可观察行为 - WAL安全冻结、索引一致、hash manifest - 真实A 88/88 13→14 边界验证、model_requests 0、cross-process - 合成 canary 探针、合成传输测试 **必须由Arena平台提供**: - 新Arena Resident 窗口受限启动 (仅安全包可见) - per-window 文件系统视图 (chroot/mount ns) - per-window git/gh/env/工具 allowlist - 外部网络仅允许到 Operator broker - 保证输出来自AI本人真实逐次输出的管道 - 可验证的隔离证明 (非提示词) **当前无依据证明可用**: - Arena 是否支持 per-window 隔离？未在文档/工具中发现，实测 unshare 失败 - 是否可配置 Resident 窗口初始工作区仅含安全包？无依据 - 是否可阻止 Resident 窗口读 reviews/internal_habitation？无依据 | **缺项**: 平台能力缺失导致既定边界无法满足，明确交付后停止，不用更多模拟测试或外部API替代方案掩盖。 | 停止条件：已明确哪项平台能力缺失。 |

## 数据流 (期望，当前未实现)

```
Operator Window (arena/01a0cf25):
  Driver -> RuntimeRecorder -> RuntimeSnapshot
  -> plain(snapshot) + input_sha256 + request_id
  -> /tmp/resident_packet/<id>.json (批准结构，仅7字段)

Resident Window (new Arena AI):
  读取安全包 (唯一可读文件)
  本人真实认知生成 ModelDirective
  写入 /tmp/resident_response/<id>.json (绑定 request_id/kind/input_sha256/output)

Operator Window:
  load_and_verify response binding
  directive(output) 验证
  Runtime 执行合法 AIOS 能力调用 (保留 Core 合法能力)
  trace.jsonl 记录 (输入、Snapshot、directive、工具调用/结果/错误、可见输出、due-work/checkpoint、metering、world_revision)
  继续下一事件 release→ingest→durable ack
```

## 权限边界 (期望 vs 现状)

| 边界 | 期望 | 现状 | 验证方式 | 结果 |
|------|------|------|----------|------|
| 文件 | 仅安全包可读 | 全仓库可读 | 合成 canary + 实际 read_file 测试 | FAIL (未阻止) |
| 仓库 | 无 git/gh | git/gh 可用 | bash git log / gh pr view | FAIL |
| 历史证据 | 无 reviews/internal_habitation | 可读 | ls reviews/... | FAIL |
| 未来材料 | 无 sealed future / C | 可读若存在 | ls governance/ | FAIL (未阻止) |
| 工具 | 仅 AIOS 交互入口 | 全量工具 | 工具列表检查 | FAIL |
| 网络 | 仅到 Operator | 全外网 (web_search等) | socket 探针 | FAIL |
| 认知来源 | Arena AI 本人真实输出 | 合成端点静态 JSON | 检查 endpoint 代码 | FAIL (脚本代替) |
| 日志归属 | Operator 拥有 trace.jsonl | 符合 | 检查日志写入 | PASS (现有代码) |
| 凭据 | HTTP 鉴权层，不在消息/日志 | 符合 | 检查 Authorization header | PASS (现有代码) |
| 能力调用 | 保留 Core 合法调用经 Runtime | 符合 | 检查 Runtime 执行 | PASS (现有代码) |

## 具体缺项 (平台能力缺失)

1. **per-window 文件系统隔离**: 无 chroot/mount namespace  per-window 视图，unshare 需特权失败
2. **per-window git/gh 禁用**: 无配置禁用 git/gh
3. **per-window env 过滤**: 无过滤 GITHUB_TOKEN 等
4. **per-window 工具 allowlist**: 无限制工具为仅 AIOS 入口
5. **新窗口受限启动**: 无方式启动仅含安全包的新 Arena 窗口
6. **真实认知管道**: 无平台管道保证输出来自 AI 本人而非脚本
7. **可验证隔离证明**: 无 OS 级证明，仅提示词自律

**结论**: 既定边界无法满足，明确交付缺项后停止。不使用更多模拟测试或外部API替代方案掩盖。不启动真正Resident或擅自邀请新窗口。

## 保留 vs 暂停

- 保留: 通用传输代码 (resident_broker.py, transport.py, isolation_probe.py, 合成测试)
- 暂停: 外部LLM API方向 (不要求 endpoint/API Key，不实现 provider 原生适配)
- 不标为: Arena Resident 已接通/已隔离 (实际 BLOCKED)
- 不运行: 真实B/C
