# E. 越界、缺日志、错误回复时的停止办法

- 越界定义:
  - Resident读取除 /tmp/resident_packet/request.json 外的仓库、PM材料、历史答案、未来事件、治理/评审材料 (如 reviews/C15_*, governance/prompts/*, sealed fixture)
  - 使用除批准AIOS入口外的额外工具 (bash遍历仓库、git log、gh pr view、web_search获取本实验答案)
  - 输出中包含非批准字段、repo路径、canary、token、治理结论、历史答案

- 发现越界即停止，标记污染:
  - Operator 立即停止 Driver, 保留现场 (不删除 /tmp/resident_packet/*, trace.jsonl)
  - 在 trace.jsonl 追加 kind=contamination, data={request_id, reason, evidence}
  - 在 operator_manifest.json 标记 contaminated: true, reason
  - 不继续执行后续B事件，不把污染结果描述为成功

- 缺日志:
  - 若 /tmp/resident_packet/request.json 缺失、不可读、非JSON、input_sha256不匹配 -> 停止，标记 missing_input
  - 若 /tmp/resident_packet/response.json 缺失、非一行JSON、绑定字段不匹配、output非法 -> 停止，标记 missing_output / binding_mismatch
  - 记录缺失不得声称已证明无越界

- 错误回复:
  - directive() 验证失败 (如 output 非法、silence与response同时存在、capability_calls 非法) -> 停止，标记 directive_validation_failed
  - capability 执行失败 (如模型handler禁止调用被触发) -> 停止，标记 capability_execution_failed
  - 超时、oversized response、不完整帧 -> 停止，标记 timeout / oversized / incomplete

- 停止命令:
  - Operator: Ctrl+C 或 `pkill -f arena_resident_file_exchange`，`driver.close(); trace.close()`
  - 保留现场，不删除证据

- 不把这轮结果描述为硬隔离实验，用户选择“规则约束＋过程审计”
