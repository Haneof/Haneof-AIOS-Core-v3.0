"""Task-scoped prompt construction for AIOS v3.0.

Separation here is by contract, not by prompt text: a task is identified by the
shape of its input and the shape of its required output. Dimension, scale and
time window are parameters read from the world, never baked into the prompt.
"""

from .constitutional_prefix import (
    CONSTITUTIONAL_PREFIX,
    CONSTITUTIONAL_PREFIX_VERSION,
    assert_prefix_present,
    constitutional_prefix,
    is_constitutional_prefix,
)
from .contracts import (
    DimensionProfile,
    FailurePolicy,
    ModelTier,
    PromptRenderParams,
    PromptSpec,
    TaskKind,
    TaskRuntimeConfig,
    render_records,
    render_sources,
)
from .executor import (
    STRUCTURED_TASKS,
    BatchTaskResult,
    TaskCaller,
    TaskResult,
    run_batch,
    run_task,
)
from .registry import (
    DEFAULT_RUNTIME,
    PROMPT_REGISTRY,
    get_prompt,
    render_task_prompt,
    render_task_prompt_from_values,
    task_model,
    task_runtime,
)
from .task_runtime import (
    MODEL_TIER_ROUTES,
    resolve_model,
    resolve_runtime,
)
from .templates_structured import AnnotatePrompt, ExtractPrompt, GatePrompt
from .templates_text import DialoguePrompt, DigestPrompt, SummarizePrompt

__all__ = [
    "BatchTaskResult",
    "CONSTITUTIONAL_PREFIX",
    "CONSTITUTIONAL_PREFIX_VERSION",
    "DEFAULT_RUNTIME",
    "MODEL_TIER_ROUTES",
    "PROMPT_REGISTRY",
    "STRUCTURED_TASKS",
    "AnnotatePrompt",
    "DialoguePrompt",
    "DigestPrompt",
    "DimensionProfile",
    "ExtractPrompt",
    "FailurePolicy",
    "GatePrompt",
    "ModelTier",
    "PromptRenderParams",
    "PromptSpec",
    "SummarizePrompt",
    "TaskCaller",
    "TaskKind",
    "TaskResult",
    "TaskRuntimeConfig",
    "assert_prefix_present",
    "constitutional_prefix",
    "get_prompt",
    "is_constitutional_prefix",
    "render_records",
    "render_sources",
    "render_task_prompt",
    "render_task_prompt_from_values",
    "resolve_model",
    "resolve_runtime",
    "run_batch",
    "run_task",
    "task_model",
    "task_runtime",
]
