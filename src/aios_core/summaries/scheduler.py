"""Deterministic scheduling for model-generated summaries across every dimension.

The scheduler owns time windows, dimension discovery, source selection, idempotent
skip logic and budgets. It never writes semantic summary text itself. A supplied
model handler receives a DimensionSummaryInput and returns descriptive content.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Callable, Sequence

from aios_core.contracts.enums import ObjectType
from aios_core.contracts.time import as_utc
from aios_core.query.search import derive_dimension, WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.contracts.refs import ObjectRef

from .cognitive_derivation import CognitiveDerivationReconcileResult, CognitiveDerivationScheduler
from .dimension_summary import DimensionSummaryInput, DimensionSummaryService, SummaryCommit

UTC = timezone.utc


class SummaryScale(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    HALF_YEAR = "half_year"
    YEAR = "year"
    MULTI_YEAR_3Y = "multi_year_3y"
    MULTI_YEAR_5Y = "multi_year_5y"
    DECADE = "decade"


SCALE_LADDER: tuple[SummaryScale, ...] = (
    SummaryScale.DAY,
    SummaryScale.WEEK,
    SummaryScale.MONTH,
    SummaryScale.QUARTER,
    SummaryScale.HALF_YEAR,
    SummaryScale.YEAR,
    SummaryScale.MULTI_YEAR_3Y,
    SummaryScale.MULTI_YEAR_5Y,
    SummaryScale.DECADE,
)


@dataclass(frozen=True, slots=True)
class ScheduledSummaryJob:
    dimension: str
    scale: SummaryScale
    window_start: datetime
    window_end: datetime
    source_count: int


@dataclass(frozen=True, slots=True)
class SummaryScheduleResult:
    attempted_jobs: tuple[ScheduledSummaryJob, ...]
    commits: tuple[SummaryCommit, ...]
    skipped_unchanged: tuple[ScheduledSummaryJob, ...]
    skipped_empty: tuple[ScheduledSummaryJob, ...]
    truncated: bool


def window_bounds(moment: datetime, scale: SummaryScale) -> tuple[datetime, datetime]:
    dt = as_utc(moment, "moment")
    if scale is SummaryScale.DAY:
        start = datetime(dt.year, dt.month, dt.day, tzinfo=UTC)
        return start, start + timedelta(days=1) - timedelta(microseconds=1)
    if scale is SummaryScale.WEEK:
        day = datetime(dt.year, dt.month, dt.day, tzinfo=UTC)
        start = day - timedelta(days=dt.isoweekday() - 1)
        return start, start + timedelta(days=7) - timedelta(microseconds=1)
    if scale is SummaryScale.MONTH:
        start = datetime(dt.year, dt.month, 1, tzinfo=UTC)
        month = dt.month % 12 + 1
        year = dt.year + (dt.month // 12)
        return start, datetime(year, month, 1, tzinfo=UTC) - timedelta(microseconds=1)
    if scale is SummaryScale.QUARTER:
        month = ((dt.month - 1) // 3) * 3 + 1
        start = datetime(dt.year, month, 1, tzinfo=UTC)
        end_month = month + 3
        year = dt.year + (end_month - 1) // 12
        normalized = (end_month - 1) % 12 + 1
        return start, datetime(year, normalized, 1, tzinfo=UTC) - timedelta(microseconds=1)
    if scale is SummaryScale.HALF_YEAR:
        month = 1 if dt.month <= 6 else 7
        start = datetime(dt.year, month, 1, tzinfo=UTC)
        end_month = month + 6
        year = dt.year + (end_month - 1) // 12
        normalized = (end_month - 1) % 12 + 1
        return start, datetime(year, normalized, 1, tzinfo=UTC) - timedelta(microseconds=1)
    if scale is SummaryScale.YEAR:
        start = datetime(dt.year, 1, 1, tzinfo=UTC)
        return start, datetime(dt.year + 1, 1, 1, tzinfo=UTC) - timedelta(microseconds=1)
    if scale is SummaryScale.MULTI_YEAR_3Y:
        start_year = (dt.year // 3) * 3
        start = datetime(start_year, 1, 1, tzinfo=UTC)
        return start, datetime(start_year + 3, 1, 1, tzinfo=UTC) - timedelta(microseconds=1)
    if scale is SummaryScale.MULTI_YEAR_5Y:
        start_year = (dt.year // 5) * 5
        start = datetime(start_year, 1, 1, tzinfo=UTC)
        return start, datetime(start_year + 5, 1, 1, tzinfo=UTC) - timedelta(microseconds=1)
    if scale is SummaryScale.DECADE:
        start_year = (dt.year // 10) * 10
        start = datetime(start_year, 1, 1, tzinfo=UTC)
        return start, datetime(start_year + 10, 1, 1, tzinfo=UTC) - timedelta(microseconds=1)
    raise ValueError(f"unsupported summary scale: {scale}")


def previous_closed_window(now: datetime, scale: SummaryScale) -> tuple[datetime, datetime]:
    current_start, _ = window_bounds(now, scale)
    return window_bounds(current_start - timedelta(microseconds=1), scale)


class MultiScaleSummaryScheduler:
    def __init__(
        self,
        *,
        store: SQLiteWorldStore,
        index: WorldSearchIndex,
        summary_handler: Callable[[DimensionSummaryInput], str],
        subject_id: str = "user_1",
        max_source_objects: int = 500,
        source_subject_ids: Sequence[str] | None = None,
        cognitive_derivation_scheduler: CognitiveDerivationScheduler | None = None,
    ) -> None:
        self.store = store
        self.index = index
        self.summary_handler = summary_handler
        self.subject_id = subject_id
        self.source_subject_ids = tuple(dict.fromkeys((subject_id, *(source_subject_ids or ()))))
        self.service = DimensionSummaryService(
            store=store,
            index=index,
            subject_id=subject_id,
            max_source_objects=max_source_objects,
            source_subject_ids=self.source_subject_ids,
        )
        self.cognitive_derivation_scheduler = (
            cognitive_derivation_scheduler
            or CognitiveDerivationScheduler(
                store=store,
                index=index,
                subject_id=subject_id,
                allowed_subject_ids=self.source_subject_ids,
            )
        )

    def reconcile_cognitive_derivation(self) -> CognitiveDerivationReconcileResult:
        """Re-ensure durable C14 opportunities after process restart."""

        return self.cognitive_derivation_scheduler.reconcile()

    def _source_payloads(self) -> list[dict]:
        return [payload for subject in self.source_subject_ids
                for payload in self.store.list_payloads(subject_id=subject)]

    def active_dimensions(self) -> tuple[str, ...]:
        payloads = self._source_payloads()
        terminal = {"merged", "split", "rejected", "archived"}
        terminal_keys: set[str] = set()
        active_definition_keys: set[str] = set()

        for payload in payloads:
            if str(payload.get("object_type") or "") != ObjectType.DIMENSION_DEFINITION.value:
                continue
            metadata = payload.get("metadata")
            key = metadata.get("dimension_key") if isinstance(metadata, dict) else None
            if not isinstance(key, str) or not key.strip():
                continue
            lifecycle = str(payload.get("lifecycle") or "").strip().lower()
            if lifecycle in terminal:
                terminal_keys.add(key.strip())
            else:
                active_definition_keys.add(key.strip())

        dimensions: set[str] = set(active_definition_keys)
        for payload in payloads:
            object_type = str(payload.get("object_type") or "")
            if object_type == ObjectType.DIMENSION_DEFINITION.value:
                continue
            dimension = derive_dimension(payload, object_type)
            if (
                dimension
                and dimension != "dim_unclassified"
                and dimension not in terminal_keys
            ):
                dimensions.add(dimension)
        return tuple(sorted(dimensions))

    @staticmethod
    def _payload_time(payload: dict) -> datetime | None:
        occurred = payload.get("occurred")
        if isinstance(occurred, dict):
            raw = occurred.get("start")
            if isinstance(raw, str):
                try:
                    return as_utc(
                        datetime.fromisoformat(raw.replace("Z", "+00:00")),
                        "occurred.start",
                    )
                except ValueError:
                    pass
        raw = payload.get("recorded_at")
        if isinstance(raw, str):
            try:
                return as_utc(
                    datetime.fromisoformat(raw.replace("Z", "+00:00")),
                    "recorded_at",
                )
            except ValueError:
                pass
        return None

    def _candidate_windows(
        self,
        *,
        now: datetime,
        scale: SummaryScale,
        dimension: str,
    ) -> tuple[tuple[datetime, datetime], ...]:
        current_start, _ = window_bounds(now, scale)
        windows: set[tuple[datetime, datetime]] = set()
        for payload in self._source_payloads():
            object_type = str(payload.get("object_type") or "")
            if derive_dimension(payload, object_type) != dimension:
                continue
            at = self._payload_time(payload)
            if at is None:
                continue
            start, end = window_bounds(at, scale)
            if end < current_start:
                windows.add((start, end))
        return tuple(sorted(windows, key=lambda item: item[0]))

    @staticmethod
    def _source_identity(prepared: DimensionSummaryInput) -> tuple[tuple[str, int], ...]:
        return tuple((item.object_id, item.revision) for item in prepared.sources)

    def _matching_current_summary(self, prepared: DimensionSummaryInput) -> dict | None:
        for payload in self.store.list_payloads(
            object_type=ObjectType.SUMMARY,
            subject_id=self.subject_id,
        ):
            metadata = payload.get("metadata")
            if not isinstance(metadata, dict) or metadata.get("dimension") != prepared.dimension:
                continue
            if str(payload.get("granularity") or "") != prepared.granularity:
                continue
            extent = payload.get("summary_time")
            if not isinstance(extent, dict):
                continue
            raw_start = extent.get("start")
            raw_end = extent.get("end")
            if not isinstance(raw_start, str) or not isinstance(raw_end, str):
                continue
            try:
                stored_start = as_utc(
                    datetime.fromisoformat(raw_start.replace("Z", "+00:00")),
                    "summary_time.start",
                )
                stored_end = as_utc(
                    datetime.fromisoformat(raw_end.replace("Z", "+00:00")),
                    "summary_time.end",
                )
            except ValueError:
                continue
            if stored_start != prepared.window_start:
                continue
            if stored_end != prepared.window_end:
                continue
            return payload
        return None

    def _unchanged(self, prepared: DimensionSummaryInput) -> bool:
        latest = self._matching_current_summary(prepared)
        if (latest is None or latest.get("summary_status") != "current"
                or latest.get("status", "active") != "active"):
            return False
        existing = tuple(
            (str(item.get("object_id")), int(item.get("revision") or 0))
            for item in (latest.get("source_refs") or [])
        )
        return existing == self._source_identity(prepared)

    def run_due(
        self,
        *,
        now: datetime,
        scales: Sequence[SummaryScale] = SCALE_LADDER,
        max_jobs: int = 64,
        dimensions: Sequence[str] | None = None,
    ) -> SummaryScheduleResult:
        """Drain all closed windows that actually contain world material.

        Unlike a single previous-window tick, this derives candidate windows from the
        durable world. Process downtime therefore cannot permanently skip old windows,
        and late-arriving facts automatically reopen their historical window because
        the prepared source identity changes.
        """

        if max_jobs < 1:
            raise ValueError("max_jobs must be >= 1")
        current = as_utc(now, "now")
        dims = tuple(dict.fromkeys(
            str(item).strip()
            for item in (dimensions or self.active_dimensions())
            if str(item).strip()
        ))
        jobs: list[ScheduledSummaryJob] = []
        commits: list[SummaryCommit] = []
        skipped_unchanged: list[ScheduledSummaryJob] = []
        skipped_empty: list[ScheduledSummaryJob] = []
        truncated = False
        semantic_jobs = 0

        # Close the commit -> crash -> missing-Wake gap before doing new work.
        self.reconcile_cognitive_derivation()

        for scale_value in scales:
            scale = SummaryScale(scale_value)
            for dimension in dims:
                for start, end in self._candidate_windows(
                    now=current,
                    scale=scale,
                    dimension=dimension,
                ):
                    prepared = self.service.prepare(
                        dimension=dimension,
                        granularity=scale.value,
                        window_start=start,
                        window_end=end,
                        include_summary_sources=(scale is not SummaryScale.DAY),
                    )
                    job = ScheduledSummaryJob(
                        dimension=dimension,
                        scale=scale,
                        window_start=start,
                        window_end=end,
                        source_count=len(prepared.sources),
                    )
                    jobs.append(job)

                    if not prepared.sources:
                        skipped_empty.append(job)
                        continue
                    if prepared.truncated:
                        # Never publish an incomplete Summary as CURRENT. If this
                        # window had an older CURRENT summary, forward-mark it STALE
                        # because the durable source set is now known to be incomplete.
                        self.service.mark_stale_if_present(
                            prepared,
                            changed_at=current,
                            reason="summary source window exceeds completeness cap",
                        )
                        truncated = True
                        continue
                    if self._unchanged(prepared):
                        skipped_unchanged.append(job)
                        continue
                    if semantic_jobs >= max_jobs:
                        truncated = True
                        continue

                    content = self.summary_handler(prepared)
                    if not isinstance(content, str) or not content.strip():
                        raise ValueError(
                            "dimension summary handler must return non-blank text"
                        )
                    committed = self.service.commit(
                        prepared,
                        content=content,
                        generated_at=current,
                    )
                    commits.append(committed)
                    self.cognitive_derivation_scheduler.ensure(
                        ObjectRef(
                            object_id=committed.object_id,
                            revision=committed.revision,
                        )
                    )
                    semantic_jobs += 1

        return SummaryScheduleResult(
            attempted_jobs=tuple(jobs),
            commits=tuple(commits),
            skipped_unchanged=tuple(skipped_unchanged),
            skipped_empty=tuple(skipped_empty),
            truncated=truncated,
        )
