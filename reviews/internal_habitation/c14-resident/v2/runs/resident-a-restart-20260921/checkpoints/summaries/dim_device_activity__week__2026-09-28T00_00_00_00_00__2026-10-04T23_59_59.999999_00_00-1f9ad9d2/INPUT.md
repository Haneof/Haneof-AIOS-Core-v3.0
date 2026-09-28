# DimensionSummaryInput — dim:device_activity__week__2026-09-28T00:00:00+00:00__2026-10-04T23:59:59.999999+00:00

- dimension: dim:device_activity
- granularity: week
- window: 2026-09-28T00:00:00+00:00 .. 2026-10-04T23:59:59.999999+00:00
- source_world_revision: 16
- source_count: 2
- truncated: False

## sources (exact pinned material)

### 1. sum_53d509d86786bde8d0e84da3@1 (summary)

- occurred_at: 2026-10-01T00:00:00Z
- metadata: {"dimension": "dim:device_activity", "summary_kind": "single_dimension_temporal"}

```text
2026-10-01 设备活动：08:02–10:18 处于专注模式；该时段内主动解锁设备 3 次，26 条通知被静音。
```

### 2. obs_c14_fixture_7422eaba53dc07eb87572e67@1 (observation)

- occurred_at: 2026-10-01T17:22:00Z
- metadata: {"dimension": "dim:device_activity", "external_record_id": "c14resv2-003", "external_revision": "1", "fixture_binding_version": "c14-fixture-event-binding-v1", "fixture_event_id": "c14resv2-003", "fixture_payload_sha256": "sha256:126fe73f4b938a5b2037a2f979696ade07f4e36844523929589ecb6d72039331", "fixture_projection_sha256": "sha256:ec6908844a7dd48ebc2aab20ba112205518ec1552bfc807885095828c9b5cdd1", "fixture_sequence": 3, "fixture_sha256": "sha256:1fb973499664d0d71d94a7b94071e3d7210395ea6a54ec4dcbb1ba115d069253", "fixture_version": "c14-resident-fixture-v2", "mechanical_ingest": true, "occurred_at_original": "2026-10-01T10:22:00-07:00", "source_class": "platform"}

```text
08:02–10:18 开启专注模式；期间主动解锁 3 次，26 条通知被静音。
```
