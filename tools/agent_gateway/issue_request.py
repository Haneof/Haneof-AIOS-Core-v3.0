"""Strict GitHub Issue -> allowlisted task parser for public Gateway v0.2.

Only the trusted repository owner may open a task Issue. Never treat issue body
as code, path, URL, command or credential. Fail closed on noncanonical requests.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any

import importlib.util

# -I excludes the script directory from sys.path. Load only our fixed local
# approved sibling source by absolute path, never from a user-supplied name.
_path = Path(__file__).resolve().with_name("runner.py")
_spec = importlib.util.spec_from_file_location("aios_issue_gateway_runner", _path)
if _spec is None or _spec.loader is None:
    raise RuntimeError("missing approved local runner")
_runner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_runner)
HEAD, REPO, TASKS = _runner.HEAD, _runner.REPO, _runner.TASKS


ISSUE_SCHEMA = "aios.agent.gateway.issue.request.v0.2"
TITLE_PREFIX = "[AIOS-GW-V02] "
TRUSTED_AUTHOR = "Haneof"
MAX_BODY_BYTES = 512


class BadIssueRequest(ValueError):
    """Untrusted or malformed task request."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise BadIssueRequest(message)


def no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON field")
        result[key] = value
    return result


def choose_task(event_name: str, event: dict) -> str:
    require(isinstance(event, dict), "GitHub event must be an object")
    repo = event.get("repository")
    require(isinstance(repo, dict) and repo.get("full_name") == REPO,
            "wrong GitHub repository")
    if event_name == "pull_request":
        return "gateway-selftest"
    require(event_name == "issues" and event.get("action") == "opened",
            "not an allowed newly opened issue event")
    issue = event.get("issue")
    require(isinstance(issue, dict), "missing issue object")
    author = issue.get("user")
    require(isinstance(author, dict) and author.get("login") == TRUSTED_AUTHOR,
            "only pinned owner may submit tasks")
    require(type(issue.get("number")) is int and issue["number"] > 0,
            "missing numeric issue identity")
    body = issue.get("body")
    require(isinstance(body, str)
            and len(body.encode("utf-8")) <= MAX_BODY_BYTES,
            "invalid task body or too large")
    try:
        request = json.loads(body, object_pairs_hook=no_duplicate_keys)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise BadIssueRequest("body must be strict JSON") from exc
    require(isinstance(request, dict)
            and set(request) == {"schema", "task", "candidate_head"},
            "unexpected or missing task fields")
    require(request["schema"] == ISSUE_SCHEMA, "wrong request schema")
    require(type(request["task"]) is str and request["task"] in TASKS,
            "task not on fixed allowlist")
    require(request["candidate_head"] == HEAD, "candidate identity mismatch")
    require(issue.get("title") == TITLE_PREFIX + request["task"],
            "issue title must exactly bind the task")
    return request["task"]


def main() -> int:
    try:
        event_path = os.environ["GITHUB_EVENT_PATH"]
        event_name = os.environ["GITHUB_EVENT_NAME"]
        output_path = os.environ["GITHUB_OUTPUT"]
        event = json.loads(Path(event_path).read_text(encoding="utf-8"))
        task = choose_task(event_name, event)
        # The output is a literal from TASKS, not user-controlled shell content.
        with Path(output_path).open("a", encoding="utf-8") as out:
            out.write("task=" + task + "\n")
        print(json.dumps({
            "schema": ISSUE_SCHEMA,
            "result": "APPROVED_ALLOWLIST_TASK",
            "task": task,
            "classification": "NON_FORMAL_PUBLIC_CI_EVIDENCE",
        }, sort_keys=True))
        return 0
    except (BadIssueRequest, ValueError, KeyError, OSError, TypeError) as exc:
        print(json.dumps({
            "result": "REJECTED",
            "reason": str(exc)[:160],
            "classification": "NO_TASK_EXECUTED",
        }, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
