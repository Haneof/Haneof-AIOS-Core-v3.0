"""Read-only verification of the pinned accepted-A handoff; never starts Core.

Only operator metadata is returned. No transcripts, decisions, fixture events or
private payloads are read into a Resident packet. Run under Python >=3.12.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

CORE_SHA = "bcd6bf353126318f9a97076b52ec1740d43f35a4"
A_SHA = "3e51f728d7959048b75fea01d405bc837b0e8185"
FIXTURE_HASH = "sha256:7ccb309d207cb6ee240fbc008ee4f535e25571f04ba7ca1b7c95bf9afb5ebf46"
# First three pins are authoritative governance hashes. Restart/manifest pins are
# independently measured from exact #117 A_SHA bytes, not an untrusted local manifest.
HASHES = {
    "private_world.sqlite": "9ff2b13cc1ec6e4d61a7910b4177ed3e1f25cfc47df8e18481a0199dd1aad395",
    "world_index.sqlite": "55282a61d714f732f1b10fa6b450853f8425b5c9f741090fcaad0f1e673a6643",
    "release_state.json": "b626cdd7d8ee16bcc9123ef8641bb05637d73d713023a471a74d7f6a392e052e",
    "restart_state.json": "7bc91400f6fa609efe7937c3b63b4823d1b269e920400149dc30d5e1a6d66e22",
    "ARTIFACT_MANIFEST.json": "cc79379f4bcc7c655d36ce8700fa24375c6c2bee84a4d9f1144e4314ece09899",
}
RESTART_KEYS = {
    "restart_state_format", "note", "session_id", "subject_id",
    "conversation_turn_index", "final_virtual_clock", "next_periodic_review_at",
    "review_interval_hours", "final_world_revision", "final_index_watermark",
    "done_at_cursor", "release_state_next_sequence", "process_ended",
}


class AuditError(ValueError):
    pass


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AuditError(label)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_files(directory: Path, expected: dict[str, str]) -> dict[str, str]:
    """Exact bytes only. Refuse sidecars rather than silently ignoring live WAL."""
    for name, wanted in expected.items():
        require(Path(name).name == name, "non-flat artifact name")
        path = directory / name
        require(path.is_file() and not path.is_symlink(), f"missing/non-regular artifact: {name}")
        for suffix in ("-wal", "-shm", "-journal"):
            require(not Path(str(path) + suffix).exists(), f"unfrozen sidecar: {name}{suffix}")
        require(digest(path) == wanted, f"hash mismatch: {name}")
    return dict(expected)


def verify_core(repo: Path) -> str:
    def git(*args: str) -> str:
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()
    frozen = git("rev-parse", f"{CORE_SHA}:src/aios_core")
    require(git("rev-parse", "HEAD:src/aios_core") == frozen, "Core committed tree mismatch")
    require(not git("diff", "HEAD", "--", "src/aios_core"), "Core worktree/index dirty")
    require(not git("ls-files", "--others", "--exclude-standard", "--", "src/aios_core"),
            "untracked Core source")
    # This proves tracked source, not interpreter/import-path/container isolation.
    return frozen


def readonly(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)


def verify_boundary(directory: Path) -> dict:
    """Metadata/durable-ref audit only, not a recomputation against sealed events."""
    release = json.loads((directory / "release_state.json").read_text())
    restart = json.loads((directory / "restart_state.json").read_text())
    require(release["active_phase"] == "A", "not an A handoff")
    require(release["fixture_sha256"] == FIXTURE_HASH, "fixture pin mismatch")
    require((release["last_acked_sequence"], release["next_sequence"], release["pending_reveal"])
            == (13, 14, None), "A cursor boundary mismatch")
    require(set(restart) == RESTART_KEYS, "restart contains missing/unreviewed fields")
    require((restart["done_at_cursor"], restart["release_state_next_sequence"])
            == (13, 14), "restart cursor mismatch")
    require(restart["subject_id"] == "user_1", "restart subject mismatch")
    receipts = release["receipts"]
    require(len(receipts) == 13, "receipt count mismatch")
    refs = set()
    with closing(readonly(directory / "private_world.sqlite")) as world, closing(
        readonly(directory / "world_index.sqlite")
    ) as index:
        for conn in (world, index):
            require(conn.execute("PRAGMA quick_check").fetchall() == [("ok",)], "SQLite integrity")
        revision = int(world.execute("SELECT value FROM world_meta WHERE key='world_revision'").fetchone()[0])
        watermark = int(index.execute("SELECT value FROM search_meta WHERE key='search_watermark_world_revision'").fetchone()[0])
        require(revision == watermark == 88, "World/index boundary mismatch")
        require(restart["final_world_revision"] == restart["final_index_watermark"] == 88,
                "restart watermark mismatch")
        for seq, receipt in enumerate(receipts, 1):
            require(receipt["sequence"] == seq, "receipt order mismatch")
            require(receipt["fixture_sha256"] == FIXTURE_HASH, "receipt fixture mismatch")
            oid, rev = receipt["ingest_object_id"], receipt["ingest_revision"]
            ref = f"{oid}@{rev}"
            require(receipt["ingest_ref"] == ref and ref not in refs, "duplicate/invalid receipt ref")
            refs.add(ref)
            row = world.execute(
                "SELECT world_revision,object_type,subject_id FROM object_revisions WHERE object_id=? AND revision=?",
                (oid, rev),
            ).fetchone()
            require(row == (receipt["ingest_world_revision"], "observation", "user_1"),
                    "receipt does not bind durable Observation")
        meters = world.execute(
            "SELECT COUNT(*), SUM(usage_complete), COUNT(provider), COUNT(model) FROM metering_records"
        ).fetchone()
    return {
        "world_revision": revision, "index_watermark": watermark,
        "durable_receipt_refs": len(refs), "next_sequence": 14,
        "restart_inventory": "MECHANICAL_FIELDS_PRESENT_NOT_RELEASED",
        "next_review_at": restart["next_periodic_review_at"],
        "a_meter_calls": meters[0], "a_complete_usage_calls": meters[1],
        "a_provider_populated_calls": meters[2], "a_model_populated_calls": meters[3],
        "trusted_identity": "UNKNOWN",
        "limitations": ["No sealed payload/projection recomputation", "No runtime restart executed",
                        "No isolation attestation", "No full archival transcript/checkpoint download"],
    }


def audit(directory: Path, repo: Path) -> dict:
    verified = verify_files(directory, HASHES)
    manifest = json.loads((directory / "ARTIFACT_MANIFEST.json").read_text())
    require(manifest["anchor_commit"] == CORE_SHA, "manifest Core pin mismatch")
    entries = {item["path"]: item for item in manifest["artifacts"]}
    for name in HASHES.keys() - {"ARTIFACT_MANIFEST.json"}:
        require(entries[name]["sha256"] == "sha256:" + HASHES[name], f"manifest mismatch: {name}")
        require(entries[name]["bytes"] == (directory / name).stat().st_size, f"size mismatch: {name}")
    result = {"status": "HANDOFF_BYTES_VERIFIED_NOT_PREFLIGHT_COMPLETE", "accepted_a": A_SHA,
              "core": CORE_SHA, "core_tree": verify_core(repo), "hashes": verified,
              **verify_boundary(directory)}
    verify_files(directory, HASHES)  # Source artifacts must remain immutable through audit.
    return result


def main() -> int:
    if sys.version_info < (3, 12):
        raise SystemExit("BLOCKED: Python >=3.12 required (no gate downgrade)")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff-dir", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(json.dumps(audit(args.handoff_dir, args.repo), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
