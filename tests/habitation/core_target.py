"""Adapter that runs a P16 resident model through the real AIOS Core.

This module contains benchmark plumbing only. It never interprets life meaning and
never supplies expected cognition. Conversation events use FusedTurnRuntime; other
reality events use P13 ingestion; virtual time runs P12 due tasks, C09 Wake dispatch,
and P15 periodic review in chronological order.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from datetime import datetime, timedelta
import hashlib
from pathlib import Path
from typing import Any, Callable, Mapping

from aios_core.contracts.enums import ObjectType, SourceClass, TaskState, WakeState
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import as_utc
from aios_core.ingest import (
    MechanicalSeriesPolicy,
    MediaDescriptorRecord,
    NumericSample,
    RealityIngestService,
    RealityRecord,
    SourceAdapterSpec,
)
from aios_core.query.search import WorldSearchIndex
from aios_core.review import ReviewSchedulePolicy
from aios_core.runtime.cognitive_runtime import ModelHandler
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.wake import (
    ObservationTriggerService,
    ObservationWakeRule,
    Step0GateInput,
)

from .harness import ResidentEvent, ResidentScenarioDescriptor


RoundSummaryHandler = Callable[[Any], str]
ModelHandlerFactory = Callable[[str], ModelHandler]
RoundSummaryHandlerFactory = Callable[[str], RoundSummaryHandler | None]
WakeStep0Provider = Callable[[Any, datetime], Step0GateInput | None]


def _safe_channel(value: str) -> str:
    normalized = "".join(
        char.lower() if char.isalnum() else "_"
        for char in value.strip()
    ).strip("_")
    if not normalized:
        raise ValueError("channel must contain at least one alphanumeric character")
    return normalized


def _runtime_view(result: Any) -> dict[str, Any]:
    if result is None:
        return {"invoked": False}
    return {
        "invoked": True,
        "response": result.response,
        "silenced": result.silenced,
        "model_rounds": result.model_rounds,
        "termination_reason": result.termination_reason,
        "capability_names": [item.name for item in result.capability_history],
    }


class CoreHabitationTarget:
    """One private SQLite AIOS world inhabited by exactly one resident model."""

    def __init__(
        self,
        *,
        db_path: str | Path,
        subject_id: str,
        model_id: str,
        model_handler: ModelHandler,
        round_summary_handler: RoundSummaryHandler | None = None,
        review_policy: ReviewSchedulePolicy | None = None,
        observation_wake_rules: tuple[ObservationWakeRule, ...] = (),
        wake_step0_provider: WakeStep0Provider | None = None,
        token_budget: int | None = None,
        require_fresh: bool = True,
        max_background_cycles: int = 10_000,
    ) -> None:
        path = Path(db_path)
        if require_fresh and path.exists():
            raise ValueError("P16 Core target requires a fresh private world database")
        if not isinstance(subject_id, str) or not subject_id.strip():
            raise ValueError("subject_id must not be blank")
        if not isinstance(model_id, str) or not model_id.strip():
            raise ValueError("model_id must not be blank")
        if max_background_cycles < 1:
            raise ValueError("max_background_cycles must be >= 1")

        path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = path
        self.subject_id = subject_id.strip()
        self.model_id = model_id.strip()
        self.review_policy = review_policy or ReviewSchedulePolicy()
        self.observation_wake_rules = tuple(observation_wake_rules)
        self.wake_step0_provider = wake_step0_provider
        self.token_budget = token_budget
        self.max_background_cycles = int(max_background_cycles)

        self.store = SQLiteWorldStore(path)
        self.index = WorldSearchIndex(path, store=self.store)
        self.index.rebuild()
        self.runtime = FusedTurnRuntime(
            store=self.store,
            index=self.index,
            model_handler=model_handler,
            subject_id=self.subject_id,
            round_summary_handler=round_summary_handler,
        )
        self.reality = RealityIngestService(
            store=self.store,
            index=self.index,
            subject_id=self.subject_id,
        )
        self.observation_triggers = ObservationTriggerService(
            store=self.store,
            wake_bus=self.runtime.wake_bus,
            subject_id=self.subject_id,
        )

        self._clock: datetime | None = None
        self._next_review_at: datetime | None = None
        self._session_turns: dict[str, int] = {}
        self._background_log: list[dict[str, Any]] = []
        self._event_log: list[dict[str, Any]] = []

    @property
    def isolation_key(self) -> str:
        return f"sqlite:{self.db_path.resolve()}"

    @property
    def clock(self) -> datetime | None:
        return self._clock

    def _review_interval(self) -> timedelta:
        return timedelta(hours=float(self.review_policy.interval_hours))

    def _next_due_task_at(self, limit: datetime) -> datetime | None:
        candidates: list[datetime] = []
        for task in self.runtime.execution_world.current_tasks():
            if task.task_state is not TaskState.WAITING_TIME:
                continue
            if task.next_wake_at is None:
                continue
            due = as_utc(task.next_wake_at, "next_wake_at")
            if due <= limit:
                if self._clock is not None and due < self._clock:
                    due = self._clock
                candidates.append(due)
        return min(candidates) if candidates else None

    def _step0_for_wake(self, wake: Any, at: datetime) -> Step0GateInput | None:
        if self.wake_step0_provider is None:
            return None
        result = self.wake_step0_provider(wake, at)
        if result is not None and not isinstance(result, Step0GateInput):
            raise TypeError("wake_step0_provider must return Step0GateInput or None")
        return result

    def _dispatch_wake(self, wake_id: str, *, at: datetime) -> dict[str, Any]:
        wake = self.runtime.wake_bus.current_wake(wake_id)
        if wake.wake_state not in {WakeState.NEW, WakeState.QUEUED}:
            return {
                "wake_id": wake.object_id,
                "wake_source": wake.wake_source.value,
                "state": wake.wake_state.value,
                "dispatched": False,
            }

        result = self.runtime.run_wake(
            wake_ref=ObjectRef(
                object_id=wake.object_id,
                revision=wake.revision,
            ),
            now=at,
            step0=self._step0_for_wake(wake, at),
            token_budget=self.token_budget,
        )
        return {
            "wake_id": result.wake.wake_id,
            "wake_source": wake.wake_source.value,
            "state": result.wake.state,
            "step0": result.step0.model_dump(mode="json"),
            "delivery_response": result.delivery_response,
            "delivery_suppressed": result.delivery_suppressed,
            "runtime": _runtime_view(result.runtime),
            "dispatched": result.runtime is not None,
        }

    def _process_due_tasks(self, at: datetime) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        while True:
            receipts = self.runtime.execution_world.wake_due_tasks(now=at)
            if not receipts:
                break
            for receipt in receipts:
                records.append(
                    {
                        "task_wake": asdict(receipt),
                        "dispatch": self._dispatch_wake(
                            receipt.wake_id,
                            at=at,
                        ),
                    }
                )
            if len(records) > self.max_background_cycles:
                raise RuntimeError("background Task/Wake loop exceeded safety guard")
        return records

    def _run_review(self, at: datetime) -> dict[str, Any]:
        result = self.runtime.run_periodic_review(
            now=at,
            policy=self.review_policy,
            token_budget=self.token_budget,
        )
        if result is None:
            return {
                "at": at.isoformat(),
                "invoked": False,
                "reason": "not_due_or_suppressed_without_model_call",
            }
        return {
            "at": at.isoformat(),
            "invoked": True,
            "wake_id": result.wake.wake_id,
            "wake_state": result.wake.state,
            "runtime": _runtime_view(result.runtime),
            "anchor_count": len(result.request.anchors),
            "window_start": result.request.window_start.isoformat(),
            "window_end": result.request.window_end.isoformat(),
        }

    def advance_to(self, instant: datetime) -> Mapping[str, Any]:
        target = as_utc(instant, "instant")
        start = self._clock

        if self._clock is None:
            self._clock = target
            self._next_review_at = target + self._review_interval()
            result = {
                "from": None,
                "to": target.isoformat(),
                "task_wakes": [],
                "periodic_reviews": [],
                "background_cycles": 0,
            }
            self._background_log.append(dict(result))
            return result

        if target < self._clock:
            raise ValueError("virtual clock cannot move backwards")

        task_records: list[dict[str, Any]] = []
        review_records: list[dict[str, Any]] = []
        cycles = 0

        while True:
            task_at = self._next_due_task_at(target)
            review_at = (
                self._next_review_at
                if self._next_review_at is not None
                and self._next_review_at <= target
                else None
            )
            candidates = [value for value in (task_at, review_at) if value is not None]
            if not candidates:
                break

            tick = min(candidates)
            if tick < self._clock:
                tick = self._clock
            self._clock = tick
            cycles += 1
            if cycles > self.max_background_cycles:
                raise RuntimeError("virtual scheduler exceeded safety guard")

            if task_at is not None and task_at <= tick:
                task_records.extend(self._process_due_tasks(tick))

            if review_at is not None and review_at <= tick:
                review_records.append(self._run_review(tick))
                self._next_review_at = review_at + self._review_interval()

            # A review or Wake may create a Task already due at this same tick.
            task_records.extend(self._process_due_tasks(tick))

        self._clock = target
        result = {
            "from": None if start is None else start.isoformat(),
            "to": target.isoformat(),
            "task_wakes": task_records,
            "periodic_reviews": review_records,
            "background_cycles": cycles,
        }
        self._background_log.append(dict(result))
        return result

    def _require_event_at_clock(self, event: ResidentEvent) -> datetime:
        at = as_utc(event.occurred_at, "occurred_at")
        if self._clock is None or at != self._clock:
            raise ValueError(
                "CoreHabitationTarget requires advance_to(event.occurred_at) "
                "before handle_event"
            )
        return at

    @staticmethod
    def _conversation_text(event: ResidentEvent) -> str:
        if isinstance(event.payload, str) and event.payload.strip():
            return event.payload
        if isinstance(event.payload, Mapping):
            text = event.payload.get("text")
            if isinstance(text, str) and text.strip():
                return text
        raise ValueError("conversation payload must contain non-blank text")

    def _conversation_event(self, event: ResidentEvent, at: datetime) -> dict[str, Any]:
        user_text = self._conversation_text(event)
        session_raw = event.metadata.get("session", "habitation-default")
        if not isinstance(session_raw, str) or not session_raw.strip():
            raise ValueError("conversation metadata.session must be a non-blank string")
        session_id = session_raw.strip()
        turn_index = self._session_turns.get(session_id, 0) + 1

        result = self.runtime.run_turn(
            session_id=session_id,
            turn_index=turn_index,
            user_input=user_text,
            current_topic=user_text,
            occurred_at=at,
            token_budget=self.token_budget,
        )
        self._session_turns[session_id] = turn_index
        return {
            "kind": "conversation",
            "session_id": session_id,
            "turn_index": turn_index,
            "runtime": _runtime_view(result.runtime),
            "user_observation_id": result.conversation_commit.user_observation_id,
            "assistant_observation_id": (
                result.conversation_commit.assistant_observation_id
            ),
            "world_revision": result.conversation_commit.world_revision,
            "continuity_summary_ids": [
                item.summary_id for item in result.continuity_summary_commits
            ],
            "continuity_summary_error": result.continuity_summary_error,
        }

    def _source_class_for_channel(self, channel: str) -> SourceClass:
        return (
            SourceClass.SENSOR
            if channel.startswith("sensor")
            else SourceClass.USER
        )

    def _generic_reality_event(
        self,
        event: ResidentEvent,
        at: datetime,
    ) -> tuple[dict[str, Any], tuple[ObjectRef, ...]]:
        channel = _safe_channel(event.channel)
        modality = "text" if isinstance(event.payload, str) else "structured_record"
        spec = SourceAdapterSpec(
            adapter_id=f"habitation.{channel}.v1",
            source_kind=channel,
            dimension=f"dim:{channel}",
            source_class=self._source_class_for_channel(channel),
            default_modality=modality,
        )
        receipt = self.reality.ingest_record(
            spec,
            RealityRecord(
                external_record_id=event.event_id,
                occurred_at=at,
                value=event.payload,
                modality=modality,
                source_locator=f"habitation://{event.event_id}",
                received_at=at,
                provenance={
                    "habitation_event_id": event.event_id,
                    "channel": event.channel,
                    "resident_metadata": dict(event.metadata),
                },
            ),
        )
        ref = ObjectRef(object_id=receipt.observation_id, revision=1)
        return (
            {
                "kind": "reality",
                "observation_ids": [receipt.observation_id],
                "world_revision": receipt.world_revision,
                "reused_existing": receipt.reused_existing,
            },
            (ref,),
        )

    def _media_descriptor_event(
        self,
        event: ResidentEvent,
        at: datetime,
    ) -> tuple[dict[str, Any], tuple[ObjectRef, ...]]:
        if not isinstance(event.payload, str) or not event.payload.strip():
            raise ValueError("photo_description payload must be non-blank text")
        channel = _safe_channel(event.channel)
        spec = SourceAdapterSpec(
            adapter_id=f"habitation.{channel}.v1",
            source_kind=channel,
            dimension=f"dim:{channel}",
            source_class=SourceClass.USER,
            default_modality="image_caption",
        )
        receipt = self.reality.ingest_media_descriptor(
            spec,
            MediaDescriptorRecord(
                external_record_id=event.event_id,
                occurred_at=at,
                descriptor=event.payload,
                descriptor_kind="image_caption",
                source_locator=f"habitation://{event.event_id}",
                received_at=at,
                provenance={
                    "habitation_event_id": event.event_id,
                    "channel": event.channel,
                    "resident_metadata": dict(event.metadata),
                },
            ),
        )
        ref = ObjectRef(object_id=receipt.observation_id, revision=1)
        return (
            {
                "kind": "media_descriptor",
                "observation_ids": [receipt.observation_id],
                "world_revision": receipt.world_revision,
                "reused_existing": receipt.reused_existing,
            },
            (ref,),
        )

    @staticmethod
    def _parse_sample_time(value: Any) -> datetime:
        if isinstance(value, datetime):
            return as_utc(value, "sample.occurred_at")
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return as_utc(parsed, "sample.occurred_at")
        raise ValueError("numeric sample occurred_at must be datetime or ISO-8601 string")

    def _numeric_series_event(
        self,
        event: ResidentEvent,
        at: datetime,
    ) -> tuple[dict[str, Any], tuple[ObjectRef, ...]]:
        if not isinstance(event.payload, Mapping):
            raise ValueError("sensor_numeric payload must be an object")
        payload = event.payload
        source_kind = payload.get("source_kind")
        dimension = payload.get("dimension")
        series_id = payload.get("series_id")
        samples_raw = payload.get("samples")
        policy_raw = payload.get("policy")
        if not isinstance(source_kind, str) or not source_kind.strip():
            raise ValueError("sensor_numeric source_kind must be non-blank")
        if not isinstance(dimension, str) or not dimension.startswith("dim:"):
            raise ValueError("sensor_numeric dimension must start with dim:")
        if not isinstance(series_id, str) or not series_id.strip():
            raise ValueError("sensor_numeric series_id must be non-blank")
        if not isinstance(samples_raw, (list, tuple)) or not samples_raw:
            raise ValueError("sensor_numeric samples must be a non-empty array")
        if not isinstance(policy_raw, Mapping):
            raise ValueError("sensor_numeric policy must be an object")

        samples: list[NumericSample] = []
        for index, raw in enumerate(samples_raw):
            if not isinstance(raw, Mapping):
                raise ValueError("numeric samples must contain objects")
            record_id = raw.get("external_record_id", f"{event.event_id}:{index}")
            if not isinstance(record_id, str) or not record_id.strip():
                raise ValueError("numeric sample external_record_id must be non-blank")
            samples.append(
                NumericSample(
                    external_record_id=record_id,
                    occurred_at=self._parse_sample_time(
                        raw.get("occurred_at", at)
                    ),
                    value=raw.get("value"),
                    source_locator=raw.get("source_locator"),
                )
            )

        spec = SourceAdapterSpec(
            adapter_id=f"habitation.{_safe_channel(source_kind)}.numeric.v1",
            source_kind=source_kind.strip(),
            dimension=dimension,
            source_class=SourceClass.SENSOR,
            default_modality="numeric",
        )
        receipt = self.reality.ingest_numeric_series(
            spec,
            series_id=series_id.strip(),
            samples=tuple(samples),
            policy=MechanicalSeriesPolicy.model_validate(dict(policy_raw)),
            unit=payload.get("unit"),
            received_at=at,
        )
        ids = (
            *receipt.segment_observation_ids,
            *receipt.change_observation_ids,
        )
        refs = tuple(ObjectRef(object_id=object_id, revision=1) for object_id in ids)
        return (
            {
                "kind": "numeric_series",
                "observation_ids": list(ids),
                "segment_observation_ids": list(receipt.segment_observation_ids),
                "change_observation_ids": list(receipt.change_observation_ids),
                "world_revision": receipt.world_revision,
                "reused_existing_count": receipt.reused_existing_count,
            },
            refs,
        )

    def _trigger_and_dispatch(
        self,
        refs: tuple[ObjectRef, ...],
        *,
        at: datetime,
    ) -> list[dict[str, Any]]:
        if not self.observation_wake_rules:
            return []

        wake_ids: set[str] = set()
        signal_records: list[dict[str, Any]] = []
        for ref in refs:
            receipts = self.observation_triggers.evaluate_observation(
                ref,
                rules=self.observation_wake_rules,
            )
            for receipt in receipts:
                signal_records.append(asdict(receipt))
                if not receipt.suppressed:
                    wake_ids.add(receipt.wake_id)

        dispatches = [
            self._dispatch_wake(wake_id, at=at)
            for wake_id in sorted(wake_ids)
        ]
        return [
            {
                "signals": signal_records,
                "dispatches": dispatches,
            }
        ] if signal_records else []

    def handle_event(self, event: ResidentEvent) -> Mapping[str, Any]:
        at = self._require_event_at_clock(event)

        if event.channel == "conversation":
            result = self._conversation_event(event, at)
        elif event.channel == "photo_description":
            result, refs = self._media_descriptor_event(event, at)
            result["wake_activity"] = self._trigger_and_dispatch(refs, at=at)
        elif event.channel == "sensor_numeric":
            result, refs = self._numeric_series_event(event, at)
            result["wake_activity"] = self._trigger_and_dispatch(refs, at=at)
        else:
            result, refs = self._generic_reality_event(event, at)
            result["wake_activity"] = self._trigger_and_dispatch(refs, at=at)

        event_record = {
            "event_id": event.event_id,
            "occurred_at": at.isoformat(),
            "channel": event.channel,
            "result": result,
        }
        self._event_log.append(event_record)
        return result

    def audit_snapshot(self) -> Mapping[str, Any]:
        objects = self.store.list_payloads(subject_id=self.subject_id)
        counts = Counter(str(item.get("object_type")) for item in objects)
        return {
            "subject_id": self.subject_id,
            "model_id": self.model_id,
            "clock": None if self._clock is None else self._clock.isoformat(),
            "world_revision": int(self.store.current_world_revision()),
            "index_watermark": int(self.index.watermark()),
            "object_counts": dict(sorted(counts.items())),
            "world_objects": objects,
            "session_turns": dict(sorted(self._session_turns.items())),
            "event_log": list(self._event_log),
            "background_log": list(self._background_log),
        }


class CoreHabitationTargetFactory:
    """Create a fresh private Core world for each model candidate."""

    def __init__(
        self,
        *,
        root_dir: str | Path,
        model_handler_factory: ModelHandlerFactory,
        round_summary_handler_factory: RoundSummaryHandlerFactory | None = None,
        review_policy: ReviewSchedulePolicy | None = None,
        observation_wake_rules: tuple[ObservationWakeRule, ...] = (),
        wake_step0_provider: WakeStep0Provider | None = None,
        token_budget: int | None = None,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.model_handler_factory = model_handler_factory
        self.round_summary_handler_factory = round_summary_handler_factory
        self.review_policy = review_policy
        self.observation_wake_rules = tuple(observation_wake_rules)
        self.wake_step0_provider = wake_step0_provider
        self.token_budget = token_budget
        self._counter = 0

    def __call__(
        self,
        *,
        model_id: str,
        scenario: ResidentScenarioDescriptor,
    ) -> CoreHabitationTarget:
        self._counter += 1
        opaque = hashlib.sha256(
            f"{self._counter}|{model_id}|{scenario.subject_id}".encode("utf-8")
        ).hexdigest()[:16]
        db_path = self.root_dir / f"world-{self._counter:04d}-{opaque}.db"
        summary_handler = (
            None
            if self.round_summary_handler_factory is None
            else self.round_summary_handler_factory(model_id)
        )
        return CoreHabitationTarget(
            db_path=db_path,
            subject_id=scenario.subject_id,
            model_id=model_id,
            model_handler=self.model_handler_factory(model_id),
            round_summary_handler=summary_handler,
            review_policy=self.review_policy,
            observation_wake_rules=self.observation_wake_rules,
            wake_step0_provider=self.wake_step0_provider,
            token_budget=self.token_budget,
        )
