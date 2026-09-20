"""Model-agnostic long-horizon habitation harness for AIOS v3.0.

The harness deliberately does not contain semantic "correct answers". A scenario
contains resident-visible life events plus a separate hidden oracle that is only
available to evaluators. This prevents the runtime under test from receiving the
answer key and keeps P16 focused on emergent long-term behavior rather than
string-matching tests.
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
    """The only event view that may be delivered to the resident system."""

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
    """One chronological event in a synthetic life.

    hidden_oracle is evaluation-only ground truth. It must never be passed to the
    resident model or included in the resident-visible metadata.
    """

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
class HabitationScenario:
    """A sealed, chronological virtual-life scenario."""

    scenario_id: str
    subject_id: str
    events: tuple[LifeEvent, ...]
    hidden_oracle: Mapping[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.scenario_id.strip():
            raise ValueError("scenario_id must be non-empty")
        if not self.subject_id.strip():
            raise ValueError("subject_id must be non-empty")
        if not self.events:
            raise ValueError("scenario must contain at least one event")

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
    """Adapter implemented by the system-under-test for one resident agent."""

    def handle_event(self, event: ResidentEvent) -> Any:
        """Deliver one resident-visible event and return the system response."""


class HabitationEvaluator(Protocol):
    """Evaluation is separate from execution and may inspect hidden truth."""

    def evaluate(
        self,
        *,
        scenario: HabitationScenario,
        run: "HabitationRun",
    ) -> Mapping[str, Any]:
        """Return metrics/findings without exposing oracle data to the resident."""


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
    agent_id: str
    steps: tuple[HabitationStep, ...]

    @property
    def delivered_count(self) -> int:
        return sum(1 for step in self.steps if step.delivered)


@dataclass(frozen=True, slots=True)
class MultiAgentHabitationResult:
    scenario_id: str
    runs: Mapping[str, HabitationRun]


class HabitationRunner:
    """Execute the same sealed life against one or many independent residents."""

    def run(
        self,
        *,
        scenario: HabitationScenario,
        agent_id: str,
        target: HabitationTarget,
    ) -> HabitationRun:
        if not agent_id.strip():
            raise ValueError("agent_id must be non-empty")

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
            agent_id=agent_id,
            steps=tuple(steps),
        )

    def run_many(
        self,
        *,
        scenario: HabitationScenario,
        targets: Mapping[str, HabitationTarget],
    ) -> MultiAgentHabitationResult:
        if not targets:
            raise ValueError("targets must contain at least one resident agent")

        runs: dict[str, HabitationRun] = {}
        seen_target_ids: set[int] = set()
        for agent_id, target in targets.items():
            identity = id(target)
            if identity in seen_target_ids:
                raise ValueError(
                    "each agent_id must receive an independent target instance"
                )
            seen_target_ids.add(identity)
            runs[agent_id] = self.run(
                scenario=scenario,
                agent_id=agent_id,
                target=target,
            )

        return MultiAgentHabitationResult(
            scenario_id=scenario.scenario_id,
            runs=runs,
        )


def evaluate_run(
    *,
    evaluator: HabitationEvaluator,
    scenario: HabitationScenario,
    run: HabitationRun,
) -> Mapping[str, Any]:
    """Run an evaluator after habitation without feeding its oracle to the agent."""

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
