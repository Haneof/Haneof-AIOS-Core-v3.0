"""Wait for the next Resident checkpoint and print it (evidence-only tooling).

Used as: append my authored decision to the journal, then call this once. It
blocks until the live runtime opens a new semantic checkpoint (or the segment
finishes) and then prints the full RuntimeSnapshot for that checkpoint.

It performs no cognition. It only waits and renders.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .peek import load_pending, render_pending

BASE = Path(__file__).resolve().parents[1]
PENDING = BASE / "run" / "pending.json"
LAST_SEEN = BASE / "run" / "last_seen.txt"
DONE = BASE / "run" / "DONE"
DAEMON_LOG = BASE / "run" / "daemon.log"


def _current_id() -> str | None:
    loaded = load_pending()
    if loaded is None:
        return None
    return str(loaded[0]["checkpoint_id"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default=1200.0)
    parser.add_argument("--tail", type=int, default=6,
                        help="daemon log lines shown when the segment completes")
    args = parser.parse_args()

    seen = LAST_SEEN.read_text(encoding="utf-8").strip() if LAST_SEEN.exists() else None
    deadline = time.time() + args.timeout

    while time.time() < deadline:
        current = _current_id()
        if DONE.exists() and (current is None or current == seen):
            print("=== SEGMENT COMPLETE (no further checkpoint) ===")
            if DAEMON_LOG.exists():
                lines = DAEMON_LOG.read_text(encoding="utf-8").splitlines()
                for line in lines[-args.tail:]:
                    print(line)
            return 0
        if current is not None and current != seen:
            LAST_SEEN.write_text(current + "\n", encoding="utf-8")
            meta, record = load_pending()  # type: ignore[misc]
            render_pending(meta, record)
            return 0
        time.sleep(0.4)

    print("=== TIMEOUT waiting for the next checkpoint ===")
    print(f"last_seen={seen} current={_current_id()}")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
