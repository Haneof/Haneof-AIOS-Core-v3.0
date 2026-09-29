"""Append-only, hash-chained exchange ledger.

Every durable exchange fact is recorded exactly once, in order, and each record
chains to its predecessor:

``record_sha256 = sha256(canonical_json(record_without_record_sha256))``

with ``prev_sha256`` inside the hashed body. Any insertion, deletion, reordering
or edit of an interior record breaks the chain and is detected. Complete-record
tail deletion cannot be distinguished from a valid prefix without an external
head anchor; this ledger does not claim to detect it.

Recorded events (at minimum):

* ``request_published``  -> sequence, request_id, request_sha256, wall clock
* ``response_published`` -> the above plus response_sha256
* ``response_consumed``  -> the above plus response_sha256
"""

from __future__ import annotations

from contextlib import contextmanager
import fcntl
import json
import os
import pathlib
import re
import stat
import threading
from typing import Any, Iterable, Iterator

from .canonical import canonical_json_bytes, sha256_hex, utc_now_iso
from .atomic import fsync_dir

__all__ = [
    "LEDGER_EVENT_REQUEST_PUBLISHED",
    "LEDGER_EVENT_RESPONSE_PUBLISHED",
    "LEDGER_EVENT_RESPONSE_CONSUMED",
    "LEDGER_EVENTS",
    "LedgerError",
    "ExchangeLedger",
]

LEDGER_EVENT_REQUEST_PUBLISHED = "request_published"
LEDGER_EVENT_RESPONSE_PUBLISHED = "response_published"
LEDGER_EVENT_RESPONSE_CONSUMED = "response_consumed"

LEDGER_EVENTS = (
    LEDGER_EVENT_REQUEST_PUBLISHED,
    LEDGER_EVENT_RESPONSE_PUBLISHED,
    LEDGER_EVENT_RESPONSE_CONSUMED,
)

GENESIS_SHA256 = "0" * 64

# The Python mutex only makes same-process threads reentrant. Every outermost
# transaction ALSO owns an exclusive flock on the same dedicated inode, shared
# by independent Python objects and OS processes. Neither is a state store.
_MUTEX_GUARD = threading.Lock()
_MUTEXES: dict[str, threading.RLock] = {}
_HELD = threading.local()


def _mutex_for(key: str) -> threading.RLock:
    with _MUTEX_GUARD:
        return _MUTEXES.setdefault(key, threading.RLock())


class LedgerError(RuntimeError):
    """The ledger/lock is unreadable, non-monotonic or cannot be made durable."""


class ExchangeLedger:
    """Append-only hash-chained JSON-lines ledger with a shared writer boundary."""

    def __init__(self, path: str | pathlib.Path) -> None:
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Never lock the ledger itself: its entry is absent before creation and
        # its inode could change. The dedicated lock file is never unlinked.
        self.lock_path = self.path.with_name(self.path.name + ".lock")
        self._lock_key = str(self.lock_path.resolve())

    def _acquire_os_lock(self) -> int:
        fd: int | None = None
        try:
            fd = os.open(str(self.lock_path), os.O_RDWR | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
            opened = os.fstat(fd)
            if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
                raise LedgerError("exchange lock path is not a single regular file")
            fcntl.flock(fd, fcntl.LOCK_EX)
            named = os.stat(self.lock_path, follow_symlinks=False)
            if (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino):
                raise LedgerError("exchange lock path changed during acquisition")
            return fd
        except (OSError, LedgerError) as exc:
            if fd is not None:
                os.close(fd)
            raise LedgerError(f"cannot acquire exchange mutation lock: {exc}") from exc

    def _release_os_lock(self, fd: int) -> None:
        try:
            named = os.stat(self.lock_path, follow_symlinks=False)
            opened = os.fstat(fd)
            if (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino):
                raise LedgerError("exchange mutation lock ownership changed")
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError as exc:
            raise LedgerError(f"cannot release exchange mutation lock: {exc}") from exc
        finally:
            os.close(fd)

    @contextmanager
    def mutation(self) -> Iterator[None]:
        """One read/validate/decide/publish/append/durability transaction.

        Callers use this outer boundary around *all* prefix-derived decisions.
        Direct ledger append/read also use it. A thread reentering through a
        nested caller or another ExchangeLedger for this path reuses its owned
        OS lock instead of taking a non-reentrant flock twice. Other threads
        and other processes must acquire their own exclusive OS lock.
        """
        with _mutex_for(self._lock_key):
            held = getattr(_HELD, "files", None)
            if held is None:
                held = {}
                _HELD.files = held
            if self._lock_key in held:
                held[self._lock_key] += 1
                try:
                    yield
                finally:
                    held[self._lock_key] -= 1
                return
            fd = self._acquire_os_lock()
            held[self._lock_key] = 1
            try:
                yield
            finally:
                del held[self._lock_key]
                self._release_os_lock(fd)

    # -- reading ---------------------------------------------------------
    def _read_raw_records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        raw = self.path.read_bytes()
        if raw and not raw.endswith(b"\n"):
            raise LedgerError("ledger ends with a torn (unterminated) record")
        records: list[dict[str, Any]] = []
        for lineno, line in enumerate(raw.splitlines(), start=1):
            if not line.strip():
                raise LedgerError(f"ledger line {lineno} is blank")
            try:
                record = json.loads(line.decode("utf-8"))
            except Exception as exc:  # torn or corrupt append
                raise LedgerError(f"ledger line {lineno} is not valid JSON: {exc}") from exc
            if not isinstance(record, dict):
                raise LedgerError(f"ledger line {lineno} is not an object")
            records.append(record)
        return records

    @staticmethod
    def _validate_records(records: list[dict[str, Any]]) -> None:
        """Non-recursive operational precondition; no lookup or append calls."""
        previous = GENESIS_SHA256
        states: dict[str, list[dict[str, Any]]] = {}
        def digest(value: Any) -> bool:
            return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None
        for seq, record in enumerate(records, 1):
            required = {"seq", "event", "request_id", "request_sha256", "response_sha256",
                        "wall_clock", "prev_sha256", "record_sha256"}
            if not required <= record.keys():
                raise LedgerError(f"missing ledger fields at seq {seq}")
            if type(record["seq"]) is not int or record["seq"] != seq:
                raise LedgerError(f"non-monotonic sequence at seq {seq}")
            if record["prev_sha256"] != previous:
                raise LedgerError(f"broken hash chain at seq {seq}")
            body = {k: v for k, v in record.items() if k != "record_sha256"}
            if record["record_sha256"] != sha256_hex(canonical_json_bytes(body)):
                raise LedgerError(f"record digest mismatch at seq {seq}")
            event, rid = record["event"], record["request_id"]
            if event not in LEDGER_EVENTS or not isinstance(rid, str) or not rid.strip():
                raise LedgerError(f"illegal event or request identity at seq {seq}")
            if not isinstance(record["wall_clock"], str) or not record["wall_clock"].strip():
                raise LedgerError(f"missing wall clock at seq {seq}")
            history = states.setdefault(rid, [])
            if len(history) >= 3 or event != LEDGER_EVENTS[len(history)]:
                raise LedgerError(f"duplicate event or illegal event order at seq {seq}")
            if not digest(record["request_sha256"]):
                raise LedgerError(f"invalid request digest at seq {seq}")
            if history and record["request_sha256"] != history[0]["request_sha256"]:
                raise LedgerError(f"request digest discontinuity at seq {seq}")
            if not history:
                if record["response_sha256"] is not None:
                    raise LedgerError(f"response before publication at seq {seq}")
            elif not digest(record["response_sha256"]):
                raise LedgerError(f"invalid response digest at seq {seq}")
            elif len(history) == 2 and record["response_sha256"] != history[1]["response_sha256"]:
                raise LedgerError(f"response digest discontinuity at seq {seq}")
            history.append(record)
            previous = record["record_sha256"]

    def read_records(self) -> list[dict[str, Any]]:
        # A failed fsync can leave a valid-looking record visible. Under the
        # shared lock, reestablish file AND directory durability before any
        # reader is allowed to treat that prefix as an exchange fact. This also
        # handles an empty ledger entry left by failed initial creation.
        with self.mutation():
            try:
                if self.path.exists():
                    with open(self.path, "rb") as handle:
                        os.fsync(handle.fileno())
                    fsync_dir(self.path.parent)
                records = self._read_raw_records()
                self._validate_records(records)
                return records
            except LedgerError:
                raise
            except (OSError, ValueError, TypeError) as exc:
                raise LedgerError(f"ledger integrity validation/durability failed: {exc}") from exc

    def last_record(self) -> dict[str, Any] | None:
        records = self.read_records()
        return records[-1] if records else None

    def last_seq(self) -> int:
        record = self.last_record()
        return int(record["seq"]) if record else 0

    def records_for(self, request_id: str) -> list[dict[str, Any]]:
        return [r for r in self.read_records() if r.get("request_id") == request_id]

    def find_event(self, request_id: str, event: str) -> list[dict[str, Any]]:
        return [
            r
            for r in self.read_records()
            if r.get("request_id") == request_id and r.get("event") == event
        ]

    def latest_event(self, request_id: str, event: str) -> dict[str, Any] | None:
        found = self.find_event(request_id, event)
        return found[-1] if found else None

    def request_ids(self) -> list[str]:
        seen: list[str] = []
        for record in self.read_records():
            value = record.get("request_id")
            if isinstance(value, str) and value not in seen:
                seen.append(value)
        return seen

    # -- writing ---------------------------------------------------------
    def append(
        self,
        event: str,
        *,
        request_id: str,
        request_sha256: str | None = None,
        response_sha256: str | None = None,
        wall_clock: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self.mutation():
            return self._append_locked(event, request_id=request_id,
                request_sha256=request_sha256, response_sha256=response_sha256,
                wall_clock=wall_clock, extra=extra)

    def _append_locked(
        self,
        event: str,
        *,
        request_id: str,
        request_sha256: str | None = None,
        response_sha256: str | None = None,
        wall_clock: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Only invoked while the caller owns the exchange mutation boundary."""
        if not getattr(_HELD, "files", {}).get(self._lock_key):
            raise LedgerError("ledger append requires the exchange mutation lock")
        if event not in LEDGER_EVENTS:
            raise LedgerError(f"unknown ledger event: {event!r}")
        if not isinstance(request_id, str) or not request_id.strip():
            raise LedgerError("request_id must be non-blank")
        if request_sha256 is not None and len(request_sha256) != 64:
            raise LedgerError("request_sha256 must be a sha256 hex digest")
        if response_sha256 is not None and len(response_sha256) != 64:
            raise LedgerError("response_sha256 must be a sha256 hex digest")

        records = self.read_records()
        previous = records[-1] if records else None
        prev_sha256 = previous["record_sha256"] if previous else GENESIS_SHA256
        body: dict[str, Any] = {
            "seq": (int(previous["seq"]) + 1) if previous else 1,
            "event": event,
            "request_id": request_id,
            "request_sha256": request_sha256,
            "response_sha256": response_sha256,
            "wall_clock": wall_clock or utc_now_iso(),
            "prev_sha256": prev_sha256,
        }
        if extra:
            for key, value in sorted(extra.items()):
                if key in body:
                    raise LedgerError(f"extra key collides with ledger field: {key}")
                body[key] = value
        record = dict(body)
        record["record_sha256"] = sha256_hex(canonical_json_bytes(body))

        self._validate_records(records + [record])
        line = canonical_json_bytes(record) + b"\n"
        if not self.path.exists():
            # Creating the ledger is itself a new directory entry. Make the
            # *empty* entry durable before writing any dispatch fact, so a
            # failed initial directory fsync cannot leave an apparently valid
            # first request_published record. An empty visible file left by a
            # failed fsync is re-synced by read_records() on retry.
            try:
                fd = os.open(str(self.path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
                fsync_dir(self.path.parent)
            except OSError as exc:
                raise LedgerError(f"ledger creation durability failed: {exc}") from exc
        try:
            with open(self.path, "ab") as handle:
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise LedgerError(f"ledger append durability failed: {exc}") from exc
        return record

    # -- verification ----------------------------------------------------
    def verify_chain(self) -> dict[str, Any]:
        """Recompute the whole chain and report the first inconsistency."""

        try:
            records = self.read_records()
        except LedgerError as exc:
            match = re.search(r"(?:seq|line) (\d+)", str(exc))
            return {"ok": False, "records": None, "error": str(exc),
                    "first_bad_seq": int(match.group(1)) if match else None}

        return {
            "ok": True, "records": len(records),
            "head_sha256": records[-1]["record_sha256"] if records else GENESIS_SHA256,
            "error": None, "first_bad_seq": None,
        }

    def iter_records(self) -> Iterable[dict[str, Any]]:
        return iter(self.read_records())
