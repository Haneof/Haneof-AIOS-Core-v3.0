"""Non-world C13 metering ledger.

R4-08 requires economic metering to live beside the operations ledger rather than
as WorldObjects. Meter writes therefore do not advance world_revision, do not enter
the World index, and cannot create Wake feedback loops.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Literal, Sequence
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aios_core.contracts.time import as_utc, canonical_utc_iso
from aios_core.storage.sqlite_store import SQLiteWorldStore

from .cognitive_runtime import ModelCallProvenance, ModelUsage


MeterExecutionClass = Literal[
    "user_interaction",
    "background",
    "periodic_review",
    "safety",
    "other",
]


class MeteringRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    record_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    world_revision: int = Field(ge=0)
    recorded_at: datetime
    execution_class: MeterExecutionClass
    wake_id: str | None = None
    session_id: str | None = None
    wake_reason: str = Field(min_length=1)
    model_round_index: int = Field(ge=0)
    provider: str | None = None
    model: str | None = None
    provider_request_id: str | None = None
    usage_complete: bool
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_record(self) -> "MeteringRecord":
        as_utc(self.recorded_at, "recorded_at")
        for field_name in (
            "wake_id",
            "session_id",
            "provider",
            "model",
            "provider_request_id",
        ):
            value = getattr(self, field_name)
            if value is not None and not value.strip():
                raise ValueError(f"{field_name} must be non-blank when provided")
        if self.usage_complete and self.total_tokens is None:
            raise ValueError("complete metering record requires total_tokens")
        if not self.usage_complete and any(
            value is not None
            for value in (
                self.input_tokens,
                self.output_tokens,
                self.total_tokens,
            )
        ):
            raise ValueError("incomplete metering record must not invent token values")
        return self


class ModelMeteringLedger:
    """Append-only model-call ledger sharing the AIOS SQLite database."""

    def __init__(self, store: SQLiteWorldStore) -> None:
        self.store = store
        self._initialize()

    def _initialize(self) -> None:
        # The store connection already applies WAL/busy handling. Metering is a
        # non-world table in the same durable database; creating or writing it must
        # never mutate world_meta.world_revision.
        with self.store._connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS metering_records (
                    record_id TEXT PRIMARY KEY,
                    subject_id TEXT NOT NULL,
                    world_revision INTEGER NOT NULL,
                    recorded_at TEXT NOT NULL,
                    execution_class TEXT NOT NULL
                        CHECK(execution_class IN (
                            'user_interaction',
                            'background',
                            'periodic_review',
                            'safety',
                            'other'
                        )),
                    wake_id TEXT,
                    session_id TEXT,
                    wake_reason TEXT NOT NULL,
                    model_round_index INTEGER NOT NULL
                        CHECK(model_round_index >= 0),
                    provider TEXT,
                    model TEXT,
                    provider_request_id TEXT,
                    usage_complete INTEGER NOT NULL
                        CHECK(usage_complete IN (0, 1)),
                    input_tokens INTEGER CHECK(input_tokens IS NULL OR input_tokens >= 0),
                    output_tokens INTEGER CHECK(output_tokens IS NULL OR output_tokens >= 0),
                    total_tokens INTEGER CHECK(total_tokens IS NULL OR total_tokens >= 0)
                );

                CREATE INDEX IF NOT EXISTS idx_meter_subject_time
                    ON metering_records(subject_id, recorded_at);
                CREATE INDEX IF NOT EXISTS idx_meter_wake
                    ON metering_records(wake_id, recorded_at);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_meter_provider_request
                    ON metering_records(provider, provider_request_id)
                    WHERE provider IS NOT NULL AND provider_request_id IS NOT NULL;
                """
            )
            conn.commit()

    @staticmethod
    def _record_id(
        *,
        provider: str | None,
        provider_request_id: str | None,
    ) -> str:
        if provider and provider_request_id:
            raw = f"{provider}\0{provider_request_id}".encode("utf-8")
            return f"meter_{hashlib.sha256(raw).hexdigest()[:32]}"
        return f"meter_{uuid4().hex}"

    def record_model_call(
        self,
        *,
        subject_id: str,
        world_revision: int,
        recorded_at: datetime,
        execution_class: MeterExecutionClass,
        wake_reason: str,
        model_round_index: int,
        usage: ModelUsage | None,
        provenance: ModelCallProvenance | None = None,
        wake_id: str | None = None,
        session_id: str | None = None,
    ) -> MeteringRecord:
        provider = None if provenance is None else provenance.provider
        model = None if provenance is None else provenance.model
        provider_request_id = None if provenance is None else provenance.request_id
        if usage is not None:
            for field_name, usage_value in (
                ("provider", usage.provider),
                ("model", usage.model),
                ("request_id", usage.request_id),
            ):
                current = {
                    "provider": provider,
                    "model": model,
                    "request_id": provider_request_id,
                }[field_name]
                if current is not None and usage_value is not None and current != usage_value:
                    raise ValueError(
                        f"usage {field_name} conflicts with model-call provenance"
                    )
            provider = usage.provider or provider
            model = usage.model or model
            provider_request_id = usage.request_id or provider_request_id
        record = MeteringRecord(
            record_id=self._record_id(
                provider=provider,
                provider_request_id=provider_request_id,
            ),
            subject_id=subject_id,
            world_revision=int(world_revision),
            recorded_at=as_utc(recorded_at, "recorded_at"),
            execution_class=execution_class,
            wake_id=wake_id,
            session_id=session_id,
            wake_reason=wake_reason,
            model_round_index=int(model_round_index),
            provider=provider,
            model=model,
            provider_request_id=provider_request_id,
            usage_complete=usage is not None,
            input_tokens=None if usage is None else usage.input_tokens,
            output_tokens=None if usage is None else usage.output_tokens,
            total_tokens=None if usage is None else usage.total_tokens,
        )

        with self.store._connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO metering_records(
                    record_id,
                    subject_id,
                    world_revision,
                    recorded_at,
                    execution_class,
                    wake_id,
                    session_id,
                    wake_reason,
                    model_round_index,
                    provider,
                    model,
                    provider_request_id,
                    usage_complete,
                    input_tokens,
                    output_tokens,
                    total_tokens
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.record_id,
                    record.subject_id,
                    record.world_revision,
                    canonical_utc_iso(record.recorded_at, "recorded_at"),
                    record.execution_class,
                    record.wake_id,
                    record.session_id,
                    record.wake_reason,
                    record.model_round_index,
                    record.provider,
                    record.model,
                    record.provider_request_id,
                    int(record.usage_complete),
                    record.input_tokens,
                    record.output_tokens,
                    record.total_tokens,
                ),
            )
            conn.commit()
            row = conn.execute(
                """
                SELECT *
                FROM metering_records
                WHERE record_id=?
                """,
                (record.record_id,),
            ).fetchone()
        if row is None:
            raise RuntimeError("metering record insert was not durable")
        persisted = self._from_row(row)
        immutable_replay_fields = (
            "subject_id",
            "execution_class",
            "wake_id",
            "session_id",
            "wake_reason",
            "model_round_index",
            "provider",
            "model",
            "provider_request_id",
            "usage_complete",
            "input_tokens",
            "output_tokens",
            "total_tokens",
        )
        conflicts = [
            field_name
            for field_name in immutable_replay_fields
            if getattr(persisted, field_name) != getattr(record, field_name)
        ]
        if conflicts:
            raise RuntimeError(
                "metering replay conflicts with durable provider response identity: "
                + ", ".join(conflicts)
            )
        return persisted

    def list_model_calls(
        self,
        *,
        subject_id: str,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        execution_classes: Sequence[MeterExecutionClass] = (),
        wake_id: str | None = None,
    ) -> tuple[MeteringRecord, ...]:
        clauses = ["subject_id=?"]
        params: list[object] = [subject_id]
        if start_at is not None:
            clauses.append("recorded_at>=?")
            params.append(canonical_utc_iso(start_at, "start_at"))
        if end_at is not None:
            clauses.append("recorded_at<?")
            params.append(canonical_utc_iso(end_at, "end_at"))
        if execution_classes:
            placeholders = ",".join("?" for _ in execution_classes)
            clauses.append(f"execution_class IN ({placeholders})")
            params.extend(execution_classes)
        if wake_id is not None:
            clauses.append("wake_id=?")
            params.append(wake_id)

        with self.store._connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM metering_records
                WHERE """
                + " AND ".join(clauses)
                + " ORDER BY recorded_at ASC, record_id ASC",
                tuple(params),
            ).fetchall()
        return tuple(self._from_row(row) for row in rows)

    @staticmethod
    def _from_row(row: object) -> MeteringRecord:
        # sqlite3.Row supports mapping-style access without exposing mutable state.
        return MeteringRecord(
            record_id=row["record_id"],
            subject_id=row["subject_id"],
            world_revision=int(row["world_revision"]),
            recorded_at=datetime.fromisoformat(str(row["recorded_at"]).replace("Z", "+00:00")),
            execution_class=row["execution_class"],
            wake_id=row["wake_id"],
            session_id=row["session_id"],
            wake_reason=row["wake_reason"],
            model_round_index=int(row["model_round_index"]),
            provider=row["provider"],
            model=row["model"],
            provider_request_id=row["provider_request_id"],
            usage_complete=bool(row["usage_complete"]),
            input_tokens=row["input_tokens"],
            output_tokens=row["output_tokens"],
            total_tokens=row["total_tokens"],
        )
