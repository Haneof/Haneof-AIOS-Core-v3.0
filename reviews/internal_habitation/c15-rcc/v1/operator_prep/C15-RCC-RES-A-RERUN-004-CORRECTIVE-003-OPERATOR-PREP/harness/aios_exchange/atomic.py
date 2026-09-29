"""Durable single-file publication primitives.

Sequence for every published artifact (request, response, ledger record):

1. write the complete bytes to a temporary file in the *same* directory;
2. ``flush`` + ``os.fsync`` the temporary file descriptor;
3. atomically move it into place with ``os.replace``;
4. ``fsync`` the containing directory (required on the qualified Linux runtime).

A reader therefore observes either no file or the complete file; partially
written content is never observable under the published name. A rename that is
visible but whose directory fsync fails is NOT a successful publication. A retry
must verify/resync those bytes or replace them durably before recording dispatch.
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
    "sync_existing_bytes",
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
    """Require directory durability; never turn an open/fsync error into a receipt.

    Directory fsync is supported and required on the qualified Linux runtime.
    Keep the bool return only for the existing receipt shape (always True on
    success); an OSError at either required primitive propagates to the caller.
    """

    flags = os.O_RDONLY | os.O_DIRECTORY
    fd = os.open(str(directory), flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    COUNTERS["dir_fsync"] += 1
    return True


def sync_existing_bytes(path: str | pathlib.Path) -> bytes:
    """Re-prove durability of a visible orphan/replay before trusting its bytes.

    Required when a prior failed publication may have left bytes visible after
    replace, and before a ledger fact can describe those bytes as durable. The
    inode check prevents a different file at the published name from being
    silently substituted between reading/fsyncing and the directory fsync.
    """

    target = pathlib.Path(path)
    with open(target, "rb") as handle:
        data = handle.read()
        os.fsync(handle.fileno())
        opened = os.fstat(handle.fileno())
        named = os.stat(target, follow_symlinks=False)
        if (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino):
            raise AtomicPublishError("published file changed while durability was being verified")
        fsync_dir(target.parent)
    return data


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
