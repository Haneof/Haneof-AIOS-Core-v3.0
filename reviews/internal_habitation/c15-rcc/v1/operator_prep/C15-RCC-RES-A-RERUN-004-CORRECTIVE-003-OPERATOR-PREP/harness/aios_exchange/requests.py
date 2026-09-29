"""Mechanical request publisher.

Writes one durable decision request per model boundary crossing:

* deterministic request identity derived from the ledger sequence and the body
  digest (never from semantics);
* canonical JSON bytes, temp write + fsync + ``os.replace`` + directory fsync;
* an append-only ``request_published`` ledger record carrying the request
  SHA-256 of the exact published bytes.

The ``request_published`` ledger record **is** the semantic dispatch boundary:
after it exists, the exchange may never be reconciled as "not submitted".
"""

from __future__ import annotations

import json
import pathlib
from typing import Any, Mapping

from . import REAL_RESPONSE_MODE
from .atomic import atomic_write_json, read_bytes, sync_existing_bytes
from .canonical import canonical_json_bytes, parse_utc_iso, sha256_hex, utc_now_iso
from .ledger import (
    LEDGER_EVENT_REQUEST_PUBLISHED,
    ExchangeLedger,
    LedgerError,
)
from .schema import REQUEST_VERSION, response_envelope_contract

__all__ = [
    "REQUEST_ID_RULE",
    "RequestPublishError",
    "RequestPublisher",
]

REQUEST_ID_RULE = "req-<sequence:04d>-<kind>-<sha256(canonical_body)[:8]>"


class RequestPublishError(RuntimeError):
    """A request could not be published durably, or is inconsistent."""


class RequestPublisher:
    def __init__(self, exchange_root: str | pathlib.Path, ledger: ExchangeLedger) -> None:
        self.root = pathlib.Path(exchange_root)
        self.requests_dir = self.root / "requests"
        self.requests_dir.mkdir(parents=True, exist_ok=True)
        self.ledger = ledger

    # -- identity --------------------------------------------------------
    def next_sequence(self) -> int:
        published = [
            record
            for record in self.ledger.read_records()
            if record.get("event") == LEDGER_EVENT_REQUEST_PUBLISHED
        ]
        return len(published) + 1

    def request_id_for(self, kind: str, body: Mapping[str, Any], sequence: int) -> str:
        if not isinstance(kind, str) or not kind.strip():
            raise RequestPublishError("kind must be non-blank text")
        digest8 = sha256_hex(canonical_json_bytes(body))[:8]
        return f"req-{int(sequence):04d}-{kind}-{digest8}"

    def path_for(self, request_id: str) -> pathlib.Path:
        return self.requests_dir / f"{request_id}.json"

    # -- publication -----------------------------------------------------
    def _validate_same_request(
        self, raw: bytes, *, request_id: str, kind: str,
        body: Mapping[str, Any], sequence: int | None,
    ) -> None:
        """Validate a visible request byte-for-byte before retry or replay."""
        try:
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict) or raw != canonical_json_bytes(payload) + b"\n":
                raise ValueError("non-canonical request bytes")
            if set(payload) != {"request_version", "request_id", "kind", "sequence",
                                "wall_clock", "response_mode", "body", "response_contract"}:
                raise ValueError("wrong request envelope fields")
            ordinal = payload["sequence"]
            if type(ordinal) is not int or ordinal < 1 or (sequence is not None and ordinal != sequence):
                raise ValueError("stale request sequence")
            if (payload["request_id"] != request_id or payload["kind"] != kind or
                    request_id != self.request_id_for(kind, body, ordinal) or
                    payload["request_version"] != REQUEST_VERSION or
                    payload["response_mode"] != REAL_RESPONSE_MODE or
                    payload["response_contract"] != response_envelope_contract() or
                    canonical_json_bytes(payload["body"]) != canonical_json_bytes(dict(body))):
                raise ValueError("request identity/body/contract mismatch")
            parse_utc_iso(payload["wall_clock"])
        except (KeyError, TypeError, ValueError, UnicodeDecodeError) as exc:
            raise RequestPublishError(f"visible request does not match this transaction: {exc}") from exc

    def publish(
        self,
        *,
        kind: str,
        body: Mapping[str, Any],
        request_id: str | None = None,
    ) -> dict[str, Any]:
        if not isinstance(body, Mapping):
            raise RequestPublishError("request body must be a mapping")
        # The sequence/id decision, any replay/orphan decision, artifact
        # publication AND durable ledger append share one cross-process lock.
        with self.ledger.mutation():
            return self._publish_locked(kind=kind, body=body, request_id=request_id)

    def _publish_locked(
        self, *, kind: str, body: Mapping[str, Any], request_id: str | None,
    ) -> dict[str, Any]:
        if request_id is not None:
            existing = self.ledger.latest_event(request_id, LEDGER_EVENT_REQUEST_PUBLISHED)
            if existing is not None:
                path = self.path_for(request_id)
                # A failed ledger file fsync may have left the record visible.
                # read_records() first re-proves the ledger; this re-proves its
                # artifact before reporting a prior durable dispatch.
                try:
                    on_disk = sync_existing_bytes(path)
                except OSError as exc:
                    raise RequestPublishError(f"cannot prove request replay durability: {exc}") from exc
                if sha256_hex(on_disk) != existing.get("request_sha256"):
                    raise RequestPublishError("published request bytes do not match the durable ledger")
                self._validate_same_request(on_disk, request_id=request_id,
                                            kind=kind, body=body, sequence=None)
                return {
                    "request_id": request_id, "sequence": int(existing["seq"]),
                    "path": str(path), "request_sha256": existing["request_sha256"],
                    "bytes": len(on_disk), "wall_clock": existing["wall_clock"],
                    "kind": kind, "idempotent_replay": True,
                }

        sequence = self.next_sequence()
        expected_id = self.request_id_for(kind, body, sequence)
        if request_id is None:
            request_id = expected_id
        if request_id != expected_id:
            raise RequestPublishError(
                f"request_id does not match the deterministic identity rule: "
                f"{request_id!r} != {expected_id!r}"
            )
        payload = {
            "request_version": REQUEST_VERSION,
            "request_id": request_id,
            "kind": kind,
            "sequence": sequence,
            "wall_clock": utc_now_iso(),
            "response_mode": REAL_RESPONSE_MODE,
            "body": dict(body),
            "response_contract": response_envelope_contract(),
        }
        data = canonical_json_bytes(payload) + b"\n"
        digest = sha256_hex(data)
        path = self.path_for(request_id)
        if path.exists():
            # A prior failed directory fsync may have left the renamed file
            # visible without ANY dispatch record. Do not adopt it as a prior
            # dispatch: verify its full envelope, replace it with this new
            # transaction's bytes, and require a successful directory fsync.
            self._validate_same_request(read_bytes(path), request_id=request_id,
                                        kind=kind, body=body, sequence=sequence)
        atomic_write_json(path, payload)
        record = self.ledger._append_locked(
            LEDGER_EVENT_REQUEST_PUBLISHED,
            request_id=request_id,
            request_sha256=digest,
        )
        return {
            "request_id": request_id, "sequence": int(record["seq"]),
            "path": str(path), "request_sha256": digest, "bytes": len(data),
            "wall_clock": record["wall_clock"], "kind": kind,
            "idempotent_replay": False,
        }

    # -- reading ---------------------------------------------------------
    def payload(self, request_id: str) -> dict[str, Any]:
        path = self.path_for(request_id)
        if not path.exists():
            raise RequestPublishError(f"published request is missing: {path}")
        raw = read_bytes(path)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise RequestPublishError(f"published request is not valid JSON: {exc}") from exc
        record = self.ledger.latest_event(request_id, LEDGER_EVENT_REQUEST_PUBLISHED)
        if record is None:
            raise LedgerError(f"request {request_id} has no durable publication record")
        if record.get("request_sha256") != sha256_hex(raw):
            raise RequestPublishError(
                f"request bytes for {request_id} do not match the ledger digest"
            )
        return payload

    def body(self, request_id: str) -> dict[str, Any]:
        payload = self.payload(request_id)
        body = payload.get("body")
        if not isinstance(body, dict):
            raise RequestPublishError("published request body is not an object")
        return body
