"""Adapter that lets the P16 harness inhabit the real current AIOS Core.

This module is test infrastructure, not an alternate runtime. It creates one private
WorldStore/Index/FusedTurnRuntime per model candidate and feeds only resident-visible
events through public Core surfaces.

The harness never manufactures cognition. A supplied real model handler remains the
only component that may interpret life events, form/revise Claims, create dimensions,
or act through AIOS capabilities.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from aios_core.contracts.enums import ObjectType, SourceClass, WakeSource
from aios_core.contracts.refs import ObjectRef
from aios_core.ingest import RealityIngestService, RealityRecord, SourceAdapterSpec
from aios_core.query.search import WorldSearchIndex
from aios_core.review import ReviewSchedulePolicy
from aios_core.runtime.cognitive_runtime import ModelHandler
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.wake import (
    ObservationTriggerService,
    ObservationWakeRule,
)

from .harness import HabitationTarget, ResidentEvent


RoundSummaryHandler = Callable[[Any], str]


def _clean_channel(channel: str) -> str:
    value = channel.strip().lower().replace("-", "_").replace(" ", "_")
    if not value:
        raise ValueError("channel must not be blank")
    if not all(ch.isalnum() or ch in {"_", "."} for ch in value):
        raise ValueError(f"unsupported channel identity: {channel!r}")
    return value


def default_source_spec(channel: str) -> SourceAdapterSpec:
    """Build a mechanical source adapter from the resident-visible channel name.

    This maps transport/source identity only. It does not classify semantic meaning.
    """

    clean = _clean_channel(channel)
    return SourceAdapterSpec(
        adapter_id=f"habitation.{clean}.v1",
        source_kind=clean,
        dimension=f"dim:{clean}",
        source_class=SourceClass.USER,
        default_modality="structured_record",
    )


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
        source_specs: Mapping[str, SourceAdapterSpec] | None = None,
        observation_wake_rules: Sequence[ObservationWakeRule] = (),
        review_policy: ReviewSchedulePolicy | None = None,
        token_budget: int | None = None,
    ) -> None:
        if not isinstance(model_id, str) or not model_id.strip():
            raise ValueError("model_id must not be blank")
        if not isinstance(subject_id, str) or not subject_id.strip():
            raise ValueError("subject_id must not be blank")

        self.model_id = model_id.strip()
        self.subject_id = subject_id.strip()
        self.db_path = Path(db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._isolation_key = f"sqlite:{self.db_path}"
        self._clock: datetime | None = None
        self._session_turns: dict[str, int] = {}
        self._source_specs = {
            _clean_channel(key): value
            for key, value in dict(source_specs or {}).items()
        }
        self._observation_wake_rules = tuple(observation_wake_rules)
        self._review_policy = review_policy or ReviewSchedulePolicy()
        self._token_budget = token_budget

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
            max_tool_rounds=8,
        )
        self.observation_triggers = ObservationTriggerService(
            store=self.store,
            wake_bus=self.runtime.wake_bus,
            subject_id=self.subject_id,
        )

    @property
    def isolation_key(self) -> str:
        return self._isolation_key

    def _spec_for(self, channel: str) -> SourceAdapterSpec:
        clean = _clean_channel(channel)
        return self._source_specs.get(clean) or default_source_spec(clean)

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
            result = self.runtime.run_wake(
                wake_ref=ObjectRef(
                    object_id=wake.object_id,
                    revision=wake.revision,
                ),
                now=now,
                token_budget=self._token_budget,
            )
            results.append(
                {
                    "wake_id": result.wake_ref.object_id,
                    "wake_revision": result.wake_ref.revision,
                    "wake_source": wake.wake_source.value,
                    "delivery_response": result.delivery_response,
                    "delivery_suppressed": result.delivery_suppressed,
                    "termination_reason": (
                        None
                        if result.runtime is None
                        else result.runtime.termination_reason
                    ),
                    "capabilities": (
                        []
                        if result.runtime is None
                        else [
                            item.name
                            for item in result.runtime.capability_history
                        ]
                    ),
                }
            )
        return results

    def advance_to(self, instant: datetime) -> Mapping[str, Any]:
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("virtual clock instant must be timezone-aware")
        if self._clock is not None and instant < self._clock:
            raise ValueError("virtual clock cannot move backwards")
        self._clock = instant

        task_wakes = self.runtime.execution_world.wake_due_tasks(now=instant)
        wake_runs = self._dispatch_pending_wakes(instant)
        review = self.runtime.run_periodic_review(
            now=instant,
            policy=self._review_policy,
            token_budget=self._token_budget,
        )

        return {
            "instant": instant.isoformat(),
            "task_wakes": [asdict(item) for item in task_wakes],
            "wake_runs": wake_runs,
            "periodic_review": (
                None
                if review is None
                else {
                    "review_id": review.request.review_id,
                    "wake_id": review.wake.wake_id,
                    "wake_revision": review.wake.revision,
                    "termination_reason": review.runtime.termination_reason,
                    "capabilities": [
                        item.name
                        for item in review.runtime.capability_history
                    ],
                }
            ),
            "world_revision": int(self.store.current_world_revision()),
        }

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
            # Use only the current resident-visible utterance as the topic gate seed.
            # The benchmark must not inject evaluator semantic labels.
            current_topic=event.payload,
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

    def _handle_reality(self, event: ResidentEvent) -> Mapping[str, Any]:
        spec = self._spec_for(event.channel)
        receipt = self.reality.ingest_record(
            spec,
            RealityRecord(
                external_record_id=event.event_id,
                occurred_at=event.occurred_at,
                received_at=event.occurred_at,
                value=event.payload,
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
        observation_ref = ObjectRef(
            object_id=receipt.observation_id,
            revision=1,
        )
        trigger_receipts = self.observation_triggers.evaluate_observation(
            observation_ref,
            rules=self._observation_wake_rules,
        )
        wake_runs = self._dispatch_pending_wakes(event.occurred_at)
        return {
            "kind": "reality",
            "observation_ref": observation_ref.model_dump(mode="json"),
            "reused_existing": receipt.reused_existing,
            "trigger_wakes": [asdict(item) for item in trigger_receipts],
            "wake_runs": wake_runs,
            "world_revision": int(self.store.current_world_revision()),
        }

    def handle_event(self, event: ResidentEvent) -> Mapping[str, Any]:
        if self._clock is None or event.occurred_at != self._clock:
            raise ValueError(
                "runner must advance virtual clock to event time before delivery"
            )
        if _clean_channel(event.channel) == "conversation":
            return self._handle_conversation(event)
        return self._handle_reality(event)

    def audit_snapshot(self) -> Mapping[str, Any]:
        payloads = self.store.list_payloads(subject_id=self.subject_id)
        payloads.sort(
            key=lambda item: (
                str(item.get("object_type") or ""),
                str(item.get("object_id") or ""),
            )
        )
        counts: dict[str, int] = {}
        for payload in payloads:
            object_type = str(payload.get("object_type") or "")
            counts[object_type] = counts.get(object_type, 0) + 1

        return {
            "subject_id": self.subject_id,
            "model_id": self.model_id,
            "world_revision": int(self.store.current_world_revision()),
            "index_watermark": int(self.index.watermark()),
            "object_counts": counts,
            "objects": payloads,
        }
