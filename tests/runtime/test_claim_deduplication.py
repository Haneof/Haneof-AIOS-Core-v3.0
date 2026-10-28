"""T08: content-level dedup of durable AI-world claims.

The extraction pass re-reads every turn, so it can re-derive a fact the anchor
already holds. Persisting it again would fill the world with duplicate claims, so
the pass asks for the comparison explicitly (``dedupe=True``) and
``_commit_ai_world_claim`` skips the write when a normalized-equal statement is
already active in that domain.

Dedup is deliberately *not* on the capability path: a capability call carries its
own identity, and a request whose arguments changed must never be conflated with
the original even when the statement text matches — that is the replay contract
covered by
``tests/integration/test_core_background_trusted_return_corrective_001_capability_replay.py``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from aios_core.ai_world import AIWorldDomain
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.cognitive_runtime import ModelDirective, RuntimeSnapshot
from aios_core.runtime.turn_runtime import FusedTurnRuntime, _normalize_statement
from aios_core.storage.sqlite_store import SQLiteWorldStore


def _reply_handler(_snapshot: RuntimeSnapshot) -> ModelDirective:
    return ModelDirective(response="好的，我记住了。")


def _make_runtime(tmp_path: Path, *, extractor) -> FusedTurnRuntime:
    store = SQLiteWorldStore(str(tmp_path / "world.sqlite"))
    index = WorldSearchIndex(str(tmp_path / "index.sqlite"), store=store)
    index.rebuild()
    return FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=_reply_handler,
        subject_id="user_1",
        recent_turn_limit=3,
        durable_fact_extractor=extractor,
    )


def test_normalize_folds_case_space_and_punctuation():
    assert _normalize_statement("User is Lao Wang.") == _normalize_statement("user is lao wang!")
    assert _normalize_statement("a, b; c: d") == "abcd"
    assert _normalize_statement("老王，在东莞做手环。") == "老王在东莞做手环"


def test_normalize_preserves_cjk_and_alphanumerics():
    assert _normalize_statement("老王 23cm 手环") == "老王23cm手环"
    assert _normalize_statement("") == ""


def test_duplicate_claim_is_not_persisted_again(tmp_path: Path) -> None:
    def extractor(user_input: str, assistant_text: str):
        return [
            {
                "domain": "user_understanding",
                "statement": "用户叫老王，在东莞做 23cm 手环",
                "confidence": 0.9,
                "tags": ["core_context"],
            }
        ]

    runtime = _make_runtime(tmp_path, extractor=extractor)
    base = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)

    runtime.run_turn(session_id="s1", turn_index=1, user_input="我叫老王。", occurred_at=base)
    runtime.run_turn(session_id="s1", turn_index=2, user_input="再说一遍，我叫老王。", occurred_at=base)

    claims = runtime.ai_world.current(
        domains=(AIWorldDomain("user_understanding"),), limit=100
    )
    # The second turn re-extracted the same fact; it must not become a second claim.
    assert len(claims) == 1
    assert "老王" in claims[0].statement


def test_equivalent_statement_with_different_punctuation_is_deduped(tmp_path: Path) -> None:
    statements = iter(["用户叫老王，在东莞。", "用户叫老王 在东莞"])

    def extractor(user_input: str, assistant_text: str):
        return [
            {
                "domain": "user_understanding",
                "statement": next(statements),
                "confidence": 0.9,
                "tags": ["core_context"],
            }
        ]

    runtime = _make_runtime(tmp_path, extractor=extractor)
    base = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)

    runtime.run_turn(session_id="s1", turn_index=1, user_input="我叫老王。", occurred_at=base)
    runtime.run_turn(session_id="s1", turn_index=2, user_input="我在东莞。", occurred_at=base)

    claims = runtime.ai_world.current(
        domains=(AIWorldDomain("user_understanding"),), limit=100
    )
    assert len(claims) == 1


def test_distinct_claims_both_persist(tmp_path: Path) -> None:
    statements = iter(["用户叫老王", "用户叫李四"])

    def extractor(user_input: str, assistant_text: str):
        return [
            {
                "domain": "user_understanding",
                "statement": next(statements),
                "confidence": 0.9,
                "tags": ["core_context"],
            }
        ]

    runtime = _make_runtime(tmp_path, extractor=extractor)
    base = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)

    runtime.run_turn(session_id="s1", turn_index=1, user_input="我叫老王。", occurred_at=base)
    runtime.run_turn(session_id="s1", turn_index=2, user_input="我叫李四。", occurred_at=base)

    claims = runtime.ai_world.current(
        domains=(AIWorldDomain("user_understanding"),), limit=100
    )
    assert len(claims) == 2
