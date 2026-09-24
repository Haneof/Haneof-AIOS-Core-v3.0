"""R5 AI Cognitive Runtime: bounded, auditable, model-driven tool loop.

This module intentionally does not encode a mandatory WAKE/ORIENT/RECALL thought
sequence. The model receives a compact snapshot and capability catalog, then decides
whether to answer, stay silent, or request capabilities. Deterministic code only
executes calls, enforces budgets/authorization, records results, and terminates loops.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Callable, Mapping, Sequence

from .capabilities import (
    CapabilityCall,
    CapabilityRegistry,
    CapabilityResult,
    CapabilitySpec,
)


@dataclass(frozen=True)
class ModelUsage:
    """Exact provider-reported usage for one model invocation."""

    total_tokens: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    provider: str | None = None
    model: str | None = None
    request_id: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("total_tokens", "input_tokens", "output_tokens"):
            value = getattr(self, field_name)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        if (
            self.input_tokens is not None
            and self.output_tokens is not None
            and self.total_tokens < self.input_tokens + self.output_tokens
        ):
            raise ValueError(
                "total_tokens must cover reported input_tokens + output_tokens"
            )
        for field_name in ("provider", "model", "request_id"):
            value = getattr(self, field_name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{field_name} must be non-blank when provided")


@dataclass(frozen=True)
class ModelCallProvenance:
    """Stable provider identity for one billable model response."""

    provider: str
    model: str
    request_id: str

    def __post_init__(self) -> None:
        for field_name in ("provider", "model", "request_id"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be non-blank")


@dataclass(frozen=True)
class ModelDirective:
    """Observable model decision surface; never carries hidden chain-of-thought."""

    capability_calls: tuple[CapabilityCall, ...] = ()
    response: str | None = None
    silence: bool = False
    usage: ModelUsage | None = None
    provenance: ModelCallProvenance | None = None

    def __post_init__(self) -> None:
        terminal_count = int(self.response is not None) + int(self.silence)
        if self.capability_calls and terminal_count:
            raise ValueError("directive cannot request capabilities and terminate simultaneously")
        if not self.capability_calls and terminal_count != 1:
            raise ValueError("directive must either request capabilities, respond, or stay silent")
        if self.response is not None and not self.response.strip():
            raise ValueError("response must be non-blank when provided")
        if self.usage is not None and not isinstance(self.usage, ModelUsage):
            raise TypeError("usage must be ModelUsage when provided")
        if self.provenance is not None and not isinstance(
            self.provenance,
            ModelCallProvenance,
        ):
            raise TypeError("provenance must be ModelCallProvenance when provided")
        if self.usage is not None and self.provenance is not None:
            for field_name, provenance_value in (
                ("provider", self.provenance.provider),
                ("model", self.provenance.model),
                ("request_id", self.provenance.request_id),
            ):
                usage_value = getattr(self.usage, field_name)
                if usage_value is not None and usage_value != provenance_value:
                    raise ValueError(
                        f"usage {field_name} conflicts with model-call provenance"
                    )


@dataclass(frozen=True)
class RuntimeSnapshot:
    user_input: str
    wake_reason: str
    cockpit: Mapping[str, Any]
    capability_catalog: tuple[Mapping[str, Any], ...]
    capability_history: tuple[CapabilityResult, ...]
    round_index: int
    remaining_tool_rounds: int
    model_attempt_id: str | None = None


@dataclass(frozen=True)
class RuntimeTurnResult:
    response: str | None
    silenced: bool
    capability_history: tuple[CapabilityResult, ...]
    model_rounds: int
    termination_reason: str
    model_input_tokens: int | None = None
    model_output_tokens: int | None = None
    model_total_tokens: int | None = None
    model_usage_complete: bool = False


class ModelDispatchNotSubmitted(RuntimeError):
    """Provider adapter knows the request did not cross its submission boundary."""


ModelHandler = Callable[[RuntimeSnapshot], ModelDirective]
ModelUsageRecorder = Callable[[RuntimeSnapshot, ModelDirective], None]
ModelAttemptAdmitter = Callable[[RuntimeSnapshot], str | None]
ModelDispatchRecorder = Callable[[RuntimeSnapshot], None]
ModelResponseRecorder = Callable[[RuntimeSnapshot, ModelDirective], None]
ModelFailureRecorder = Callable[[RuntimeSnapshot, BaseException, bool], None]
SideEffectAuthorizer = Callable[[CapabilitySpec, CapabilityCall, RuntimeSnapshot], bool]


class CognitiveRuntime:
    """Thin Executive Plane that lets the model drive registered capabilities."""

    def __init__(
        self,
        *,
        registry: CapabilityRegistry,
        model_handler: ModelHandler,
        max_tool_rounds: int = 4,
        max_total_capability_calls: int = 12,
        repeated_call_limit: int = 2,
        side_effect_authorizer: SideEffectAuthorizer | None = None,
        model_usage_recorder: ModelUsageRecorder | None = None,
        model_attempt_admitter: ModelAttemptAdmitter | None = None,
        model_dispatch_recorder: ModelDispatchRecorder | None = None,
        model_response_recorder: ModelResponseRecorder | None = None,
        model_failure_recorder: ModelFailureRecorder | None = None,
    ) -> None:
        if max_tool_rounds < 0:
            raise ValueError("max_tool_rounds must be >= 0")
        if max_total_capability_calls < 1:
            raise ValueError("max_total_capability_calls must be >= 1")
        if repeated_call_limit < 1:
            raise ValueError("repeated_call_limit must be >= 1")
        self.registry = registry
        self.model_handler = model_handler
        self.max_tool_rounds = max_tool_rounds
        self.max_total_capability_calls = max_total_capability_calls
        self.repeated_call_limit = repeated_call_limit
        self.side_effect_authorizer = side_effect_authorizer
        self.model_usage_recorder = model_usage_recorder
        self.model_attempt_admitter = model_attempt_admitter
        self.model_dispatch_recorder = model_dispatch_recorder
        self.model_response_recorder = model_response_recorder
        self.model_failure_recorder = model_failure_recorder

    def _snapshot(
        self,
        *,
        user_input: str,
        wake_reason: str,
        cockpit: Mapping[str, Any],
        history: Sequence[CapabilityResult],
        round_index: int,
        effective_model_rounds: int,
        model_round_offset: int,
    ) -> RuntimeSnapshot:
        return RuntimeSnapshot(
            user_input=user_input,
            wake_reason=wake_reason,
            cockpit=dict(cockpit),
            capability_catalog=tuple(self.registry.catalog()),
            capability_history=tuple(history),
            round_index=model_round_offset + round_index,
            remaining_tool_rounds=max(
                0,
                effective_model_rounds - round_index - 1,
            ),
        )

    def run_turn(
        self,
        user_input: str,
        *,
        wake_reason: str = "user_interaction",
        cockpit: Mapping[str, Any] | None = None,
        max_model_rounds: int | None = None,
        model_round_offset: int = 0,
    ) -> RuntimeTurnResult:
        if not isinstance(user_input, str) or not user_input.strip():
            raise ValueError("user_input must be non-blank")
        if (
            isinstance(model_round_offset, bool)
            or not isinstance(model_round_offset, int)
            or model_round_offset < 0
        ):
            raise ValueError("model_round_offset must be a non-negative integer")

        history: list[CapabilityResult] = []
        signature_counts: dict[tuple[str, tuple[tuple[str, str], ...]], int] = {}
        total_calls = 0
        cockpit_data = dict(cockpit or {})
        model_usages: list[ModelUsage] = []
        model_usage_complete = True

        def _result(**kwargs: Any) -> RuntimeTurnResult:
            rounds = int(kwargs["model_rounds"])
            complete = model_usage_complete and len(model_usages) == rounds
            input_complete = complete and all(
                item.input_tokens is not None for item in model_usages
            )
            output_complete = complete and all(
                item.output_tokens is not None for item in model_usages
            )
            return RuntimeTurnResult(
                **kwargs,
                model_input_tokens=(
                    sum(int(item.input_tokens or 0) for item in model_usages)
                    if input_complete
                    else None
                ),
                model_output_tokens=(
                    sum(int(item.output_tokens or 0) for item in model_usages)
                    if output_complete
                    else None
                ),
                model_total_tokens=(
                    sum(item.total_tokens for item in model_usages)
                    if complete
                    else None
                ),
                model_usage_complete=complete,
            )

        normal_model_rounds = self.max_tool_rounds + 1
        if max_model_rounds is None:
            effective_model_rounds = normal_model_rounds
        else:
            if max_model_rounds < 1:
                raise ValueError("max_model_rounds must be >= 1")
            effective_model_rounds = min(
                int(max_model_rounds),
                normal_model_rounds,
            )

        # round_index counts model decisions, not a prescribed thought stage.
        for round_index in range(effective_model_rounds):
            snapshot = self._snapshot(
                user_input=user_input,
                wake_reason=wake_reason,
                cockpit=cockpit_data,
                history=history,
                round_index=round_index,
                effective_model_rounds=effective_model_rounds,
                model_round_offset=model_round_offset,
            )
            if self.model_attempt_admitter is not None:
                attempt_id = self.model_attempt_admitter(snapshot)
                if attempt_id is not None:
                    snapshot = replace(snapshot, model_attempt_id=attempt_id)
            if self.model_dispatch_recorder is not None:
                self.model_dispatch_recorder(snapshot)
            try:
                directive = self.model_handler(snapshot)
                if not isinstance(directive, ModelDirective):
                    raise TypeError("model_handler must return ModelDirective")
            except ModelDispatchNotSubmitted as exc:
                if self.model_failure_recorder is not None:
                    self.model_failure_recorder(snapshot, exc, True)
                raise
            except Exception as exc:
                if self.model_failure_recorder is not None:
                    self.model_failure_recorder(snapshot, exc, False)
                raise
            if self.model_response_recorder is not None:
                self.model_response_recorder(snapshot, directive)
            if directive.usage is None:
                model_usage_complete = False
            else:
                model_usages.append(directive.usage)
            if self.model_usage_recorder is not None:
                # Meter immediately after the provider/model returns. This intentionally
                # happens before tool execution or Wake completion so a later crash
                # cannot erase an already-consumed model call.
                self.model_usage_recorder(snapshot, directive)

            if directive.response is not None:
                return _result(
                    response=directive.response,
                    silenced=False,
                    capability_history=tuple(history),
                    model_rounds=round_index + 1,
                    termination_reason="responded",
                )
            if directive.silence:
                return _result(
                    response=None,
                    silenced=True,
                    capability_history=tuple(history),
                    model_rounds=round_index + 1,
                    termination_reason="silence",
                )

            # At the final allowed model round, new tool requests are not executed.
            # We fail closed rather than silently granting unbounded autonomous loops.
            if round_index >= effective_model_rounds - 1:
                return _result(
                    response=None,
                    silenced=False,
                    capability_history=tuple(history),
                    model_rounds=round_index + 1,
                    termination_reason=(
                        "model_round_budget_exhausted"
                        if effective_model_rounds < normal_model_rounds
                        else "tool_round_budget_exhausted"
                    ),
                )

            for call in directive.capability_calls:
                if total_calls >= self.max_total_capability_calls:
                    return _result(
                        response=None,
                        silenced=False,
                        capability_history=tuple(history),
                        model_rounds=round_index + 1,
                        termination_reason="capability_call_budget_exhausted",
                    )

                signature = call.normalized_signature()
                seen = signature_counts.get(signature, 0)
                if seen >= self.repeated_call_limit:
                    history.append(
                        CapabilityResult(
                            name=call.name,
                            ok=False,
                            error_code="REPEATED_CAPABILITY_CALL_BLOCKED",
                            error_message=(
                                "same capability call repeated beyond runtime loop guard; "
                                "change query path or terminate"
                            ),
                            call_id=call.call_id,
                        )
                    )
                    continue
                signature_counts[signature] = seen + 1

                try:
                    spec = self.registry.get_spec(call.name)
                except KeyError:
                    # Let registry.invoke produce the canonical not-found result.
                    spec = None

                if spec is not None and spec.side_effecting:
                    allowed = (
                        self.side_effect_authorizer is not None
                        and self.side_effect_authorizer(spec, call, snapshot)
                    )
                    if not allowed:
                        history.append(
                            CapabilityResult(
                                name=call.name,
                                ok=False,
                                error_code="CAPABILITY_NOT_AUTHORIZED",
                                error_message=(
                                    "side-effecting capability requires an explicit runtime authorizer"
                                ),
                                call_id=call.call_id,
                            )
                        )
                        total_calls += 1
                        continue

                history.append(self.registry.invoke(call))
                total_calls += 1

        raise AssertionError("unreachable runtime loop state")
