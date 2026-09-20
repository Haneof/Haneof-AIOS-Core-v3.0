"""Conversation facts -> unified AIOS world.

Raw user/assistant text is durable world fact. The runtime conversation-state tables
are only working projections/checkpoints; they are not the source of truth.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

from aios_core.contracts.enums import ErrorCode, SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent, as_utc
from aios_core.storage.idempotency import canonical_json_dumps
from aios_core.storage.sqlite_store import SQLiteWorldStore, StoreError

INTERACTION_DIMENSION = "dim:user_ai_interaction"


@dataclass(frozen=True, slots=True)
class ConversationCommit:
    world_revision: int
    user_observation_id: str
    assistant_observation_id: str
    idempotent_replay: bool
    user_world_revision: int | None = None
    assistant_world_revision: int | None = None


@dataclass(frozen=True, slots=True)
class ConversationMessageCommit:
    world_revision: int
    observation_id: str
    role: str
    idempotent_replay: bool


def _stable_suffix(*parts: object) -> str:
    payload = canonical_json_dumps(list(parts))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


class ConversationIngestor:
    """Persist raw user/assistant interaction facts into the unified world ledger."""

    def __init__(self, store: SQLiteWorldStore, *, subject_id: str = "user_1") -> None:
        if not isinstance(subject_id, str) or not subject_id.strip():
            raise ValueError("subject_id must not be blank")
        self.store = store
        self.subject_id = subject_id.strip()

    def _turn_identity(self, session_id: str, turn_index: int) -> tuple[str, str, str]:
        turn_key = _stable_suffix(self.subject_id, session_id, turn_index)
        user_id = (
            f"obs_conv_user_"
            f"{_stable_suffix(self.subject_id, session_id, turn_index, 'user')}"
        )
        assistant_id = (
            f"obs_conv_ai_"
            f"{_stable_suffix(self.subject_id, session_id, turn_index, 'assistant')}"
        )
        return turn_key, user_id, assistant_id

    @staticmethod
    def _expected_revision_for_retry(
        store: SQLiteWorldStore,
        operation_id: str,
    ) -> int:
        expected = int(store.current_world_revision())
        try:
            previous = store.operation_record(operation_id)
        except StoreError as exc:
            if exc.code == ErrorCode.NOT_FOUND:
                previous = None
            else:
                raise
        if previous is not None:
            expected = int(previous["expected_world_revision"])
        return expected

    def commit_user_input(
        self,
        *,
        session_id: str,
        turn_index: int,
        user_text: str,
        occurred_at: datetime,
        recorded_at: datetime | None = None,
    ) -> ConversationMessageCommit:
        if not session_id.strip():
            raise ValueError("session_id must not be blank")
        session_id = session_id.strip()
        if turn_index < 1:
            raise ValueError("turn_index must be >= 1")
        occurred = as_utc(occurred_at, "occurred_at")
        recorded = as_utc(recorded_at or occurred_at, "recorded_at")
        if recorded < occurred:
            raise ValueError("recorded_at must be >= occurred_at")

        turn_key, user_id, _assistant_id = self._turn_identity(
            session_id,
            turn_index,
        )
        metadata = {
            "dimension": INTERACTION_DIMENSION,
            "session_id": session_id,
            "turn_index": turn_index,
            "turn_key": turn_key,
            "role": "user",
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
            raw_locator=f"conversation://{self.subject_id}/{session_id}/{turn_index}/user",
            metadata=metadata,
        )
        operation_id = f"op_conv_user_{turn_key}"
        result = self.store.commit(
            [user_obs],
            OperationRequest(
                operation_id=operation_id,
                session_id=session_id,
                operation_name="conversation.commit_user_input",
                arguments={"turn_index": turn_index},
                expected_world_revision=self._expected_revision_for_retry(
                    self.store,
                    operation_id,
                ),
                reason="persist current user input before model inference",
                idempotency_key=(
                    f"conversation-user:{self.subject_id}:{session_id}:{turn_index}"
                ),
                source_class=SourceClass.USER,
            ),
        )
        return ConversationMessageCommit(
            world_revision=result.world_revision,
            observation_id=user_id,
            role="user",
            idempotent_replay=result.idempotent_replay,
        )

    def commit_assistant_output(
        self,
        *,
        session_id: str,
        turn_index: int,
        assistant_text: str,
        occurred_at: datetime,
        recorded_at: datetime | None = None,
    ) -> ConversationMessageCommit:
        if not session_id.strip():
            raise ValueError("session_id must not be blank")
        session_id = session_id.strip()
        if turn_index < 1:
            raise ValueError("turn_index must be >= 1")
        occurred = as_utc(occurred_at, "occurred_at")
        recorded = as_utc(recorded_at or occurred_at, "recorded_at")
        if recorded < occurred:
            raise ValueError("recorded_at must be >= occurred_at")

        turn_key, _user_id, assistant_id = self._turn_identity(
            session_id,
            turn_index,
        )
        metadata = {
            "dimension": INTERACTION_DIMENSION,
            "session_id": session_id,
            "turn_index": turn_index,
            "turn_key": turn_key,
            "role": "assistant",
        }
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
            raw_locator=f"conversation://{self.subject_id}/{session_id}/{turn_index}/assistant",
            metadata=metadata,
        )
        operation_id = f"op_conv_ai_{turn_key}"
        result = self.store.commit(
            [assistant_obs],
            OperationRequest(
                operation_id=operation_id,
                session_id=session_id,
                operation_name="conversation.commit_assistant_output",
                arguments={"turn_index": turn_index},
                expected_world_revision=self._expected_revision_for_retry(
                    self.store,
                    operation_id,
                ),
                reason="persist raw assistant output after model inference",
                idempotency_key=(
                    f"conversation-assistant:{self.subject_id}:{session_id}:{turn_index}"
                ),
                source_class=SourceClass.AI_COGNITION,
            ),
        )
        return ConversationMessageCommit(
            world_revision=result.world_revision,
            observation_id=assistant_id,
            role="assistant",
            idempotent_replay=result.idempotent_replay,
        )

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
        session_id = session_id.strip()
        if turn_index < 1:
            raise ValueError("turn_index must be >= 1")

        occurred = as_utc(occurred_at, "occurred_at")
        recorded = as_utc(recorded_at or occurred_at, "recorded_at")
        if recorded < occurred:
            raise ValueError("recorded_at must be >= occurred_at")

        turn_key, user_id, assistant_id = self._turn_identity(
            session_id,
            turn_index,
        )

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
            raw_locator=f"conversation://{self.subject_id}/{session_id}/{turn_index}/user",
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
            raw_locator=f"conversation://{self.subject_id}/{session_id}/{turn_index}/assistant",
            metadata={**common_metadata, "role": "assistant"},
        )

        operation_id = f"op_conv_{turn_key}"
        expected_world_revision = self.store.current_world_revision()
        try:
            previous = self.store.operation_record(operation_id)
        except StoreError as exc:
            if exc.code == ErrorCode.NOT_FOUND:
                previous = None
            else:
                raise
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
            idempotency_key=(
                f"conversation:{self.subject_id}:{session_id}:{turn_index}"
            ),
            source_class=SourceClass.USER,
        )
        result = self.store.commit([user_obs, assistant_obs], op)
        return ConversationCommit(
            world_revision=result.world_revision,
            user_observation_id=user_id,
            assistant_observation_id=assistant_id,
            idempotent_replay=result.idempotent_replay,
            user_world_revision=result.world_revision,
            assistant_world_revision=result.world_revision,
        )
