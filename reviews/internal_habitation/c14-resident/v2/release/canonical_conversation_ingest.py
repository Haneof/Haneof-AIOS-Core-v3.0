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

from aios_core.ingest import ConversationIngestor, INTERACTION_DIMENSION
from aios_core.storage.sqlite_store import SQLiteWorldStore

FIXTURE_VERSION = "c14-resident-fixture-v2"
FIXTURE_SHA256 = "sha256:1fb973499664d0d71d94a7b94071e3d7210395ea6a54ec4dcbb1ba115d069253"
ADAPTER_VERSION = "c14-canonical-conversation-adapter-v1"
BINDING_VERSION = "c14-canonical-conversation-binding-v1"
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


class CanonicalConversationIngestError(RuntimeError):
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
    return _sha256_text(
        _canonical_json({key: event[key] for key in VISIBLE_KEYS})
    )


def _read_manifest() -> dict[str, Any]:
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise CanonicalConversationIngestError(
            "fixture manifest unavailable or invalid"
        ) from exc
    expected = {
        "fixture_version": FIXTURE_VERSION,
        "fixture_sha256": FIXTURE_SHA256,
        "canonical_conversation_adapter_version": ADAPTER_VERSION,
        "canonical_conversation_binding_version": BINDING_VERSION,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise CanonicalConversationIngestError(f"manifest {key} mismatch")
    subject_id = manifest.get("subject_id")
    if not isinstance(subject_id, str) or not subject_id.strip():
        raise CanonicalConversationIngestError("manifest subject_id missing")
    return manifest


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise CanonicalConversationIngestError("invalid occurred_at") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CanonicalConversationIngestError("occurred_at must be timezone-aware")
    return parsed


def _validate_projection(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise CanonicalConversationIngestError("released event must be a JSON object")
    if set(raw) != set(VISIBLE_KEYS):
        raise CanonicalConversationIngestError("released event projection keys mismatch")
    event = dict(raw)
    if not isinstance(event["event_id"], str) or not event["event_id"].strip():
        raise CanonicalConversationIngestError("event_id must be non-blank")
    if (
        not isinstance(event["sequence"], int)
        or isinstance(event["sequence"], bool)
        or event["sequence"] < 1
    ):
        raise CanonicalConversationIngestError("sequence must be a positive integer")
    _parse_time(str(event["occurred_at"]))
    expected = {
        "dimension": "dim:conversation",
        "source_kind": "conversation",
        "source_class": "USER",
        "modality": "text",
    }
    for key, value in expected.items():
        if event.get(key) != value:
            raise CanonicalConversationIngestError(
                f"event is not a canonical USER conversation release: {key}"
            )
    payload = event["resident_visible_payload"]
    if not isinstance(payload, str) or not payload.strip():
        raise CanonicalConversationIngestError(
            "resident_visible_payload must be non-blank text"
        )
    return event


def _verify_exact_canonical_user(
    store: SQLiteWorldStore,
    *,
    object_id: str,
    revision: int,
    subject_id: str,
    session_id: str,
    turn_index: int,
    user_text: str,
    occurred_at: str,
) -> dict[str, Any]:
    record = store.object_revision_record(object_id, revision=revision)
    payload = store.get_payload(object_id, revision=revision)
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        raise CanonicalConversationIngestError(
            "canonical user Observation metadata missing"
        )
    occurred = payload.get("occurred")
    if not isinstance(occurred, dict):
        raise CanonicalConversationIngestError(
            "canonical user Observation occurred time missing"
        )
    expected = (
        (record.get("object_type"), "observation", "record object_type"),
        (record.get("subject_id"), subject_id, "record subject_id"),
        (record.get("source_class"), "user", "durable source_class"),
        (record.get("revision_kind"), "content", "revision_kind"),
        (payload.get("object_type"), "observation", "payload object_type"),
        (payload.get("object_id"), object_id, "payload object_id"),
        (int(payload.get("revision", 0)), revision, "payload revision"),
        (payload.get("subject_id"), subject_id, "payload subject_id"),
        (payload.get("source_kind"), "user_ai_interaction", "source_kind"),
        (payload.get("modality"), "text", "modality"),
        (payload.get("value"), user_text, "value"),
        (payload.get("created_by"), "conversation_ingest:user", "created_by"),
        (metadata.get("dimension"), INTERACTION_DIMENSION, "dimension"),
        (metadata.get("role"), "user", "role"),
        (metadata.get("session_id"), session_id, "session_id"),
        (metadata.get("turn_index"), turn_index, "turn_index"),
    )
    for actual, wanted, label in expected:
        if actual != wanted:
            raise CanonicalConversationIngestError(
                f"canonical user Observation mismatch: {label}"
            )

    expected_time = _parse_time(occurred_at)
    for field in ("start", "end"):
        value = occurred.get(field)
        if not isinstance(value, str):
            raise CanonicalConversationIngestError(
                "canonical user Observation point time missing"
            )
        if (
            _parse_time(value).astimezone(timezone.utc)
            != expected_time.astimezone(timezone.utc)
        ):
            raise CanonicalConversationIngestError(
                "canonical user Observation timestamp mismatch"
            )

    return {
        "ingest_ref": f"{object_id}@{revision}",
        "object_id": object_id,
        "revision": revision,
        "world_revision": int(record["world_revision"]),
        "durable_source_class": str(record["source_class"]),
    }


def ingest_canonical_conversation(
    world_db: str | Path,
    raw_event: dict[str, Any],
    *,
    session_id: str,
    turn_index: int,
) -> dict[str, Any]:
    manifest = _read_manifest()
    event = _validate_projection(raw_event)
    if not isinstance(session_id, str) or not session_id.strip():
        raise CanonicalConversationIngestError("session_id must be non-blank")
    session_id = session_id.strip()
    if not isinstance(turn_index, int) or isinstance(turn_index, bool) or turn_index < 1:
        raise CanonicalConversationIngestError("turn_index must be >= 1")

    subject_id = str(manifest["subject_id"]).strip()
    world_path = Path(world_db)
    world_path.parent.mkdir(parents=True, exist_ok=True)
    store = SQLiteWorldStore(world_path)
    ingestor = ConversationIngestor(store, subject_id=subject_id)
    occurred_at = str(event["occurred_at"])
    commit = ingestor.commit_user_input(
        session_id=session_id,
        turn_index=turn_index,
        user_text=event["resident_visible_payload"],
        occurred_at=_parse_time(occurred_at),
        recorded_at=_parse_time(occurred_at),
    )
    exact = _verify_exact_canonical_user(
        store,
        object_id=commit.observation_id,
        revision=1,
        subject_id=subject_id,
        session_id=session_id,
        turn_index=turn_index,
        user_text=event["resident_visible_payload"],
        occurred_at=occurred_at,
    )
    return {
        **exact,
        "fixture_version": FIXTURE_VERSION,
        "fixture_sha256": FIXTURE_SHA256,
        "fixture_event_id": event["event_id"],
        "fixture_sequence": event["sequence"],
        "fixture_payload_sha256": _sha256_text(event["resident_visible_payload"]),
        "fixture_projection_sha256": _projection_sha256(event),
        "binding_mode": "canonical_user_turn",
        "binding_version": BINDING_VERSION,
        "session_id": session_id,
        "turn_index": turn_index,
        "idempotent_replay": bool(commit.idempotent_replay),
    }


def _read_event(path_arg: str) -> dict[str, Any]:
    try:
        raw = sys.stdin.read() if path_arg == "-" else Path(path_arg).read_text(
            encoding="utf-8"
        )
        return json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise CanonicalConversationIngestError(
            "released event JSON is unreadable"
        ) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Persist one already-released USER conversation through the canonical "
            "ConversationIngestor user-input path."
        )
    )
    parser.add_argument("--world-db", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--turn-index", type=int, required=True)
    parser.add_argument(
        "--event-file",
        default="-",
        help="JSON file containing only the released event projection; '-' reads stdin.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        receipt = ingest_canonical_conversation(
            args.world_db,
            _read_event(args.event_file),
            session_id=args.session_id,
            turn_index=args.turn_index,
        )
        sys.stdout.write(_canonical_json(receipt) + "\n")
        return 0
    except (
        CanonicalConversationIngestError,
        ValueError,
        TypeError,
        RuntimeError,
    ) as exc:
        sys.stderr.write(f"canonical-conversation-ingest-error: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
