"""Synthetic positive and fail-closed checks for the public owner-only Issue inbox."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "agent_gateway"))
import issue_request as gateway_issue  # noqa: E402


def make_event(task="gateway-selftest", author="Haneof", action="opened"):
    return {
        "action": action,
        "repository": {"full_name": gateway_issue.REPO},
        "issue": {
            "number": 123,
            "user": {"login": author},
            "title": gateway_issue.TITLE_PREFIX + task,
            "body": json.dumps({
                "schema": gateway_issue.ISSUE_SCHEMA,
                "task": task,
                "candidate_head": gateway_issue.HEAD,
            }, separators=(",", ":")),
        },
    }


class IssueGatewayTests(unittest.TestCase):
    def test_approve_each_fixed_task_for_repository_owner(self):
        for task in gateway_issue.TASKS:
            with self.subTest(task=task):
                self.assertEqual(gateway_issue.choose_task("issues", make_event(task)), task)

    def test_pr_ci_selects_only_selftest(self):
        self.assertEqual(gateway_issue.choose_task("pull_request", {
            "repository": {"full_name": gateway_issue.REPO},
            "pull_request": {"head": {"sha": "nonsensitive"}},
        }), "gateway-selftest")

    def test_reject_other_people_and_bots(self):
        for author in ("evil", "Haneof[bot]", "", "haneof"):
            with self.subTest(author=author), self.assertRaises(gateway_issue.BadIssueRequest):
                gateway_issue.choose_task("issues", make_event(author=author))

    def test_reject_wrong_repository(self):
        data = make_event()
        data["repository"]["full_name"] = "other/project"
        with self.assertRaises(gateway_issue.BadIssueRequest):
            gateway_issue.choose_task("issues", data)

    def test_reject_other_events(self):
        for event in ("issue_comment", "push", "workflow_dispatch", ""):
            with self.subTest(event=event), self.assertRaises(gateway_issue.BadIssueRequest):
                gateway_issue.choose_task(event, make_event())
        with self.assertRaises(gateway_issue.BadIssueRequest):
            gateway_issue.choose_task("issues", make_event(action="edited"))

    def test_reject_wrong_title(self):
        data = make_event()
        data["issue"]["title"] = "[AIOS-GW-V02] gateway-selftest EXTRA"
        with self.assertRaises(gateway_issue.BadIssueRequest):
            gateway_issue.choose_task("issues", data)

    def test_reject_unknown_or_injected_task(self):
        for task in ("echo hello", "gateway-selftest\nrun=evil", "pr370-artifact-audit && rm -rf /"):
            data = make_event(task=task)
            with self.subTest(task=task), self.assertRaises(gateway_issue.BadIssueRequest):
                gateway_issue.choose_task("issues", data)

    def test_reject_wrong_candidate(self):
        data = make_event()
        doc = json.loads(data["issue"]["body"])
        doc["candidate_head"] = "0" * 40
        data["issue"]["body"] = json.dumps(doc)
        with self.assertRaises(gateway_issue.BadIssueRequest):
            gateway_issue.choose_task("issues", data)

    def test_reject_wrong_schema(self):
        data = make_event()
        doc = json.loads(data["issue"]["body"])
        doc["schema"] = "unexpected"
        data["issue"]["body"] = json.dumps(doc)
        with self.assertRaises(gateway_issue.BadIssueRequest):
            gateway_issue.choose_task("issues", data)

    def test_reject_extra_fields_and_missing_fields(self):
        data = make_event()
        doc = json.loads(data["issue"]["body"])
        doc["shell"] = "whoami"
        data["issue"]["body"] = json.dumps(doc)
        with self.assertRaises(gateway_issue.BadIssueRequest):
            gateway_issue.choose_task("issues", data)
        del doc["shell"]
        del doc["candidate_head"]
        data["issue"]["body"] = json.dumps(doc)
        with self.assertRaises(gateway_issue.BadIssueRequest):
            gateway_issue.choose_task("issues", data)

    def test_reject_duplicate_json_fields(self):
        data = make_event()
        data["issue"]["body"] = (
            '{"schema":"aios.agent.gateway.issue.request.v0.2",'
            '"task":"gateway-selftest","task":"pr370-artifact-audit",'
            '"candidate_head":"' + gateway_issue.HEAD + '"}'
        )
        with self.assertRaises(gateway_issue.BadIssueRequest):
            gateway_issue.choose_task("issues", data)

    def test_reject_body_too_large_or_invalid(self):
        for body in ("x" * 600, "{not json", None):
            data = make_event()
            data["issue"]["body"] = body
            with self.subTest(body=type(body).__name__), self.assertRaises(gateway_issue.BadIssueRequest):
                gateway_issue.choose_task("issues", data)

    def test_reject_noninteger_issue_identity(self):
        for number in (0, "123", True, None):
            data = make_event()
            data["issue"]["number"] = number
            with self.subTest(number=number), self.assertRaises(gateway_issue.BadIssueRequest):
                gateway_issue.choose_task("issues", data)

    def test_main_writes_only_literal_task_to_output(self):
        data = make_event(task="pr370-source-boundary")
        with tempfile.TemporaryDirectory() as folder:
            event_file = Path(folder) / "event.json"
            output_file = Path(folder) / "output.txt"
            event_file.write_text(json.dumps(data), encoding="utf-8")
            output_file.write_text("", encoding="utf-8")
            with patch.dict(os.environ, {
                "GITHUB_EVENT_NAME": "issues",
                "GITHUB_EVENT_PATH": str(event_file),
                "GITHUB_OUTPUT": str(output_file),
            }):
                self.assertEqual(gateway_issue.main(), 0)
            self.assertEqual(output_file.read_text(encoding="utf-8"),
                             "task=pr370-source-boundary\n")

    def test_main_denies_untrusted_author_without_task_output(self):
        data = make_event(author="not_owner")
        with tempfile.TemporaryDirectory() as folder:
            event_file = Path(folder) / "event.json"
            output_file = Path(folder) / "output.txt"
            event_file.write_text(json.dumps(data), encoding="utf-8")
            output_file.write_text("", encoding="utf-8")
            with patch.dict(os.environ, {
                "GITHUB_EVENT_NAME": "issues",
                "GITHUB_EVENT_PATH": str(event_file),
                "GITHUB_OUTPUT": str(output_file),
            }):
                self.assertEqual(gateway_issue.main(), 2)
            self.assertEqual(output_file.read_text(encoding="utf-8"), "")


if __name__ == "__main__":
    unittest.main()
