"""Does a persisted claim actually survive the session boundary?

This test uses no model and no network. The handler is a scripted stand-in for a
competent model: it fills the write with the schema it was shown, and later reads
the answer back out of the continuity anchor. That isolates the kernel's half of
the promise — if this fails, nothing a real model does can save the conversation,
and if it passes, the remaining gap is purely behavioural.

What it deliberately does **not** prove: that a real model volunteers the write.
Measured separately against a live endpoint: three four-turn conversations with a
frontier model produced zero capability calls, with the full write signature and a
copy-this-shape example in the prompt. Kernel plumbing and model willingness are
different problems and are tested differently.
"""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.grok_provider import _render_identity
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore

FACTS = "我叫老王，在东莞做23cm柔性屏手环，跟我说话别用敬语。"


def _build(store_path: Path, index_path: Path, handler, recent_turn_limit: int) -> FusedTurnRuntime:
    store = SQLiteWorldStore(str(store_path))
    index = WorldSearchIndex(str(index_path), store=store)
    index.rebuild()
    return FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=handler,
        subject_id="user_1",
        recent_turn_limit=recent_turn_limit,
    )


def _committing_handler(snapshot, seen: list):
    """A model that does the one thing the prompt asks for: write it down."""

    seen.append(snapshot)
    if snapshot.capability_history:
        return ModelDirective(response="记下了。")

    ref = snapshot.cockpit["task_context"]["current_user_observation_ref"]
    return ModelDirective(
        capability_calls=(
            CapabilityCall(
                name="commit_ai_world_claim",
                arguments={
                    "domain": "user_understanding",
                    "statement": "用户叫老王，在东莞做 23cm 柔性屏手环。",
                    # The kernel must accept exactly this shape; the observation ref
                    # is handed to the model in THIS TURN — GROUNDING.
                    "evidence_refs": [ref],
                    "confidence": 0.95,
                    "tags": ["core_context"],
                },
                call_id="call-1",
            ),
        )
    )


def _asking_handler(snapshot, seen: list):
    seen.append(snapshot)
    return ModelDirective(response="ok")


def test_a_claim_written_in_one_session_is_in_the_anchor_of_the_next(tmp_path: Path) -> None:
    store_path = tmp_path / "world.sqlite"
    index_path = tmp_path / "index.sqlite"
    seen_a: list = []

    session_a = _build(
        store_path, index_path, lambda s: _committing_handler(s, seen_a), recent_turn_limit=2
    )
    session_a.run_turn(
        session_id="s1",
        turn_index=1,
        user_input=FACTS,
        occurred_at=datetime(2026, 10, 22, 10, tzinfo=timezone.utc),
    )

    # The call has to have been executed, not just attempted.
    assert seen_a, "the model was never called"
    assert any(
        r.name == "commit_ai_world_claim" and r.ok for r in seen_a[0].capability_history
    ) or len(seen_a) > 1, "the write never reached the registry"

    seen_b: list = []
    session_b = _build(
        store_path, index_path, lambda s: _asking_handler(s, seen_b), recent_turn_limit=0
    )
    session_b.run_turn(
        session_id="s2",
        turn_index=1,
        # A new session, and no verbatim turns in view: the answer can only come
        # from durable state.
        user_input="我刚才跟你说我是做什么的？在哪个城市？",
        occurred_at=datetime(2026, 10, 23, 9, tzinfo=timezone.utc),
    )

    assert seen_b, "the second session never called the model"
    anchor = _render_identity(seen_b[0].cockpit.get("ai_identity"))
    assert "东莞" in anchor, f"the claim did not survive the session boundary; anchor was:\n{anchor}"
    assert "23cm" in anchor


def test_the_anchor_quotes_the_claim_as_evidence_with_a_reference(tmp_path: Path) -> None:
    """The anchor is evidence, not a script: it must carry the object reference."""

    store_path = tmp_path / "world.sqlite"
    index_path = tmp_path / "index.sqlite"
    seen_a: list = []
    _build(
        store_path, index_path, lambda s: _committing_handler(s, seen_a), recent_turn_limit=2
    ).run_turn(
        session_id="s1",
        turn_index=1,
        user_input=FACTS,
        occurred_at=datetime(2026, 10, 22, 10, tzinfo=timezone.utc),
    )

    seen_b: list = []
    _build(
        store_path, index_path, lambda s: _asking_handler(s, seen_b), recent_turn_limit=0
    ).run_turn(
        session_id="s2",
        turn_index=1,
        user_input="随便聊聊",
        occurred_at=datetime(2026, 10, 23, 9, tzinfo=timezone.utc),
    )

    anchor = _render_identity(seen_b[0].cockpit.get("ai_identity"))
    claim_lines = [line for line in anchor.splitlines() if "老王" in line]
    assert claim_lines, f"no claim line in anchor:\n{anchor}"
    assert "@" in claim_lines[0], "a claim without a reference cannot be weighed or cited"
