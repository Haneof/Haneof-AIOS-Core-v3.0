"""Minimal process/lifecycle wrapper for the existing AIOS Core runtime.

This module deliberately owns no cognition, truth, scheduling policy, attempt ledger,
or conversation history. It opens the existing SQLite World, rebuildable search
projection and FusedTurnRuntime, then keeps one OS-level writer lease for the lifetime
of the process.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import errno
import importlib
import json
import os
from pathlib import Path
import socket
from typing import Any, Callable, Mapping

from aios_core.contracts.time import as_utc
from aios_core.ingest.reality import (
    IngestFailureReceipt,
    IngestReceipt,
    RealityRecord,
    SourceAdapterSpec,
)
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.cognitive_runtime import ModelHandler
from aios_core.runtime.turn_runtime import (
    FusedTurnResult,
    FusedTurnRuntime,
    PeriodicReviewRunResult,
    WakeDispatchRunResult,
)
from aios_core.storage.sqlite_store import SQLiteWorldStore


class HeadlessConfigurationError(ValueError):
    """The process cannot start with the requested headless configuration."""


class HeadlessWriterBusy(RuntimeError):
    """Another live process already owns the configured World writer lease."""


def load_model_handler(spec: str) -> ModelHandler:
    """Load an existing AIOS ModelHandler from a module:attribute reference.

    The referenced object is the normal CognitiveRuntime callable:
    RuntimeSnapshot -> ModelDirective. Provider choice and credentials stay in
    that adapter; the headless process does not make a provider constitutional.
    """

    if not isinstance(spec, str) or not spec.strip():
        raise HeadlessConfigurationError("model handler must be module:attribute")
    module_name, separator, attribute_name = spec.strip().partition(":")
    if not separator or not module_name or not attribute_name:
        raise HeadlessConfigurationError("model handler must be module:attribute")
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        raise HeadlessConfigurationError(
            f"cannot import model handler module {module_name!r}: {exc}"
        ) from exc
    try:
        handler = getattr(module, attribute_name)
    except AttributeError as exc:
        raise HeadlessConfigurationError(
            f"model handler attribute {attribute_name!r} not found in {module_name!r}"
        ) from exc
    if not callable(handler):
        raise HeadlessConfigurationError("configured model handler is not callable")
    return handler


@dataclass(frozen=True, slots=True)
class HeadlessConfig:
    world_path: Path
    index_path: Path | None = None
    lock_path: Path | None = None
    subject_id: str = "user_1"

    def __post_init__(self) -> None:
        world = Path(self.world_path).expanduser().resolve()
        if world.exists() and world.is_dir():
            raise HeadlessConfigurationError("world_path must be a SQLite file path")
        subject = self.subject_id.strip() if isinstance(self.subject_id, str) else ""
        if not subject:
            raise HeadlessConfigurationError("subject_id must not be blank")
        index = (
            Path(self.index_path).expanduser().resolve()
            if self.index_path is not None
            else Path(str(world) + ".search.sqlite")
        )
        lock = (
            Path(self.lock_path).expanduser().resolve()
            if self.lock_path is not None
            else Path(str(world) + ".writer.lock")
        )
        if index == world:
            raise HeadlessConfigurationError("index_path must not equal world_path")
        if lock in {world, index}:
            raise HeadlessConfigurationError("lock_path must not overlap SQLite files")
        object.__setattr__(self, "world_path", world)
        object.__setattr__(self, "index_path", index)
        object.__setattr__(self, "lock_path", lock)
        object.__setattr__(self, "subject_id", subject)


class _WriterLease:
    """Crash-safe advisory process lease; the lock file is never World truth."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._file: Any | None = None

    def acquire(self) -> None:
        if self._file is not None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+", encoding="utf-8")
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0, os.SEEK_END)
                if handle.tell() == 0:
                    handle.write("\n")
                    handle.flush()
                handle.seek(0)
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError as exc:
                    raise HeadlessWriterBusy(
                        f"World writer already active: {self.path}"
                    ) from exc
            else:
                import fcntl

                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError as exc:
                    if exc.errno in {errno.EACCES, errno.EAGAIN}:
                        raise HeadlessWriterBusy(
                            f"World writer already active: {self.path}"
                        ) from exc
                    raise

            metadata = {
                "kind": "aios-headless-writer-lease-v1",
                "pid": os.getpid(),
                "host": socket.gethostname(),
                "world_lock_path": str(self.path),
            }
            # Metadata is diagnostic only. Never use it to decide World state.
            handle.seek(0)
            handle.truncate()
            handle.write(json.dumps(metadata, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        except Exception:
            handle.close()
            raise
        self._file = handle

    def release(self) -> None:
        handle = self._file
        if handle is None:
            return
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()
            self._file = None

    @property
    def held(self) -> bool:
        return self._file is not None


@dataclass(frozen=True, slots=True)
class DueWorkResult:
    wakes: tuple[WakeDispatchRunResult, ...]
    periodic_review: PeriodicReviewRunResult | None


class HeadlessCore:
    """One writable process bound to the already-existing AIOS FusedTurnRuntime."""

    def __init__(
        self,
        *,
        config: HeadlessConfig,
        model_handler: ModelHandler,
        round_summary_handler: Callable[[Any], str] | None = None,
        dimension_summary_handler: Callable[[Any], str] | None = None,
    ) -> None:
        if not callable(model_handler):
            raise HeadlessConfigurationError("model_handler must be callable")
        self.config = config
        self.model_handler = model_handler
        self.round_summary_handler = round_summary_handler
        self.dimension_summary_handler = dimension_summary_handler
        self._lease = _WriterLease(config.lock_path)
        self.store: SQLiteWorldStore | None = None
        self.index: WorldSearchIndex | None = None
        self.runtime: FusedTurnRuntime | None = None

    def start(self) -> "HeadlessCore":
        if self.runtime is not None:
            return self
        self._lease.acquire()
        try:
            self.config.world_path.parent.mkdir(parents=True, exist_ok=True)
            self.config.index_path.parent.mkdir(parents=True, exist_ok=True)
            store = SQLiteWorldStore(self.config.world_path)
            index = WorldSearchIndex(self.config.index_path, store=store)
            index.catch_up()
            runtime = FusedTurnRuntime(
                store=store,
                index=index,
                subject_id=self.config.subject_id,
                model_handler=self.model_handler,
                round_summary_handler=self.round_summary_handler,
                dimension_summary_handler=self.dimension_summary_handler,
            )
            self.store = store
            self.index = index
            self.runtime = runtime
            return self
        except Exception:
            self.store = None
            self.index = None
            self.runtime = None
            self._lease.release()
            raise

    def stop(self) -> None:
        try:
            if self.index is not None:
                # World writes are transactional already. Catch the rebuildable
                # projection up before relinquishing the single-writer lease.
                self.index.catch_up()
        finally:
            self.runtime = None
            self.index = None
            self.store = None
            self._lease.release()

    def __enter__(self) -> "HeadlessCore":
        return self.start()

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.stop()

    def _require_started(
        self,
    ) -> tuple[SQLiteWorldStore, WorldSearchIndex, FusedTurnRuntime]:
        if self.store is None or self.index is None or self.runtime is None:
            raise RuntimeError("headless Core is not started")
        return self.store, self.index, self.runtime

    def status(self) -> dict[str, Any]:
        store, index, _runtime = self._require_started()
        return {
            "status": "ready",
            "subject_id": self.config.subject_id,
            "world_path": str(self.config.world_path),
            "index_path": str(self.config.index_path),
            "world_revision": int(store.current_world_revision()),
            "index_watermark": int(index.watermark()),
            "index_lag": int(index.lag()),
            "writer_lease_held": self._lease.held,
        }

    def submit_user_turn(
        self,
        *,
        session_id: str,
        turn_index: int,
        user_input: str,
        occurred_at: datetime,
        token_budget: int | None = None,
    ) -> FusedTurnResult:
        _store, _index, runtime = self._require_started()
        return runtime.run_turn(
            session_id=session_id,
            turn_index=turn_index,
            user_input=user_input,
            occurred_at=as_utc(occurred_at, "occurred_at"),
            token_budget=token_budget,
        )

    def ingest_external_fact(
        self,
        *,
        adapter: SourceAdapterSpec | Mapping[str, Any],
        record: RealityRecord | Mapping[str, Any],
    ) -> IngestReceipt | IngestFailureReceipt:
        _store, _index, runtime = self._require_started()
        spec = (
            adapter
            if isinstance(adapter, SourceAdapterSpec)
            else SourceAdapterSpec.model_validate(dict(adapter))
        )
        if isinstance(record, RealityRecord):
            return runtime.reality_ingest.ingest_record(spec, record)
        return runtime.reality_ingest.ingest_mapping(spec, dict(record))

    def process_due_work(
        self,
        *,
        now: datetime,
        max_wakes: int = 8,
        include_periodic_review: bool = True,
        token_budget: int | None = None,
    ) -> DueWorkResult:
        if type(max_wakes) is not int or max_wakes < 0:
            raise ValueError("max_wakes must be a non-negative integer")
        _store, _index, runtime = self._require_started()
        moment = as_utc(now, "now")
        wakes: list[WakeDispatchRunResult] = []
        for _ in range(max_wakes):
            result = runtime.dispatch_next_pending_wake(
                now=moment,
                token_budget=token_budget,
            )
            if result is None:
                break
            wakes.append(result)
        review = (
            runtime.run_periodic_review(now=moment, token_budget=token_budget)
            if include_periodic_review
            else None
        )
        return DueWorkResult(wakes=tuple(wakes), periodic_review=review)
