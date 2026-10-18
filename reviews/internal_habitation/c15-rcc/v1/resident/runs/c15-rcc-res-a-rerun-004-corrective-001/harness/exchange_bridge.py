"""Run-local deterministic Resident Exchange Bridge.

Enforces mechanical evidence boundaries for Resident AI decision requests and responses:
1. Append-only, hash-chained, fsynced exchange ledger.
2. Atomic request and response publication.
3. Durable ordering: request_published -> response_published -> response_consumed -> Core effect.
4. Fail-closed on missing, torn, mismatched or unproven artifacts.
5. Strict semantic dispatch boundary: once request is published, not_submitted is forbidden.

No C15 fixture content or semantic rules are contained in this bridge.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping
import uuid


class ExchangeError(Exception):
    """Base exception for exchange bridge failures."""


class ExchangeBlockedError(ExchangeError):
    """Binding exchange failure requiring the run to stop / fail closed."""


class LedgerIntegrityError(ExchangeBlockedError):
    """Ledger sequence break, hash-chain mismatch, or record corruption."""


class RequestIdMismatchError(ExchangeBlockedError):
    """Response request_id does not echo the request_id."""


class UnpublishedRequestError(ExchangeBlockedError):
    """Cannot publish response for a request that was not durably published."""


def utc_iso_now() -> str:
    """Return ISO-8601 wall-clock timestamp with UTC timezone."""
    return datetime.now(timezone.utc).isoformat()


def fsync_dir(dir_path: Path | str) -> None:
    """Fsync containing directory to ensure directory entry durability."""
    p = Path(dir_path)
    try:
        fd = os.open(str(p), os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass


def atomic_write_bytes(target_path: Path, data: bytes) -> str:
    """Atomically write bytes to target_path using temp file + replace + fsync.

    Returns SHA-256 hex digest of data.
    """
    target_path = Path(target_path).resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(data).hexdigest()

    temp_path = target_path.with_name(f"{target_path.name}.tmp.{uuid.uuid4().hex}")
    with open(temp_path, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())

    os.replace(temp_path, target_path)
    fsync_dir(target_path.parent)
    return digest


@dataclass(frozen=True)
class LedgerRecord:
    sequence: int
    event: str
    request_id: str
    request_sha256: str
    response_sha256: str | None
    wall_clock_iso: str
    prev_record_hash: str
    record_hash: str
    metadata: dict[str, Any]

    def canonical_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "metadata": self.metadata,
            "prev_record_hash": self.prev_record_hash,
            "request_id": self.request_id,
            "request_sha256": self.request_sha256,
            "response_sha256": self.response_sha256,
            "sequence": self.sequence,
            "wall_clock_iso": self.wall_clock_iso,
        }

    def compute_hash(self) -> str:
        raw = json.dumps(
            self.canonical_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


class ExchangeLedger:
    """Append-only, hash-chained, fsynced ledger recording exchange chronology."""

    INITIAL_PREV_HASH = "0" * 64

    def __init__(self, ledger_path: Path | str) -> None:
        self.ledger_path = Path(ledger_path).resolve()
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)

    def _read_all_records_raw(self) -> list[LedgerRecord]:
        if not self.ledger_path.exists():
            return []
        records: list[LedgerRecord] = []
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except Exception as exc:
                    raise LedgerIntegrityError(
                        f"Malformed JSON at ledger line {line_no}: {exc}"
                    ) from exc
                records.append(
                    LedgerRecord(
                        sequence=data["sequence"],
                        event=data["event"],
                        request_id=data["request_id"],
                        request_sha256=data["request_sha256"],
                        response_sha256=data.get("response_sha256"),
                        wall_clock_iso=data["wall_clock_iso"],
                        prev_record_hash=data["prev_record_hash"],
                        record_hash=data["record_hash"],
                        metadata=data.get("metadata") or {},
                    )
                )
        return records

    def verify(self) -> list[LedgerRecord]:
        """Verify sequence monotonicity, hash chaining, and record integrity."""
        records = self._read_all_records_raw()
        prev_hash = self.INITIAL_PREV_HASH
        for idx, rec in enumerate(records):
            expected_seq = idx + 1
            if rec.sequence != expected_seq:
                raise LedgerIntegrityError(
                    f"Ledger sequence broke at index {idx}: expected {expected_seq}, got {rec.sequence}"
                )
            if rec.prev_record_hash != prev_hash:
                raise LedgerIntegrityError(
                    f"Ledger hash chain broken at sequence {rec.sequence}: expected prev {prev_hash}, got {rec.prev_record_hash}"
                )
            computed_hash = rec.compute_hash()
            if rec.record_hash != computed_hash:
                raise LedgerIntegrityError(
                    f"Ledger record hash mismatch at sequence {rec.sequence}: expected {computed_hash}, got {rec.record_hash}"
                )
            prev_hash = rec.record_hash
        return records

    def get_last_record(self) -> LedgerRecord | None:
        records = self.verify()
        return records[-1] if records else None

    def append(
        self,
        *,
        event: str,
        request_id: str,
        request_sha256: str,
        response_sha256: str | None = None,
        wall_clock_iso: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> LedgerRecord:
        records = self.verify()
        last_rec = records[-1] if records else None
        sequence = (last_rec.sequence + 1) if last_rec else 1
        prev_hash = last_rec.record_hash if last_rec else self.INITIAL_PREV_HASH
        ts = wall_clock_iso or utc_iso_now()
        meta = dict(metadata or {})

        canonical_data = {
            "event": event,
            "metadata": meta,
            "prev_record_hash": prev_hash,
            "request_id": request_id,
            "request_sha256": request_sha256,
            "response_sha256": response_sha256,
            "sequence": sequence,
            "wall_clock_iso": ts,
        }
        raw = json.dumps(
            canonical_data,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        record_hash = hashlib.sha256(raw).hexdigest()

        record = LedgerRecord(
            sequence=sequence,
            event=event,
            request_id=request_id,
            request_sha256=request_sha256,
            response_sha256=response_sha256,
            wall_clock_iso=ts,
            prev_record_hash=prev_hash,
            record_hash=record_hash,
            metadata=meta,
        )

        full_data = asdict(record)
        line_bytes = json.dumps(
            full_data,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8") + b"\n"

        fd = os.open(
            str(self.ledger_path),
            os.O_WRONLY | os.O_CREAT | os.O_APPEND,
            0o644,
        )
        try:
            os.write(fd, line_bytes)
            os.fsync(fd)
        finally:
            os.close(fd)

        fsync_dir(self.ledger_path.parent)
        return record

    def find_records_for_request(self, request_id: str) -> list[LedgerRecord]:
        records = self.verify()
        return [r for r in records if r.request_id == request_id]

    def has_event(self, request_id: str, event: str) -> bool:
        records = self.find_records_for_request(request_id)
        return any(r.event == event for r in records)


class ExchangeBridge:
    """Run-local deterministic Resident Exchange Bridge."""

    def __init__(
        self,
        *,
        requests_dir: Path | str,
        responses_dir: Path | str,
        ledger: ExchangeLedger,
    ) -> None:
        self.requests_dir = Path(requests_dir).resolve()
        self.responses_dir = Path(responses_dir).resolve()
        self.ledger = ledger

        self.requests_dir.mkdir(parents=True, exist_ok=True)
        self.responses_dir.mkdir(parents=True, exist_ok=True)

    def request_file(self, request_id: str) -> Path:
        return self.requests_dir / f"{request_id}.json"

    def response_file(self, request_id: str) -> Path:
        return self.responses_dir / f"{request_id}.json"

    def publish_request(
        self,
        request_id: str,
        request_data: Mapping[str, Any],
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> tuple[Path, str, LedgerRecord]:
        """Publish request bytes atomically, then write request_published to ledger."""
        data_copy = dict(request_data)
        data_copy["request_id"] = request_id
        content_bytes = json.dumps(
            data_copy,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        ).encode("utf-8")
        req_sha = hashlib.sha256(content_bytes).hexdigest()

        target_file = self.request_file(request_id)
        atomic_write_bytes(target_file, content_bytes)

        record = self.ledger.append(
            event="request_published",
            request_id=request_id,
            request_sha256=req_sha,
            response_sha256=None,
            metadata=dict(metadata or {}),
        )
        return target_file, req_sha, record

    def publish_response(
        self,
        request_id: str,
        request_sha256: str,
        response_data: Mapping[str, Any],
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> tuple[Path, str, LedgerRecord]:
        """Resident publishes response bytes atomically, then writes response_published."""
        records = self.ledger.find_records_for_request(request_id)
        req_pub = next((r for r in records if r.event == "request_published"), None)
        if req_pub is None:
            raise UnpublishedRequestError(
                f"Cannot publish response: request {request_id} was never published to ledger"
            )
        if req_pub.request_sha256 != request_sha256:
            raise ExchangeBlockedError(
                f"Request SHA-256 mismatch for {request_id}: expected {req_pub.request_sha256}, got {request_sha256}"
            )

        resp_req_id = response_data.get("request_id")
        if resp_req_id != request_id:
            raise RequestIdMismatchError(
                f"Response request_id mismatch: expected '{request_id}', got '{resp_req_id}'"
            )

        content_bytes = json.dumps(
            dict(response_data),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        ).encode("utf-8")
        resp_sha = hashlib.sha256(content_bytes).hexdigest()

        target_file = self.response_file(request_id)
        atomic_write_bytes(target_file, content_bytes)

        record = self.ledger.append(
            event="response_published",
            request_id=request_id,
            request_sha256=request_sha256,
            response_sha256=resp_sha,
            metadata=dict(metadata or {}),
        )
        return target_file, resp_sha, record

    def consume_response(
        self,
        request_id: str,
        expected_request_sha256: str,
    ) -> tuple[dict[str, Any], LedgerRecord]:
        """Runner verifies durable response publication, reads response, and writes response_consumed."""
        records = self.ledger.find_records_for_request(request_id)
        req_pub = next((r for r in records if r.event == "request_published"), None)
        if req_pub is None:
            raise ExchangeBlockedError(
                f"Consume failed: request {request_id} has no request_published in ledger"
            )
        if req_pub.request_sha256 != expected_request_sha256:
            raise ExchangeBlockedError(
                f"Consume failed: request SHA mismatch for {request_id}"
            )

        resp_pub = next((r for r in records if r.event == "response_published"), None)
        if resp_pub is None:
            raise ExchangeBlockedError(
                f"Consume failed: request {request_id} has no response_published in ledger"
            )
        if resp_pub.request_sha256 != expected_request_sha256:
            raise ExchangeBlockedError(
                f"Consume failed: response_published bound to different request SHA"
            )
        if resp_pub.response_sha256 is None:
            raise ExchangeBlockedError(
                f"Consume failed: response_published has null response_sha256"
            )

        target_file = self.response_file(request_id)
        if not target_file.exists():
            raise ExchangeBlockedError(
                f"Consume failed: response file {target_file} does not exist"
            )

        with open(target_file, "rb") as f:
            resp_bytes = f.read()

        actual_resp_sha = hashlib.sha256(resp_bytes).hexdigest()
        if actual_resp_sha != resp_pub.response_sha256:
            raise ExchangeBlockedError(
                f"Consume failed: response file SHA {actual_resp_sha} != ledger response SHA {resp_pub.response_sha256}"
            )

        try:
            resp_dict = json.loads(resp_bytes.decode("utf-8"))
        except Exception as exc:
            raise ExchangeBlockedError(
                f"Consume failed: response file is not valid JSON: {exc}"
            ) from exc

        if resp_dict.get("request_id") != request_id:
            raise RequestIdMismatchError(
                f"Consume failed: response JSON request_id {resp_dict.get('request_id')} != {request_id}"
            )

        # Record response_consumed if not already recorded
        consumed_rec = next((r for r in records if r.event == "response_consumed"), None)
        if consumed_rec is None:
            consumed_rec = self.ledger.append(
                event="response_consumed",
                request_id=request_id,
                request_sha256=expected_request_sha256,
                response_sha256=actual_resp_sha,
            )

        return resp_dict, consumed_rec

    def can_reconcile_not_submitted(self, request_id: str) -> bool:
        """Binding blocker IA-A004-01 check:

        Once a request is durably published to the exchange boundary, it is considered
        semantically dispatched. It may NOT be reconciled as not_submitted.
        not_submitted is permitted ONLY if failure is durably proven to have occurred
        BEFORE request publication.
        """
        records = self.ledger.find_records_for_request(request_id)
        has_req_pub = any(r.event == "request_published" for r in records)
        return not has_req_pub

    def can_recover_published_response(
        self,
        request_id: str,
        expected_request_sha256: str,
    ) -> bool:
        """Binding blocker IA-A004-02 check:

        Check if durable contemporaneous evidence exists to legally recover an already-published response.
        """
        records = self.ledger.find_records_for_request(request_id)
        req_pub = next((r for r in records if r.event == "request_published"), None)
        if req_pub is None or req_pub.request_sha256 != expected_request_sha256:
            return False
        resp_pub = next((r for r in records if r.event == "response_published"), None)
        if resp_pub is None or resp_pub.request_sha256 != expected_request_sha256:
            return False
        if not resp_pub.response_sha256:
            return False
        target_file = self.response_file(request_id)
        if not target_file.exists():
            return False
        with open(target_file, "rb") as f:
            data = f.read()
        return hashlib.sha256(data).hexdigest() == resp_pub.response_sha256
