"""External reality facts -> unified AIOS world.

This module is intentionally mechanical. It accepts source-bound facts whose
meaning/dimension was already decided by the caller/adapter. It does not infer
importance, identity, relationship, intent, causality, or any other cognition.

The durable source of truth remains SQLiteWorldStore; source adapters must not
create a parallel task/cache/truth database.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from aios_core.contracts.enums import SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent, as_utc
from aios_core.storage.sqlite_store import SQLiteWorldStore


_ALLOWED_EXTERNAL_SOURCE_CLASSES = frozenset({SourceClass.USER, SourceClass.SENSOR})
_RESERVED_METADATA_KEYS = frozenset(
    {
        "dimension",
        "source_system",
        "source_record_id",
        "source_kind",
        "ingest_mode",
        "source_schema_version",
    }
)


@dataclass(frozen=True, slots=True)
class ExternalFactCommit:
    world_revision: int
    observation_id: str
    idempotent_replay: bool


def _require_nonblank(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    return value.strip()


def _stable_suffix(*parts: object) -> str:
    payload = "|".join(str(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


class ExternalFactIngestor:
    """Commit already-normalized external facts into the unified world.

    A separate instance should be used for each trust/source class boundary:
    USER for user-owned digital records (calendar, notes, app exports, etc.) and
    SENSOR for device-originated measurements/perception facts.

    source_record_id is the stable identity of the *normalized durable fact* in
    its source system. Exact retries replay idempotently; reusing that identity
    with mutated content is rejected by the store's idempotency contract.
    """

    def __init__(
        self,
        store: SQLiteWorldStore,
        *,
        subject_id: str = "user_1",
        source_class: SourceClass = SourceClass.USER,
        created_by: str = "external_fact_ingest",
    ) -> None:
        if source_class not in _ALLOWED_EXTERNAL_SOURCE_CLASSES:
            raise ValueError(
                "external fact ingest source_class must be USER or SENSOR; "
                "cognition/maintenance/safety writes require their own boundary"
            )
        self.store = store
        self.subject_id = _require_nonblank(subject_id, "subject_id")
        self.source_class = source_class
        self.created_by = _require_nonblank(created_by, "created_by")

    def commit_fact(
        self,
        *,
        source_system: str,
        source_record_id: str,
        dimension: str,
        source_kind: str,
        modality: str,
        value: Any,
        occurred_at: datetime,
        learned_at: datetime,
        recorded_at: datetime | None = None,
        raw_locator: str | None = None,
        unit: str | None = None,
        data_quality: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
        ingest_mode: str = "stream",
        source_schema_version: str | None = None,
    ) -> ExternalFactCommit:
        source_system = _require_nonblank(source_system, "source_system")
        source_record_id = _require_nonblank(source_record_id, "source_record_id")
        dimension = _require_nonblank(dimension, "dimension")
        source_kind = _require_nonblank(source_kind, "source_kind")
        modality = _require_nonblank(modality, "modality")

        if ingest_mode not in {"historical", "stream"}:
            raise ValueError("ingest_mode must be 'historical' or 'stream'")

        learned = as_utc(learned_at, "learned_at")
        recorded = as_utc(recorded_at or learned_at, "recorded_at")
        occurred = as_utc(occurred_at, "occurred_at")
        if recorded < learned:
            raise ValueError("recorded_at must be >= learned_at")

        extra_metadata = dict(metadata or {})
        reserved = sorted(_RESERVED_METADATA_KEYS.intersection(extra_metadata))
        if reserved:
            raise ValueError(
                "metadata cannot override reserved provenance keys: "
                + ", ".join(reserved)
            )

        schema_version = None
        if source_schema_version is not None:
            schema_version = _require_nonblank(
                source_schema_version, "source_schema_version"
            )

        identity_suffix = _stable_suffix(
            self.subject_id,
            source_system,
            source_kind,
            source_record_id,
        )
        observation_id = f"obs_ext_{identity_suffix}"

        provenance = {
            "dimension": dimension,
            "source_system": source_system,
            "source_record_id": source_record_id,
            "source_kind": source_kind,
            "ingest_mode": ingest_mode,
        }
        if schema_version is not None:
            provenance["source_schema_version"] = schema_version
        provenance.update(extra_metadata)

        observation = Observation(
            object_id=observation_id,
            subject_id=self.subject_id,
            occurred=TemporalExtent.point(occurred),
            learned_at=learned,
            recorded_at=recorded,
            created_by=self.created_by,
            source_kind=source_kind,
            modality=modality,
            value=value,
            unit=unit,
            data_quality=dict(data_quality or {}),
            raw_locator=raw_locator,
            metadata=provenance,
        )

        operation_id = f"op_ext_{identity_suffix}"
        expected_world_revision = self.store.current_world_revision()
        try:
            previous = self.store.operation_record(operation_id)
        except Exception:
            previous = None
        if previous is not None:
            expected_world_revision = int(previous["expected_world_revision"])

        operation = OperationRequest(
            operation_id=operation_id,
            operation_name="external_fact.commit",
            arguments={
                "dimension": dimension,
                "source_system": source_system,
                "source_kind": source_kind,
                "ingest_mode": ingest_mode,
            },
            expected_world_revision=expected_world_revision,
            reason="persist source-bound external fact into unified AIOS world",
            idempotency_key=(
                f"external:{self.subject_id}:{source_system}:"
                f"{source_kind}:{source_record_id}"
            ),
            source_class=self.source_class,
        )
        result = self.store.commit([observation], operation)
        return ExternalFactCommit(
            world_revision=result.world_revision,
            observation_id=observation_id,
            idempotent_replay=result.idempotent_replay,
        )
