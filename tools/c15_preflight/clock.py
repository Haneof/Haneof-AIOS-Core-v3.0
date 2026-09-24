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
        # The underlying clock's old helper dispatches a snapshot directly via
        # run_wake. Use the normal router instead to retain background batching
        # and REVIEW_QUEUE exclusion. Never repeatedly retry a deferred head.
        results = []
        for _ in range(self._max_background_cycles):
            result = self.runtime.dispatch_next_pending_wake(now=now)
            if result is None:
                return results
            results.append({'wake_id': result.wake_ref.object_id, 'state': result.wake.state})
            if result.runtime is None or result.wake.state != 'completed':
                return results
        raise RuntimeError('clock dispatch safety cap; not completion')

    def advance_to(self, instant):
        result = super().advance_to(instant)
        if result.get('dimension_summaries', {}).get('truncated'):
            raise RuntimeError('clock Summary incomplete; not completion')
        # advance_to only dispatches at Task/Review ticks. A boundary with no
        # such tick still needs the normal router pass BEFORE the new input is
        # ingested. Use this protocol boundary, never backdate model execution
        # to the Wake's origin or force-drain a budget-deferred queue.
        result['pre_ingest_wakes'] = self._dispatch_pending_wakes(instant)
        return result
