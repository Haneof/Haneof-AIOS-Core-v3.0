#!/usr/bin/env python3
"""Reviewer child-process helper for the Independent Acceptance probes.

Used to simulate a *fresh execution environment* that recovers only from the
remote authoritative backend.  Deliberately minimal and reviewer-authored; it
never touches PR #216, the canonical persistence ref, or any candidate code.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True,
                    choices=("materialize-report", "resume-report", "push-report"))
    ap.add_argument("--root", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--session-id", required=True)
    ap.add_argument("--remote", default="origin")
    ap.add_argument("--remote-ref", default=None)
    ap.add_argument("--commit-sha", default=None)
    ap.add_argument("--repo-dir", default=None)
    args = ap.parse_args(argv)

    from tools.c15_persistence.backend import RunBackend
    from tools.c15_persistence.operator_session import OperatorSession

    def snapshot(session):
        root = Path(session.backend.root)
        cur_p = root / "state" / "current-event.json"
        rs_p = root / "state" / "runtime" / "release_state.json"
        cur = json.loads(cur_p.read_text()) if cur_p.is_file() else {}
        rs = json.loads(rs_p.read_text()) if rs_p.is_file() else {}
        rep = session.report()
        gens = rep.get("generations")
        if isinstance(gens, dict):
            gens = sorted(gens)
        return {
            "cursor": cur.get("sequence"),
            "event_id": cur.get("event_id"),
            "last_acked_sequence": rs.get("last_acked_sequence"),
            "next_sequence": rs.get("next_sequence"),
            "counters": rep.get("counters"),
            "generations": len(gens or []),
            "dispatch_ledger": len(rep.get("dispatch_ledger") or []),
            "capability_ledger": len(rep.get("capability_ledger") or []),
        }

    if args.mode == "materialize-report":
        # A brand new environment: nothing local, only the remote ref.
        session = OperatorSession.materialize_and_attach(
            args.root,
            run_id=args.run_id,
            session_id=args.session_id,
            remote_ref=args.remote_ref,
            commit_sha=args.commit_sha,
            remote=args.remote,
            repo_dir=Path(args.repo_dir) if args.repo_dir else None,
        )
        rep = session.report()
        out = dict(snapshot(session), mode=args.mode)
    elif args.mode == "resume-report":
        session = OperatorSession.attach(args.root, run_id=args.run_id,
                                         session_id=args.session_id)
        out = dict(snapshot(session), mode=args.mode)
    else:  # push-report
        backend = RunBackend.open(args.root, run_id=args.run_id,
                                  session_id=args.session_id,
                                  adopt_stale_owner=True)
        ref, sha = backend.push_to_remote(
            remote_ref=args.remote_ref, remote=args.remote,
            repo_dir=Path(args.repo_dir) if args.repo_dir else None,
        )
        backend.release()
        out = {"mode": args.mode, "remote_ref": ref, "commit_sha": sha}

    print(json.dumps(out, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
