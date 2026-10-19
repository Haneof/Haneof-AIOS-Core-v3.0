"""NarrativeSegmenter: Life narrative segmentation and slice pipeline for AIOS 3.0.

Fulfills Constitution Chapter 8 Article 29 & Chapter 24.
Segments the user's ongoing life narrative by themes, events, and temporal windows,
providing the underlying segmentation infrastructure for LifeChapter transition identification.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from typing import Sequence

from aios_core.contracts.enums import NarrativeSegmentStatus, ObjectType, SourceClass
from aios_core.contracts.models import Dependency, NarrativeSegment, ObjectRef
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent, as_utc
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256(
        "|".join(str(part) for part in parts).encode("utf-8")
    ).hexdigest()[:24]
    return f"{prefix}_{digest}"


@dataclass(frozen=True, slots=True)
class NarrativeSegmentReceipt:
    segment_id: str
    revision: int
    status: NarrativeSegmentStatus
    world_revision: int


class NarrativeSegmenter:
    """Manages creation, attachment, sealing, and merging of NarrativeSegment objects."""

    def __init__(
        self,
        *,
        store: SQLiteWorldStore,
        index: WorldSearchIndex | None = None,
        subject_id: str = "user_1",
    ) -> None:
        self.store = store
        self.index = index
        self.subject_id = subject_id

    def _catch_up(self) -> None:
        if self.index is not None:
            self.index.catch_up()

    def _require_pinned_refs(self, refs: Sequence[ObjectRef], field_name: str) -> None:
        for ref in refs:
            if ref.revision is None or ref.revision < 1:
                raise ValueError(f"{field_name} requires pinned ObjectRef revisions with revision >= 1")

    def _validate_ref_exists(self, ref: ObjectRef, expected_type: ObjectType | None = None) -> dict:
        payload = self.store.get_payload(ref.object_id, revision=ref.revision)
        if str(payload.get("subject_id") or "") != self.subject_id:
            raise ValueError(f"{ref.object_id} crosses the runtime subject scope")
        if expected_type is not None:
            actual_type = str(payload.get("object_type") or "")
            if actual_type != expected_type.value:
                raise ValueError(
                    f"{ref.object_id} is of type {actual_type}, expected {expected_type.value}"
                )
        return payload

    def open_segment(
        self,
        *,
        title: str,
        description: str = "",
        segment_time: TemporalExtent | None = None,
        dimension_refs: Sequence[ObjectRef] = (),
        key_event_refs: Sequence[ObjectRef] = (),
        key_claim_refs: Sequence[ObjectRef] = (),
        participant_refs: Sequence[ObjectRef] = (),
        theme_tags: Sequence[str] = (),
        coherence_score: float = 0.5,
        life_chapter_ref: ObjectRef | None = None,
        created_at: datetime | None = None,
    ) -> NarrativeSegmentReceipt:
        """Open a new narrative segment in OPEN status."""
        created = as_utc(created_at or datetime.now(timezone.utc), "created_at")
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("NarrativeSegment title must not be blank")

        self._require_pinned_refs(dimension_refs, "dimension_refs")
        self._require_pinned_refs(key_event_refs, "key_event_refs")
        self._require_pinned_refs(key_claim_refs, "key_claim_refs")
        self._require_pinned_refs(participant_refs, "participant_refs")
        if life_chapter_ref is not None:
            if life_chapter_ref.revision is None or life_chapter_ref.revision < 1:
                raise ValueError("life_chapter_ref requires pinned revision")
            self._validate_ref_exists(life_chapter_ref, ObjectType.LIFE_CHAPTER)

        for ref in dimension_refs:
            self._validate_ref_exists(ref)
        for ref in key_event_refs:
            self._validate_ref_exists(ref, ObjectType.EVENT)
        for ref in key_claim_refs:
            self._validate_ref_exists(ref, ObjectType.CLAIM)
        for ref in participant_refs:
            self._validate_ref_exists(ref, ObjectType.ENTITY)

        segment_id = _stable_id(
            "narrative",
            self.subject_id,
            clean_title,
            created.isoformat(),
        )

        segment = NarrativeSegment(
            object_id=segment_id,
            subject_id=self.subject_id,
            occurred=segment_time or TemporalExtent.point(created),
            learned_at=created,
            recorded_at=created,
            created_by="narrative_segmenter",
            title=clean_title,
            description=description.strip(),
            segment_time=segment_time or TemporalExtent.point(created),
            segment_status=NarrativeSegmentStatus.OPEN,
            dimension_refs=list(dimension_refs),
            key_event_refs=list(key_event_refs),
            key_claim_refs=list(key_claim_refs),
            participant_refs=list(participant_refs),
            supersedes_ref=None,
            merged_into_ref=None,
            life_chapter_ref=life_chapter_ref,
            theme_tags=list(theme_tags),
            coherence_score=float(coherence_score),
            metadata={"segmenter_origin": "aios_core.narrative"},
        )

        segment_ref = ObjectRef(object_id=segment_id, revision=1)
        dependencies: list[Dependency] = []
        for ref in dimension_refs:
            dependencies.append(
                Dependency(
                    object_id=_stable_id("dep", segment_id, 1, ref.object_id, ref.revision),
                    subject_id=self.subject_id,
                    learned_at=created,
                    recorded_at=created,
                    created_by="narrative_segmenter:dependency",
                    dependent_ref=segment_ref,
                    dependency_ref=ref,
                    dependency_type="narrative_segment_covers_dimension",
                )
            )
        for ref in key_event_refs:
            dependencies.append(
                Dependency(
                    object_id=_stable_id("dep", segment_id, 1, ref.object_id, ref.revision),
                    subject_id=self.subject_id,
                    learned_at=created,
                    recorded_at=created,
                    created_by="narrative_segmenter:dependency",
                    dependent_ref=segment_ref,
                    dependency_ref=ref,
                    dependency_type="narrative_segment_contains_event",
                )
            )
        for ref in key_claim_refs:
            dependencies.append(
                Dependency(
                    object_id=_stable_id("dep", segment_id, 1, ref.object_id, ref.revision),
                    subject_id=self.subject_id,
                    learned_at=created,
                    recorded_at=created,
                    created_by="narrative_segmenter:dependency",
                    dependent_ref=segment_ref,
                    dependency_ref=ref,
                    dependency_type="narrative_segment_contains_claim",
                )
            )

        operation = OperationRequest(
            operation_name="narrative.segment.open",
            arguments={"segment_id": segment_id, "title": clean_title},
            expected_world_revision=int(self.store.current_world_revision()),
            reason="open new narrative segment",
            idempotency_key=f"narrative-open:{segment_id}:1",
            source_class=SourceClass.AI_COGNITION,
        )

        result = self.store.commit([segment, *dependencies], operation)
        self._catch_up()
        return NarrativeSegmentReceipt(
            segment_id=segment_id,
            revision=1,
            status=NarrativeSegmentStatus.OPEN,
            world_revision=result.world_revision,
        )

    def attach_event(
        self,
        *,
        segment_ref: ObjectRef,
        event_ref: ObjectRef,
        attached_at: datetime | None = None,
    ) -> NarrativeSegmentReceipt:
        """Attach an event to an OPEN narrative segment, generating a forward revision."""
        attached = as_utc(attached_at or datetime.now(timezone.utc), "attached_at")
        self._require_pinned_refs([segment_ref], "segment_ref")
        self._require_pinned_refs([event_ref], "event_ref")
        self._validate_ref_exists(event_ref, ObjectType.EVENT)

        payload = self.store.get_payload(segment_ref.object_id, revision=segment_ref.revision)
        current = NarrativeSegment.model_validate(payload)
        if current.segment_status != NarrativeSegmentStatus.OPEN:
            raise ValueError(
                f"cannot attach event to NarrativeSegment in status {current.segment_status.value}"
            )

        event_keys = {(r.object_id, r.revision) for r in current.key_event_refs}
        if (event_ref.object_id, event_ref.revision) in event_keys:
            # Idempotent re-attachment
            return NarrativeSegmentReceipt(
                segment_id=current.object_id,
                revision=current.revision,
                status=current.segment_status,
                world_revision=int(self.store.current_world_revision()),
            )

        new_revision = current.revision + 1
        new_event_refs = [*current.key_event_refs, event_ref]
        # Re-estimate coherence score slightly as events enrich context
        new_coherence = min(1.0, current.coherence_score + 0.05)

        updated_segment = NarrativeSegment(
            object_id=current.object_id,
            revision=new_revision,
            subject_id=current.subject_id,
            occurred=current.occurred,
            learned_at=attached,
            recorded_at=attached,
            created_by="narrative_segmenter",
            title=current.title,
            description=current.description,
            segment_time=current.segment_time,
            segment_status=NarrativeSegmentStatus.OPEN,
            dimension_refs=current.dimension_refs,
            key_event_refs=new_event_refs,
            key_claim_refs=current.key_claim_refs,
            participant_refs=current.participant_refs,
            supersedes_ref=segment_ref,
            merged_into_ref=None,
            life_chapter_ref=current.life_chapter_ref,
            theme_tags=current.theme_tags,
            coherence_score=new_coherence,
            metadata=dict(current.metadata),
        )

        dep = Dependency(
            object_id=_stable_id(
                "dep", current.object_id, new_revision, event_ref.object_id, event_ref.revision
            ),
            subject_id=self.subject_id,
            learned_at=attached,
            recorded_at=attached,
            created_by="narrative_segmenter:dependency",
            dependent_ref=ObjectRef(object_id=current.object_id, revision=new_revision),
            dependency_ref=event_ref,
            dependency_type="narrative_segment_contains_event",
        )

        operation = OperationRequest(
            operation_name="narrative.segment.attach_event",
            arguments={
                "segment_id": current.object_id,
                "revision": new_revision,
                "event_id": event_ref.object_id,
            },
            expected_world_revision=int(self.store.current_world_revision()),
            reason=f"attach event {event_ref.object_id} to segment",
            idempotency_key=f"narrative-attach-event:{current.object_id}:{new_revision}:{event_ref.object_id}",
            source_class=SourceClass.AI_COGNITION,
        )

        result = self.store.commit([updated_segment, dep], operation)
        self._catch_up()
        return NarrativeSegmentReceipt(
            segment_id=current.object_id,
            revision=new_revision,
            status=NarrativeSegmentStatus.OPEN,
            world_revision=result.world_revision,
        )

    def attach_claim(
        self,
        *,
        segment_ref: ObjectRef,
        claim_ref: ObjectRef,
        attached_at: datetime | None = None,
    ) -> NarrativeSegmentReceipt:
        """Attach a claim to an OPEN narrative segment, generating a forward revision."""
        attached = as_utc(attached_at or datetime.now(timezone.utc), "attached_at")
        self._require_pinned_refs([segment_ref], "segment_ref")
        self._require_pinned_refs([claim_ref], "claim_ref")
        self._validate_ref_exists(claim_ref, ObjectType.CLAIM)

        payload = self.store.get_payload(segment_ref.object_id, revision=segment_ref.revision)
        current = NarrativeSegment.model_validate(payload)
        if current.segment_status != NarrativeSegmentStatus.OPEN:
            raise ValueError(
                f"cannot attach claim to NarrativeSegment in status {current.segment_status.value}"
            )

        claim_keys = {(r.object_id, r.revision) for r in current.key_claim_refs}
        if (claim_ref.object_id, claim_ref.revision) in claim_keys:
            return NarrativeSegmentReceipt(
                segment_id=current.object_id,
                revision=current.revision,
                status=current.segment_status,
                world_revision=int(self.store.current_world_revision()),
            )

        new_revision = current.revision + 1
        new_claim_refs = [*current.key_claim_refs, claim_ref]

        updated_segment = NarrativeSegment(
            object_id=current.object_id,
            revision=new_revision,
            subject_id=current.subject_id,
            occurred=current.occurred,
            learned_at=attached,
            recorded_at=attached,
            created_by="narrative_segmenter",
            title=current.title,
            description=current.description,
            segment_time=current.segment_time,
            segment_status=NarrativeSegmentStatus.OPEN,
            dimension_refs=current.dimension_refs,
            key_event_refs=current.key_event_refs,
            key_claim_refs=new_claim_refs,
            participant_refs=current.participant_refs,
            supersedes_ref=segment_ref,
            merged_into_ref=None,
            life_chapter_ref=current.life_chapter_ref,
            theme_tags=current.theme_tags,
            coherence_score=current.coherence_score,
            metadata=dict(current.metadata),
        )

        dep = Dependency(
            object_id=_stable_id(
                "dep", current.object_id, new_revision, claim_ref.object_id, claim_ref.revision
            ),
            subject_id=self.subject_id,
            learned_at=attached,
            recorded_at=attached,
            created_by="narrative_segmenter:dependency",
            dependent_ref=ObjectRef(object_id=current.object_id, revision=new_revision),
            dependency_ref=claim_ref,
            dependency_type="narrative_segment_contains_claim",
        )

        operation = OperationRequest(
            operation_name="narrative.segment.attach_claim",
            arguments={
                "segment_id": current.object_id,
                "revision": new_revision,
                "claim_id": claim_ref.object_id,
            },
            expected_world_revision=int(self.store.current_world_revision()),
            reason=f"attach claim {claim_ref.object_id} to segment",
            idempotency_key=f"narrative-attach-claim:{current.object_id}:{new_revision}:{claim_ref.object_id}",
            source_class=SourceClass.AI_COGNITION,
        )

        result = self.store.commit([updated_segment, dep], operation)
        self._catch_up()
        return NarrativeSegmentReceipt(
            segment_id=current.object_id,
            revision=new_revision,
            status=NarrativeSegmentStatus.OPEN,
            world_revision=result.world_revision,
        )

    def seal_segment(
        self,
        *,
        segment_ref: ObjectRef,
        reason: str,
        sealed_at: datetime | None = None,
    ) -> NarrativeSegmentReceipt:
        """Seal an OPEN narrative segment, preventing further attachments."""
        sealed = as_utc(sealed_at or datetime.now(timezone.utc), "sealed_at")
        self._require_pinned_refs([segment_ref], "segment_ref")
        clean_reason = reason.strip()
        if not clean_reason:
            raise ValueError("seal_segment requires explicit non-empty reason")

        payload = self.store.get_payload(segment_ref.object_id, revision=segment_ref.revision)
        current = NarrativeSegment.model_validate(payload)
        if current.segment_status != NarrativeSegmentStatus.OPEN:
            raise ValueError(
                f"only OPEN NarrativeSegment may be sealed, current is {current.segment_status.value}"
            )

        new_revision = current.revision + 1
        metadata = dict(current.metadata)
        metadata["seal_reason"] = clean_reason
        metadata["sealed_at"] = sealed.isoformat()

        sealed_segment = NarrativeSegment(
            object_id=current.object_id,
            revision=new_revision,
            subject_id=current.subject_id,
            occurred=current.occurred,
            learned_at=sealed,
            recorded_at=sealed,
            created_by="narrative_segmenter",
            title=current.title,
            description=current.description,
            segment_time=current.segment_time,
            segment_status=NarrativeSegmentStatus.SEALED,
            dimension_refs=current.dimension_refs,
            key_event_refs=current.key_event_refs,
            key_claim_refs=current.key_claim_refs,
            participant_refs=current.participant_refs,
            supersedes_ref=segment_ref,
            merged_into_ref=None,
            life_chapter_ref=current.life_chapter_ref,
            theme_tags=current.theme_tags,
            coherence_score=current.coherence_score,
            metadata=metadata,
        )

        operation = OperationRequest(
            operation_name="narrative.segment.seal",
            arguments={"segment_id": current.object_id, "revision": new_revision, "reason": clean_reason},
            expected_world_revision=int(self.store.current_world_revision()),
            reason=f"seal narrative segment: {clean_reason}",
            idempotency_key=f"narrative-seal:{current.object_id}:{new_revision}",
            source_class=SourceClass.AI_COGNITION,
        )

        result = self.store.commit([sealed_segment], operation)
        self._catch_up()
        return NarrativeSegmentReceipt(
            segment_id=current.object_id,
            revision=new_revision,
            status=NarrativeSegmentStatus.SEALED,
            world_revision=result.world_revision,
        )

    def merge_segments(
        self,
        *,
        source_segment_refs: Sequence[ObjectRef],
        target_title: str,
        target_description: str = "",
        merged_at: datetime | None = None,
    ) -> NarrativeSegmentReceipt:
        """Merge multiple narrative segments into a single unified segment."""
        merged = as_utc(merged_at or datetime.now(timezone.utc), "merged_at")
        if len(source_segment_refs) < 2:
            raise ValueError("merge_segments requires at least 2 source segment references")
        self._require_pinned_refs(source_segment_refs, "source_segment_refs")

        clean_title = target_title.strip()
        if not clean_title:
            raise ValueError("target_title must not be blank")

        source_segments: list[NarrativeSegment] = []
        all_dim_refs: list[ObjectRef] = []
        all_event_refs: list[ObjectRef] = []
        all_claim_refs: list[ObjectRef] = []
        all_participant_refs: list[ObjectRef] = []
        all_tags: set[str] = set()

        for ref in source_segment_refs:
            payload = self.store.get_payload(ref.object_id, revision=ref.revision)
            seg = NarrativeSegment.model_validate(payload)
            if seg.segment_status in {NarrativeSegmentStatus.MERGED, NarrativeSegmentStatus.REVISED}:
                raise ValueError(
                    f"cannot merge segment {seg.object_id} in terminal status {seg.segment_status.value}"
                )
            source_segments.append(seg)
            all_dim_refs.extend(seg.dimension_refs)
            all_event_refs.extend(seg.key_event_refs)
            all_claim_refs.extend(seg.key_claim_refs)
            all_participant_refs.extend(seg.participant_refs)
            all_tags.update(seg.theme_tags)

        # Deduplicate pinned refs
        unique_dim_refs = list({(r.object_id, r.revision): r for r in all_dim_refs}.values())
        unique_event_refs = list({(r.object_id, r.revision): r for r in all_event_refs}.values())
        unique_claim_refs = list({(r.object_id, r.revision): r for r in all_claim_refs}.values())
        unique_participant_refs = list({(r.object_id, r.revision): r for r in all_participant_refs}.values())

        target_id = _stable_id("narrative_merged", self.subject_id, clean_title, merged.isoformat())
        target_ref = ObjectRef(object_id=target_id, revision=1)

        # 1. Create the new merged target segment
        new_segment = NarrativeSegment(
            object_id=target_id,
            revision=1,
            subject_id=self.subject_id,
            occurred=TemporalExtent.point(merged),
            learned_at=merged,
            recorded_at=merged,
            created_by="narrative_segmenter",
            title=clean_title,
            description=target_description.strip(),
            segment_time=TemporalExtent.point(merged),
            segment_status=NarrativeSegmentStatus.OPEN,
            dimension_refs=unique_dim_refs,
            key_event_refs=unique_event_refs,
            key_claim_refs=unique_claim_refs,
            participant_refs=unique_participant_refs,
            supersedes_ref=None,
            merged_into_ref=None,
            life_chapter_ref=None,
            theme_tags=sorted(all_tags),
            coherence_score=0.7,
            metadata={"merge_sources": [r.object_id for r in source_segment_refs]},
        )

        # 2. Forward-revise all source segments to MERGED pointing to target_ref
        retired_segments: list[NarrativeSegment] = []
        merge_deps: list[Dependency] = []
        for seg in source_segments:
            seg_next_rev = seg.revision + 1
            meta = dict(seg.metadata)
            meta["merged_at"] = merged.isoformat()
            meta["merged_into"] = target_id
            retired = NarrativeSegment(
                object_id=seg.object_id,
                revision=seg_next_rev,
                subject_id=seg.subject_id,
                occurred=seg.occurred,
                learned_at=merged,
                recorded_at=merged,
                created_by="narrative_segmenter",
                title=seg.title,
                description=seg.description,
                segment_time=seg.segment_time,
                segment_status=NarrativeSegmentStatus.MERGED,
                dimension_refs=seg.dimension_refs,
                key_event_refs=seg.key_event_refs,
                key_claim_refs=seg.key_claim_refs,
                participant_refs=seg.participant_refs,
                supersedes_ref=ObjectRef(object_id=seg.object_id, revision=seg.revision),
                merged_into_ref=target_ref,
                life_chapter_ref=seg.life_chapter_ref,
                theme_tags=seg.theme_tags,
                coherence_score=seg.coherence_score,
                metadata=meta,
            )
            retired_segments.append(retired)
            merge_deps.append(
                Dependency(
                    object_id=_stable_id("dep", seg.object_id, seg_next_rev, target_id, 1),
                    subject_id=self.subject_id,
                    learned_at=merged,
                    recorded_at=merged,
                    created_by="narrative_segmenter:dependency",
                    dependent_ref=ObjectRef(object_id=seg.object_id, revision=seg_next_rev),
                    dependency_ref=target_ref,
                    dependency_type="narrative_segment_merged_into",
                )
            )

        operation = OperationRequest(
            operation_name="narrative.segment.merge",
            arguments={
                "target_id": target_id,
                "sources": [r.object_id for r in source_segment_refs],
            },
            expected_world_revision=int(self.store.current_world_revision()),
            reason=f"merge {len(source_segment_refs)} segments into {clean_title}",
            idempotency_key=f"narrative-merge:{target_id}:1",
            source_class=SourceClass.AI_COGNITION,
        )

        result = self.store.commit([new_segment, *retired_segments, *merge_deps], operation)
        self._catch_up()
        return NarrativeSegmentReceipt(
            segment_id=target_id,
            revision=1,
            status=NarrativeSegmentStatus.OPEN,
            world_revision=result.world_revision,
        )

    def get_segment(self, segment_id: str, revision: int | None = None) -> NarrativeSegment:
        """Fetch a specific narrative segment by id and optional revision."""
        payload = self.store.get_payload(segment_id, revision=revision)
        return NarrativeSegment.model_validate(payload)

    def list_segments(
        self,
        *,
        status: NarrativeSegmentStatus | None = None,
        dimension_id: str | None = None,
    ) -> tuple[NarrativeSegment, ...]:
        """Query narrative segments with optional status and dimension filters."""
        payloads = self.store.list_payloads(
            object_type=ObjectType.NARRATIVE_SEGMENT,
            subject_id=self.subject_id,
        )
        segments: list[NarrativeSegment] = []
        for payload in payloads:
            seg = NarrativeSegment.model_validate(payload)
            if status is not None and seg.segment_status != status:
                continue
            if dimension_id is not None:
                dim_ids = {r.object_id for r in seg.dimension_refs}
                if dimension_id not in dim_ids:
                    continue
            segments.append(seg)
        return tuple(segments)

    def suggest_segment_closure(
        self,
        segment_id: str,
        *,
        max_events: int = 50,
        max_time_span_days: int = 30,
    ) -> tuple[bool, str]:
        """Heuristic analysis of whether an open segment should be sealed.
        
        Evaluates event count threshold and temporal duration span without
        substituting for model reasoning.
        """
        seg = self.get_segment(segment_id)
        if seg.segment_status != NarrativeSegmentStatus.OPEN:
            return False, f"segment is already {seg.segment_status.value}"

        if len(seg.key_event_refs) >= max_events:
            return True, f"event count ({len(seg.key_event_refs)}) exceeded capacity threshold ({max_events})"

        if seg.occurred.start is not None and seg.occurred.end is not None:
            span_days = (seg.occurred.end - seg.occurred.start).total_seconds() / 86400.0
            if span_days >= max_time_span_days:
                return True, f"temporal span ({span_days:.1f} days) exceeded closure threshold ({max_time_span_days} days)"

        return False, "segment remains within cohesive accumulation bounds"
