"""Authoritative non-ephemeral run backend for the C15 persistence corrective.

Historical context
------------------
The original RERUN-002 incident was an *environment* state loss: the operator run
root lived under ``/tmp`` and the whole root disappeared when the platform
execution environment was torn down.  A process restart inside the same
environment is therefore NOT the same boundary, and proving the former requires a
backend whose durability contract is explicit and mechanically testable.

This module defines that contract:

* **exact authoritative backend/path** - a private child directory of the
  platform-persisted workspace ``/home/user``.  ``/tmp``, ``/var/tmp``,
  ``/dev/shm``, ``/run``, any tmpfs/ramfs-backed mount and any path component
  excluded from platform persistence are rejected.  Symlink aliases are
  rejected because a symlink can quietly redirect a "persisted" path onto an
  ephemeral one.
* **persistence ownership** - exactly one writer process owns a run.  Ownership
  is an advisory ``flock`` on ``<root>/.owner.lock`` plus an immutable
  ``owner.json`` identity record.  The lock stops cooperating drivers; the
  identity record stops a *fresh* process from silently rebuilding a lost run.
* **creation semantics** - exclusive.  Creation never adopts, never repairs and
  never rebuilds.  A backend that already exists is a hard error.
* **reopen semantics** - reopen is read/write against *existing* state only.
  Missing state, wrong identity, corrupt state or a live foreign owner are all
  hard errors.  Reopening after a dead owner is possible but must be requested
  explicitly (``adopt_stale_owner=True``) and is recorded in the audit trail.
* **locking semantics** - exclusive flock for the whole process lifetime, plus
  directory fsync of every durability barrier.
* **backup/checkpoint semantics** - immutable sealed *generations*.  A
  generation is a directory of exact artifact bytes plus a SHA-256 manifest;
  once sealed the directory is read-only and every later open re-verifies every
  hash.  Generations are never rewritten in place.

This module is operator-side durability only.  It stores bytes and manifests; it
never interprets a ModelDirective, never executes capability semantics, never
produces assistant output, never forges a receipt and never decides that a
response was applied.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import sqlite3
import stat
import time
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any, Iterator, Mapping, Sequence

WORKSPACE = Path("/home/user")

#: Path components the platform excludes from persistence.  A backend under any
#: of these can vanish with the execution environment.
EXCLUDED = frozenset(
    {
        ".arena",
        ".cache",
        ".git",
        ".local",
        ".mypy_cache",
        ".next",
        ".nox",
        ".npm",
        ".nuxt",
        ".output",
        ".parcel-cache",
        ".pytest_cache",
        ".ruff_cache",
        ".svelte-kit",
        ".tox",
        ".turbo",
        ".venv",
        ".vite",
        "__pycache__",
        "build",
        "coverage",
        "dist",
        "node_modules",
        "out",
        "target",
    }
)

#: Absolute spellings that are ephemeral regardless of what they are mounted on.
EPHEMERAL_ROOTS = ("/tmp", "/var/tmp", "/dev/shm", "/run", "/dev", "/proc", "/sys")

#: Default authoritative location for operator run roots created by this
#: corrective.  It is a private child of the persisted workspace and is not one
#: of the excluded components above.
DEFAULT_RUNS_ROOT = WORKSPACE / "c15-persistence-runs"

EPHEMERAL_FILESYSTEMS = frozenset({"tmpfs", "ramfs"})


class BackendError(RuntimeError):
    """Raised for every durability-contract violation. Always fail closed."""


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise BackendError(reason)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def fsync_file(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def backing_filesystem(root: Path) -> str:
    """Longest matching mount entry's filesystem type for ``root``."""
    best: tuple[int, str] | None = None
    for line in Path("/proc/self/mountinfo").read_text().splitlines():
        fields = line.split()
        if len(fields) < 10 or "-" not in fields:
            continue
        target = Path(fields[4].replace("\\040", " ").replace("\\134", "\\"))
        if not root.is_relative_to(target):
            continue
        fstype = fields[fields.index("-") + 1]
        if best is None or len(target.parts) > best[0]:
            best = (len(target.parts), fstype)
    require(best is not None, "cannot determine backing filesystem")
    return str(best[1])


def durable_root(root: str | Path) -> Path:
    """Validate and canonicalise an authoritative backend path.

    Rejects (non-exhaustive): symlinked or non-canonical spellings, anything
    outside the persisted workspace, workspace roots themselves, excluded
    snapshot components, absolute ephemeral roots, and tmpfs/ramfs backing
    mounts - including a tmpfs mounted *under* a persisted path.
    """
    candidate = Path(root)
    require(candidate.is_absolute(), "backend path must be absolute")
    resolved = candidate.resolve()
    require(resolved == Path(os.path.normpath(str(candidate))), "backend path is not canonical")
    require(
        not any(part in ("", ".", "..") for part in PurePosixPath(str(candidate)).parts[1:]),
        "degenerate backend path",
    )
    for bad in EPHEMERAL_ROOTS:
        require(
            str(resolved) != bad and not str(resolved).startswith(bad + "/"),
            f"ephemeral backend path: {bad}",
        )
    require(resolved.is_relative_to(WORKSPACE), "backend must live under the persisted workspace")
    require(resolved != WORKSPACE, "backend must be a private child, not the workspace root")
    relative = resolved.relative_to(WORKSPACE)
    require(not (set(relative.parts) & EXCLUDED), "backend path is excluded from platform persistence")
    require(
        backing_filesystem(resolved) not in EPHEMERAL_FILESYSTEMS,
        "ephemeral backing filesystem",
    )
    return resolved


def runs_root() -> Path:
    """Authoritative parent for operator run roots (env-overridable for tests)."""
    override = os.environ.get("C15_PERSISTENCE_RUNS_ROOT")
    if override:
        return durable_root(override)
    return durable_root(DEFAULT_RUNS_ROOT)


def _boot_id() -> str:
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        return "unknown-boot-id"


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class RunBackend:
    """Owned, locked, non-ephemeral operator run backend.

    Sub-layout::

        <root>/.owner.lock      advisory flock held for the process lifetime
        <root>/owner.json       immutable creator identity record
        <root>/journal.sqlite   production relay journal (see relay.py)
        <root>/state/           live run state (world, index, release state, ...)
        <root>/mailbox/         provider outbox / inbox / dispatch ledger
        <root>/generations/     immutable sealed checkpoint generations
        <root>/audit.jsonl      append-only durability audit trail
    """

    OWNER_NAME = "owner.json"
    LOCK_NAME = ".owner.lock"
    AUDIT_NAME = "audit.jsonl"

    def __init__(self, root: Path) -> None:
        self.root = root
        self._lock_fd: int | None = None
        self._owner: dict[str, Any] | None = None

    # ---------------------------------------------------------------- create

    @classmethod
    def create(
        cls,
        root: str | Path,
        *,
        run_id: str,
        session_id: str,
        subject_id: str,
        phase: str,
    ) -> "RunBackend":
        root = durable_root(root)
        require(bool(run_id) and bool(session_id), "run/session identity required")
        require(
            not run_id.startswith("c15-rcc-res-b-rerun-002"),
            "retired RERUN-002 run identity is permanently forbidden",
        )
        require(
            not session_id.startswith("c15-rcc-res-b-session-002"),
            "retired RERUN-002 session identity is permanently forbidden",
        )
        require(root.parent.is_dir(), "backend parent must already exist")
        require(not root.exists(), "backend already exists; creation never adopts")

        root.mkdir(mode=0o700)
        fsync_dir(root.parent)
        for child in ("state", "mailbox", "generations"):
            (root / child).mkdir(mode=0o700)
        fsync_dir(root)

        backend = cls(root)
        owner = {
            "run_id": run_id,
            "session_id": session_id,
            "subject_id": subject_id,
            "phase": phase,
            "created_at_epoch": time.time(),
            "creator_pid": os.getpid(),
            "boot_id": _boot_id(),
            "backend_version": "c15-persistence-backend-v1",
        }
        owner_path = root / cls.OWNER_NAME
        fd = os.open(owner_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(owner, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        fsync_dir(root)
        backend._acquire_lock()
        backend._owner = owner
        backend.audit("backend_created", {"run_id": run_id, "session_id": session_id})
        return backend

    # ----------------------------------------------------------------- open

    @classmethod
    def open(
        cls,
        root: str | Path,
        *,
        run_id: str,
        session_id: str,
        adopt_stale_owner: bool = False,
    ) -> "RunBackend":
        """Reopen an existing backend. Never reconstructs missing state."""
        root = durable_root(root)
        require(root.is_dir(), "backend does not exist; reopen never creates")
        owner_path = root / cls.OWNER_NAME
        require(owner_path.is_file(), "backend ownership record is missing; refusing to rebuild a lost run")
        owner = json.loads(owner_path.read_text(encoding="utf-8"))
        require(owner.get("run_id") == run_id, "backend run identity mismatch")
        require(owner.get("session_id") == session_id, "backend session identity mismatch")

        backend = cls(root)
        live = backend._try_lock()
        if not live:
            recorded_pid = int(owner.get("creator_pid", 0) or 0)
            same_boot = owner.get("boot_id") == _boot_id()
            stale = (not same_boot) or (not pid_alive(recorded_pid))
            require(
                stale and adopt_stale_owner,
                "backend is owned by another live process; refusing concurrent ownership",
            )
            backend.audit(
                "stale_owner_adopted",
                {"previous_pid": recorded_pid, "previous_boot_id": owner.get("boot_id")},
            )
        elif adopt_stale_owner:
            backend.audit("owner_reclaimed", {"pid": os.getpid()})
        backend._owner = owner
        backend.audit("backend_reopened", {"run_id": run_id, "session_id": session_id})
        return backend

    # ---------------------------------------------------------------- locks

    def _lock_path(self) -> Path:
        return self.root / self.LOCK_NAME

    def _acquire_lock(self) -> None:
        require(self._lock_fd is None, "backend lock already held")
        fd = os.open(self._lock_path(), os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            raise BackendError("backend is locked by another live process")
        os.ftruncate(fd, 0)
        os.write(fd, f"{os.getpid()}\n".encode())
        os.fsync(fd)
        self._lock_fd = fd

    def _try_lock(self) -> bool:
        fd = os.open(self._lock_path(), os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            return False
        os.ftruncate(fd, 0)
        os.write(fd, f"{os.getpid()}\n".encode())
        os.fsync(fd)
        self._lock_fd = fd
        return True

    def release(self) -> None:
        if self._lock_fd is not None:
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
            finally:
                os.close(self._lock_fd)
                self._lock_fd = None

    @property
    def owner(self) -> Mapping[str, Any]:
        require(self._owner is not None, "backend not initialised")
        return dict(self._owner)

    # ---------------------------------------------------------------- audit

    def audit(self, event: str, detail: Mapping[str, Any] | None = None) -> None:
        record = {
            "event": event,
            "at_epoch": time.time(),
            "pid": os.getpid(),
            "boot_id": _boot_id(),
            "detail": dict(detail or {}),
        }
        path = self.root / self.AUDIT_NAME
        fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def audit_trail(self) -> list[dict[str, Any]]:
        path = self.root / self.AUDIT_NAME
        if not path.is_file():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    # ------------------------------------------------------------ locations

    @property
    def state_dir(self) -> Path:
        return self.root / "state"

    @property
    def mailbox_dir(self) -> Path:
        return self.root / "mailbox"

    @property
    def generations_dir(self) -> Path:
        return self.root / "generations"

    @property
    def journal_path(self) -> Path:
        return self.root / "journal.sqlite"

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"RunBackend({str(self.root)!r})"


class GenerationStore:
    """Immutable sealed checkpoint generations with whole-bundle hash manifests.

    A generation is created by writing every artifact into a fresh directory and
    then *sealing* it: the manifest is written, every file is fsynced, the
    directory is fsynced and the directory mode drops to ``0o500``.  Sealed
    generations are never mutated; ``verify`` recomputes every hash on every
    open.
    """

    MANIFEST_NAME = "manifest.json"
    SEAL_NAME = ".sealed"

    def __init__(self, backend: RunBackend) -> None:
        self.backend = backend
        self.root = backend.generations_dir

    def _generation_dir(self, generation: int) -> Path:
        return self.root / f"{generation:06d}"

    def next_generation(self) -> int:
        existing = sorted(p.name for p in self.root.glob("[0-9]" * 6) if p.is_dir())
        return (int(existing[-1]) + 1) if existing else 1

    def seal(self, artifacts: Mapping[str, bytes], *, label: str) -> int:
        require(bool(artifacts), "generation needs at least one artifact")
        for name, body in artifacts.items():
            path = PurePosixPath(name)
            require(
                not path.is_absolute() and ".." not in path.parts and str(path) == name,
                f"unsafe artifact name: {name}",
            )
            require(type(body) is bytes, "artifact must be exact bytes")
        generation = self.next_generation()
        target = self._generation_dir(generation)
        require(not target.exists(), "generation collision")
        target.mkdir(mode=0o700)
        manifest: dict[str, str] = {}
        for name, body in artifacts.items():
            child = target / name
            child.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(child, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
            manifest[name] = digest(body)
        manifest_path = target / self.MANIFEST_NAME
        fd = os.open(manifest_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(
                json.dumps(
                    {
                        "generation": generation,
                        "label": label,
                        "sealed_at_epoch": time.time(),
                        "artifacts": manifest,
                        "manifest_sha256": digest(canonical_json(manifest)),
                    },
                    sort_keys=True,
                    indent=2,
                )
                + "\n"
            )
            stream.flush()
            os.fsync(stream.fileno())
        seal = target / self.SEAL_NAME
        fd = os.open(seal, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(f"{generation}\n")
            stream.flush()
            os.fsync(stream.fileno())
        for directory in sorted({target} | {p for p in target.rglob("*") if p.is_dir()}, key=lambda p: len(p.parts), reverse=True):
            fsync_dir(directory)
        os.chmod(target, 0o500)
        fsync_dir(self.root)
        self.backend.audit(
            "generation_sealed",
            {"generation": generation, "label": label, "artifacts": len(manifest)},
        )
        return generation

    def manifest(self, generation: int) -> dict[str, Any]:
        path = self._generation_dir(generation) / self.MANIFEST_NAME
        require(path.is_file(), "generation manifest missing")
        return json.loads(path.read_text(encoding="utf-8"))

    def verify(self, generation: int) -> dict[str, Any]:
        """Recompute every artifact hash. Raises on any mismatch."""
        target = self._generation_dir(generation)
        require(target.is_dir(), "generation missing")
        require((target / self.SEAL_NAME).is_file(), "generation is not sealed")
        manifest = self.manifest(generation)
        artifacts: dict[str, str] = manifest["artifacts"]
        require(
            manifest.get("manifest_sha256") == digest(canonical_json(artifacts)),
            "generation manifest corruption",
        )
        for name, expected in artifacts.items():
            child = target / name
            require(child.is_file(), f"generation artifact missing: {name}")
            require(digest(child.read_bytes()) == expected, f"generation artifact corruption: {name}")
        return manifest

    def read(self, generation: int, name: str) -> bytes:
        self.verify(generation)
        child = self._generation_dir(generation) / name
        require(child.is_file(), f"generation artifact missing: {name}")
        return child.read_bytes()

    def latest(self) -> int | None:
        sealed = sorted(
            int(p.name)
            for p in self.root.glob("[0-9]" * 6)
            if p.is_dir() and (p / self.SEAL_NAME).is_file()
        )
        return sealed[-1] if sealed else None

    def verify_all(self) -> list[int]:
        verified = []
        for generation in sorted(
            int(p.name) for p in self.root.glob("[0-9]" * 6) if p.is_dir()
        ):
            self.verify(generation)
            verified.append(generation)
        return verified


def sqlite_snapshot(path: Path) -> bytes:
    """Coherent SQLite snapshot bytes using the online backup API.

    Used for World / index bytes: a raw file copy of a live SQLite database is
    not a coherent snapshot, and pretending otherwise would silently corrupt a
    "checkpoint".
    """
    require(path.is_file(), f"sqlite database missing: {path}")
    memory = sqlite3.connect(":memory:")
    try:
        source = sqlite3.connect(str(path))
        try:
            source.backup(memory)
        finally:
            source.close()
        out = sqlite3.connect(":memory:")
        try:
            memory.backup(out)
        finally:
            pass
        # ``out`` is an in-memory copy; serialise via backup into a temp file.
        temp = Path(os.environ.get("C15_PERSISTENCE_TMPDIR", str(path.parent))) / (
            "." + path.name + ".snapshot"
        )
        disk = sqlite3.connect(str(temp))
        try:
            out.backup(disk)
        finally:
            disk.close()
        raw = temp.read_bytes()
        temp.unlink()
        return raw
    finally:
        memory.close()
