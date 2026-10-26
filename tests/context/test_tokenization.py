"""Token estimation contract for aios_core.context.tokenization.

What this pins is a direction, not a tokenizer. The legacy estimator billed every
character at ``len(json)/4`` = 0.25 token/char. Measured against a real API
(differential slope method) Chinese costs ~0.636 token/char, so the old formula
under-counted Chinese by ~2.55x and the budget never reported an overflow. The
tests below assert the one property that matters: for CJK text the new estimate
must clear a conservative floor of the real cost -- never under-count -- while
ASCII text must stay in the band the old estimator already established.
"""

from __future__ import annotations

import json
import math
import time

import pytest

from aios_core.context.tokenization import (
    ASCII_TOKENS_PER_CHAR,
    CJK_TOKENS_PER_CHAR,
    count_text_tokens,
    estimate_tokens,
)

# Empirical reference coefficients (real API, differential slope method).
REF_CJK = 0.636
REF_OTHER = 0.207

# The floor: measured CJK cost discounted to 0.6, everything else at the legacy
# 0.25. Lower than any honest estimate must be, higher than the old /4 ever was.
FLOOR_CJK = 0.6
FLOOR_OTHER = 0.25

_CJK_RANGES = (
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0xF900, 0xFAFF),
    (0x3040, 0x30FF),
    (0xAC00, 0xD7AF),
    (0x3000, 0x303F),
)


def _legacy_estimate(value: object) -> int:
    """The pre-fix formula, reproduced so tests can prove it is the wrong shape."""

    text = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return max(1, (len(text) + 3) // 4)


def _floor(text: str) -> int:
    """Conservative lower bound on the real token count of ``text``."""

    cjk = sum(1 for char in text if any(lo <= ord(char) <= hi for lo, hi in _CJK_RANGES))
    return int(cjk * FLOOR_CJK + (len(text) - cjk) * FLOOR_OTHER)


def _reference(text: str) -> float:
    """Empirical reference: 0.636 token/char CJK, 0.207 otherwise."""

    cjk = sum(1 for char in text if any(lo <= ord(char) <= hi for lo, hi in _CJK_RANGES))
    return cjk * REF_CJK + (len(text) - cjk) * REF_OTHER


_ZH = (
    "用户谈到城西那套老房子下个月就要拆迁，父亲留下的那台蝴蝶牌缝纫机至今不知道该搬到哪里去。"
    "他说母亲当年在灯下踩着踏板做衣服的声音，是他记忆里最稳定的一段背景音，"
    "机器一响，整个屋子就像还有人在。"
)

_EN = (
    "The user is unsure what to do with the old sewing machine his father left behind, "
    "and the house in the west of the city is scheduled for demolition next month."
)

_MIX = (
    "用户说 memory continuity 是关键，因为 model API 是 stateless 的，"
    "每轮都要把 world snapshot 重新渲染成 prompt。"
)

_FULLWIDTH = "「缝纫机」——母亲留下的遗物；父亲说过：「别丢。」（他说得很轻）"


def _zh(length: int) -> str:
    out = ""
    while len(out) < length:
        out += _ZH
    return out[:length]


# ---------------------------------------------------------------------------
# Core property: never under-count CJK.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("length", [50, 200, 600, 2000])
def test_chinese_is_never_undercounted(length: int) -> None:
    """New estimate must clear the conservative floor at every Chinese size."""

    sample = _zh(length)
    assert count_text_tokens(sample) >= _floor(sample)
    assert count_text_tokens(sample) >= _reference(sample)


def test_legacy_formula_does_undercount_chinese() -> None:
    """The bug this module fixes, stated as a fact: /4 is 2.5x blind on Chinese."""

    sample = _zh(600)
    legacy = _legacy_estimate(sample)
    new = estimate_tokens(sample)

    assert new > legacy, "the new estimator must bill Chinese higher than /4"
    assert legacy < _floor(sample), "the legacy formula is expected to miss the floor"
    assert new >= _floor(sample)
    # The gap is the whole point: /4 sees roughly a third of the real cost.
    assert new / legacy == pytest.approx(2.8, abs=0.3)


def test_chinese_estimates_above_the_english_rate() -> None:
    """A Chinese char must not be billed like an ASCII char."""

    assert CJK_TOKENS_PER_CHAR > ASCII_TOKENS_PER_CHAR
    zh_sample = _zh(1000)
    en_sample = _zh(0) + _EN * 8
    assert len(en_sample) >= len(zh_sample)
    assert count_text_tokens(zh_sample) > count_text_tokens(en_sample)


# ---------------------------------------------------------------------------
# English must not inflate.
# ---------------------------------------------------------------------------


def test_english_stays_in_the_legacy_band() -> None:
    """ASCII keeps the /4 rate, so English estimates are unchanged, not inflated."""

    sample = _EN * 6
    legacy = _legacy_estimate(sample)
    new = estimate_tokens(sample)

    assert new == legacy, "ASCII-only input must keep the legacy /4 estimate"
    # And /4 already sits above the measured 0.207 token/char for English.
    assert new >= _reference(sample)


def test_mixed_text_lands_between_the_two_bands() -> None:
    """中英混排: above the legacy count, still under a full CJK billing."""

    sample = _MIX
    assert estimate_tokens(sample) > _legacy_estimate(sample)
    assert count_text_tokens(sample) >= _floor(sample)
    assert count_text_tokens(sample) <= math.ceil(len(sample) * CJK_TOKENS_PER_CHAR)


# ---------------------------------------------------------------------------
# Shapes the controller actually measures.
# ---------------------------------------------------------------------------


def test_nested_json_structures_are_counted() -> None:
    """dict/list nesting: values dominate, but JSON syntax is billed too."""

    payload = {
        "turn_index": 1,
        "user": {"text": _zh(300)},
        "assistant": {"text": _zh(160)},
        "tags": ["relationship", "event"],
        "scores": [{"object_id": f"obj_{i}", "score": 90 - i} for i in range(8)],
    }

    new = estimate_tokens(payload)
    inner = "".join(
        [
            payload["user"]["text"],
            payload["assistant"]["text"],
            "relationship",
            "event",
            "".join(f"obj_{i}" for i in range(8)),
        ]
    )

    assert new >= _floor(inner), "nested payload must clear the floor of its content"
    assert new > _legacy_estimate(payload)
    assert new > count_text_tokens(inner), "JSON syntax overhead must be billed"


def test_estimate_tokens_accepts_any_jsonable_value() -> None:
    """Legacy signature: str, None, numbers, containers, non-serialisable objects."""

    assert estimate_tokens("中文") == count_text_tokens('"中文"')
    assert estimate_tokens(None) >= 1
    assert estimate_tokens(12345) >= 1
    assert estimate_tokens([{"a": "缝纫机"}, {"b": "老房子"}]) >= _floor("缝纫机老房子")

    class _Opaque:
        def __str__(self) -> str:
            return "不透明对象"

    assert estimate_tokens({"x": _Opaque()}) >= _floor("不透明对象")


def test_fullwidth_punctuation_is_billed_at_the_cjk_rate() -> None:
    """。、「」are U+3000-U+303F and must count as CJK, not as ASCII."""

    assert count_text_tokens("。") >= 1
    assert count_text_tokens(_FULLWIDTH) >= _floor(_FULLWIDTH)
    # Same character count, but CJK punctuation must cost more than ASCII punctuation.
    assert count_text_tokens("。，，") > count_text_tokens("...")


def test_kana_and_hangul_are_billed_at_the_cjk_rate() -> None:
    """No per-language measurement exists for kana/Hangul; bill them like CJK."""

    kana = "ミシンは母の形見です。父は「捨てるな」と言いました。"
    hangul = "그 재봉틀은 어머니의 유품입니다. 아버지는 버리지 말라고 했습니다."

    assert count_text_tokens(kana) >= _floor(kana)
    assert count_text_tokens(hangul) >= _floor(hangul)
    assert count_text_tokens(kana) > _legacy_estimate(kana)


# ---------------------------------------------------------------------------
# Degenerate input: the estimator is held in Field(ge=...) positions downstream.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("sample", ["", "中", "a", " ", "。", None, 0, {}, []])
def test_degenerate_input_never_returns_zero(sample: object) -> None:
    """A 0 would be rejected by pydantic validation, not by the budget."""

    assert estimate_tokens(sample) >= 1
    if isinstance(sample, str):
        assert count_text_tokens(sample) >= 1


def test_empty_string_is_one_token() -> None:
    assert count_text_tokens("") == 1
    assert estimate_tokens("") == 1


# ---------------------------------------------------------------------------
# Monotonicity and scale.
# ---------------------------------------------------------------------------


def test_estimation_is_monotonic_in_text_length() -> None:
    """A longer text never estimates cheaper than its prefix."""

    previous = 0
    for repeat in range(1, 60):
        current = count_text_tokens(_ZH * repeat)
        assert current >= previous
        previous = current


def test_monotonic_under_single_character_growth() -> None:
    sample = ""
    previous = count_text_tokens(sample)
    for char in _ZH[:400]:
        sample += char
        current = count_text_tokens(sample)
        assert current >= previous
        previous = current


def test_oversized_text_does_not_blow_up() -> None:
    """>100k characters must be counted iteratively: no recursion, no timeout."""

    huge = _zh(120_000)
    assert len(huge) == 120_000

    started = time.perf_counter()
    tokens = count_text_tokens(huge)
    elapsed = time.perf_counter() - started

    assert tokens >= _floor(huge)
    assert tokens > _legacy_estimate(huge)
    assert elapsed < 5.0, f"120k chars took {elapsed:.2f}s"

    payload = {"world": [{"id": i, "text": _zh(2_000)} for i in range(60)]}
    started = time.perf_counter()
    nested = estimate_tokens(payload)
    elapsed = time.perf_counter() - started
    assert nested > 0
    assert elapsed < 5.0, f"nested 120k-char payload took {elapsed:.2f}s"
