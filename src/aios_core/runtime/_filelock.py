"""Cross-platform exclusive file lock.

The rate limiter coordinates several processes through one shared state file, so
it needs an advisory lock that works wherever the project actually runs. POSIX
has ``fcntl.flock``; Windows has ``msvcrt.locking``, which locks a byte range at
the current file position and offers no blocking mode — the wait is a bounded
retry loop here.

Why not a third-party package: the runtime is deliberately dependency-free (the
SSE client is plain ``urllib``), and a lock is small enough to own.

Contract
--------
``lock`` blocks until it holds the lock, or raises ``OSError`` if the platform
cannot lock at all (some network filesystems). Callers treat that as "no
cross-process coordination available" and degrade, rather than failing the turn.
"""

from __future__ import annotations

import os
import time

if os.name == "nt":  # pragma: no cover - exercised on Windows only
    import msvcrt

    _LOCK_BYTES = 1
else:  # pragma: no cover - exercised on POSIX only
    import fcntl

# Windows has no blocking byte-range lock, so wait in small steps. The waiters
# here are rate-limit contenders; a 20ms poll is well under the pacing interval.
_POLL_SECONDS = 0.02
_DEFAULT_TIMEOUT = 120.0


def lock(fd: int, *, timeout: float = _DEFAULT_TIMEOUT) -> None:
    """Take an exclusive lock on ``fd``. Raises ``OSError`` if unavailable."""

    if os.name == "nt":
        deadline = time.monotonic() + timeout
        while True:
            try:
                # The lock covers one byte from the current position, and the
                # position moves as the caller reads and writes the state file.
                # Anchor it at 0 every attempt so all processes contend for the
                # same byte.
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, _LOCK_BYTES)
                return
            except OSError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(_POLL_SECONDS)

    fcntl.flock(fd, fcntl.LOCK_EX)


def unlock(fd: int) -> None:
    """Release the lock taken by :func:`lock`. Safe to call after a failed lock."""

    if os.name == "nt":
        # Unlocking is also position-relative; the caller may have written to
        # the file and left the descriptor at EOF.
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, _LOCK_BYTES)
        return

    fcntl.flock(fd, fcntl.LOCK_UN)
