"""Durable remote backend implementation using Git storage for C15 persistence.

Historical Context & Degradation of Local Cache
------------------------------------------------
In the initial corrective attempt, the platform-persisted path ``/home/user``
was assumed to persist across new Arena execution environments. Real-world
multi-window testing demonstrated that ``/home/user`` is wiped across different
Arena attachment environments. Consequently:

* Local ``/home/user`` is **degraded** to a disposable local cache and
  materialization directory. It is ephemeral across session boundaries.
* The **authoritative** run state must be stored in a durable remote backend
  accessible across windows: Git branches/refs on GitHub (``origin``).
* Every critical milestone (generation sealed, run-state manifest pinned) can be
  persisted to an authoritative Git ref (``refs/heads/persistence/<run_id>``).
* When a fresh Arena execution environment starts (Stage B / reattach), it
  fetches the remote ref from GitHub, materializes the exact artifacts into its
  disposable local cache, and proves byte-for-byte re-attach fidelity.

This module provides the remote backend Git plumbing. It uses Git trees and
commits directly via plumbing commands so that:
1. The code repository's worktree and index are NEVER dirtied.
2. The entire run backend directory (owner record, journal, sqlite databases,
   mailbox, sealed generations, audit log, and pinned manifests) is captured
   as an immutable Git commit tree.
3. Checkpointed SQLite databases have their WAL flushed to disk before tree creation.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping

from .backend import BackendError, GenerationStore, RunBackend, digest, require, runs_root

DEFAULT_REMOTE = "origin"
DEFAULT_REF_PREFIX = "refs/heads/persistence"
LOCAL_EXPECTED_HEAD = ".remote-head"


def default_repo_dir() -> Path:
    """Return the root of the code git repository."""
    override = os.environ.get("C15_PERSISTENCE_REPO_DIR")
    if override:
        return Path(override).resolve()
    return Path(__file__).resolve().parents[2]


def remote_ref_for_run(run_id: str, *, prefix: str = DEFAULT_REF_PREFIX) -> str:
    """Construct canonical remote ref name for a given run_id."""
    require(bool(run_id), "run_id is required to construct remote ref")
    return f"{prefix}/{run_id}"


def _remote_head(repo: Path, remote: str, ref: str) -> str | None:
    completed = subprocess.run(
        ["git", "ls-remote", remote, ref],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    require(
        completed.returncode == 0,
        f"failed to read remote head {remote} {ref}:\n{completed.stderr}",
    )
    if not completed.stdout.strip():
        return None
    return completed.stdout.strip().split()[0]


def _expected_head_path(backend: RunBackend) -> Path:
    return backend.root / LOCAL_EXPECTED_HEAD


def _read_expected_remote_head(backend: RunBackend) -> str | None:
    path = _expected_head_path(backend)
    if not path.is_file():
        return None
    value = path.read_text(encoding="utf-8").strip()
    require(bool(value), "local expected remote head is empty")
    return value


def _write_expected_remote_head(backend: RunBackend, commit_sha: str) -> None:
    path = _expected_head_path(backend)
    temp = path.with_name(path.name + ".tmp")
    fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(commit_sha + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        dir_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if temp.exists():
            temp.unlink(missing_ok=True)


def checkpoint_sqlite_databases(root: Path) -> None:
    """Flush and truncate WALs for all SQLite databases under root before archiving."""
    for db_path in sorted(root.rglob("*.sqlite")):
        if db_path.is_file():
            try:
                conn = sqlite3.connect(str(db_path), timeout=10)
                try:
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                finally:
                    conn.close()
            except sqlite3.Error:
                pass


def commit_backend_tree(
    backend_root: Path,
    *,
    message: str,
    parent_sha: str | None = None,
    repo_dir: Path | None = None,
) -> tuple[str, str]:
    """Create a Git tree and commit object directly from the backend directory.

    Leaves the repository's working tree and primary index completely clean by
    using an isolated temporary index file.
    Returns (tree_sha, commit_sha).
    """
    repo = repo_dir or default_repo_dir()
    require(backend_root.is_dir(), f"backend root missing: {backend_root}")
    checkpoint_sqlite_databases(backend_root)

    temp_index = Path(tempfile.mktemp(prefix="persistence_git_idx_"))
    try:
        env = dict(os.environ, GIT_INDEX_FILE=str(temp_index))
        # git commit-tree is plumbing and must not depend on ambient per-runner
        # user.name/user.email configuration. Use a fixed operator identity so
        # the remote durability layer behaves identically in Arena and CI.
        env.setdefault("GIT_AUTHOR_NAME", "AIOS Persistence Operator")
        env.setdefault("GIT_AUTHOR_EMAIL", "aios-persistence@invalid.local")
        env.setdefault("GIT_COMMITTER_NAME", "AIOS Persistence Operator")
        env.setdefault("GIT_COMMITTER_EMAIL", "aios-persistence@invalid.local")
        # Add all backend files, excluding advisory flock files, temporary snapshots,
        # and SQLite WAL/SHM artifacts (checkpointed above).
        add_cmd = [
            "git",
            f"--work-tree={backend_root}",
            "add",
            "-A",
            "--",
            ".",
            ":!.owner.lock",
            ":!.remote-head",
            ":!*.tmp",
            ":!*.snapshot",
            ":!*-shm",
            ":!*-wal",
        ]
        completed = subprocess.run(
            add_cmd, cwd=str(repo), env=env, capture_output=True, text=True
        )
        require(
            completed.returncode == 0,
            f"git add failed for persistence backend:\n{completed.stderr}",
        )

        tree_sha = subprocess.check_output(
            ["git", "write-tree"], cwd=str(repo), env=env, text=True
        ).strip()
        require(bool(tree_sha), "empty git tree produced for persistence backend")

        commit_cmd = ["git", "commit-tree", tree_sha]
        if parent_sha:
            commit_cmd.extend(["-p", parent_sha])
        commit_cmd.extend(["-m", message])

        commit_sha = subprocess.check_output(
            commit_cmd, cwd=str(repo), env=env, text=True
        ).strip()
        require(bool(commit_sha), "git commit-tree produced empty commit sha")
        return tree_sha, commit_sha
    finally:
        if temp_index.exists():
            temp_index.unlink(missing_ok=True)


def push_run_state(
    backend: RunBackend,
    *,
    remote_ref: str | None = None,
    remote: str = DEFAULT_REMOTE,
    repo_dir: Path | None = None,
    message: str | None = None,
) -> tuple[str, str]:
    """Commit and push authoritative run state to the remote Git backend.

    Returns (persistence_remote_ref, exact_remote_commit_sha).
    """
    repo = repo_dir or default_repo_dir()
    run_id = str(backend.owner["run_id"])
    ref = remote_ref or remote_ref_for_run(run_id)

    # Compare-and-swap discipline: a writer may advance only the remote head
    # it explicitly materialized or previously pushed.  Never "adopt" a newer
    # remote head as parent for a stale local tree: that would be a fast-forward
    # Git push while still semantically overwriting another writer's state.
    actual_head = _remote_head(repo, remote, ref)
    expected_head = _read_expected_remote_head(backend)
    if expected_head is None:
        require(
            actual_head is None,
            "remote ref already exists but local writer has no expected head; "
            "materialize the authoritative remote state before writing",
        )
    else:
        require(
            actual_head == expected_head,
            f"remote CAS conflict for {ref}: expected {expected_head}, observed {actual_head}",
        )
    parent_sha = expected_head

    gen = GenerationStore(backend).latest() or 0
    msg = message or f"persisted run state: run_id={run_id} generation={gen}"

    tree_sha, commit_sha = commit_backend_tree(
        backend.root, message=msg, parent_sha=parent_sha, repo_dir=repo
    )

    push_cmd = ["git", "push", remote, f"{commit_sha}:{ref}"]
    pushed = subprocess.run(push_cmd, cwd=str(repo), capture_output=True, text=True)
    require(
        pushed.returncode == 0,
        f"failed to push run state to {remote} {ref}:\n{pushed.stderr}",
    )

    # Verify remote ref was updated to commit_sha.
    verify = subprocess.run(
        ["git", "ls-remote", remote, ref],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    require(
        verify.returncode == 0 and commit_sha in verify.stdout,
        f"remote ref {ref} on {remote} does not point to pushed commit {commit_sha}",
    )

    _write_expected_remote_head(backend, commit_sha)
    backend.audit(
        "remote_persisted",
        {
            "remote": remote,
            "remote_ref": ref,
            "commit_sha": commit_sha,
            "tree_sha": tree_sha,
            "parent_sha": parent_sha,
        },
    )
    return ref, commit_sha


def materialize_run_state(
    *,
    run_id: str,
    session_id: str,
    target_dir: Path | str,
    remote_ref: str | None = None,
    commit_sha: str | None = None,
    remote: str = DEFAULT_REMOTE,
    repo_dir: Path | None = None,
) -> RunBackend:
    """Fetch remote run state and materialize it into a local disposable directory.

    Reopens the materialized backend with adopt_stale_owner=True.
    """
    repo = repo_dir or default_repo_dir()
    ref = remote_ref or remote_ref_for_run(run_id)
    target = Path(target_dir).resolve()

    remote_head = _remote_head(repo, remote, ref)
    require(remote_head is not None, f"remote ref {ref} not found on {remote}")
    if commit_sha is not None:
        require(
            remote_head == commit_sha,
            f"remote ref {ref} head {remote_head} != pinned commit {commit_sha}",
        )
    resolved_commit = commit_sha or remote_head

    if target.exists():
        require(target.is_dir(), f"target path is not a directory: {target}")
        require(
            not any(target.iterdir()),
            f"target directory is not empty; materialization never overwrites: {target}",
        )
    else:
        target.mkdir(parents=True, mode=0o700)

    # Fetch ref from remote into a dedicated tracking ref or FETCH_HEAD.
    fetch_cmd = ["git", "fetch", remote, f"{ref}:refs/remotes/{remote}/persistence/{run_id}"]
    fetched = subprocess.run(
        fetch_cmd, cwd=str(repo), capture_output=True, text=True
    )
    if fetched.returncode != 0:
        # Fallback to direct fetch
        fallback = subprocess.run(
            ["git", "fetch", remote, ref], cwd=str(repo), capture_output=True, text=True
        )
        require(
            fallback.returncode == 0,
            f"failed to fetch {ref} from remote {remote}:\n{fetched.stderr}\n{fallback.stderr}",
        )

    # Extract all files from the exact commit currently pinned by the remote
    # ref.  The ref/commit equality check above prevents a stale pin from
    # silently materializing a different generation.
    p1 = subprocess.Popen(
        ["git", "archive", resolved_commit], cwd=str(repo), stdout=subprocess.PIPE
    )
    p2 = subprocess.Popen(["tar", "-x", "-C", str(target)], stdin=p1.stdout)
    p1.stdout.close()
    p2.communicate()
    require(p2.returncode == 0, "failed to extract git archive into target directory")

    # Restore directory permissions on sealed generations.
    generations_dir = target / "generations"
    if generations_dir.is_dir():
        for gen_dir in generations_dir.glob("[0-9]" * 6):
            if (gen_dir / ".sealed").is_file():
                try:
                    os.chmod(gen_dir, 0o500)
                except OSError:
                    pass

    # Open local backend with adopt_stale_owner=True.
    backend = RunBackend.open(
        target,
        run_id=run_id,
        session_id=session_id,
        adopt_stale_owner=True,
    )
    _write_expected_remote_head(backend, resolved_commit)
    backend.audit(
        "materialized_from_remote",
        {
            "remote": remote,
            "remote_ref": ref,
            "commit_sha": resolved_commit,
        },
    )
    return backend


def verify_remote_state(
    *,
    remote_ref: str,
    commit_sha: str,
    expected_manifest_sha256: str | None = None,
    remote: str = DEFAULT_REMOTE,
    repo_dir: Path | None = None,
) -> dict[str, Any]:
    """Verify that remote state exists and is internally consistent."""
    repo = repo_dir or default_repo_dir()

    ls = subprocess.run(
        ["git", "ls-remote", remote, remote_ref],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    require(
        ls.returncode == 0 and bool(ls.stdout.strip()),
        f"remote ref {remote_ref} not found on {remote}",
    )
    remote_head = ls.stdout.strip().split()[0]
    require(
        remote_head == commit_sha,
        f"remote ref {remote_ref} head {remote_head} != expected {commit_sha}",
    )

    owner_raw = subprocess.check_output(
        ["git", "show", f"{commit_sha}:owner.json"], cwd=str(repo), text=True
    )
    owner = json.loads(owner_raw)
    require(bool(owner.get("run_id")), "owner.json missing run_id in remote commit")

    manifest_check: dict[str, Any] = {}
    if expected_manifest_sha256:
        manifest_raw = subprocess.check_output(
            ["git", "show", f"{commit_sha}:run-state-manifest.json"],
            cwd=str(repo),
            text=True,
        )
        manifest = json.loads(manifest_raw)
        actual_sha = manifest.get("manifest_sha256")
        require(
            actual_sha == expected_manifest_sha256,
            f"remote manifest_sha256 {actual_sha} != expected {expected_manifest_sha256}",
        )
        manifest_check = {
            "manifest_sha256": actual_sha,
            "cursor": manifest.get("cursor"),
            "event_id": manifest.get("event_id"),
        }

    return {
        "verified": True,
        "remote": remote,
        "remote_ref": remote_ref,
        "commit_sha": commit_sha,
        "run_id": owner.get("run_id"),
        "session_id": owner.get("session_id"),
        "manifest": manifest_check,
    }
