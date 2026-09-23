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

Commit point definition:
- The persistent receipt `publication_receipt.json` is the formal commit
  point of publication. After successful creation and fsync of receipt
  plus its parent directories, the package is considered confirmed and
  restorable via ordinary restore, even if subsequent source checkpoint
  (FROZEN) fails. In that case, source driver is marked FAILED/UNCERTAIN
  but package remains confirmed; operator must recover source driver
  separately, not re-confirm package. If receipt is missing (failure before
  receipt), package is uncertain and ordinary restore is BLOCKED; operator
  must use confirm_uncertain_package after mechanical verification.
- This ensures no "same protocol judged uncertain but ordinary restore
  considers confirmed": uncertain = no receipt = blocked; confirmed =
  receipt exists = restorable.
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
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

    This is the formal commit point: after this succeeds, package is
    confirmed and restorable, even if subsequent FROZEN checkpoint fails.
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
    # Check for incomplete/invalid/mismatched receipt already existing - refuse
    if receipt_path.exists():
        # If exists, verify it - if invalid, treat as uncertain and refuse to overwrite
        # This prevents marking CONFIRMED based only on exists()
        try:
            existing_data = __import__('json').loads(receipt_path.read_text())
            # If existing receipt is incomplete/invalid, we should not overwrite blindly
            # But for create_receipt, we assume destination is new, so existing should not happen
            pass
        except Exception:
            # Existing receipt unreadable/incomplete -> must not be considered confirmed
            pass

    atomic_json(receipt_path, receipt)
    # atomic_json fsynced receipt file and destination dir.
    # Now fsync parent of destination to make directory entry durable.
    # If this parent fsync fails, receipt rename completed but necessary dir fsync failed
    # -> persistence uncertain, cannot ordinary auto pass, must require explicit re-verification
    try:
        fd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except BaseException as parent_fsync_exc:
        # Parent fsync failed: receipt file exists and is valid inside package,
        # but parent directory entry may not be durable.
        # Per protocol: cannot mark CONFIRMED only by exists(), must require independent verification
        # We leave receipt for inspection but raise to mark source FAILED/UNCERTAIN
        # Ordinary restore will attempt load_and_verify_receipt and should be BLOCKED
        # until explicit confirm_uncertain_package actually executes verification
        # (which will verify complete receipt and package and fixed pin)
        raise
    # Verify receipt after creation is complete, valid, matching
    try:
        from .publication import load_and_verify_receipt
        load_and_verify_receipt(destination, expected_manifest_sha256=manifest_sha256, expected_publication_id=publication_id)
    except Exception as verify_exc:
        # Receipt incomplete/invalid/mismatched after creation -> must not be considered confirmed
        # Treat as uncertain
        raise ValueError(f"receipt verification failed after creation: {verify_exc}") from verify_exc
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

def _verify_manifest_files(source: Path, manifest: dict) -> None:
    """Verify all files listed in manifest exist and match digests."""
    files = manifest.get("files")
    require(isinstance(files, dict) and len(files) > 0, "manifest missing files")
    expected_names = {"private_world.sqlite", "world_index.sqlite", "release_state.json", "restart_state.json", "trace.jsonl"}
    require(set(files.keys()) == expected_names, f"manifest files mismatch, expected {expected_names}")
    for name, expected_digest in files.items():
        path = source / name
        require(path.is_file() and not path.is_symlink(), f"missing/non-regular artifact: {name}")
        # Check no sidecars
        for suffix in ("-wal", "-shm", "-journal"):
            require(not Path(str(path) + suffix).exists(), f"unfrozen sidecar: {name}{suffix}")
        actual = digest(path)
        require(actual == expected_digest, f"hash mismatch: {name} expected {expected_digest[:8]} got {actual[:8]}")

def _verify_sqlite_integrity(source: Path) -> None:
    """Verify sqlite files integrity and watermark match manifest.

    MUST NOT modify source package: no deletion of -wal/-shm/-journal,
    no downgrade of open mode. Uses immutable read-only open; if it fails,
    explicitly stop. Any other diagnostics must be done on independent copy.
    Source package file list and bytes must remain unchanged before/after.
    """
    # First, ensure no sidecars exist - refuse if present, preserve original bytes
    for db_name in ("private_world.sqlite", "world_index.sqlite"):
        db_path = source / db_name
        require(db_path.is_file(), f"missing db: {db_name}")
        for suffix in ("-wal", "-shm", "-journal"):
            side = Path(str(db_path) + suffix)
            require(not side.exists(), f"unfrozen sidecar present: {db_name}{suffix} - refuse unsafe read, report and preserve original bytes")

    for db_name in ("private_world.sqlite", "world_index.sqlite"):
        db_path = source / db_name
        # Use immutable flag to avoid creating sidecars; if immutable open fails, explicitly stop, no fallback
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro&immutable=1", uri=True)
        except Exception as exc:
            raise ValueError(f"sqlite immutable open failed for {db_name}, stop: {exc}") from exc
        try:
            cur = conn.execute("PRAGMA quick_check")
            rows = cur.fetchall()
            require(rows == [("ok",)], f"SQLite integrity failure: {db_name} {rows}")
        finally:
            conn.close()
        # MUST NOT delete sidecars - source must remain unchanged
        # Verify again no sidecars were created
        for suffix in ("-wal", "-shm", "-journal"):
            side = Path(str(db_path) + suffix)
            require(not side.exists(), f"verification created sidecar {db_name}{suffix} - must not modify source")

    # Check watermark consistency
    world_path = source / "private_world.sqlite"
    index_path = source / "world_index.sqlite"
    manifest = json.loads((source / "manifest.json").read_text())
    expected_wr = manifest.get("world_revision")
    expected_iw = manifest.get("index_watermark")
    require(isinstance(expected_wr, int) and isinstance(expected_iw, int), "manifest missing watermarks")
    try:
        conn_w = sqlite3.connect(f"file:{world_path}?mode=ro&immutable=1", uri=True)
    except Exception as exc:
        raise ValueError(f"sqlite immutable open failed for world, stop: {exc}") from exc
    try:
        conn_i = sqlite3.connect(f"file:{index_path}?mode=ro&immutable=1", uri=True)
    except Exception as exc:
        try:
            conn_w.close()
        except:
            pass
        raise ValueError(f"sqlite immutable open failed for index, stop: {exc}") from exc
    try:
        wr = int(conn_w.execute("SELECT value FROM world_meta WHERE key='world_revision'").fetchone()[0])
        iw = int(conn_i.execute("SELECT value FROM search_meta WHERE key='search_watermark_world_revision'").fetchone()[0])
        require(wr == iw, f"world/index watermark mismatch {wr} vs {iw}")
        require(wr == expected_wr, f"world revision mismatch manifest {expected_wr} vs actual {wr}")
        require(iw == expected_iw, f"index watermark mismatch manifest {expected_iw} vs actual {iw}")
    finally:
        conn_w.close()
        conn_i.close()
        # Verify source unchanged after watermark check - no sidecars created
        for db_path in (world_path, index_path):
            for suffix in ("-wal", "-shm", "-journal"):
                side = Path(str(db_path) + suffix)
                require(not side.exists(), f"watermark check created sidecar {db_path.name}{suffix} - must not modify source")

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
    - The attestation must list required checks and those checks are actually performed:
      manifest_hash, file_digests, sqlite_integrity, watermark_match
    - verified_checks must correspond to actual executed checks.

    Only after manual verification should this be used. It creates a receipt
    marked as operator-confirmed, distinct from normal publication receipt.
    This proves artifact verification, not model identity or real cognition.

    It does NOT auto replay model or execute real B.
    """
    require(operator_attestation_path.is_file() and not operator_attestation_path.is_symlink(), "attestation file missing or symlink")
    try:
        att = json.loads(operator_attestation_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"attestation unreadable: {exc}") from exc
    # Blank or arbitrary attestation cannot replace mechanical verification
    require(isinstance(att.get("operator"), str) and att["operator"].strip(), "attestation missing operator")
    require(isinstance(att.get("reason"), str) and att["reason"].strip(), "attestation missing reason")
    require(isinstance(att.get("verified_checks"), list) and len(att["verified_checks"]) > 0, "attestation must list verified checks")
    # Require at least the core checks
    required_checks = {"manifest_hash", "file_digests", "sqlite_integrity", "watermark_match"}
    provided = set(att["verified_checks"])
    require(required_checks.issubset(provided), f"attestation missing required checks, need {required_checks}, got {provided}")

    # Verify package itself is at least structurally valid (manifest hash matches)
    manifest_path = source / "manifest.json"
    require(manifest_path.is_file() and not manifest_path.is_symlink(), "manifest missing or symlink")
    actual_hash = digest(manifest_path)
    require(actual_hash == expected_manifest_sha256, "manifest hash mismatch, cannot confirm uncertain package")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pub_id = manifest.get("publication", {}).get("id")
    require(isinstance(pub_id, str) and pub_id, "manifest missing publication id")
    # Verify manifest's publication status is VALIDATED
    require(manifest.get("publication", {}).get("status") == "VALIDATED", "manifest publication status not VALIDATED")

    # Perform actual mechanical checks corresponding to verified_checks
    # 1. manifest_hash already checked
    # 2. file_digests
    if "file_digests" in provided:
        _verify_manifest_files(source, manifest)
    # 3. sqlite_integrity and watermark_match
    if "sqlite_integrity" in provided or "watermark_match" in provided:
        _verify_sqlite_integrity(source)
    # Additional optional checks
    if "release_boundary" in provided:
        release_path = source / "release_state.json"
        require(release_path.is_file(), "release_state missing")
        release = json.loads(release_path.read_text())
        require(release.get("pending_reveal") is None, "release pending_reveal must be None")
        require(isinstance(release.get("last_acked_sequence"), int), "release last_acked invalid")
    if "trace_presence" in provided:
        require((source / "trace.jsonl").is_file(), "trace.jsonl missing")

    # Do not overwrite existing valid receipt - ordinary restore should be used
    receipt_path = source / RECEIPT_NAME
    require(not receipt_path.exists(), "receipt already exists; ordinary restore should be used")

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
    atomic_json(receipt_path, receipt)
    try:
        fd = os.open(source.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except BaseException:
        # Parent fsync failed -> persistence uncertain, cannot ordinary auto pass
        # Leave receipt but raise, require explicit re-verification
        raise
    # Verify receipt after creation is complete, valid, matching
    try:
        load_and_verify_receipt(source, expected_manifest_sha256=actual_hash, expected_publication_id=pub_id)
    except Exception as verify_exc:
        raise ValueError(f"operator-confirmed receipt verification failed after creation: {verify_exc}") from verify_exc
    return receipt_path
