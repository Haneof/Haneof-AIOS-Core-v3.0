"""Identity continuity across context exhaustion.

The failure this locks down: after the anchor turns scroll out of RECENT
CONVERSATION, the model used to receive a factory identity and nothing else — the
user's name, their work, their standing preferences and the assistant's own
invariants were all absent. Switching model or starting a new session therefore
felt like talking to a different assistant.

Three separate breaks caused that, and each gets its own assertion here:

1. ``ai_identity`` is a mapping, so the scalar-only prompt builder dropped it.
2. Round summaries were committed and budgeted into the cockpit but had no renderer.
3. Persisting several durable facts from one utterance failed on a content-addressed
   evidence-set collision, so "I'm Lao Wang, I build 23cm bands, drop the honorifics"
   could only keep one fact.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.cognitive_runtime import ModelDirective, RuntimeSnapshot
from aios_core.runtime.grok_provider import GrokProviderConfig, GrokStreamingProvider
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore


class _PromptCapture:
    """Stub the network call and keep the exact system prompt the model would read."""

    def __init__(self) -> None:
        self.prompts: list[str] = []
        self.provider = GrokStreamingProvider(
            GrokProviderConfig(api_key="test-key", base_url="http://127.0.0.1:1/v1")
        )
        self.provider.stream_chat = self._stream_chat  # type: ignore[method-assign]

    def _stream_chat(self, messages, *, model=None, **kwargs):
        self.prompts.append(messages[0]["content"])
        return "ok", [], None

    @property
    def last(self) -> str:
        assert self.prompts, "no prompt was captured"
        return self.prompts[-1]


def _snapshot(cockpit: dict) -> RuntimeSnapshot:
    return RuntimeSnapshot(
        user_input=cockpit.get("user_input", "hi"),
        wake_reason="user_explicit",
        cockpit=cockpit,
        capability_catalog=(),
        capability_history=(),
        round_index=0,
        remaining_tool_rounds=2,
    )


def _run(snapshot: RuntimeSnapshot) -> str:
    capture = _PromptCapture()
    handler = capture.provider.as_model_handler()
    try:
        handler(snapshot)
    except Exception:
        # Only the outbound prompt matters here; the stub's usage payload may be
        # rejected after the request was already captured.
        pass
    return capture.last


def _claim(domain: str, statement: str, ref: str, revision: int = 1) -> dict:
    return {
        "domain": domain,
        "dimension": f"dim_{domain}",
        "object_id": ref,
        "revision": revision,
        "statement": statement,
        "confidence": 0.9,
    }


def test_identity_anchor_is_rendered_with_evidence_refs() -> None:
    prompt = _run(
        _snapshot(
            {
                "user_input": "我们上次说到哪了？",
                "ai_identity": {
                    "relationship": [
                        _claim("relationship", "用户要求不用敬语、直接说结论", "clm_rel1", 2)
                    ],
                    "user_understanding": [
                        _claim("user_understanding", "用户叫老王", "clm_user1"),
                        _claim("user_understanding", "用户做 23cm 柔性屏手环", "clm_user2"),
                    ],
                    "symbiotic_posture": "old_friend",
                    "rapport_score": 0.5,
                    "outstanding_promises": [
                        {"desc": "周四再问一次东莞供应链", "due": "2026-10-23"}
                    ],
                },
                "recent_turns": [],
            }
        )
    )

    assert "CONTINUITY ANCHOR" in prompt
    assert "用户叫老王" in prompt
    assert "23cm" in prompt
    assert "不用敬语" in prompt
    # Claims must stay citable, not become unattributed persona prose.
    assert "clm_user1@1" in prompt
    assert "clm_rel1@2" in prompt
    # Promises are the strongest evidence of "same assistant, still owes me this".
    assert "周四再问一次东莞供应链" in prompt
    assert "posture=old_friend" in prompt


def test_standing_constraints_precede_dialogue_and_are_never_omitted() -> None:
    prompt = _run(
        _snapshot(
            {
                "user_input": "继续",
                "ai_identity": {
                    "ethical_invariants": ["反爹味、反谄媚，守住平等真诚"],
                    "symbiotic_posture": "old_friend",
                },
                "recent_turns": [
                    {
                        "turn_index": 40,
                        "user": {"text": "供应链还是卡着"},
                        "assistant": {"text": "我记着"},
                    }
                ],
            }
        )
    )

    assert "STANDING CONSTRAINTS" in prompt
    assert "反爹味" in prompt
    assert prompt.index("STANDING CONSTRAINTS") < prompt.index("RECENT CONVERSATION")
    assert prompt.index("CONTINUITY ANCHOR") < prompt.index("RECENT CONVERSATION")


def test_round_summaries_reach_the_prompt_as_covered_history() -> None:
    prompt = _run(
        _snapshot(
            {
                "user_input": "继续",
                "ai_identity": {},
                "conversation_summaries": [
                    {
                        "turn_start": 1,
                        "turn_end": 4,
                        "content": "用户说明自己在杭州做柔性屏手环，供应链卡在东莞。",
                    }
                ],
                "recent_turns": [],
            }
        )
    )

    assert "WHAT WE ALREADY COVERED" in prompt
    assert "turns 1-4" in prompt
    assert "供应链卡在东莞" in prompt
    # Summaries are an index; the exact-wording route must stay named.
    assert "drill_down_conversation" in prompt


def test_absent_identity_creates_no_continuity_block() -> None:
    """No evidence must not become fabricated continuity."""

    prompt = _run(_snapshot({"user_input": "你好", "ai_identity": {}, "recent_turns": []}))

    assert "CONTINUITY ANCHOR" not in prompt
    assert "STANDING CONSTRAINTS" not in prompt


def test_identity_keys_are_not_duplicated_into_scalar_cockpit() -> None:
    prompt = _run(
        _snapshot(
            {
                "user_input": "继续",
                "ai_identity": {
                    "symbiotic_posture": "comrade",
                    "rapport_score": 0.82,
                },
                "recent_turns": [],
            }
        )
    )

    cockpit_section = prompt.split("ACTIVE COCKPIT CONTEXT:")
    if len(cockpit_section) > 1:
        assert "symbiotic_posture" not in cockpit_section[1].split("RECENT CONVERSATION")[0]
    assert "posture=comrade" in prompt


def test_oversized_anchor_keeps_the_relationship_entries() -> None:
    """Trimming must drop the tail, not the head.

    Relationship entries come first because they frame how everything else is read.
    Truncating from the tail (the previous behaviour) would have kept the status line
    and discarded the relationship, which is exactly backwards.
    """

    prompt = _run(
        _snapshot(
            {
                "user_input": "继续",
                "ai_identity": {
                    "relationship": [
                        _claim("relationship", "用户要求不用敬语、直接说结论", "clm_rel_head")
                    ],
                    "user_understanding": [
                        _claim("user_understanding", f"用户细节条目 {i} " + "填充" * 40, f"clm_u{i}")
                        for i in range(20)
                    ],
                    "symbiotic_posture": "old_friend",
                },
                "recent_turns": [],
            }
        )
    )

    assert "clm_rel_head@1" in prompt
    assert "不用敬语" in prompt
    assert "further anchor entries omitted" in prompt


def _build_runtime(tmp_path: Path, capture: _PromptCapture) -> tuple[FusedTurnRuntime, dict]:
    store = SQLiteWorldStore(str(tmp_path / "world.sqlite"))
    index = WorldSearchIndex(str(tmp_path / "index.sqlite"), store=store)
    index.rebuild()

    ref: dict = {}

    def handler(snapshot: RuntimeSnapshot) -> ModelDirective:
        runtime = ref["rt"]
        user_ref = (snapshot.cockpit.get("task_context") or {}).get(
            "current_user_observation_ref"
        )
        if user_ref and not ref.get("committed"):
            ref["committed"] = True
            for domain, statement in (
                ("user_understanding", "用户叫老王"),
                ("user_understanding", "用户做 23cm 柔性屏手环"),
                ("user_understanding", "供应链卡在东莞那家供应商"),
                ("relationship", "用户要求不用敬语"),
            ):
                runtime._commit_ai_world_claim(
                    domain=domain,
                    statement=statement,
                    evidence_refs=[user_ref],
                    confidence=0.9,
                    knowledge_state="observed",
                    claim_type="fact",
                    tags=("core_context",),
                )
        try:
            return capture.provider.as_model_handler()(snapshot)
        except Exception:
            return ModelDirective(response="ok")

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=handler,
        subject_id="user_1",
        recent_turn_limit=3,
    )
    ref["rt"] = runtime
    return runtime, ref


def test_identity_survives_context_exhaustion_end_to_end(tmp_path: Path) -> None:
    """The anchor turn leaves the window; the identity facts must not leave with it."""

    capture = _PromptCapture()
    runtime, ref = _build_runtime(tmp_path, capture)

    turns = [
        "请记住：我叫老王，做 23cm 柔性屏手环，供应链卡在东莞那家。别跟我用敬语。",
        "今天天气怎么样？",
        "海底火山为什么会喷发？",
        "四季是怎么形成的？",
        "光速为什么不变？",
        "推荐一部纪录片。",
        "咖啡因多久代谢完？",
        "珠峰有多高？",
        "企鹅会飞吗？",
        "我们上次说到哪了？",
    ]
    base = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)
    for i, text in enumerate(turns, start=1):
        runtime.run_turn(
            session_id="s_anchor",
            turn_index=i,
            user_input=text,
            occurred_at=base + timedelta(minutes=5 * i),
        )

    prompt = capture.last

    # Precondition: the anchor utterance itself is gone from verbatim history.
    assert "请记住：我叫老王" not in prompt
    assert "[turn 1]" not in prompt

    # Yet the durable facts are still in front of the model.
    assert "CONTINUITY ANCHOR" in prompt
    assert "老王" in prompt
    assert "23cm" in prompt
    assert "东莞" in prompt
    assert "敬语" in prompt
    assert ref["committed"] is True
