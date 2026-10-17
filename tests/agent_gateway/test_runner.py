"""Public, no-secret tests for the v0.1 read-only Gateway."""
import hashlib
import importlib.util
import io
from pathlib import Path
import tarfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "tools" / "agent_gateway" / "runner.py"
spec = importlib.util.spec_from_file_location("aios_remote_agent_gateway", RUNNER)
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)


def sample_archive(*, wrong_sha=False, wrong_mode=False, link=False,
                   traversal=False, duplicate=False):
    manifest = b'{"test":"public-synthetic"}'
    inventory = {}
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        for index in range(22):
            name = ("harness/IDENTITY.json" if index == 0
                    else f"harness/r005/sample_{index:02d}.py")
            if traversal and index == 1:
                name = "harness/../../escape.py"
            if duplicate and index == 2:
                name = "harness/r005/sample_01.py"
            data = manifest if index == 0 else f"# harmless {index}\n".encode()
            info = tarfile.TarInfo(name)
            info.uid = info.gid = info.mtime = 0
            info.mode = 0o755 if wrong_mode and index == 1 else 0o644
            info.size = len(data)
            if link and index == 1:
                info.type = tarfile.SYMTYPE
                info.linkname = "unexpected"
                info.size = 0
            else:
                inventory[name] = {
                    "mode": 0o644, "size": len(data),
                    "sha256": gateway.digest(data),
                }
                if wrong_sha and index == 1:
                    inventory[name]["sha256"] = "0" * 64
            archive.addfile(info, None if info.issym() else io.BytesIO(data))
    return stream.getvalue(), inventory, gateway.digest(manifest)


class TaskPolicyTests(unittest.TestCase):
    def test_allowlisted_task_names_are_fixed(self):
        self.assertEqual(gateway.selftest()["allowlisted_tasks"], list(gateway.TASKS))
        self.assertEqual(len(gateway.TASKS), 5)

    def test_source_scope_accepts_only_approved_harness_and_evidence(self):
        gateway.check_changed_paths([
            gateway.PACKET, gateway.ARTIFACT, gateway.IDENTITY,
            "reviews/C15_RERUN005_SIGNED_TTYLESS_WINDOW66/README.md",
        ])

    def test_source_scope_rejects_core_or_tests(self):
        for unsafe in (
            "src/aios_core/runtime.py", "tools/c15_persistence/backend.py",
            "tests/test_existing.py", ".github/workflows/privileged.yml",
            "reviews/internal_habitation/c15-rcc/v1/sealed_fixture.json",
        ):
            with self.subTest(path=unsafe):
                with self.assertRaises(gateway.GateFailure):
                    gateway.check_changed_paths([
                        gateway.PACKET, gateway.ARTIFACT, gateway.IDENTITY, unsafe
                    ])

    def test_scope_rejects_empty_duplicate_and_missing(self):
        for items in ([], [gateway.PACKET], [gateway.PACKET] * 2):
            with self.assertRaises(gateway.GateFailure):
                gateway.check_changed_paths(items)

    def test_argument_parser_rejects_arbitrary_commands(self):
        with self.assertRaises(SystemExit) as caught:
            gateway.main(["--task", "echo-malicious-shell"])
        self.assertEqual(caught.exception.code, 2)

    def test_only_frozen_commit_and_artifact_are_supported(self):
        self.assertEqual(gateway.HEAD,
                         "6fb725407569bc719c049587f67fe65e797eb734")
        self.assertEqual(gateway.PARENT,
                         "9d3b19b0e7bf090e5d472d9781b9156f73ea2088")


class ArchiveAuditTests(unittest.TestCase):
    def test_valid_synthetic_regular_archive(self):
        raw, inventory, fake_pin = sample_archive()
        with mock.patch.object(gateway, "EXPECTED_IDENTITY", fake_pin):
            result = gateway.audit_tar(raw, inventory)
        self.assertEqual(result["member_count"], 22)

    def test_reject_tampered_sha(self):
        raw, inventory, fake_pin = sample_archive(wrong_sha=True)
        with mock.patch.object(gateway, "EXPECTED_IDENTITY", fake_pin):
            with self.assertRaises(gateway.GateFailure):
                gateway.audit_tar(raw, inventory)

    def test_reject_mode_mismatch(self):
        raw, inventory, fake_pin = sample_archive(wrong_mode=True)
        with mock.patch.object(gateway, "EXPECTED_IDENTITY", fake_pin):
            with self.assertRaises(gateway.GateFailure):
                gateway.audit_tar(raw, inventory)

    def test_reject_symlink(self):
        raw, inventory, fake_pin = sample_archive(link=True)
        with mock.patch.object(gateway, "EXPECTED_IDENTITY", fake_pin):
            with self.assertRaises(gateway.GateFailure):
                gateway.audit_tar(raw, inventory)

    def test_reject_path_traversal(self):
        raw, inventory, fake_pin = sample_archive(traversal=True)
        with mock.patch.object(gateway, "EXPECTED_IDENTITY", fake_pin):
            with self.assertRaises(gateway.GateFailure):
                gateway.audit_tar(raw, inventory)

    def test_reject_duplicate(self):
        raw, inventory, fake_pin = sample_archive(duplicate=True)
        with mock.patch.object(gateway, "EXPECTED_IDENTITY", fake_pin):
            with self.assertRaises(gateway.GateFailure):
                gateway.audit_tar(raw, inventory)

    def test_reject_invalid_archive_bytes(self):
        with self.assertRaises(gateway.GateFailure):
            gateway.audit_tar(b"not a tar archive", {
                f"harness/r005/x{i}.py": {"mode": 0o644,
                                          "size": 0, "sha256": "0" * 64}
                for i in range(22)
            })


if __name__ == "__main__":
    unittest.main()
