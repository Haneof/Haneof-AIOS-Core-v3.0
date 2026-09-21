# Segment 003 Resident Task

## 当前状态

- **Habitation run**: `sol-resident-20260921-001`
- **Logical Resident**: `gpt-5.6-sol-interactive-resident-001`
- **Segment**: `segment-003`
- **SEG003_STATUS**: `pending`
- **Cursor**: `d026-pos`
- **World revision**: `146`
- **Index watermark**: `145`
- **当前模拟时间**: `2027-01-19T08:15:00Z`
- **累计入住**: `14 天`

## 世界状态

- **Source artifact id**: `10612379363`
- **World SHA-256**: `ba843f00e107cf6184ae25941d96ceb4ddb9a19234c99a789967c48f21cabec8`
- **World revision**: `146`（已从 145 更新）
- **Index watermark**: `145`

## 当前 RuntimeSnapshot (pending)

```
RuntimeSnapshot:
  wake_reason: "user_interaction"
  user_input: "上次拍的那个商业区照片，光线怎么样来着？我有点忘了，当时咋拍的"
  
  cockpit:
    current_time: "2027-01-19T08:15:00Z"
    session_id: "sess-003-continuation"
    turn_index: 1
    residency_days: 14
    recent_observations:
      - event_id: "d026-pos"
        channel: "conversation"
        occurred_at: "2027-01-19T07:45:00Z"
        payload: "晚上好，今天有个老客户打电话过来，想看看我以前拍过的一个商业区的照片。
                  就是那个位于徐汇区的老办公楼群，我2026年秋天拍过。客户说要参考下光线效果。
                  你帮我找找那次拍摄记录？"
      - event_id: "d025-sensor"
        channel: "sensor_numeric"
        occurred_at: "2027-01-19T06:00:00Z"
        payload:
          source_kind: "weather"
          dimension: "dim:weather"
          series_id: "weather-shanghai-2027"
          samples:
            - external_record_id: "weather-001"
              occurred_at: "2027-01-19T06:00:00Z"
              value: 12.5
          policy:
            tolerance: 0.5
            max_gap_seconds: 3600
          unit: "celsius"
    world_revision: 146
    
  capability_catalog:
    - name: "search_world"
      description: "Search the AIOS world for observations, claims, events by query"
      input_schema:
        query: "string"
        time_range_start?: "ISO-8601 datetime"
        time_range_end?: "ISO-8601 datetime"
        object_types?: "array[string]"
    - name: "inspect_world_object"
      description: "Get full details of a world object by ID"
      input_schema:
        object_id: "string"
        revision?: "integer"
    - name: "request_all_dimensions_projection"
      description: "Get a projection across all active dimensions for a time window"
      input_schema:
        time_start: "ISO-8601 datetime"
        time_end: "ISO-8601 datetime"
    - name: "commit_claim"
      description: "Commit a new claim to the world"
      input_schema:
        claim_text: "string"
        evidence_refs: "array[string]"
        subject_id: "string"
    - name: "revise_claim"
      description: "Revise an existing claim"
      input_schema:
        claim_id: "string"
        new_claim_text: "string"
        evidence_refs: "array[string]"
    - name: "create_goal"
      description: "Create a new goal"
      input_schema:
        goal_text: "string"
        priority?: "string"
    - name: "create_task"
      description: "Create a new task"
      input_schema:
        task_text: "string"
        goal_id?: "string"
    - name: "focus_entity"
      description: "Focus on a specific entity and see related observations"
      input_schema:
        entity_id: "string"
    - name: "search_timeline"
      description: "Search events along a timeline"
      input_schema:
        time_start: "ISO-8601 datetime"
        time_end: "ISO-8601 datetime"
        filters?: "object"
    - name: "follow_relation"
      description: "Follow a relation between entities"
      input_schema:
        from_entity: "string"
        relation_type: "string"
        to_entity?: "string"
    - name: "compare_claims"
      description: "Compare two claims"
      input_schema:
        claim_id_1: "string"
        claim_id_2: "string"
    - name: "retrieve_original_observation"
      description: "Retrieve the original observation for a claim or summary"
      input_schema:
        claim_id: "string"
    - name: "expand_recall"
      description: "Expand recall to find related memories"
      input_schema:
        anchor_object_id: "string"
        expand_by: "integer"
    - name: "inspect_outcome"
      description: "Inspect the outcome of a task or action"
      input_schema:
        task_id: "string"
        
  capability_history: []
  round_index: 0
  remaining_tool_rounds: 8
```

## 你的任务

这是一个**跨会话引用**场景。

用户说"上次拍的那个商业区照片"，但：
1. 他没有明确说是哪个商业区
2. 他提到了"2026年秋天"这个时间范围
3. 他提到了"徐汇区的老办公楼群"

你需要：
1. **判断这个引用是否足够明确** - 如果不够明确，是否需要澄清？
2. **检索记忆** - 使用 search_world 或 search_timeline 查找相关的拍摄记录
3. **基于检索结果回答用户** - 告诉用户找到什么，以及光线情况
4. **是否需要形成 Claim**？ - 如果有重要的发现，是否应该记录下来？

**重要**: 你不能提前知道未来会发生什么。你只能看到当前的 RuntimeSnapshot。

**记忆恢复**: 如果你不记得之前的拍摄记录，必须通过 AIOS 正式检索机制恢复记忆。

## 决定格式

根据你的判断，选择以下格式之一：

### 如果你选择回复用户：

```json
{
  "seg003-d026-response": {
    "kind": "response",
    "response": "你的真实 Resident 回复"
  }
}
```

### 如果你需要检索世界：

```json
{
  "seg003-d026-capability-calls": {
    "kind": "capability_calls",
    "calls": [
      {
        "name": "search_world",
        "arguments": {
          "query": "徐汇区 商业区 办公楼 2026年秋天 拍摄",
          "time_range_start": "2026-09-01T00:00:00Z",
          "time_range_end": "2026-11-30T23:59:59Z"
        },
        "call_id": "seg003-d026-search-001"
      }
    ]
  }
}
```

### 如果你选择沉默：

```json
{
  "seg003-d026-silence": {
    "kind": "silence"
  }
}
```

## 禁止事项

- 不要读取 Life Director 分支或 sealed_fixture.json
- 不要尝试预测未来事件
- 不要一次性生成所有决策
- 不要为了测试覆盖率而机械创建 Goal/Task/Claim
- 不要修改 src/aios_core/**

## 提交位置

决策文件：`reviews/internal_habitation/sol-yearlong/segments/segment-003/decisions/part-001.json`

提交到分支：`arena/sol-yearlong-resident-20260921`
