"""Runtime state for the fused AIOS v3.0 execution plane.

This package starts with conversation continuity state. Cognitive execution and
context control are added only after the durable world + index gates are green.
"""

from .conversation_state import *
from .conversation_timeline import *
from .budget_gate import BackgroundBudgetDecision, BackgroundBudgetGate
from .background_attempt import (
    BackgroundModelAttempt,
    BackgroundModelAttemptBlocked,
    BackgroundModelAttemptStore,
    BackgroundModelExecutionInDoubt,
    BackgroundModelResponsePending,
)
from .metering import MeteringRecord, ModelMeteringLedger

from .capabilities import (
    CapabilityCall,
    CapabilityKind,
    CapabilityRegistry,
    CapabilityResult,
    CapabilitySpec,
)
from .cognitive_runtime import (
    CognitiveRuntime,
    ModelCallProvenance,
    ModelDirective,
    ModelDispatchNotSubmitted,
    ModelUsage,
    RuntimeSnapshot,
    RuntimeTurnResult,
)

from .turn_runtime import FusedTurnResult, FusedTurnRuntime, WakeDispatchRunResult

from .turn_execution import (
    TurnAlreadyCompleted, TurnExecutionInDoubt, TurnExecutionRefused, TurnInputConflict,
)
