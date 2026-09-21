"""Read-only continuity verification for a frozen Sol Resident World.

Mechanical only: file digest, World revision, index watermark, subject payload
census. It performs no semantic interpretation, writes nothing to the World copy
it is pointed at, and never touches the sealed Life Director fixture.

Usage (from the repository root):

    PYTHONPATH=<pylibs>:src python3 \
      reviews/internal_habitation/sol-yearlong/segments/segment-003/verify_frozen_world.py \
      --world /path/to/world-145.sqlite \
      --expected-sha256 ba843f00e107cf6184ae25941d96ceb4ddb9a19234c99a789967c48f21cabec8 \
      --expected-revision 145 \
      --expected-watermark 145 \
      --expected-subject sol-resident-20260921-001
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path

from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", required=True, type=Path)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--expected-revision", required=True, type=int)
    parser.add_argument("--expected-watermark", required=True, type=int)
    parser.add_argument("--expected-subject", required=True)
    args = parser.parse_args()

    world = args.world.resolve()
    observed_sha = sha256_file(world)
    store = SQLiteWorldStore(world)
    index = WorldSearchIndex(world, store=store)
    observed_revision = int(store.current_world_revision())
    observed_watermark = int(index.watermark())

    census: collections.Counter[str] = collections.Counter()
    payloads = store.list_payloads(subject_id=args.expected_subject)
    for payload in payloads:
        record = payload if isinstance(payload, dict) else payload.model_dump(mode="json")
        census[str(record.get("object_type") or "unknown")] += 1

    report = {
        "world_path": str(world),
        "world_size_bytes": world.stat().st_size,
        "world_sha256": observed_sha,
        "expected_sha256": args.expected_sha256,
        "sha256_match": observed_sha == args.expected_sha256,
        "world_revision": observed_revision,
        "expected_revision": args.expected_revision,
        "revision_match": observed_revision == args.expected_revision,
        "index_watermark": observed_watermark,
        "expected_watermark": args.expected_watermark,
        "watermark_match": observed_watermark == args.expected_watermark,
        "subject_id": args.expected_subject,
        "subject_payload_count": len(payloads),
        "subject_payload_census": dict(sorted(census.items())),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))

    ok = all(
        (
            report["sha256_match"],
            report["revision_match"],
            report["watermark_match"],
            report["subject_payload_count"] > 0,
        )
    )
    print("CONTINUITY_OK" if ok else "CONTINUITY_FAILURE")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
