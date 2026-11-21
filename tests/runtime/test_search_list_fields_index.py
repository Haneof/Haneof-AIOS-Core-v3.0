"""Regression tests for PM-SEARCH-LIST-FIELDS-INDEX-001.

The world-search projection must index only the explicitly approved string
items in ToolProposal and NarrativeSegment list fields. Existing
CommunicationExperience search coverage must remain intact after whitelist
deduplication.
"""

from datetime import datetime, timezone

import pytest

from aios_core.contracts.enums import SourceClass, UserReaction
from aios_core.contracts.models import (
    CommunicationExperience,
    NarrativeSegment,
    ToolProposal,
)
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.tools.proposal_pipeline import ToolProposalStatus

NOW = datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc)


def _seed_list_field_fixtures(store: SQLiteWorldStore) -> None:
    use_case_proposal = ToolProposal(
        object_id="tpr_list_use_case",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="test",
        status=ToolProposalStatus.DRAFT.value,
        capability_gap="a distinct capability gap",
        use_cases=["usecasequartz", "", "   "],
        current_limitations=["manual process only"],
        proposed_interface={"run": {"id": "string"}},
        expected_benefit="a distinct expected benefit",
        validation_plan="a distinct validation plan",
    )
    limitation_proposal = ToolProposal(
        object_id="tpr_list_limitation",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="test",
        status=ToolProposalStatus.DRAFT.value,
        capability_gap="another distinct capability gap",
        use_cases=["anotherusecase"],
        current_limitations=["limitationnebula", " ", ""],
        proposed_interface={"inspect": {"id": "string"}},
        expected_benefit="another distinct benefit",
        validation_plan="another distinct validation plan",
    )
    unrelated_proposal = ToolProposal(
        object_id="tpr_unrelated",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="test",
        status=ToolProposalStatus.DRAFT.value,
        capability_gap="unrelated capability",
        use_cases=["unrelatedusecase"],
        current_limitations=["unrelatedlimitation"],
        proposed_interface={"noop": {"id": "string"}},
        expected_benefit="unrelated benefit",
        validation_plan="unrelated validation",
    )
    segment = NarrativeSegment(
        object_id="nsg_list_theme_tag",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="test",
        title="A generic segment title",
        description="A generic segment description",
        theme_tags=["narrativetagcobalt", "", "   "],
    )
    communication = CommunicationExperience(
        object_id="cme_search_after_dedup",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="test",
        scenario="a communication scenario",
        style="communicationstyleamber",
        tone="calm",
        user_reaction=UserReaction.ACCEPTED,
    )
    operation = OperationRequest(
        operation_name="test.seed_search_list_field_fixtures",
        expected_world_revision=0,
        reason="seed fixtures for list-valued keyword-search regression",
        idempotency_key="seed_search_list_field_fixtures",
        source_class=SourceClass.USER,
    )
    store.commit(
        [
            use_case_proposal,
            limitation_proposal,
            unrelated_proposal,
            segment,
            communication,
        ],
        operation,
    )


@pytest.fixture
def indexed_world(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    _seed_list_field_fixtures(store)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return index


def test_keyword_search_indexes_tool_proposal_use_cases(indexed_world):
    page = indexed_world.co_search(["usecasequartz"])
    assert any(hit.object_id == "tpr_list_use_case" for hit in page.hits)


def test_keyword_search_indexes_tool_proposal_current_limitations(indexed_world):
    page = indexed_world.co_search(["limitationnebula"])
    assert any(hit.object_id == "tpr_list_limitation" for hit in page.hits)


def test_keyword_search_indexes_narrative_segment_theme_tags(indexed_world):
    page = indexed_world.co_search(["narrativetagcobalt"])
    assert any(hit.object_id == "nsg_list_theme_tag" for hit in page.hits)


def test_list_field_search_has_no_unrelated_hit_and_communication_experience_still_searches(
    indexed_world,
):
    list_page = indexed_world.co_search(["usecasequartz"])
    assert {hit.object_id for hit in list_page.hits} == {"tpr_list_use_case"}

    communication_page = indexed_world.co_search(["communicationstyleamber"])
    assert any(
        hit.object_id == "cme_search_after_dedup"
        for hit in communication_page.hits
    )
