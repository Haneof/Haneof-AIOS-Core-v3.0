# DimensionSummaryInput — dim:sleep__week__2026-09-28T00:00:00+00:00__2026-10-04T23:59:59.999999+00:00

- dimension: dim:sleep
- granularity: week
- window: 2026-09-28T00:00:00+00:00 .. 2026-10-04T23:59:59.999999+00:00
- source_world_revision: 20
- source_count: 2
- truncated: False

## sources (exact pinned material)

### 1. sum_e4577fa411beaabd5bb78300@1 (summary)

- occurred_at: 2026-10-01T00:00:00Z
- metadata: {"dimension": "dim:sleep", "summary_kind": "single_dimension_temporal"}

```text
2026-10-01 睡眠：昨夜睡眠 7小时44分；睡眠评分 84/100；07:08 醒来。
```

### 2. obs_c14_fixture_b32d3cded992194438f114a9@1 (observation)

- occurred_at: 2026-10-01T14:12:00Z
- metadata: {"dimension": "dim:sleep", "external_record_id": "c14resv2-001", "external_revision": "1", "fixture_binding_version": "c14-fixture-event-binding-v1", "fixture_event_id": "c14resv2-001", "fixture_payload_sha256": "sha256:8f0368bff1263924e037ce3d9814f95ad1543e054bb1916fe97fa893dc1119f3", "fixture_projection_sha256": "sha256:0ae667657344eadd1a0d4b67a1d1262bf48c7398a5f560f3096d925f2e7b7882", "fixture_sequence": 1, "fixture_sha256": "sha256:1fb973499664d0d71d94a7b94071e3d7210395ea6a54ec4dcbb1ba115d069253", "fixture_version": "c14-resident-fixture-v2", "mechanical_ingest": true, "occurred_at_original": "2026-10-01T07:12:00-07:00", "source_class": "sensor"}

```text
昨晚睡眠 7小时44分；睡眠评分 84/100；07:08 醒来。
```
