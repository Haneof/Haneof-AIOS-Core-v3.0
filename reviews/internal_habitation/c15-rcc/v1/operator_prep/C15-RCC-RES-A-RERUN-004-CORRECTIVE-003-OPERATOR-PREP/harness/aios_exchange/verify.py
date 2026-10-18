"""Verification utilities.

Mechanical only: exchange integrity, frozen-Core identity, environment triple,
and the frozen ``CapabilityResult`` surface. No cognition, no policy.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any, Mapping

from .atomic import read_bytes
from .canonical import canonical_json_bytes, sha256_hex
from .ledger import (
    LEDGER_EVENT_REQUEST_PUBLISHED,
    LEDGER_EVENT_RESPONSE_CONSUMED,
    LEDGER_EVENT_RESPONSE_PUBLISHED,
    ExchangeLedger,
)
from .schema import (
    CAPABILITY_RESULT_EXPECTED_FIELDS,
    CAPABILITY_RESULT_FORBIDDEN_FIELDS,
    SchemaContractError,
    assert_capability_result_contract,
    capability_result_field_names,
)

__all__ = [
    "verify_exchange_integrity",
    "core_content_manifest",
    "verify_core_content_manifest",
    "verify_environment",
    "capability_result_surface_report",
]


def verify_exchange_integrity(exchange_root: str | pathlib.Path) -> dict[str, Any]:
    """Verify ledger chain, durable chronology, digests and orphan files."""

    root = pathlib.Path(exchange_root)
    ledger = ExchangeLedger(root / "ledger.jsonl")
    chain = ledger.verify_chain()
    problems: list[str] = []
    requests_dir = root / "requests"
    responses_dir = root / "responses"

    if not chain["ok"]:
        problems.append(f"ledger chain invalid: {chain.get('error')}")

    try:
        records = ledger.read_records()
    except Exception as exc:
        return {
            "ok": False,
            "problems": problems + [f"ledger unreadable: {exc}"],
            "chain": chain,
        }

    per_request: dict[str, dict[str, Any]] = {}
    for record in records:
        request_id = record.get("request_id")
        if not isinstance(request_id, str):
            problems.append(f"ledger record {record.get('seq')} has no request_id")
            continue
        entry = per_request.setdefault(
            request_id,
            {"first_seq": record.get("seq"), "events": [], "request_sha256": None, "response_sha256": None},
        )
        entry["events"].append(record.get("event"))
        if record.get("event") == LEDGER_EVENT_REQUEST_PUBLISHED:
            entry["request_sha256"] = record.get("request_sha256")
        if record.get("event") in (LEDGER_EVENT_RESPONSE_PUBLISHED, LEDGER_EVENT_RESPONSE_CONSUMED):
            entry["response_sha256"] = record.get("response_sha256")

    for request_id, entry in per_request.items():
        events = entry["events"]
        if events.count(LEDGER_EVENT_REQUEST_PUBLISHED) != 1:
            problems.append(f"{request_id}: request_published recorded {events.count(LEDGER_EVENT_REQUEST_PUBLISHED)} times")
        if events.count(LEDGER_EVENT_RESPONSE_PUBLISHED) > 1:
            problems.append(f"{request_id}: response_published recorded more than once")
        if events.count(LEDGER_EVENT_RESPONSE_CONSUMED) > 1:
            problems.append(f"{request_id}: response_consumed recorded more than once")
        if LEDGER_EVENT_RESPONSE_PUBLISHED in events and events.index(LEDGER_EVENT_RESPONSE_PUBLISHED) < events.index(LEDGER_EVENT_REQUEST_PUBLISHED):
            problems.append(f"{request_id}: response published before request")
        if LEDGER_EVENT_RESPONSE_CONSUMED in events and LEDGER_EVENT_RESPONSE_PUBLISHED not in events:
            problems.append(f"{request_id}: response consumed before publication")

        request_path = requests_dir / f"{request_id}.json"
        if entry["request_sha256"] is None:
            problems.append(f"{request_id}: no request digest recorded")
        elif not request_path.exists():
            problems.append(f"{request_id}: request file missing")
        elif sha256_hex(read_bytes(request_path)) != entry["request_sha256"]:
            problems.append(f"{request_id}: request file digest mismatch")

        response_path = responses_dir / f"{request_id}.json"
        if LEDGER_EVENT_RESPONSE_PUBLISHED not in events:
            if response_path.exists():
                problems.append(
                    f"{request_id}: response file exists without a durable response_published record"
                )
        elif not response_path.exists():
            problems.append(f"{request_id}: published response file missing")
        elif entry["response_sha256"] is not None and sha256_hex(read_bytes(response_path)) != entry["response_sha256"]:
            problems.append(f"{request_id}: response file digest mismatch")

    ledger_ids = set(per_request)
    for path in sorted(requests_dir.glob("req-*.json")) if requests_dir.exists() else []:
        if path.stem not in ledger_ids:
            problems.append(f"orphan request file without ledger record: {path.name}")
    for path in sorted(responses_dir.glob("req-*.json")) if responses_dir.exists() else []:
        if path.stem not in ledger_ids:
            problems.append(f"orphan response file without ledger record: {path.name}")

    return {
        "ok": not problems,
        "problems": problems,
        "chain": chain,
        "requests": per_request,
        "exchange_root": str(root),
    }


def core_content_manifest(core_root: str | pathlib.Path) -> dict[str, Any]:
    """Deterministic content manifest (path -> sha256) of a Core source tree."""

    root = pathlib.Path(core_root)
    if not root.is_dir():
        raise FileNotFoundError(f"core root not found: {root}")
    files: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts:
            continue
        relative = path.relative_to(root).as_posix()
        files.append(
            {
                "path": relative,
                "sha256": sha256_hex(read_bytes(path)),
                "size": path.stat().st_size,
            }
        )
    combined = sha256_hex(canonical_json_bytes(files))
    return {"core_root": str(root), "file_count": len(files), "files": files, "manifest_sha256": combined}


def verify_core_content_manifest(
    core_root: str | pathlib.Path, expected_manifest_sha256: str
) -> dict[str, Any]:
    manifest = core_content_manifest(core_root)
    return {
        "ok": manifest["manifest_sha256"] == expected_manifest_sha256,
        "observed_manifest_sha256": manifest["manifest_sha256"],
        "expected_manifest_sha256": expected_manifest_sha256,
        "file_count": manifest["file_count"],
    }


def verify_environment(
    *,
    expected_python: str,
    expected_pydantic: str,
    expected_pytest: str | None = None,
    expected_sqlite: str | None = None,
) -> dict[str, Any]:
    """Verify the interpreter actually executing this code."""

    import platform
    import sqlite3
    import sys

    observed = {
        "python_version": platform.python_version(),
        "python_version_info": list(sys.version_info[:3]),
        "executable": sys.executable,
        "sqlite_version": sqlite3.sqlite_version,
    }
    try:
        import pydantic

        observed["pydantic_version"] = pydantic.VERSION
    except Exception as exc:  # pragma: no cover - diagnostic
        observed["pydantic_version"] = f"MISSING:{exc}"
    try:
        import pytest

        observed["pytest_version"] = pytest.__version__
    except Exception as exc:  # pragma: no cover - diagnostic
        observed["pytest_version"] = f"MISSING:{exc}"

    checks = {
        "python": observed["python_version"] == expected_python,
        "pydantic": observed["pydantic_version"] == expected_pydantic,
    }
    if expected_pytest is not None:
        checks["pytest"] = observed["pytest_version"] == expected_pytest
    if expected_sqlite is not None:
        checks["sqlite"] = observed["sqlite_version"] == expected_sqlite
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "observed": observed,
        "expected": {
            "python": expected_python,
            "pydantic": expected_pydantic,
            "pytest": expected_pytest,
            "sqlite": expected_sqlite,
        },
    }


def capability_result_surface_report() -> dict[str, Any]:
    """Evidence that the frozen result surface is exactly the six legal fields."""

    contract = assert_capability_result_contract()
    return {
        "legal_fields": list(capability_result_field_names()),
        "expected_fields": list(CAPABILITY_RESULT_EXPECTED_FIELDS),
        "forbidden_fields_absent": list(CAPABILITY_RESULT_FORBIDDEN_FIELDS),
        "contract": contract,
    }
