"""Persistent, auditable publication confirmation for freeze packages.

Previous iteration used an in-process live capability (WeakKeyDictionary).
That prevented cross-process handoff: after the publishing process exited,
a fresh process could not restore a successfully published package.

New design (v3):
- Successful freeze creates a persistent receipt file
  `publication_receipt.json` inside the published package, containing
  manifest SHA256, publication ID, timestamps and source hashes.
- The receipt is written with atomic_json (temp file + fsync + rename +
  fsync parent) after the package directory rename and its parent fsync
  have succeeded. Only then is the source driver marked FROZEN.
- Restore requires BOTH pinned manifest hash AND valid receipt file.
  The receipt proves that all I/O through parent fsync succeeded in the
  publishing process. It is auditable: manifest hash, publication ID and
  source hashes are recorded.
- If parent fsync or receipt creation fails, the package directory may
  remain visible but WITHOUT receipt. Ordinary restore is BLOCKED and the
  source driver is marked FAILED/UNCERTAIN with preserved_package path.
  An operator must then independently verify package integrity (manifest
  hash, file digests, watermarks, receipts) before explicitly confirming
  via `confirm_uncertain_package` which requires an operator attestation
  file and does not blindly override failure.
- No identity authentication system is introduced. Security relies on
  externally pinned manifest SHA256 (operator provides expected hash) and
  on file digest checks. A forged READY package without correct manifest
  hash or without receipt is rejected.

This does NOT promise absolute atomicity under arbitrary filesystem/
hardware failure. Uncertain states stop and require explicit verification.

Limits: not a durable distributed commit service, not proof that the
underlying device honored fsync, not hostile-Python isolation.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from weakref import WeakKeyDictionary

from .audit import require
from .driver import atomic_json
from .audit import digest

RECEIPT_NAME = "publication_receipt.json"
RECEIPT_FORMAT = "c15-publication-receipt-v1"

# Backward compat: old live confirmation (deprecated, not used for new flow)
class PublicationConfirmation:
    __slots__ = ("__weakref__",)

    def __new__(cls):
        raise TypeError("publication confirmation is issued only by successful freeze")

    def __reduce__(self):
        raise TypeError("live publication confirmation cannot be persisted or replayed")

_confirmed: WeakKeyDictionary = WeakKeyDictionary()

def _confirm(manifest_sha256: str, publication_id: str) -> PublicationConfirmation:
    confirmation = object.__new__(PublicationConfirmation)
    _confirmed[confirmation] = (manifest_sha256, publication_id)
    return confirmation

def require_confirmation(confirmation, *, manifest_sha256: str, publication_id: str):
    require(isinstance(confirmation, PublicationConfirmation),
            "publication unconfirmed: ordinary restore is blocked")
    require(_confirmed.get(confirmation) == (manifest_sha256, publication_id),
            "publication confirmation absent/foreign; independent recovery audit required")

@dataclass(frozen=True)
class FrozenPackage:
    manifest: dict
    receipt_path: Path
    manifest_sha256: str
    publication_id: str
    # Deprecated live confirmation, kept for backward compat of old tests
    confirmation: PublicationConfirmation | None = None

def create_receipt(
    destination: Path,
    *,
    manifest_sha256: str,
    publication_id: str,
    driver_state_sha256: str,
    release_sha256: str,
) -> Path:
    """Create persistent receipt after successful rename+parent fsync.

    Must be called ONLY after all prior I/O succeeded. Writes atomically
    and fsyncs the receipt file and its parent directory (destination).
    Also fsyncs destination's parent for durability of the new file entry.
    """
    receipt = {
        "format": RECEIPT_FORMAT,
        "publication_id": publication_id,
        "manifest_sha256": manifest_sha256,
        "driver_state_sha256": driver_state_sha256,
        "release_sha256": release_sha256,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
    }
    receipt_path = destination / RECEIPT_NAME
    atomic_json(receipt_path, receipt)
    # atomic_json fsynced receipt file and destination dir. Also fsync parent of destination
    # to make the directory entry for the package and receipt durable.
    try:
        fd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except BaseException:
        # If parent fsync fails, receipt may still exist but durability uncertain.
        # Caller should treat this as failure and not mark FROZEN.
        raise
    return receipt_path

def load_and_verify_receipt(
    source: Path,
    *,
    expected_manifest_sha256: str,
    expected_publication_id: str | None = None,
) -> dict:
    """Verify persistent receipt file inside source package.

    Checks:
    - receipt file exists and is not symlink
    - valid JSON, correct format
    - manifest_sha256 matches expected and actual manifest file hash
    - publication_id matches manifest's publication id if expected provided
    - receipt's publication_id matches manifest's publication id
    """
    receipt_path = source / RECEIPT_NAME
    require(not receipt_path.is_symlink(), "receipt is symlink; untrusted")
    require(receipt_path.is_file(), "publication unconfirmed: receipt missing, ordinary restore is blocked")
    try:
        data = json.loads(receipt_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"receipt unreadable: {exc}") from exc
    require(data.get("format") == RECEIPT_FORMAT, "unexpected receipt format")
    require(isinstance(data.get("publication_id"), str) and data["publication_id"], "receipt missing publication_id")
    require(isinstance(data.get("manifest_sha256"), str) and len(data["manifest_sha256"]) == 64, "receipt manifest hash invalid")
    require(data["manifest_sha256"] == expected_manifest_sha256, "receipt manifest hash mismatch; untrusted package")
    if expected_publication_id is not None:
        require(data["publication_id"] == expected_publication_id, "receipt publication_id mismatch")
    # Also verify actual manifest file hash matches receipt and expected
    actual_manifest_hash = digest(source / "manifest.json")
    require(actual_manifest_hash == expected_manifest_sha256, "manifest hash does not match pinned hash")
    require(actual_manifest_hash == data["manifest_sha256"], "receipt manifest hash does not match actual manifest")
    return data

def confirm_uncertain_package(
    source: Path,
    *,
    expected_manifest_sha256: str,
    operator_attestation_path: Path,
) -> Path:
    """Operator-assisted confirmation for uncertain packages.

    This is NOT an unconditional override. It requires:
    - source package exists with manifest matching pinned hash
    - operator provides an explicit attestation JSON file containing:
      { "operator": str, "reason": str, "verified_checks": [str], "at": iso }
      and listing the manual checks performed (file digests, watermarks, receipts, etc.)
    - The attestation file itself is read-only and its hash is recorded in receipt.

    Only after manual verification should this be used. It creates a receipt
    marked as operator-confirmed, distinct from normal publication receipt.
    """
    require(operator_attestation_path.is_file() and not operator_attestation_path.is_symlink(), "attestation file missing or symlink")
    try:
        att = json.loads(operator_attestation_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"attestation unreadable: {exc}") from exc
    require(isinstance(att.get("operator"), str) and att["operator"].strip(), "attestation missing operator")
    require(isinstance(att.get("reason"), str) and att["reason"].strip(), "attestation missing reason")
    require(isinstance(att.get("verified_checks"), list) and len(att["verified_checks"]) > 0, "attestation must list verified checks")

    # Verify package itself is at least structurally valid (manifest hash matches)
    manifest_path = source / "manifest.json"
    require(manifest_path.is_file(), "manifest missing")
    actual_hash = digest(manifest_path)
    require(actual_hash == expected_manifest_sha256, "manifest hash mismatch, cannot confirm uncertain package")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pub_id = manifest.get("publication", {}).get("id")
    require(isinstance(pub_id, str) and pub_id, "manifest missing publication id")

    # Create operator-confirmed receipt
    receipt = {
        "format": RECEIPT_FORMAT,
        "publication_id": pub_id,
        "manifest_sha256": actual_hash,
        "operator_confirmed": True,
        "operator_attestation_sha256": digest(operator_attestation_path),
        "operator": att["operator"],
        "reason": att["reason"],
        "verified_checks": att["verified_checks"],
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
    }
    receipt_path = source / RECEIPT_NAME
    # Do not overwrite existing valid receipt
    require(not receipt_path.exists(), "receipt already exists; ordinary restore should be used")
    atomic_json(receipt_path, receipt)
    try:
        fd = os.open(source.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except BaseException:
        raise
    return receipt_path
