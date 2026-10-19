"""Canonical encodings and digests.

Deterministic byte encodings so that a request or response digest always
describes exactly the bytes that are durable. No cognition, no policy.
"""

from __future__ import annotations

import base64
import dataclasses
import datetime as _dt
import enum
import hashlib
import json
import pathlib
from typing import Any

__all__ = [
    "canonical_json_bytes",
    "json_default",
    "sha256_hex",
    "sha256_file",
    "utc_now_iso",
    "parse_utc_iso",
]


def json_default(value: Any) -> Any:
    """Deterministic fallback for values that are not natively JSON.

    Only mechanical type projection happens here: enums to their value,
    dataclasses to their declared fields, bytes to base64, sets/tuples to
    sorted/ordered lists, path-like and datetime objects to text.
    """

    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, (bytes, bytearray, memoryview)):
        return base64.b64encode(bytes(value)).decode("ascii")
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: getattr(value, f.name) for f in dataclasses.fields(value)}
    if isinstance(value, _dt.datetime):
        moment = value if value.tzinfo is not None else value.replace(tzinfo=_dt.timezone.utc)
        return moment.astimezone(_dt.timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, _dt.date):
        return value.isoformat()
    if isinstance(value, (set, frozenset)):
        return sorted(value, key=repr)
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, pathlib.PurePath):
        return str(value)
    if hasattr(value, "model_dump") and callable(value.model_dump):
        return value.model_dump(mode="json")
    if hasattr(value, "items") and callable(value.items):
        return {str(k): v for k, v in value.items()}
    return str(value)


def canonical_json_bytes(payload: Any) -> bytes:
    """UTF-8 canonical JSON: sorted keys, compact separators, no NaN/Infinity."""

    text = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=json_default,
    )
    return text.encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | pathlib.Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1 << 20)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def utc_now_iso() -> str:
    return (
        _dt.datetime.now(_dt.timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def parse_utc_iso(text: str) -> _dt.datetime:
    """Parse an ISO-8601 UTC timestamp produced by :func:`utc_now_iso`."""

    raw = text[:-1] + "+00:00" if text.endswith("Z") else text
    moment = _dt.datetime.fromisoformat(raw)
    if moment.tzinfo is None:
        raise ValueError("timestamp is not timezone-aware")
    return moment.astimezone(_dt.timezone.utc)
