from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Annotated, Iterable, Iterator, Sequence, TypeVar

from pydantic import BaseModel, Field, JsonValue, TypeAdapter, ValidationError

from aios_core.contracts.base import WorldObject
from aios_core.contracts.enums import ErrorCode, ObjectType
from aios_core.contracts.models import Dependency, EvidenceSet
from aios_core.contracts.operations import CommitResult, OperationRequest
from aios_core.contracts.refs import ObjectRef, SourceRef
from aios_core.contracts.time import as_utc, canonical_utc_iso, utc_now
from aios_core.dependency import validate_dependency_graph_acyclic
from aios_core.errors import AIOSProtocolError
from aios_core.storage.idempotency import (
    DurableJSONError,
    canonical_json_dumps,
    legacy_request_fingerprint,
    normalize_operation_for_persistence,
    normalize_world_object_for_persistence,
    request_fingerprint,
    stored_request_fingerprint,
)

T = TypeVar("T", bound=WorldObject)
_REQUEST_FINGERPRINT_KEY = "_request_fingerprint"
_IDEMPOTENCY_KEY_ADAPTER = TypeAdapter(Annotated[str, Field(min_length=1)])


def _normalize_idempotency_lookup_key(value: object) -> str:
    """Normalize only the routing key before touching SQLite.

    Full request normalization happens after lookup for fresh requests and inside
    request_fingerprint for retries. Keeping lookup normalization field-scoped lets
    an existing key classify a dirty retry as IDEMPOTENCY_CONFLICT while preventing
    unvalidated values from reaching the SQLite binder. Semantic checks that require
    the full OperationRequest (such as non-blank identity fields) remain there.
    """

    return _IDEMPOTENCY_KEY_ADAPTER.validate_python(value)


class StoreError(AIOSProtocolError):
    """Storage layer error, now inherits from AIOSProtocolError for unified handling.

    Keeps backward compatibility:
    - except StoreError still works
    - except AIOSProtocolError also catches StoreError
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        context: dict[str, JsonValue] | None = None,
    ):
        super().__init__(code, message, context=context)


_SQLITE_INT64_MIN = -(1 << 63)
_SQLITE_INT64_MAX = (1 << 63) - 1


def _normalize_query_integer(value: object, field_name: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < _SQLITE_INT64_MIN
        or value > _SQLITE_INT64_MAX
    ):
        raise StoreError(
            ErrorCode.INVALID_ARGUMENT,
            f"{field_name} is outside the supported SQLite integer range",
            context={
                "field": field_name,
                "value": repr(value),
                "reason": "query_integer_out_of_range",
            },
        )
    return value


def _normalize_query_cutoff(value: datetime, field_name: str = "knowledge_cutoff") -> str:
    # Preserve the already-frozen public contract for naive datetimes: callers
    # receive the original ValueError. Protocol mapping applies to aware values
    # that still fail canonical UTC conversion (for example datetime overflow).
    if isinstance(value, datetime) and (
        value.tzinfo is None or value.utcoffset() is None
    ):
        return canonical_utc_iso(value, field_name)
    try:
        return canonical_utc_iso(value, field_name)
    except (AttributeError, OverflowError, OSError, TypeError, ValueError) as exc:
        raise StoreError(
            ErrorCode.INVALID_ARGUMENT,
            f"{field_name} is not a supported timestamp",
            context={
                "field": field_name,
                "reason": "query_timestamp_invalid",
            },
        ) from exc


def _parse_world_revision_row(row: sqlite3.Row | None) -> int:
    if row is None:
        raise StoreError(
            ErrorCode.STORAGE_FAILURE,
            "world store is missing the world revision record",
            context={"reason": "missing_world_revision"},
        )
    try:
        value = int(row["value"])
    except (TypeError, ValueError, OverflowError) as exc:
        raise StoreError(
            ErrorCode.STORAGE_FAILURE,
            "world store contains an invalid world revision",
            context={"reason": "corrupt_world_revision"},
        ) from exc
    if value < 0 or value > _SQLITE_INT64_MAX:
        raise StoreError(
            ErrorCode.STORAGE_FAILURE,
            "world store contains an out-of-range world revision",
            context={"reason": "corrupt_world_revision"},
        )
    return value


def _decode_durable_object_json(
    raw: object,
    *,
    reason: str,
    object_id: str | None = None,
) -> dict:
    try:
        if not isinstance(raw, (str, bytes, bytearray)):
            raise TypeError("durable JSON payload must be text or bytes")
        value = json.loads(raw)
    except (json.JSONDecodeError, UnicodeError, TypeError, RecursionError) as exc:
        context: dict[str, JsonValue] = {"reason": reason}
        if object_id is not None:
            context["object_id"] = object_id
        raise StoreError(
            ErrorCode.STORAGE_FAILURE,
            "durable JSON payload is corrupt",
            context=context,
        ) from exc
    if not isinstance(value, dict):
        context = {"reason": reason}
        if object_id is not None:
            context["object_id"] = object_id
        raise StoreError(
            ErrorCode.STORAGE_FAILURE,
            "durable JSON payload has an invalid shape",
            context=context,
        )
    return value


class SQLiteWorldStore:
    """Append-only object revision store with global world revisions.

    This is a deliberately small reference implementation. It establishes the
    invariants that higher layers must not bypass:
      * object revisions are append-only;
      * every write transaction advances one global world revision;
      * optimistic concurrency uses expected_world_revision;
      * idempotency keys prevent duplicate writes;
      * references are validated before every commit;
      * historical reads can reconstruct what was visible at a world revision.
    """

    SQLITE_BUSY_TIMEOUT_MS = 5000
    CURRENT_SCHEMA_VERSION = 1

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._preflight_schema_compatibility()
        self._initialize()

    def _preflight_schema_compatibility(self) -> None:
        """Reject future World schemas before any writable SQLite open.

        Version 0 is the historical unversioned schema and remains eligible for the
        small idempotent migrations below. A version newer than this runtime must
        fail without changing the database, creating WAL state, or attempting a
        downgrade.
        """

        path = Path(self.db_path)
        if not path.exists():
            return
        conn: sqlite3.Connection | None = None
        try:
            conn = sqlite3.connect(
                path.resolve().as_uri() + "?mode=ro",
                uri=True,
                timeout=self.SQLITE_BUSY_TIMEOUT_MS / 1000.0,
            )
            row = conn.execute("PRAGMA user_version").fetchone()
            version = 0 if row is None else int(row[0])
        except (sqlite3.DatabaseError, OSError, TypeError, ValueError) as exc:
            raise StoreError(
                ErrorCode.STORAGE_FAILURE,
                "World schema compatibility preflight failed",
                context={"reason": "schema_preflight_failed"},
            ) from exc
        finally:
            if conn is not None:
                conn.close()
        if version > self.CURRENT_SCHEMA_VERSION:
            raise StoreError(
                ErrorCode.STORAGE_FAILURE,
                (
                    f"World schema version {version} is newer than supported "
                    f"version {self.CURRENT_SCHEMA_VERSION}"
                ),
                context={
                    "reason": "incompatible_future_schema",
                    "schema_version": version,
                    "supported_schema_version": self.CURRENT_SCHEMA_VERSION,
                },
            )

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn: sqlite3.Connection | None = None
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=self.SQLITE_BUSY_TIMEOUT_MS / 1000.0,
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(f"PRAGMA busy_timeout = {self.SQLITE_BUSY_TIMEOUT_MS}")
            conn.execute("PRAGMA journal_mode = WAL")
            yield conn
        except sqlite3.IntegrityError as exc:
            raise StoreError(
                ErrorCode.STORAGE_FAILURE,
                "SQLite integrity failure",
                context={"reason": "sqlite_integrity_error"},
            ) from exc
        except sqlite3.OperationalError as exc:
            sqlite_code = getattr(exc, "sqlite_errorcode", None)
            base_code = sqlite_code & 0xFF if isinstance(sqlite_code, int) else None
            if base_code in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED}:
                raise StoreError(
                    ErrorCode.VERSION_CONFLICT,
                    "world store is busy; retry from a fresh snapshot",
                    context={
                        "reason": "storage_busy",
                        "sqlite_errorcode": sqlite_code,
                    },
                ) from exc
            reason = "storage_unavailable" if conn is None else "sqlite_operational_error"
            raise StoreError(
                ErrorCode.STORAGE_FAILURE,
                "SQLite storage operation failed",
                context={
                    "reason": reason,
                    "sqlite_errorcode": sqlite_code,
                },
            ) from exc
        except sqlite3.DatabaseError as exc:
            raise StoreError(
                ErrorCode.STORAGE_FAILURE,
                "SQLite database failure",
                context={"reason": "sqlite_database_error"},
            ) from exc
        finally:
            if conn is not None:
                conn.close()

    def _initialize(self) -> None:
        with self._connection() as conn:
            # M0-023：迁移必须先于任何引用 source_class 的 DDL（旧库上建部分索引会炸）。
            self._ensure_source_class_schema(conn)
            self._ensure_revision_kind_schema(conn)
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS world_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                INSERT OR IGNORE INTO world_meta(key, value)
                VALUES ('world_revision', '0');

                CREATE TABLE IF NOT EXISTS world_commits (
                    world_revision INTEGER PRIMARY KEY,
                    committed_at TEXT NOT NULL,
                    operation_id TEXT NOT NULL UNIQUE,
                    session_id TEXT,
                    reason TEXT NOT NULL,
                    source_class TEXT NOT NULL
                        CHECK(source_class IN ('user','sensor','platform','ai_cognition','maintenance','safety'))
                );
                CREATE INDEX IF NOT EXISTS idx_commits_triggerable
                    ON world_commits(world_revision) WHERE source_class <> 'maintenance';

                CREATE TABLE IF NOT EXISTS object_revisions (
                    object_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    object_type TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    world_revision INTEGER NOT NULL,
                    learned_at TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    revision_kind TEXT NOT NULL DEFAULT 'content',
                    PRIMARY KEY(object_id, revision),
                    FOREIGN KEY(world_revision) REFERENCES world_commits(world_revision)
                );

                CREATE INDEX IF NOT EXISTS idx_objects_current_lookup
                    ON object_revisions(object_id, world_revision DESC);
                CREATE INDEX IF NOT EXISTS idx_objects_type_subject
                    ON object_revisions(object_type, subject_id, world_revision DESC);
                CREATE INDEX IF NOT EXISTS idx_objects_type_subject_learned
                    ON object_revisions(
                        object_type, subject_id, learned_at DESC, object_id, revision DESC
                    );
                CREATE INDEX IF NOT EXISTS idx_objects_learned
                    ON object_revisions(learned_at);

                CREATE TABLE IF NOT EXISTS operations (
                    operation_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    operation_name TEXT NOT NULL,
                    arguments_json TEXT NOT NULL,
                    expected_world_revision INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    result_world_revision INTEGER,
                    error_code TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS idempotency_records (
                    idempotency_key TEXT PRIMARY KEY,
                    operation_id TEXT NOT NULL,
                    world_revision INTEGER NOT NULL,
                    result_json TEXT NOT NULL
                );
                """
            )
            # Publish the compatibility marker only after all supported legacy
            # migrations and current DDL completed successfully. A failed upgrade
            # therefore never leaves the World falsely marked current.
            conn.execute(f"PRAGMA user_version = {self.CURRENT_SCHEMA_VERSION}")
            conn.commit()

    def schema_version(self) -> int:
        with self._connection() as conn:
            row = conn.execute("PRAGMA user_version").fetchone()
            return 0 if row is None else int(row[0])

    def quick_check(self) -> tuple[str, ...]:
        """Return SQLite quick-check rows without treating them as World truth."""

        with self._connection() as conn:
            return tuple(str(row[0]) for row in conn.execute("PRAGMA quick_check").fetchall())

    def _ensure_source_class_schema(self, conn: sqlite3.Connection) -> None:
        """Keep the frozen commit-authority taxonomy forward compatible.

        Earlier AIOS databases allowed USER/SENSOR/AI_COGNITION/MAINTENANCE/SAFETY.
        P12 constitutional closure adds PLATFORM so trusted platform authorization
        and real external Action outcomes are not mislabeled as AI cognition.

        SQLite CHECK constraints cannot be altered in place, so existing databases
        are rebuilt losslessly when their world_commits DDL does not yet admit the
        platform source class. Object/history rows are untouched and foreign keys are
        restored immediately after the table swap.
        """

        table_row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='world_commits'"
        ).fetchone()
        if table_row is None:
            return

        create_sql = str(table_row["sql"] or "")
        columns = {row[1] for row in conn.execute("PRAGMA table_info(world_commits)")}
        has_source_class = "source_class" in columns
        admits_platform = "'platform'" in create_sql

        if has_source_class and admits_platform:
            return

        fk_enabled_row = conn.execute("PRAGMA foreign_keys").fetchone()
        fk_enabled = bool(fk_enabled_row[0]) if fk_enabled_row is not None else True
        if fk_enabled:
            conn.execute("PRAGMA foreign_keys = OFF")

        try:
            if not has_source_class:
                conn.execute("ALTER TABLE world_commits ADD COLUMN source_class TEXT")
                conn.execute(
                    "UPDATE world_commits "
                    "SET source_class='ai_cognition' WHERE source_class IS NULL"
                )

            conn.execute("DROP INDEX IF EXISTS idx_commits_triggerable")
            conn.execute("DROP TABLE IF EXISTS world_commits_sourceclass_next")
            conn.execute(
                """
                CREATE TABLE world_commits_sourceclass_next (
                    world_revision INTEGER PRIMARY KEY,
                    committed_at TEXT NOT NULL,
                    operation_id TEXT NOT NULL UNIQUE,
                    session_id TEXT,
                    reason TEXT NOT NULL,
                    source_class TEXT NOT NULL
                        CHECK(source_class IN (
                            'user','sensor','platform','ai_cognition','maintenance','safety'
                        ))
                )
                """
            )
            conn.execute(
                """
                INSERT INTO world_commits_sourceclass_next(
                    world_revision, committed_at, operation_id, session_id, reason,
                    source_class
                )
                SELECT world_revision, committed_at, operation_id, session_id, reason,
                       source_class
                FROM world_commits
                """
            )
            migrated = int(
                conn.execute(
                    "SELECT COUNT(*) FROM world_commits_sourceclass_next"
                ).fetchone()[0]
            )
            original = int(
                conn.execute("SELECT COUNT(*) FROM world_commits").fetchone()[0]
            )
            if migrated != original:
                raise sqlite3.IntegrityError(
                    "world_commits source-class migration row-count mismatch"
                )

            conn.execute("DROP TABLE world_commits")
            conn.execute(
                "ALTER TABLE world_commits_sourceclass_next RENAME TO world_commits"
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_commits_triggerable
                    ON world_commits(world_revision)
                    WHERE source_class <> 'maintenance'
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS world_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO world_meta(key, value)
                VALUES ('schema_migration_sourceclass_platform', ?)
                """,
                (
                    json.dumps(
                        {
                            "migrated_at": canonical_utc_iso(
                                utc_now(), "migrated_at"
                            ),
                            "preserved_rows": migrated,
                            "added_source_class": "platform",
                            "legacy_missing_source_backfill": (
                                None if has_source_class else "ai_cognition"
                            ),
                            "policy": "lossless CHECK-constraint table rebuild",
                        },
                        sort_keys=True,
                    ),
                ),
            )
            if not has_source_class:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO world_meta(key, value)
                    VALUES ('schema_migration_m0_023', ?)
                    """,
                    (
                        json.dumps(
                            {
                                "migrated_at": canonical_utc_iso(
                                    utc_now(), "migrated_at"
                                ),
                                "backfilled_rows": migrated,
                                "backfilled_as": "ai_cognition",
                                "policy": "explicit update; no silent DEFAULT",
                            },
                            sort_keys=True,
                        ),
                    ),
                )
            conn.commit()
        finally:
            if fk_enabled:
                conn.execute("PRAGMA foreign_keys = ON")


    def _ensure_revision_kind_schema(self, conn: sqlite3.Connection) -> None:
        """M1-019 runtime layer: support tombstone revision kind and cold archive."""
        try:
            cols_obj = {row[1] for row in conn.execute("PRAGMA table_info(object_revisions)")}
            if cols_obj and "revision_kind" not in cols_obj:
                conn.execute(
                    "ALTER TABLE object_revisions ADD COLUMN revision_kind TEXT NOT NULL DEFAULT 'content'"
                )
        except sqlite3.OperationalError:
            pass  # Race condition with concurrent connection

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cold_archive (
                object_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                archived_at TEXT NOT NULL,
                authz_ref TEXT NOT NULL,
                reason TEXT,
                PRIMARY KEY(object_id, revision)
            )
            """
        )

    def commit_source_class(self, world_revision: int) -> str | None:
        """Return the frozen source class of one committed world revision."""

        with self._connection() as conn:
            row = conn.execute(
                "SELECT source_class FROM world_commits WHERE world_revision=?",
                (world_revision,),
            ).fetchone()
            return None if row is None else str(row["source_class"])

    def object_revision_record(self, object_id: str, *, revision: int) -> dict:
        """Return durable mechanical provenance for one exact object revision.

        C14 uses this read surface to derive routing lineage from the existing
        world ledger.  It intentionally exposes no semantic classification and
        creates no second provenance store.
        """

        revision = _normalize_query_integer(revision, "revision")
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT
                    o.object_id,
                    o.revision,
                    o.object_type,
                    o.subject_id,
                    o.world_revision,
                    o.revision_kind,
                    c.source_class,
                    (
                        SELECT MAX(o2.revision)
                        FROM object_revisions o2
                        WHERE o2.object_id=o.object_id
                    ) AS latest_revision
                FROM object_revisions o
                JOIN world_commits c ON c.world_revision=o.world_revision
                WHERE o.object_id=? AND o.revision=?
                """,
                (object_id, revision),
            ).fetchone()
        if row is None:
            raise StoreError(
                ErrorCode.NOT_FOUND,
                f"object revision not found: {object_id}@{revision}",
                context={
                    "object_id": object_id,
                    "revision": revision,
                    "reason": "exact_revision_not_found",
                },
            )
        record = dict(row)
        record["is_latest"] = int(record["latest_revision"]) == int(record["revision"])
        return record

    def triggerable_commits_after(
        self, world_revision: int, *, limit: int = 500
    ) -> list[dict]:
        """Read surface for the M2 trigger engine (R4-02 closure point).

        MAINTENANCE commits are structurally invisible here; review work must
        reach the AI through task channels, never through trigger evaluation.
        """

        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT world_revision, committed_at, operation_id, session_id, reason, source_class
                FROM world_commits
                WHERE world_revision > ? AND source_class <> 'maintenance'
                ORDER BY world_revision
                LIMIT ?
                """,
                (world_revision, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def revisions_after(
        self, world_revision: int, *, limit: int = 5000, complete_commits: bool = False
    ) -> list[dict]:
        """Replay surface for rebuildable projections (search index, hot cards).

        Delivers every object revision committed after ``world_revision`` in
        commit order. Projections must never scan the whole object table to
        stay fresh. With ``complete_commits=True``, ``limit`` is a soft row
        target: the boundary commit is returned in full, even when a single
        commit exceeds the target. The default retains the bounded row API.
        """

        if type(limit) is not int or limit < 1:
            raise ValueError("limit must be a positive integer")
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT world_revision, object_id, revision, object_type, subject_id, payload_json
                FROM object_revisions
                WHERE world_revision > ?
                ORDER BY world_revision, object_id, revision
                LIMIT ?
                """,
                (world_revision, limit),
            ).fetchall()
            if complete_commits and len(rows) == limit:
                # A World commit is immutable once visible. Complete the last
                # group rather than advertising a watermark across a partial cut.
                # limit is a soft batching target in this explicitly opted-in mode.
                last = rows[-1]
                rows.extend(conn.execute(
                    """
                    SELECT world_revision, object_id, revision, object_type, subject_id, payload_json
                    FROM object_revisions
                    WHERE world_revision = ? AND (object_id, revision) > (?, ?)
                    ORDER BY object_id, revision
                    """,
                    (last["world_revision"], last["object_id"], last["revision"]),
                ).fetchall())
        return [dict(row) for row in rows]

    def current_world_revision(self) -> int:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT value FROM world_meta WHERE key='world_revision'"
            ).fetchone()
            return _parse_world_revision_row(row)

    def _get_idempotent_result(
        self,
        conn: sqlite3.Connection,
        operation: OperationRequest,
        objects: list[WorldObject],
    ) -> CommitResult | None:
        try:
            lookup_key = _normalize_idempotency_lookup_key(operation.idempotency_key)
        except (ValidationError, ValueError, TypeError) as exc:
            raise StoreError(
                ErrorCode.INVALID_ARGUMENT,
                "idempotency key failed persistence validation",
                context={
                    "operation_id": str(operation.operation_id),
                    "reason": "idempotency_key_revalidation_failed",
                },
            ) from exc

        row = conn.execute(
            """
            SELECT operation_id, world_revision, result_json
            FROM idempotency_records
            WHERE idempotency_key=?
            """,
            (lookup_key,),
        ).fetchone()
        if not row:
            return None

        try:
            incoming_fingerprint = request_fingerprint(operation, objects)
        except (ValidationError, DurableJSONError, TypeError) as exc:
            raise StoreError(
                ErrorCode.IDEMPOTENCY_CONFLICT,
                "idempotency key retry is not a valid equivalent request",
                context={
                    "idempotency_key": lookup_key,
                    "operation_id": str(operation.operation_id),
                    "reason": "request_revalidation_failed",
                },
            ) from exc

        data = _decode_durable_object_json(
            row["result_json"],
            reason="corrupt_idempotency_result",
        )
        original_fingerprint = data.pop(_REQUEST_FINGERPRINT_KEY, None)
        if original_fingerprint is None:
            # Rows written before semantic fingerprints were persisted can only be
            # compared using their legacy durable JSON identity. This compatibility
            # path cannot recover typed-ref information that older rows never stored.
            try:
                incoming_fingerprint = legacy_request_fingerprint(operation, objects)
            except (ValidationError, DurableJSONError, TypeError) as exc:
                raise StoreError(
                    ErrorCode.IDEMPOTENCY_CONFLICT,
                    "idempotency key retry is not a valid equivalent request",
                    context={
                        "idempotency_key": lookup_key,
                        "operation_id": str(operation.operation_id),
                        "reason": "request_revalidation_failed",
                    },
                ) from exc
            try:
                original_fingerprint = stored_request_fingerprint(
                    conn,
                    operation_id=str(row["operation_id"]),
                    world_revision=int(row["world_revision"]),
                )
            except (
                DurableJSONError,
                json.JSONDecodeError,
                RuntimeError,
                TypeError,
                ValueError,
                OverflowError,
            ) as exc:
                raise StoreError(
                    ErrorCode.STORAGE_FAILURE,
                    "legacy idempotency records are internally inconsistent",
                    context={
                        "idempotency_key": lookup_key,
                        "operation_id": str(row["operation_id"]),
                        "reason": "corrupt_legacy_idempotency_state",
                    },
                ) from exc
        elif not isinstance(original_fingerprint, str):
            raise StoreError(
                ErrorCode.STORAGE_FAILURE,
                "idempotency record contains an invalid request fingerprint",
                context={
                    "idempotency_key": lookup_key,
                    "operation_id": str(row["operation_id"]),
                    "reason": "corrupt_idempotency_fingerprint",
                },
            )

        if incoming_fingerprint != original_fingerprint:
            raise StoreError(
                ErrorCode.IDEMPOTENCY_CONFLICT,
                "idempotency key was already used for a different request",
                context={
                    "idempotency_key": lookup_key,
                    "original_operation_id": str(row["operation_id"]),
                    "operation_id": str(operation.operation_id),
                    "reason": "request_fingerprint_mismatch",
                },
            )

        data["idempotent_replay"] = True
        try:
            return CommitResult.model_validate(data)
        except (ValidationError, TypeError, ValueError) as exc:
            raise StoreError(
                ErrorCode.STORAGE_FAILURE,
                "idempotency result payload is inconsistent with its contract",
                context={
                    "idempotency_key": lookup_key,
                    "operation_id": str(row["operation_id"]),
                    "reason": "corrupt_idempotency_result",
                },
            ) from exc

    def _latest_revision(self, conn: sqlite3.Connection, object_id: str) -> int | None:
        row = conn.execute(
            "SELECT MAX(revision) AS rev FROM object_revisions WHERE object_id=?",
            (object_id,),
        ).fetchone()
        return None if row["rev"] is None else int(row["rev"])

    def _latest_object_type(self, conn: sqlite3.Connection, object_id: str) -> str | None:
        row = conn.execute(
            """
            SELECT object_type
            FROM object_revisions
            WHERE object_id=?
            ORDER BY revision DESC
            LIMIT 1
            """,
            (object_id,),
        ).fetchone()
        return None if row is None else str(row["object_type"])

    def _reference_exists(
        self,
        conn: sqlite3.Connection,
        ref: ObjectRef | SourceRef,
        pending_pairs: set[tuple[str, int]],
        pending_objects: dict[tuple[str, int], WorldObject],
        *,
        knowledge_cutoff: datetime,
    ) -> bool:
        """
        Generic knowledge visibility: target learned_at <= referencing_object.learned_at
        - For pinned ref (revision=N): check exact revision visible within cutoff
        - For floating ref (revision=None): check at least one visible revision within cutoff
        - Pending objects are considered with UTC instant comparison
        """
        cutoff_canonical = canonical_utc_iso(knowledge_cutoff, "knowledge_cutoff")

        if ref.revision is not None:
            key = (ref.object_id, ref.revision)
            if key in pending_pairs:
                pending_target = pending_objects.get(key)
                if pending_target is None:
                    return False
                try:
                    if as_utc(pending_target.learned_at, "pending_learned_at") <= as_utc(
                        knowledge_cutoff, "knowledge_cutoff"
                    ):
                        return True
                    return False
                except Exception:
                    return False
            row = conn.execute(
                "SELECT 1 FROM object_revisions WHERE object_id=? AND revision=? AND learned_at<=? LIMIT 1",
                (ref.object_id, ref.revision, cutoff_canonical),
            ).fetchone()
            return row is not None

        for (oid, _rev), pending_obj in pending_objects.items():
            if oid == ref.object_id:
                try:
                    if as_utc(pending_obj.learned_at, "pending_learned_at") <= as_utc(
                        knowledge_cutoff, "knowledge_cutoff"
                    ):
                        return True
                except Exception:
                    continue
        row = conn.execute(
            "SELECT 1 FROM object_revisions WHERE object_id=? AND learned_at<=? LIMIT 1",
            (ref.object_id, cutoff_canonical),
        ).fetchone()
        return row is not None

    @staticmethod
    def _collect_refs(value: object) -> list[ObjectRef | SourceRef]:
        refs: list[ObjectRef | SourceRef] = []

        def walk(node: object) -> None:
            if isinstance(node, (ObjectRef, SourceRef)):
                refs.append(node)
                return
            if isinstance(node, BaseModel):
                for field_name in type(node).model_fields:
                    walk(getattr(node, field_name))
                return
            if isinstance(node, dict):
                for v in node.values():
                    walk(v)
                return
            if isinstance(node, (list, tuple, set)):
                for v in node:
                    walk(v)

        walk(value)
        return refs

    def _validate_dependency_graph(
        self,
        conn: sqlite3.Connection,
        objects: list[WorldObject],
    ) -> None:
        pending = [obj for obj in objects if isinstance(obj, Dependency)]
        if not pending:
            return

        rows = conn.execute(
            """
            SELECT o.object_id, o.payload_json
            FROM object_revisions o
            JOIN (
                SELECT object_id, MAX(revision) AS max_revision
                FROM object_revisions
                WHERE object_type=?
                GROUP BY object_id
            ) latest
            ON latest.object_id=o.object_id AND latest.max_revision=o.revision
            WHERE o.object_type=?
            """,
            (ObjectType.DEPENDENCY.value, ObjectType.DEPENDENCY.value),
        ).fetchall()

        current_by_id: dict[str, Dependency] = {}
        for row in rows:
            try:
                dependency = Dependency.model_validate(json.loads(row["payload_json"]))
            except (ValidationError, json.JSONDecodeError, TypeError, ValueError) as exc:
                raise StoreError(
                    ErrorCode.STORAGE_FAILURE,
                    "durable dependency payload is inconsistent with its object_type",
                    context={
                        "object_id": str(row["object_id"]),
                        "reason": "corrupt_dependency_payload",
                    },
                ) from exc
            current_by_id[dependency.object_id] = dependency
        for dependency in pending:
            current_by_id[dependency.object_id] = dependency

        try:
            validate_dependency_graph_acyclic(current_by_id.values())
        except ValueError as exc:
            raise StoreError(
                ErrorCode.DEPENDENCY_INVALID,
                str(exc),
                context={
                    "reason": "dependency_cycle",
                    "pending_dependency_ids": [dep.object_id for dep in pending],
                },
            ) from exc

    def commit(
        self,
        objects: Iterable[WorldObject],
        operation: OperationRequest,
    ) -> CommitResult:
        object_list = list(objects)
        if not object_list:
            raise StoreError(
                ErrorCode.INVALID_ARGUMENT,
                "commit requires at least one object",
                context={
                    "operation_id": operation.operation_id,
                    "reason": "empty_commit",
                },
            )

        with self._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                replay = self._get_idempotent_result(conn, operation, object_list)
                if replay is not None:
                    conn.rollback()
                    return replay

                try:
                    operation = normalize_operation_for_persistence(operation)
                except ValidationError as exc:
                    raise StoreError(
                        ErrorCode.INVALID_ARGUMENT,
                        "operation request failed persistence validation",
                        context={
                            "operation_id": str(operation.operation_id),
                            "reason": "operation_persistence_revalidation_failed",
                        },
                    ) from exc

                reused_operation = conn.execute(
                    "SELECT idempotency_key FROM operations WHERE operation_id=?",
                    (operation.operation_id,),
                ).fetchone()
                if reused_operation is not None:
                    raise StoreError(
                        ErrorCode.IDEMPOTENCY_CONFLICT,
                        "operation_id was already committed with a different idempotency key",
                        context={
                            "operation_id": operation.operation_id,
                            "idempotency_key": operation.idempotency_key,
                            "original_idempotency_key": str(reused_operation["idempotency_key"]),
                            "reason": "operation_id_reused",
                        },
                    )

                current_world_revision = _parse_world_revision_row(
                    conn.execute(
                        "SELECT value FROM world_meta WHERE key='world_revision'"
                    ).fetchone()
                )
                if operation.expected_world_revision != current_world_revision:
                    raise StoreError(
                        ErrorCode.VERSION_CONFLICT,
                        f"expected world revision {operation.expected_world_revision}, current is {current_world_revision}",
                        context={
                            "expected_world_revision": operation.expected_world_revision,
                            "current_world_revision": current_world_revision,
                            "operation_id": operation.operation_id,
                        },
                    )

                validated_objects: list[WorldObject] = []
                for obj in object_list:
                    try:
                        validated = normalize_world_object_for_persistence(obj)
                    except ValidationError as exc:
                        raise StoreError(
                            ErrorCode.INVALID_ARGUMENT,
                            "world object failed persistence validation",
                            context={
                                "object_id": obj.object_id,
                                "object_type": (
                                    obj.object_type.value
                                    if isinstance(obj.object_type, ObjectType)
                                    else str(obj.object_type)
                                ),
                                "revision": obj.revision,
                                "reason": "persistence_revalidation_failed",
                            },
                        ) from exc
                    validated_objects.append(validated)
                object_list = validated_objects

                try:
                    operation_arguments_json = canonical_json_dumps(operation.arguments)
                    object_payload_json = {
                        (obj.object_id, obj.revision): canonical_json_dumps(
                            obj.model_dump(mode="python", round_trip=True)
                        )
                        for obj in object_list
                    }
                    request_identity = request_fingerprint(operation, object_list)
                except (ValidationError, DurableJSONError, TypeError) as exc:
                    raise StoreError(
                        ErrorCode.INVALID_ARGUMENT,
                        "request contains data that cannot be represented safely as durable JSON",
                        context={
                            "operation_id": operation.operation_id,
                            "reason": "durable_json_validation_failed",
                        },
                    ) from exc

                pending_pairs = {(o.object_id, o.revision) for o in object_list}
                pending_objects = {(o.object_id, o.revision): o for o in object_list}
                if len(pending_pairs) != len(object_list):
                    raise StoreError(
                        ErrorCode.INVALID_ARGUMENT,
                        "duplicate object revision in one commit",
                        context={
                            "operation_id": operation.operation_id,
                            "reason": "duplicate_revision",
                        },
                    )

                for obj in object_list:
                    latest = self._latest_revision(conn, obj.object_id)
                    expected_revision = 1 if latest is None else latest + 1
                    if obj.revision != expected_revision:
                        raise StoreError(
                            ErrorCode.VERSION_CONFLICT,
                            f"{obj.object_id} must write revision {expected_revision}, got {obj.revision}",
                            context={
                                "object_id": obj.object_id,
                                "expected_revision": expected_revision,
                                "actual_revision": obj.revision,
                            },
                        )
                    if latest is not None:
                        existing_object_type = self._latest_object_type(conn, obj.object_id)
                        if existing_object_type is not None and existing_object_type != obj.object_type.value:
                            raise StoreError(
                                ErrorCode.VERSION_CONFLICT,
                                "object type cannot change across revisions",
                                context={
                                    "object_id": obj.object_id,
                                    "expected_object_type": existing_object_type,
                                    "actual_object_type": obj.object_type.value,
                                },
                            )

                for obj in object_list:
                    reference_cutoff = (
                        obj.knowledge_window.knowledge_cutoff
                        if isinstance(obj, EvidenceSet)
                        else obj.learned_at
                    )
                    for ref in self._collect_refs(obj):
                        if ref.object_id == obj.object_id and (
                            ref.revision is None or ref.revision == obj.revision
                        ):
                            raise StoreError(
                                ErrorCode.DEPENDENCY_INVALID,
                                f"object {obj.object_id} cannot cite its own current/floating revision as evidence/source",
                                context={
                                    "object_id": obj.object_id,
                                    "revision": obj.revision,
                                    "referenced_revision": ref.revision,
                                    "reason": "self_reference",
                                },
                            )
                        if not self._reference_exists(
                            conn,
                            ref,
                            pending_pairs,
                            pending_objects,
                            knowledge_cutoff=reference_cutoff,
                        ):
                            raise StoreError(
                                ErrorCode.NOT_FOUND,
                                f"reference does not exist: {ref.object_id}@{ref.revision or 'latest'}",
                                context={
                                    "referenced_object_id": ref.object_id,
                                    "referenced_revision": ref.revision,
                                    "reason": "reference_not_visible_or_missing",
                                },
                            )

                self._validate_dependency_graph(conn, object_list)

                next_world_revision = current_world_revision + 1
                now_dt = utc_now()
                now = canonical_utc_iso(now_dt, "now")
                conn.execute(
                    "INSERT INTO world_commits(world_revision, committed_at, operation_id, session_id, reason, source_class) VALUES(?,?,?,?,?,?)",
                    (
                        next_world_revision,
                        now,
                        operation.operation_id,
                        operation.session_id,
                        operation.reason,
                        operation.source_class.value,
                    ),
                )

                refs: list[tuple[str, int]] = []
                for obj in object_list:
                    payload = object_payload_json[(obj.object_id, obj.revision)]
                    conn.execute(
                        """
                        INSERT INTO object_revisions(
                            object_id, revision, object_type, subject_id, world_revision,
                            learned_at, recorded_at, payload_json
                        ) VALUES(?,?,?,?,?,?,?,?)
                        """,
                        (
                            obj.object_id,
                            obj.revision,
                            obj.object_type.value,
                            obj.subject_id,
                            next_world_revision,
                            canonical_utc_iso(obj.learned_at, "learned_at"),
                            canonical_utc_iso(obj.recorded_at, "recorded_at"),
                            payload,
                        ),
                    )
                    refs.append((obj.object_id, obj.revision))

                result = CommitResult(
                    operation_id=operation.operation_id,
                    world_revision=next_world_revision,
                    object_refs=refs,
                )
                result_payload = result.model_dump(mode="python")
                result_payload[_REQUEST_FINGERPRINT_KEY] = request_identity
                result_json = canonical_json_dumps(result_payload)

                conn.execute(
                    """
                    INSERT INTO operations(
                        operation_id, session_id, operation_name, arguments_json,
                        expected_world_revision, reason, idempotency_key, status,
                        result_world_revision, created_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        operation.operation_id,
                        operation.session_id,
                        operation.operation_name,
                        operation_arguments_json,
                        operation.expected_world_revision,
                        operation.reason,
                        operation.idempotency_key,
                        "committed",
                        next_world_revision,
                        now,
                    ),
                )
                conn.execute(
                    "INSERT INTO idempotency_records(idempotency_key, operation_id, world_revision, result_json) VALUES(?,?,?,?)",
                    (
                        operation.idempotency_key,
                        operation.operation_id,
                        next_world_revision,
                        result_json,
                    ),
                )
                conn.execute(
                    "UPDATE world_meta SET value=? WHERE key='world_revision'",
                    (str(next_world_revision),),
                )
                conn.commit()
                return result
            except Exception:
                conn.rollback()
                raise

    def get_payload(
        self,
        object_id: str,
        *,
        revision: int | None = None,
        as_of_world_revision: int | None = None,
        knowledge_cutoff: datetime | None = None,
    ) -> dict:
        clauses = ["object_id=?"]
        params: list[object] = [object_id]
        if revision is not None:
            revision = _normalize_query_integer(revision, "revision")
            clauses.append("revision=?")
            params.append(revision)
        if as_of_world_revision is not None:
            as_of_world_revision = _normalize_query_integer(
                as_of_world_revision, "as_of_world_revision"
            )
            clauses.append("world_revision<=?")
            params.append(as_of_world_revision)
        if knowledge_cutoff is not None:
            clauses.append("learned_at<=?")
            params.append(_normalize_query_cutoff(knowledge_cutoff))
        sql = (
            "SELECT payload_json FROM object_revisions WHERE "
            + " AND ".join(clauses)
            + " ORDER BY revision DESC LIMIT 1"
        )
        with self._connection() as conn:
            row = conn.execute(sql, tuple(params)).fetchone()
            if row is None:
                raise StoreError(
                    ErrorCode.NOT_FOUND,
                    f"object not found: {object_id}",
                    context={
                        "object_id": object_id,
                        "revision": revision,
                    },
                )
            return _decode_durable_object_json(
                row["payload_json"],
                reason="corrupt_object_payload",
                object_id=object_id,
            )

    def list_payloads(
        self,
        *,
        object_type: ObjectType | None = None,
        subject_id: str | None = None,
        as_of_world_revision: int | None = None,
        knowledge_cutoff: datetime | None = None,
    ) -> list[dict]:
        """Return the newest visible revision of each object under the supplied cutoff."""
        if as_of_world_revision is not None:
            as_of_world_revision = _normalize_query_integer(
                as_of_world_revision, "as_of_world_revision"
            )
        if as_of_world_revision is not None or knowledge_cutoff is not None:
            return self._list_payloads_historical(
                object_type=object_type,
                subject_id=subject_id,
                as_of_world_revision=as_of_world_revision,
                knowledge_cutoff=knowledge_cutoff,
            )

        clauses = ["1=1"]
        params: list[object] = []
        if object_type is not None:
            clauses.append("o.object_type=?")
            params.append(object_type.value)
        if subject_id is not None:
            clauses.append("o.subject_id=?")
            params.append(subject_id)
        where = " AND ".join(clauses)
        sql = f"""
            SELECT o.payload_json
            FROM object_revisions o
            JOIN (
                SELECT object_id, MAX(revision) AS max_revision
                FROM object_revisions
                GROUP BY object_id
            ) latest
            ON latest.object_id=o.object_id AND latest.max_revision=o.revision
            WHERE {where}
            ORDER BY o.recorded_at ASC
        """
        with self._connection() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [
            _decode_durable_object_json(
                row["payload_json"],
                reason="corrupt_object_payload",
            )
            for row in rows
        ]

    def iter_latest_payloads(
        self,
        *,
        object_type: ObjectType | None = None,
        subject_id: str | None = None,
        as_of_world_revision: int | None = None,
        knowledge_cutoff: datetime | None = None,
        payload_equals: dict[str, object] | None = None,
        metadata_equals: dict[str, object] | None = None,
        metadata_in: dict[str, Sequence[object]] | None = None,
        required_metadata_tags: Sequence[str] = (),
        order_by_metadata_key: str | None = None,
    ) -> Iterator[dict]:
        """Stream newest visible payloads without materializing the whole World.

        The latest visible revision is chosen before mutable payload/subject
        filtering, preserving the same revision and historical-cut semantics as
        list_payloads. Optional JSON predicates are mechanical pushdowns only;
        callers must still perform their typed semantic validation.
        """

        visible_clauses: list[str] = []
        params: list[object] = []
        if as_of_world_revision is not None:
            as_of_world_revision = _normalize_query_integer(
                as_of_world_revision, "as_of_world_revision"
            )
            visible_clauses.append("world_revision<=?")
            params.append(as_of_world_revision)
        if knowledge_cutoff is not None:
            visible_clauses.append("learned_at<=?")
            params.append(_normalize_query_cutoff(knowledge_cutoff))

        visible_where = (
            ""
            if not visible_clauses
            else " WHERE " + " AND ".join(visible_clauses)
        )
        latest_sql = (
            "SELECT object_id, MAX(revision) AS max_revision "
            "FROM object_revisions"
            + visible_where
            + " GROUP BY object_id"
        )

        clauses = ["1=1"]
        if object_type is not None:
            clauses.append("o.object_type=?")
            params.append(object_type.value)
        if subject_id is not None:
            clauses.append("o.subject_id=?")
            params.append(subject_id)

        for key, value in (payload_equals or {}).items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("payload_equals keys must be non-blank strings")
            clauses.append("json_extract(o.payload_json, ?)=?")
            params.extend((f"$.{key.strip()}", value))

        for key, value in (metadata_equals or {}).items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("metadata_equals keys must be non-blank strings")
            clauses.append("json_extract(o.payload_json, ?)=?")
            params.extend((f"$.metadata.{key.strip()}", value))

        for key, values in (metadata_in or {}).items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("metadata_in keys must be non-blank strings")
            normalized = tuple(values)
            if not normalized:
                return
            placeholders = ",".join("?" for _ in normalized)
            clauses.append(
                f"json_extract(o.payload_json, ?) IN ({placeholders})"
            )
            params.append(f"$.metadata.{key.strip()}")
            params.extend(normalized)

        for tag in required_metadata_tags:
            clean_tag = str(tag).strip()
            if not clean_tag:
                raise ValueError(
                    "required_metadata_tags must not contain blank values"
                )
            clauses.append(
                "EXISTS ("
                "SELECT 1 FROM json_each(o.payload_json, '$.metadata.tags') tag "
                "WHERE CAST(tag.value AS TEXT)=?"
                ")"
            )
            params.append(clean_tag)

        order_parts = ["o.learned_at DESC"]
        if order_by_metadata_key is not None:
            key = str(order_by_metadata_key).strip()
            if not key:
                raise ValueError("order_by_metadata_key must not be blank")
            order_parts.append("json_extract(o.payload_json, ?) ASC")
            params.append(f"$.metadata.{key}")
        order_parts.append("o.object_id ASC")

        sql = (
            "SELECT o.object_id, o.payload_json "
            "FROM object_revisions o JOIN ("
            + latest_sql
            + ") latest ON latest.object_id=o.object_id "
            "AND latest.max_revision=o.revision WHERE "
            + " AND ".join(clauses)
            + " ORDER BY "
            + ", ".join(order_parts)
        )

        with self._connection() as conn:
            cursor = conn.execute(sql, tuple(params))
            for row in cursor:
                object_id = str(row["object_id"])
                yield _decode_durable_object_json(
                    row["payload_json"],
                    reason="corrupt_object_payload",
                    object_id=object_id,
                )

    def get_payloads_for_ids(
        self,
        object_ids: Sequence[str],
        *,
        as_of_world_revision: int | None = None,
        knowledge_cutoff: datetime | None = None,
    ) -> dict[str, dict]:
        """Return the newest visible payload for each requested object id.

        This is the batch equivalent of repeated get_payload latest reads.
        Chunking stays below SQLite variable limits while eliminating per-candidate
        connection/query amplification.
        """

        ids = tuple(dict.fromkeys(str(item) for item in object_ids if str(item)))
        if not ids:
            return {}

        cutoff_world = (
            None
            if as_of_world_revision is None
            else _normalize_query_integer(
                as_of_world_revision, "as_of_world_revision"
            )
        )
        cutoff_knowledge = (
            None
            if knowledge_cutoff is None
            else _normalize_query_cutoff(knowledge_cutoff)
        )

        selected: dict[str, dict] = {}
        chunk_size = 400
        with self._connection() as conn:
            for start in range(0, len(ids), chunk_size):
                chunk = ids[start : start + chunk_size]
                clauses = [
                    "object_id IN (" + ",".join("?" for _ in chunk) + ")"
                ]
                chunk_params: list[object] = list(chunk)
                if cutoff_world is not None:
                    clauses.append("world_revision<=?")
                    chunk_params.append(cutoff_world)
                if cutoff_knowledge is not None:
                    clauses.append("learned_at<=?")
                    chunk_params.append(cutoff_knowledge)
                rows = conn.execute(
                    "SELECT object_id, revision, payload_json "
                    "FROM object_revisions WHERE "
                    + " AND ".join(clauses)
                    + " ORDER BY object_id ASC, revision DESC",
                    tuple(chunk_params),
                )
                seen: set[str] = set()
                for row in rows:
                    object_id = str(row["object_id"])
                    if object_id in seen:
                        continue
                    seen.add(object_id)
                    selected[object_id] = _decode_durable_object_json(
                        row["payload_json"],
                        reason="corrupt_object_payload",
                        object_id=object_id,
                    )
        return selected

    def list_ai_world_claim_payloads(
        self,
        *,
        domain_subject_pairs: Iterable[tuple[str, str]],
        scope_key: str | None = None,
        required_tags: Iterable[str] = (),
        limit: int = 100,
        as_of_world_revision: int | None = None,
        knowledge_cutoff: datetime | None = None,
    ) -> list[dict]:
        """Return only current visible AI-world Claim payloads needed by typed views.

        This is a read-plan optimization over the authoritative World table, not a
        materialized cognition store.  Latest-revision selection is resolved before
        mutable payload predicates so an older matching revision can never reappear.
        Historical cutoffs apply to both the selected row and the anti-newer check,
        preserving the FIX-001 knowledge-time contract.
        """

        bounded_limit = max(0, int(limit))
        if bounded_limit == 0:
            return []

        pairs = tuple(
            dict.fromkeys(
                (str(domain), str(subject))
                for domain, subject in domain_subject_pairs
                if str(domain) and str(subject)
            )
        )
        if not pairs:
            return []

        clauses = ["o.object_type=?"]
        params: list[object] = [ObjectType.CLAIM.value]
        newer_clauses = [
            "newer.object_id=o.object_id",
            "newer.revision>o.revision",
        ]
        newer_params: list[object] = []

        if as_of_world_revision is not None:
            as_of_world_revision = _normalize_query_integer(
                as_of_world_revision, "as_of_world_revision"
            )
            clauses.append("o.world_revision<=?")
            params.append(as_of_world_revision)
            newer_clauses.append("newer.world_revision<=?")
            newer_params.append(as_of_world_revision)

        if knowledge_cutoff is not None:
            cutoff = _normalize_query_cutoff(knowledge_cutoff)
            clauses.append("o.learned_at<=?")
            params.append(cutoff)
            newer_clauses.append("newer.learned_at<=?")
            newer_params.append(cutoff)

        clauses.append(
            "NOT EXISTS (SELECT 1 FROM object_revisions newer WHERE "
            + " AND ".join(newer_clauses)
            + ")"
        )
        params.extend(newer_params)

        pair_clauses: list[str] = []
        for domain, subject in pairs:
            pair_clauses.append(
                "(o.subject_id=? AND "
                "json_extract(o.payload_json, '$.metadata.ai_domain')=?)"
            )
            params.extend([subject, domain])
        clauses.append("(" + " OR ".join(pair_clauses) + ")")
        clauses.append(
            "json_extract(o.payload_json, '$.metadata.ai_world')=1"
        )
        clauses.append(
            "COALESCE(NULLIF(CAST(json_extract(o.payload_json, '$.status') AS TEXT), ''), "
            "'active')='active'"
        )

        if scope_key is not None:
            clauses.append(
                "json_extract(o.payload_json, '$.metadata.scope_key')=?"
            )
            params.append(scope_key)

        clean_tags = tuple(dict.fromkeys(str(tag) for tag in required_tags))
        for tag in clean_tags:
            clauses.append(
                "EXISTS ("
                "SELECT 1 FROM json_each("
                "json_extract(o.payload_json, '$.metadata.tags')"
                ") tag WHERE CAST(tag.value AS TEXT)=?"
                ")"
            )
            params.append(tag)

        params.append(bounded_limit)
        sql = (
            "SELECT o.payload_json "
            "FROM object_revisions o "
            "WHERE "
            + " AND ".join(clauses)
            + " ORDER BY o.learned_at DESC, "
            "json_extract(o.payload_json, '$.metadata.ai_domain') ASC, "
            "o.object_id ASC LIMIT ?"
        )

        with self._connection() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [
            _decode_durable_object_json(
                row["payload_json"],
                reason="corrupt_object_payload",
            )
            for row in rows
        ]

    def payloads_for_object_ids(
        self,
        object_ids: Iterable[str],
        *,
        knowledge_cutoff: datetime | None = None,
    ) -> dict[str, dict]:
        """Batch newest-visible payload lookup for retrieval verification.

        The returned rows come directly from the World truth store.  Chunking only
        avoids SQLite bind limits; it does not change revision or cutoff semantics.
        """

        ids = tuple(dict.fromkeys(str(item) for item in object_ids if str(item)))
        if not ids:
            return {}

        cutoff = (
            None
            if knowledge_cutoff is None
            else _normalize_query_cutoff(knowledge_cutoff)
        )
        result: dict[str, dict] = {}
        chunk_size = 800

        with self._connection() as conn:
            for offset in range(0, len(ids), chunk_size):
                chunk = ids[offset : offset + chunk_size]
                placeholders = ",".join("?" for _ in chunk)
                params: list[object] = list(chunk)
                cutoff_sql = ""
                if cutoff is not None:
                    cutoff_sql = " AND learned_at<=?"
                    params.append(cutoff)
                sql = f"""
                    WITH ranked AS (
                        SELECT object_id, revision, payload_json,
                               ROW_NUMBER() OVER (
                                   PARTITION BY object_id
                                   ORDER BY revision DESC
                               ) AS row_rank
                        FROM object_revisions
                        WHERE object_id IN ({placeholders})
                        {cutoff_sql}
                    )
                    SELECT object_id, payload_json
                    FROM ranked
                    WHERE row_rank=1
                """
                for row in conn.execute(sql, tuple(params)).fetchall():
                    object_id = str(row["object_id"])
                    result[object_id] = _decode_durable_object_json(
                        row["payload_json"],
                        reason="corrupt_object_payload",
                        object_id=object_id,
                    )
        return result

    def _list_payloads_historical(
        self,
        *,
        object_type: ObjectType | None,
        subject_id: str | None,
        as_of_world_revision: int | None,
        knowledge_cutoff: datetime | None,
    ) -> list[dict]:
        # First reconstruct the latest visible revision of each object. Only then
        # apply mutable-object filters such as subject_id; otherwise an older
        # matching revision could incorrectly reappear after the latest visible
        # revision changed subject.
        clauses = ["1=1"]
        params: list[object] = []
        if as_of_world_revision is not None:
            as_of_world_revision = _normalize_query_integer(
                as_of_world_revision, "as_of_world_revision"
            )
            clauses.append("world_revision<=?")
            params.append(as_of_world_revision)
        if knowledge_cutoff is not None:
            clauses.append("learned_at<=?")
            params.append(_normalize_query_cutoff(knowledge_cutoff))
        sql = (
            "SELECT object_id, revision, object_type, subject_id, recorded_at, payload_json "
            "FROM object_revisions WHERE "
            + " AND ".join(clauses)
            + " ORDER BY object_id, revision DESC"
        )
        with self._connection() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()

        seen: set[str] = set()
        selected: list[tuple[str, dict]] = []
        for row in rows:
            object_id = str(row["object_id"])
            if object_id in seen:
                continue
            seen.add(object_id)
            if object_type is not None and row["object_type"] != object_type.value:
                continue
            if subject_id is not None and row["subject_id"] != subject_id:
                continue
            selected.append(
                (
                    row["recorded_at"],
                    _decode_durable_object_json(
                        row["payload_json"],
                        reason="corrupt_object_payload",
                        object_id=object_id,
                    ),
                )
            )

        selected.sort(key=lambda item: item[0])
        return [payload for _, payload in selected]

    def operation_record(self, operation_id: str) -> dict:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT * FROM operations WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
            if row is None:
                raise StoreError(
                    ErrorCode.NOT_FOUND,
                    f"operation not found: {operation_id}",
                    context={
                        "operation_id": operation_id,
                    },
                )
            return dict(row)


    def prune(
        self,
        object_id: str,
        *,
        authz_ref: str,
        reason: str,
    ) -> None:
        """M1-019 prune submission: append tombstone revision and archive cold payload."""
        with self._connection() as conn:
            self._ensure_revision_kind_schema(conn)
            row = conn.execute(
                """
                SELECT revision, object_type, subject_id, learned_at, payload_json
                FROM object_revisions
                WHERE object_id = ?
                ORDER BY revision DESC LIMIT 1
                """,
                (object_id,),
            ).fetchone()
            if row is None:
                raise StoreError(
                    ErrorCode.NOT_FOUND,
                    f"object {object_id} not found to prune",
                    context={"object_id": object_id},
                )
            cur_rev = int(row["revision"])
            obj_type = str(row["object_type"])
            subj_id = str(row["subject_id"])
            learned_at = str(row["learned_at"])
            payload_json = str(row["payload_json"])

            now = canonical_utc_iso(utc_now(), "archived_at")

            # 1. Store in cold archive
            conn.execute(
                """
                INSERT OR REPLACE INTO cold_archive (object_id, revision, payload_json, archived_at, authz_ref, reason)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (object_id, cur_rev, payload_json, now, authz_ref, reason),
            )

            # 2. Advance global world revision with maintenance commit
            cur_world_rev = conn.execute(
                "SELECT value FROM world_meta WHERE key='world_revision'"
            ).fetchone()[0]
            new_world_rev = int(cur_world_rev) + 1
            op_id = f"op_prune_{object_id}_{new_world_rev}"

            conn.execute(
                """
                INSERT INTO world_commits (world_revision, committed_at, operation_id, session_id, reason, source_class)
                VALUES (?, ?, ?, NULL, ?, 'maintenance')
                """,
                (new_world_rev, now, op_id, reason),
            )
            conn.execute(
                "UPDATE world_meta SET value=? WHERE key='world_revision'",
                (str(new_world_rev),),
            )

            # 3. Append tombstone revision to object_revisions
            new_obj_rev = cur_rev + 1
            tombstone_payload = json.dumps(
                {
                    "pruned": True,
                    "reason": reason,
                    "authz_ref": authz_ref,
                    "previous_revision": cur_rev,
                    "object_id": object_id,
                }
            )
            conn.execute(
                """
                INSERT INTO object_revisions (
                    object_id, revision, object_type, subject_id, world_revision,
                    learned_at, recorded_at, payload_json, revision_kind
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'tombstone')
                """,
                (
                    object_id,
                    new_obj_rev,
                    obj_type,
                    subj_id,
                    new_world_rev,
                    learned_at,
                    now,
                    tombstone_payload,
                ),
            )
            conn.commit()

    def is_latest_pruned(self, object_id: str) -> bool:
        """Return True if the newest revision of object_id is a tombstone."""
        with self._connection() as conn:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(object_revisions)")}
            if "revision_kind" not in cols:
                return False
            row = conn.execute(
                "SELECT revision_kind FROM object_revisions WHERE object_id=? ORDER BY revision DESC LIMIT 1",
                (object_id,),
            ).fetchone()
            if row is None:
                return False
            return str(row["revision_kind"]) == "tombstone"
