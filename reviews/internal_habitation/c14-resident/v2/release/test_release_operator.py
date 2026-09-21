from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


VISIBLE_KEYS = {
    "event_id",
    "sequence",
    "occurred_at",
    "dimension",
    "source_kind",
    "source_class",
    "modality",
    "resident_visible_payload",
}


class ReleaseOperatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        source_root = Path(__file__).resolve().parents[1]
        self.root = Path(self.temp.name) / "v2"
        shutil.copytree(source_root, self.root)
        self.operator = self.root / "release" / "release_operator.py"
        self.state = Path(self.temp.name) / "release_state.json"
        self.fixture_path = self.root / "fixture" / "sealed_fixture.json"
        self.manifest_path = self.root / "fixture" / "fixture_manifest.json"
        self.evaluator_path = self.root / "evaluator" / "EVALUATOR_ONLY_design_notes.md"
        self.fixture = json.loads(self.fixture_path.read_text(encoding="utf-8"))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_op(self, *args: str, ok: bool = True) -> subprocess.CompletedProcess[str]:
        proc = subprocess.run(
            [sys.executable, str(self.operator), *args],
            text=True,
            capture_output=True,
            check=False,
        )
        if ok and proc.returncode != 0:
            self.fail(f"operator failed: {proc.stderr}")
        if not ok and proc.returncode == 0:
            self.fail(f"operator unexpectedly succeeded: {proc.stdout}")
        return proc

    def init_a(self) -> None:
        self.run_op("init", "--phase", "A", "--state", str(self.state))

    def reveal(self, phase: str) -> dict:
        proc = self.run_op("reveal", "--phase", phase, "--state", str(self.state))
        return json.loads(proc.stdout)

    def ack(self, phase: str, event: dict) -> dict:
        proc = self.run_op(
            "ack",
            "--phase",
            phase,
            "--state",
            str(self.state),
            "--sequence",
            str(event["sequence"]),
            "--event-id",
            event["event_id"],
            "--ingest-ref",
            f"obs_{event['sequence']:03d}@1",
        )
        return json.loads(proc.stdout)

    def advance_a_to_24(self) -> None:
        self.init_a()
        for seq in range(1, 25):
            event = self.reveal("A")
            self.assertEqual(event["sequence"], seq)
            self.ack("A", event)

    def test_01_init_phase_a(self) -> None:
        proc = self.run_op("init", "--phase", "A", "--state", str(self.state))
        out = json.loads(proc.stdout)
        self.assertEqual(out["phase"], "A")
        self.assertEqual(out["next_sequence"], 1)
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(state["next_sequence"], 1)
        self.assertEqual(state["last_acked_sequence"], 0)

    def test_02_reveal_cursor_1_is_blind_and_does_not_advance(self) -> None:
        self.init_a()
        proc = self.run_op("reveal", "--phase", "A", "--state", str(self.state))
        out = json.loads(proc.stdout)
        self.assertEqual(set(out), VISIBLE_KEYS)
        self.assertEqual(out["sequence"], 1)
        self.assertNotIn("phase", out)
        next_payload = self.fixture["events"][1]["resident_visible_payload"]
        self.assertNotIn(next_payload, proc.stdout)
        evaluator_text = self.evaluator_path.read_text(encoding="utf-8")
        self.assertTrue(evaluator_text)
        self.assertNotIn("EVALUATOR_ONLY", proc.stdout)
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(state["next_sequence"], 1)
        self.assertEqual(state["pending_reveal"]["sequence"], 1)

    def test_03_ack_advances_only_after_exact_pending_event(self) -> None:
        self.init_a()
        event = self.reveal("A")
        out = self.ack("A", event)
        self.assertEqual(out["next_sequence"], 2)
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(state["last_acked_sequence"], 1)
        self.assertEqual(state["next_sequence"], 2)
        self.assertIsNone(state["pending_reveal"])
        self.assertEqual(state["receipts"][0]["ingest_ref"], "obs_001@1")

    def test_04_skip_ack_is_rejected(self) -> None:
        self.init_a()
        event = self.reveal("A")
        proc = self.run_op(
            "ack", "--phase", "A", "--state", str(self.state),
            "--sequence", "2", "--event-id", self.fixture["events"][1]["event_id"],
            "--ingest-ref", "obs_002@1", ok=False,
        )
        self.assertEqual(proc.stdout, "")
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(state["next_sequence"], 1)
        self.assertEqual(state["pending_reveal"]["event_id"], event["event_id"])

    def test_05_repeat_ack_is_rejected(self) -> None:
        self.init_a()
        event = self.reveal("A")
        self.ack("A", event)
        proc = self.run_op(
            "ack", "--phase", "A", "--state", str(self.state),
            "--sequence", "1", "--event-id", event["event_id"],
            "--ingest-ref", "obs_001@1", ok=False,
        )
        self.assertEqual(proc.stdout, "")
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(state["next_sequence"], 2)

    def test_06_ack_without_valid_durable_ingest_ref_is_rejected(self) -> None:
        self.init_a()
        event = self.reveal("A")
        proc = self.run_op(
            "ack", "--phase", "A", "--state", str(self.state),
            "--sequence", "1", "--event-id", event["event_id"],
            "--ingest-ref", "not-durable", ok=False,
        )
        self.assertEqual(proc.stdout, "")
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(state["next_sequence"], 1)

    def test_07_digest_mismatch_fails_closed(self) -> None:
        raw = self.fixture_path.read_text(encoding="utf-8")
        self.fixture_path.write_text(raw.replace("7小时44分", "7小时45分", 1), encoding="utf-8")
        proc = self.run_op("init", "--phase", "A", "--state", str(self.state), ok=False)
        self.assertEqual(proc.stdout, "")
        self.assertIn("digest mismatch", proc.stderr)

    def test_08_phase_a_cursor_24_reveal_and_ack_to_25(self) -> None:
        self.init_a()
        for seq in range(1, 24):
            event = self.reveal("A")
            self.ack("A", event)
        event24 = self.reveal("A")
        self.assertEqual(event24["sequence"], 24)
        self.assertEqual(event24["event_id"], "c14resv2-024")
        self.ack("A", event24)
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(state["last_acked_sequence"], 24)
        self.assertEqual(state["next_sequence"], 25)

    def test_09_phase_a_reveal_25_is_rejected(self) -> None:
        self.advance_a_to_24()
        proc = self.run_op("reveal", "--phase", "A", "--state", str(self.state), ok=False)
        self.assertEqual(proc.stdout, "")
        self.assertIn("cursor 25 is forbidden", proc.stderr)

    def test_10_phase_b_requires_exact_handoff_state(self) -> None:
        self.init_a()
        proc = self.run_op("init", "--phase", "B", "--state", str(self.state), ok=False)
        self.assertEqual(proc.stdout, "")
        self.assertIn("cursor 25", proc.stderr)

    def test_11_phase_b_init_and_reveal_25(self) -> None:
        self.advance_a_to_24()
        init_b = self.run_op("init", "--phase", "B", "--state", str(self.state))
        self.assertEqual(json.loads(init_b.stdout)["next_sequence"], 25)
        event25 = self.reveal("B")
        self.assertEqual(event25["sequence"], 25)
        self.assertEqual(event25["event_id"], "c14resv2-025")
        self.assertNotIn("phase", event25)

    def test_12_phase_b_cannot_re_release_phase_a(self) -> None:
        self.advance_a_to_24()
        self.run_op("init", "--phase", "B", "--state", str(self.state))
        state = json.loads(self.state.read_text(encoding="utf-8"))
        state["next_sequence"] = 24
        state["last_acked_sequence"] = 23
        state["last_acked_event_id"] = self.fixture["events"][22]["event_id"]
        state["receipts"] = state["receipts"][:23]
        self.state.write_text(json.dumps(state), encoding="utf-8")
        proc = self.run_op("reveal", "--phase", "B", "--state", str(self.state), ok=False)
        self.assertEqual(proc.stdout, "")

    def test_13_fixture_schema_or_state_version_mismatch_fails_closed(self) -> None:
        self.init_a()
        state = json.loads(self.state.read_text(encoding="utf-8"))
        state["schema_version"] = "wrong"
        self.state.write_text(json.dumps(state), encoding="utf-8")
        proc = self.run_op("reveal", "--phase", "A", "--state", str(self.state), ok=False)
        self.assertEqual(proc.stdout, "")
        self.assertIn("schema version mismatch", proc.stderr)

    def test_14_reveal_stdout_contains_only_current_projection(self) -> None:
        self.init_a()
        proc = self.run_op("reveal", "--phase", "A", "--state", str(self.state))
        out = json.loads(proc.stdout)
        self.assertEqual(set(out), VISIBLE_KEYS)
        self.assertEqual(out, {k: self.fixture["events"][0][k] for k in VISIBLE_KEYS})
        self.assertNotIn(self.fixture["events"][1]["resident_visible_payload"], proc.stdout)
        self.assertNotIn("fixture_sha256", proc.stdout)
        self.assertNotIn("remaining", proc.stdout)
        self.assertNotIn("phase", out)

    def test_15_evaluator_material_cannot_be_emitted_by_release_command(self) -> None:
        marker = "EVALUATOR_SENTINEL_MUST_NEVER_BE_RELEASED"
        with self.evaluator_path.open("a", encoding="utf-8") as handle:
            handle.write("\n" + marker + "\n")
        self.init_a()
        proc = self.run_op("reveal", "--phase", "A", "--state", str(self.state))
        self.assertNotIn(marker, proc.stdout)
        source = self.operator.read_text(encoding="utf-8")
        self.assertNotIn("EVALUATOR_ONLY_design_notes", source)
        self.assertNotIn("/evaluator/", source)

    def test_16_manifest_digest_matches_exact_fixture_bytes(self) -> None:
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        digest = "sha256:" + hashlib.sha256(self.fixture_path.read_bytes()).hexdigest()
        self.assertEqual(manifest["fixture_sha256"], digest)

    def test_17_fixture_mechanical_shape(self) -> None:
        events = self.fixture["events"]
        self.assertEqual(len(events), 36)
        self.assertEqual([e["sequence"] for e in events], list(range(1, 37)))
        self.assertEqual(len({e["event_id"] for e in events}), 36)
        self.assertTrue(all(e["phase"] == "A" for e in events[:24]))
        self.assertTrue(all(e["phase"] == "B" for e in events[24:]))
        times = [e["occurred_at"] for e in events]
        self.assertEqual(times, sorted(times))

    def test_18_no_answer_fields_in_resident_visible_events(self) -> None:
        forbidden_fields = {
            "expected_cognition", "expected_claim", "expected_preference",
            "expected_personality", "correct_answer", "semantic_label",
        }
        for event in self.fixture["events"]:
            self.assertTrue(forbidden_fields.isdisjoint(event))
            self.assertNotIn("正例", event["resident_visible_payload"])
            self.assertNotIn("负例", event["resident_visible_payload"])
            self.assertNotIn("反例", event["resident_visible_payload"])


    def test_19_manifest_and_operator_version_mismatch_fail_closed(self) -> None:
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        manifest["release_operator_version"] = "wrong-operator-version"
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        proc = self.run_op("init", "--phase", "A", "--state", str(self.state), ok=False)
        self.assertEqual(proc.stdout, "")
        self.assertIn("release operator version mismatch", proc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
