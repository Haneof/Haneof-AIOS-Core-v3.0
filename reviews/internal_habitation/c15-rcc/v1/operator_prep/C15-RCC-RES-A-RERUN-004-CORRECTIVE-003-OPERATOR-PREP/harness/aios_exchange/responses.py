"""Mechanical response publisher.

The Resident (or any external session) decides *everything* semantic. This
module only transports the exact bytes it is given:

1. verify a durable ``request_published`` record exists for the request id;
2. verify the response envelope echoes the request id and the request SHA-256;
3. validate the envelope/directive shape against the frozen Core contract;
4. write the exact bytes through temp write + fsync + ``os.replace`` + dir fsync;
5. append the ``response_published`` ledger record with the response SHA-256.

It never generates, repairs, defaults, infers or rewrites response content.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any, Mapping

from .atomic import atomic_write_bytes, read_bytes
from .canonical import sha256_hex
from .ledger import (
    LEDGER_EVENT_REQUEST_PUBLISHED,
    LEDGER_EVENT_RESPONSE_PUBLISHED,
    ExchangeLedger,
    LedgerError,
)
from .schema import SchemaContractError, parse_response_envelope

__all__ = [
    "ResponsePublishError",
    "ResponsePublisher",
]


class ResponsePublishError(RuntimeError):
    """A response could not be published durably, or violates the contract."""


class ResponsePublisher:
    def __init__(self, exchange_root: str | pathlib.Path, ledger: ExchangeLedger) -> None:
        self.root = pathlib.Path(exchange_root)
        self.responses_dir = self.root / "responses"
        self.responses_dir.mkdir(parents=True, exist_ok=True)
        self.ledger = ledger

    def path_for(self, request_id: str) -> pathlib.Path:
        return self.responses_dir / f"{request_id}.json"

    def _request_record(self, request_id: str) -> dict[str, Any]:
        record = self.ledger.latest_event(request_id, LEDGER_EVENT_REQUEST_PUBLISHED)
        if record is None:
            raise ResponsePublishError(
                f"refusing to publish a response for {request_id!r}: "
                "no durable request_published record exists"
            )
        return record

    def publish_bytes(
        self,
        *,
        request_id: str,
        response_bytes: bytes,
        adopt_existing: bool = True,
    ) -> dict[str, Any]:
        if not isinstance(request_id, str) or not request_id.strip():
            raise ResponsePublishError("request_id must be non-blank text")
        if not isinstance(response_bytes, (bytes, bytearray, memoryview)):
            raise ResponsePublishError("response_bytes must be bytes")

        data = bytes(response_bytes)
        request_record = self._request_record(request_id)

        try:
            decoded = json.loads(data.decode("utf-8"))
        except Exception as exc:
            raise ResponsePublishError(f"response bytes are not valid UTF-8 JSON: {exc}") from exc
        try:
            envelope = parse_response_envelope(decoded)
        except SchemaContractError as exc:
            raise ResponsePublishError(f"response envelope is invalid: {exc}") from exc

        if envelope["request_id"] != request_id:
            raise ResponsePublishError(
                "response envelope request_id does not match the published request"
            )
        if envelope["request_sha256"] != request_record.get("request_sha256"):
            raise ResponsePublishError(
                "response envelope request_sha256 does not match the durable request digest"
            )

        digest = sha256_hex(data)
        path = self.path_for(request_id)
        existing = self.ledger.latest_event(request_id, LEDGER_EVENT_RESPONSE_PUBLISHED)
        if existing is not None:
            durable_digest = existing.get("response_sha256")
            if existing.get("request_sha256") != request_record.get("request_sha256"):
                raise ResponsePublishError(
                    "durable response record is not bound to the current request digest (fail closed)"
                )
            if not isinstance(durable_digest, str) or len(durable_digest) != 64:
                raise ResponsePublishError(
                    "durable response record has no valid response digest (fail closed)"
                )
            if digest != durable_digest:
                raise ResponsePublishError(
                    "response already durably published with a different digest; "
                    "refusing to overwrite (fail closed)"
                )
            if not path.is_file():
                raise ResponsePublishError(
                    f"published response is missing from disk: {path} (fail closed)"
                )
            try:
                on_disk = read_bytes(path)
            except OSError as exc:
                raise ResponsePublishError(
                    f"cannot read durable published response {path}: {exc} (fail closed)"
                ) from exc
            on_disk_digest = sha256_hex(on_disk)
            if on_disk_digest != durable_digest:
                raise ResponsePublishError(
                    "published response on disk does not match the durable ledger digest; "
                    "refusing to repair or overwrite (fail closed)"
                )
            if digest != durable_digest:
                raise ResponsePublishError(
                    "replay input does not match the durable ledger response digest (fail closed)"
                )
            return {
                "request_id": request_id,
                "path": str(path),
                "response_sha256": digest,
                "bytes": len(data),
                "wall_clock": existing["wall_clock"],
                "idempotent_replay": True,
                "adopted_existing_bytes": False,
            }

        adopted = False
        if path.exists():
            on_disk = read_bytes(path)
            if not adopt_existing:
                raise ResponsePublishError(
                    "response file already exists without a ledger record; "
                    "adoption disabled (fail closed)"
                )
            if sha256_hex(on_disk) != digest:
                raise ResponsePublishError(
                    "response file exists with different bytes and has no ledger record"
                )
            adopted = True
        else:
            atomic_write_bytes(path, data)

        record = self.ledger.append(
            LEDGER_EVENT_RESPONSE_PUBLISHED,
            request_id=request_id,
            request_sha256=request_record.get("request_sha256"),
            response_sha256=digest,
        )

        if sha256_hex(read_bytes(path)) != digest:
            raise ResponsePublishError("durable response bytes do not match the submitted digest")

        return {
            "request_id": request_id,
            "path": str(path),
            "response_sha256": digest,
            "bytes": len(data),
            "wall_clock": record["wall_clock"],
            "idempotent_replay": False,
            "adopted_existing_bytes": adopted,
        }

    def publish_object(
        self,
        *,
        request_id: str,
        response: Mapping[str, Any],
        adopt_existing: bool = True,
    ) -> dict[str, Any]:
        """Canonical-encode a JSON object and publish it byte-exactly."""

        from .canonical import canonical_json_bytes

        if not isinstance(response, Mapping):
            raise ResponsePublishError("response must be a mapping")
        return self.publish_bytes(
            request_id=request_id,
            response_bytes=canonical_json_bytes(dict(response)) + b"\n",
            adopt_existing=adopt_existing,
        )

    def published_bytes(self, request_id: str) -> bytes:
        """Read published response bytes after verifying the ledger binding."""

        record = self.ledger.latest_event(request_id, LEDGER_EVENT_RESPONSE_PUBLISHED)
        if record is None:
            raise LedgerError(
                f"no durable response_published record for {request_id!r} (fail closed)"
            )
        path = self.path_for(request_id)
        if not path.exists():
            raise ResponsePublishError(f"published response is missing from disk: {path}")
        data = read_bytes(path)
        if sha256_hex(data) != record.get("response_sha256"):
            raise ResponsePublishError(
                f"published response bytes for {request_id!r} do not match the ledger digest"
            )
        return data
