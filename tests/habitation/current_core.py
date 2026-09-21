"""Adapter that lets the P16 harness inhabit the real current AIOS Core.

This module is test infrastructure, not an alternate runtime. It creates one private
WorldStore/Index/FusedTurnRuntime per model candidate and feeds only resident-visible
events through public Core surfaces.

The harness never manufactures cognition. A supplied real model handler remains the
only component that may interpret life events, form/revise Claims, create dimensions,
or act through AIOS capabilities.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from datetime import datetime, timedelta
import hashlib
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from aios_core.contracts.enums import (
    ObjectType,
    SourceClass,
    TaskState,
    WakeSource,
    WakeState,
)
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

from .harness import (
    HabitationTarget,
    ResidentEvent,
    ResidentScenarioDescriptor,
)


RoundSummaryHandler = Callable[[Any], str]
ModelHandlerFactory = Callable[[str], ModelHandler]
RoundSummaryHandlerFactory = Callable[[str], RoundSummaryHandler | None]
WakeStep0Provider = Callable[[Any, datetime], Step0GateInput | None]


def _clean_channel(channel: str) -> str:
    value = "".join(
        char.lower() if char.isalnum() else "_"
        for char in channel.strip()
    ).strip("_")
    if not value:
        raise ValueError("channel must contain at least one alphanumeric character")
    return value


def default_source_spec(channel: str) -> SourceAdapterSpec:
    """Build a mechanical source adapter from the resident-visible channel name.

    This maps transport/source identity only. It does not classify semantic meaning.
    """

    clean = _clean_channel(channel)
    source_class = (
        SourceClass.SENSOR if clean.startswith("sensor") else SourceClass.USER
    )
    return SourceAdapterSpec(
        adapter_id=f"habitation.{clean}.v1",
        source_kind=clean,
        dimension=f"dim:{clean}",
        source_class=source_class,
        default_modality=(
            "numeric" if source_class is SourceClass.SENSOR else "structured_record"
        ),
    )


def _runtime_view(result: Any) -> dict[str, Any]:
    if result is None:
        return {"invoked": False}
    return {
        "invoked": True,
        "response": result.response,
        "silenced": result.silenced,
        "model_rounds": result.model_rounds,
        "termination_reason": result.termination_reason,
        "capabilities": [item.name for item in result.capability_history],
    }


class CurrentCoreHabitationTarget(HabitationTarget):
    """One private current-Core world inhabited by one resident model."""

    def __init__(
        self,
        *,
        model_id: str,
        subject_id: str,
        db_path: str | Path,
        model_handler: ModelHandler,
        round_summary_handler: RoundSummaryHandler | None = None,
        dimension_summary_handler: RoundSummaryHandler | None = None,
        source_specs: Mapping[str, SourceAdapterSpec] | None = None,
        observation_wake_rules: Sequence[ObservationWakeRule] = (),
        review_policy: ReviewSchedulePolicy | None = None,
        wake_step0_provider: WakeStep0Provider | None = None,
        token_budget: int | None = None,
        require_fresh: bool = True,
        max_background_cycles: int = 10_000,
    ) -> None:
        if not isinstance(model_id, str) or not model_id.strip():
            raise ValueError("model_id must not be blank")
        if not isinstance(subject_id, str) or not subject_id.strip():
            raise ValueError("subject_id must not be blank")
        if max_background_cycles < 1:
            raise ValueError("max_background_cycles must be >= 1")

        self.model_id = model_id.strip()
        self.subject_id = subject_id.strip()
        bound_model_id = getattr(model_handler, "model_id", None)
        if bound_model_id is not None:
            if not isinstance(bound_model_id, str) or not bound_model_id.strip():
                raise ValueError("model_handler model_id must be non-blank when exposed")
            if bound_model_id.strip() != self.model_id:
                raise ValueError(
                    "model_handler model_id does not match target model_id"
                )
        if round_summary_handler is not None:
            summary_model_id = getattr(round_summary_handler, "model_id", None)
            if summary_model_id is not None and (
                not isinstance(summary_model_id, str)
                or not summary_model_id.strip()
                or summary_model_id.strip() != self.model_id
            ):
                raise ValueError(
                    "round_summary_handler model_id does not match target model_id"
                )
        effective_dimension_summary_handler = (
            dimension_summary_handler
            if dimension_summary_handler is not None
            else round_summary_handler
        )
        if effective_dimension_summary_handler is not None:
            dimension_model_id = getattr(
                effective_dimension_summary_handler,
                "model_id",
                None,
            )
            if dimension_model_id is not None and (
                not isinstance(dimension_model_id, str)
                or not dimension_model_id.strip()
                or dimension_model_id.strip() != self.model_id
            ):
                raise ValueError(
                    "dimension_summary_handler model_id does not match target model_id"
                )
        self._model_handler = model_handler
        self._round_summary_handler = round_summary_handler
        self._dimension_summary_handler = effective_dimension_summary_handler
        self.db_path = Path(db_path).expanduser().resolve()
        existing_world = self.db_path.exists()
        if require_fresh and existing_world:
            raise ValueError("P16 target requires a fresh private world database")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._isolation_key = f"sqlite:{self.db_path}"
        self._resumed_from_world = bool(existing_world and not require_fresh)
        self._clock: datetime | None = None
        self._next_review_at: datetime | None = None
        self._session_turns: dict[str, int] = {}
        self._source_specs = {
            _clean_channel(key): value
            for key, value in dict(source_specs or {}).items()
        }
        self._observation_wake_rules = tuple(observation_wake_rules)
        self._review_policy = review_policy or ReviewSchedulePolicy()
        self._wake_step0_provider = wake_step0_provider
        self._token_budget = token_budget
        self._max_background_cycles = int(max_background_cycles)
        self._background_log: list[dict[str, Any]] = []
        self._event_log: list[dict[str, Any]] = []

        self.store = SQLiteWorldStore(self.db_path)
        self.index = WorldSearchIndex(self.db_path, store=self.store)
        self.index.rebuild()
        self.reality = RealityIngestService(
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
            dimension_summary_handler=effective_dimension_summary_handler,
            max_tool_rounds=8,
        )
        self.observation_triggers = ObservationTriggerService(
            store=self.store,
            wake_bus=self.runtime.wake_bus,
            subject_id=self.subject_id,
        )
        if self._resumed_from_world:
            self._restore_runtime_state_from_world()

    @property
    def isolation_key(self) -> str:
        return self._isolation_key

    @property
    def clock(self) -> datetime | None:
        return self._clock

    @staticmethod
    def _payload_time(payload: Mapping[str, Any], field_name: str) -> datetime | None:
        raw = payload.get(field_name)
        if not isinstance(raw, str) or not raw.strip():
            return None
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return as_utc(parsed, field_name)
        except (TypeError, ValueError):
            return None

    def _restore_runtime_state_from_world(self) -> None:
        """Reconstruct scheduler/session cursors from the durable World only.

        This deliberately does not restore model-private memory. A replacement model
        must continue from world facts, summaries, cognition, tasks and Wakes.
        """

        payloads = self.store.list_payloads(subject_id=self.subject_id)
        if not payloads:
            return

        recorded_times: list[datetime] = []
        session_turns: dict[str, int] = {}
        review_markers: list[tuple[datetime, str, int, Mapping[str, Any]]] = []

        for payload in payloads:
            recorded = self._payload_time(payload, "recorded_at")
            if recorded is not None:
                recorded_times.append(recorded)

            if (
                payload.get("object_type") == ObjectType.OBSERVATION.value
                and payload.get("source_kind") == "user_ai_interaction"
            ):
                metadata = payload.get("metadata")
                if isinstance(metadata, Mapping) and metadata.get("role") == "user":
                    session_id = metadata.get("session_id")
                    turn_index = metadata.get("turn_index")
                    if (
                        isinstance(session_id, str)
                        and session_id.strip()
                        and isinstance(turn_index, int)
                        and not isinstance(turn_index, bool)
                        and turn_index > 0
                    ):
                        session = session_id.strip()
                        session_turns[session] = max(
                            session_turns.get(session, 0),
                            turn_index,
                        )

            if (
                payload.get("object_type") == ObjectType.WAKE.value
                and payload.get("wake_source") == WakeSource.PERIODIC_REVIEW.value
            ):
                last_hit = self._payload_time(payload, "last_hit_at")
                if last_hit is None:
                    continue
                review_markers.append(
                    (
                        last_hit,
                        str(payload.get("object_id") or ""),
                        int(payload.get("revision") or 0),
                        payload,
                    )
                )

        self._session_turns = session_turns
        if recorded_times:
            # This is a conservative replay cursor. It never jumps beyond durable
            # evidence; work between this point and the next requested instant is
            # replayed through idempotent Core scheduling.
            self._clock = max(recorded_times)

        if self._clock is None:
            return

        if review_markers:
            review_markers.sort(key=lambda item: (item[0], item[1], item[2]))
            last_hit, _object_id, _revision, latest = review_markers[-1]
            wake_state = str(latest.get("wake_state") or "")
            if wake_state in {WakeState.NEW.value, WakeState.RUNNING.value}:
                self._next_review_at = self._clock
            else:
                self._next_review_at = last_hit + self._review_interval()
        else:
            self._next_review_at = min(recorded_times) + self._review_interval()

    def _spec_for(self, channel: str) -> SourceAdapterSpec:
        clean = _clean_channel(channel)
        return self._source_specs.get(clean) or default_source_spec(clean)

    def _review_interval(self) -> timedelta:
        return timedelta(hours=float(self._review_policy.interval_hours))

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

    def _step0_for_wake(self, wake: Any, now: datetime) -> Step0GateInput | None:
        if self._wake_step0_provider is None:
            return None
        result = self._wake_step0_provider(wake, now)
        if result is not None and not isinstance(result, Step0GateInput):
            raise TypeError("wake_step0_provider must return Step0GateInput or None")
        return result

    def _dispatch_pending_wakes(self, now: datetime) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        # Snapshot first: a model-run Wake may create another Wake, which belongs to
        # the next deterministic scheduling pass rather than an unbounded loop here.
        for wake in self.runtime.wake_bus.pending_wakes():
            if wake.wake_source in {
                WakeSource.PERIODIC_REVIEW,
                WakeSource.USER_INTERACTION,
            }:
                continue

            # A prior dispatch in this same snapshot may mechanically merge sibling
            # BACKGROUND Wakes into one AttentionBundle. Re-read the durable current
            # Wake before dispatch so the habitation adapter never tries to claim a
            # child that has already become MERGED.
            current = self.runtime.wake_bus.current_wake(wake.object_id)
            if current.wake_state.value not in {"new", "queued"}:
                continue

            result = self.runtime.run_wake(
                wake_ref=ObjectRef(
                    object_id=current.object_id,
                    revision=current.revision,
                ),
                now=now,
                step0=self._step0_for_wake(wake, now),
                token_budget=self._token_budget,
            )
            results.append(
                {
                    "wake_id": result.wake_ref.object_id,
                    "wake_revision": result.wake_ref.revision,
                    "wake_source": wake.wake_source.value,
                    "wake_state": result.wake.state,
                    "step0": result.step0.model_dump(mode="json"),
                    "delivery_response": result.delivery_response,
                    "delivery_suppressed": result.delivery_suppressed,
                    "runtime": _runtime_view(result.runtime),
                }
            )
        return results

    def _process_due_tasks(self, now: datetime) -> dict[str, Any]:
        task_wakes = self.runtime.execution_world.wake_due_tasks(now=now)
        wake_runs = self._dispatch_pending_wakes(now)
        return {
            "at": now.isoformat(),
            "task_wakes": [asdict(item) for item in task_wakes],
            "wake_runs": wake_runs,
        }

    def _run_periodic_review(self, now: datetime) -> dict[str, Any]:
        review = self.runtime.run_periodic_review(
            now=now,
            policy=self._review_policy,
            token_budget=self._token_budget,
        )
        if review is None:
            return {
                "at": now.isoformat(),
                "invoked": False,
                "reason": "not_due_or_suppressed_without_model_call",
            }
        return {
            "at": now.isoformat(),
            "invoked": True,
            "review_id": review.request.review_id,
            "wake_id": review.wake.wake_id,
            "wake_revision": review.wake.revision,
            "anchor_count": len(review.request.anchors),
            "window_start": review.request.window_start.isoformat(),
            "window_end": review.request.window_end.isoformat(),
            "runtime": _runtime_view(review.runtime),
        }

    def _run_dimension_summaries(self, now: datetime) -> dict[str, Any]:
        if self.runtime.dimension_summary_scheduler is None:
            return {
                "at": now.isoformat(),
                "invoked": False,
                "reason": "dimension_summary_handler_not_configured",
            }
        result = self.runtime.run_due_dimension_summaries(
            now=now,
            max_jobs=64,
        )
        return {
            "at": now.isoformat(),
            "invoked": True,
            "attempted_jobs": len(result.attempted_jobs),
            "commits": [asdict(item) for item in result.commits],
            "skipped_unchanged": len(result.skipped_unchanged),
            "skipped_empty": len(result.skipped_empty),
            "truncated": result.truncated,
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
                "task_cycles": [],
                "periodic_reviews": [],
                "background_cycles": 0,
                "world_revision": int(self.store.current_world_revision()),
            }
            self._background_log.append(dict(result))
            return result

        if target < self._clock:
            raise ValueError("virtual clock cannot move backwards")

        task_cycles: list[dict[str, Any]] = []
        review_runs: list[dict[str, Any]] = []
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
            if cycles > self._max_background_cycles:
                raise RuntimeError("virtual scheduler exceeded safety guard")

            if task_at is not None and task_at <= tick:
                task_cycle = self._process_due_tasks(tick)
                if task_cycle["task_wakes"] or task_cycle["wake_runs"]:
                    task_cycles.append(task_cycle)

            if review_at is not None and review_at <= tick:
                review_runs.append(self._run_periodic_review(tick))
                self._next_review_at = review_at + self._review_interval()

            # A periodic review or Wake may create a Task already due at this tick.
            follow_up = self._process_due_tasks(tick)
            if follow_up["task_wakes"] or follow_up["wake_runs"]:
                task_cycles.append(follow_up)

        dimension_summaries = self._run_dimension_summaries(target)
        self._clock = target
        result = {
            "from": None if start is None else start.isoformat(),
            "to": target.isoformat(),
            "task_cycles": task_cycles,
            "periodic_reviews": review_runs,
            "dimension_summaries": dimension_summaries,
            "background_cycles": cycles,
            "world_revision": int(self.store.current_world_revision()),
        }
        self._background_log.append(dict(result))
        return result

    def _conversation_session(self, event: ResidentEvent) -> str:
        raw = event.metadata.get("session")
        if raw is None:
            return "default"
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError("conversation metadata.session must be a non-blank string")
        return raw.strip()

    def _handle_conversation(self, event: ResidentEvent) -> Mapping[str, Any]:
        if not isinstance(event.payload, str) or not event.payload.strip():
            raise ValueError("conversation event payload must be non-blank text")
        session_id = self._conversation_session(event)
        turn_index = self._session_turns.get(session_id, 0) + 1
        result = self.runtime.run_turn(
            session_id=session_id,
            turn_index=turn_index,
            user_input=event.payload,
            # Topic state is derived inside Core from the resident-visible current
            # utterance + canonical same-session continuity. The habitation adapter
            # must not inject evaluator semantic labels or pre-decide memory relevance.
            occurred_at=event.occurred_at,
            token_budget=self._token_budget,
        )
        self._session_turns[session_id] = turn_index
        return {
            "kind": "conversation",
            "session_id": session_id,
            "turn_index": turn_index,
            "response": result.runtime.response,
            "silenced": result.runtime.silenced,
            "termination_reason": result.runtime.termination_reason,
            "capabilities": [
                item.name for item in result.runtime.capability_history
            ],
            "recommended_memory_count": len(result.recommendation.cards),
            "continuity_summary_ids": [
                item.object_id
                for item in result.continuity_summary_commits
            ],
            "continuity_summary_error": result.continuity_summary_error,
            "world_revision": int(self.store.current_world_revision()),
        }

    def _handle_generic_reality(
        self,
        event: ResidentEvent,
    ) -> tuple[dict[str, Any], tuple[ObjectRef, ...]]:
        spec = self._spec_for(event.channel)
        modality = "text" if isinstance(event.payload, str) else spec.default_modality
        receipt = self.reality.ingest_record(
            spec,
            RealityRecord(
                external_record_id=event.event_id,
                occurred_at=event.occurred_at,
                received_at=event.occurred_at,
                value=event.payload,
                modality=modality,
                source_locator=(
                    f"habitation://{self.subject_id}/"
                    f"{_clean_channel(event.channel)}/{event.event_id}"
                ),
                provenance={
                    "habitation_resident_metadata": dict(event.metadata),
                    "model_id_not_part_of_fact": True,
                },
            ),
        )
        ref = ObjectRef(object_id=receipt.observation_id, revision=1)
        return (
            {
                "kind": "reality",
                "observation_refs": [ref.model_dump(mode="json")],
                "reused_existing": receipt.reused_existing,
                "world_revision": int(self.store.current_world_revision()),
            },
            (ref,),
        )

    def _handle_media_descriptor(
        self,
        event: ResidentEvent,
    ) -> tuple[dict[str, Any], tuple[ObjectRef, ...]]:
        if not isinstance(event.payload, str) or not event.payload.strip():
            raise ValueError("photo_description payload must be non-blank text")
        clean = _clean_channel(event.channel)
        spec = self._source_specs.get(clean) or SourceAdapterSpec(
            adapter_id=f"habitation.{clean}.v1",
            source_kind=clean,
            dimension=f"dim:{clean}",
            source_class=SourceClass.USER,
            default_modality="image_caption",
        )
        receipt = self.reality.ingest_media_descriptor(
            spec,
            MediaDescriptorRecord(
                external_record_id=event.event_id,
                occurred_at=event.occurred_at,
                descriptor=event.payload,
                descriptor_kind="image_caption",
                source_locator=(
                    f"habitation://{self.subject_id}/{clean}/{event.event_id}"
                ),
                received_at=event.occurred_at,
                provenance={
                    "habitation_resident_metadata": dict(event.metadata),
                    "model_id_not_part_of_fact": True,
                },
            ),
        )
        ref = ObjectRef(object_id=receipt.observation_id, revision=1)
        return (
            {
                "kind": "media_descriptor",
                "observation_refs": [ref.model_dump(mode="json")],
                "reused_existing": receipt.reused_existing,
                "world_revision": int(self.store.current_world_revision()),
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
        raise ValueError(
            "numeric sample occurred_at must be datetime or ISO-8601 string"
        )

    def _handle_numeric_series(
        self,
        event: ResidentEvent,
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
            sample_time = self._parse_sample_time(
                raw.get("occurred_at", event.occurred_at)
            )
            if sample_time > as_utc(event.occurred_at, "event.occurred_at"):
                raise ValueError(
                    "sensor_numeric sample cannot occur after its resident-visible "
                    "delivery event; future samples would leak future information"
                )
            samples.append(
                NumericSample(
                    external_record_id=record_id,
                    occurred_at=sample_time,
                    value=raw.get("value"),
                    source_locator=raw.get("source_locator"),
                )
            )

        spec = SourceAdapterSpec(
            adapter_id=f"habitation.{_clean_channel(source_kind)}.numeric.v1",
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
            received_at=event.occurred_at,
        )
        ids = (
            *receipt.segment_observation_ids,
            *receipt.change_observation_ids,
        )
        refs = tuple(
            ObjectRef(object_id=object_id, revision=1)
            for object_id in ids
        )
        return (
            {
                "kind": "numeric_series",
                "observation_refs": [
                    ref.model_dump(mode="json") for ref in refs
                ],
                "segment_observation_ids": list(receipt.segment_observation_ids),
                "change_observation_ids": list(receipt.change_observation_ids),
                "reused_existing_count": receipt.reused_existing_count,
                "world_revision": int(self.store.current_world_revision()),
            },
            refs,
        )

    def _apply_observation_rules(
        self,
        refs: tuple[ObjectRef, ...],
        *,
        now: datetime,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        trigger_receipts: list[dict[str, Any]] = []
        for ref in refs:
            receipts = self.observation_triggers.evaluate_observation(
                ref,
                rules=self._observation_wake_rules,
            )
            trigger_receipts.extend(asdict(item) for item in receipts)
        wake_runs = self._dispatch_pending_wakes(now)
        return trigger_receipts, wake_runs

    def handle_event(self, event: ResidentEvent) -> Mapping[str, Any]:
        event_time = as_utc(event.occurred_at, "occurred_at")
        if self._clock is None or event_time != self._clock:
            raise ValueError(
                "runner must advance virtual clock to event time before delivery"
            )

        channel = _clean_channel(event.channel)
        if channel == "conversation":
            result = dict(self._handle_conversation(event))
        elif channel == "photo_description":
            base, refs = self._handle_media_descriptor(event)
            trigger_wakes, wake_runs = self._apply_observation_rules(
                refs,
                now=event_time,
            )
            result = {
                **base,
                "trigger_wakes": trigger_wakes,
                "wake_runs": wake_runs,
            }
        elif channel == "sensor_numeric":
            base, refs = self._handle_numeric_series(event)
            trigger_wakes, wake_runs = self._apply_observation_rules(
                refs,
                now=event_time,
            )
            result = {
                **base,
                "trigger_wakes": trigger_wakes,
                "wake_runs": wake_runs,
            }
        else:
            base, refs = self._handle_generic_reality(event)
            trigger_wakes, wake_runs = self._apply_observation_rules(
                refs,
                now=event_time,
            )
            result = {
                **base,
                "trigger_wakes": trigger_wakes,
                "wake_runs": wake_runs,
            }

        self._event_log.append(
            {
                "event_id": event.event_id,
                "occurred_at": event_time.isoformat(),
                "channel": event.channel,
                "result": result,
            }
        )
        return result

    def audit_snapshot(self) -> Mapping[str, Any]:
        payloads = self.store.list_payloads(subject_id=self.subject_id)
        payloads.sort(
            key=lambda item: (
                str(item.get("object_type") or ""),
                str(item.get("object_id") or ""),
            )
        )
        counts = Counter(str(item.get("object_type") or "") for item in payloads)

        provider_provenance = None
        for handler in (self._model_handler, self._round_summary_handler):
            if handler is None:
                continue
            snapshotter = getattr(handler, "provenance_snapshot", None)
            if callable(snapshotter):
                provider_provenance = snapshotter()
                break

        return {
            "subject_id": self.subject_id,
            "model_id": self.model_id,
            "provider_provenance": provider_provenance,
            "resumed_from_world": self._resumed_from_world,
            "clock": None if self._clock is None else self._clock.isoformat(),
            "world_revision": int(self.store.current_world_revision()),
            "index_watermark": int(self.index.watermark()),
            "object_counts": dict(sorted(counts.items())),
            "objects": payloads,
            "session_turns": dict(sorted(self._session_turns.items())),
            "event_log": list(self._event_log),
            "background_log": list(self._background_log),
        }


class CurrentCoreHabitationTargetFactory:
    """Create a fresh private current-Core world per model candidate."""

    def __init__(
        self,
        *,
        root_dir: str | Path,
        model_handler_factory: ModelHandlerFactory,
        round_summary_handler_factory: RoundSummaryHandlerFactory | None = None,
        source_specs: Mapping[str, SourceAdapterSpec] | None = None,
        observation_wake_rules: Sequence[ObservationWakeRule] = (),
        review_policy: ReviewSchedulePolicy | None = None,
        wake_step0_provider: WakeStep0Provider | None = None,
        token_budget: int | None = None,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.model_handler_factory = model_handler_factory
        self.round_summary_handler_factory = round_summary_handler_factory
        self.source_specs = dict(source_specs or {})
        self.observation_wake_rules = tuple(observation_wake_rules)
        self.review_policy = review_policy
        self.wake_step0_provider = wake_step0_provider
        self.token_budget = token_budget
        self._counter = 0

    def __call__(
        self,
        *,
        model_id: str,
        scenario: ResidentScenarioDescriptor,
    ) -> CurrentCoreHabitationTarget:
        self._counter += 1
        opaque = hashlib.sha256(
            f"{self._counter}|{model_id}|{scenario.subject_id}".encode("utf-8")
        ).hexdigest()[:16]
        db_path = self.root_dir / f"world-{self._counter:04d}-{opaque}.sqlite"
        summary_handler = (
            None
            if self.round_summary_handler_factory is None
            else self.round_summary_handler_factory(model_id)
        )
        return CurrentCoreHabitationTarget(
            model_id=model_id,
            subject_id=scenario.subject_id,
            db_path=db_path,
            model_handler=self.model_handler_factory(model_id),
            round_summary_handler=summary_handler,
            source_specs=self.source_specs,
            observation_wake_rules=self.observation_wake_rules,
            review_policy=self.review_policy,
            wake_step0_provider=self.wake_step0_provider,
            token_budget=self.token_budget,
        )
