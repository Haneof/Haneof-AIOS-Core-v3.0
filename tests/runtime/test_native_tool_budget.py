"""The tools array is a budget, so what goes in it needs a test.

Advertising all 53 capabilities cost 34,736 characters on every dialogue call.
The measured benefit on the endpoint available here was zero calls in six turns,
so the payload was almost entirely waste. The hot set cuts it to twelve.

Two things have to stay true for that trade to be safe:

1. the payload really is smaller (otherwise nothing was gained), and
2. a capability left out of the array is still reachable (otherwise it was
   silently removed from the product).
"""

from __future__ import annotations

import json
from pathlib import Path

from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.grok_provider import (
    _HOT_TOOL_NAMES,
    _build_native_tools,
    native_tools_enabled,
    select_native_tools,
)
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore


def _catalog(tmp_path: Path) -> list:
    captured: dict = {}

    def handler(snapshot):  # type: ignore[no-untyped-def]
        captured["snap"] = snapshot
        return ModelDirective(response="ok")

    store = SQLiteWorldStore(str(tmp_path / "world.sqlite"))
    index = WorldSearchIndex(str(tmp_path / "index.sqlite"), store=store)
    index.rebuild()
    FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=handler,
        subject_id="user_1",
        recent_turn_limit=2,
    ).run_turn(
        session_id="s",
        turn_index=1,
        user_input="hi",
        occurred_at=__import__("datetime").datetime(
            2026, 10, 28, 10, tzinfo=__import__("datetime").timezone.utc
        ),
    )
    return captured["snap"].capability_catalog


def test_hot_set_is_a_small_fraction_of_the_payload(tmp_path: Path) -> None:
    catalog = _catalog(tmp_path)
    full = _build_native_tools(catalog)
    hot = select_native_tools(catalog)

    assert len(full) == len(catalog)
    assert len(hot) <= 15
    assert len(hot) < len(full) / 2

    full_chars = len(json.dumps(full, ensure_ascii=False))
    hot_chars = len(json.dumps(hot, ensure_ascii=False))
    assert hot_chars <= 8_000, f"hot set is {hot_chars} chars, over the 8k budget"
    assert hot_chars < full_chars / 3


def test_hot_set_covers_every_write_the_standing_prompt_asks_for(tmp_path: Path) -> None:
    """If a prompt instruction names a capability, it cannot be cold."""

    names = {tool["function"]["name"] for tool in select_native_tools(_catalog(tmp_path))}
    for required in (
        "commit_ai_world_claim",
        "revise_claim",
        "retract_claim",
        "record_ai_promise",
        "propose_goal",
        "create_task",
    ):
        assert required in names


def test_a_cold_capability_is_still_reachable_by_name(tmp_path: Path) -> None:
    """Cold means "no schema advertised", not "removed from the product".

    The names stay in the prompt and the text-protocol parser still accepts them,
    so the model can call one when it knows it exists.
    """

    from aios_core.runtime.grok_provider import GrokStreamingProvider

    catalog = _catalog(tmp_path)
    hot_names = {tool["function"]["name"] for tool in select_native_tools(catalog)}
    cold = next(
        cap["name"]
        for cap in catalog
        if cap.get("name") not in hot_names and cap.get("name") != "commit_ai_world_claim"
    )
    text = f'```json\n{{"call": "{cold}", "arguments": {{}}}}\n```'
    calls = GrokStreamingProvider._extract_capability_calls(text, catalog)
    assert [call.name for call in calls] == [cold]


def test_switch_off_disables_advertising(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AIOS_NATIVE_TOOLS", "off")
    assert native_tools_enabled() is False
    monkeypatch.setenv("AIOS_NATIVE_TOOLS", "on")
    assert native_tools_enabled() is True
    monkeypatch.delenv("AIOS_NATIVE_TOOLS", raising=False)
    assert native_tools_enabled() is True


def test_hot_names_are_all_real_capabilities(tmp_path: Path) -> None:
    """A typo here would silently shrink the array without failing anything else."""

    names = {cap["name"] for cap in _catalog(tmp_path)}
    assert _HOT_TOOL_NAMES <= names
