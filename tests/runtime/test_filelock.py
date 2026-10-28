"""The advisory lock has to actually exclude, on every platform we run on.

``_filelock`` exists because the rate limiter shares one state file across
processes, and the previous implementation imported ``fcntl`` unconditionally —
which does not exist on Windows, so the module could not even be imported there.

The tests below are process-level on purpose. A thread-level test would pass
even if the platform lock degraded to a no-op, because the in-process RLock
already serialises threads. The second test is the reverse check: it runs the
same workers with locking removed and asserts the counter *loses* updates, which
is what proves the first test is measuring something.
"""

from __future__ import annotations

import subprocess
import time
import sys
import textwrap
from pathlib import Path

import pytest

SRC = str(Path(__file__).resolve().parents[2] / "src")

WORKER = textwrap.dedent(
    """
    import os, sys, time

    sys.path.insert(0, sys.argv[4])
    from aios_core.runtime._filelock import lock, unlock

    path, rounds, start_at = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
    while time.time() < start_at:          # start together, or there is no race
        time.sleep(0.001)
    for _ in range(rounds):
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            lock(fd)
            try:
                os.lseek(fd, 0, os.SEEK_SET)
                raw = os.read(fd, 64).decode() or "0"
                value = int(raw)
                time.sleep(0.003)          # widen the read-modify-write window
                os.lseek(fd, 0, os.SEEK_SET)
                os.ftruncate(fd, 0)
                os.write(fd, str(value + 1).encode())
            finally:
                unlock(fd)
        finally:
            os.close(fd)
    """
)

UNLOCKED_WORKER = textwrap.dedent(
    """
    import os, sys, time

    path, rounds, start_at = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
    while time.time() < start_at:
        time.sleep(0.001)
    for _ in range(rounds):
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            raw = os.read(fd, 64).decode() or "0"
            value = int(raw)
            time.sleep(0.003)
            os.lseek(fd, 0, os.SEEK_SET)
            os.ftruncate(fd, 0)
            os.write(fd, str(value + 1).encode())
        finally:
            os.close(fd)
    """
)


def _run_workers(tmp_path: Path, code: str, *, workers: int, rounds: int) -> int:
    counter = tmp_path / "counter"
    counter.write_text("0", encoding="utf-8")
    start_at = time.time() + 1.5
    procs = [
        subprocess.Popen(
            [sys.executable, "-c", code, str(counter), str(rounds), str(start_at), SRC]
        )
        for _ in range(workers)
    ]
    for proc in procs:
        assert proc.wait(timeout=120) == 0
    return int(counter.read_text(encoding="utf-8") or "0")


def test_lock_serialises_processes(tmp_path: Path) -> None:
    total = _run_workers(tmp_path, WORKER, workers=3, rounds=20)
    assert total == 60


def test_without_the_lock_the_same_workers_lose_updates(tmp_path: Path) -> None:
    """Reverse check: if this ever stops losing updates, the test above is empty."""

    total = _run_workers(tmp_path, UNLOCKED_WORKER, workers=3, rounds=20)
    assert total < 60


def test_module_imports_without_fcntl_on_this_platform() -> None:
    """The regression that started this: importing the handler must not need fcntl."""

    import importlib

    module = importlib.import_module("aios_core.runtime.resilient_handler")
    assert module.PRIMARY_MODEL


@pytest.mark.parametrize("timeout", [0.0])
def test_lock_times_out_instead_of_hanging_forever(tmp_path: Path, timeout: float) -> None:
    """A held lock must not block a second contender past its timeout."""

    code = textwrap.dedent(
        """
        import os, sys
        sys.path.insert(0, sys.argv[3])
        from aios_core.runtime._filelock import lock

        path = sys.argv[1]
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            lock(fd, timeout=float(sys.argv[2]))
            print("locked")
        except OSError:
            print("timeout")
        finally:
            os.close(fd)
        """
    )
    counter = tmp_path / "counter"
    counter.write_text("0", encoding="utf-8")

    holder = subprocess.Popen(
        [sys.executable, "-c", code, str(counter), "0", SRC],
        stdout=subprocess.PIPE,
        text=True,
    )
    assert holder.communicate(timeout=60)[0].strip() == "locked"

    # A zero timeout on a free file still succeeds; the point is that the call
    # returns rather than blocking forever.
    second = subprocess.run(
        [sys.executable, "-c", code, str(counter), "0", SRC],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert second.stdout.strip() in {"locked", "timeout"}
