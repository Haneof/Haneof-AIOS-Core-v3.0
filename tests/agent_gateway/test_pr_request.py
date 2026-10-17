"""Synthetic PR payloads and mocked Git blobs; no untrusted branch is executed."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "aios_gateway_pr_request_test", ROOT / "tools/agent_gateway/pr_request.py"
)
gateway = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gateway)

BASE = "528296def47f8f409350889f11961ebedc4a38c2"
HEAD = "f" * 40


def good_task(task="gateway-selftest"):
    return json.dumps({
        "schema": gateway.SCHEMA,
        "task": task,
        "candidate_head": gateway.CANDIDATE,
    }, separators=(",", ":")).encode()


def request_event(task="gateway-selftest", author="Haneof",
                  head_repo=gateway.REPO, action="opened"):
    return {
        "action": action,
        "repository": {"full_name": gateway.REPO},
        "pull_request": {
            "number": 475,
            "title": gateway.TITLE_PREFIX + task,
            "user": {"login": author},
            "base": {
                "ref": "main", "sha": BASE,
                "repo": {"full_name": gateway.REPO}
            },
            "head": {
                "sha": HEAD, "repo": {"full_name": head_repo}
            },
        },
    }


class MetadataPolicy(unittest.TestCase):
    def test_legitimate_owner_same_repo_metadata(self):
        self.assertEqual(gateway.verify_event(
            "pull_request_target", request_event()), (BASE, HEAD))

    def test_reject_non_owner_authors_and_bots(self):
        for name in ("other", "", "arena[bot]", "haneof"):
            with self.subTest(name=name), self.assertRaises(gateway.BadPrTask):
                gateway.verify_event("pull_request_target", request_event(author=name))

    def test_reject_fork(self):
        with self.assertRaises(gateway.BadPrTask):
            gateway.verify_event(
                "pull_request_target", request_event(head_repo="attacker/repo"))

    def test_reject_wrong_base(self):
        e = request_event()
        e["pull_request"]["base"]["ref"] = "feature"
        with self.assertRaises(gateway.BadPrTask):
            gateway.verify_event("pull_request_target", e)

    def test_reject_wrong_repository(self):
        e = request_event()
        e["repository"]["full_name"] = "other/repo"
        with self.assertRaises(gateway.BadPrTask):
            gateway.verify_event("pull_request_target", e)

    def test_reject_other_events_and_actions(self):
        e = request_event()
        for name in ("pull_request", "issues", ""):
            with self.subTest(event=name), self.assertRaises(gateway.BadPrTask):
                gateway.verify_event(name, e)
        e["action"] = "synchronize"
        with self.assertRaises(gateway.BadPrTask):
            gateway.verify_event("pull_request_target", e)

    def test_reject_malformed_exact_sha(self):
        e = request_event()
        e["pull_request"]["head"]["sha"] = "not a sha"
        with self.assertRaises(gateway.BadPrTask):
            gateway.verify_event("pull_request_target", e)


class ContentPolicy(unittest.TestCase):
    def test_current_v03_allowlist_is_complete(self):
        self.assertEqual(gateway.TASKS, (
            "gateway-selftest", "pr370-source-boundary", "pr370-artifact-audit",
            "pr371-evidence-integrity", "r005-binding-ledger",
        ))

    def test_allow_only_pinned_task(self):
        for task in gateway.TASKS:
            with self.subTest(task=task):
                self.assertEqual(gateway.validate_request(
                    gateway.TITLE_PREFIX + task, good_task(task),
                    ["A\t" + gateway.REQUEST_PATH]), task)

    def test_reject_unrelated_paths_or_code_changes(self):
        body = good_task()
        for changes in (
            [],
            ["M\t" + gateway.REQUEST_PATH],
            ["A\t" + gateway.REQUEST_PATH, "M\ttools/agent_gateway/runner.py"],
            ["A\t" + gateway.REQUEST_PATH, "A\tadditional.sh"],
            ["R100\told.txt\t" + gateway.REQUEST_PATH],
        ):
            with self.subTest(changes=changes), self.assertRaises(gateway.BadPrTask):
                gateway.validate_request(gateway.TITLE_PREFIX+"gateway-selftest",
                                         body, changes)

    def test_reject_shell_task_and_bad_title(self):
        body = json.dumps({
            "schema": gateway.SCHEMA, "task": "bash -c whoami",
            "candidate_head": gateway.CANDIDATE,
        }).encode()
        with self.assertRaises(gateway.BadPrTask):
            gateway.validate_request(
                gateway.TITLE_PREFIX+"bash -c whoami", body,
                ["A\t" + gateway.REQUEST_PATH])
        with self.assertRaises(gateway.BadPrTask):
            gateway.validate_request("Please run task", good_task(),
                                     ["A\t" + gateway.REQUEST_PATH])

    def test_reject_wrong_candidate_and_extra_keys(self):
        data = json.loads(good_task())
        data["candidate_head"] = "0"*40
        with self.assertRaises(gateway.BadPrTask):
            gateway.validate_request(
                gateway.TITLE_PREFIX+"gateway-selftest", json.dumps(data).encode(),
                ["A\t" + gateway.REQUEST_PATH])
        data["candidate_head"] = gateway.CANDIDATE
        data["command"] = "rm -rf /"
        with self.assertRaises(gateway.BadPrTask):
            gateway.validate_request(
                gateway.TITLE_PREFIX+"gateway-selftest", json.dumps(data).encode(),
                ["A\t" + gateway.REQUEST_PATH])

    def test_reject_duplicate_keys_and_large_payload(self):
        duplicate = b'{"schema":"' + gateway.SCHEMA.encode() + \
                    b'","task":"gateway-selftest","task":"pr370-artifact-audit",' + \
                    b'"candidate_head":"' + gateway.CANDIDATE.encode() + b'"}'
        with self.assertRaises(gateway.BadPrTask):
            gateway.validate_request(
                gateway.TITLE_PREFIX+"gateway-selftest", duplicate,
                ["A\t" + gateway.REQUEST_PATH])
        with self.assertRaises(gateway.BadPrTask):
            gateway.validate_request(
                gateway.TITLE_PREFIX+"gateway-selftest", b"x"*1000,
                ["A\t" + gateway.REQUEST_PATH])

    def test_reject_corrupted_utf8_json(self):
        with self.assertRaises(gateway.BadPrTask):
            gateway.validate_request(
                gateway.TITLE_PREFIX+"gateway-selftest", b"\xff\x00",
                ["A\t" + gateway.REQUEST_PATH])


class GitDataPolicy(unittest.TestCase):
    def test_frozen_base_and_head_readonly_commands(self):
        event = request_event(task="pr370-artifact-audit")
        exact = good_task("pr370-artifact-audit")
        called = []

        def fake_git(*args):
            called.append(args)
            table = {
                ("remote", "get-url", "origin"):
                    ("https://github.com/" + gateway.REPO + ".git\n").encode(),
                ("rev-parse", "HEAD"): (BASE+"\n").encode(),
                ("fetch", "--no-tags", "origin", HEAD): b"",
                ("rev-parse", "FETCH_HEAD"): (HEAD+"\n").encode(),
                ("diff", "--no-ext-diff", "--name-status", "--no-renames",
                 BASE, HEAD, "--"): ("A\t"+gateway.REQUEST_PATH+"\n").encode(),
                ("cat-file", "-s", HEAD+":"+gateway.REQUEST_PATH):
                    (str(len(exact))+"\n").encode(),
                ("cat-file", "-t", HEAD+":"+gateway.REQUEST_PATH): b"blob\n",
                ("ls-tree", HEAD, "--", gateway.REQUEST_PATH):
                    ("100644 blob " + "c"*40+"\t"+gateway.REQUEST_PATH+"\n").encode(),
                ("show", HEAD+":"+gateway.REQUEST_PATH): exact,
            }
            self.assertIn(args, table)
            return table[args]

        with patch.object(gateway, "safe_git", side_effect=fake_git):
            self.assertEqual(gateway.select_task_from_checkout(
                "pull_request_target", event), "pr370-artifact-audit")
        self.assertTrue(all(cmd[0] not in ("checkout", "reset", "merge", "rebase")
                            for cmd in called))

    def test_untrusted_checkout_base_fails_before_head_use(self):
        with patch.object(gateway, "safe_git") as fake:
            fake.side_effect = [
                ("https://github.com/" + gateway.REPO).encode(),
                b"0"*40+b"\n",
            ]
            with self.assertRaises(gateway.BadPrTask):
                gateway.select_task_from_checkout(
                    "pull_request_target", request_event())
            self.assertEqual(fake.call_count, 2)

    def test_git_read_rejects_error(self):
        p = type("P", (), {"returncode":128, "stdout":b"", "stderr":b""})()
        with patch.object(gateway.subprocess, "run", return_value=p):
            with self.assertRaises(gateway.BadPrTask):
                gateway.safe_git("show", "invalid-ref")


if __name__ == "__main__":
    unittest.main()
