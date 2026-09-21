#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RELEASE_DIR = Path(__file__).resolve().parent
V2_ROOT = RELEASE_DIR.parent
def _bootstrap_repo_src() -> None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "src"
        if (candidate / "aios_core").is_dir():
            sys.path.insert(0, str(candidate))
            return


_bootstrap_repo_src()

from aios_core.contracts.enums import ErrorCode, SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent, TimePrecision, as_utc
from aios_core.storage.sqlite_store import SQLiteWorldStore, StoreError

FIXTURE_VERSION = "c14-resident-fixture-v2"
FIXTURE_SHA256 = "sha256:1fb973499664d0d71d94a7b94071e3d7210395ea6a54ec4dcbb1ba115d069253"
INGEST_ADAPTER_VERSION = "c14-mechanical-ingest-adapter-v1"
BINDING_VERSION = "c14-fixture-event-binding-v1"
SUBJECT_ID = "user_1"
MANIFEST_PATH = V2_ROOT / "fixture" / "fixture_manifest.json"
VISIBLE_KEYS = (
    "event_id",
    "sequence",
    "occurred_at",
    "dimension",
    "source_kind",
    "source_class",
    "modality",
    "resident_visible_payload",
)
ALLOWED_SOURCE_CLASSES = {"USER", "SENSOR", "PLATFORM"}


class IngestAdapterError(RuntimeError):
    pass


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _projection_sha256(event: dict[str, Any]) -> str:
    projection = {key: event[key] for key in VISIBLE_KEYS}
    return _sha256_text(_canonical_json(projection))


def _stable_id(prefix: str, *parts: Any) -> str:
    digest = hashlib.sha256(_canonical_json(list(parts)).encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{digest}"


def _load_manifest() -> dict[str, Any]:
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise IngestAdapterError("fixture manifest unavailable or invalid") from exc
    expected = {
        "fixture_version": FIXTURE_VERSION,
        "fixture_sha256": FIXTURE_SHA256,
        "subject_id": SUBJECT_ID,
        "ingest_adapter_version": INGEST_ADAPTER_VERSION,
        "fixture_binding_version": BINDING_VERSION,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise IngestAdapterError(f"manifest {key} mismatch")
    return manifest


def _parse_occurred(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise IngestAdapterError("invalid occurred_at") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise IngestAdapterError("occurred_at must be timezone-aware")
    return parsed


def _validate_projection(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise IngestAdapterError("released event must be a JSON object")
    if set(raw) != set(VISIBLE_KEYS):
        raise IngestAdapterError("released event projection keys mismatch")
    event = dict(raw)
    if not isinstance(event["event_id"], str) or not event["event_id"].strip():
        raise IngestAdapterError("event_id must be non-blank")
    if not isinstance(event["sequence"], int) or isinstance(event["sequence"], bool) or event["sequence"] < 1:
        raise IngestAdapterError("sequence must be a positive integer")
    _parse_occurred(str(event["occurred_at"]))
    if not isinstance(event["dimension"], str) or not event["dimension"].startswith("dim:"):
        raise IngestAdapterError("dimension must start with dim:")
    for key in ("source_kind", "modality", "resident_visible_payload"):
        if not isinstance(event[key], str) or not event[key].strip():
            raise IngestAdapterError(f"{key} must be non-blank text")
    if event["source_class"] not in ALLOWED_SOURCE_CLASSES:
        raise IngestAdapterError("unsupported source_class")
    return event


def _verify_existing(
    store: SQLiteWorldStore,
    *,
    object_id: str,
    event: dict[str, Any],
    subject_id: str,
    projection_sha256: str,
    payload_sha256: str,
) -> dict[str, Any] | None:
    try:
        payload = store.get_payload(object_id, revision=1)
        record = store.object_revision_record(object_id, revision=1)
    except StoreError as exc:
        if exc.code == ErrorCode.NOT_FOUND:
            return None
        raise
    metadata = payload.get("metadata") or {}
    expected_source = SourceClass[event["source_class"]].value
    checks = (
        payload.get("object_type") == "observation",
        payload.get("subject_id") == subject_id,
        payload.get("source_kind") == event["source_kind"],
        payload.get("modality") == event["modality"],
        payload.get("value") == event["resident_visible_payload"],
        metadata.get("fixture_version") == FIXTURE_VERSION,
        metadata.get("fixture_sha256") == FIXTURE_SHA256,
        metadata.get("fixture_event_id") == event["event_id"],
        metadata.get("fixture_sequence") == event["sequence"],
        metadata.get("fixture_payload_sha256") == payload_sha256,
        metadata.get("fixture_projection_sha256") == projection_sha256,
        metadata.get("dimension") == event["dimension"],
        record.get("subject_id") == subject_id,
        record.get("source_class") == expected_source,
        int(record.get("revision", 0)) == 1,
    )
    if not all(checks):
        raise IngestAdapterError("existing durable object conflicts with released event binding")
    return {
        "ingest_ref": f"{object_id}@1",
        "object_id": object_id,
        "revision": 1,
        "world_revision": int(record["world_revision"]),
        "fixture_payload_sha256": payload_sha256,
        "fixture_projection_sha256": projection_sha256,
        "reused_existing": True,
    }


def ingest_projection(
    world_db: str | Path,
    raw_event: dict[str, Any],
    *,
    subject_id: str = SUBJECT_ID,
) -> dict[str, Any]:
    _load_manifest()
    event = _validate_projection(raw_event)
    if not isinstance(subject_id, str) or not subject_id.strip():
        raise IngestAdapterError("subject_id must be non-blank")
    subject_id = subject_id.strip()

    world_path = Path(world_db)
    world_path.parent.mkdir(parents=True, exist_ok=True)
    store = SQLiteWorldStore(world_path)

    payload_sha256 = _sha256_text(event["resident_visible_payload"])
    projection_sha256 = _projection_sha256(event)
    object_id = _stable_id(
        "obs_c14_fixture",
        subject_id,
        FIXTURE_VERSION,
        event["event_id"],
    )

    existing = _verify_existing(
        store,
        object_id=object_id,
        event=event,
        subject_id=subject_id,
        projection_sha256=projection_sha256,
        payload_sha256=payload_sha256,
    )
    if existing is not None:
        return existing

    occurred_original = str(event["occurred_at"])
    occurred = as_utc(_parse_occurred(occurred_original), "occurred_at")
    source_class = SourceClass[event["source_class"]]

    observation = Observation(
        object_id=object_id,
        subject_id=subject_id,
        occurred=TemporalExtent.point(
            occurred,
            precision=TimePrecision.SECOND,
            timezone_name="UTC",
        ),
        learned_at=occurred,
        recorded_at=occurred,
        created_by=f"c14_fixture_ingest:{INGEST_ADAPTER_VERSION}",
        source_kind=event["source_kind"],
        modality=event["modality"],
        value=event["resident_visible_payload"],
        data_quality={"fixture_release": True},
        raw_locator=f"fixture://{FIXTURE_VERSION}/{event['event_id']}",
        metadata={
            "dimension": event["dimension"],
            "source_class": source_class.value,
            "fixture_version": FIXTURE_VERSION,
            "fixture_sha256": FIXTURE_SHA256,
            "fixture_binding_version": BINDING_VERSION,
            "fixture_event_id": event["event_id"],
            "fixture_sequence": event["sequence"],
            "fixture_payload_sha256": payload_sha256,
            "fixture_projection_sha256": projection_sha256,
            "external_record_id": event["event_id"],
            "external_revision": "1",
            "occurred_at_original": occurred_original,
            "mechanical_ingest": True,
        },
    )

    operation_id = _stable_id(
        "op_c14_fixture_ingest",
        subject_id,
        FIXTURE_VERSION,
        event["event_id"],
        projection_sha256,
    )
    result = store.commit(
        [observation],
        OperationRequest(
            operation_id=operation_id,
            operation_name="ingest.c14_resident_fixture_event",
            arguments={
                "fixture_version": FIXTURE_VERSION,
                "fixture_event_id": event["event_id"],
                "fixture_sequence": event["sequence"],
                "fixture_projection_sha256": projection_sha256,
                "subject_id": subject_id,
                "dimension": event["dimension"],
                "source_kind": event["source_kind"],
                "source_class": source_class.value,
            },
            expected_world_revision=store.current_world_revision(),
            reason="persist one released C14 fixture event without semantic interpretation",
            idempotency_key=f"c14-fixture-ingest:{operation_id}",
            source_class=source_class,
        ),
    )
    if (object_id, 1) not in result.object_refs:
        raise IngestAdapterError("WorldStore commit did not return expected exact observation ref")
    record = store.object_revision_record(object_id, revision=1)
    return {
        "ingest_ref": f"{object_id}@1",
        "object_id": object_id,
        "revision": 1,
        "world_revision": int(record["world_revision"]),
        "fixture_payload_sha256": payload_sha256,
        "fixture_projection_sha256": projection_sha256,
        "reused_existing": bool(result.idempotent_replay),
    }


def _read_event(path_arg: str) -> dict[str, Any]:
    try:
        if path_arg == "-":
            raw = sys.stdin.read()
        else:
            raw = Path(path_arg).read_text(encoding="utf-8")
        return json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise IngestAdapterError("released event JSON is unreadable") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Mechanically ingest exactly one already-released C14 fixture event."
    )
    parser.add_argument("--world-db", required=True)
    parser.add_argument(
        "--event-file",
        default="-",
        help="JSON file containing only the released event projection; '-' reads stdin.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        receipt = ingest_projection(args.world_db, _read_event(args.event_file))
        sys.stdout.write(_canonical_json(receipt) + "\n")
        return 0
    except (IngestAdapterError, StoreError, ValueError, TypeError) as exc:
        sys.stderr.write(f"mechanical-ingest-error: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
