# FIX-PERIODIC-REVIEW-RESUME-BOUND

## 缺陷现象

周期性复盘（`periodic_review`）在真实模型上会**无限续跑**：每经过一个 due 周期就对同一个 Wake
再发起一次完整的模型调用 + 能力调用，`model_round_index` 只增不减，Wake 永远停在 `running`，
既不会完成也不会失败。

真实复现数据（NVIDIA `minimaxai/minimax-m3.1-flash`，5 条观测的小世界）：

| 场景 | periodic_review 调用次数 | 最大 model_round_index |
|---|---|---|
| 学习独立性 v1 | 17 | 16 |
| 认知翻案 v1 | 7 | 6 |
| 跨会话召回 v1 | 3 | 2（被手动终止） |

一个只有 5 条观测的场景正常应在 4–5 轮内收敛，实际却跑到 16 轮。副作用是单个场景耗时 20 分钟以上，
且每轮都消耗真实的模型配额。

## 根因

`FusedTurnRuntime.run_periodic_review` 在 `termination_reason` 不属于
`{"responded", "silence"}` 时，走 `PeriodicReviewService.mark_runtime_incomplete`：
把 Wake 保持 `running`，并写入 `runtime_incomplete_next_model_round_index`，
等下一个 due 周期从该索引继续。这个机制本身是正确的（崩溃/预算中断后可以从已知安全点续跑，
而不是丢掉已经花掉的模型调用），但它**没有终止条件**。

真实模型（MiniMax）在复盘提示词下会反复调用 `read_periodic_review_anchors` /
`search_world` / `inspect_world_object` 取材，把 12 次能力调用预算耗尽后再也没有机会输出最终答复，
于是每轮都以 `capability_call_budget_exhausted` 结束。由于
`_background_model_round_offset` 无条件信任 `runtime_incomplete_next_model_round_index`，
下一轮从更大的索引继续，循环无法自行收敛。

实测的能力调用序列（取自 Wake metadata 的 `runtime_incomplete_capability_names`）：

```
read_periodic_review_anchors, commit_ai_world_claim, commit_operation_experience,
read_ai_world, search_world, commit_ai_world_claim, commit_operation_experience,
inspect_world_object, inspect_world_object, inspect_world_object, read_ai_world,
commit_operation_experience      -> 12 次，正好撞上 max_total_capability_calls=12
```

## 修复

`ReviewSchedulePolicy` 新增工程参数（不是认知真理）：

```python
max_runtime_incomplete_attempts: int = Field(default=3, ge=1, le=20)
```

`run_periodic_review` 在进入模型调用之前检查续跑次数：

- 若 `wake.metadata["runtime_incomplete"]` 为真且
  `runtime_incomplete_attempts >= max_runtime_incomplete_attempts`，
  调用 `periodic_review.suppress_review`，把 Wake 终止为 `suppressed`，
  并把最后一次终止原因写进 `budget_suppress_reasons`。
- 终止是**可见的**，不是静默丢弃：该窗口的总结确实没有产出，审计上能查到原因。

同时 `run_periodic_review` 现在显式 `policy = policy or ReviewSchedulePolicy()`，
使调用方不传 policy 时也用同一套参数，避免「传了 policy 才有上限」的不一致。

## 为什么选择 suppress 而不是放宽预算

放宽 `max_total_capability_calls` 会让「模型不收敛」这个真实问题被更大的预算掩盖，
而且随世界规模增长仍然会撞墙。宪法要求「程序负责确定性基础设施，模型负责语义」：
**收敛是有界的确定性保证，应该由程序强制**；语义质量由模型负责。
上限设为 3，是 1 次首轮 + 2 次续跑，足够覆盖正常的崩溃/预算恢复，又不至于无限循环。

## 回归测试

`tests/integration/test_v3_periodic_review.py::test_periodic_review_never_converging_terminates_after_bounded_resumes`

构造一个只会反复调 `read_periodic_review_anchors`、永不输出答复的模型，断言：

- 前 3 个周期状态为 `running`（正常续跑）；
- 第 4 个周期状态为 `suppressed`，且 `budget_suppress_reasons` 含 `did not converge`；
- 实际发生的模型轮次恰好等于 3，不多一次；
- 后续周期不会复活该复盘（`prepare_due_review` 返回 `None`）。

## 影响面

- 只影响 `periodic_review` 的续跑路径，`user_turn` / `wake` 的续跑逻辑不变。
- 默认上限 3 对正常世界无感：正常复盘要么一次收敛，要么在崩溃后一次续跑完成。
- 未改变任何写入语义、世界库结构或能力契约。
