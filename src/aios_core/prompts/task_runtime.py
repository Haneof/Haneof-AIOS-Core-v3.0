"""Per-task runtime configuration: model routing, budget, timeout, failure policy.

Why this module exists. Before it, every knob was a process-global ``AIOS_LIVE_*``
environment variable. That forces one model, one temperature and one timeout on
six jobs with nothing in common: labelling 30 records needs a cheap, cold,
short, deterministic JSON answer, while a cross-dimension digest needs a model
that can hold nine summaries in mind and write 3000 tokens. Sharing the knobs
meant paying frontier prices for the cheap jobs and — the part that actually
hurt — inheriting the expensive job's timeout budget on the cheap ones, so a
slow label batch stalled the whole pipeline.

Task-scoped config also makes failure policy a per-task decision instead of a
global retry: a failed gate must keep everything, a failed digest must not stop
the other dimensions, a failed dialogue must answer without the missing context.

Values here are measured defaults, not guesses; the provenance is recorded next
to each one so nobody "cleans up" a number that is holding something up.
"""

from __future__ import annotations

from dataclasses import fields, replace
from typing import Any, Mapping

from .contracts import FailurePolicy, ModelTier, TaskKind, TaskRuntimeConfig

__all__ = [
    "DEFAULT_RUNTIME",
    "MODEL_TIER_ROUTES",
    "resolve_runtime",
    "resolve_model",
]


DEFAULT_RUNTIME: dict[TaskKind, TaskRuntimeConfig] = {
    # Short structured JSON over a batch. Determinism beats capability: these
    # three run at 0.0-0.2 because a label that flips between runs is worse
    # than a slightly dumber label — the same batch gets re-labelled later.
    TaskKind.ANNOTATE: TaskRuntimeConfig(
        task=TaskKind.ANNOTATE,
        model_tier=ModelTier.CHEAP,
        temperature=0.0,
        # 3000 is measured, not estimated. The first default was 1200 on the
        # theory that "20 labels is a short JSON answer" — a real run returned
        # an empty body three times in a row: the reasoning model spent the
        # budget on thinking tokens and hit finish_reason before writing JSON.
        # The labels are short; the *thinking* about them is not. 2500 was the
        # smallest value that produced output, 3000 leaves headroom for a full
        # 40-record batch. Do not "optimise" this back down without re-running
        # against a real endpoint.
        max_output_tokens=3000,
        timeout_seconds=120.0,
        max_retries=2,
        # A failed batch simply is not labelled this cycle; it is retried on the
        # next one. Nothing is lost, so nothing needs a special policy.
        failure_policy=FailurePolicy.SKIP_RETRY_NEXT,
    ),
    TaskKind.GATE: TaskRuntimeConfig(
        task=TaskKind.GATE,
        model_tier=ModelTier.CHEAP,
        temperature=0.0,
        # Same reasoning-token trap as ANNOTATE. 2500 is the *smallest* value
        # that produced output at all on a real endpoint, i.e. it is a cliff
        # edge, not a safe setting — the candidate list is shorter than an
        # annotate batch but not reliably short, and the gate is the one call
        # where an empty body costs a whole cycle. Matched to ANNOTATE.
        max_output_tokens=3000,
        timeout_seconds=120.0,
        max_retries=2,
        # The one irreversible operation. If the gate cannot decide, the answer
        # must be "keep" — a failed call is never allowed to delete.
        failure_policy=FailurePolicy.CONSERVATIVE_KEEP,
    ),
    TaskKind.EXTRACT: TaskRuntimeConfig(
        task=TaskKind.EXTRACT,
        model_tier=ModelTier.CHEAP,
        temperature=0.0,
        # 2500, not 2000. The old value repeated the exact misjudgement behind
        # ANNOTATE's 1200: "one turn yields a couple of facts, so the answer is
        # short". The answer is short; the thinking is not. Experiments measured
        # 2500 as the smallest budget that produced output at all on this
        # endpoint, and 2000 sits under it — same empty-body failure, quieter,
        # because one missing fact looks like a turn that had nothing to extract.
        max_output_tokens=2500,
        timeout_seconds=120.0,
        max_retries=2,
        failure_policy=FailurePolicy.SKIP_RETRY_NEXT,
    ),
    TaskKind.SUMMARIZE: TaskRuntimeConfig(
        task=TaskKind.SUMMARIZE,
        model_tier=ModelTier.STANDARD,
        temperature=0.3,
        # 4000 is a measured sweet spot, not a round number. 2500 and 4500 both
        # came back with empty bodies because the reasoning model spent the whole
        # budget on thinking tokens and hit finish_reason before writing prose;
        # 8000 tripped the gateway's own 504. 4000 produces consistently.
        max_output_tokens=4000,
        timeout_seconds=300.0,
        max_retries=2,
        failure_policy=FailurePolicy.FAIL_SOFT,
    ),
    TaskKind.DIGEST: TaskRuntimeConfig(
        task=TaskKind.DIGEST,
        model_tier=ModelTier.STANDARD,
        temperature=0.3,
        # Same 4000 reasoning-token cliff as SUMMARIZE — a digest merges nine
        # summaries, so it is the job most exposed to it.
        max_output_tokens=4000,
        timeout_seconds=300.0,
        max_retries=2,
        # One dimension failing must not stop the other dimensions' digests.
        failure_policy=FailurePolicy.FAIL_SOFT,
    ),
    TaskKind.DIALOGUE: TaskRuntimeConfig(
        task=TaskKind.DIALOGUE,
        model_tier=ModelTier.STRONG,
        # Warm on purpose: this is the only task whose output is read by a human.
        temperature=0.6,
        max_output_tokens=4096,
        timeout_seconds=300.0,
        max_retries=1,
        # Missing context degrades the answer; it never justifies silence.
        failure_policy=FailurePolicy.DEGRADE,
    ),
}


MODEL_TIER_ROUTES: dict[ModelTier, str] = {
    ModelTier.CHEAP: "cheap-tier-default",
    ModelTier.STANDARD: "standard-tier-default",
    ModelTier.STRONG: "strong-tier-default",
}
"""Tier -> concrete model id.

Placeholders on purpose. A tier is a *capability* claim ("this job needs short
deterministic JSON"), while a model id is a vendor fact that changes on someone
else's schedule. Hard-coding a vendor id here would silently re-price every task
the day it is deprecated, and reading an env var here would put process-global
state back into the thing this module exists to replace. The deployment supplies
the real mapping via ``resolve_model(..., tier_models=...)``.
"""

_RUNTIME_FIELDS: frozenset[str] = frozenset(field.name for field in fields(TaskRuntimeConfig))


def resolve_runtime(
    task: TaskKind, *, overrides: Mapping[str, Any] | None = None
) -> TaskRuntimeConfig:
    """Return the config for ``task``, with selected fields overridden.

    Override keys are ``TaskRuntimeConfig`` field names. Unknown keys raise
    instead of being ignored: a typo like ``max_tokens`` silently falling back to
    the default is the exact class of bug this module replaced, where a renamed
    env var kept the old budget without anyone noticing.

    The result goes back through ``TaskRuntimeConfig``'s own validation, so an
    override cannot smuggle in a negative timeout or a sub-minimum token budget.
    """

    base = DEFAULT_RUNTIME[task]
    if not overrides:
        return base
    unknown = sorted(set(overrides) - _RUNTIME_FIELDS)
    if unknown:
        raise ValueError(
            f"unknown TaskRuntimeConfig field(s) for {task}: {', '.join(unknown)}"
        )
    return replace(base, **dict(overrides))


def resolve_model(
    task: TaskKind, *, tier_models: Mapping[ModelTier, str] | None = None
) -> str:
    """Return the model id ``task`` should use.

    Routing goes through the tier, never through the task: a task says what it
    needs (cheap/short/deterministic), the deployment says which model that is
    today. A task that named its model directly would freeze a vendor choice into
    the prompt layer.
    """

    routes: dict[ModelTier, str] = dict(MODEL_TIER_ROUTES)
    if tier_models:
        routes.update(tier_models)
    tier = resolve_runtime(task).model_tier
    if tier not in routes:
        raise KeyError(f"no model route configured for tier {tier!r} (task {task})")
    return routes[tier]
