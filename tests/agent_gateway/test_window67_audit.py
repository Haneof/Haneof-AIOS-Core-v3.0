"""Only synthetic fixtures. Never execute or materialize historic evidence."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "tools" / "agent_gateway" / "window67_audit.py"
spec = importlib.util.spec_from_file_location("aios_window67_static_verifier", MODULE)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

BASE = gate.WINDOW67_BASE
MINIMUM = (
    "WINDOW67_FORMAL_SECURITY_REPORT.md",
    "WINDOW67_SECURITY_BLOCKERS.md",
    "WINDOW67_TEST_RESULTS.json",
    "WINDOW67_EXACT_IDENTITY.json",
    "raw/original38.xml",
    "raw/parent-original38.xml",
)


def make_manifest():
    blobs = {p: (p + " synthetic test bytes").encode() for p in MINIMUM}
    manifest = {
        name: {"size": len(value), "sha256": hashlib.sha256(value).hexdigest()}
        for name, value in blobs.items()
    }
    raw = json.dumps(manifest, sort_keys=True).encode()
    return blobs, raw


def suite(count, failing_names=()):
    failing_names = list(failing_names)
    cases = [
        {"id": "module::passing_case_" + str(i), "name": "passing_case_" + str(i),
         "outcome": "PASS"}
        for i in range(count - len(failing_names))
    ]
    cases += [{"id": "module::" + name, "name": name, "outcome": "FAIL"}
              for name in failing_names]
    return {"tests": count, "pass": count - len(failing_names),
            "fail": len(failing_names), "skip": 0,
            "exit_code": 1 if failing_names else 0, "cases": cases}


def sample_ledger():
    failures = list(gate.FAIL_NAMES)
    suites = {
        "original38": suite(38, failures),
        "parent-original38": suite(38, failures),
        "window55": suite(33),
        "window57": suite(29),
    }
    status = {
        "WINDOW": 67, "CANDIDATE_HEAD": "6fb725407569bc719c049587f67fe65e797eb734",
        "FORMAL_DISPOSITION": "FORMAL_VALIDATION_FAIL", "DO_NOT_MERGE": "YES",
        "INDEPENDENT_ACCEPTANCE": "NOT_STARTED", "REAL_RESIDENT_STARTED": "NO",
        "CURSOR_1_REVEALED": "NO",
        "ORIGINAL_38": "31 PASS / 7 FAIL / 0 SKIP",
        "WINDOW55_REGRESSION": "33 PASS / 0 FAIL",
        "WINDOW57_REGRESSION": "29 PASS / 0 FAIL",
        "ENROLLMENT_AUTHORITY": "BLOCKED",
        "SIGNED_RESPONSE_AUTHORIZATION": "BLOCKED",
        "PM54_BLK_001": "UNVERIFIED", "PM54_BLK_002": "UNVERIFIED",
        "PM54_BLK_003": "UNVERIFIED",
        "PUBLISHER_IMPORT_EQUIVALENCE": "UNVERIFIED",
    }
    engineering = {
        key: {"tests": 38, "pass": 31, "fail": 7,
              "skip": 0, "failure_names": failures}
        for key in ("ORIGINAL_38", "BASE_ORIGINAL_38")
    }
    for key, count in (("WINDOW55", 33), ("WINDOW57", 29)):
        engineering[key] = {
            "tests": count, "pass": count, "fail": 0, "skip": 0, "failure_names": []
        }
    author = {"regression": engineering, "FORMAL_SECURITY_VALIDATION": "PENDING",
              "PUBLISHER_IMPORT_EQUIVALENCE": "UNVERIFIED"}
    return {"status": status, "suites": suites}, author


class ManifestTests(unittest.TestCase):
    def test_minimal_closed_fixture(self):
        blobs, raw = make_manifest()
        manifest = gate.validate_manifest(raw, digest=gate.sha(raw),
                                          count=len(blobs))
        paths = [BASE + "/" + p for p in blobs] + [BASE + "/SHA256.json"]
        result = gate.verify_manifest_members(manifest, paths, blobs.__getitem__)
        self.assertEqual(result["file_count"], len(blobs))

    def test_mismatched_manifest_pin_rejected(self):
        _, raw = make_manifest()
        with self.assertRaises(gate.EvidenceGateError):
            gate.validate_manifest(raw)

    def test_duplicate_json_manifest_key_rejected(self):
        _, raw = make_manifest()
        duplicate = b'{"raw/original38.xml":{"size":0,"sha256":"' + \
                    b"0" * 64 + b'"},"raw/original38.xml":{"size":0,"sha256":"' + \
                    b"0" * 64 + b'"}}'
        with self.assertRaises(gate.EvidenceGateError):
            gate.validate_manifest(duplicate, digest=gate.sha(duplicate), count=1)

    def test_invalid_manifest_path_rejected(self):
        blobs, raw = make_manifest()
        doc = json.loads(raw)
        doc["raw/../../escape.sh"] = doc.pop("raw/original38.xml")
        changed = json.dumps(doc).encode()
        with self.assertRaises(gate.EvidenceGateError):
            gate.validate_manifest(changed, digest=gate.sha(changed),
                                   count=len(blobs))

    def test_unexpected_git_tracked_path_rejected(self):
        blobs, raw = make_manifest()
        manifest = gate.validate_manifest(raw, digest=gate.sha(raw), count=len(blobs))
        paths = [BASE + "/" + p for p in blobs] + [
            BASE + "/SHA256.json", BASE + "/unexpected.txt"
        ]
        with self.assertRaises(gate.EvidenceGateError):
            gate.verify_manifest_members(manifest, paths, blobs.__getitem__)

    def test_member_tamper_rejected(self):
        blobs, raw = make_manifest()
        manifest = gate.validate_manifest(raw, digest=gate.sha(raw), count=len(blobs))
        paths = [BASE + "/" + p for p in blobs] + [BASE + "/SHA256.json"]
        blobs["raw/original38.xml"] += b" modified"
        with self.assertRaises(gate.EvidenceGateError):
            gate.verify_manifest_members(manifest, paths, blobs.__getitem__)

    def test_required_evidence_missing_rejected(self):
        blobs, _ = make_manifest()
        del blobs["WINDOW67_FORMAL_SECURITY_REPORT.md"]
        raw = json.dumps({
            name: {"size": len(value), "sha256": gate.sha(value)}
            for name, value in blobs.items()
        }).encode()
        with self.assertRaises(gate.EvidenceGateError):
            gate.validate_manifest(raw, digest=gate.sha(raw), count=len(blobs))

    def test_oversized_identity_claim_rejected(self):
        blobs, raw = make_manifest()
        doc = json.loads(raw)
        doc["raw/original38.xml"]["size"] = 1_000_000
        changed = json.dumps(doc).encode()
        with self.assertRaises(gate.EvidenceGateError):
            gate.validate_manifest(changed, digest=gate.sha(changed),
                                   count=len(blobs))


class BindingLedgerTests(unittest.TestCase):
    def verify(self, status, author):
        return gate.validate_binding_ledger(
            status, author, "6fb725407569bc719c049587f67fe65e797eb734"
        )

    def test_frozen_failure_ledger_and_open_gate(self):
        status, author = sample_ledger()
        result = self.verify(status, author)
        self.assertEqual(result["original38"]["fail"], 7)
        self.assertEqual(result["binding_failure_gate"], "OPEN")
        self.assertEqual(result["window67_formal_disposition"],
                         "FORMAL_VALIDATION_FAIL")
        self.assertTrue(result["historical_evidence_review_only"])

    def test_false_formal_pass_rejected(self):
        status, author = sample_ledger()
        status["status"]["FORMAL_DISPOSITION"] = "FORMAL_VALIDATION_PASS"
        with self.assertRaises(gate.EvidenceGateError):
            self.verify(status, author)

    def test_false_closed_historical_gate_rejected(self):
        status, author = sample_ledger()
        status["status"]["PM54_BLK_001"] = "CLOSED"
        with self.assertRaises(gate.EvidenceGateError):
            self.verify(status, author)

    def test_missing_legacy_regression_rejected(self):
        status, author = sample_ledger()
        status["suites"]["original38"]["fail"] = 0
        with self.assertRaises(gate.EvidenceGateError):
            self.verify(status, author)

    def test_exact_failure_name_set_required(self):
        status, author = sample_ledger()
        status["suites"]["original38"]["cases"][-1]["name"] = "unrecognized_failure"
        with self.assertRaises(gate.EvidenceGateError):
            self.verify(status, author)

    def test_parent_candidate_failure_difference_rejected(self):
        status, author = sample_ledger()
        status["suites"]["parent-original38"]["cases"][-1]["name"] = "other_fail"
        with self.assertRaises(gate.EvidenceGateError):
            self.verify(status, author)

    def test_author_declaration_mismatch_rejected(self):
        status, author = sample_ledger()
        author["regression"]["ORIGINAL_38"]["failure_names"].append("extra_failure")
        with self.assertRaises(gate.EvidenceGateError):
            self.verify(status, author)

    def test_skipped_case_rejected(self):
        status, author = sample_ledger()
        status["suites"]["original38"]["cases"][0]["outcome"] = "SKIP"
        with self.assertRaises(gate.EvidenceGateError):
            self.verify(status, author)

    def test_duplicate_case_id_rejected(self):
        status, author = sample_ledger()
        cases = status["suites"]["original38"]["cases"]
        cases[-1]["id"] = cases[-2]["id"]
        with self.assertRaises(gate.EvidenceGateError):
            self.verify(status, author)

    def test_engineer_selftest_cannot_replace_independent_validation(self):
        status, author = sample_ledger()
        author["FORMAL_SECURITY_VALIDATION"] = "PASS"
        with self.assertRaises(gate.EvidenceGateError):
            self.verify(status, author)


if __name__ == "__main__":
    unittest.main()
