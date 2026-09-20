from datetime import datetime, timedelta, timezone

from aios_core.contracts.enums import ObjectType, SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent
from aios_core.projections.all_dimensions import AllDimensionsProjectionService
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.summaries.dimension_summary import DimensionSummaryService


DAY = datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc)


def _obs(oid, dimension, text, at):
    return Observation(
        object_id=oid,
        subject_id="user_1",
        occurred=TemporalExtent.point(at),
        learned_at=at,
        recorded_at=at,
        created_by="projection-test",
        source_kind="virtual_life",
        modality="text",
        value=text,
        metadata={"dimension": dimension},
    )


def _seed(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    objects = [
        _obs("obs_work_1", "dim:work", "项目连续加班到很晚", DAY + timedelta(hours=10)),
        _obs("obs_sleep_1", "dim:sleep", "凌晨两点后才入睡", DAY + timedelta(hours=23)),
    ]
    op = OperationRequest(
        operation_name="test.seed",
        expected_world_revision=0,
        reason="seed projection world",
        idempotency_key="projection-seed",
        source_class=SourceClass.USER,
    )
    store.commit(objects, op)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    summaries = DimensionSummaryService(store=store, index=index)
    for dim, text in [
        ("dim:work", "工作维度：当天项目加班明显。"),
        ("dim:sleep", "睡眠维度：当天入睡时间明显延后。"),
    ]:
        prepared = summaries.prepare(
            dimension=dim,
            granularity="day",
            window_start=DAY,
            window_end=DAY + timedelta(days=1) - timedelta(microseconds=1),
        )
        summaries.commit(
            prepared,
            content=text,
            generated_at=DAY + timedelta(days=1),
        )
    return store, index


def test_projection_keeps_dimensions_parallel_and_preserves_types(tmp_path):
    store, index = _seed(tmp_path)
    service = AllDimensionsProjectionService(store=store, index=index)

    projection = service.project(
        dimensions=["dim:work", "dim:sleep"],
        window_start=DAY,
        window_end=DAY + timedelta(days=1),
    )

    assert [slice_.dimension for slice_ in projection.slices] == ["dim:work", "dim:sleep"]
    assert all(slice_.items for slice_ in projection.slices)
    assert all(slice_.items[0].object_type == "summary" for slice_ in projection.slices)
    assert not hasattr(projection, "causal_conclusion")
    assert not hasattr(projection, "parent_dimension")


def test_projection_can_be_topic_filtered_without_inventing_causality(tmp_path):
    store, index = _seed(tmp_path)
    service = AllDimensionsProjectionService(store=store, index=index)

    projection = service.project(
        dimensions=["dim:work", "dim:sleep"],
        window_start=DAY,
        window_end=DAY + timedelta(days=1),
        query="加班",
    )

    work = next(s for s in projection.slices if s.dimension == "dim:work")
    sleep = next(s for s in projection.slices if s.dimension == "dim:sleep")
    assert work.items
    assert sleep.items == ()
    assert projection.query == "加班"
