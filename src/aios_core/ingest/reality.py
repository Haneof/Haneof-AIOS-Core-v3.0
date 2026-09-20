"""Reality-source adapters and mechanical cleaning for AIOS v3.0.

This module is intentionally cognition-free. It standardizes source identity,
timestamps, provenance and objectively configured numeric compression. It never
infers personality, emotion, intent, relationships or higher-level user meaning.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from aios_core.contracts.enums import ObjectType, SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent, TimePrecision, as_utc
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.idempotency import canonical_json_dumps
from aios_core.storage.sqlite_store import SQLiteWorldStore


AUDIT_DIMENSION = "dim:system_ingest_audit"


def _stable_id(prefix: str, *parts: object) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]}"


def _contains_binary(value: Any) -> bool:
    if isinstance(value, (bytes, bytearray, memoryview)):
        return True
    if isinstance(value, Mapping):
        return any(
            _contains_binary(key) or _contains_binary(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple, set, frozenset)):
        return any(_contains_binary(item) for item in value)
    return False


def _digest_payload(value: Any) -> str:
    return hashlib.sha256(
        canonical_json_dumps(value).encode("utf-8")
    ).hexdigest()


class SourceAdapterSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    adapter_id: str = Field(min_length=1)
    source_kind: str = Field(min_length=1)
    dimension: str = Field(min_length=1)
    source_class: SourceClass
    schema_version: str = Field(default="1", min_length=1)
    default_modality: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_spec(self) -> "SourceAdapterSpec":
        for name in (
            "adapter_id",
            "source_kind",
            "dimension",
            "schema_version",
            "default_modality",
        ):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must not be blank")
        if not self.dimension.startswith("dim:"):
            raise ValueError("dimension must be explicit and start with 'dim:'")
        if self.source_class not in {SourceClass.USER, SourceClass.SENSOR}:
            raise ValueError(
                "reality adapters may only write USER or SENSOR source classes"
            )
        return self


class RealityRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    external_record_id: str = Field(min_length=1)
    occurred_at: datetime
    value: Any
    modality: str | None = None
    unit: str | None = None
    source_locator: str | None = None
    received_at: datetime | None = None
    external_revision: str = "1"
    data_quality: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_record(self) -> "RealityRecord":
        if not self.external_record_id.strip():
            raise ValueError("external_record_id must not be blank")
        if self.modality is not None and not self.modality.strip():
            raise ValueError("modality must not be blank")
        if self.source_locator is not None and not self.source_locator.strip():
            raise ValueError("source_locator must not be blank")
        if not self.external_revision.strip():
            raise ValueError("external_revision must not be blank")
        as_utc(self.occurred_at, "occurred_at")
        if self.received_at is not None:
            as_utc(self.received_at, "received_at")
        if _contains_binary(self.value):
            raise ValueError(
                "raw binary payloads are not valid long-term AIOS reality facts"
            )
        if _contains_binary(self.provenance) or _contains_binary(self.data_quality):
            raise ValueError("binary provenance/data_quality is not allowed")
        return self


class MediaDescriptorRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    external_record_id: str = Field(min_length=1)
    occurred_at: datetime
    descriptor: str = Field(min_length=1)
    descriptor_kind: str = Field(min_length=1)
    source_locator: str = Field(min_length=1)
    received_at: datetime | None = None
    external_revision: str = "1"
    data_quality: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    object_facts: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_record(self) -> "MediaDescriptorRecord":
        for name in (
            "external_record_id",
            "descriptor",
            "descriptor_kind",
            "source_locator",
            "external_revision",
        ):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must not be blank")
        if any(not item.strip() for item in self.object_facts):
            raise ValueError("object_facts must not contain blank values")
        as_utc(self.occurred_at, "occurred_at")
        if self.received_at is not None:
            as_utc(self.received_at, "received_at")
        if _contains_binary(self.provenance) or _contains_binary(self.data_quality):
            raise ValueError("binary provenance/data_quality is not allowed")
        return self


class NumericSample(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    external_record_id: str = Field(min_length=1)
    occurred_at: datetime
    value: float
    source_locator: str | None = None

    @model_validator(mode="after")
    def validate_sample(self) -> "NumericSample":
        if not self.external_record_id.strip():
            raise ValueError("external_record_id must not be blank")
        as_utc(self.occurred_at, "occurred_at")
        return self


class MechanicalSeriesPolicy(BaseModel):
    """Explicit engineering policy; it carries no semantic/psychological meaning."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tolerance: float = Field(ge=0.0)
    change_threshold: float = Field(gt=0.0)
    max_gap_seconds: float = Field(default=300.0, gt=0.0)
    minimum_segment_samples: int = Field(default=1, ge=1)


@dataclass(frozen=True, slots=True)
class IngestReceipt:
    observation_id: str
    world_revision: int
    reused_existing: bool


@dataclass(frozen=True, slots=True)
class IngestFailureReceipt:
    audit_observation_id: str
    world_revision: int
    error_type: str


@dataclass(frozen=True, slots=True)
class MechanicalSeriesReceipt:
    series_id: str
    segment_observation_ids: tuple[str, ...]
    change_observation_ids: tuple[str, ...]
    input_sample_count: int
    world_revision: int
    reused_existing_count: int


class RealityIngestService:
    """Cognition-free ingestion into the unified WorldStore."""

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

    @staticmethod
    def _locator(
        spec: SourceAdapterSpec,
        *,
        external_record_id: str,
        source_locator: str | None,
    ) -> str:
        if source_locator is not None and source_locator.strip():
            return source_locator.strip()
        return (
            f"adapter://{spec.adapter_id.strip()}/"
            f"{external_record_id.strip()}"
        )

    def _observation_from_record(
        self,
        spec: SourceAdapterSpec,
        record: RealityRecord,
    ) -> Observation:
        occurred_original = record.occurred_at.isoformat()
        occurred = as_utc(record.occurred_at, "occurred_at")
        learned = as_utc(
            record.received_at or datetime.now(timezone.utc),
            "received_at",
        )
        modality = (
            record.modality.strip()
            if record.modality is not None
            else spec.default_modality.strip()
        )
        identity = {
            "adapter_id": spec.adapter_id,
            "external_record_id": record.external_record_id,
            "external_revision": record.external_revision,
        }
        source_digest = _digest_payload(
            {
                **identity,
                "occurred_at": occurred.isoformat(),
                "value": record.value,
                "modality": modality,
                "unit": record.unit,
                "data_quality": record.data_quality,
                "provenance": record.provenance,
            }
        )
        object_id = _stable_id(
            "obs_src",
            spec.adapter_id,
            record.external_record_id,
            record.external_revision,
        )
        return Observation(
            object_id=object_id,
            subject_id=self.subject_id,
            occurred=TemporalExtent.point(occurred),
            learned_at=learned,
            recorded_at=learned,
            created_by=f"reality_ingest:{spec.adapter_id}",
            source_kind=spec.source_kind.strip(),
            modality=modality,
            value=record.value,
            unit=record.unit,
            data_quality=dict(record.data_quality),
            raw_locator=self._locator(
                spec,
                external_record_id=record.external_record_id,
                source_locator=record.source_locator,
            ),
            metadata={
                "dimension": spec.dimension.strip(),
                "adapter_id": spec.adapter_id.strip(),
                "source_schema_version": spec.schema_version.strip(),
                "external_record_id": record.external_record_id.strip(),
                "external_revision": record.external_revision.strip(),
                "source_digest": source_digest,
                "occurred_at_original": occurred_original,
                "provenance": dict(record.provenance),
                "mechanical_ingest": True,
            },
        )

    def ingest_record(
        self,
        spec: SourceAdapterSpec,
        record: RealityRecord,
    ) -> IngestReceipt:
        observation = self._observation_from_record(spec, record)
        try:
            existing = self.store.get_payload(observation.object_id, revision=1)
        except Exception:
            existing = None
        if existing is not None:
            existing_digest = (
                existing.get("metadata") or {}
            ).get("source_digest")
            new_digest = observation.metadata["source_digest"]
            if existing_digest != new_digest:
                raise ValueError(
                    "source record identity conflict: same adapter/external id/revision "
                    "arrived with different fact content"
                )
            return IngestReceipt(
                observation_id=observation.object_id,
                world_revision=int(self.store.current_world_revision()),
                reused_existing=True,
            )

        result = self.store.commit(
            [observation],
            OperationRequest(
                operation_name="ingest.reality.record",
                arguments={
                    "adapter_id": spec.adapter_id,
                    "external_record_id": record.external_record_id,
                    "external_revision": record.external_revision,
                    "dimension": spec.dimension,
                },
                expected_world_revision=int(self.store.current_world_revision()),
                reason="persist canonical source fact without semantic interpretation",
                idempotency_key=(
                    f"reality:{spec.adapter_id}:"
                    f"{record.external_record_id}:{record.external_revision}"
                ),
                source_class=spec.source_class,
            ),
        )
        self._catch_up()
        return IngestReceipt(
            observation_id=observation.object_id,
            world_revision=result.world_revision,
            reused_existing=result.idempotent_replay,
        )

    def ingest_mapping(
        self,
        spec: SourceAdapterSpec,
        payload: Mapping[str, Any],
        *,
        failure_time: datetime | None = None,
    ) -> IngestReceipt | IngestFailureReceipt:
        try:
            record = RealityRecord.model_validate(dict(payload))
            return self.ingest_record(spec, record)
        except (ValidationError, ValueError) as exc:
            errors: list[dict[str, str]] = []
            if isinstance(exc, ValidationError):
                for error in exc.errors(include_input=False):
                    errors.append(
                        {
                            "location": ".".join(str(x) for x in error.get("loc", ())),
                            "type": str(error.get("type") or "validation_error"),
                        }
                    )
            else:
                errors.append({"location": "", "type": type(exc).__name__})
            external_id = str(
                payload.get("external_record_id")
                or _stable_id("unknown", spec.adapter_id, tuple(sorted(payload.keys())))
            )
            return self.record_failure(
                spec,
                external_record_id=external_id,
                occurred_at=failure_time or datetime.now(timezone.utc),
                source_locator=(
                    str(payload.get("source_locator"))
                    if payload.get("source_locator") is not None
                    else None
                ),
                error_type=type(exc).__name__,
                field_errors=errors,
            )

    def record_failure(
        self,
        spec: SourceAdapterSpec,
        *,
        external_record_id: str,
        occurred_at: datetime,
        source_locator: str | None,
        error_type: str,
        field_errors: Sequence[Mapping[str, str]] = (),
    ) -> IngestFailureReceipt:
        occurred = as_utc(occurred_at, "occurred_at")
        audit_id = _stable_id(
            "obs_ingest_failure",
            spec.adapter_id,
            external_record_id,
            error_type,
            tuple(
                (item.get("location", ""), item.get("type", ""))
                for item in field_errors
            ),
        )
        try:
            existing = self.store.get_payload(audit_id, revision=1)
        except Exception:
            existing = None
        if existing is not None:
            return IngestFailureReceipt(
                audit_observation_id=audit_id,
                world_revision=int(self.store.current_world_revision()),
                error_type=error_type,
            )

        audit = Observation(
            object_id=audit_id,
            subject_id=self.subject_id,
            occurred=TemporalExtent.point(occurred),
            learned_at=occurred,
            recorded_at=occurred,
            created_by=f"reality_ingest:{spec.adapter_id}:failure",
            source_kind="ingest_audit",
            modality="adapter_failure",
            value={
                "adapter_id": spec.adapter_id,
                "source_kind": spec.source_kind,
                "external_record_id": external_record_id,
                "error_type": error_type,
                "field_errors": [dict(item) for item in field_errors],
            },
            raw_locator=self._locator(
                spec,
                external_record_id=external_record_id,
                source_locator=source_locator,
            ),
            metadata={
                "dimension": AUDIT_DIMENSION,
                "adapter_id": spec.adapter_id,
                "source_dimension": spec.dimension,
                "mechanical_ingest_failure": True,
            },
        )
        result = self.store.commit(
            [audit],
            OperationRequest(
                operation_name="ingest.reality.failure",
                arguments={
                    "adapter_id": spec.adapter_id,
                    "external_record_id": external_record_id,
                    "error_type": error_type,
                },
                expected_world_revision=int(self.store.current_world_revision()),
                reason="audit source-adapter record that could not enter the fact world",
                idempotency_key=f"reality-failure:{audit_id}",
                source_class=spec.source_class,
            ),
        )
        self._catch_up()
        return IngestFailureReceipt(
            audit_observation_id=audit_id,
            world_revision=result.world_revision,
            error_type=error_type,
        )

    def ingest_media_descriptor(
        self,
        spec: SourceAdapterSpec,
        record: MediaDescriptorRecord,
    ) -> IngestReceipt:
        value = record.descriptor.strip()
        if record.object_facts:
            value = value + "\n" + "\n".join(
                f"OBJECT: {item.strip()}" for item in record.object_facts
            )
        return self.ingest_record(
            spec,
            RealityRecord(
                external_record_id=record.external_record_id,
                occurred_at=record.occurred_at,
                received_at=record.received_at,
                external_revision=record.external_revision,
                value=value,
                modality=record.descriptor_kind.strip(),
                source_locator=record.source_locator,
                data_quality=record.data_quality,
                provenance={
                    **record.provenance,
                    "media_descriptor": True,
                    "raw_media_retained": False,
                    "object_facts_count": len(record.object_facts),
                },
            ),
        )

    def ingest_numeric_series(
        self,
        spec: SourceAdapterSpec,
        *,
        series_id: str,
        samples: Sequence[NumericSample],
        policy: MechanicalSeriesPolicy,
        unit: str | None = None,
        received_at: datetime | None = None,
    ) -> MechanicalSeriesReceipt:
        if spec.source_class is not SourceClass.SENSOR:
            raise ValueError("numeric stream compression requires SENSOR source_class")
        if not series_id.strip():
            raise ValueError("series_id must not be blank")
        if not samples:
            raise ValueError("samples must not be empty")

        ordered = sorted(
            samples,
            key=lambda item: (
                as_utc(item.occurred_at, "occurred_at"),
                item.external_record_id,
            ),
        )
        seen_ids: set[str] = set()
        for sample in ordered:
            if sample.external_record_id in seen_ids:
                raise ValueError("duplicate external_record_id inside numeric batch")
            seen_ids.add(sample.external_record_id)

        segments: list[list[NumericSample]] = []
        current: list[NumericSample] = []
        running_sum = 0.0
        changes: list[tuple[NumericSample, NumericSample]] = []
        previous: NumericSample | None = None

        for sample in ordered:
            at = as_utc(sample.occurred_at, "occurred_at")
            if previous is not None:
                prev_at = as_utc(previous.occurred_at, "occurred_at")
                if abs(sample.value - previous.value) >= policy.change_threshold:
                    changes.append((previous, sample))
                gap = (at - prev_at).total_seconds()
            else:
                gap = 0.0

            if not current:
                current = [sample]
                running_sum = sample.value
            else:
                mean = running_sum / len(current)
                if (
                    gap <= policy.max_gap_seconds
                    and abs(sample.value - mean) <= policy.tolerance
                ):
                    current.append(sample)
                    running_sum += sample.value
                else:
                    segments.append(current)
                    current = [sample]
                    running_sum = sample.value
            previous = sample
        if current:
            segments.append(current)

        observations: list[Observation] = []
        segment_ids: list[str] = []
        change_ids: list[str] = []
        learned = as_utc(
            received_at or datetime.now(timezone.utc),
            "received_at",
        )
        policy_payload = policy.model_dump(mode="json")

        for index, segment in enumerate(segments):
            start = as_utc(segment[0].occurred_at, "occurred_at")
            end = as_utc(segment[-1].occurred_at, "occurred_at")
            values = [item.value for item in segment]
            record_ids = [item.external_record_id for item in segment]
            object_id = _stable_id(
                "obs_num_segment",
                spec.adapter_id,
                series_id,
                tuple(record_ids),
            )
            segment_ids.append(object_id)
            observations.append(
                Observation(
                    object_id=object_id,
                    subject_id=self.subject_id,
                    occurred=TemporalExtent(
                        start=start,
                        end=end,
                        precision=TimePrecision.SECOND,
                        timezone_name="UTC",
                    ),
                    learned_at=learned,
                    recorded_at=learned,
                    created_by=f"reality_ingest:{spec.adapter_id}:numeric",
                    source_kind=spec.source_kind,
                    modality="numeric_segment",
                    value={
                        "mean": sum(values) / len(values),
                        "min": min(values),
                        "max": max(values),
                        "sample_count": len(values),
                    },
                    unit=unit,
                    data_quality={
                        "compression": "mechanical_tolerance_segment",
                        "policy": policy_payload,
                    },
                    raw_locator=(
                        f"adapter://{spec.adapter_id}/series/{series_id}/"
                        f"segment/{index}"
                    ),
                    metadata={
                        "dimension": spec.dimension,
                        "adapter_id": spec.adapter_id,
                        "series_id": series_id,
                        "mechanical_ingest": True,
                        "mechanical_compression": True,
                        "source_record_ids": record_ids,
                        "raw_sample_values_retained": False,
                    },
                )
            )

        for before, after in changes:
            at = as_utc(after.occurred_at, "occurred_at")
            object_id = _stable_id(
                "obs_num_change",
                spec.adapter_id,
                series_id,
                before.external_record_id,
                after.external_record_id,
            )
            change_ids.append(object_id)
            observations.append(
                Observation(
                    object_id=object_id,
                    subject_id=self.subject_id,
                    occurred=TemporalExtent.point(at),
                    learned_at=learned,
                    recorded_at=learned,
                    created_by=f"reality_ingest:{spec.adapter_id}:numeric",
                    source_kind=spec.source_kind,
                    modality="numeric_change",
                    value={
                        "previous": before.value,
                        "current": after.value,
                        "delta": after.value - before.value,
                        "absolute_delta": abs(after.value - before.value),
                    },
                    unit=unit,
                    data_quality={
                        "change_threshold": policy.change_threshold,
                        "policy": policy_payload,
                    },
                    raw_locator=(
                        after.source_locator
                        or f"adapter://{spec.adapter_id}/series/{series_id}/"
                        f"{after.external_record_id}"
                    ),
                    metadata={
                        "dimension": spec.dimension,
                        "adapter_id": spec.adapter_id,
                        "series_id": series_id,
                        "mechanical_ingest": True,
                        "mechanical_threshold_event": True,
                        "source_record_ids": [
                            before.external_record_id,
                            after.external_record_id,
                        ],
                    },
                )
            )

        new_objects: list[Observation] = []
        reused = 0
        for observation in observations:
            try:
                existing = self.store.get_payload(
                    observation.object_id,
                    revision=1,
                )
            except Exception:
                existing = None
            if existing is None:
                new_objects.append(observation)
            else:
                reused += 1

        world_revision = int(self.store.current_world_revision())
        if new_objects:
            result = self.store.commit(
                new_objects,
                OperationRequest(
                    operation_name="ingest.reality.numeric_series",
                    arguments={
                        "adapter_id": spec.adapter_id,
                        "series_id": series_id,
                        "input_sample_count": len(ordered),
                        "segment_count": len(segment_ids),
                        "change_count": len(change_ids),
                    },
                    expected_world_revision=world_revision,
                    reason=(
                        "mechanically compress numeric source stream without "
                        "semantic interpretation"
                    ),
                    idempotency_key=(
                        f"numeric-series:{spec.adapter_id}:{series_id}:"
                        f"{_digest_payload([x.model_dump(mode='json') for x in ordered])}"
                    ),
                    source_class=spec.source_class,
                ),
            )
            world_revision = result.world_revision
            self._catch_up()

        return MechanicalSeriesReceipt(
            series_id=series_id,
            segment_observation_ids=tuple(segment_ids),
            change_observation_ids=tuple(change_ids),
            input_sample_count=len(ordered),
            world_revision=world_revision,
            reused_existing_count=reused,
        )
