from datetime import datetime, timedelta, timezone

from aios_core.contracts.enums import SourceClass, WakeSource
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.wake import WakeBus, WakeSignalRequest


NOW = datetime(2026, 9, 21, 10, 0, tzinfo=timezone.utc)


def _obs(object_id: str, dimension: str, text: str, occurred_at: datetime) -> Observation:
    return Observation(
        object_id=object_id,
        subject_id="user_1",
        occurred=TemporalExtent.point(occurred_at),
        learned_at=occurred_at,
        recorded_at=occurred_at,
        created_by="world-map-test",
        source_kind="virtual_life",
        modality="text",
        value=text,
        metadata={"dimension": dimension},
    )


def _seed_world(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    store.commit(
        [
            _obs(
                "obs_world_map_work",
                "dim:work",
                "项目上午出现新的排期变化。",
                NOW - timedelta(hours=2),
            ),
            _obs(
                "obs_world_map_sleep",
                "dim:sleep",
                "昨晚睡眠时间明显缩短。",
                NOW - timedelta(hours=8),
            ),
            _obs(
                "obs_world_map_old_finance",
                "dim:finance",
                "上个月有一笔设备采购。",
                NOW - timedelta(days=20),
            ),
        ],
        OperationRequest(
            operation_name="test.seed.world_map",
            expected_world_revision=0,
            reason="seed L0 world map test",
            idempotency_key="seed-world-map",
            source_class=SourceClass.USER,
        ),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index


def test_dimension_directory_is_mechanical_and_payload_free(tmp_path):
    store, index = _seed_world(tmp_path)

    directory = index.dimension_directory(
        subject="user_1",
        as_of=NOW,
    )

    by_dimension = {
        item["dimension"]: item
        for item in directory["dimensions"]
    }
    assert by_dimension["dim:work"]["current_object_count"] == 1
    assert by_dimension["dim:work"]["recent_24h_count"] == 1
    assert by_dimension["dim:sleep"]["recent_24h_count"] == 1
    assert by_dimension["dim:finance"]["recent_24h_count"] == 0
    assert by_dimension["dim:finance"]["recent_7d_count"] == 0

    serialized = str(directory)
    assert "项目上午出现新的排期变化" not in serialized
    assert "昨晚睡眠时间明显缩短" not in serialized
    assert "上个月有一笔设备采购" not in serialized
    assert "excerpt" not in serialized
    assert "payload" not in serialized


def test_turn_cockpit_exposes_l0_map_then_model_selects_multi_dimension_projection(tmp_path):
    store, index = _seed_world(tmp_path)

    def model(snapshot):
        world_map = snapshot.cockpit["world_map"]
        assert world_map["schema"] == "aios.world-map.l0.v1"
        assert world_map["directory_only"] is True
        assert world_map["semantic_conclusions"] is False

        keys = {item["dimension"] for item in world_map["dimensions"]}
        assert "dim:work" in keys
        assert "dim:sleep" in keys
        assert (
            world_map["expand_capabilities"]["multi_dimension_window"]
            == "request_all_dimensions_projection"
        )

        serialized = str(world_map)
        assert "项目上午出现新的排期变化" not in serialized
        assert "昨晚睡眠时间明显缩短" not in serialized

        if not snapshot.capability_history:
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="request_all_dimensions_projection",
                        arguments={
                            "dimensions": ["dim:work", "dim:sleep"],
                            "window_start": (NOW - timedelta(days=1)).isoformat(),
                            "window_end": NOW.isoformat(),
                        },
                    ),
                )
            )

        projection = snapshot.capability_history[-1]
        assert projection.ok is True
        assert [
            item["dimension"]
            for item in projection.data["slices"]
        ] == ["dim:work", "dim:sleep"]
        return ModelDirective(
            response="我先同时展开了工作和睡眠两个相关维度，再基于当前时间窗判断。"
        )

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
    )
    result = runtime.run_turn(
        session_id="world-map-session",
        turn_index=1,
        user_input="我今天整体状态怎么样？",
        current_topic=None,
        occurred_at=NOW,
    )

    assert result.runtime.response.startswith("我先同时展开了工作和睡眠")
    assert [
        item.name for item in result.runtime.capability_history
    ] == ["request_all_dimensions_projection"]


def test_non_conversation_wake_cockpit_also_exposes_l0_world_map(tmp_path):
    store, index = _seed_world(tmp_path)
    bus = WakeBus(store=store, index=index)

    evidence_ref = ObjectRef(
        object_id="obs_world_map_work",
        revision=1,
    )
    emitted = bus.emit(
        WakeSignalRequest(
            wake_source=WakeSource.WATCH_MATCH,
            rule_id="world-map.wake.test",
            observed_at=NOW,
            evidence_refs=(evidence_ref,),
            dedupe_key="world-map:wake:test",
        )
    )

    def model(snapshot):
        assert snapshot.wake_reason == WakeSource.WATCH_MATCH.value
        world_map = snapshot.cockpit["world_map"]
        keys = {item["dimension"] for item in world_map["dimensions"]}
        assert "dim:work" in keys
        assert world_map["directory_only"] is True
        return ModelDirective(silence=True)

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
    )
    result = runtime.run_wake(
        wake_ref=ObjectRef(
            object_id=emitted.wake_id,
            revision=emitted.revision,
        ),
        now=NOW + timedelta(minutes=1),
    )

    assert result.runtime is not None
    assert result.runtime.silenced is True
    assert result.context is not None
    assert result.context.world_map["schema"] == "aios.world-map.l0.v1"
