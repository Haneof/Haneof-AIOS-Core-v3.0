from datetime import datetime, timezone

import pytest

from aios_core.query.search import WorldSearchIndex
from aios_core.runtime import (
    ModelCallProvenance,
    ModelDirective,
    ModelUsage,
    TurnExecutionInDoubt,
)
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore


NOW = datetime(2026, 9, 24, 9, 50, tzinfo=timezone.utc)
TURN = {
    "session_id": "independent-old-blocker",
    "turn_index": 1,
    "user_input": "independent blocker reproduction",
    "occurred_at": NOW,
}


def _directive():
    return ModelDirective(
        response="must not execute",
        usage=ModelUsage(
            input_tokens=1,
            output_tokens=1,
            total_tokens=2,
            provider="synthetic",
            model="synthetic-model",
            request_id="independent-old-blocker",
        ),
        provenance=ModelCallProvenance(
            provider="synthetic",
            model="synthetic-model",
            request_id="independent-old-blocker",
        ),
    )


def test_independent_reproduces_claim_to_attempt_dead_zone(tmp_path, monkeypatch):
    store = SQLiteWorldStore(tmp_path / "world.sqlite")
    index = WorldSearchIndex(tmp_path / "index.sqlite", store=store)
    provider_calls = []

    def model(_snapshot):
        provider_calls.append("called")
        return _directive()

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)

    def crash_before_attempt_admission(**_kwargs):
        raise RuntimeError("INDEPENDENT crash after claim before attempt admission")

    monkeypatch.setattr(
        runtime.background_model_attempts,
        "admit",
        crash_before_attempt_admission,
    )

    with pytest.raises(RuntimeError, match="after claim before attempt admission"):
        runtime.run_turn(**TURN)

    inspected = runtime.inspect_turn_execution(**TURN)
    assert inspected.recovery_disposition == "in_doubt"
    assert inspected.model_attempts == ()
    assert provider_calls == []

    with pytest.raises(TurnExecutionInDoubt):
        runtime.authorize_turn_retry(
            **TURN,
            evidence="provider dispatch was structurally unreachable",
        )
