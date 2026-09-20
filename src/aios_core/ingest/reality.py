"""Reality-source adapters and mechanical cleaning for AIOS v3.0.

This module is intentionally cognition-free. It standardizes source identity,
timestamps, provenance and objectively configured numeric compression. It never
infers personality, emotion, intent, relationships or higher-level user meaning.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, fields as dataclass_fields, is_dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    ValidationError,
    field_validator,
    model_validator,
)

from aios_core.contracts.enums import ErrorCode, ObjectType, SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent, TimePrecision, as_utc
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.idempotency import canonical_json_dumps
from aios_core.storage.sqlite_store import SQLiteWorldStore, StoreError


AUDIT_DIMENSION = "dim:system_ingest_audit"


def _stable_id(prefix: str, *parts: object) -> str:
    """Hash a structured identity without delimiter-boundary ambiguity."""
    raw = canonical_json_dumps(list(parts))
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]}"


def _contains_binary(
    value: Any,
    *,
    _active: set[int] | None = None,
) -> bool:
    """Detect raw binary recursively without crashing on cyclic containers."""
    if isinstance(value, (bytes, bytearray, memoryview)):
        return True
    if value is None or isinstance(value, (str, int, float, bool)):
        return False

    if _active is None:
        _active = set()
    marker = id(value)
    if marker in _active:
        return False

    if isinstance(value, BaseModel):
        _active.add(marker)
        try:
            return any(
                _contains_binary(
                    getattr(value, field_name),
                    _active=_active,
                )
                for field_name in type(value).model_fields
            )
        finally:
            _active.remove(marker)

    if is_dataclass(value) and not isinstance(value, type):
        _active.add(marker)
        try:
            return any(
                _contains_binary(
                    getattr(value, field.name),
                    _active=_active,
                )
                for field in dataclass_fields(value)
            )
        finally:
            _active.remove(marker)

    if isinstance(value, Mapping):
        _active.add(marker)
        try:
            return any(
                _contains_binary(key, _active=_active)
                or _contains_binary(item, _active=_active)
                for key, item in value.items()
            )
        finally:
            _active.remove(marker)

    if isinstance(value, (list, tuple, set, frozenset)):
        _active.add(marker)
        try:
            return any(
                _contains_binary(item, _active=_active)
                for item in value
            )
        finally:
            _active.remove(marker)

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

    @field_validator(
        "adapter_id",
        "source_kind",
        "dimension",
        "schema_version",
        "default_modality",
        mode="before",
    )
    @classmethod
    def normalize_identity_text(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value

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
    occurred_end_at: datetime | None = None
    value: Any
    modality: str | None = None
    unit: str | None = None
    source_locator: str | None = None
    received_at: datetime | None = None
    external_revision: str = "1"
    data_quality: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)

    @field_validator("external_record_id", "external_revision", mode="before")
    @classmethod
    def normalize_identity_text(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value

    @field_validator("modality", "unit", "source_locator", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: Any) -> Any:
        if value is None:
            return None
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_record(self) -> "RealityRecord":
        if not self.external_record_id:
            raise ValueError("external_record_id must not be blank")
        if self.modality is not None and not self.modality:
            raise ValueError("modality must not be blank")
        if self.unit is not None and not self.unit:
            raise ValueError("unit must not be blank")
        if self.source_locator is not None and not self.source_locator:
            raise ValueError("source_locator must not be blank")
        if not self.external_revision:
            raise ValueError("external_revision must not be blank")
        occurred = as_utc(self.occurred_at, "occurred_at")
        if self.occurred_end_at is not None:
            occurred_end = as_utc(self.occurred_end_at, "occurred_end_at")
            if occurred_end < occurred:
                raise ValueError("occurred_end_at must not be before occurred_at")
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
    occurred_end_at: datetime | None = None
    descriptor: str = Field(min_length=1)
    descriptor_kind: str = Field(min_length=1)
    source_locator: str = Field(min_length=1)
    received_at: datetime | None = None
    external_revision: str = "1"
    data_quality: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    object_facts: tuple[str, ...] = ()

    @field_validator(
        "external_record_id",
        "descriptor",
        "descriptor_kind",
        "source_locator",
        "external_revision",
        mode="before",
    )
    @classmethod
    def normalize_text_fields(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value

    @field_validator("object_facts", mode="before")
    @classmethod
    def normalize_object_facts(cls, value: Any) -> Any:
        if isinstance(value, (list, tuple)):
            return tuple(
                item.strip() if isinstance(item, str) else item
                for item in value
            )
        return value

    @model_validator(mode="after")
    def validate_record(self) -> "MediaDescriptorRecord":
        for name in (
            "external_record_id",
            "descriptor",
            "descriptor_kind",
            "source_locator",
            "external_revision",
        ):
            if not str(getattr(self, name)):
                raise ValueError(f"{name} must not be blank")
        if any(not item for item in self.object_facts):
            raise ValueError("object_facts must not contain blank values")
        occurred = as_utc(self.occurred_at, "occurred_at")
        if self.occurred_end_at is not None:
            occurred_end = as_utc(self.occurred_end_at, "occurred_end_at")
            if occurred_end < occurred:
                raise ValueError("occurred_end_at must not be before occurred_at")
        if self.received_at is not None:
            as_utc(self.received_at, "received_at")
        if _contains_binary(self.provenance) or _contains_binary(self.data_quality):
            raise ValueError("binary provenance/data_quality is not allowed")
        return self


class NumericSample(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    external_record_id: str = Field(min_length=1)
    occurred_at: datetime
    value: FiniteFloat
    source_locator: str | None = None

    @field_validator("external_record_id", "source_locator", mode="before")
    @classmethod
    def normalize_text_fields(cls, value: Any) -> Any:
        if value is None:
            return None
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_sample(self) -> "NumericSample":
        if not self.external_record_id:
            raise ValueError("external_record_id must not be blank")
        if self.source_locator is not None and not self.source_locator:
            raise ValueError("source_locator must not be blank")
        as_utc(self.occurred_at, "occurred_at")
        return self


class MechanicalSeriesPolicy(BaseModel):
    """Explicit engineering policy; it carries no semantic/psychological meaning."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tolerance: FiniteFloat = Field(ge=0.0)
    change_threshold: FiniteFloat = Field(gt=0.0)
    max_gap_seconds: FiniteFloat = Field(default=300.0, gt=0.0)


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
        if not isinstance(subject_id, str) or not subject_id.strip():
            raise ValueError("subject_id must not be blank")
        self.store = store
        self.index = index
        self.subject_id = subject_id.strip()

    @staticmethod
    def _validated_spec(spec: SourceAdapterSpec) -> SourceAdapterSpec:
        # Pydantic model_copy(update=...) does not validate updates. Public ingest
        # boundaries therefore revalidate frozen model snapshots before trusting
        # adapter identity or source-class semantics.
        return SourceAdapterSpec.model_validate(
            spec.model_dump(mode="python", round_trip=True)
        )

    @staticmethod
    def _validated_record(record: RealityRecord) -> RealityRecord:
        return RealityRecord.model_validate(
            record.model_dump(mode="python", round_trip=True)
        )

    @staticmethod
    def _validated_media_record(
        record: MediaDescriptorRecord,
    ) -> MediaDescriptorRecord:
        return MediaDescriptorRecord.model_validate(
            record.model_dump(mode="python", round_trip=True)
        )

    @staticmethod
    def _validated_sample(sample: NumericSample) -> NumericSample:
        return NumericSample.model_validate(
            sample.model_dump(mode="python", round_trip=True)
        )

    @staticmethod
    def _validated_policy(
        policy: MechanicalSeriesPolicy,
    ) -> MechanicalSeriesPolicy:
        return MechanicalSeriesPolicy.model_validate(
            policy.model_dump(mode="python", round_trip=True)
        )

    def _catch_up(self) -> None:
        if self.index is not None:
            self.index.catch_up()

    @staticmethod
    def _adapter_identity(spec: SourceAdapterSpec) -> dict[str, str]:
        return {
            "adapter_id": spec.adapter_id,
            "source_kind": spec.source_kind,
            "dimension": spec.dimension,
            "source_class": spec.source_class.value,
            "schema_version": spec.schema_version,
        }

    def _get_payload_if_exists(self, object_id: str) -> dict[str, Any] | None:
        try:
            return self.store.get_payload(object_id, revision=1)
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
        occurred_end = (
            as_utc(record.occurred_end_at, "occurred_end_at")
            if record.occurred_end_at is not None
            else None
        )
        occurred_extent = (
            TemporalExtent(
                start=occurred,
                end=occurred_end,
                precision=TimePrecision.SECOND,
                timezone_name="UTC",
            )
            if occurred_end is not None
            else TemporalExtent.point(occurred)
        )
        learned = as_utc(
            record.received_at or datetime.now(timezone.utc),
            "received_at",
        )
        modality = (
            record.modality
            if record.modality is not None
            else spec.default_modality
        )
        locator = self._locator(
            spec,
            external_record_id=record.external_record_id,
            source_locator=record.source_locator,
        )
        adapter_identity = self._adapter_identity(spec)
        source_digest = _digest_payload(
            {
                "subject_id": self.subject_id,
                "adapter": adapter_identity,
                "external_record_id": record.external_record_id,
                "external_revision": record.external_revision,
                "occurred_at": occurred.isoformat(),
                "occurred_end_at": (
                    occurred_end.isoformat() if occurred_end is not None else None
                ),
                "value": record.value,
                "modality": modality,
                "unit": record.unit,
                "data_quality": record.data_quality,
                "provenance": record.provenance,
                "source_locator": locator,
            }
        )
        object_id = _stable_id(
            "obs_src",
            self.subject_id,
            spec.adapter_id,
            record.external_record_id,
            record.external_revision,
        )
        metadata = {
            "dimension": spec.dimension,
            "adapter_id": spec.adapter_id,
            "source_schema_version": spec.schema_version,
            "source_class": spec.source_class.value,
            "external_record_id": record.external_record_id,
            "external_revision": record.external_revision,
            "source_digest": source_digest,
            "occurred_at_original": occurred_original,
            "provenance": dict(record.provenance),
            "mechanical_ingest": True,
        }
        if record.occurred_end_at is not None:
            metadata["occurred_end_at_original"] = record.occurred_end_at.isoformat()

        return Observation(
            object_id=object_id,
            subject_id=self.subject_id,
            occurred=occurred_extent,
            learned_at=learned,
            recorded_at=learned,
            created_by=f"reality_ingest:{spec.adapter_id}",
            source_kind=spec.source_kind,
            modality=modality,
            value=record.value,
            unit=record.unit,
            data_quality=dict(record.data_quality),
            raw_locator=locator,
            metadata=metadata,
        )

    def ingest_record(
        self,
        spec: SourceAdapterSpec,
        record: RealityRecord,
    ) -> IngestReceipt:
        spec = self._validated_spec(spec)
        record = self._validated_record(record)
        observation = self._observation_from_record(spec, record)
        existing = self._get_payload_if_exists(observation.object_id)
        if existing is not None:
            existing_digest = (
                existing.get("metadata") or {}
            ).get("source_digest")
            new_digest = observation.metadata["source_digest"]
            if existing_digest != new_digest:
                raise ValueError(
                    "source record identity conflict: same subject/adapter/external "
                    "id/revision arrived with different fact or adapter semantics"
                )
            self._catch_up()
            return IngestReceipt(
                observation_id=observation.object_id,
                world_revision=int(self.store.current_world_revision()),
                reused_existing=True,
            )

        operation_id = _stable_id(
            "op_reality_record",
            self.subject_id,
            spec.adapter_id,
            record.external_record_id,
            record.external_revision,
        )
        result = self.store.commit(
            [observation],
            OperationRequest(
                operation_id=operation_id,
                operation_name="ingest.reality.record",
                arguments={
                    "subject_id": self.subject_id,
                    "adapter_id": spec.adapter_id,
                    "external_record_id": record.external_record_id,
                    "external_revision": record.external_revision,
                    "dimension": spec.dimension,
                    "source_class": spec.source_class.value,
                    "schema_version": spec.schema_version,
                },
                expected_world_revision=self._expected_revision_for_retry(operation_id),
                reason="persist canonical source fact without semantic interpretation",
                idempotency_key=f"reality:{operation_id}",
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
            raw_external_id = payload.get("external_record_id")
            external_id = (
                raw_external_id.strip()
                if isinstance(raw_external_id, str) and raw_external_id.strip()
                else _stable_id(
                    "unknown",
                    spec.adapter_id,
                    tuple(sorted(str(key) for key in payload.keys())),
                )
            )
            raw_external_revision = payload.get("external_revision", "1")
            external_revision = (
                raw_external_revision.strip()
                if isinstance(raw_external_revision, str)
                and raw_external_revision.strip()
                else "<invalid>"
            )
            return self.record_failure(
                spec,
                external_record_id=external_id,
                external_revision=external_revision,
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
        external_revision: str = "1",
        field_errors: Sequence[Mapping[str, str]] = (),
    ) -> IngestFailureReceipt:
        spec = self._validated_spec(spec)
        occurred = as_utc(occurred_at, "occurred_at")
        external_record_id = str(external_record_id).strip()
        external_revision = str(external_revision).strip()
        if not external_record_id:
            raise ValueError("external_record_id must not be blank")
        if not external_revision:
            raise ValueError("external_revision must not be blank")
        locator = self._locator(
            spec,
            external_record_id=external_record_id,
            source_locator=source_locator,
        )
        adapter_identity = self._adapter_identity(spec)
        normalized_errors = tuple(
            (str(item.get("location", "")), str(item.get("type", "")))
            for item in field_errors
        )
        failure_digest = _digest_payload(
            {
                "subject_id": self.subject_id,
                "adapter": adapter_identity,
                "external_record_id": external_record_id,
                "external_revision": external_revision,
                "source_locator": locator,
                "error_type": error_type,
                "field_errors": normalized_errors,
            }
        )
        audit_id = _stable_id(
            "obs_ingest_failure",
            self.subject_id,
            adapter_identity,
            external_record_id,
            external_revision,
            locator,
            error_type,
            normalized_errors,
        )
        existing = self._get_payload_if_exists(audit_id)
        if existing is not None:
            existing_digest = (
                existing.get("metadata") or {}
            ).get("failure_digest")
            if existing_digest != failure_digest:
                raise ValueError(
                    "ingest failure identity conflict: same audit identity "
                    "arrived with different adapter/source semantics"
                )
            self._catch_up()
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
                "external_revision": external_revision,
                "error_type": error_type,
                "field_errors": [
                    {"location": location, "type": error_kind}
                    for location, error_kind in normalized_errors
                ],
            },
            raw_locator=locator,
            metadata={
                "dimension": AUDIT_DIMENSION,
                "adapter_id": spec.adapter_id,
                "source_dimension": spec.dimension,
                "source_class": spec.source_class.value,
                "source_schema_version": spec.schema_version,
                "failure_digest": failure_digest,
                "mechanical_ingest_failure": True,
            },
        )
        operation_id = _stable_id("op_reality_failure", audit_id)
        result = self.store.commit(
            [audit],
            OperationRequest(
                operation_id=operation_id,
                operation_name="ingest.reality.failure",
                arguments={
                    "adapter_id": spec.adapter_id,
                    "external_record_id": external_record_id,
                    "external_revision": external_revision,
                    "error_type": error_type,
                },
                expected_world_revision=self._expected_revision_for_retry(operation_id),
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
        spec = self._validated_spec(spec)
        record = self._validated_media_record(record)
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
                occurred_end_at=record.occurred_end_at,
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
        """Compress one immutable numeric batch identified by series_id.

        Exact retries may reuse the same series_id. If source samples, policy,
        unit, adapter semantics, or source locators change, callers must use a
        new series_id; reusing the old identity fails closed.
        """
        spec = self._validated_spec(spec)
        policy = self._validated_policy(policy)
        samples = tuple(self._validated_sample(sample) for sample in samples)
        if spec.source_class is not SourceClass.SENSOR:
            raise ValueError("numeric stream compression requires SENSOR source_class")
        if not isinstance(series_id, str) or not series_id.strip():
            raise ValueError("series_id must not be blank")
        series_id = series_id.strip()
        if unit is not None:
            if not isinstance(unit, str) or not unit.strip():
                raise ValueError("unit must not be blank")
            unit = unit.strip()
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
                gap = (at - prev_at).total_seconds()
                # A large observation gap means we did not observe the transition.
                # Preserve two segments, but do not fabricate a point-in-time
                # numeric_change across an unobserved interval.
                if (
                    gap <= policy.max_gap_seconds
                    and abs(sample.value - previous.value) >= policy.change_threshold
                ):
                    changes.append((previous, sample))
            else:
                gap = 0.0

            if not current:
                current = [sample]
                running_sum = float(sample.value)
            else:
                mean = running_sum / len(current)
                if (
                    gap <= policy.max_gap_seconds
                    and abs(sample.value - mean) <= policy.tolerance
                ):
                    current.append(sample)
                    running_sum += float(sample.value)
                else:
                    segments.append(current)
                    current = [sample]
                    running_sum = float(sample.value)
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
        adapter_identity = self._adapter_identity(spec)

        def sample_identity(item: NumericSample) -> dict[str, Any]:
            return {
                "external_record_id": item.external_record_id,
                "occurred_at": as_utc(
                    item.occurred_at,
                    "occurred_at",
                ).isoformat(),
                "value": float(item.value),
                "source_locator": item.source_locator,
            }

        for index, segment in enumerate(segments):
            start = as_utc(segment[0].occurred_at, "occurred_at")
            end = as_utc(segment[-1].occurred_at, "occurred_at")
            values = [float(item.value) for item in segment]
            record_ids = [item.external_record_id for item in segment]
            object_id = _stable_id(
                "obs_num_segment",
                self.subject_id,
                spec.adapter_id,
                series_id,
                tuple(record_ids),
            )
            segment_digest = _digest_payload(
                {
                    "kind": "numeric_segment",
                    "subject_id": self.subject_id,
                    "adapter": adapter_identity,
                    "series_id": series_id,
                    "unit": unit,
                    "policy": policy_payload,
                    "samples": [sample_identity(item) for item in segment],
                }
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
                        "source_class": spec.source_class.value,
                        "series_id": series_id,
                        "source_digest": segment_digest,
                        "mechanical_ingest": True,
                        "mechanical_compression": True,
                        "source_record_range": {
                            "first": record_ids[0],
                            "last": record_ids[-1],
                            "count": len(record_ids),
                        },
                        "source_record_ids_digest": _digest_payload(record_ids),
                        "source_locator_range": {
                            "first": segment[0].source_locator,
                            "last": segment[-1].source_locator,
                        },
                        "raw_sample_values_retained": False,
                    },
                )
            )

        for before, after in changes:
            at = as_utc(after.occurred_at, "occurred_at")
            object_id = _stable_id(
                "obs_num_change",
                self.subject_id,
                spec.adapter_id,
                series_id,
                before.external_record_id,
                after.external_record_id,
            )
            change_digest = _digest_payload(
                {
                    "kind": "numeric_change",
                    "subject_id": self.subject_id,
                    "adapter": adapter_identity,
                    "series_id": series_id,
                    "unit": unit,
                    "policy": policy_payload,
                    "before": sample_identity(before),
                    "after": sample_identity(after),
                }
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
                        "previous": float(before.value),
                        "current": float(after.value),
                        "delta": float(after.value - before.value),
                        "absolute_delta": float(abs(after.value - before.value)),
                    },
                    unit=unit,
                    data_quality={
                        "change_threshold": float(policy.change_threshold),
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
                        "source_class": spec.source_class.value,
                        "series_id": series_id,
                        "source_digest": change_digest,
                        "mechanical_ingest": True,
                        "mechanical_threshold_event": True,
                        "source_record_ids": [
                            before.external_record_id,
                            after.external_record_id,
                        ],
                        "source_locators": [
                            locator
                            for locator in (
                                before.source_locator,
                                after.source_locator,
                            )
                            if locator is not None
                        ],
                    },
                )
            )

        new_objects: list[Observation] = []
        reused = 0
        for observation in observations:
            existing = self._get_payload_if_exists(observation.object_id)
            if existing is None:
                new_objects.append(observation)
                continue
            existing_digest = (existing.get("metadata") or {}).get("source_digest")
            expected_digest = observation.metadata.get("source_digest")
            if existing_digest != expected_digest:
                raise ValueError(
                    "numeric series identity conflict: same subject/adapter/series "
                    "source identity arrived with different samples, policy, unit, "
                    "locator, or adapter semantics"
                )
            reused += 1

        world_revision = int(self.store.current_world_revision())
        if new_objects:
            batch_digest = _digest_payload(
                {
                    "subject_id": self.subject_id,
                    "adapter": adapter_identity,
                    "series_id": series_id,
                    "unit": unit,
                    "policy": policy_payload,
                    "samples": [sample_identity(item) for item in ordered],
                }
            )
            operation_id = _stable_id(
                "op_numeric_series",
                self.subject_id,
                spec.adapter_id,
                series_id,
            )
            result = self.store.commit(
                new_objects,
                OperationRequest(
                    operation_id=operation_id,
                    operation_name="ingest.reality.numeric_series",
                    arguments={
                        "subject_id": self.subject_id,
                        "adapter_id": spec.adapter_id,
                        "series_id": series_id,
                        "batch_digest": batch_digest,
                        "input_sample_count": len(ordered),
                        "segment_count": len(segment_ids),
                        "change_count": len(change_ids),
                    },
                    expected_world_revision=self._expected_revision_for_retry(
                        operation_id
                    ),
                    reason=(
                        "mechanically compress numeric source stream without "
                        "semantic interpretation"
                    ),
                    idempotency_key=f"numeric-series:{operation_id}",
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

