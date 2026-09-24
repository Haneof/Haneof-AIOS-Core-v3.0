"""Reuse the existing habitation clock, attached to the SAME FusedTurnRuntime.

No target constructor is called: it would create another World/index and change
runtime configuration. Only the existing audited clock/helper methods are reused.
The proxy routes calls through the observer without altering Core semantics.
"""
from __future__ import annotations

import importlib.util
import sys
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

    @staticmethod
    def _pre_ingest_view(run):
        """Expose only mechanical scheduling state required by the operator.

        Core owns the Wake state transition and budget decision.  The operator
        records it; it never rewrites QUEUED/RUNNING into completion.
        """
        runtime = run.get("runtime")
        return {
            "wake_ref": {
                "object_id": run["wake_id"],
                "revision": run["wake_revision"],
            },
            "wake_source": run["wake_source"],
            "state": run["wake_state"],
            "termination_reason": (
                runtime.get("termination_reason")
                if isinstance(runtime, dict)
                else None
            ),
            "step0": run.get("step0"),
        }

    def advance_to(self, instant):
        """Advance with the existing scheduler before the caller ingests input.

        The inherited habitation scheduler owns intermediate task/review ticks,
        so a T+49h advance still executes the T+24h review at T+24h.  Its normal
        Wake dispatch path is observed through RuntimeRecorder.

        Dimension-summary work is also executed by the inherited scheduler at
        the target instant.  After that, drain any remaining non-user/background
        Wake once through the same normal Core path *before* returning to Driver,
        while the newly revealed event is still not in World.  A budget-denied
        or otherwise unfinished Wake remains non-completed and is merely
        reported in pre_ingest_wakes; this adapter never force-completes it.
        """
        result = dict(super().advance_to(instant))

        # The parent scheduler dispatches Wakes at intermediate due ticks.  A
        # Wake can also already be pending when there is no intermediate tick,
        # or be emitted by the target-time dimension-summary pass.  Dispatch
        # those now, still before Driver.ingest(event).
        trailing = self._dispatch_pending_wakes(self._clock)
        result["pre_ingest_wakes"] = [
            self._pre_ingest_view(run) for run in trailing
        ]
        result["world_revision"] = int(self.store.current_world_revision())
        return result
