"""Run-state manifest and re-attach verification for the persistence corrective.

Why this exists
---------------
The frozen WIP only proved *process* restart.  The original state-loss incident
was bigger: the platform execution environment disappeared and the whole ``/tmp``
run root went with it.  A credible re-attach proof therefore has to reopen every
artifact of a run - not just the journal - from a pinned manifest captured
*before* detachment, and prove:

* every artifact is still openable;
* every artifact's SHA-256 matches the pre-detach manifest;
* run/session/cursor/event/binding identities are unchanged.

It must never reconstruct missing state: if one byte is missing the manifest
check fails and the run is reported as not re-attached.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from .backend import BackendError, RunBackend, digest, require

MANIFEST_NAME = "run-state-manifest.json"
MANIFEST_VERSION = "c15-run-state-manifest-v1"

#: Logical slots that must survive a re-attach. ``required=False`` slots are
#: recorded when present but their absence is not a re-attach failure (for
#: example before the first provider request has been written).
SLOTS: tuple[tuple[str, str], ...] = (
    ("world", "runtime/world.sqlite"),
    ("search_index", "runtime/index.sqlite"),
    ("release_state", "runtime/release_state.json"),
    ("current_event", "current-event.json"),
    ("binding", "binding/current-event-binding.json"),
    ("projection", "evidence/projection.json"),
    ("failure_evidence", "evidence/failures.jsonl"),
    ("mailbox", "mailbox/archive.jsonl"),
    ("provider_request", "mailbox/outbox/current.request"),
    ("provider_reply", "mailbox/inbox/current.reply"),
    ("persistence_journal", "journal.sqlite"),
)

REQUIRED_SLOTS: frozenset[str] = frozenset(
    {
        "world",
        "search_index",
        "release_state",
        "current_event",
        "binding",
        "projection",
        "failure_evidence",
        "mailbox",
        "persistence_journal",
    }
)


def _slot_path(backend: RunBackend, relative: str) -> Path:
    if relative.startswith("journal.sqlite"):
        return backend.root / relative
    if relative.split("/")[0] == "mailbox":
        return backend.mailbox_dir / relative[len("mailbox/") :]
    return backend.state_dir / relative


def slot_bytes(backend: RunBackend, relative: str) -> bytes | None:
    path = _slot_path(backend, relative)
    if not path.is_file():
        return None
    return path.read_bytes()


def capture_manifest(
    backend: RunBackend,
    *,
    cursor: int | None,
    event_id: str | None,
    phase: str,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Hash every existing slot and pin the run identity. Call before detach."""
    # Ensure SQLite databases have WAL pages checkpointed so disk bytes are coherent.
    for relative in ("runtime/world.sqlite", "runtime/index.sqlite", "journal.sqlite"):
        p = _slot_path(backend, relative)
        if p.is_file():
            try:
                conn = sqlite3.connect(str(p), timeout=10)
                try:
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                finally:
                    conn.close()
            except sqlite3.Error:
                pass

    artifacts: dict[str, str] = {}
    for name, relative in SLOTS:
        raw = slot_bytes(backend, relative)
        if raw is None:
            continue
        artifacts[relative] = digest(raw)
    manifest: dict[str, Any] = {
        "manifest_version": MANIFEST_VERSION,
        "captured_at_epoch": time.time(),
        "run_id": backend.owner["run_id"],
        "session_id": backend.owner["session_id"],
        "subject_id": backend.owner["subject_id"],
        "phase": phase,
        "cursor": cursor,
        "event_id": event_id,
        "boot_id": _boot_id(),
        "artifacts": artifacts,
        "extra": dict(extra or {}),
    }
    manifest["manifest_sha256"] = digest(
        json.dumps(manifest["artifacts"], sort_keys=True, separators=(",", ":")).encode()
    )
    return manifest


def _boot_id() -> str:
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        return "unknown-boot-id"


def write_manifest(backend: RunBackend, manifest: Mapping[str, Any], *, name: str = MANIFEST_NAME) -> Path:
    path = backend.root / name
    fd = os.open(path, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return path


def read_manifest(path: Path) -> dict[str, Any]:
    require(path.is_file(), "run-state manifest is missing; refusing to reconstruct state")
    return json.loads(path.read_text(encoding="utf-8"))


def verify_reattach(backend: RunBackend, manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Reopen every pinned artifact and prove byte-for-byte identity.

    Returns a report; raises :class:`BackendError` on any mismatch.  A missing
    file is a failure, never an invitation to rebuild.
    """
    require(
        manifest.get("manifest_version") == MANIFEST_VERSION,
        "unknown run-state manifest version",
    )
    require(
        manifest.get("run_id") == backend.owner["run_id"],
        "run identity mismatch on re-attach",
    )
    require(
        manifest.get("session_id") == backend.owner["session_id"],
        "session identity mismatch on re-attach",
    )
    artifacts: Mapping[str, str] = manifest["artifacts"]
    require(
        manifest.get("manifest_sha256")
        == digest(
            json.dumps(dict(artifacts), sort_keys=True, separators=(",", ":")).encode()
        ),
        "run-state manifest corruption",
    )

    checked: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    for name, relative in SLOTS:
        expected = artifacts.get(relative)
        if expected is None:
            if name in REQUIRED_SLOTS:
                failures.append(f"missing pinned slot: {name}")
            else:
                checked[name] = {"status": "absent_never_created", "required": False}
            continue
        path = _slot_path(backend, relative)
        if not path.is_file():
            checked[name] = {"status": "MISSING", "required": name in REQUIRED_SLOTS}
            failures.append(f"slot vanished: {name} ({relative})")
            continue
        raw = path.read_bytes()
        actual = digest(raw)
        if actual != expected:
            checked[name] = {
                "status": "HASH_MISMATCH",
                "expected": expected,
                "actual": actual,
                "required": name in REQUIRED_SLOTS,
            }
            failures.append(f"slot changed: {name} ({relative})")
            continue
        checked[name] = {
            "status": "OK",
            "sha256": actual,
            "bytes": len(raw),
            "required": name in REQUIRED_SLOTS,
        }
        if relative.endswith(".sqlite"):
            # An openable SQLite file with a valid header is not the same as a
            # readable database; actually run an integrity check.
            try:
                db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=10)
                try:
                    result = db.execute("PRAGMA quick_check").fetchall()
                finally:
                    db.close()
                if result != [("ok",)]:
                    checked[name]["status"] = "SQLITE_CHECK_FAILED"
                    failures.append(f"sqlite quick_check failed: {name}")
            except sqlite3.Error as exc:  # pragma: no cover - defensive
                checked[name]["status"] = "SQLITE_UNREADABLE"
                failures.append(f"sqlite unreadable: {name}: {exc}")
        elif relative.endswith(".json") or relative.endswith(".jsonl"):
            try:
                if relative.endswith(".json"):
                    json.loads(raw.decode("utf-8"))
                else:
                    for line in raw.decode("utf-8").splitlines():
                        if line.strip():
                            json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                checked[name]["status"] = "JSON_UNREADABLE"
                failures.append(f"json unreadable: {name}: {exc}")

    report = {
        "manifest_version": MANIFEST_VERSION,
        "run_id": manifest.get("run_id"),
        "session_id": manifest.get("session_id"),
        "cursor": manifest.get("cursor"),
        "event_id": manifest.get("event_id"),
        "phase": manifest.get("phase"),
        "detach_boot_id": manifest.get("boot_id"),
        "attach_boot_id": _boot_id(),
        "slots": checked,
        "failures": failures,
        "reattached": not failures,
    }
    if failures:
        raise BackendError("re-attach verification failed: " + "; ".join(failures))
    return report
