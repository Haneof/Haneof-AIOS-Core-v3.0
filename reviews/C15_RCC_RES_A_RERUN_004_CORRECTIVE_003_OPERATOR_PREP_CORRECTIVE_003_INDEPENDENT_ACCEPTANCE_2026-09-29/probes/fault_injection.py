"""Reviewer-authored fault injection: directory durability only.

The injector fails *directory* fsync/os.open(O_DIRECTORY) for a set of paths
while every ordinary regular-file fsync/open continues to work untouched. The
counters let a probe prove that the fault was specific (files still synced).

No candidate source is edited: `os.open`/`os.fsync` are replaced at run time in
the probe process only.
"""

from __future__ import annotations

import os
import pathlib
import stat

_REAL_OPEN = os.open
_REAL_FSYNC = os.fsync


class FaultConfig:
    def __init__(
        self,
        *,
        dir_fsync_fail: tuple[str, ...] = (),
        dir_open_fail: tuple[str, ...] = (),
        file_fsync_fail: tuple[str, ...] = (),
    ) -> None:
        self.dir_fsync_fail = {os.path.realpath(str(p)) for p in dir_fsync_fail}
        self.dir_open_fail = {os.path.realpath(str(p)) for p in dir_open_fail}
        self.file_fsync_fail = {os.path.realpath(str(p)) for p in file_fsync_fail}
        self.counters: dict[str, int] = {
            "dir_open_ok": 0,
            "dir_open_failed": 0,
            "dir_fsync_ok": 0,
            "dir_fsync_failed": 0,
            "file_fsync_ok": 0,
            "file_fsync_failed": 0,
        }

    def as_dict(self) -> dict:
        return {
            "dir_fsync_fail": sorted(self.dir_fsync_fail),
            "dir_open_fail": sorted(self.dir_open_fail),
            "file_fsync_fail": sorted(self.file_fsync_fail),
            "counters": dict(self.counters),
        }


def _fd_path(fd: int) -> str | None:
    try:
        return os.readlink(f"/proc/self/fd/{fd}")
    except OSError:
        return None


def install(config: FaultConfig) -> FaultConfig:
    def _open(path, flags, *args, **kwargs):
        if isinstance(flags, int) and flags & getattr(os, "O_DIRECTORY", 0):
            real = os.path.realpath(str(path))
            if real in config.dir_open_fail:
                config.counters["dir_open_failed"] += 1
                raise OSError(5, "injected directory open failure", str(path))
            config.counters["dir_open_ok"] += 1
        return _REAL_OPEN(path, flags, *args, **kwargs)

    def _fsync(fd):
        path = _fd_path(fd)
        real = os.path.realpath(path) if path else None
        try:
            mode = os.fstat(fd).st_mode
        except OSError:
            mode = 0
        if stat.S_ISDIR(mode):
            if real is not None and real in config.dir_fsync_fail:
                config.counters["dir_fsync_failed"] += 1
                raise OSError(5, "injected directory fsync failure", real)
            config.counters["dir_fsync_ok"] += 1
        else:
            if real is not None and real in config.file_fsync_fail:
                config.counters["file_fsync_failed"] += 1
                raise OSError(5, "injected file fsync failure", real)
            config.counters["file_fsync_ok"] += 1
        return _REAL_FSYNC(fd)

    os.open = _open
    os.fsync = _fsync
    return config


def restore() -> None:
    os.open = _REAL_OPEN
    os.fsync = _REAL_FSYNC


def visible_files(root: str | pathlib.Path) -> list[str]:
    root_path = pathlib.Path(root)
    if not root_path.exists():
        return []
    return sorted(
        p.relative_to(root_path).as_posix()
        for p in root_path.rglob("*")
        if p.is_file()
    )
