"""World-backed long-conversation continuity for AIOS v3.0.

Raw user/assistant observations remain the source of truth. This module derives
recent-turn state from WorldStore, schedules bounded round summaries, stores those
summaries as pinned-source index objects, and can drill back down to exact dialogue.
It does not infer user meaning or create cognition Claims.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aios_core.contracts.enums import (
    ErrorCode,
    MaintenanceClass,
    ObjectType,
    SourceClass,
    SummaryStatus,
)
from aios_core.contracts.models import Dependency, Summary
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef, SourceRef
from aios_core.contracts.time import TemporalExtent, TimePrecision, as_utc
from aios_core.ingest.conversation import INTERACTION_DIMENSION
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.idempotency import canonical_json_dumps
from aios_core.storage.sqlite_store import SQLiteWorldStore, StoreError


ROUND_SUMMARY_KIND = "conversation_round"


def _stable_id(prefix: str, *parts: object) -> str:
    raw = canonical_json_dumps(list(parts))
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]}"


def _estimate_message_tokens(messages: Sequence[ConversationMessage]) -> int:
    """Cheap deterministic pressure estimate; only schedules maintenance."""
    chars = sum(len(item.text) for item in messages)
    return max(1, (chars + 3) // 4)


def _parse_datetime(value: Any, field_name: str) -> datetime:
    if isinstance(value, datetime):
        return as_utc(value, field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be an aware datetime")
    return as_utc(
        datetime.fromisoformat(value.strip().replace("Z", "+00:00")),
        field_name,
    )


class ConversationMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    object_id: str = Field(min_length=1)
    revision: int = Field(ge=1)
    session_id: str = Field(min_length=1)
    turn_index: int = Field(ge=1)
    role: str = Field(pattern="^(user|assistant)$")
    text: str
    occurred_at: datetime
    raw_locator: str | None = None

    @model_validator(mode="after")
    def validate_message(self) -> "ConversationMessage":
        as_utc(self.occurred_at, "occurred_at")
        return self

    def object_ref(self) -> dict[str, Any]:
        return {"object_id": self.object_id, "revision": self.revision}

    def as_context_message(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "text": self.text,
            "object_ref": self.object_ref(),
            "occurred_at": as_utc(self.occurred_at, "occurred_at").isoformat(),
        }


class RoundSummaryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    subject_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    turn_start: int = Field(ge=1)
    turn_end: int = Field(ge=1)
    source_world_revision: int = Field(ge=0)
    sources: tuple[ConversationMessage, ...] = Field(min_length=2)

    @model_validator(mode="after")
    def validate_request(self) -> "RoundSummaryRequest":
        if self.turn_end < self.turn_start:
            raise ValueError("turn_end must not be before turn_start")
        if any(item.session_id != self.session_id for item in self.sources):
            raise ValueError("all summary sources must belong to the requested session")
        turns = {item.turn_index for item in self.sources}
        expected = set(range(self.turn_start, self.turn_end + 1))
        if turns != expected:
            raise ValueError("round summary sources must cover a contiguous turn range")
        for turn_index in expected:
            roles = {
                item.role
                for item in self.sources
                if item.turn_index == turn_index
            }
            if roles != {"user", "assistant"}:
                raise ValueError("every summarized turn must pin user and assistant facts")
        return self

    def as_model_input(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "turn_start": self.turn_start,
            "turn_end": self.turn_end,
            "instruction": (
                "Summarize only what happened in this dialogue range for later "
                "same-session continuity. Do not infer personality, relationships, "
                "causality, or facts not present in the pinned raw messages."
            ),
            "messages": [
                {
                    "turn_index": item.turn_index,
                    **item.as_context_message(),
                }
                for item in self.sources
            ],
        }


class ContinuitySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str
    recent_turns: tuple[Mapping[str, Any], ...] = ()
    round_summaries: tuple[Mapping[str, Any], ...] = ()
    pending_summary: RoundSummaryRequest | None = None


@dataclass(frozen=True, slots=True)
class RoundSummaryCommit:
    object_id: str
    revision: int
    world_revision: int
    reused_existing: bool


class ConversationContinuityService:
    """Rebuildable continuity view over canonical conversation world facts."""

    def __init__(
        self,
        *,
        store: SQLiteWorldStore,
        index: WorldSearchIndex | None = None,
        subject_id: str = "user_1",
    ) -> None:
        if not isinstance(subject_id, str) or not subject_id.strip():
            raise ValueError("subject_id must not be blank")
        self.store = store
        self.index = index
        self.subject_id = subject_id.strip()

    def _catch_up(self) -> None:
        if self.index is not None:
            self.index.catch_up()

    def _get_payload_if_exists(
        self,
        object_id: str,
        *,
        revision: int | None = None,
    ) -> dict[str, Any] | None:
        try:
            return self.store.get_payload(object_id, revision=revision)
        except StoreError as exc:
            if exc.code == ErrorCode.NOT_FOUND:
                return None
            raise

    def _expected_revision_for_retry(self, operation_id: str) -> int:
        expected = int(self.store.current_world_revision())
        try:
            previous = self.store.operation_record(operation_id)
        except StoreError as exc:
            if exc.code == ErrorCode.NOT_FOUND:
                return expected
            raise
        return int(previous["expected_world_revision"])

    def _messages(
        self,
        *,
        session_id: str,
        before_turn: int | None = None,
        turn_start: int | None = None,
        turn_end: int | None = None,
    ) -> tuple[ConversationMessage, ...]:
        session = session_id.strip()
        if not session:
            raise ValueError("session_id must not be blank")

        result: list[ConversationMessage] = []
        for payload in self.store.list_payloads(
            object_type=ObjectType.OBSERVATION,
            subject_id=self.subject_id,
        ):
            metadata = payload.get("metadata") or {}
            if metadata.get("dimension") != INTERACTION_DIMENSION:
                continue
            if str(metadata.get("session_id") or "") != session:
                continue
            role = str(metadata.get("role") or "")
            if role not in {"user", "assistant"}:
                continue
            try:
                index = int(metadata.get("turn_index"))
            except (TypeError, ValueError):
                continue
            if index < 1:
                continue
            if before_turn is not None and index >= int(before_turn):
                continue
            if turn_start is not None and index < int(turn_start):
                continue
            if turn_end is not None and index > int(turn_end):
                continue

            occurred = payload.get("occurred") or {}
            raw_start = occurred.get("start")
            if raw_start is None:
                raw_start = payload.get("learned_at")
            result.append(
                ConversationMessage(
                    object_id=str(payload["object_id"]),
                    revision=int(payload.get("revision", 1)),
                    session_id=session,
                    turn_index=index,
                    role=role,
                    text=str(payload.get("value") or ""),
                    occurred_at=_parse_datetime(raw_start, "occurred_at"),
                    raw_locator=(
                        str(payload["raw_locator"])
                        if payload.get("raw_locator") is not None
                        else None
                    ),
                )
            )

        role_order = {"user": 0, "assistant": 1}
        result.sort(
            key=lambda item: (
                item.turn_index,
                role_order[item.role],
                item.object_id,
            )
        )
        return tuple(result)

    def _complete_turns(
        self,
        *,
        session_id: str,
        before_turn: int | None = None,
    ) -> tuple[dict[str, Any], ...]:
        grouped: dict[int, dict[str, ConversationMessage]] = {}
        for message in self._messages(
            session_id=session_id,
            before_turn=before_turn,
        ):
            roles = grouped.setdefault(message.turn_index, {})
            if message.role in roles:
                raise ValueError(
                    f"duplicate {message.role} fact for session {session_id} "
                    f"turn {message.turn_index}"
                )
            roles[message.role] = message

        turns: list[dict[str, Any]] = []
        for turn_index in sorted(grouped):
            pair = grouped[turn_index]
            if set(pair) != {"user", "assistant"}:
                continue
            turns.append(
                {
                    "turn_index": turn_index,
                    "user": pair["user"].as_context_message(),
                    "assistant": pair["assistant"].as_context_message(),
                }
            )
        return tuple(turns)

    def recent_turns(
        self,
        *,
        session_id: str,
        before_turn: int,
        limit: int,
    ) -> tuple[Mapping[str, Any], ...]:
        if limit < 0:
            raise ValueError("limit must be >= 0")
        if limit == 0:
            return ()
        turns = self._complete_turns(
            session_id=session_id,
            before_turn=before_turn,
        )
        return tuple(turns[-limit:])

    def round_summaries(
        self,
        *,
        session_id: str,
        before_turn: int | None = None,
    ) -> tuple[Mapping[str, Any], ...]:
        session = session_id.strip()
        if not session:
            raise ValueError("session_id must not be blank")
        summaries: list[dict[str, Any]] = []

        for payload in self.store.list_payloads(
            object_type=ObjectType.SUMMARY,
            subject_id=self.subject_id,
        ):
            metadata = payload.get("metadata") or {}
            if metadata.get("summary_kind") != ROUND_SUMMARY_KIND:
                continue
            if str(metadata.get("session_id") or "") != session:
                continue
            if str(payload.get("summary_status") or "") == SummaryStatus.STALE.value:
                continue
            try:
                turn_start = int(metadata["turn_start"])
                turn_end = int(metadata["turn_end"])
            except (KeyError, TypeError, ValueError):
                continue
            if before_turn is not None and turn_end >= int(before_turn):
                continue
            summaries.append(
                {
                    "object_ref": {
                        "object_id": str(payload["object_id"]),
                        "revision": int(payload.get("revision", 1)),
                    },
                    "session_id": session,
                    "turn_start": turn_start,
                    "turn_end": turn_end,
                    "content": str(payload.get("content") or ""),
                    "source_refs": [
                        {
                            "object_id": str(item["object_id"]),
                            "revision": int(item["revision"]),
                        }
                        for item in payload.get("source_refs") or []
                    ],
                    "raw_drill_down_available": True,
                }
            )

        summaries.sort(
            key=lambda item: (
                int(item["turn_start"]),
                int(item["turn_end"]),
                str(item["object_ref"]["object_id"]),
            )
        )
        return tuple(summaries)

    def prepare_next_round_summary(
        self,
        *,
        session_id: str,
        before_turn: int,
        recent_turn_limit: int,
        summary_chunk_turns: int,
        summary_trigger_tokens: int | None = None,
    ) -> RoundSummaryRequest | None:
        if recent_turn_limit < 0:
            raise ValueError("recent_turn_limit must be >= 0")
        if summary_chunk_turns < 1:
            raise ValueError("summary_chunk_turns must be >= 1")
        if summary_trigger_tokens is not None and summary_trigger_tokens < 128:
            raise ValueError("summary_trigger_tokens must be >= 128")

        turns = list(
            self._complete_turns(
                session_id=session_id,
                before_turn=before_turn,
            )
        )
        if len(turns) <= recent_turn_limit:
            return None

        existing = self.round_summaries(
            session_id=session_id,
            before_turn=before_turn,
        )
        covered_until = max(
            (int(item["turn_end"]) for item in existing),
            default=0,
        )
        eligible = [
            item
            for item in turns[:-recent_turn_limit or None]
            if int(item["turn_index"]) > covered_until
        ]
        if not eligible:
            return None

        pressure_triggered = False
        if summary_trigger_tokens is not None:
            first_turn = int(eligible[0]["turn_index"])
            last_turn = int(eligible[-1]["turn_index"])
            pressure_messages = self._messages(
                session_id=session_id,
                turn_start=first_turn,
                turn_end=last_turn,
            )
            pressure_triggered = (
                _estimate_message_tokens(pressure_messages)
                >= summary_trigger_tokens
            )

        if len(eligible) < summary_chunk_turns and not pressure_triggered:
            return None
        # Under token pressure we may summarize before the normal chunk is full,
        # but avoid churning one-turn summaries unless the configured chunk itself
        # explicitly requests one-turn windows.
        if (
            pressure_triggered
            and summary_chunk_turns > 1
            and len(eligible) < 2
        ):
            return None

        target_turns = min(summary_chunk_turns, len(eligible))
        selected: list[Mapping[str, Any]] = []
        expected_turn: int | None = None
        for item in eligible:
            turn_index = int(item["turn_index"])
            if expected_turn is None:
                expected_turn = turn_index
            if turn_index != expected_turn:
                break
            selected.append(item)
            expected_turn += 1
            if len(selected) == target_turns:
                break
        if len(selected) < target_turns:
            return None

        start = int(selected[0]["turn_index"])
        end = int(selected[-1]["turn_index"])
        source_messages = self._messages(
            session_id=session_id,
            turn_start=start,
            turn_end=end,
        )
        return RoundSummaryRequest(
            subject_id=self.subject_id,
            session_id=session_id.strip(),
            turn_start=start,
            turn_end=end,
            source_world_revision=int(self.store.current_world_revision()),
            sources=source_messages,
        )

    def commit_round_summary(
        self,
        request: RoundSummaryRequest,
        *,
        content: str,
        generated_at: datetime,
    ) -> RoundSummaryCommit:
        if request.subject_id != self.subject_id:
            raise ValueError("round summary request belongs to another subject")
        text = content.strip()
        if not text:
            raise ValueError("round summary content must not be blank")
        generated = as_utc(generated_at, "generated_at")

        for source in request.sources:
            payload = self.store.get_payload(
                source.object_id,
                revision=source.revision,
            )
            metadata = payload.get("metadata") or {}
            if payload.get("object_type") != ObjectType.OBSERVATION.value:
                raise ValueError("round summary source must be an Observation")
            if payload.get("subject_id") != self.subject_id:
                raise ValueError("round summary source belongs to another subject")
            if metadata.get("dimension") != INTERACTION_DIMENSION:
                raise ValueError("round summary source must be a conversation fact")
            if str(metadata.get("session_id") or "") != request.session_id:
                raise ValueError("round summary source belongs to another session")
            if int(metadata.get("turn_index", 0)) != source.turn_index:
                raise ValueError("round summary source turn identity changed")
            if str(metadata.get("role") or "") != source.role:
                raise ValueError("round summary source role identity changed")

        object_id = _stable_id(
            "sum_conv_round",
            self.subject_id,
            request.session_id,
            request.turn_start,
            request.turn_end,
        )
        latest = self._get_payload_if_exists(object_id)
        expected_refs = [
            {"object_id": item.object_id, "revision": item.revision}
            for item in request.sources
        ]
        if latest is not None:
            existing_refs = [
                {
                    "object_id": str(item["object_id"]),
                    "revision": int(item["revision"]),
                }
                for item in latest.get("source_refs") or []
            ]
            if existing_refs != expected_refs:
                raise ValueError(
                    "conversation round identity conflict: source refs changed"
                )
            if str(latest.get("content") or "") != text:
                raise ValueError(
                    "conversation round is already summarized with different content"
                )
            self._catch_up()
            return RoundSummaryCommit(
                object_id=object_id,
                revision=int(latest.get("revision", 1)),
                world_revision=int(self.store.current_world_revision()),
                reused_existing=True,
            )

        first = request.sources[0]
        last = request.sources[-1]
        summary_time = TemporalExtent(
            start=as_utc(first.occurred_at, "summary_start"),
            end=as_utc(last.occurred_at, "summary_end"),
            precision=TimePrecision.SECOND,
            timezone_name="UTC",
        )
        summary = Summary(
            object_id=object_id,
            subject_id=self.subject_id,
            occurred=summary_time,
            learned_at=generated,
            recorded_at=generated,
            source_refs=[
                SourceRef(object_id=item.object_id, revision=item.revision)
                for item in request.sources
            ],
            created_by="conversation_continuity:model",
            summary_time=summary_time,
            granularity="conversation_round",
            content=text,
            source_world_revision=request.source_world_revision,
            coverage={
                "session_id": request.session_id,
                "turn_start": request.turn_start,
                "turn_end": request.turn_end,
                "turn_count": request.turn_end - request.turn_start + 1,
                "source_count": len(request.sources),
                "complete": True,
            },
            summary_status=SummaryStatus.CURRENT,
            metadata={
                "dimension": INTERACTION_DIMENSION,
                "summary_kind": ROUND_SUMMARY_KIND,
                "session_id": request.session_id,
                "turn_start": request.turn_start,
                "turn_end": request.turn_end,
                "raw_drill_down_available": True,
            },
        )

        dependencies = [
            Dependency(
                object_id=_stable_id(
                    "dep_conv_round",
                    object_id,
                    1,
                    item.object_id,
                    item.revision,
                ),
                subject_id=self.subject_id,
                learned_at=generated,
                recorded_at=generated,
                created_by="conversation_continuity:dependency",
                dependent_ref=ObjectRef(object_id=object_id, revision=1),
                dependency_ref=ObjectRef(
                    object_id=item.object_id,
                    revision=item.revision,
                ),
                dependency_type="conversation_round_summary_uses_raw_dialogue",
            )
            for item in request.sources
        ]
        operation_id = _stable_id(
            "op_conv_round",
            self.subject_id,
            request.session_id,
            request.turn_start,
            request.turn_end,
        )
        result = self.store.commit(
            [summary, *dependencies],
            OperationRequest(
                operation_id=operation_id,
                session_id=request.session_id,
                operation_name="continuity.commit_round_summary",
                arguments={
                    "session_id": request.session_id,
                    "turn_start": request.turn_start,
                    "turn_end": request.turn_end,
                    "source_refs": expected_refs,
                },
                expected_world_revision=self._expected_revision_for_retry(operation_id),
                reason=(
                    "persist model-generated same-session continuity index over "
                    "pinned raw dialogue"
                ),
                idempotency_key=f"conversation-round:{operation_id}",
                source_class=SourceClass.MAINTENANCE,
                maintenance_class=MaintenanceClass.SUMMARY_REBUILD,
            ),
        )
        self._catch_up()
        return RoundSummaryCommit(
            object_id=object_id,
            revision=1,
            world_revision=result.world_revision,
            reused_existing=result.idempotent_replay,
        )

    def search_round_summaries(
        self,
        *,
        session_id: str,
        query: str,
        limit: int = 8,
    ) -> tuple[Mapping[str, Any], ...]:
        """Search summary indexes for one active session, then allow raw drill-down."""
        session = session_id.strip()
        clean = query.strip()
        if not session:
            raise ValueError("session_id must not be blank")
        if not clean:
            raise ValueError("query must not be blank")
        bounded = max(1, min(int(limit), 20))

        if self.index is None:
            candidates = [
                item
                for item in self.round_summaries(session_id=session)
                if clean.casefold() in str(item.get("content") or "").casefold()
            ]
            return tuple(candidates[-bounded:])

        page = self.index.recall_candidates(
            clean,
            subject=self.subject_id,
            dimension=INTERACTION_DIMENSION,
            object_types=[ObjectType.SUMMARY.value],
            limit=min(100, bounded * 6),
        )
        result: list[Mapping[str, Any]] = []
        for hit in page.hits:
            payload = self.store.get_payload(
                hit.object_id,
                revision=hit.revision,
            )
            metadata = payload.get("metadata") or {}
            if metadata.get("summary_kind") != ROUND_SUMMARY_KIND:
                continue
            if str(metadata.get("session_id") or "") != session:
                continue
            if str(payload.get("summary_status") or "") == SummaryStatus.STALE.value:
                continue
            result.append(
                {
                    "object_ref": {
                        "object_id": hit.object_id,
                        "revision": hit.revision,
                    },
                    "session_id": session,
                    "turn_start": int(metadata["turn_start"]),
                    "turn_end": int(metadata["turn_end"]),
                    "content": str(payload.get("content") or ""),
                    "retrieval_score": hit.score,
                    "raw_drill_down_available": True,
                }
            )
            if len(result) >= bounded:
                break
        return tuple(result)

    def drill_down_summary(
        self,
        summary_id: str,
        *,
        revision: int | None = None,
    ) -> tuple[Mapping[str, Any], ...]:
        payload = self.store.get_payload(summary_id, revision=revision)
        metadata = payload.get("metadata") or {}
        if payload.get("object_type") != ObjectType.SUMMARY.value:
            raise ValueError("summary_id must point to a Summary")
        if payload.get("subject_id") != self.subject_id:
            raise ValueError("summary belongs to another subject")
        if metadata.get("summary_kind") != ROUND_SUMMARY_KIND:
            raise ValueError("summary is not a conversation round summary")

        messages: list[ConversationMessage] = []
        for ref in payload.get("source_refs") or []:
            raw = self.store.get_payload(
                str(ref["object_id"]),
                revision=int(ref["revision"]),
            )
            raw_meta = raw.get("metadata") or {}
            messages.append(
                ConversationMessage(
                    object_id=str(raw["object_id"]),
                    revision=int(raw.get("revision", 1)),
                    session_id=str(raw_meta["session_id"]),
                    turn_index=int(raw_meta["turn_index"]),
                    role=str(raw_meta["role"]),
                    text=str(raw.get("value") or ""),
                    occurred_at=_parse_datetime(
                        (raw.get("occurred") or {}).get("start")
                        or raw.get("learned_at"),
                        "occurred_at",
                    ),
                    raw_locator=(
                        str(raw["raw_locator"])
                        if raw.get("raw_locator") is not None
                        else None
                    ),
                )
            )
        messages.sort(
            key=lambda item: (
                item.turn_index,
                0 if item.role == "user" else 1,
                item.object_id,
            )
        )
        return tuple(
            {
                "turn_index": item.turn_index,
                **item.as_context_message(),
            }
            for item in messages
        )

    def drill_down_range(
        self,
        *,
        session_id: str,
        turn_start: int,
        turn_end: int,
    ) -> tuple[Mapping[str, Any], ...]:
        if turn_start < 1 or turn_end < turn_start:
            raise ValueError("invalid conversation turn range")
        return tuple(
            {
                "turn_index": item.turn_index,
                **item.as_context_message(),
            }
            for item in self._messages(
                session_id=session_id,
                turn_start=turn_start,
                turn_end=turn_end,
            )
        )

    def snapshot(
        self,
        *,
        session_id: str,
        before_turn: int,
        recent_turn_limit: int,
        summary_chunk_turns: int,
        summary_trigger_tokens: int | None = None,
    ) -> ContinuitySnapshot:
        return ContinuitySnapshot(
            session_id=session_id.strip(),
            recent_turns=self.recent_turns(
                session_id=session_id,
                before_turn=before_turn,
                limit=recent_turn_limit,
            ),
            round_summaries=self.round_summaries(
                session_id=session_id,
                before_turn=before_turn,
            ),
            pending_summary=self.prepare_next_round_summary(
                session_id=session_id,
                before_turn=before_turn,
                recent_turn_limit=recent_turn_limit,
                summary_chunk_turns=summary_chunk_turns,
                summary_trigger_tokens=summary_trigger_tokens,
            ),
        )
