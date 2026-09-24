from datetime import datetime, timedelta, timezone

from aios_core.context.continuity import ConversationContinuityService
from aios_core.contracts.enums import SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.ingest.conversation import ConversationIngestor
from aios_core.query.search import WorldSearchIndex
from aios_core.recommendation.proactive import ProactiveMemoryRecommender
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.writeback.cognition import ClaimWriteRequest, CognitionWritebackService


NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)


def _system(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    ingest = ConversationIngestor(store)
    ingest.commit_turn(
        session_id="old-session",
        turn_index=1,
        user_text="智能索引和推荐机制一定要分开。",
        assistant_text="索引是公共能力，推荐只是调用方。",
        occurred_at=NOW - timedelta(days=10),
    )
    ingest.commit_turn(
        session_id="other-session",
        turn_index=1,
        user_text="妈妈生日准备买一个保温杯。",
        assistant_text="记录一下这个计划。",
        occurred_at=NOW - timedelta(days=8),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index


def _commit_external_observation(store: SQLiteWorldStore) -> Observation:
    occurred = NOW - timedelta(days=2)
    observation = Observation(
        object_id="obs_external_badminton",
        subject_id="user_1",
        occurred=TemporalExtent.point(occurred),
        learned_at=occurred,
        recorded_at=occurred,
        created_by="test:calendar",
        source_kind="calendar",
        modality="text",
        value="周六的羽毛球课安排在上午十点。",
        metadata={"dimension": "dim:calendar"},
    )
    store.commit(
        [observation],
        OperationRequest(
            operation_name="test.seed.external_observation",
            expected_world_revision=store.current_world_revision(),
            reason="seed T28 external fact regression",
            idempotency_key="t28-external-badminton",
            source_class=SourceClass.PLATFORM,
        ),
    )
    return observation


def test_no_topic_means_zero_historical_injection(tmp_path):
    store, index = _system(tmp_path)
    recommender = ProactiveMemoryRecommender(index=index, store=store)
    bundle = recommender.recommend(current_topic=None)

    assert bundle.topic_gate_open is False
    assert bundle.cards == ()
    assert bundle.reason == "no_current_topic"


def test_topic_proactively_recalls_related_user_history(tmp_path):
    store, index = _system(tmp_path)
    recommender = ProactiveMemoryRecommender(index=index, store=store)
    bundle = recommender.recommend(current_topic="智能索引")

    assert bundle.topic_gate_open is True
    assert bundle.cards
    assert all("生日" not in card.excerpt for card in bundle.cards)
    assert any(
        (store.get_payload(card.object_id, revision=card.revision).get("metadata") or {}).get("role")
        == "user"
        for card in bundle.cards
    )


def test_unrelated_topic_returns_empty_bundle(tmp_path):
    store, index = _system(tmp_path)
    recommender = ProactiveMemoryRecommender(index=index, store=store)
    bundle = recommender.recommend(current_topic="天气预报")

    assert bundle.topic_gate_open is True
    assert bundle.cards == ()
    assert bundle.reason == "topic_has_no_matching_history"


def test_current_session_can_be_excluded_from_history_recommendation(tmp_path):
    store, index = _system(tmp_path)
    recommender = ProactiveMemoryRecommender(index=index, store=store)
    bundle = recommender.recommend(
        current_topic="智能索引",
        exclude_session_id="old-session",
    )

    assert bundle.cards == ()


def test_assistant_raw_dialogue_is_not_ordinary_proactive_user_memory(tmp_path):
    store, index = _system(tmp_path)
    recommender = ProactiveMemoryRecommender(index=index, store=store)

    # The raw assistant Observation remains in the public rebuildable index.
    raw_search = index.recall_candidates("公共能力")
    assert any(
        (store.get_payload(hit.object_id, revision=hit.revision).get("metadata") or {}).get("role")
        == "assistant"
        for hit in raw_search.hits
    )

    # Same-session continuity also keeps the exact assistant turn available.
    continuity = ConversationContinuityService(store=store, index=index)
    recent = continuity.recent_turns(
        session_id="old-session",
        before_turn=2,
        limit=1,
    )
    assert recent[0]["assistant"]["text"] == "索引是公共能力，推荐只是调用方。"

    # But ordinary proactive memory must not recycle assistant raw prose as an
    # independent user/world fact.
    bundle = recommender.recommend(current_topic="公共能力")
    assert bundle.cards == ()
    assert bundle.reason == "topic_has_no_matching_history"

    fallback_bundle = recommender.recommend(
        current_topic="公共能力",
        antecedent_fallback=True,
    )
    assert all(
        (store.get_payload(card.object_id, revision=card.revision).get("metadata") or {}).get("role")
        != "assistant"
        for card in fallback_bundle.cards
    )


def test_external_fact_and_grounded_claim_remain_proactively_recallable(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    external = _commit_external_observation(store)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    writeback = CognitionWritebackService(store=store, index=index)
    receipt = writeback.commit_claim(
        ClaimWriteRequest(
            content="这次羽毛球课程需要提前十分钟到场。",
            evidence_refs=(ObjectRef(object_id=external.object_id, revision=1),),
            confidence=0.9,
            dimension="dim:planning",
        ),
        learned_at=NOW,
    )

    recommender = ProactiveMemoryRecommender(index=index, store=store)
    external_bundle = recommender.recommend(current_topic="羽毛球课安排")
    assert any(card.object_id == external.object_id for card in external_bundle.cards)

    claim_bundle = recommender.recommend(current_topic="提前十分钟到场")
    assert any(card.object_id == receipt.claim_id for card in claim_bundle.cards)
