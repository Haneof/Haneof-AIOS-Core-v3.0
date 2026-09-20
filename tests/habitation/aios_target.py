"""Adapter that lets P16 residents inhabit the real current AIOS Core.

This file contains benchmark plumbing, not benchmark cognition. It maps sealed
resident-visible life events onto the stabilized public Core surfaces:

- conversation -> P14/FusedTurnRuntime
- non-conversation reality -> P13 RealityIngestService
- virtual clock -> P12 due-task scheduler + generic durable Wake dispatch
- daily background review -> P15 PeriodicReview

No hidden oracle, scenario label, evaluator criterion, or future event is available
to this target.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
from pathlib import Path
from typing import Any, Callable, Mapping

from aios_core.contracts.enums import SourceClass, TaskState
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import as_utc
from aios_core.ingest.reality import (
    RealityIngestService,
    RealityRecord,
    SourceAdapterSpec,
)
from aios_core.query.search import WorldSearchIndex
from aios_core.review import ReviewSchedulePolicy
from aios_core.runtime.cognitive_runtime import ModelHandler
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.wake import WakeStep0Decision, WakeStep0Outcome

from .harness import ResidentEvent, ResidentScenarioDescriptor


_SENSOR_CHANNELS = frozenset(
    {
        "sensor",
        "heart_rate",
        "imu",
        "temperature",
        "gps",
        "vehicle_sensor",
        "home_sensor",
    }
)


def _channel_slug(channel: str) -> str:
    normalized = "".join(
        char.lower() if char.isalnum() else "_"
        for char in str(channel)
    ).strip("_")
    if normalized:
        return normalized[:48]
    return hashlib.sha256(str(channel).encode("utf-8")).hexdigest()[:16]


class AIOSHabitationTarget:
    """One model's private AIOS world for a sealed habitation run."""

    def __init__(
        self,
        *,
        db_path: str | Path,
        model_id: str,
        subject_id: str,
        model_handler: ModelHandler,
        round_summary_handler: Callable[[Any], str] | None = None,
        review_policy: ReviewSchedulePolicy | None = None,
    ) -> None:
        if not str(model_id).strip():
            raise ValueError("model_id must not be blank")
        if not str(subject_id).strip():
            raise ValueError("subject_id must not be blank")
        self.model_id = str(model_id).strip()
        self.subject_id = str(subject_id).strip()
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.store = SQLiteWorldStore(self.db_path)
        self.index = WorldSearchIndex(self.db_path, store=self.store)
        self.index.rebuild()
        self.ingest = RealityIngestService(
            store=self.store,
            index=self.index,
            subject_id=self.subject_id,
        )
        self.runtime = FusedTurnRuntime(
            store=self.store,
            index=self.index,
            model_handler=model_handler,
            subject_id=self.subject_id,
            round_summary_handler=round_summary_handler,
        )
        self.review_policy = review_policy or ReviewSchedulePolicy()
        self._clock: datetime | None = None
        self._turn_index_by_session: dict[str, int] = {}

    @property
    def isolation_key(self) -> str:
        return str(self.db_path.resolve())

    @staticmethod
    def _step0_gate(_wake, _now: datetime) -> WakeStep0Decision:
        # The virtual environment has no physical playback channel. Explicitly
        # recording this synthetic gate prevents Core from implicitly assuming a
        # real-world notification is legal.
        return WakeStep0Decision(
            outcome=WakeStep0Outcome.QUIET,
            audit={
                "environment": "p16_virtual_habitation",
                "safety": "no_physical_safety_signal",
                "convenience": "background_only",
                "channel": "no_physical_delivery_channel",
                "budget": "benchmark_runtime",
            },
        )

    def _adapter_for(self, channel: str) -> SourceAdapterSpec:
        slug = _channel_slug(channel)
        source_class = (
            SourceClass.SENSOR
            if channel.strip().lower() in _SENSOR_CHANNELS
            else SourceClass.USER
        )
        return SourceAdapterSpec(
            adapter_id=f"p16.{slug}",
            source_kind=channel.strip(),
            dimension=f"dim:p16_source_{slug}",
            source_class=source_class,
            schema_version="1",
            default_modality="text" if channel != "order" else "structured",
        )

    def _dispatch_due_tasks(self, now: datetime) -> list[dict[str, Any]]:
        receipts = self.runtime.execution_world.wake_due_tasks(now=now)
        dispatched: list[dict[str, Any]] = []
        for receipt in receipts:
            result = self.runtime.run_wake(
                wake_ref=ObjectRef(object_id=receipt.wake_id, revision=1),
                now=now,
                step0_gate=self._step0_gate,
            )
            dispatched.append(
                {
                    "wake_id": result.wake.wake_id,
                    "wake_state": result.wake.state,
                    "wake_source": result.request.wake_source.value,
                    "termination_reason": result.runtime.termination_reason,
                    "delivery_allowed": result.delivery_allowed,
                }
            )
        return dispatched

    def _process_tick(
        self,
        now: datetime,
        *,
        allow_review: bool = True,
    ) -> dict[str, Any]:
        now = as_utc(now, "virtual_clock")
        before = self._dispatch_due_tasks(now)
        review = (
            self.runtime.run_periodic_review(
                now=now,
                policy=self.review_policy,
            )
            if allow_review
            else None
        )
        # A review may itself create an immediately-due Task. Give that Task the
        # same clock tick rather than delaying it until the next visible life event.
        after = self._dispatch_due_tasks(now)
        return {
            "at": now.isoformat(),
            "task_wakes": [*before, *after],
            "periodic_review": (
                None
                if review is None
                else {
                    "review_id": review.request.review_id,
                    "wake_state": review.wake.state,
                    "termination_reason": review.runtime.termination_reason,
                }
            ),
        }

    def _next_task_due(
        self,
        *,
        after: datetime,
        through: datetime,
    ) -> datetime | None:
        candidates: list[datetime] = []
        for task in self.runtime.execution_world.current_tasks():
            if task.task_state is not TaskState.WAITING_TIME:
                continue
            if task.next_wake_at is None:
                continue
            due = as_utc(task.next_wake_at, "next_wake_at")
            if after < due <= through:
                candidates.append(due)
        return min(candidates) if candidates else None

    def advance_to(self, instant: datetime) -> Mapping[str, Any]:
        """Advance virtual time, including background days with no visible events."""

        target = as_utc(instant, "instant")
        if self._clock is not None and target < self._clock:
            raise ValueError("habitation virtual clock cannot move backwards")

        ticks: list[dict[str, Any]] = []
        if self._clock is None:
            # Before the very first resident-visible fact there is nothing to
            # review. Writing an empty P15 marker here would place the first event
            # exactly on the next review window's exclusive lower boundary.
            self._clock = target
            return {"from": None, "to": target.isoformat(), "ticks": ticks}

        start = self._clock
        cursor = start

        # Catch same-instant work created by the previous visible event.
        if target > cursor:
            # Catch Tasks created at the previous event timestamp, but do not run a
            # zero-age Review. The first review tick is one full interval later.
            ticks.append(self._process_tick(cursor, allow_review=False))

        review_interval = timedelta(hours=float(self.review_policy.interval_hours))
        next_review = cursor + review_interval

        while cursor < target:
            task_due = self._next_task_due(after=cursor, through=target)
            candidates = [target]
            if next_review <= target:
                candidates.append(next_review)
            if task_due is not None:
                candidates.append(task_due)
            tick_at = min(candidates)

            # Multiple mechanisms may nominate the same timestamp; one tick handles
            # all deterministic due work at that instant.
            ticks.append(self._process_tick(tick_at))
            cursor = tick_at
            if cursor >= next_review:
                next_review = cursor + review_interval

        self._clock = target
        return {
            "from": start.isoformat(),
            "to": target.isoformat(),
            "ticks": ticks,
        }

    def _next_turn_index(self, session_id: str) -> int:
        current = self._turn_index_by_session.get(session_id, 0) + 1
        self._turn_index_by_session[session_id] = current
        return current

    def handle_event(self, event: ResidentEvent) -> Mapping[str, Any]:
        at = as_utc(event.occurred_at, "event.occurred_at")
        if self._clock is None or at != self._clock:
            raise ValueError("advance_to(event.occurred_at) must run before handle_event")

        channel = event.channel.strip().lower()
        if channel == "conversation":
            if not isinstance(event.payload, str) or not event.payload.strip():
                raise ValueError("conversation payload must be non-blank text")
            raw_session = event.metadata.get("session", "habitation")
            session_id = str(raw_session).strip() or "habitation"
            result = self.runtime.run_turn(
                session_id=session_id,
                turn_index=self._next_turn_index(session_id),
                user_input=event.payload,
                current_topic=None,
                occurred_at=at,
            )
            return {
                "kind": "conversation",
                "termination_reason": result.runtime.termination_reason,
                "response": result.runtime.response,
                "silenced": result.runtime.silenced,
                "capability_names": [
                    item.name for item in result.runtime.capability_history
                ],
                "world_revision": result.conversation_commit.world_revision,
            }

        spec = self._adapter_for(event.channel)
        receipt = self.ingest.ingest_record(
            spec,
            RealityRecord(
                external_record_id=event.event_id,
                occurred_at=at,
                received_at=at,
                value=event.payload,
                modality=(
                    "text"
                    if isinstance(event.payload, str)
                    else "structured"
                ),
                provenance={
                    "benchmark_transport": "p16_habitation",
                    "resident_visible": True,
                    "channel": event.channel,
                },
            ),
        )
        return {
            "kind": "reality_ingest",
            "observation_id": receipt.observation_id,
            "world_revision": receipt.world_revision,
            "reused_existing": receipt.reused_existing,
        }

    def audit_snapshot(self) -> Mapping[str, Any]:
        current = self.store.list_payloads(subject_id=self.subject_id)
        histories: dict[str, list[dict[str, Any]]] = {}
        for payload in current:
            latest_revision = int(payload.get("revision", 1))
            if latest_revision <= 1:
                continue
            histories[str(payload["object_id"])] = [
                self.store.get_payload(
                    str(payload["object_id"]),
                    revision=revision,
                )
                for revision in range(1, latest_revision + 1)
            ]
        return {
            "subject_id": self.subject_id,
            "world_revision": int(self.store.current_world_revision()),
            "current_objects": current,
            "revision_histories": histories,
        }


class AIOSHabitationTargetFactory:
    """Create one fresh private AIOS world from oracle-free descriptor data."""

    def __init__(
        self,
        *,
        root: str | Path,
        model_handler_factory: Callable[[str], ModelHandler],
        round_summary_handler_factory: Callable[[str], Callable[[Any], str] | None]
        | None = None,
        review_policy: ReviewSchedulePolicy | None = None,
    ) -> None:
        self.root = Path(root)
        self.model_handler_factory = model_handler_factory
        self.round_summary_handler_factory = round_summary_handler_factory
        self.review_policy = review_policy

    def __call__(
        self,
        *,
        model_id: str,
        scenario: ResidentScenarioDescriptor,
    ) -> AIOSHabitationTarget:
        digest = hashlib.sha256(model_id.encode("utf-8")).hexdigest()[:16]
        db_path = self.root / digest / "world.db"
        summary_handler = (
            None
            if self.round_summary_handler_factory is None
            else self.round_summary_handler_factory(model_id)
        )
        return AIOSHabitationTarget(
            db_path=db_path,
            model_id=model_id,
            subject_id=scenario.subject_id,
            model_handler=self.model_handler_factory(model_id),
            round_summary_handler=summary_handler,
            review_policy=self.review_policy,
        )
