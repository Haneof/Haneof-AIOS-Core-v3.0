"""Conversation facts -> unified AIOS world.

Raw user/assistant text is durable world fact. The runtime conversation-state tables
are only working projections/checkpoints; they are not the source of truth.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

from aios_core.contracts.enums import SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent, as_utc
from aios_core.storage.sqlite_store import SQLiteWorldStore

INTERACTION_DIMENSION = "dim:user_ai_interaction"


@dataclass(frozen=True, slots=True)
class ConversationCommit:
    world_revision: int
    user_observation_id: str
    assistant_observation_id: str
    idempotent_replay: bool


def _stable_suffix(*parts: object) -> str:
    payload = "|".join(str(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


class ConversationIngestor:
    """Atomically commit one user/assistant turn into the unified world ledger."""

    def __init__(self, store: SQLiteWorldStore, *, subject_id: str = "user_1") -> None:
        self.store = store
        self.subject_id = subject_id

    def commit_turn(
        self,
        *,
        session_id: str,
        turn_index: int,
        user_text: str,
        assistant_text: str,
        occurred_at: datetime,
        recorded_at: datetime | None = None,
    ) -> ConversationCommit:
        if not session_id.strip():
            raise ValueError("session_id must not be blank")
        if turn_index < 1:
            raise ValueError("turn_index must be >= 1")

        occurred = as_utc(occurred_at, "occurred_at")
        recorded = as_utc(recorded_at or occurred_at, "recorded_at")
        if recorded < occurred:
            raise ValueError("recorded_at must be >= occurred_at")

        turn_key = _stable_suffix(session_id, turn_index)
        user_id = f"obs_conv_user_{_stable_suffix(session_id, turn_index, 'user')}"
        assistant_id = f"obs_conv_ai_{_stable_suffix(session_id, turn_index, 'assistant')}"

        common_metadata = {
            "dimension": INTERACTION_DIMENSION,
            "session_id": session_id,
            "turn_index": turn_index,
            "turn_key": turn_key,
        }

        user_obs = Observation(
            object_id=user_id,
            subject_id=self.subject_id,
            occurred=TemporalExtent.point(occurred),
            learned_at=recorded,
            recorded_at=recorded,
            created_by="conversation_ingest:user",
            source_kind="user_ai_interaction",
            modality="text",
            value=user_text,
            raw_locator=f"conversation://{session_id}/{turn_index}/user",
            metadata={**common_metadata, "role": "user"},
        )
        assistant_obs = Observation(
            object_id=assistant_id,
            subject_id=self.subject_id,
            occurred=TemporalExtent.point(occurred),
            learned_at=recorded,
            recorded_at=recorded,
            created_by="conversation_ingest:assistant",
            source_kind="user_ai_interaction",
            modality="text",
            value=assistant_text,
            raw_locator=f"conversation://{session_id}/{turn_index}/assistant",
            metadata={**common_metadata, "role": "assistant"},
        )

        operation_id = f"op_conv_{turn_key}"
        expected_world_revision = self.store.current_world_revision()
        try:
            previous = self.store.operation_record(operation_id)
        except Exception:
            previous = None
        if previous is not None:
            # Exact retries must replay the original request identity. Reusing the
            # original expected revision lets the store's idempotency fingerprint
            # distinguish a true retry from mutated content in the same turn slot.
            expected_world_revision = int(previous["expected_world_revision"])

        op = OperationRequest(
            operation_id=operation_id,
            session_id=session_id,
            operation_name="conversation.commit_turn",
            arguments={"turn_index": turn_index},
            expected_world_revision=expected_world_revision,
            reason="persist raw user/AI interaction as unified-world fact",
            idempotency_key=f"conversation:{session_id}:{turn_index}",
            source_class=SourceClass.USER,
        )
        result = self.store.commit([user_obs, assistant_obs], op)
        return ConversationCommit(
            world_revision=result.world_revision,
            user_observation_id=user_id,
            assistant_observation_id=assistant_id,
            idempotent_replay=result.idempotent_replay,
        )
