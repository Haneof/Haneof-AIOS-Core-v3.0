"""Pure, fail-closed checks over pre-existing PUBLIC Window67 evidence.

Never imports or executes candidate files; every input is a Git blob supplied
by the read-only Gateway runner. This checks frozen historical evidence and
cannot certify current/formal Resident security.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import PurePosixPath
import re
from typing import Callable


WINDOW67_HEAD = "391c4815ac77ef82cabcf13798de4d8fa8e7c0b0"
WINDOW67_TREE = "d4dc287feb2e59f42bdaadbc15cf4d3406c9845a"
WINDOW67_BRANCH = "review/window67-formal-security-evidence"
WINDOW67_BASE = "reviews/C15_RERUN005_FORMAL_SECURITY_WINDOW67"
WINDOW67_MANIFEST_SHA256 = (
    "a9acee9a91d28920d42a91ff2db35d63630331a7dd9aaa6868a725fa35d42a76"
)
WINDOW67_MEMBER_COUNT = 154
WINDOW67_MAX_MEMBER_BYTES = 128 * 1024

FAIL_NAMES = (
    "test_sigkill_after_request_never_regenerates_or_redispatches",
    "test_absent_external_response_bounded_fail_closed",
    "test_real_core_external_publisher_with_c15_remote_barriers[due]",
    "test_real_core_external_publisher_with_c15_remote_barriers[user]",
    "test_real_core_external_publisher_with_c15_remote_barriers[summary]",
    "test_real_core_external_publisher_with_c15_remote_barriers[delivered]",
    "test_signer_not_importable_in_recovery_caller",
)


class EvidenceGateError(ValueError):
    """The frozen public-evidence gate did not pass."""


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise EvidenceGateError(reason)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_object_no_duplicates(data: bytes):
    def hook(pairs):
        obj = {}
        for key, value in pairs:
            require(key not in obj, "duplicate JSON key")
            obj[key] = value
        return obj
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=hook)
    except (ValueError, UnicodeDecodeError) as exc:
        if isinstance(exc, EvidenceGateError):
            raise
        raise EvidenceGateError("invalid UTF-8 JSON") from exc


def validate_manifest(
    raw_manifest: bytes, *, digest: str = WINDOW67_MANIFEST_SHA256,
    count: int = WINDOW67_MEMBER_COUNT
) -> dict:
    require(sha(raw_manifest) == digest, "Window67 SHA256.json is not the frozen bytes")
    items = json_object_no_duplicates(raw_manifest)
    require(isinstance(items, dict) and len(items) == count,
            "Window67 member count does not equal frozen manifest")
    for name, pin in items.items():
        require(type(name) is str
                and re.fullmatch(r"[A-Za-z0-9_./-]+", name) is not None
                and not PurePosixPath(name).is_absolute()
                and all(part not in ("", ".", "..") for part in name.split("/"))
                and name != "SHA256.json",
                "unapproved Window67 evidence member")
        require(isinstance(pin, dict) and set(pin) == {"sha256", "size"}
                and type(pin["sha256"]) is str
                and re.fullmatch(r"[0-9a-f]{64}", pin["sha256"]) is not None
                and type(pin["size"]) is int
                and 0 <= pin["size"] <= WINDOW67_MAX_MEMBER_BYTES,
                "invalid Window67 member identity")
    for essential in (
        "WINDOW67_FORMAL_SECURITY_REPORT.md",
        "WINDOW67_SECURITY_BLOCKERS.md",
        "WINDOW67_TEST_RESULTS.json",
        "WINDOW67_EXACT_IDENTITY.json",
        "raw/original38.xml",
        "raw/parent-original38.xml",
    ):
        require(essential in items, "required evidence member missing: " + essential)
    return items


def verify_manifest_members(
    manifest: dict, tracked_paths: list[str],
    read_member: Callable[[str], bytes]
) -> dict:
    prefix = WINDOW67_BASE + "/"
    expected = {prefix + name for name in manifest} | {prefix + "SHA256.json"}
    require(len(tracked_paths) == len(set(tracked_paths)),
            "duplicate git tracked evidence paths")
    require(set(tracked_paths) == expected,
            "tracked Window67 files differ from closed frozen manifest")
    total_bytes = 0
    for name in sorted(manifest):
        content = read_member(name)
        pin = manifest[name]
        require(type(content) is bytes
                and len(content) == pin["size"]
                and sha(content) == pin["sha256"],
                "Window67 hash mismatch: " + name)
        total_bytes += len(content)
    return {
        "source": "WINDOW67_FROZEN_EVIDENCE_ONLY",
        "evidence_head": WINDOW67_HEAD,
        "file_count": len(manifest),
        "total_verified_bytes": total_bytes,
        "manifest_sha256": WINDOW67_MANIFEST_SHA256,
        "immutable_members": "PASS",
        "formal_security_retested": False,
    }


def check_suite(name: str, suite: dict, count: int, passed: int, failed: int) -> set:
    require(isinstance(suite, dict), "missing regression suite: " + name)
    require(
        suite.get("tests") == count
        and suite.get("pass") == passed
        and suite.get("fail") == failed
        and suite.get("skip") == 0
        and suite.get("exit_code") == (1 if failed else 0),
        "frozen regression counts differ in " + name,
    )
    cases = suite.get("cases")
    require(type(cases) is list and len(cases) == count, "case-count mismatch in " + name)
    require(
        len({case.get("id") for case in cases if isinstance(case, dict)}) == count,
        "duplicate or malformed case identities in " + name,
    )
    outcomes = [case.get("outcome") for case in cases]
    require(
        outcomes.count("PASS") == passed
        and outcomes.count("FAIL") == failed
        and set(outcomes) <= {"PASS", "FAIL"},
        "individual outcomes differ in " + name,
    )
    failures = [case.get("name") for case in cases if case.get("outcome") == "FAIL"]
    require(len(failures) == len(set(failures)), "repeated failure names in " + name)
    return set(failures)


def validate_binding_ledger(status_doc: dict, engineer_doc: dict, candidate_head: str) -> dict:
    require(type(status_doc) is dict and type(engineer_doc) is dict,
            "regression status must be JSON objects")
    status = status_doc.get("status")
    suites = status_doc.get("suites")
    require(isinstance(status, dict) and isinstance(suites, dict),
            "missing formal security status or suites")
    require(
        status.get("WINDOW") == 67
        and status.get("CANDIDATE_HEAD") == candidate_head
        and status.get("FORMAL_DISPOSITION") == "FORMAL_VALIDATION_FAIL"
        and status.get("DO_NOT_MERGE") == "YES"
        and status.get("INDEPENDENT_ACCEPTANCE") == "NOT_STARTED"
        and status.get("REAL_RESIDENT_STARTED") == "NO"
        and status.get("CURSOR_1_REVEALED") == "NO"
        and status.get("ORIGINAL_38") == "31 PASS / 7 FAIL / 0 SKIP"
        and status.get("WINDOW55_REGRESSION") == "33 PASS / 0 FAIL"
        and status.get("WINDOW57_REGRESSION") == "29 PASS / 0 FAIL"
        and status.get("ENROLLMENT_AUTHORITY") == "BLOCKED"
        and status.get("SIGNED_RESPONSE_AUTHORIZATION") == "BLOCKED",
        "binding formal Window67 status differs from immutable FAIL record",
    )
    for name in ("PM54_BLK_001", "PM54_BLK_002", "PM54_BLK_003"):
        require(status.get(name) == "UNVERIFIED",
                "legacy formal security gate is not independently closed: " + name)
    require(status.get("PUBLISHER_IMPORT_EQUIVALENCE") == "UNVERIFIED",
            "publisher import equivalence status was altered")
    real_fail = check_suite("original38", suites.get("original38"), 38, 31, 7)
    parent_fail = check_suite("parent-original38", suites.get("parent-original38"), 38, 31, 7)
    require(real_fail == parent_fail == set(FAIL_NAMES),
            "exact seven binding failure names changed or disappeared")
    require(not check_suite("window55", suites.get("window55"), 33, 33, 0),
            "unexpected Window55 failures")
    require(not check_suite("window57", suites.get("window57"), 29, 29, 0),
            "unexpected Window57 failures")
    engineering = engineer_doc.get("regression")
    require(isinstance(engineering, dict), "engineer baseline missing")
    for key in ("ORIGINAL_38", "BASE_ORIGINAL_38"):
        info = engineering.get(key)
        require(isinstance(info, dict)
                and info.get("tests") == 38
                and info.get("pass") == 31
                and info.get("fail") == 7
                and info.get("skip") == 0
                and set(info.get("failure_names", ())) == real_fail,
                "engineer regression ledger mismatch: " + key)
    for key, count in (("WINDOW55", 33), ("WINDOW57", 29)):
        info = engineering.get(key)
        require(isinstance(info, dict)
                and info.get("tests") == count
                and info.get("pass") == count
                and info.get("fail") == 0
                and info.get("skip") == 0
                and info.get("failure_names") == [],
                "engineering positive-regression receipt mismatch")
    require(engineer_doc.get("FORMAL_SECURITY_VALIDATION") == "PENDING"
            and engineer_doc.get("PUBLISHER_IMPORT_EQUIVALENCE") == "UNVERIFIED",
            "engineer report must not be treated as formal PASS")
    return {
        "source": "FROZEN_WINDOW66_AND_WINDOW67_HISTORICAL_SNAPSHOTS",
        "original38": {"tests": 38, "pass": 31, "fail": 7, "skip": 0},
        "historical_binding_failures": list(FAIL_NAMES),
        "window55": {"pass": 33, "tests": 33},
        "window57": {"pass": 29, "tests": 29},
        "binding_failure_gate": "OPEN",
        "pm54_gates": "UNVERIFIED",
        "publisher_import_equivalence": "UNVERIFIED",
        "window67_formal_disposition": "FORMAL_VALIDATION_FAIL",
        "window69_formal_validation": "NOT_PERFORMED",
        "historical_evidence_review_only": True,
    }
