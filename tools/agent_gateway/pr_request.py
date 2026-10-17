"""Strict *owner-authored*, single-file PR task request intake.

For pull_request_target on GitHub-hosted ephemeral runners:
- the workflow MUST checkout only the immutable trusted base commit;
- this module MUST only read the untrusted PR commit as Git data;
- NEVER checkout, import, execute, pip install or eval code from the PR head.

GitHub event metadata is trusted only to identify the PR actor and exact SHAs.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

_THIS = Path(__file__).resolve()
_SPEC = importlib.util.spec_from_file_location(
    "aios_pr_gateway_runner", _THIS.with_name("runner.py")
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("trusted runner is missing")
_RUNNER = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_RUNNER)

REPO = _RUNNER.REPO
CANDIDATE = _RUNNER.HEAD
TASKS = _RUNNER.TASKS
REQUEST_PATH = "agent-tasks/gateway-request.json"
SCHEMA = "aios.agent.gateway.pr.request.v0.4"
TITLE_PREFIX = "[AIOS-GW-V04] "
TRUSTED_PR_AUTHOR = "Haneof"
MAX_REQUEST_BYTES = 512


class BadPrTask(ValueError):
    """Explicit fail-closed denial of an untrusted PR task."""


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise BadPrTask(reason)


def no_duplicate_keys(pairs):
    obj = {}
    for key, value in pairs:
        require(key not in obj, "duplicate JSON field")
        obj[key] = value
    return obj


def verify_event(event_name: str, event: dict) -> tuple[str, str]:
    require(event_name == "pull_request_target"
            and type(event) is dict and event.get("action") == "opened",
            "only newly opened pull_request_target events are allowed")
    repo = event.get("repository")
    pr = event.get("pull_request")
    require(type(repo) is dict and repo.get("full_name") == REPO,
            "wrong repository")
    require(type(pr) is dict and type(pr.get("number")) is int
            and pr["number"] > 0, "missing PR identity")
    author = pr.get("user")
    require(type(author) is dict and author.get("login") == TRUSTED_PR_AUTHOR,
            "unapproved PR author")
    base = pr.get("base")
    head = pr.get("head")
    require(type(base) is dict and type(head) is dict,
            "missing PR base or head")
    require(base.get("ref") == "main", "PR target must be main")
    for name, obj in (("base", base), ("head", head)):
        info = obj.get("repo")
        require(type(info) is dict and info.get("full_name") == REPO,
                f"{name} repository must be the trusted same repository")
    base_sha, head_sha = base.get("sha"), head.get("sha")
    require(all(type(sha) is str and re.fullmatch(r"[a-f0-9]{40}", sha)
                for sha in (base_sha, head_sha))
            and head_sha != base_sha, "invalid exact commit identity")
    return base_sha, head_sha


def validate_request(title: str, blob: bytes, changed_paths: list[str]) -> str:
    require(changed_paths == ["A\t" + REQUEST_PATH],
            "only a single added fixed task JSON file is allowed")
    require(type(blob) is bytes and 0 < len(blob) <= MAX_REQUEST_BYTES,
            "invalid request file size")
    try:
        doc = json.loads(blob.decode("utf-8"), object_pairs_hook=no_duplicate_keys)
    except (UnicodeError, ValueError) as exc:
        if isinstance(exc, BadPrTask):
            raise
        raise BadPrTask("invalid UTF-8 JSON request") from exc
    require(type(doc) is dict
            and set(doc) == {"schema", "task", "candidate_head"},
            "exact three-field JSON task request required")
    require(doc["schema"] == SCHEMA, "incorrect request schema")
    require(type(doc["task"]) is str and doc["task"] in TASKS,
            "task not in immutable allowlist")
    require(doc["candidate_head"] == CANDIDATE,
            "candidate is not the frozen engineering SHA")
    require(title == TITLE_PREFIX + doc["task"], "PR title does not match task")
    return doc["task"]


def safe_git(*args: str) -> bytes:
    try:
        proc = subprocess.run(
            ["git", *args], cwd=_RUNNER.ROOT, capture_output=True,
            timeout=90, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise BadPrTask("git read-only operation timed out") from exc
    if proc.returncode:
        raise BadPrTask("git " + args[0] + " refused, exit="
                        + str(proc.returncode))
    return proc.stdout


def select_task_from_checkout(event_name: str, event: dict) -> str:
    base_sha, head_sha = verify_event(event_name, event)
    origin = safe_git("remote", "get-url", "origin").decode("utf-8").strip()
    require(origin.rstrip("/").removesuffix(".git")
            == "https://github.com/" + REPO,
            "unexpected remote origin")
    require(safe_git("rev-parse", "HEAD").decode("ascii").strip()
            == base_sha, "trusted checkout does not equal event base SHA")
    # Only fetch data objects. No checkout, script execution or Git hooks.
    safe_git("fetch", "--no-tags", "origin", head_sha)
    require(safe_git("rev-parse", "FETCH_HEAD").decode("ascii").strip()
            == head_sha, "fetched request HEAD mismatch")
    diff = safe_git(
        "diff", "--no-ext-diff", "--name-status", "--no-renames",
        base_sha, head_sha, "--",
    ).decode("utf-8").splitlines()
    # Reject even harmless additional PR changes, file updates, deletions,
    # submodules, symlinks/rename tricks, and unrelated task code modifications.
    require(diff == ["A\t" + REQUEST_PATH],
            "PR contains anything other than one added task file")
    blob_ref = head_sha + ":" + REQUEST_PATH
    size = safe_git("cat-file", "-s", blob_ref).decode("ascii").strip()
    require(size.isdecimal() and 0 < int(size) <= MAX_REQUEST_BYTES,
            "task JSON blob too large")
    kind = safe_git("cat-file", "-t", blob_ref).decode("ascii").strip()
    require(kind == "blob", "task request not a regular Git blob")
    mode = safe_git("ls-tree", head_sha, "--", REQUEST_PATH).decode().strip()
    require(mode.startswith("100644 blob "), "task file is not a regular 0644 blob")
    return validate_request(event["pull_request"].get("title", ""),
                            safe_git("show", blob_ref), diff)


def main() -> int:
    try:
        event = json.loads(
            Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8")
        )
        task = select_task_from_checkout(
            os.environ["GITHUB_EVENT_NAME"], event
        )
        with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as out:
            out.write("task=" + task + "\n")
        print(json.dumps({
            "schema": SCHEMA, "status": "APPROVED_ALLOWLIST_TASK",
            "task": task, "classification": "NON_FORMAL_PUBLIC_CI_EVIDENCE",
        }, sort_keys=True))
        return 0
    except (BadPrTask, KeyError, TypeError, UnicodeError, ValueError, OSError) as exc:
        print(json.dumps({
            "status": "REJECTED", "classification": "NO_TASK_EXECUTED",
            "error": type(exc).__name__ + ": " + str(exc)[:180],
        }, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
