"""Model context preparation for AIOS v3.0."""

from .active_window import ActiveRollingWindow, ActiveTurn
from .continuity import (
    ConversationContinuityService,
    ConversationMessage,
    ContinuitySnapshot,
    ROUND_SUMMARY_KIND,
    RoundSummaryCommit,
    RoundSummaryRequest,
)
from .controller import ContextController, ModelContextBundle
# estimate_tokens lives in .tokenization and is only re-exported by .controller for
# the legacy ``from aios_core.context.controller import estimate_tokens`` path. The
# package exports it from the owning module so both import paths resolve to the same
# object and the package never depends on that compatibility shim.
from .tokenization import count_text_tokens, estimate_tokens

__all__ = [
    "ActiveRollingWindow",
    "ActiveTurn",
    "ContextController",
    "ModelContextBundle",
    "count_text_tokens",
    "estimate_tokens",
    "ConversationContinuityService",
    "ConversationMessage",
    "ContinuitySnapshot",
    "ROUND_SUMMARY_KIND",
    "RoundSummaryCommit",
    "RoundSummaryRequest",
]
