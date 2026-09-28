"""Subprocess entry point for the frozen K1-K5 kill/restart probes.

Usage::

    python -m tools.c15_persistence.probe_cli --root <backend> --run-id <r> \\
        --session-id <s> --mode create [--kill-at K1_AFTER_REVEAL]
    python -m tools.c15_persistence.probe_cli --root <backend> --run-id <r> \\
        --session-id <s> --mode resume [--kill-at K2_AFTER_INGEST]

The child prints one JSON object on success.  When a kill barrier fires the
child dies with SIGKILL and prints nothing, which is exactly the state the
parent asserts on.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .operator_session import KILL_POINTS, OperatorSession


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--mode", choices=("create", "resume", "report"), required=True)
    parser.add_argument("--kill-at", choices=list(KILL_POINTS), default=None)
    parser.add_argument("--event-count", type=int, default=30)
    args = parser.parse_args(argv)

    if args.mode == "create":
        session = OperatorSession.create(
            args.root, run_id=args.run_id, session_id=args.session_id, event_count=args.event_count
        )
        outcome = session.process_one_cursor(kill_at=args.kill_at)
    elif args.mode == "resume":
        session = OperatorSession.attach(args.root, run_id=args.run_id, session_id=args.session_id)
        outcome = session.resume(kill_at=args.kill_at)
    else:
        session = OperatorSession.attach(args.root, run_id=args.run_id, session_id=args.session_id)
        print(json.dumps(session.report(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    report = session.report()
    print(
        json.dumps(
            {
                "mode": args.mode,
                "kill_at": args.kill_at,
                "projection": outcome["projection"],
                "ingest": outcome["ingest"],
                "turn": outcome["turn"],
                "ack": outcome["ack"],
                "observed": {
                    "observation_counts": session.observation_counts(outcome["projection"]["event_id"]),
                    "metering_rows": session.metering_rows(),
                    "counters": report["counters"],
                    "dispatch_ledger": report["dispatch_ledger"],
                    "capability_ledger": report["capability_ledger"],
                    "generations": report["generations"],
                },
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
