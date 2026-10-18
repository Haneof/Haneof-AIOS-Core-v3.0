"""Durable single-file publication primitives.

Sequence for every published artifact (request, response, ledger record):

1. write the complete bytes to a temporary file in the *same* directory;
2. ``flush`` + ``os.fsync`` the temporary file descriptor;
3. atomically move it into place with ``os.replace``;
4. ``fsync`` the containing directory where the platform supports it.

A reader therefore observes either no file or the complete file; partially
written content is never observable under the published name.
"""

from __future__ import annotations

import itertools
import os
import pathlib
from typing import Any

from .canonical import canonical_json_bytes, sha256_hex, utc_now_iso

_TEMP_COUNTER = itertools.count(1)

__all__ = [
    "COUNTERS",
    "AtomicPublishError",
    "atomic_write_bytes",
    "atomic_write_json",
    "fsync_dir",
    "read_bytes",
    "reset_counters",
]

#: Mechanical instrumentation so tests can prove which primitives ran.
COUNTERS: dict[str, int] = {
    "temp_writes": 0,
    "file_fsync": 0,
    "dir_fsync": 0,
    "replace": 0,
}


class AtomicPublishError(RuntimeError):
    """Publication could not be completed durably."""


def reset_counters() -> None:
    for key in COUNTERS:
        COUNTERS[key] = 0


def _temp_path(path: pathlib.Path) -> pathlib.Path:
    return path.parent / f".{path.name}.tmp-{os.getpid()}-{next(_TEMP_COUNTER)}"


def fsync_dir(directory: pathlib.Path) -> bool:
    """Fsync a directory entry list. Returns True when the fsync happened."""

    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    try:
        fd = os.open(str(directory), flags)
    except OSError:
        return False
    try:
        os.fsync(fd)
    except OSError:
        return False
    finally:
        os.close(fd)
    COUNTERS["dir_fsync"] += 1
    return True


def atomic_write_bytes(
    path: str | pathlib.Path,
    data: bytes,
    *,
    create_parents: bool = True,
) -> dict[str, Any]:
    """Durably publish ``data`` at ``path``. Returns a publication receipt."""

    target = pathlib.Path(path)
    if create_parents:
        target.parent.mkdir(parents=True, exist_ok=True)
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise AtomicPublishError("atomic_write_bytes requires bytes")
    payload = bytes(data)

    tmp = _temp_path(target)
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        COUNTERS["temp_writes"] += 1
        COUNTERS["file_fsync"] += 1
        os.replace(str(tmp), str(target))
        COUNTERS["replace"] += 1
    except BaseException:
        try:
            os.unlink(str(tmp))
        except OSError:
            pass
        raise
    directory_fsynced = fsync_dir(target.parent)
    return {
        "path": str(target),
        "sha256": sha256_hex(payload),
        "bytes": len(payload),
        "wall_clock": utc_now_iso(),
        "fsync_file": True,
        "fsync_directory": directory_fsynced,
        "atomic_replace": True,
    }


def atomic_write_json(
    path: str | pathlib.Path,
    payload: Any,
    *,
    create_parents: bool = True,
) -> dict[str, Any]:
    """Publish canonical JSON bytes plus a trailing newline."""

    return atomic_write_bytes(
        path, canonical_json_bytes(payload) + b"\n", create_parents=create_parents
    )


def read_bytes(path: str | pathlib.Path) -> bytes:
    with open(path, "rb") as handle:
        return handle.read()
