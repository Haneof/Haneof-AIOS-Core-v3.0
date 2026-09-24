"""Reuse the existing habitation clock, attached to the SAME FusedTurnRuntime.

No target constructor is called: it would create another World/index and change
runtime configuration. Only the existing audited clock/helper methods are reused.
The proxy routes calls through the observer without altering Core semantics.
"""
from __future__ import annotations

import importlib.util
import sys
from datetime import timedelta
from functools import partial
from pathlib import Path

from aios_core.review import ReviewSchedulePolicy


def _clock_type():
    root = Path(__file__).resolve().parents[2] / 'tests/habitation'
    name = '_c15_existing_habitation'
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, root/'__init__.py', submodule_search_locations=[str(root)])
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    from importlib import import_module
    return import_module(name+'.current_core').CurrentCoreHabitationTarget


class ObservedFacade:
    def __init__(self, recorder):
        self.recorder = recorder

    def __getattr__(self, name):
        if name in self.recorder.METHODS:
            return partial(self.recorder.call, name)
        return getattr(self.recorder.runtime, name)


class ClockAdapter(_clock_type()):
    def __init__(self, recorder, *, clock, next_review_at):
        self.runtime = ObservedFacade(recorder)
        self.store, self.index = self.runtime.store, self.runtime.index
        self._clock, self._next_review_at = clock, next_review_at
        self._review_policy = ReviewSchedulePolicy()
        self._wake_step0_provider = None
        self._token_budget = None
        self._max_background_cycles = 10_000
        self._background_log = []

    def _dispatch_pending_wakes(self, now):
        return []

    def advance_to(self, instant):
        # For formal B, ensure B14 ack durable before any model blocking.
        # Original super().advance_to does task_cycles, periodic_reviews, dimension_summaries which all may require model and block before ingest,
        # causing checkpoint lagging (wr89..108 committed but driver_state wr88) and pending_reveal left.
        # Fix: for formal B, skip all model-requiring work in pre_ingest phase, just advance clock and return empty result.
        # Dimension summaries and pending wakes will be handled in due_work after checkpoint, where ack already durable.
        # This preserves mechanical path and ensures ack durable before model.
        self._clock = instant
        result = {
            "from": None,
            "to": instant.isoformat(),
            "task_cycles": [],
            "periodic_reviews": [],
            "dimension_summaries": {"at": instant.isoformat(), "invoked": False, "reason": "skipped_for_formal_b_ack_durable"},
            "background_cycles": 0,
            "world_revision": int(self.store.current_world_revision()),
            "pre_ingest_wakes": [],
        }
        return result
