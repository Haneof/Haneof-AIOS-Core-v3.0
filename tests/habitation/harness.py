"""Model-agnostic long-horizon habitation benchmark for AIOS v3.0.

P16 compares different resident models by letting each model independently inhabit
its own AIOS instance while receiving the same sealed synthetic life. Models never
communicate, share state, or cooperate.

A scenario may contain evaluator-only hidden oracle data. Only resident-visible
projections and oracle-free structural metadata may cross into model-side adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Protocol, Sequence


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class ResidentEvent:
    """The only life-event view that may be delivered to a resident model."""

    event_id: str
    occurred_at: datetime
    channel: str
    payload: Any
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise ValueError("event_id must be non-empty")
        if not self.channel.strip():
            raise ValueError("channel must be non-empty")
        _require_aware(self.occurred_at, "occurred_at")


@dataclass(frozen=True, slots=True)
class LifeEvent:
    """One chronological event in a sealed synthetic life."""

    event_id: str
    occurred_at: datetime
    channel: str
    payload: Any
    metadata: Mapping[str, Any] = field(default_factory=dict)
    hidden_oracle: Mapping[str, Any] = field(default_factory=dict)
    deliver_to_resident: bool = True

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise ValueError("event_id must be non-empty")
        if not self.channel.strip():
            raise ValueError("channel must be non-empty")
        _require_aware(self.occurred_at, "occurred_at")
        overlap = set(self.metadata).intersection(self.hidden_oracle)
        if overlap:
            raise ValueError(
                "resident-visible metadata and hidden_oracle must use disjoint keys: "
                + ", ".join(sorted(overlap))
            )

    def resident_view(self) -> ResidentEvent:
        return ResidentEvent(
            event_id=self.event_id,
            occurred_at=self.occurred_at,
            channel=self.channel,
            payload=self.payload,
            metadata=dict(self.metadata),
        )


@dataclass(frozen=True, slots=True)
class ResidentScenarioDescriptor:
    """Oracle-free structural metadata safe to expose to model-side factories."""

    scenario_id: str
    subject_id: str
    scenario_version: str
    seed: int
    visible_event_count: int
    first_visible_at: datetime | None
    last_visible_at: datetime | None
    channels: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HabitationScenario:
    """A sealed chronological virtual life reused across model candidates."""

    scenario_id: str
    subject_id: str
    events: tuple[LifeEvent, ...]
    hidden_oracle: Mapping[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = ()
    scenario_version: str = "1"
    seed: int = 0

    def __post_init__(self) -> None:
        if not self.scenario_id.strip():
            raise ValueError("scenario_id must be non-empty")
        if not self.subject_id.strip():
            raise ValueError("subject_id must be non-empty")
        if not self.events:
            raise ValueError("scenario must contain at least one event")
        if not self.scenario_version.strip():
            raise ValueError("scenario_version must be non-empty")
        if self.seed < 0:
            raise ValueError("seed must be >= 0")

        seen: set[str] = set()
        previous: datetime | None = None
        for event in self.events:
            if event.event_id in seen:
                raise ValueError(f"duplicate event_id: {event.event_id}")
            seen.add(event.event_id)
            if previous is not None and event.occurred_at < previous:
                raise ValueError("scenario events must already be chronological")
            previous = event.occurred_at


class HabitationTarget(Protocol):
    """One isolated AIOS instance backed by exactly one resident model."""

    @property
    def isolation_key(self) -> str:
        """Stable identity for the private world/store owned by this target."""

    def handle_event(self, event: ResidentEvent) -> Any:
        """Deliver one event to this model's private AIOS world."""


class HabitationTargetFactory(Protocol):
    """Create one fresh target using only oracle-free scenario metadata."""

    def __call__(
        self,
        *,
        model_id: str,
        scenario: ResidentScenarioDescriptor,
    ) -> HabitationTarget:
        """Return a fresh isolated target for one model candidate."""


class HabitationEvaluator(Protocol):
    """Post-run evaluation may inspect hidden truth; the resident may not."""

    def evaluate(
        self,
        *,
        scenario: HabitationScenario,
        run: "HabitationRun",
    ) -> Mapping[str, Any]:
        """Return findings after a completed independent resident run."""


@dataclass(frozen=True, slots=True)
class HabitationStep:
    event_id: str
    occurred_at: datetime
    channel: str
    delivered: bool
    response: Any = None


@dataclass(frozen=True, slots=True)
class HabitationRun:
    scenario_id: str
    subject_id: str
    model_id: str
    steps: tuple[HabitationStep, ...]

    @property
    def delivered_count(self) -> int:
        return sum(1 for step in self.steps if step.delivered)


@dataclass(frozen=True, slots=True)
class MultiModelHabitationResult:
    """Independent runs of multiple model candidates over the same sealed life."""

    scenario_id: str
    runs: Mapping[str, HabitationRun]


def resident_scenario_descriptor(
    scenario: HabitationScenario,
) -> ResidentScenarioDescriptor:
    """Project a sealed scenario into metadata that cannot contain hidden oracle."""

    visible = tuple(
        event for event in scenario.events if event.deliver_to_resident
    )
    return ResidentScenarioDescriptor(
        scenario_id=scenario.scenario_id,
        subject_id=scenario.subject_id,
        scenario_version=scenario.scenario_version,
        seed=scenario.seed,
        visible_event_count=len(visible),
        first_visible_at=visible[0].occurred_at if visible else None,
        last_visible_at=visible[-1].occurred_at if visible else None,
        channels=tuple(dict.fromkeys(event.channel for event in visible)),
    )


class HabitationRunner:
    """Execute one sealed life independently against one or more model candidates."""

    def run(
        self,
        *,
        scenario: HabitationScenario,
        model_id: str,
        target: HabitationTarget,
    ) -> HabitationRun:
        if not model_id.strip():
            raise ValueError("model_id must be non-empty")

        steps: list[HabitationStep] = []
        for event in scenario.events:
            if not event.deliver_to_resident:
                steps.append(
                    HabitationStep(
                        event_id=event.event_id,
                        occurred_at=event.occurred_at,
                        channel=event.channel,
                        delivered=False,
                    )
                )
                continue

            response = target.handle_event(event.resident_view())
            steps.append(
                HabitationStep(
                    event_id=event.event_id,
                    occurred_at=event.occurred_at,
                    channel=event.channel,
                    delivered=True,
                    response=response,
                )
            )

        return HabitationRun(
            scenario_id=scenario.scenario_id,
            subject_id=scenario.subject_id,
            model_id=model_id,
            steps=tuple(steps),
        )

    def run_models(
        self,
        *,
        scenario: HabitationScenario,
        targets: Mapping[str, HabitationTarget],
    ) -> MultiModelHabitationResult:
        """Run each model candidate in an independently identified AIOS world."""

        if not targets:
            raise ValueError("targets must contain at least one model candidate")

        runs: dict[str, HabitationRun] = {}
        seen_target_ids: set[int] = set()
        seen_isolation_keys: set[str] = set()

        for model_id, target in targets.items():
            target_identity = id(target)
            if target_identity in seen_target_ids:
                raise ValueError(
                    "each model_id must receive an independent AIOS target instance"
                )
            seen_target_ids.add(target_identity)

            isolation_key = str(target.isolation_key).strip()
            if not isolation_key:
                raise ValueError("target isolation_key must be non-empty")
            if isolation_key in seen_isolation_keys:
                raise ValueError(
                    "each model_id must receive an independent AIOS world/store"
                )
            seen_isolation_keys.add(isolation_key)

            runs[model_id] = self.run(
                scenario=scenario,
                model_id=model_id,
                target=target,
            )

        return MultiModelHabitationResult(
            scenario_id=scenario.scenario_id,
            runs=runs,
        )

    def run_model_factories(
        self,
        *,
        scenario: HabitationScenario,
        factories: Mapping[str, HabitationTargetFactory],
    ) -> MultiModelHabitationResult:
        """Create a fresh oracle-isolated target/world for each model candidate."""

        if not factories:
            raise ValueError("factories must contain at least one model candidate")

        descriptor = resident_scenario_descriptor(scenario)
        targets: dict[str, HabitationTarget] = {}
        for model_id, factory in factories.items():
            targets[model_id] = factory(
                model_id=model_id,
                scenario=descriptor,
            )

        return self.run_models(scenario=scenario, targets=targets)


def evaluate_run(
    *,
    evaluator: HabitationEvaluator,
    scenario: HabitationScenario,
    run: HabitationRun,
) -> Mapping[str, Any]:
    """Evaluate one model only after its independent habitation run has finished."""

    if run.scenario_id != scenario.scenario_id:
        raise ValueError("run and scenario do not match")
    if run.subject_id != scenario.subject_id:
        raise ValueError("run subject and scenario subject do not match")
    return evaluator.evaluate(scenario=scenario, run=run)


def scenario_channels(scenario: HabitationScenario) -> tuple[str, ...]:
    """Return unique channels in first-seen order for reporting and sharding."""

    return tuple(dict.fromkeys(event.channel for event in scenario.events))


def visible_events(scenario: HabitationScenario) -> Sequence[ResidentEvent]:
    """Return resident-visible event projections only; hidden oracle stays sealed."""

    return tuple(
        event.resident_view()
        for event in scenario.events
        if event.deliver_to_resident
    )
