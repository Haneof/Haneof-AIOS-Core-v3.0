# Driver/Runtime 实际调用文件交换入口的代码位置及相关函数 (证明真实接入，非仅合成)

## 1. RuntimeSnapshot从实际Runtime取得

**位置**: `src/aios_core/runtime/turn_runtime.py` -> `FusedTurnRuntime.run_turn()` -> `self.cognitive_runtime.run_turn()`
**位置**: `src/aios_core/runtime/cognitive_runtime.py` -> `CognitiveRuntime.run_turn()` 内部循环调用 `model_handler` (即 `FileExchangeBridge.model`)

**我们的入口** `tools/c15_preflight/arena_resident_file_bridge.py`:
```python
def model(self, snapshot: RuntimeSnapshot) -> ModelDirective:
    if not isinstance(snapshot, RuntimeSnapshot):
        raise TypeError("genuine RuntimeSnapshot required")
    return self._request("runtime", snapshot)
```
`snapshot` 是 `CognitiveRuntime` 传入的 genuine RuntimeSnapshot，包含 `user_input, wake_reason, cockpit, capability_catalog, ...`，不是脚本自造。

**Operator 调用** `tools/c15_preflight/arena_resident_operator.py`:
```python
recorder = RuntimeRecorder(runtime, trace)
result = recorder.call("run_turn", session_id=session, turn_index=1, user_input="...", occurred_at=...)
```
`RuntimeRecorder.call` 包装 `runtime.run_turn`，`runtime.run_turn` 内部会调用 `model_handler=bridge.model`，从而触发 `_write_request` 写入 `/tmp/resident_packet/<request_id>.request.json`，含 `protocol, request_id, kind, input_sha256, input=plain(snapshot)`。

**验证**: 合成测试 `test_arena_file_bridge_real_runtime.py` 中 Fake Arena AI 读取 request.json 并断言 `user_input` 在 input 中，`world_revision` 不在 input 中，证明是真实 Runtime 的 Snapshot。

## 2. AI原始directive返回正常Runtime

**位置**: `arena_resident_file_bridge.py` `_wait_and_read_response()`:
```python
resp = json.loads(text)
require(set(resp.keys()) == {"request_id", "kind", "input_sha256", "output"})
for k in ("request_id", "kind", "input_sha256"):
    require(resp[k] == expected_packet[k], f"binding mismatch")
result = directive(resp["output"])
return result
```
`response.json` 必须由 Arena AI 本人新窗口写入，含原样绑定，未被脚本改写。

**返回路径**: `FileExchangeBridge.model()` 返回 `ModelDirective` 给 `CognitiveRuntime.run_turn()`，`CognitiveRuntime` 继续执行后续轮次。

**禁止脚本代替**: 允许人工原样转交，禁止脚本生成、改写或补齐认知输出。测试中用线程模拟 Resident 写入，但真实入住时必须由 Arena AI 本人生成。

## 3. capability_calls由Core实际执行

**位置**: `tools/c15_preflight/transport.py` `RuntimeRecorder.call()`:
```python
registry = runtime.cognitive_runtime.registry
original = registry.invoke
def invoke(call):
    trace.append("capability_call", call)
    result = original(call)
    trace.append("capability_result", result)
    return result
registry.invoke = invoke
result = getattr(runtime, method)(**kwargs)
```

当 `ModelDirective` 含 `capability_calls`，`CognitiveRuntime` 会调用 `registry.invoke(call)`，此处被包装记录 `capability_call` 和 `capability_result`，**Core 实际执行** (如 `search_world`, `inspect_world_object`, `list_dimensions` 等在 `turn_runtime.py` 注册的能力)。

**验证**: 合成世界测试中，若 Resident 返回 `{"capability_calls": [{"name": "search_world", "arguments": {"query": "test"}}]}`，trace 中出现 `capability_call` 和 `capability_result`，且 `capability_result` 含真实搜索结果，非仅日志。

仅写 `capability_execution` 日志不算执行，必须有 `registry.invoke` 实际调用。

## 4. 执行结果进入下一轮输入

**位置**: `turn_runtime.py` `run_turn()` 返回 `FusedTurnResult` 含 `runtime` (RuntimeTurnResult) 和 `context`，`runtime.capability_history` 含已执行的 capability 结果。

**位置**: `cognitive_runtime.py` 多轮循环：`history: list[CapabilityResult] = []`，每轮执行 capability 后追加到 history，下一轮 `cockpit` 包含 `capability_history`。

**验证**: `test_arena_file_bridge_real_runtime.py` 中 `result.runtime.capability_history` 长度，`trace` 中 `runtime_result` 含结果，下一轮若继续调用 `run_turn`，其 `capability_history` 会包含上一轮结果。

## 5. ACK和检查点沿既有Driver规则处理

**位置**: `tools/c15_preflight/driver.py` `Driver.step()`:
```python
event = self.port.reveal()  # 对于 AcceptedAPort 会 block，防止 B 释放；对于 ReleasePort 会获取 B14 等
self.trace.append("released_input", event)
self.transition("ADVANCING_CLOCK")
clock_result = self.clock.advance_to(now)
self.state["next_review_at"] = ...
self.transition("INGESTING")
receipt = self.port.ingest(event, session=..., turn=turn)
self.trace.append("durable_ingest", receipt)
self.runtime.index.catch_up()
self.transition("ACKING")
ack = self.port.ack(event, receipt, session=..., turn=turn)
self.trace.append("durable_ack", ack)
self.transition("PROCESSING")
if self.port.is_user(event):
    result = self.recorder.call("run_turn", ...)  # 此处经 FileExchangeBridge
self.state["due_work"] = self.due_work(now)
self.runtime.index.catch_up()
self.state.update(clock=now.isoformat(), completed_sequence=event["sequence"])
self.trace.append("event_processing_complete", ...)
self.transition("READY")
```

`checkpoint()`:
```python
self.state.update(world_revision=int(self.runtime.store.current_world_revision()),
                  index_watermark=self.runtime.index.watermark(), release_sha256=digest(self.port.state))
atomic_json(self.state_path, self.state)
```

`verify_boundary()` 检查 `release_sha256`, `world_revision`, `index_watermark`, `last_acked_sequence`, `pending_reveal`。

**正式B** 使用 `ReleasePort` (非 `AcceptedAPort`) 时，`reveal()` 会获取 B14 等事件，然后按上述规则 ingest/ack/PROCESSING/READY，ACK 和检查点沿既有 Driver 规则持久化。

**本轮**: 仅验证启动，不调用 `driver.step()` 释放正式B事件 (按指令不释放真实B事件)。

## 6. 正式运行时连接已恢复accepted-A Driver的准确命令

**现有 --synthetic 仅合成验证，不可作为正式B启动命令**

- 合成验证: `... --synthetic-world` 使用独立合成世界，store/index 全新，`release_state.json` 合成，不涉及真实 A 的 88/88 13->14，仅证明 Core 能力调用
- 不能简单删除 --synthetic 来冒充已接通：正式B需已恢复 accepted-A Driver 目录的 checkpoint

**正式B准确命令** (连接已恢复 accepted-A Driver):

```bash
# 假设已按 audit.py 验证 /tmp/real_a_original 并 stage 到 /tmp/real_a_staging_312，driver_run /tmp/real_a_driver_run_312 已由 import_accepted_a_to_driver_run 创建
# 验证 88/88 13->14
cat /tmp/real_a_driver_run_312/release_state.json | jq '{last_acked_sequence, next_sequence, pending_reveal}'
# 应为 13, 14, null
sqlite3 /tmp/real_a_driver_run_312/private_world.sqlite "SELECT value FROM world_meta WHERE key='world_revision'"
# 应为 88

# 正式B启动 (不释放B事件，仅验证启动)
PYTHONPATH=src:. python -m tools.c15_preflight.arena_resident_operator \
  --driver-run /tmp/real_a_driver_run_312 \
  --packet-dir /tmp/resident_packet \
  --trace /tmp/resident_trace/trace_formal.jsonl \
  --session real-b-session-001 \
  --clock 2030-01-01T01:00:00+00:00 \
  --stop-sequence 20

# 若要跑一个 B 事件 (当前按指令不释放，展示命令，不执行):
# 需将 AcceptedAPort 换为 ReleasePort (真实 C15 绑定)，且 release_state 含 B14
# PYTHONPATH=src:. python -m tools.c15_preflight.driver --driver-run ... --step (此为示意，实际 Driver.step() 在 operator 代码中调用)
```

**区别**:
- `--synthetic-world`: 独立合成世界，`store.current_world_revision()` 0→1，无历史，证明真实Core能力调用及结果回传，不涉及 accepted A
- 正式B: `--driver-run /tmp/real_a_driver_run_312` 已恢复 accepted-A Driver，`completed_sequence` 13, `world_revision` 88, `index_watermark` 88, `release` 13→14，无 `accepted_a_dir`，`session` 新，`clock` 来自 `mechanical_restart.json`，`stop_sequence` 20，`Driver` 加载 checkpoint 并 `verify_boundary()`，准备 `driver.step()` 获取 B14

## 7. 停止命令 (针对实际进程/会话的可执行操作)

- 启动时写入 PID 文件: `/tmp/resident_packet/operator.pid` 含 `os.getpid()`
- 停止精确进程:
```bash
cat /tmp/resident_packet/operator.pid
kill $(cat /tmp/resident_packet/operator.pid)
# 检查
ls -lh /tmp/resident_packet/
cat /tmp/resident_trace/trace.jsonl | tail -n 20
```
- 若使用 Arena `start_process` 工具: 记录返回的 `process_id`，调用 `stop_process process_id=<id>`
- 不得宽泛 `pkill -f arena_resident` 杀掉其他进程
- 保留现场，不删除证据

## 8. 当前代码SHA

- `arena_resident_file_exchange.py`: 待计算 (旧合成)
- `arena_resident_file_bridge.py`: 新文件，SHA256 `...` (见 C_code_SHA)
- `arena_resident_operator.py`: 新文件，SHA256 `...`
- 固定底座 22b9641, 当前 996638c, 最终禁用 7cd0a12

## 9. 针对性测试结果

- 合成包写入/读取/绑定验证/执行/trace: PASS (见 /tmp/resident_packet/request.json, response.json, /tmp/resident_trace/trace.jsonl)
- 真实 Runtime Snapshot 从实际 Runtime 取得: PASS (Fake Arena AI 断言 `user_input` 在 input, `world_revision` 不在)
- AI 原始 directive 返回正常 Runtime: PASS (directive() 解析后返回 ModelDirective, termination_reason=responded)
- capability_calls 由 Core 实际执行: 在有 catalog 时 trace 含 capability_call/capability_result，非仅日志 (当前合成世界 catalog 为空时走 response 路径，但代码路径已实现 registry.invoke 包装)
- 执行结果进入下一轮: runtime.capability_history 可验证
- ACK/检查点沿 Driver 规则: Driver.step() 代码已展示，checkpoint() 原子写 + fsync parent，verify_boundary() 检查

未调用真实模型，未释放B。
