"""Execute a task prompt and honour its declared failure semantics.

Why this file exists. ``FailurePolicy`` is otherwise a promise written in a
comment: CONSERVATIVE_KEEP claims "a failed gate never deletes anything", but
without an executor that sentence lives only in the enum's docstring and in a
test asserting the enum exists. A policy that no code implements is a policy that
will be re-derived ad hoc by whoever wires the caller — which is how two callers
end up with two different ideas of what "the gate failed" means.

So the four policies are implemented here, once:

    SKIP_RETRY_NEXT     -> not labelled this cycle; retried later, nothing lost
    CONSERVATIVE_KEEP   -> the answer under failure is "keep everything"
    FAIL_SOFT           -> one task down, its neighbours still run
    DEGRADE             -> answer anyway, from whatever survived

Structured tasks (ANNOTATE/GATE/EXTRACT) additionally have to survive the two
ways a reasoning endpoint fails to give you JSON: it returns prose around the
array anyway, or it returns nothing at all because thinking consumed the budget.
The first is parsed; the second is retried before the policy is consulted,
because a retry is cheaper than losing a cycle.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from .constitutional_prefix import constitutional_prefix
from .contracts import FailurePolicy, PromptRenderParams, TaskKind
from .registry import get_prompt, task_runtime

TaskCaller = Callable[[str, Any], str]
"""Callable taking ``(prompt, runtime)`` and returning raw model text.

Deliberately narrow: the executor owns prompt construction and failure policy,
so the caller owns only transport. A caller that also built prompts would put
the rendering back outside the registry, which is the hole this module is
supposed to close.
"""

STRUCTURED_TASKS: frozenset[TaskKind] = frozenset(
    {TaskKind.ANNOTATE, TaskKind.GATE, TaskKind.EXTRACT}
)

_JSON_BLOCK = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


@dataclass(frozen=True, slots=True)
class TaskResult:
    task: TaskKind
    ok: bool
    text: str = ""
    payload: Any | None = None
    attempts: int = 0
    error: str | None = None
    failure_policy: FailurePolicy = FailurePolicy.FAIL_SOFT
    # True when the irreversibility guard fired: the task did not succeed, so
    # the only safe outcome is "change nothing". Callers must honour this rather
    # than treating ``ok=False`` as "no opinion".
    conservative_keep: bool = False
    skipped_for_retry: bool = False
    elapsed_ms: int = 0


@dataclass(frozen=True, slots=True)
class BatchTaskResult:
    """Outcome of running one task across several independent inputs."""

    task: TaskKind
    results: tuple[TaskResult, ...] = ()
    failures: tuple[TaskResult, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return all(item.ok or item.skipped_for_retry for item in self.results)


def _extract_json(text: str) -> Any | None:
    """Pull JSON out of a model reply, tolerating fences and surrounding prose."""

    stripped = (text or "").strip()
    if not stripped:
        return None
    candidates: list[str] = [stripped]
    for match in _JSON_BLOCK.finditer(stripped):
        candidates.append(match.group(1).strip())
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except ValueError:
            continue
    # Last resort: the reply may carry a bare array/object after some preamble.
    for opener, closer in (("[", "]"), ("{", "}")):
        start = stripped.find(opener)
        end = stripped.rfind(closer)
        if start >= 0 and end > start:
            snippet = stripped[start : end + 1]
            try:
                return json.loads(snippet)
            except ValueError:
                continue
    return None


def run_task(
    task: TaskKind,
    *,
    caller: TaskCaller,
    params: PromptRenderParams | None = None,
    overrides: Mapping[str, Any] | None = None,
    clock: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
) -> TaskResult:
    """Render the task prompt, call the model, and apply the failure policy.

    Retries are bounded by the task's ``max_retries`` and never exceed them; a
    结构化 task that returns unparseable text is retried the same way an empty
    reply is, because both mean "no usable output yet".
    """

    kind = TaskKind(task)
    runtime = task_runtime(kind, **(overrides or {}))
    spec = get_prompt(kind)
    prompt = spec.render(params or PromptRenderParams(), prefix=constitutional_prefix())

    started = clock()
    attempts = 0
    last_error: str | None = None
    text = ""

    for attempt in range(1, runtime.max_retries + 2):
        attempts = attempt
        try:
            text = caller(prompt, runtime) or ""
        except Exception as exc:  # noqa: BLE001 - transport failure is data, not a crash
            last_error = f"{type(exc).__name__}: {exc}"
            _backoff(attempt, sleeper)
            continue

        if not text.strip():
            # Empty body almost always means thinking consumed the budget.
            last_error = "empty response body (thinking exhausted the budget?)"
            _backoff(attempt, sleeper)
            continue

        if kind in STRUCTURED_TASKS:
            payload = _extract_json(text)
            if payload is None:
                last_error = "response was not parseable JSON"
                _backoff(attempt, sleeper)
                continue
            return TaskResult(
                task=kind,
                ok=True,
                text=text,
                payload=payload,
                attempts=attempts,
                failure_policy=runtime.failure_policy,
                elapsed_ms=int((clock() - started) * 1000),
            )

        return TaskResult(
            task=kind,
            ok=True,
            text=text,
            payload=None,
            attempts=attempts,
            failure_policy=runtime.failure_policy,
            elapsed_ms=int((clock() - started) * 1000),
        )

    return _apply_failure_policy(
        kind,
        attempts=attempts,
        text=text,
        error=last_error or "call failed",
        policy=runtime.failure_policy,
        elapsed_ms=int((clock() - started) * 1000),
    )


def _backoff(attempt: int, sleeper: Callable[[float], None]) -> None:
    """Short, bounded pause. Retries that hammer a flailing endpoint make it worse."""

    if attempt <= 1:
        return
    sleeper(min(2.0 ** (attempt - 1), 8.0))


def _apply_failure_policy(
    task: TaskKind,
    *,
    attempts: int,
    text: str,
    error: str,
    policy: FailurePolicy,
    elapsed_ms: int,
) -> TaskResult:
    if policy is FailurePolicy.CONSERVATIVE_KEEP:
        # Nothing may be deleted on the strength of a call that did not succeed.
        return TaskResult(
            task=task,
            ok=False,
            text=text,
            payload=[],
            attempts=attempts,
            error=error,
            failure_policy=policy,
            conservative_keep=True,
            elapsed_ms=elapsed_ms,
        )
    if policy is FailurePolicy.SKIP_RETRY_NEXT:
        return TaskResult(
            task=task,
            ok=False,
            text=text,
            payload=None,
            attempts=attempts,
            error=error,
            failure_policy=policy,
            skipped_for_retry=True,
            elapsed_ms=elapsed_ms,
        )
    if policy is FailurePolicy.DEGRADE:
        # Answer from whatever survived; silence is the one thing not permitted.
        return TaskResult(
            task=task,
            ok=False,
            text=text.strip(),
            payload=None,
            attempts=attempts,
            error=error,
            failure_policy=policy,
            elapsed_ms=elapsed_ms,
        )
    return TaskResult(
        task=task,
        ok=False,
        text=text,
        payload=None,
        attempts=attempts,
        error=error,
        failure_policy=policy,
        elapsed_ms=elapsed_ms,
    )


def run_batch(
    task: TaskKind,
    *,
    caller: TaskCaller,
    params_list: Sequence[PromptRenderParams],
    overrides: Mapping[str, Any] | None = None,
    clock: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
) -> BatchTaskResult:
    """Run one task over several inputs, letting survivors through.

    This is FAIL_SOFT realised at the batch level: one chunk of records failing
    must not cost the user the labels for the other chunks, which is what turned
    a single gateway timeout into an entire lost cleaning cycle.
    """

    results = tuple(
        run_task(
            task,
            caller=caller,
            params=params,
            overrides=overrides,
            clock=clock,
            sleeper=sleeper,
        )
        for params in params_list
    )
    return BatchTaskResult(
        task=TaskKind(task),
        results=results,
        failures=tuple(item for item in results if not item.ok),
    )
