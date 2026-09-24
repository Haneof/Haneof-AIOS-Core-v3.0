# A. operator实际安装、启动、收发、停止命令

# 固定底座: PR125交接头 22b9641f85e0e20f1bd87ed85100a1e268e56dea, 固定分支 arena/01a0cf25-haneof-aios-core-v3-0
# 保持冻结Core bcd6bf353126318f9a97076b52ec1740d43f35a4, accepted A 3e51f728d7959048b75fea01d405bc837b0e8185
# 不用PR126新Core，不用旧B初始化，不合并PR，不触发公开CI真实A工作流 (real-a-import-312.yml 已 if: false 禁用)

## 1. 安装 (Python>=3.12)
python -c 'import sys; assert sys.version_info >= (3,12)'
pip install -e ".[dev]"
find src -type d -name __pycache__ -exec rm -rf {} + || true
export PYTHONDONTWRITEBYTECODE=1
git rev-parse HEAD  # 应为 996638c90a0b167a228c90cb5020b0ebbe0643da 或后续仅文档头

## 2. 启动 - 合成验证 (本轮仅用独立合成数据完成一次收发核验，不释放正式B事件)
# 现有入口复用 transport.plain/encode/directive, driver, restart, audit
# 最小文件交换入口 tools/c15_preflight/arena_resident_file_bridge.py + arena_resident_file_exchange.py
# 合成验证命令 (证明5步链路):
PYTHONPATH=src:. python -m tools.c15_preflight.arena_resident_operator --driver-run /tmp/real_a_driver_run_312 --packet-dir /tmp/resident_packet --trace /tmp/resident_trace/trace.jsonl --session test-session-001 --clock 2030-01-01T00:00:00+00:00 --stop-sequence 20 --synthetic-world

# 该命令实际执行:
# - 独立合成世界 (store, index) 创建
# - Trace /tmp/.../trace.jsonl exclusive create
# - FileExchangeBridge packet_dir=/tmp/resident_packet
# - RuntimeRecorder.call("run_turn") -> runtime.run_turn -> cognitive_runtime -> model_handler=bridge.model -> genuine RuntimeSnapshot -> plain(snapshot) 仅7批准字段 -> write /tmp/resident_packet/<request_id>.request.json (protocol, request_id, kind, input_sha256, input)
# - 等待 Arena AI 本人写入 <request_id>.response.json
# - 校验绑定 request_id/kind/input_sha256, directive() 解析, 返回 ModelDirective 到正常 Runtime
# - capability_calls 由 Core 实际执行 (registry.invoke 被 RuntimeRecorder 包装记录 capability_call/capability_result)
# - 执行结果进入下一轮输入 (runtime_result, capability_history)
# - trace 记录 model_request/model_return_validated/runtime_result 等，hash链 fsync

## 3. 正式运行时连接已恢复accepted-A Driver的准确命令 (不可用 --synthetic 冒充)
# 现有 --synthetic 命令只用于合成验证，不可作为正式B启动命令；不能简单删除 --synthetic 来冒充已接通
# 正式B需已恢复 accepted-A Driver (88/88, 13->14) 的目录，例如 /tmp/real_a_driver_run_312 (由 import_accepted_a_to_driver_run 创建，含 driver_state.json completed 13 wr88 iw88)
# 准确命令:
PYTHONPATH=src:. python -m tools.c15_preflight.arena_resident_operator --driver-run /tmp/real_a_driver_run_312 --packet-dir /tmp/resident_packet --trace /tmp/resident_trace/trace_formal.jsonl --session real-b-session-001 --clock 2030-01-01T01:00:00+00:00 --stop-sequence 20

# 该命令:
# - 验证 driver_run_dir 含 private_world.sqlite, world_index.sqlite, release_state.json, driver_state.json
# - 验证 release last_acked 13 next 14 pending None, store wr88 index 88
# - 创建新 trace 文件 (exclusive create, 非复用旧)
# - FileExchangeBridge 写入 operator.pid 文件
# - Driver(runtime, trace, port, directory, session, clock, stop_sequence) 加载已有 checkpoint, verify_boundary()
# - 准备运行 B 事件: driver.step() 将执行 reveal -> clock_advance -> ingest -> durable_ack -> PROCESSING (run_turn via FileExchangeBridge) -> READY, checkpoint() 持久化 world_revision/index_watermark/release_sha256
# - 本轮仅验证启动，不调用 driver.step() 释放正式B事件 (按指令不释放真实B事件)

## 4. 收发 - 人工原样转交 (禁止脚本代替AI生成或改写决定)
# Operator已将批准的Runtime输入写入 /tmp/resident_packet/<request_id>.request.json (含 protocol, request_id, kind, input_sha256, input)
# 将该文件原样提供给 fresh Resident 新Arena窗口 (新窗口未接触本实验历史和评审材料)
# Resident窗口AI本人读取后，生成原始directive，写入 /tmp/resident_packet/<request_id>.response.json (需含 request_id/kind/input_sha256/output 绑定，output 仅允许 response/silence/capability_calls 或 text)
# Operator收回: FileExchangeBridge 自动等待、校验绑定、directive()、返回 Runtime、记录 trace

## 5. 停止 - 针对实际进程/会话的可执行操作 (不得宽泛杀掉其他进程)
# 启动时 Operator 写入 PID 文件:
cat /tmp/resident_packet/operator.pid
# 停止该精确进程:
kill $(cat /tmp/resident_packet/operator.pid)
# 或若使用 Arena process 工具启动:
# 记录 start_process 返回的 process_id, 调用 stop_process process_id=<id>
# 检查 trace 是否完整:
ls -lh /tmp/resident_trace/
cat /tmp/resident_trace/trace.jsonl | tail -n 20
# 保留现场，不删除 /tmp/resident_packet/*, trace.jsonl
# 若发现越界、缺日志、错误回复，立即停止，标记污染，见 E_stop_method.md
# 不自行跑真实B/C
