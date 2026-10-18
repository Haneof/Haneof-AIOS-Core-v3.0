from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore


def run_due_for_event(
    runtime: FusedTurnRuntime,
    store: SQLiteWorldStore,
    index: WorldSearchIndex,
    now: datetime,
    append_trace: Callable[[str, Any], None],
) -> None:
    index.catch_up()
    summary_result = runtime.run_due_dimension_summaries(now=now)
    append_trace("summary_scheduler_result", summary_result)
    index.catch_up()

    reconcile = runtime.cognitive_derivation.reconcile()
    append_trace("c14_reconcile", reconcile)
    index.catch_up()

    for _ in range(100):
        result = runtime.dispatch_next_pending_wake(now=now)
        if result is None:
            break
        append_trace("wake_dispatch_result", result)
        index.catch_up()
    else:
        raise RuntimeError("mechanical wake drain exceeded 100 iterations")

    review = runtime.run_periodic_review(now=now)
    if review is not None:
        append_trace("periodic_review_result", review)
        index.catch_up()
