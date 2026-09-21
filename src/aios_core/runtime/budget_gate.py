"""C13 mechanical budget gate for autonomous Resident model execution.

The gate reads durable BudgetPolicy objects from the unified World and measures
usage from durable Wake lifecycle records. It never judges semantic importance.

Provider token usage is intentionally *not* estimated here. If an active budget
declares max_tokens before real provider telemetry exists, the gate fails closed
instead of inventing usage numbers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from aios_core.contracts.enums import (
    BudgetOnExceed,
    BudgetScope,
    ObjectType,
    WakeSource,
    WakeState,
)
from aios_core.contracts.models import BudgetPolicy, Wake
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import as_utc
from aios_core.storage.sqlite_store import SQLiteWorldStore


@dataclass(frozen=True, slots=True)
class BackgroundBudgetDecision:
    applies: bool
    available: bool
    world_revision: int
    window_start: datetime | None = None
    window_end: datetime | None = None
    policy_refs: tuple[ObjectRef, ...] = ()
    used_wakes: int = 0
    used_model_calls: int = 0
    max_wakes: int | None = None
    max_model_calls: int | None = None
    model_round_limit: int | None = None
    reserved_model_calls: int = 0
    reasons: tuple[str, ...] = ()
    on_exceed: tuple[BudgetOnExceed, ...] = ()

    @property
    def hard_deny(self) -> bool:
        return (not self.available) and BudgetOnExceed.HARD_DENY in self.on_exceed

    @property
    def requires_reservation(self) -> bool:
        return self.applies and self.available and bool(self.policy_refs)

    def reservation_metadata(self) -> dict[str, Any]:
        if not self.requires_reservation or self.window_start is None or self.window_end is None:
            return {}
        return {
            "budget_scope": BudgetScope.BACKGROUND_DAY.value,
            "budget_window_start": self.window_start.isoformat(),
            "budget_window_end": self.window_end.isoformat(),
            "budget_policy_refs": [
                ref.model_dump(mode="json") for ref in self.policy_refs
            ],
            "budget_reserved_wakes": 1,
            "budget_reserved_model_calls": int(self.reserved_model_calls),
        }

    def context_payload(self) -> dict[str, Any]:
        return {
            "applies": self.applies,
            "available": self.available,
            "scope": (
                BudgetScope.BACKGROUND_DAY.value if self.applies else None
            ),
            "window_start": (
                None if self.window_start is None else self.window_start.isoformat()
            ),
            "window_end": (
                None if self.window_end is None else self.window_end.isoformat()
            ),
            "policy_refs": [
                ref.model_dump(mode="json") for ref in self.policy_refs
            ],
            "used_wakes": self.used_wakes,
            "used_model_calls": self.used_model_calls,
            "max_wakes": self.max_wakes,
            "max_model_calls": self.max_model_calls,
            "model_round_limit": self.model_round_limit,
            "reserved_model_calls": self.reserved_model_calls,
            "reasons": list(self.reasons),
        }


class BackgroundBudgetGate:
    """Enforce BACKGROUND_DAY BudgetPolicy before autonomous model execution."""

    def __init__(
        self,
        *,
        store: SQLiteWorldStore,
        subject_id: str = "user_1",
    ) -> None:
        if not isinstance(subject_id, str) or not subject_id.strip():
            raise ValueError("subject_id must not be blank")
        self.store = store
        self.subject_id = subject_id.strip()

    @staticmethod
    def _window(now: datetime) -> tuple[datetime, datetime]:
        moment = as_utc(now, "now")
        start = moment.astimezone(timezone.utc).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        return start, start + timedelta(days=1)

    def _policies(self) -> tuple[BudgetPolicy, ...]:
        policies: list[BudgetPolicy] = []
        for payload in self.store.list_payloads(
            object_type=ObjectType.BUDGET_POLICY,
            subject_id=self.subject_id,
        ):
            if str(payload.get("status") or "active") != "active":
                continue
            policy = BudgetPolicy.model_validate(payload)
            if policy.scope is BudgetScope.BACKGROUND_DAY:
                policies.append(policy)
        policies.sort(
            key=lambda item: (
                as_utc(item.recorded_at, "recorded_at"),
                item.object_id,
                item.revision,
            )
        )
        return tuple(policies)

    @staticmethod
    def _parse_time(value: object, field_name: str) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return as_utc(value, field_name)
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return as_utc(parsed, field_name)

    @staticmethod
    def _is_autonomous_wake(wake: Wake) -> bool:
        return wake.wake_source not in {
            WakeSource.SAFETY,
            WakeSource.USER_INTERACTION,
        }

    def _usage(
        self,
        *,
        window_start: datetime,
        window_end: datetime,
        exclude_wake_id: str,
    ) -> tuple[int, int]:
        used_wakes = 0
        used_model_calls = 0

        for payload in self.store.list_payloads(
            object_type=ObjectType.WAKE,
            subject_id=self.subject_id,
        ):
            wake = Wake.model_validate(payload)
            if wake.object_id == exclude_wake_id:
                continue
            if not self._is_autonomous_wake(wake):
                continue

            metadata: Mapping[str, Any] = wake.metadata
            if wake.wake_state is WakeState.RUNNING:
                started_at = self._parse_time(
                    metadata.get("started_at"),
                    "started_at",
                )
                if started_at is None:
                    started_at = as_utc(wake.recorded_at, "recorded_at")
                if not (window_start <= started_at < window_end):
                    continue
                used_wakes += 1
                reserved = metadata.get("budget_reserved_model_calls")
                if isinstance(reserved, int) and not isinstance(reserved, bool) and reserved > 0:
                    used_model_calls += reserved
                else:
                    # Legacy RUNNING work has already crossed the model boundary.
                    # Count at least one call rather than pretending it costs zero.
                    used_model_calls += 1
                continue

            if wake.wake_state is not WakeState.COMPLETED:
                continue

            completed_at = self._parse_time(
                metadata.get("completed_at"),
                "completed_at",
            )
            if completed_at is None:
                completed_at = self._parse_time(
                    metadata.get("started_at"),
                    "started_at",
                )
            if completed_at is None:
                completed_at = as_utc(wake.recorded_at, "recorded_at")
            if not (window_start <= completed_at < window_end):
                continue

            rounds = metadata.get("model_rounds")
            if (
                not isinstance(rounds, int)
                or isinstance(rounds, bool)
                or rounds <= 0
            ):
                continue
            used_wakes += 1
            used_model_calls += rounds

        return used_wakes, used_model_calls

    def evaluate(
        self,
        wake: Wake,
        *,
        now: datetime,
        max_model_rounds: int,
    ) -> BackgroundBudgetDecision:
        if max_model_rounds < 1:
            raise ValueError("max_model_rounds must be >= 1")

        world_revision = int(self.store.current_world_revision())
        if not self._is_autonomous_wake(wake):
            return BackgroundBudgetDecision(
                applies=False,
                available=True,
                world_revision=world_revision,
            )

        policies = self._policies()
        if not policies:
            return BackgroundBudgetDecision(
                applies=False,
                available=True,
                world_revision=world_revision,
            )

        window_start, window_end = self._window(now)
        policy_refs = tuple(
            ObjectRef(object_id=item.object_id, revision=item.revision)
            for item in policies
        )

        # A resumed RUNNING Wake keeps its already-durable reservation. This avoids
        # charging the same invocation twice after process recovery.
        if wake.wake_state is WakeState.RUNNING:
            metadata = wake.metadata
            if str(metadata.get("budget_scope") or "") == BudgetScope.BACKGROUND_DAY.value:
                reserved = metadata.get("budget_reserved_model_calls")
                limit = (
                    int(reserved)
                    if isinstance(reserved, int)
                    and not isinstance(reserved, bool)
                    and reserved > 0
                    else None
                )
                return BackgroundBudgetDecision(
                    applies=True,
                    available=True,
                    world_revision=world_revision,
                    window_start=window_start,
                    window_end=window_end,
                    policy_refs=policy_refs,
                    model_round_limit=limit,
                    reserved_model_calls=limit or 0,
                )

        used_wakes, used_model_calls = self._usage(
            window_start=window_start,
            window_end=window_end,
            exclude_wake_id=wake.object_id,
        )

        wake_caps = [item.max_wakes for item in policies if item.max_wakes is not None]
        call_caps = [
            item.max_model_calls
            for item in policies
            if item.max_model_calls is not None
        ]
        max_wakes = min(wake_caps) if wake_caps else None
        max_model_calls = min(call_caps) if call_caps else None

        reasons: list[str] = []
        exceeded_modes: list[BudgetOnExceed] = []

        token_policies = [item for item in policies if item.max_tokens is not None]
        if token_policies:
            reasons.append("background_token_budget_requires_provider_usage_telemetry")
            exceeded_modes.extend(item.on_exceed for item in token_policies)

        if max_wakes is not None and used_wakes >= max_wakes:
            reasons.append(
                f"background_wake_budget_exhausted:{used_wakes}/{max_wakes}"
            )
            exceeded_modes.extend(
                item.on_exceed
                for item in policies
                if item.max_wakes is not None and used_wakes >= item.max_wakes
            )

        remaining_calls: int | None = None
        if max_model_calls is not None:
            remaining_calls = max_model_calls - used_model_calls
            if remaining_calls <= 0:
                reasons.append(
                    "background_model_call_budget_exhausted:"
                    f"{used_model_calls}/{max_model_calls}"
                )
                exceeded_modes.extend(
                    item.on_exceed
                    for item in policies
                    if item.max_model_calls is not None
                    and used_model_calls >= item.max_model_calls
                )

        available = not reasons
        if not available:
            return BackgroundBudgetDecision(
                applies=True,
                available=False,
                world_revision=world_revision,
                window_start=window_start,
                window_end=window_end,
                policy_refs=policy_refs,
                used_wakes=used_wakes,
                used_model_calls=used_model_calls,
                max_wakes=max_wakes,
                max_model_calls=max_model_calls,
                reasons=tuple(dict.fromkeys(reasons)),
                on_exceed=tuple(dict.fromkeys(exceeded_modes)),
            )

        model_round_limit = None
        reserved_model_calls = 0
        if remaining_calls is not None:
            model_round_limit = min(max_model_rounds, remaining_calls)
            reserved_model_calls = model_round_limit

        return BackgroundBudgetDecision(
            applies=True,
            available=True,
            world_revision=world_revision,
            window_start=window_start,
            window_end=window_end,
            policy_refs=policy_refs,
            used_wakes=used_wakes,
            used_model_calls=used_model_calls,
            max_wakes=max_wakes,
            max_model_calls=max_model_calls,
            model_round_limit=model_round_limit,
            reserved_model_calls=reserved_model_calls,
            on_exceed=tuple(dict.fromkeys(item.on_exceed for item in policies)),
        )
