"""Platform reattach runner for Stage A and Stage B.

Cross-Attachment Protocol
-------------------------
Stage A (executed in the current environment):
1. Verifies the code worktree is clean and pins the PR candidate SHA.
2. Creates a synthetic run under disposable local cache.
3. Advances at least one synthetic cursor through the full wired pipeline.
4. Pins the run-state manifest and seals the generation.
5. Pushes the complete authoritative run state to the durable remote Git backend (origin).
6. Verifies remote ref existence and manifest integrity.
7. Verifies the code repository's worktree remains clean.
8. Outputs the fixed parameters and stops at PLATFORM_REATTACH_STAGE_A_READY.

Stage B (executed exclusively in a fresh, independent Arena AI window):
1. Materializes the run state directly from the remote Git ref into its fresh local cache.
2. Proves byte-for-byte re-attach fidelity against the pre-detach manifest.
3. Advances to the next cursor and pushes the updated state to the remote ref.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

from .backend import RunBackend, require, runs_root
from .operator_session import OperatorSession
from .remote_backend import (
    DEFAULT_REMOTE,
    default_repo_dir,
    materialize_run_state,
    push_run_state,
    remote_ref_for_run,
    verify_remote_state,
)
from .runstate import capture_manifest, read_manifest, verify_reattach, write_manifest


def run_stage_a(args: argparse.Namespace) -> dict[str, Any]:
    repo = default_repo_dir()

    # 1. Candidate SHA: HEAD commit of the current branch
    candidate_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=str(repo), text=True
    ).strip()

    # 2. Check local repository worktree is clean
    status = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=str(repo), text=True
    ).strip()
    require(
        not status,
        f"worktree must be clean before Stage A, found changes:\n{status}",
    )

    # 3. Create fresh run and session identity
    uid = uuid.uuid4().hex[:12]
    run_id = args.run_id or f"c15-persistence-synthetic-run-{uid}"
    session_id = args.session_id or f"c15-persistence-synthetic-session-{uid}"

    # 4. Local disposable cache directory
    runs_dir = runs_root()
    runs_dir.mkdir(parents=True, exist_ok=True)
    local_dir = runs_dir / run_id
    require(not local_dir.exists(), f"run cache already exists: {local_dir}")

    # 5. Establish the authoritative remote binding at creation time, then
    # process at least one cursor.  Remote-authoritative runs may never be
    # promoted later from a local-only owner record.
    remote_ref = args.remote_ref or remote_ref_for_run(run_id)
    remote = args.remote or DEFAULT_REMOTE
    session = OperatorSession.create(
        local_dir,
        run_id=run_id,
        session_id=session_id,
        event_count=args.event_count,
        remote_ref=remote_ref,
        remote=remote,
        repo_dir=repo,
        require_remote_durability=True,
    )
    outcome = session.process_one_cursor()
    require(outcome["ack"]["status"] == "acked", "Cursor 1 was not acked")

    # 6. Capture pre-detach run-state manifest and record latest generation
    cursor = int(outcome["projection"]["sequence"])
    event_id = str(outcome["projection"]["event_id"])
    manifest = capture_manifest(
        session.backend, cursor=cursor, event_id=event_id, phase="A"
    )
    write_manifest(session.backend, manifest, name="run-state-manifest.json")
    manifest_sha256 = manifest["manifest_sha256"]
    generation = session.generations.latest() or 1

    # Release backend flock before Git commit
    session.backend.release()

    # 7. Push the manifest-bearing authoritative run state to durable remote backend
    pushed_ref, commit_sha = push_run_state(
        session.backend,
        remote_ref=remote_ref,
        remote=remote,
        repo_dir=repo,
        message=(
            f"Platform Reattach Stage A: run_id={run_id} generation={generation} "
            f"manifest={manifest_sha256}"
        ),
    )

    # 8. Verify remote state is readable on remote
    remote_check = verify_remote_state(
        remote_ref=pushed_ref,
        commit_sha=commit_sha,
        expected_manifest_sha256=manifest_sha256,
        remote=remote,
        repo_dir=repo,
    )
    require(remote_check["verified"] is True, f"Remote verification failed: {remote_check}")

    # 9. Verify local worktree in repo remains clean
    status_after = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=str(repo), text=True
    ).strip()
    require(
        not status_after,
        f"worktree must remain clean after Stage A, found changes:\n{status_after}",
    )

    return {
        "status": "PLATFORM_REATTACH_STAGE_A_READY",
        "candidate_sha": candidate_sha,
        "remote_ref": pushed_ref,
        "remote_commit_sha": commit_sha,
        "run_id": run_id,
        "session_id": session_id,
        "generation": generation,
        "manifest_sha256": manifest_sha256,
        "cursor": cursor,
        "event_id": event_id,
    }


def run_stage_b(args: argparse.Namespace) -> dict[str, Any]:
    repo = default_repo_dir()
    run_id = args.run_id
    session_id = args.session_id
    remote_ref = args.remote_ref or remote_ref_for_run(run_id)
    remote = args.remote or DEFAULT_REMOTE
    expected_manifest_sha256 = args.manifest_sha256
    commit_sha = args.commit_sha

    runs_dir = runs_root()
    runs_dir.mkdir(parents=True, exist_ok=True)
    local_dir = runs_dir / f"{run_id}-stage-b"
    require(not local_dir.exists(), f"Target local directory already exists: {local_dir}")

    # 1. Materialize from remote
    backend = materialize_run_state(
        run_id=run_id,
        session_id=session_id,
        target_dir=local_dir,
        remote_ref=remote_ref,
        commit_sha=commit_sha,
        remote=remote,
        repo_dir=repo,
    )

    # 2. Verify pre-detach manifest byte-for-byte
    manifest = read_manifest(local_dir / "run-state-manifest.json")
    if expected_manifest_sha256:
        require(
            manifest["manifest_sha256"] == expected_manifest_sha256,
            "Manifest SHA256 mismatch",
        )
    report = verify_reattach(backend, manifest)
    require(report["reattached"] is True, f"Reattach verification failed: {report['failures']}")
    backend.release()

    # 3. Attach session and advance to next cursor
    session = OperatorSession.attach(local_dir, run_id=run_id, session_id=session_id)
    outcome = session.resume()
    require(outcome["ack"]["status"] == "acked", "Resumed cursor was not acked")

    # 4. Capture new manifest
    cursor = int(outcome["projection"]["sequence"])
    event_id = str(outcome["projection"]["event_id"])
    new_manifest = capture_manifest(
        session.backend, cursor=cursor, event_id=event_id, phase="A"
    )
    write_manifest(session.backend, new_manifest, name="run-state-manifest.json")
    generation = session.generations.latest()
    session.backend.release()

    # 5. Push updated state to remote
    new_ref, new_commit_sha = push_run_state(
        session.backend,
        remote_ref=remote_ref,
        remote=remote,
        repo_dir=repo,
        message=f"Platform Reattach Stage B: run_id={run_id} generation={generation} cursor={cursor}",
    )

    return {
        "status": "PLATFORM_REATTACH_STAGE_B_COMPLETE",
        "run_id": run_id,
        "session_id": session_id,
        "resumed_cursor": cursor,
        "resumed_event_id": event_id,
        "generation": generation,
        "manifest_sha256": new_manifest["manifest_sha256"],
        "remote_ref": new_ref,
        "remote_commit_sha": new_commit_sha,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    parser_a = subparsers.add_parser("stage-a", help="Execute Platform Reattach Stage A")
    parser_a.add_argument("--run-id", default=None, help="Custom run id (optional)")
    parser_a.add_argument("--session-id", default=None, help="Custom session id (optional)")
    parser_a.add_argument("--remote-ref", default=None, help="Custom remote ref (optional)")
    parser_a.add_argument("--remote", default=DEFAULT_REMOTE, help="Git remote (default origin)")
    parser_a.add_argument("--event-count", type=int, default=30)

    parser_b = subparsers.add_parser("stage-b", help="Execute Platform Reattach Stage B")
    parser_b.add_argument("--run-id", required=True)
    parser_b.add_argument("--session-id", required=True)
    parser_b.add_argument("--remote-ref", default=None)
    parser_b.add_argument("--commit-sha", default=None)
    parser_b.add_argument("--manifest-sha256", default=None)
    parser_b.add_argument("--remote", default=DEFAULT_REMOTE)

    args = parser.parse_args(argv)
    if args.subcommand == "stage-a":
        result = run_stage_a(args)
    elif args.subcommand == "stage-b":
        result = run_stage_b(args)
    else:
        parser.print_help()
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
