"""Append-only, hash-chained exchange ledger.

Every durable exchange fact is recorded exactly once, in order, and each record
chains to its predecessor:

``record_sha256 = sha256(canonical_json(record_without_record_sha256))``

with ``prev_sha256`` inside the hashed body. Any insertion, deletion, reordering
or edit of a record breaks the chain and is detected.

Recorded events (at minimum):

* ``request_published``  -> sequence, request_id, request_sha256, wall clock
* ``response_published`` -> the above plus response_sha256
* ``response_consumed``  -> the above plus response_sha256
"""

from __future__ import annotations

import json
import os
import pathlib
from typing import Any, Iterable

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


class LedgerError(RuntimeError):
    """The ledger is unreadable, non-monotonic or tamper-evident."""


class ExchangeLedger:
    """Append-only hash-chained JSON-lines ledger."""

    def __init__(self, path: str | pathlib.Path) -> None:
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # -- reading ---------------------------------------------------------
    def read_records(self) -> list[dict[str, Any]]:
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

        line = canonical_json_bytes(record) + b"\n"
        existed = self.path.exists()
        with open(self.path, "ab") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
        if not existed:
            fsync_dir(self.path.parent)
        return record

    # -- verification ----------------------------------------------------
    def verify_chain(self) -> dict[str, Any]:
        """Recompute the whole chain and report the first inconsistency."""

        try:
            records = self.read_records()
        except LedgerError as exc:
            return {"ok": False, "records": None, "error": str(exc), "first_bad_seq": None}

        expected_prev = GENESIS_SHA256
        for index, record in enumerate(records, start=1):
            for required in ("seq", "event", "request_id", "wall_clock", "prev_sha256", "record_sha256"):
                if required not in record:
                    return {
                        "ok": False,
                        "records": len(records),
                        "error": f"record {index} missing field {required}",
                        "first_bad_seq": index,
                    }
            if int(record["seq"]) != index:
                return {
                    "ok": False,
                    "records": len(records),
                    "error": f"non-monotonic sequence at index {index}: {record['seq']}",
                    "first_bad_seq": index,
                }
            if record["event"] not in LEDGER_EVENTS:
                return {
                    "ok": False,
                    "records": len(records),
                    "error": f"unknown event at seq {record['seq']}: {record['event']}",
                    "first_bad_seq": index,
                }
            if record["prev_sha256"] != expected_prev:
                return {
                    "ok": False,
                    "records": len(records),
                    "error": f"broken hash chain at seq {record['seq']}",
                    "first_bad_seq": index,
                }
            body = {k: v for k, v in record.items() if k != "record_sha256"}
            recomputed = sha256_hex(canonical_json_bytes(body))
            if recomputed != record["record_sha256"]:
                return {
                    "ok": False,
                    "records": len(records),
                    "error": f"record digest mismatch at seq {record['seq']}",
                    "first_bad_seq": index,
                }
            expected_prev = record["record_sha256"]
        return {
            "ok": True,
            "records": len(records),
            "head_sha256": expected_prev,
            "error": None,
            "first_bad_seq": None,
        }

    def iter_records(self) -> Iterable[dict[str, Any]]:
        return iter(self.read_records())
