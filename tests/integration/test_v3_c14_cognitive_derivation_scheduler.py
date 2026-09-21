from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from aios_core.contracts.enums import (
    AttentionClass,
    MaintenanceClass,
    ObjectType,
    SourceClass,
    SummaryStatus,
    WakeSource,
)
from aios_core.contracts.models import Dependency, Observation, Summary
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef, SourceRef
from aios_core.contracts.time import TemporalExtent, TimePrecision
from aios_core.ingest.conversation import ConversationIngestor
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.summaries import (
    CognitiveDerivationScheduler,
    DerivedLineageClass,
    MultiScaleSummaryScheduler,
    SummaryScale,
)
from aios_core.wake import AttentionRouter


UTC = timezone.utc
NOW = datetime(2026, 9, 20, 18, 0, tzinfo=UTC)


def _commit(
    store: SQLiteWorldStore,
    objects,
    *,
    source_class: SourceClass,
    tag: str,
) -> None:
    maintenance_class = (
        MaintenanceClass.SUMMARY_REBUILD
        if source_class is SourceClass.MAINTENANCE
        else None
    )
    store.commit(
        list(objects),
        OperationRequest(
            operation_name=f"test.c14.{tag}",
            expected_world_revision=int(store.current_world_revision()),
            reason=f"seed C14 {tag}",
            idempotency_key=(
                f"test-c14:{tag}:{store.current_world_revision()}"
            ),
            source_class=source_class,
            maintenance_class=maintenance_class,
        ),
    )


def _observation(
    store: SQLiteWorldStore,
    object_id: str,
    *,
    source_class: SourceClass = SourceClass.SENSOR,
    subject_id: str = "user_1",
    dimension: str = "dim:test",
    at: datetime = NOW,
) -> ObjectRef:
    obs = Observation(
        object_id=object_id,
        subject_id=subject_id,
        occurred=TemporalExtent.point(at),
        learned_at=at,
        recorded_at=at,
        created_by="test:c14",
        source_kind="sensor" if source_class is not SourceClass.MAINTENANCE else "maintenance",
        modality="structured_record",
        value={"marker": object_id},
        metadata={"dimension": dimension},
    )
    _commit(
        store,
        [obs],
        source_class=source_class,
        tag=f"obs:{object_id}",
    )
    return ObjectRef(object_id=object_id, revision=1)


def _summary(
    store: SQLiteWorldStore,
    object_id: str,
    source_refs: tuple[ObjectRef, ...],
    *,
    revision: int = 1,
    summary_status: SummaryStatus = SummaryStatus.CURRENT,
    status: str = "active",
    granularity: str = "day",
    dimension: str = "dim:test",
    truncated: bool = False,
    at: datetime | None = None,
) -> ObjectRef:
    moment = at or (NOW + timedelta(minutes=10 + revision))
    summary = Summary(
        object_id=object_id,
        subject_id="user_1",
        revision=revision,
        occurred=TemporalExtent(
            start=NOW,
            end=NOW + timedelta(hours=1),
            precision=TimePrecision.DAY,
        ),
        learned_at=moment,
        recorded_at=moment,
        source_refs=[
            SourceRef(object_id=ref.object_id, revision=ref.revision)
            for ref in source_refs
        ],
        created_by="test:c14:summary",
        status=status,
        summary_time=TemporalExtent(
            start=NOW,
            end=NOW + timedelta(hours=1),
            precision=TimePrecision.DAY,
        ),
        granularity=granularity,
        content="opaque summary text that routing must never interpret",
        source_world_revision=int(store.current_world_revision()),
        coverage={
            "dimension": dimension,
            "source_count": len(source_refs),
            "truncated": truncated,
        },
        summary_status=summary_status,
        metadata={
            "dimension": dimension,
            "summary_kind": "single_dimension_temporal",
        },
    )
    dependencies = [
        Dependency(
            object_id=(
                f"dep_c14_{object_id}_{revision}_"
                f"{ref.object_id}_{ref.revision}"
            ),
            subject_id="user_1",
            learned_at=moment,
            recorded_at=moment,
            created_by="test:c14:dependency",
            dependent_ref=ObjectRef(object_id=object_id, revision=revision),
            dependency_ref=ref,
            dependency_type="summary_uses_source",
        )
        for ref in source_refs
    ]
    _commit(
        store,
        [summary, *dependencies],
        source_class=SourceClass.MAINTENANCE,
        tag=f"summary:{object_id}:{revision}",
    )
    return ObjectRef(object_id=object_id, revision=revision)


def _world(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return db, store, index


def _derivation_wakes(store: SQLiteWorldStore):
    return [
        payload
        for payload in store.list_payloads(
            object_type=ObjectType.WAKE,
            subject_id="user_1",
        )
        if payload.get("wake_source") == WakeSource.COGNITIVE_DERIVATION.value
    ]


def test_reality_summary_schedules_exactly_one_background_opportunity_and_router_sees_it(
    tmp_path,
) -> None:
    _db, store, index = _world(tmp_path)
    source = _observation(store, "obs_reality")
    summary_ref = _summary(store, "sum_reality", (source,))
    scheduler = CognitiveDerivationScheduler(store=store, index=index)

    first = scheduler.ensure(summary_ref)
    retry = scheduler.ensure(summary_ref)

    assert first.eligible is True
    assert first.lineage.classification is DerivedLineageClass.REALITY
    assert retry.wake is not None and first.wake is not None
    assert retry.wake.wake_id == first.wake.wake_id
    assert len(_derivation_wakes(store)) == 1

    wake = scheduler.wake_bus.current_wake(first.wake.wake_id)
    assert wake.wake_source is WakeSource.COGNITIVE_DERIVATION
    assert scheduler.wake_bus.attention_class_for_wake(wake) is AttentionClass.BACKGROUND
    assert wake.evidence_refs == [summary_ref]
    assert wake.metadata["summary_ref"] == summary_ref.model_dump(mode="json")
    assert wake.metadata["dimension"] == "dim:test"
    assert wake.metadata["semantic_conclusions"] is False
    assert wake.metadata["routing_only"] is True
    assert set(wake.metadata).isdisjoint(
        {"meaning", "claim", "preference", "personality", "causal_conclusion"}
    )

    routed = AttentionRouter(
        store=store,
        wake_bus=scheduler.wake_bus,
    ).next_dispatchable(
        now=NOW + timedelta(hours=1),
        background_batch_window_seconds=0,
    )
    assert routed is not None
    assert routed.object_id == wake.object_id


def test_summary_revision_n_plus_one_gets_new_opportunity_but_old_revision_retry_does_not(
    tmp_path,
) -> None:
    _db, store, index = _world(tmp_path)
    first_source = _observation(store, "obs_rev_1", at=NOW)
    first_ref = _summary(store, "sum_revisioned", (first_source,), revision=1)
    scheduler = CognitiveDerivationScheduler(store=store, index=index)
    wake_1 = scheduler.ensure(first_ref).wake
    assert wake_1 is not None

    second_source = _observation(
        store,
        "obs_rev_2",
        at=NOW + timedelta(minutes=5),
    )
    second_ref = _summary(
        store,
        "sum_revisioned",
        (first_source, second_source),
        revision=2,
        at=NOW + timedelta(minutes=20),
    )
    wake_2 = scheduler.ensure(second_ref).wake
    assert wake_2 is not None
    assert wake_2.wake_id != wake_1.wake_id
    assert len(_derivation_wakes(store)) == 2

    old_retry = scheduler.ensure(first_ref)
    assert old_retry.eligible is False
    assert old_retry.reason == "summary_revision_superseded"
    assert len(_derivation_wakes(store)) == 2


def test_nested_higher_scale_summary_recurses_to_exact_reality_leaf(tmp_path) -> None:
    _db, store, index = _world(tmp_path)
    leaf = _observation(store, "obs_nested")
    day = _summary(store, "sum_nested_day", (leaf,), granularity="day")
    week = _summary(
        store,
        "sum_nested_week",
        (day,),
        granularity="week",
        at=NOW + timedelta(minutes=30),
    )
    year = _summary(
        store,
        "sum_nested_year",
        (week,),
        granularity="year",
        at=NOW + timedelta(minutes=40),
    )

    scheduler = CognitiveDerivationScheduler(store=store, index=index)
    result = scheduler.ensure(year)

    assert result.eligible is True
    assert result.lineage.classification is DerivedLineageClass.REALITY
    assert leaf in result.lineage.leaf_refs
    assert result.lineage.unresolved_refs == ()
    assert result.wake is not None


def test_legacy_assistant_raw_is_ai_cognition_only_and_mixed_keeps_sources_separate(
    tmp_path,
) -> None:
    _db, store, index = _world(tmp_path)
    turn = ConversationIngestor(store).commit_turn(
        session_id="legacy-combined-turn",
        turn_index=1,
        user_text="user supplied fact",
        assistant_text="assistant generated text",
        occurred_at=NOW,
    )
    user_ref = ObjectRef(object_id=turn.user_observation_id, revision=1)
    assistant_ref = ObjectRef(object_id=turn.assistant_observation_id, revision=1)

    ai_only = _summary(
        store,
        "sum_ai_only",
        (assistant_ref,),
        at=NOW + timedelta(minutes=20),
    )
    mixed = _summary(
        store,
        "sum_mixed",
        (user_ref, assistant_ref),
        at=NOW + timedelta(minutes=30),
    )
    scheduler = CognitiveDerivationScheduler(store=store, index=index)

    ai_result = scheduler.ensure(ai_only)
    assert ai_result.eligible is False
    assert (
        ai_result.lineage.classification
        is DerivedLineageClass.AI_COGNITION_ONLY
    )
    assert ai_result.lineage.has_ai_cognition is True
    assert ai_result.lineage.has_reality is False

    mixed_result = scheduler.ensure(mixed)
    assert mixed_result.eligible is True
    assert mixed_result.lineage.classification is DerivedLineageClass.MIXED
    assert mixed_result.lineage.has_reality is True
    assert mixed_result.lineage.has_ai_cognition is True
    assert {ref.object_id for ref in mixed_result.lineage.leaf_refs} == {
        turn.user_observation_id,
        turn.assistant_observation_id,
    }
    assert mixed_result.wake is not None


def test_maintenance_only_unknown_missing_and_cross_subject_fail_closed(tmp_path) -> None:
    _db, store, index = _world(tmp_path)
    maintenance = _observation(
        store,
        "obs_maintenance",
        source_class=SourceClass.MAINTENANCE,
    )
    maintenance_summary = _summary(
        store,
        "sum_maintenance",
        (maintenance,),
    )

    foreign = _observation(
        store,
        "obs_foreign",
        source_class=SourceClass.SENSOR,
        subject_id="user_2",
    )
    cross_subject_summary = _summary(
        store,
        "sum_cross_subject",
        (foreign,),
        at=NOW + timedelta(minutes=30),
    )

    missing = _observation(store, "obs_will_be_missing", at=NOW + timedelta(minutes=1))
    missing_summary = _summary(
        store,
        "sum_missing_lineage",
        (missing,),
        at=NOW + timedelta(minutes=40),
    )
    with store._connection() as conn:
        conn.execute(
            "DELETE FROM object_revisions WHERE object_id=? AND revision=?",
            (missing.object_id, missing.revision),
        )
        conn.commit()

    scheduler = CognitiveDerivationScheduler(store=store, index=index)

    maintenance_result = scheduler.ensure(maintenance_summary)
    assert maintenance_result.eligible is False
    assert (
        maintenance_result.lineage.classification
        is DerivedLineageClass.MAINTENANCE_ONLY
    )

    subject_result = scheduler.ensure(cross_subject_summary)
    assert subject_result.eligible is False
    assert subject_result.lineage.classification is DerivedLineageClass.UNKNOWN
    assert "cross_subject_ref" in subject_result.lineage.issues

    missing_result = scheduler.ensure(missing_summary)
    assert missing_result.eligible is False
    assert missing_result.lineage.classification is DerivedLineageClass.UNKNOWN
    assert "missing_or_corrupt_ref" in missing_result.lineage.issues
    assert len(_derivation_wakes(store)) == 0


def test_corrupt_cycle_fails_closed_without_recursive_loop(tmp_path) -> None:
    _db, store, index = _world(tmp_path)
    leaf = _observation(store, "obs_cycle_leaf")
    first = _summary(store, "sum_cycle_a", (leaf,))
    second = _summary(
        store,
        "sum_cycle_b",
        (first,),
        at=NOW + timedelta(minutes=30),
    )

    payload = store.get_payload(first.object_id, revision=first.revision)
    payload["source_refs"] = [
        {"object_id": second.object_id, "revision": second.revision}
    ]
    with store._connection() as conn:
        conn.execute(
            """
            UPDATE object_revisions
            SET payload_json=?
            WHERE object_id=? AND revision=?
            """,
            (
                json.dumps(payload, ensure_ascii=False, sort_keys=True),
                first.object_id,
                first.revision,
            ),
        )
        conn.commit()

    scheduler = CognitiveDerivationScheduler(store=store, index=index)
    result = scheduler.ensure(second)

    assert result.eligible is False
    assert result.lineage.classification is DerivedLineageClass.UNKNOWN
    assert "lineage_cycle" in result.lineage.issues
    assert _derivation_wakes(store) == []


def test_non_current_incomplete_inactive_tombstoned_and_superseded_summaries_do_not_schedule(
    tmp_path,
) -> None:
    _db, store, index = _world(tmp_path)
    leaf = _observation(store, "obs_state")
    scheduler = CognitiveDerivationScheduler(store=store, index=index)

    stale = _summary(
        store,
        "sum_stale",
        (leaf,),
        summary_status=SummaryStatus.STALE,
    )
    partial = _summary(
        store,
        "sum_partial",
        (leaf,),
        summary_status=SummaryStatus.PARTIAL,
        at=NOW + timedelta(minutes=20),
    )
    missing = _summary(
        store,
        "sum_missing_status",
        (leaf,),
        summary_status=SummaryStatus.MISSING,
        at=NOW + timedelta(minutes=30),
    )
    incomplete = _summary(
        store,
        "sum_incomplete",
        (leaf,),
        truncated=True,
        at=NOW + timedelta(minutes=40),
    )
    inactive = _summary(
        store,
        "sum_inactive",
        (leaf,),
        status="inactive",
        at=NOW + timedelta(minutes=50),
    )

    superseded_v1 = _summary(
        store,
        "sum_superseded",
        (leaf,),
        revision=1,
        at=NOW + timedelta(minutes=60),
    )
    superseded_v2 = _summary(
        store,
        "sum_superseded",
        (leaf,),
        revision=2,
        at=NOW + timedelta(minutes=70),
    )

    tombstoned_v1 = _summary(
        store,
        "sum_tombstoned",
        (leaf,),
        at=NOW + timedelta(minutes=80),
    )
    store.prune(
        tombstoned_v1.object_id,
        authz_ref="test:c14",
        reason="C14 tombstone regression",
    )
    tombstoned_latest = ObjectRef(
        object_id=tombstoned_v1.object_id,
        revision=2,
    )

    for ref in (
        stale,
        partial,
        missing,
        incomplete,
        inactive,
        superseded_v1,
        tombstoned_latest,
    ):
        assert scheduler.ensure(ref).eligible is False

    assert scheduler.ensure(superseded_v2).eligible is True
    assert len(_derivation_wakes(store)) == 1


def test_commit_crash_gap_is_recovered_after_store_and_scheduler_restart_and_retry_is_idempotent(
    tmp_path,
) -> None:
    db, store, index = _world(tmp_path)
    source = _observation(store, "obs_crash_gap")
    committed_summary = _summary(store, "sum_crash_gap", (source,))

    # Simulated crash boundary: Summary is durable, but ensure() was never called.
    assert _derivation_wakes(store) == []

    reopened = SQLiteWorldStore(db)
    reopened_index = WorldSearchIndex(db, store=reopened)
    reopened_index.rebuild()
    recovered_scheduler = CognitiveDerivationScheduler(
        store=reopened,
        index=reopened_index,
    )
    first_reconcile = recovered_scheduler.reconcile()
    assert first_reconcile.examined >= 1
    assert len(first_reconcile.scheduled) == 1
    assert first_reconcile.scheduled[0].summary_ref == committed_summary
    assert len(_derivation_wakes(reopened)) == 1

    second_reconcile = recovered_scheduler.reconcile()
    assert len(second_reconcile.scheduled) == 1
    assert (
        second_reconcile.scheduled[0].wake.wake_id
        == first_reconcile.scheduled[0].wake.wake_id
    )
    assert len(_derivation_wakes(reopened)) == 1


def test_multiscale_scheduler_auto_schedules_new_summary_and_unchanged_rerun_adds_no_wake(
    tmp_path,
) -> None:
    _db, store, index = _world(tmp_path)
    old = NOW - timedelta(days=2)
    _observation(
        store,
        "obs_multiscale",
        source_class=SourceClass.SENSOR,
        dimension="dim:test",
        at=old,
    )
    index.rebuild()

    scheduler = MultiScaleSummaryScheduler(
        store=store,
        index=index,
        summary_handler=lambda prepared: (
            f"{prepared.granularity}:{prepared.dimension}:"
            f"{len(prepared.sources)}"
        ),
    )
    first = scheduler.run_due(
        now=NOW,
        scales=(SummaryScale.DAY,),
        dimensions=("dim:test",),
        max_jobs=10,
    )
    assert len(first.commits) == 1
    assert len(_derivation_wakes(store)) == 1

    second = scheduler.run_due(
        now=NOW + timedelta(minutes=1),
        scales=(SummaryScale.DAY,),
        dimensions=("dim:test",),
        max_jobs=10,
    )
    assert second.commits == ()
    assert second.skipped_unchanged
    assert len(_derivation_wakes(store)) == 1
