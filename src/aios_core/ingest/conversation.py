"""Conversation facts -> unified AIOS world.

Raw user/assistant text is durable world fact. The runtime conversation-state tables
are only working projections/checkpoints; they are not the source of truth.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from aios_core.contracts.enums import ErrorCode, ObjectType, SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
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

    def _wake_delivery_identity(self, wake_id: str) -> tuple[str, str]:
        if not isinstance(wake_id, str) or not wake_id.strip():
            raise ValueError("wake_id must not be blank")
        wake_id = wake_id.strip()
        delivery_key = _stable_suffix(
            self.subject_id,
            wake_id,
            "wake_user_delivery",
        )
        return delivery_key, f"obs_wake_ai_{delivery_key}"

    def assistant_delivery_payload(self, wake_id: str) -> dict[str, Any] | None:
        """Return the durable proactive assistant delivery for one logical Wake."""

        _delivery_key, assistant_id = self._wake_delivery_identity(wake_id)
        try:
            payload = self.store.get_payload(assistant_id)
        except StoreError as exc:
            if exc.code == ErrorCode.NOT_FOUND:
                return None
            raise
        metadata = payload.get("metadata")
        if not isinstance(metadata, Mapping):
            raise ValueError("wake delivery Observation metadata is invalid")
        if payload.get("object_type") != ObjectType.OBSERVATION.value:
            raise ValueError("wake delivery identity points to a non-Observation")
        if payload.get("subject_id") != self.subject_id:
            raise ValueError("wake delivery Observation crosses subject scope")
        if payload.get("source_kind") != "user_ai_interaction":
            raise ValueError("wake delivery Observation has invalid source_kind")
        if metadata.get("role") != "assistant":
            raise ValueError("wake delivery Observation has invalid role")
        if metadata.get("interaction_kind") != "wake_delivery":
            raise ValueError("wake delivery Observation has invalid interaction_kind")
        if metadata.get("origin_wake_id") != wake_id.strip():
            raise ValueError("wake delivery Observation has invalid Wake provenance")
        expected_key, _assistant_id = self._wake_delivery_identity(wake_id)
        if metadata.get("delivery_key") != expected_key:
            raise ValueError("wake delivery Observation has invalid delivery identity")
        raw_origin_ref = metadata.get("origin_wake_ref")
        if not isinstance(raw_origin_ref, Mapping):
            raise ValueError("wake delivery Observation lacks exact Wake provenance")
        origin_ref = ObjectRef.model_validate(raw_origin_ref)
        if origin_ref.revision is None or origin_ref.object_id != wake_id.strip():
            raise ValueError("wake delivery Observation has invalid exact Wake ref")
        if metadata.get("origin_wake_revision") != origin_ref.revision:
            raise ValueError("wake delivery Observation Wake revision mismatch")
        origin_payload = self.store.get_payload(
            origin_ref.object_id,
            revision=origin_ref.revision,
        )
        if origin_payload.get("object_type") != ObjectType.WAKE.value:
            raise ValueError("wake delivery provenance does not point to a Wake")
        if origin_payload.get("subject_id") != self.subject_id:
            raise ValueError("wake delivery provenance crosses subject scope")
        return payload

    def commit_assistant_delivery(
        self,
        *,
        assistant_text: str,
        occurred_at: datetime,
        origin_wake_ref: ObjectRef,
        termination_reason: str,
        model_rounds: int,
        capability_names: tuple[str, ...],
        step0: Mapping[str, Any],
        recorded_at: datetime | None = None,
    ) -> ConversationMessageCommit:
        """Persist one proactive assistant->user delivery without fabricating USER input.

        The logical Wake object id is the stable delivery identity; the first exact
        RUNNING Wake revision remains immutable provenance. Replaying the same exact
        persistence request is idempotent, while changed text/metadata under the same
        logical delivery identity fails closed in SQLiteWorldStore.
        """

        if origin_wake_ref.revision is None:
            raise ValueError("origin_wake_ref must pin an exact Wake revision")
        occurred = as_utc(occurred_at, "occurred_at")
        recorded = as_utc(recorded_at or occurred_at, "recorded_at")
        if recorded < occurred:
            raise ValueError("recorded_at must be >= occurred_at")

        wake_payload = self.store.get_payload(
            origin_wake_ref.object_id,
            revision=origin_wake_ref.revision,
        )
        if wake_payload.get("object_type") != ObjectType.WAKE.value:
            raise ValueError("origin_wake_ref must point to a Wake object")
        if wake_payload.get("subject_id") != self.subject_id:
            raise ValueError("origin_wake_ref crosses the interaction subject scope")

        delivery_key, assistant_id = self._wake_delivery_identity(
            origin_wake_ref.object_id
        )
        origin_ref_payload = origin_wake_ref.model_dump(mode="json")
        metadata = {
            "dimension": INTERACTION_DIMENSION,
            "role": "assistant",
            "interaction_kind": "wake_delivery",
            "delivery_provenance": "wake_user_delivery",
            "delivered_at": occurred.isoformat(),
            "origin_wake_ref": origin_ref_payload,
            "origin_wake_id": origin_wake_ref.object_id,
            "origin_wake_revision": origin_wake_ref.revision,
            "delivery_key": delivery_key,
            "delivery_runtime": {
                "termination_reason": str(termination_reason),
                "model_rounds": int(model_rounds),
                "capability_names": list(capability_names),
                "step0": dict(step0),
            },
        }
        assistant_obs = Observation(
            object_id=assistant_id,
            subject_id=self.subject_id,
            occurred=TemporalExtent.point(occurred),
            learned_at=recorded,
            recorded_at=recorded,
            created_by="conversation_ingest:wake_delivery",
            source_kind="user_ai_interaction",
            modality="text",
            value=assistant_text,
            raw_locator=(
                f"wake-delivery://{self.subject_id}/"
                f"{origin_wake_ref.object_id}/{origin_wake_ref.revision}/assistant"
            ),
            metadata=metadata,
        )
        operation_id = f"op_wake_ai_{delivery_key}"
        result = self.store.commit(
            [assistant_obs],
            OperationRequest(
                operation_id=operation_id,
                operation_name="conversation.commit_assistant_delivery",
                arguments={
                    "origin_wake_ref": origin_ref_payload,
                    "interaction_kind": "wake_delivery",
                },
                expected_world_revision=self._expected_revision_for_retry(
                    self.store,
                    operation_id,
                ),
                reason="persist proactive assistant output committed for user delivery",
                idempotency_key=(
                    "wake-assistant-delivery:"
                    f"{self.subject_id}:"
                    f"{origin_wake_ref.object_id}"
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
