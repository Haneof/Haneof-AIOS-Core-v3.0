"""The prompt registry: one lookup table for every AI job AIOS performs.

Why a registry at all. The cockpit shipped the same defect three times: a block
was assembled, the renderer silently dropped it, and nobody noticed until a
conversation came back amnesiac. Each fix addressed the field somebody happened
to look at. The missing thing was never a patch, it was a guardrail.

So prompts are registered, not scattered. ``PROMPT_REGISTRY`` must contain an
entry for every ``TaskKind``; a task added to the enum without a prompt fails
``every_task_has_a_registered_prompt`` at the moment it is introduced rather than
three turns later. Rendering goes through one door (``render_task_prompt``) so the
constitutional prefix cannot be forgotten by a caller.
"""

from __future__ import annotations

from typing import Mapping

from .constitutional_prefix import (
    assert_prefix_present,
    constitutional_prefix,
    is_constitutional_prefix,
)
from .contracts import (
    DimensionProfile,
    PromptRenderParams,
    PromptSpec,
    TaskKind,
    TaskRuntimeConfig,
)
from .task_runtime import DEFAULT_RUNTIME, resolve_model, resolve_runtime
from .templates_structured import AnnotatePrompt, ExtractPrompt, GatePrompt
from .templates_text import DialoguePrompt, DigestPrompt, SummarizePrompt

PROMPT_REGISTRY: dict[TaskKind, PromptSpec] = {
    TaskKind.ANNOTATE: AnnotatePrompt(),
    TaskKind.GATE: GatePrompt(),
    TaskKind.EXTRACT: ExtractPrompt(),
    TaskKind.SUMMARIZE: SummarizePrompt(),
    TaskKind.DIGEST: DigestPrompt(),
    TaskKind.DIALOGUE: DialoguePrompt(),
}


def get_prompt(task: TaskKind) -> PromptSpec:
    try:
        return PROMPT_REGISTRY[TaskKind(task)]
    except KeyError as exc:  # pragma: no cover - guarded by the registry test
        raise ValueError(f"no prompt registered for task: {task}") from exc


def render_task_prompt(
    task: TaskKind,
    *,
    params: PromptRenderParams | None = None,
    prefix: str | None = None,
) -> str:
    """The single door every caller uses to build a task prompt.

    The prefix is supplied here, not by the caller, so "someone forgot the
    invariant block" cannot happen silently — a task that declares
    ``requires_constitutional_prefix`` raises instead of rendering.

    The ``prefix`` argument is therefore not a free-form override. A caller that
    passes one must pass the canonical text: accepting arbitrary content would
    keep the marker check satisfied while letting a caller swap the rules behind
    it, which is the drift this door exists to prevent. Pin a version through
    ``constitutional_prefix(version=...)`` instead.
    """

    spec = get_prompt(task)
    if prefix is None:
        chosen = constitutional_prefix()
    else:
        chosen = prefix
        if not is_constitutional_prefix(chosen):
            raise ValueError(
                "caller-supplied prefix must be the canonical constitutional "
                "prefix; a task may not render under a different one"
            )
    rendered = spec.render(params or PromptRenderParams(), prefix=chosen)
    if spec.requires_constitutional_prefix:
        assert_prefix_present(rendered)
    return rendered


def render_task_prompt_from_values(
    task: TaskKind,
    **values: object,
) -> str:
    """Convenience wrapper: build PromptRenderParams from loose keyword values.

    Unknown keys raise rather than being swallowed into ``extra`` — a typo in a
    parameter name must not turn into a silently incomplete prompt.
    """

    known = set(PromptRenderParams.__dataclass_fields__)
    unknown = sorted(set(values) - known)
    if unknown:
        raise ValueError(
            f"unknown prompt parameters for {task}: {unknown}; "
            f"known: {sorted(known)}"
        )
    return render_task_prompt(task, params=PromptRenderParams(**values))  # type: ignore[arg-type]


def task_runtime(task: TaskKind, **overrides: object) -> TaskRuntimeConfig:
    return resolve_runtime(TaskKind(task), overrides=overrides or None)


def task_model(task: TaskKind, *, tier_models: Mapping[str, str] | None = None) -> str:
    return resolve_model(TaskKind(task), tier_models=tier_models)


__all__ = [
    "DEFAULT_RUNTIME",
    "PROMPT_REGISTRY",
    "DimensionProfile",
    "PromptRenderParams",
    "PromptSpec",
    "TaskKind",
    "TaskRuntimeConfig",
    "get_prompt",
    "render_task_prompt",
    "render_task_prompt_from_values",
    "task_model",
    "task_runtime",
]
