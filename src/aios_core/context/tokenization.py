"""Token estimation for AIOS v3.0 context assembly.

Why this module exists
----------------------
``ContextController`` decides whether a memory section fits into the budget by
calling ``estimate_tokens``. The historical implementation was::

    len(json.dumps(value, ensure_ascii=False)) / 4

i.e. a flat 0.25 token/char. Measured against a real API (differential slope
method, so the fixed template overhead cancels out):

* Chinese: ~0.636 token/char  -> ``/4`` under-counts by ~2.55x
* English: ~0.207 token/char  -> ``/4`` slightly over-counts, which is why the
  bug stayed invisible for as long as the corpus was mostly ASCII

An estimator that cannot see the cost of Chinese is worse than no estimator: it
reports "never over budget" while the prompt is already past the limit, and the
moment it is fixed the same input jumps and starts dropping memory silently.

The model
---------
Two coefficients, applied per character:

* CJK and CJK-like code points: ``CJK_TOKENS_PER_CHAR = 0.7``.
  Measured Chinese is ~0.636; we deliberately use 0.7.
* Everything else (ASCII letters, digits, JSON syntax, whitespace):
  ``ASCII_TOKENS_PER_CHAR = 0.25``, unchanged from the legacy estimator.

Why 0.7 and not 0.636 -- "宁高勿低" (never under-count)
------------------------------------------------------
This estimator is a *budget guard*, not a tokenizer. Its only job is to decide
whether a section is admitted into the prompt. The two error directions are not
symmetric:

* Over-count: a section is dropped that would have fit. Annoying, visible,
  recoverable -- the section stays in the store and can come back next round.
* Under-count: the budget is exceeded, the model is fed a prompt larger than
  what the budget was sized for, or a later section is dropped to compensate.
  The model experiences unexplained amnesia, and the overflow never shows up in
  ``truncated`` because the estimator swore it never happened.

So we round *up*. 0.7 vs 0.636 is a ~10% safety margin on CJK, and it keeps the
estimator honest for Japanese kana and Hangul, which we have no per-language
measurement for. English keeps 0.25, which already sits above its measured
0.207, so English estimates stay in the same band as before.

No third-party dependency (no tiktoken, no transformers): this is a wearable /
edge kernel and the dependency surface must stay at zero. Code point ranges are
used instead of ``unicodedata`` because they are faster and are exactly the
contract we want to pin.
"""

from __future__ import annotations

import json
import math
from typing import Any

#: Tokens per character for CJK and CJK-like code points.
#: Measured Chinese is ~0.636 token/char (real API, differential slope method);
#: we deliberately round up to 0.7 -- a budget estimator must never under-count.
CJK_TOKENS_PER_CHAR = 0.7

#: Tokens per character for everything else (ASCII, digits, JSON syntax, spaces).
#: Unchanged from the legacy ``len(text) / 4`` estimator, and still above the
#: measured ~0.207 token/char for English.
ASCII_TOKENS_PER_CHAR = 0.25

#: Code point ranges treated as CJK-like, i.e. billed at CJK_TOKENS_PER_CHAR.
#: (inclusive lower bound, inclusive upper bound)
CJK_CODE_POINT_RANGES: tuple[tuple[int, int], ...] = (
    (0x3400, 0x4DBF),  # CJK Unified Ideographs Extension A
    (0x4E00, 0x9FFF),  # CJK Unified Ideographs (the common Chinese band)
    (0xF900, 0xFAFF),  # CJK Compatibility Ideographs
    (0x3040, 0x30FF),  # Japanese kana (hiragana + katakana)
    (0xAC00, 0xD7AF),  # Hangul syllables
    (0x3000, 0x303F),  # CJK symbols and punctuation (。、「」etc.)
)


def _is_cjk(code_point: int) -> bool:
    """Whether a code point is billed at the CJK rate.

    The ``code_point < 0x3000`` fast path matters: real prompts are dominated by
    ASCII, and that single comparison skips the range scan for all of it, which
    keeps 100k+ character snapshots well inside a single-digit millisecond.
    """

    if code_point < 0x3000:
        return False
    for lower, upper in CJK_CODE_POINT_RANGES:
        if lower <= code_point <= upper:
            return True
    return False


def count_text_tokens(text: str) -> int:
    """Estimated token count for a plain string.

    Returns at least 1: downstream models hold this in ``Field(ge=...)``
    positions, so a 0 would be rejected by validation rather than by us.

    Monotonic by construction -- every extra character adds a non-negative
    amount, so a longer text never estimates cheaper than its prefix.
    """

    cjk = 0
    for char in text:
        if _is_cjk(ord(char)):
            cjk += 1
    rest = len(text) - cjk
    return max(
        1,
        math.ceil(cjk * CJK_TOKENS_PER_CHAR + rest * ASCII_TOKENS_PER_CHAR),
    )


def estimate_tokens(value: Any) -> int:
    """Estimated token count for any JSON-able object (legacy signature).

    Serialization is unchanged from the legacy estimator except for
    ``sort_keys``: ``ensure_ascii=False`` is mandatory, because escaping Chinese
    into ``\\uXXXX`` would inflate the character count ~6x and corrupt exactly
    the measurement this module exists to fix.
    """

    text = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return count_text_tokens(text)


__all__ = [
    "ASCII_TOKENS_PER_CHAR",
    "CJK_CODE_POINT_RANGES",
    "CJK_TOKENS_PER_CHAR",
    "count_text_tokens",
    "estimate_tokens",
]
