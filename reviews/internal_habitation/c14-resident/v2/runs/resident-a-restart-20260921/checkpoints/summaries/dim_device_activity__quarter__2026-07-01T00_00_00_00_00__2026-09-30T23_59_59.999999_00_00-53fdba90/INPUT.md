# DimensionSummaryInput — dim:device_activity__quarter__2026-07-01T00:00:00+00:00__2026-09-30T23:59:59.999999+00:00

- dimension: dim:device_activity
- granularity: quarter
- window: 2026-07-01T00:00:00+00:00 .. 2026-09-30T23:59:59.999999+00:00
- source_world_revision: 32
- source_count: 2
- truncated: False

## sources (exact pinned material)

### 1. sum_621dbad73aff86b121ff5f4d@1 (summary)

- occurred_at: 2026-09-01T00:00:00Z
- metadata: {"dimension": "dim:device_activity", "summary_kind": "single_dimension_temporal"}

```text
2026-09 设备活动：本月窗口内仅含一份下级摘要（09-28–10-04 周摘要）：该周唯一记录为 10-01 的 08:02–10:18 专注模式，期间主动解锁设备 3 次、26 条通知被静音。
```

### 2. sum_fa279a5040c9a67efcae4f10@1 (summary)

- occurred_at: 2026-09-28T00:00:00Z
- metadata: {"dimension": "dim:device_activity", "summary_kind": "single_dimension_temporal"}

```text
2026-09-28–10-04 当周设备活动：本周仅 10-01 有一条记录——08:02–10:18 处于专注模式，期间主动解锁设备 3 次、26 条通知被静音。
```
