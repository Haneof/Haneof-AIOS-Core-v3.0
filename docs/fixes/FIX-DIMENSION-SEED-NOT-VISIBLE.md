# FIX-DIMENSION-SEED-NOT-VISIBLE

## 缺陷现象

AI 的「世界地图」（WORLD MAP，每轮必注入提示词的维度目录）里，只有从观测数据里
统计出来的**渠道维度**（`dim:user_ai_interaction`、`dim:note`、`dim:calendar`），
而系统自己在启动时写入的两个自我认知维度 **完全看不到**：

- `dim:ai_promises_ledger`（AI承诺负债与兑现账本）
- `dim:ai_rapport_depth`（共生羁绊深度与默契历程）

真实世界库核验（`w_long2.sqlite`）：

```
dimension_definition {"name": "AI承诺负债与兑现账本", "status": "active"}  metadata={}
dimension_definition {"name": "共生羁绊深度与默契历程", "status": "active"}  metadata={}
观测所属维度: {'dim:user_ai_interaction': 3, 'dim:note': 1}
```

## 根因

`FusedTurnRuntime._world_map_context` 用 **`metadata["dimension_key"]`** 作为维度定义的索引键：

```python
key = str(metadata.get("dimension_key") or "").strip()
lifecycle = str(definition.get("lifecycle") or "")
if not key or lifecycle in terminal_lifecycles:
    continue          # ← 没有 key 就直接丢弃
```

而 `AISelfMindTracker._ensure_ai_dimensions` 创建这两个维度时**没有写 metadata**，
`DimensionDefinition` 本身也没有 `dimension_key` 字段（key 就是 `object_id`）。
结果是：这两个维度在库里存在、状态是 `candidate`，却在渲染世界地图时被静默丢弃。

对照：`DimensionRegistry.propose`（AI 自己提案的维度）**有**写
`metadata={"dimension_key": key, "proposal": {...}}`，所以模型提案的维度能出现在世界地图里，
只有系统种子维度不能。这是不一致，而非设计取舍。

## 为什么这是实质缺陷而不是小瑕疵

宪法要求「系统主动把维度数据推给 AI，AI 自己知道当前世界有什么」。世界地图是 AI
判断「我该往哪个维度写」的唯一常驻依据。少两个维度意味着：

- AI 永远不知道存在「承诺账本」这个轴，于是不会用 `record_promise` 记账，
  承诺失效机制等于没有被触发过；
- AI 无从判断「这个事实该归到已有的哪个轴」，也就更容易把一切都塞进
  `dim:user_ai_interaction` —— 这与实测到的「维度分类退化为渠道分类」现象直接相关。

## 修复

1. **创建时写入 key**：`_ensure_ai_dimensions` 给两个种子维度补上
   `metadata={"dimension_key": ...}`。
2. **存量世界回填**：创建分支对已存在的世界会整段跳过（`except Exception: pass`），
   所以老世界不会自动修好。新增回填逻辑：读出现有定义，如果缺 `metadata_key`
   就按 `revision + 1` 提交一次 `ai_self.backfill_dimension_key` 操作，
   保留审计历史，不覆盖已存在的 key。
3. 回填使用 `MaintenanceClass.INDEX_META`（结构元数据维护，不改变语义）。

## 回归测试

`tests/cognition/test_ai_self.py::test_seed_dimensions_carry_dimension_key_and_repair_existing_worlds`

- 新世界：两个种子维度创建后即带 `dimension_key`；
- 模拟老世界：把 metadata 清空（复现旧代码的落库结果），
  再调用一次 `_ensure_ai_dimensions`，断言 key 被回填。

## 影响面

- 只影响 `dimension_definition` 的 metadata 与 revision，不改世界语义。
- 老世界一次性多 2 个 revision，操作名可审计。
- 不改任何能力契约、提示词结构或写入授权。
