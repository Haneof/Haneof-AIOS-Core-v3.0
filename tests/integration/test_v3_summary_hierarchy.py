from datetime import datetime, timedelta, timezone

from aios_core.ingest.conversation import ConversationIngestor, INTERACTION_DIMENSION
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.summaries import MultiScaleSummaryScheduler, SummaryScale


UTC = timezone.utc
NOW = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


def test_multiscale_summary_is_bottom_up_and_never_depends_on_itself(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    ingest = ConversationIngestor(store)

    ingest.commit_turn(
        session_id="s1",
        turn_index=1,
        user_text="week fact one",
        assistant_text="answer one",
        occurred_at=NOW - timedelta(days=8),
    )
    ingest.commit_turn(
        session_id="s2",
        turn_index=1,
        user_text="week fact two",
        assistant_text="answer two",
        occurred_at=NOW - timedelta(days=7),
    )
    index.rebuild()

    def summarize(prepared):
        return (
            f"{prepared.granularity}:{prepared.dimension}:"
            f"{len(prepared.sources)}"
        )

    scheduler = MultiScaleSummaryScheduler(
        store=store,
        index=index,
        summary_handler=summarize,
    )

    first = scheduler.run_due(
        now=NOW,
        scales=(SummaryScale.DAY, SummaryScale.WEEK),
        dimensions=(INTERACTION_DIMENSION,),
        max_jobs=20,
    )
    assert first.commits

    # Re-running over the same durable world must never form a Summary->itself
    # dependency, nor create an equal-scale cycle.
    second = scheduler.run_due(
        now=NOW + timedelta(minutes=1),
        scales=(SummaryScale.DAY, SummaryScale.WEEK),
        dimensions=(INTERACTION_DIMENSION,),
        max_jobs=20,
    )
    assert second.commits == ()

    summaries = [
        payload
        for payload in store.list_payloads(subject_id="user_1")
        if payload.get("object_type") == "summary"
    ]
    summary_refs = {
        (item["object_id"], item["revision"])
        for item in summaries
    }
    for dep in store.list_payloads(
        object_type="dependency",
        subject_id="user_1",
    ):
        if dep.get("dependency_type") != "summary_uses_source":
            continue
        dependent = (
            dep["dependent_ref"]["object_id"],
            dep["dependent_ref"]["revision"],
        )
        dependency = (
            dep["dependency_ref"]["object_id"],
            dep["dependency_ref"]["revision"],
        )
        assert dependent != dependency
        if dependent in summary_refs and dependency in summary_refs:
            dependent_payload = store.get_payload(
                dependent[0], revision=dependent[1]
            )
            dependency_payload = store.get_payload(
                dependency[0], revision=dependency[1]
            )
            rank = {
                "day": 0,
                "week": 1,
                "month": 2,
                "quarter": 3,
                "half_year": 4,
                "year": 5,
                "multi_year_3y": 6,
                "multi_year_5y": 7,
                "decade": 8,
            }
            assert rank[dependency_payload["granularity"]] < rank[
                dependent_payload["granularity"]
            ]
