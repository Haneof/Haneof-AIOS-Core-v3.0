"""Daily digest (dim:daily_digest), source admission and per-dimension caps."""

from datetime import datetime, timedelta, timezone

from aios_core.contracts.enums import ObjectType
from aios_core.ingest.conversation import ConversationIngestor, INTERACTION_DIMENSION
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.summaries import (
    DIGEST_DIMENSION,
    MultiScaleSummaryScheduler,
    SummaryScale,
)

UTC = timezone.utc
DAY = datetime(2026, 9, 20, 0, 0, tzinfo=UTC)
CLOSED = DAY + timedelta(days=1, minutes=1)  # digest window fully closed


def _seed(tmp_path, turns=((1, 9), (2, 10))):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    ingest = ConversationIngestor(store)
    for i, hour in turns:
        ingest.commit_turn(
            session_id="s1",
            turn_index=i,
            user_text=f"fact {i} about indexing",
            assistant_text=f"answer {i}",
            occurred_at=DAY + timedelta(hours=hour),
        )
    index.rebuild()
    return store, index, ingest


def _summarize(prepared):
    return f"{prepared.granularity}:{prepared.dimension}:{len(prepared.sources)}"


def test_digest_is_a_first_class_basic_dimension(tmp_path):
    store, index, _ = _seed(tmp_path)
    scheduler = MultiScaleSummaryScheduler(
        store=store, index=index, summary_handler=_summarize,
    )

    result = scheduler.run_due(
        now=CLOSED, scales=(SummaryScale.DAY,), max_jobs=32,
    )
    dims = {job.dimension for job in result.attempted_jobs}
    assert INTERACTION_DIMENSION in dims
    assert DIGEST_DIMENSION in dims

    digest = [
        payload for payload in store.list_payloads(
            object_type=ObjectType.SUMMARY, subject_id="user_1",
        )
        if (payload.get("metadata") or {}).get("dimension") == DIGEST_DIMENSION
    ]
    assert len(digest) == 1
    payload = digest[0]
    assert payload["summary_kind"] if False else payload["metadata"]["summary_kind"] == "cross_dimension_daily_digest"
    assert payload["granularity"] == "day"

    # digest sources must be the same-day single-dimension DAY summaries
    day_summaries = [
        p for p in store.list_payloads(object_type=ObjectType.SUMMARY, subject_id="user_1")
        if (p.get("metadata") or {}).get("dimension") == INTERACTION_DIMENSION
        and p.get("granularity") == "day"
    ]
    digest_refs = {(r["object_id"], r["revision"]) for r in payload["source_refs"]}
    day_refs = {(p["object_id"], p["revision"]) for p in day_summaries}
    assert digest_refs == day_refs


def test_digest_is_idempotent_and_never_recurses(tmp_path):
    store, index, _ = _seed(tmp_path)
    scheduler = MultiScaleSummaryScheduler(
        store=store, index=index, summary_handler=_summarize,
    )
    first = scheduler.run_due(now=CLOSED, scales=(SummaryScale.DAY,), max_jobs=32)
    first_digest = [c for c in first.commits if _is_digest(store, c.object_id)]
    assert first_digest

    second = scheduler.run_due(
        now=CLOSED + timedelta(minutes=1), scales=(SummaryScale.DAY,), max_jobs=32,
    )
    assert second.commits == ()
    assert any(j.dimension == DIGEST_DIMENSION for j in second.skipped_unchanged)

    # no digest-of-digest: digest count stays at 1
    digests = [
        p for p in store.list_payloads(object_type=ObjectType.SUMMARY, subject_id="user_1")
        if (p.get("metadata") or {}).get("dimension") == DIGEST_DIMENSION
    ]
    assert len(digests) == 1

    # digest deps never point at another digest
    for dep in store.list_payloads(object_type=ObjectType.DEPENDENCY, subject_id="user_1"):
        if dep.get("dependency_type") != "digest_uses_day_summary":
            continue
        src = store.get_payload(dep["dependency_ref"]["object_id"])
        assert (src.get("metadata") or {}).get("dimension") != DIGEST_DIMENSION


def _is_digest(store, object_id):
    return (store.get_payload(object_id).get("metadata") or {}).get("dimension") == DIGEST_DIMENSION


def test_source_admission_drops_flagged_noise(tmp_path):
    store, index, _ = _seed(tmp_path, turns=((1, 9), (2, 10), (3, 11)))
    prepared_all = None

    def admission(object_id, object_type, payload):
        metadata = payload.get("metadata") or {}
        provenance = metadata.get("provenance") or {}
        return provenance.get("cleaning_decision") != "DROP"

    scheduler = MultiScaleSummaryScheduler(
        store=store, index=index, summary_handler=_summarize,
        source_admission=admission,
    )
    service = scheduler.service

    # flag turn 2's sources as DROP noise by writing a labelled twin: easier —
    # re-prepare after marking via provenance is not possible post-hoc, so we
    # assert on prepare() honouring admission for a service-level flag instead.
    prepared_all = service.prepare(
        dimension=INTERACTION_DIMENSION, granularity="day",
        window_start=DAY, window_end=DAY + timedelta(days=1) - timedelta(microseconds=1),
    )
    assert len(prepared_all.sources) == 6  # 3 turns -> 2 observations each
    assert prepared_all.admission_filtered is False

    # now inject a DROP-labelled observation directly (simulating cleaning
    # labels persisted in provenance) and confirm admission excludes it
    # consistently in prepare() and commit()'s internal re-check.
    import pydantic

    from aios_core.contracts.enums import MaintenanceClass, SourceClass
    from aios_core.contracts.models import Observation
    from aios_core.contracts.operations import OperationRequest
    from aios_core.contracts.time import TemporalExtent

    src_payload = store.get_payload(prepared_all.sources[-1].object_id)
    noisy_id = "obs_noisy_" + src_payload["object_id"][-8:]
    noisy = Observation(
        object_id=noisy_id,
        subject_id="user_1",
        occurred=TemporalExtent(
            start=DAY + timedelta(hours=12),
            end=DAY + timedelta(hours=12, minutes=1),
        ),
        learned_at=DAY + timedelta(hours=12),
        recorded_at=DAY + timedelta(hours=12),
        created_by="test:noisy_seed",
        source_kind=src_payload.get("source_kind") or "user_device",
        modality=src_payload.get("modality") or "text",
        value="在吗",
        metadata={
            "dimension": INTERACTION_DIMENSION,
            "provenance": {"cleaning_decision": "DROP"},
        },
    )
    store.commit([noisy], OperationRequest(
        operation_id="op_noisy_test", operation_name="test.seed_noisy",
        arguments={}, expected_world_revision=store.current_world_revision(),
        reason="seed noise", idempotency_key="seed-noisy",
        source_class=SourceClass.MAINTENANCE, maintenance_class=MaintenanceClass.PRUNE,
    ))
    index.catch_up()

    prepared = service.prepare(
        dimension=INTERACTION_DIMENSION, granularity="day",
        window_start=DAY, window_end=DAY + timedelta(days=1) - timedelta(microseconds=1),
    )
    assert noisy_id not in {s.object_id for s in prepared.sources}
    assert prepared.admission_filtered is True

    committed = service.commit(
        prepared, content="只有干净事实的一天。", generated_at=CLOSED,
    )
    payload = store.get_payload(committed.object_id)
    assert payload["coverage"]["admission_filtered"] is True


def test_handler_failure_is_fail_soft_and_retried_next_tick(tmp_path):
    store, index, _ = _seed(tmp_path)
    attempts = {"n": 0}

    def flaky(prepared):
        attempts["n"] += 1
        if prepared.dimension == DIGEST_DIMENSION:
            raise RuntimeError("gateway 504")  # model outage on the digest only
        return _summarize(prepared)

    scheduler = MultiScaleSummaryScheduler(
        store=store, index=index, summary_handler=flaky,
    )
    result = scheduler.run_due(now=CLOSED, scales=(SummaryScale.DAY,), max_jobs=32)
    # the 9 single-dimension style windows still commit; the digest is recorded
    assert result.commits, "handler failure must not abort the whole sweep"
    assert len(result.failed) == 1
    assert result.failed[0].job.dimension == DIGEST_DIMENSION
    assert "504" in result.failed[0].error

    def ok(prepared):
        return _summarize(prepared)

    scheduler.summary_handler = ok
    second = scheduler.run_due(
        now=CLOSED + timedelta(minutes=1), scales=(SummaryScale.DAY,), max_jobs=32,
    )
    assert second.failed == ()
    assert [c for c in second.commits if _is_digest(store, c.object_id)]


def test_dimension_source_cap_override(tmp_path):
    store, index, _ = _seed(tmp_path, turns=tuple((i, 8 + i) for i in range(1, 8)))
    scheduler = MultiScaleSummaryScheduler(
        store=store, index=index, summary_handler=_summarize,
        max_source_objects=5,
        dimension_source_caps={INTERACTION_DIMENSION: 20},
    )
    result = scheduler.run_due(now=CLOSED, scales=(SummaryScale.DAY,), max_jobs=32)
    # 7 turns produce >5 sources; without the override the DAY job would be
    # truncated and fail closed. With the cap override it must commit.
    day_commits = [
        c for c in result.commits
        if (store.get_payload(c.object_id).get("metadata") or {}).get("dimension")
        == INTERACTION_DIMENSION
    ]
    assert day_commits
    payload = store.get_payload(day_commits[0].object_id)
    assert payload["coverage"]["truncated"] is False
    assert payload["coverage"]["max_source_objects"] == 20
