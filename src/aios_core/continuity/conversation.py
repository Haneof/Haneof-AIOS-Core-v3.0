"""Same-session long-conversation continuity for AIOS v3.0.

Raw user/assistant observations in WorldStore remain the source of truth. This service
uses the rebuildable runtime timeline only as a fast exact-session projection and
stores model-generated round summaries back in WorldStore as Summary objects.

It deliberately does not create User Understanding / relationship / personality
claims. A round summary answers only: "what was discussed in these turns?"
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Mapping, Sequence

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
from aios_core.runtime.conversation_timeline import (
    ConversationTimelineConflict,
    ConversationTimelineStore,
    ConversationTurn,
)
from aios_core.storage.idempotency import canonical_json_dumps
from aios_core.storage.sqlite_store import SQLiteWorldStore, StoreError


ROUND_SUMMARY_KIND = "conversation_round_continuity"


def _stable_id(prefix: str, *parts: object) -> str:
    raw = canonical_json_dumps(list(parts))
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]}"


def _estimate_text_tokens(*texts: str) -> int:
    total = sum(len(text) for text in texts)
    return max(1, (total + 3) // 4)


def _parse_time(payload: Mapping[str, Any], field: str) -> datetime:
    raw = payload.get(field)
    if not isinstance(raw, str):
        raise ValueError(f"conversation payload missing {field}")
    return as_utc(datetime.fromisoformat(raw), field)


def _occurred_start(payload: Mapping[str, Any]) -> datetime:
    occurred = payload.get("occurred")
    if not isinstance(occurred, Mapping):
        raise ValueError("conversation observation missing occurred extent")
    raw = occurred.get("start")
    if not isinstance(raw, str):
        raise ValueError("conversation observation missing occurred.start")
    return as_utc(datetime.fromisoformat(raw), "occurred.start")


class ConversationSummaryTurn(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    turn_index: int = Field(ge=1)
    user_text: str
    assistant_text: str
    user_ref: ObjectRef
    assistant_ref: ObjectRef
    occurred_at: datetime

    @model_validator(mode="after")
    def validate_turn(self) -> "ConversationSummaryTurn":
        if self.user_ref.revision is None or self.assistant_ref.revision is None:
            raise ValueError("round-summary source refs must pin exact revisions")
        as_utc(self.occurred_at, "occurred_at")
        return self


class ConversationSummaryRequest(BaseModel):
    """Input handed to a real model for descriptive round summarization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    subject_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    turn_start: int = Field(ge=1)
    turn_end: int = Field(ge=1)
    source_world_revision: int = Field(ge=0)
    turns: tuple[ConversationSummaryTurn, ...] = Field(min_length=1)
    instruction: str = (
        "Summarize only what happened in these conversation turns. "
        "Preserve concrete decisions, unresolved questions and references needed "
        "to continue the same session. Do not infer personality, motive, diagnosis, "
        "relationship meaning or facts not present in the source turns."
    )

    @model_validator(mode="after")
    def validate_range(self) -> "ConversationSummaryRequest":
        if self.turn_end < self.turn_start:
            raise ValueError("turn_end must not be before turn_start")
        expected = list(range(self.turn_start, self.turn_end + 1))
        actual = [turn.turn_index for turn in self.turns]
        if actual != expected:
            raise ValueError("round-summary turns must be contiguous and match range")
        return self


ConversationSummaryHandler = Callable[[ConversationSummaryRequest], str]


@dataclass(frozen=True, slots=True)
class ConversationSummaryCommit:
    object_id: str
    revision: int
    world_revision: int
    reused_existing: bool


@dataclass(frozen=True, slots=True)
class ConversationContinuityPlan:
    session_id: str
    raw_turns: tuple[dict[str, Any], ...]
    summaries: tuple[dict[str, Any], ...]
    completed_turn_count: int
    summarized_turn_count: int
    estimated_raw_tokens: int


class ConversationContinuityService:
    """Plan same-session context, round summaries and exact raw drill-down."""

    def __init__(
        self,
        *,
        store: SQLiteWorldStore,
        index: WorldSearchIndex,
        subject_id: str = "user_1",
        recent_raw_turns: int = 6,
        summary_batch_turns: int = 5,
        summary_trigger_tokens: int = 1800,
    ) -> None:
        if not isinstance(subject_id, str) or not subject_id.strip():
            raise ValueError("subject_id must not be blank")
        if recent_raw_turns < 1:
            raise ValueError("recent_raw_turns must be >= 1")
        if summary_batch_turns < 2:
            raise ValueError("summary_batch_turns must be >= 2")
        if summary_trigger_tokens < 128:
            raise ValueError("summary_trigger_tokens must be >= 128")
        self.store = store
        self.index = index
        self.subject_id = subject_id.strip()
        self.recent_raw_turns = int(recent_raw_turns)
        self.summary_batch_turns = int(summary_batch_turns)
        self.summary_trigger_tokens = int(summary_trigger_tokens)
        self.timeline = ConversationTimelineStore(store.db_path)

    def _world_turns(self, session_id: str) -> list[ConversationTurn]:
        grouped: dict[int, dict[str, Mapping[str, Any]]] = {}
        for payload in self.store.list_payloads(
            object_type=ObjectType.OBSERVATION,
            subject_id=self.subject_id,
        ):
            if payload.get("source_kind") != "user_ai_interaction":
                continue
            metadata = payload.get("metadata")
            if not isinstance(metadata, Mapping):
                continue
            if metadata.get("session_id") != session_id:
                continue
            role = metadata.get("role")
            turn_index = metadata.get("turn_index")
            if role not in {"user", "assistant"} or not isinstance(turn_index, int):
                continue
            grouped.setdefault(turn_index, {})[str(role)] = payload

        turns: list[ConversationTurn] = []
        expected = 1
        for turn_index in sorted(grouped):
            if turn_index != expected:
                break
            pair = grouped[turn_index]
            user = pair.get("user")
            assistant = pair.get("assistant")
            if user is None or assistant is None:
                break
            user_text = user.get("value")
            assistant_text = assistant.get("value")
            if not isinstance(user_text, str) or not isinstance(assistant_text, str):
                raise ValueError("conversation raw facts must contain text values")
            occurred = min(_occurred_start(user), _occurred_start(assistant))
            recorded = max(
                _parse_time(user, "recorded_at"),
                _parse_time(assistant, "recorded_at"),
            )
            turns.append(
                ConversationTurn.create(
                    subject_id=self.subject_id,
                    session_id=session_id,
                    turn_index=turn_index,
                    user_text=user_text,
                    assistant_text=assistant_text,
                    user_observation_ref=ObjectRef(
                        object_id=str(user["object_id"]),
                        revision=int(user["revision"]),
                    ),
                    assistant_observation_ref=ObjectRef(
                        object_id=str(assistant["object_id"]),
                        revision=int(assistant["revision"]),
                    ),
                    occurred_at=occurred,
                    recorded_at=recorded,
                )
            )
            expected += 1
        return turns

    def synchronize_session(self, session_id: str) -> tuple[ConversationTurn, ...]:
        session = session_id.strip()
        if not session:
            raise ValueError("session_id must not be blank")
        truth = self._world_turns(session)
        projected = self.timeline.list_turns(
            session,
            subject_id=self.subject_id,
            limit=max(1000, len(truth) + 1),
        )
        if projected == truth:
            return tuple(projected)

        # Projection is explicitly rebuildable and may never outrank WorldStore.
        self.timeline.reset_session(session, subject_id=self.subject_id)
        for turn in truth:
            self.timeline.append(turn)
        return tuple(truth)

    def record_completed_turn(
        self,
        *,
        session_id: str,
        turn_index: int,
        user_text: str,
        assistant_text: str,
        user_ref: ObjectRef,
        assistant_ref: ObjectRef,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> ConversationTurn:
        turn = ConversationTurn.create(
            subject_id=self.subject_id,
            session_id=session_id,
            turn_index=turn_index,
            user_text=user_text,
            assistant_text=assistant_text,
            user_observation_ref=user_ref,
            assistant_observation_ref=assistant_ref,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
        )
        try:
            return self.timeline.append(turn)
        except ConversationTimelineConflict:
            self.synchronize_session(session_id)
            existing = self.timeline.get(
                session_id,
                turn_index,
                subject_id=self.subject_id,
            )
            if existing is None:
                raise
            return existing

    def summaries_for_session(self, session_id: str) -> tuple[dict[str, Any], ...]:
        result: list[dict[str, Any]] = []
        for payload in self.store.list_payloads(
            object_type=ObjectType.SUMMARY,
            subject_id=self.subject_id,
        ):
            metadata = payload.get("metadata")
            if not isinstance(metadata, Mapping):
                continue
            if metadata.get("summary_kind") != ROUND_SUMMARY_KIND:
                continue
            if metadata.get("session_id") != session_id:
                continue
            result.append(payload)
        result.sort(
            key=lambda item: (
                int((item.get("metadata") or {}).get("turn_start") or 0),
                int(item.get("revision") or 0),
            )
        )
        return tuple(result)

    @staticmethod
    def _covered_turns(
        summaries: Sequence[Mapping[str, Any]],
    ) -> set[int]:
        covered: set[int] = set()
        for summary in summaries:
            metadata = summary.get("metadata")
            if not isinstance(metadata, Mapping):
                continue
            start = metadata.get("turn_start")
            end = metadata.get("turn_end")
            if isinstance(start, int) and isinstance(end, int) and end >= start:
                covered.update(range(start, end + 1))
        return covered

    def next_summary_request(
        self,
        *,
        session_id: str,
        current_turn_index: int,
    ) -> ConversationSummaryRequest | None:
        turns = [
            turn
            for turn in self.synchronize_session(session_id)
            if turn.turn_index < current_turn_index
        ]
        if not turns:
            return None
        summaries = self.summaries_for_session(session_id)
        covered = self._covered_turns(summaries)
        old_cutoff = max(0, len(turns) - self.recent_raw_turns)
        old_turns = turns[:old_cutoff]
        unsummarized = [
            turn for turn in old_turns if turn.turn_index not in covered
        ]
        if not unsummarized:
            return None

        total_tokens = sum(
            _estimate_text_tokens(turn.user_text, turn.assistant_text)
            for turn in turns
        )
        if (
            len(unsummarized) < self.summary_batch_turns
            and total_tokens < self.summary_trigger_tokens
        ):
            return None

        first = unsummarized[0]
        contiguous = [first]
        for turn in unsummarized[1:]:
            if turn.turn_index != contiguous[-1].turn_index + 1:
                break
            contiguous.append(turn)
            if len(contiguous) >= self.summary_batch_turns:
                break
        if len(contiguous) < 2:
            return None

        summary_turns: list[ConversationSummaryTurn] = []
        for turn in contiguous:
            if turn.user_observation_ref is None or turn.assistant_observation_ref is None:
                raise ValueError("conversation projection missing pinned raw world refs")
            summary_turns.append(
                ConversationSummaryTurn(
                    turn_index=turn.turn_index,
                    user_text=turn.user_text,
                    assistant_text=turn.assistant_text,
                    user_ref=turn.user_observation_ref,
                    assistant_ref=turn.assistant_observation_ref,
                    occurred_at=turn.occurred_at,
                )
            )
        return ConversationSummaryRequest(
            subject_id=self.subject_id,
            session_id=session_id,
            turn_start=summary_turns[0].turn_index,
            turn_end=summary_turns[-1].turn_index,
            source_world_revision=int(self.store.current_world_revision()),
            turns=tuple(summary_turns),
        )

    def commit_summary(
        self,
        request: ConversationSummaryRequest,
        *,
        content: str,
        generated_at: datetime,
    ) -> ConversationSummaryCommit:
        request = ConversationSummaryRequest.model_validate(
            request.model_dump(mode="python", round_trip=True)
        )
        if request.subject_id != self.subject_id:
            raise ValueError("summary request subject does not match continuity service")
        text = content.strip()
        if not text:
            raise ValueError("conversation summary content must be non-blank")
        generated = as_utc(generated_at, "generated_at")

        raw_refs: list[ObjectRef] = []
        for turn in request.turns:
            raw_refs.extend((turn.user_ref, turn.assistant_ref))
        for ref in raw_refs:
            payload = self.store.get_payload(ref.object_id, revision=ref.revision)
            if payload.get("object_type") != ObjectType.OBSERVATION.value:
                raise ValueError("round-summary sources must be raw Observation objects")
            metadata = payload.get("metadata")
            if (
                not isinstance(metadata, Mapping)
                or metadata.get("session_id") != request.session_id
            ):
                raise ValueError("round-summary source escaped the target session")

        object_id = _stable_id(
            "sum_conv_round",
            self.subject_id,
            request.session_id,
            request.turn_start,
            request.turn_end,
        )
        try:
            latest = self.store.get_payload(object_id)
        except StoreError as exc:
            if exc.code == ErrorCode.NOT_FOUND:
                latest = None
            else:
                raise

        source_pairs = [
            (ref.object_id, int(ref.revision or 0))
            for ref in raw_refs
        ]
        if latest is not None:
            latest_pairs = [
                (str(ref["object_id"]), int(ref["revision"]))
                for ref in latest.get("source_refs") or []
            ]
            if latest_pairs != source_pairs:
                raise ValueError(
                    "conversation summary range already exists with different raw sources"
                )
            if str(latest.get("content") or "") != text:
                raise ValueError(
                    "conversation summary range already exists with different content"
                )
            return ConversationSummaryCommit(
                object_id=object_id,
                revision=int(latest["revision"]),
                world_revision=int(self.store.current_world_revision()),
                reused_existing=True,
            )

        start = request.turns[0].occurred_at
        end = request.turns[-1].occurred_at
        summary_time = TemporalExtent(
            start=start,
            end=end,
            precision=TimePrecision.SECOND,
            timezone_name="UTC",
        )
        summary = Summary(
            object_id=object_id,
            subject_id=self.subject_id,
            revision=1,
            occurred=summary_time,
            learned_at=generated,
            recorded_at=generated,
            source_refs=[
                SourceRef(object_id=ref.object_id, revision=ref.revision)
                for ref in raw_refs
            ],
            created_by="conversation_continuity:model",
            summary_time=summary_time,
            granularity="conversation_rounds",
            content=text,
            source_world_revision=request.source_world_revision,
            coverage={
                "session_id": request.session_id,
                "turn_start": request.turn_start,
                "turn_end": request.turn_end,
                "turn_count": len(request.turns),
                "source_count": len(raw_refs),
            },
            summary_status=SummaryStatus.CURRENT,
            metadata={
                "dimension": INTERACTION_DIMENSION,
                "summary_kind": ROUND_SUMMARY_KIND,
                "session_id": request.session_id,
                "turn_start": request.turn_start,
                "turn_end": request.turn_end,
            },
        )
        summary_ref = ObjectRef(object_id=object_id, revision=1)
        dependencies = [
            Dependency(
                object_id=_stable_id(
                    "dep",
                    object_id,
                    1,
                    ref.object_id,
                    ref.revision,
                ),
                subject_id=self.subject_id,
                learned_at=generated,
                recorded_at=generated,
                created_by="conversation_continuity:dependency",
                dependent_ref=summary_ref,
                dependency_ref=ref,
                dependency_type="conversation_summary_uses_raw_turn",
            )
            for ref in raw_refs
        ]
        operation_id = _stable_id(
            "op_conv_summary",
            object_id,
            source_pairs,
        )
        result = self.store.commit(
            [summary, *dependencies],
            OperationRequest(
                operation_id=operation_id,
                session_id=request.session_id,
                operation_name="continuity.commit_round_summary",
                arguments={
                    "turn_start": request.turn_start,
                    "turn_end": request.turn_end,
                    "source_count": len(raw_refs),
                },
                expected_world_revision=int(self.store.current_world_revision()),
                reason="persist model-generated same-session continuity summary",
                idempotency_key=f"continuity-summary:{object_id}",
                source_class=SourceClass.MAINTENANCE,
                maintenance_class=MaintenanceClass.SUMMARY_REBUILD,
            ),
        )
        self.index.catch_up()
        return ConversationSummaryCommit(
            object_id=object_id,
            revision=1,
            world_revision=result.world_revision,
            reused_existing=result.idempotent_replay,
        )

    def context_plan(
        self,
        *,
        session_id: str,
        current_turn_index: int,
    ) -> ConversationContinuityPlan:
        turns = [
            turn
            for turn in self.synchronize_session(session_id)
            if turn.turn_index < current_turn_index
        ]
        summaries = self.summaries_for_session(session_id)
        covered = self._covered_turns(summaries)

        raw_turns = [
            {
                "turn_index": turn.turn_index,
                "user": turn.user_text,
                "assistant": turn.assistant_text,
                "user_ref": (
                    None
                    if turn.user_observation_ref is None
                    else turn.user_observation_ref.model_dump(mode="json")
                ),
                "assistant_ref": (
                    None
                    if turn.assistant_observation_ref is None
                    else turn.assistant_observation_ref.model_dump(mode="json")
                ),
            }
            for turn in turns
            if turn.turn_index not in covered
        ]
        summary_cards = [
            {
                "summary_ref": {
                    "object_id": str(summary["object_id"]),
                    "revision": int(summary["revision"]),
                },
                "turn_start": int((summary.get("metadata") or {})["turn_start"]),
                "turn_end": int((summary.get("metadata") or {})["turn_end"]),
                "content": str(summary.get("content") or ""),
                "source_count": int(
                    (summary.get("coverage") or {}).get("source_count") or 0
                ),
            }
            for summary in summaries
        ]
        estimated_raw_tokens = sum(
            _estimate_text_tokens(turn.user_text, turn.assistant_text)
            for turn in turns
            if turn.turn_index not in covered
        )
        return ConversationContinuityPlan(
            session_id=session_id,
            raw_turns=tuple(raw_turns),
            summaries=tuple(summary_cards),
            completed_turn_count=len(turns),
            summarized_turn_count=len(covered),
            estimated_raw_tokens=estimated_raw_tokens,
        )

    def read_turn_range(
        self,
        *,
        session_id: str,
        start_turn: int,
        end_turn: int,
        limit: int = 50,
    ) -> tuple[dict[str, Any], ...]:
        if start_turn < 1 or end_turn < start_turn:
            raise ValueError("invalid conversation turn range")
        if end_turn - start_turn + 1 > max(1, min(int(limit), 50)):
            raise ValueError("requested conversation turn range exceeds limit")
        turns = self.synchronize_session(session_id)
        selected = [
            turn
            for turn in turns
            if start_turn <= turn.turn_index <= end_turn
        ]
        return tuple(
            {
                "turn_index": turn.turn_index,
                "user": turn.user_text,
                "assistant": turn.assistant_text,
                "user_ref": (
                    None
                    if turn.user_observation_ref is None
                    else turn.user_observation_ref.model_dump(mode="json")
                ),
                "assistant_ref": (
                    None
                    if turn.assistant_observation_ref is None
                    else turn.assistant_observation_ref.model_dump(mode="json")
                ),
                "occurred_at": turn.occurred_at.isoformat(),
            }
            for turn in selected
        )

    def search_session_summaries(
        self,
        *,
        session_id: str,
        query: str,
        limit: int = 8,
    ) -> tuple[dict[str, Any], ...]:
        clean = query.strip()
        if not clean:
            raise ValueError("summary search query must not be blank")
        page = self.index.recall_candidates(
            clean,
            subject=self.subject_id,
            dimension=INTERACTION_DIMENSION,
            object_types=[ObjectType.SUMMARY.value],
            limit=max(1, min(int(limit) * 4, 50)),
        )
        selected: list[dict[str, Any]] = []
        for hit in page.hits:
            payload = self.store.get_payload(hit.object_id, revision=hit.revision)
            metadata = payload.get("metadata")
            if (
                not isinstance(metadata, Mapping)
                or metadata.get("summary_kind") != ROUND_SUMMARY_KIND
                or metadata.get("session_id") != session_id
            ):
                continue
            selected.append(
                {
                    "summary_ref": {
                        "object_id": hit.object_id,
                        "revision": hit.revision,
                    },
                    "turn_start": int(metadata["turn_start"]),
                    "turn_end": int(metadata["turn_end"]),
                    "content": str(payload.get("content") or ""),
                    "retrieval_score": hit.score,
                }
            )
            if len(selected) >= max(1, min(int(limit), 20)):
                break
        return tuple(selected)
