from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from aios_core.contracts.enums import SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.storage.sqlite_store import SQLiteWorldStore


FROZEN_FIXTURE_SHA256 = "sha256:1fb973499664d0d71d94a7b94071e3d7210395ea6a54ec4dcbb1ba115d069253"
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
        self.repo_root = Path(__file__).resolve().parents[5]
        self.root = Path(self.temp.name) / "v2"
        shutil.copytree(source_root, self.root)
        self.operator = self.root / "release" / "release_operator.py"
        self.adapter = self.root / "release" / "mechanical_ingest_adapter.py"
        self.state = Path(self.temp.name) / "release_state.json"
        self.world_db = Path(self.temp.name) / "private_world.db"
        self.fixture_path = self.root / "fixture" / "sealed_fixture.json"
        self.manifest_path = self.root / "fixture" / "fixture_manifest.json"
        self.evaluator_path = self.root / "evaluator" / "EVALUATOR_ONLY_design_notes.md"
        self.fixture = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        self.env = os.environ.copy()
        src = str(self.repo_root / "src")
        self.env["PYTHONPATH"] = src + (
            os.pathsep + self.env["PYTHONPATH"]
            if self.env.get("PYTHONPATH")
            else ""
        )

        spec = importlib.util.spec_from_file_location(
            "c14_mechanical_ingest_adapter_testcopy",
            self.adapter,
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load mechanical ingest adapter")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.adapter_module = module

    def tearDown(self) -> None:
        self.temp.cleanup()

    def event_projection(self, sequence: int) -> dict:
        event = self.fixture["events"][sequence - 1]
        return {key: event[key] for key in VISIBLE_KEYS}

    def run_op(self, *args: str, ok: bool = True) -> subprocess.CompletedProcess[str]:
        proc = subprocess.run(
            [sys.executable, str(self.operator), *args],
            text=True,
            capture_output=True,
            check=False,
            env=self.env,
        )
        if ok and proc.returncode != 0:
            self.fail(f"operator failed: {proc.stderr}")
        if not ok and proc.returncode == 0:
            self.fail(f"operator unexpectedly succeeded: {proc.stdout}")
        return proc

    def run_ingest(
        self,
        event: dict,
        *,
        world_db: Path | None = None,
        ok: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        target = world_db or self.world_db
        proc = subprocess.run(
            [
                sys.executable,
                str(self.adapter),
                "--world-db",
                str(target),
                "--event-file",
                "-",
            ],
            input=json.dumps(event, ensure_ascii=False),
            text=True,
            capture_output=True,
            check=False,
            env=self.env,
        )
        if ok and proc.returncode != 0:
            self.fail(f"ingest adapter failed: {proc.stderr}")
        if not ok and proc.returncode == 0:
            self.fail(f"ingest adapter unexpectedly succeeded: {proc.stdout}")
        return proc

    def init_a(self) -> None:
        self.run_op("init", "--phase", "A", "--state", str(self.state))

    def reveal(self, phase: str) -> dict:
        proc = self.run_op("reveal", "--phase", phase, "--state", str(self.state))
        return json.loads(proc.stdout)

    def ingest(self, event: dict | None = None) -> dict:
        event = event or self.event_projection(1)
        return json.loads(self.run_ingest(event).stdout)

    def ack(
        self,
        phase: str,
        event: dict,
        ingest_ref: str,
        *,
        world_db: Path | None = None,
        ok: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        return self.run_op(
            "ack",
            "--phase",
            phase,
            "--state",
            str(self.state),
            "--world-db",
            str(world_db or self.world_db),
            "--sequence",
            str(event["sequence"]),
            "--event-id",
            event["event_id"],
            "--ingest-ref",
            ingest_ref,
            ok=ok,
        )

    def exact_receipt(self, event: dict, ingest: dict, *, world_db: Path | None = None) -> dict:
        target = world_db or self.world_db
        object_id, revision_text = ingest["ingest_ref"].rsplit("@", 1)
        revision = int(revision_text)
        record = SQLiteWorldStore(target).object_revision_record(
            object_id,
            revision=revision,
        )
        return {
            "fixture_sha256": self.manifest["fixture_sha256"],
            "sequence": event["sequence"],
            "event_id": event["event_id"],
            "occurred_at": event["occurred_at"],
            "ingest_ref": ingest["ingest_ref"],
            "ingest_object_id": object_id,
            "ingest_revision": revision,
            "ingest_world_revision": int(record["world_revision"]),
            "ingest_source_class": str(record["source_class"]),
            "fixture_payload_sha256": ingest["fixture_payload_sha256"],
            "fixture_projection_sha256": ingest["fixture_projection_sha256"],
        }

    def seed_a_state_with_real_world(self, last_acked: int) -> None:
        receipts = []
        for sequence in range(1, last_acked + 1):
            event = self.event_projection(sequence)
            ingest = self.adapter_module.ingest_projection(self.world_db, event)
            receipts.append(self.exact_receipt(event, ingest))
        state = {
            "state_version": "c14-release-state-v3",
            "fixture_version": "c14-resident-fixture-v2",
            "schema_version": "c14-resident-event-v2",
            "release_contract_version": "c14-sequential-release-v2",
            "release_operator_version": "c14-blind-release-operator-v3",
            "fixture_sha256": self.manifest["fixture_sha256"],
            "active_phase": "A",
            "last_acked_sequence": last_acked,
            "last_acked_event_id": (
                None
                if last_acked == 0
                else self.fixture["events"][last_acked - 1]["event_id"]
            ),
            "next_sequence": last_acked + 1,
            "pending_reveal": None,
            "receipts": receipts,
        }
        self.state.write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def test_01_fixture_sha_is_frozen(self) -> None:
        digest = "sha256:" + hashlib.sha256(self.fixture_path.read_bytes()).hexdigest()
        self.assertEqual(digest, FROZEN_FIXTURE_SHA256)
        self.assertEqual(self.manifest["fixture_sha256"], FROZEN_FIXTURE_SHA256)

    def test_02_init_phase_a(self) -> None:
        proc = self.run_op("init", "--phase", "A", "--state", str(self.state))
        out = json.loads(proc.stdout)
        self.assertEqual(out["phase"], "A")
        self.assertEqual(out["next_sequence"], 1)
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(state["state_version"], "c14-release-state-v3")
        self.assertEqual(state["next_sequence"], 1)

    def test_03_reveal_cursor_1_is_blind_and_does_not_advance(self) -> None:
        self.init_a()
        proc = self.run_op("reveal", "--phase", "A", "--state", str(self.state))
        out = json.loads(proc.stdout)
        self.assertEqual(set(out), VISIBLE_KEYS)
        self.assertEqual(out["sequence"], 1)
        self.assertNotIn("phase", out)
        self.assertNotIn(
            self.fixture["events"][1]["resident_visible_payload"],
            proc.stdout,
        )
        self.assertNotIn("EVALUATOR_ONLY", proc.stdout)
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(state["next_sequence"], 1)
        self.assertEqual(state["pending_reveal"]["sequence"], 1)

    def test_04_ack_before_ingest_is_rejected_and_pending_remains(self) -> None:
        self.init_a()
        event = self.reveal("A")
        proc = self.ack("A", event, "fake_object@1", ok=False)
        self.assertEqual(proc.stdout, "")
        self.assertIn("World database does not exist", proc.stderr)
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(state["next_sequence"], 1)
        self.assertEqual(state["pending_reveal"]["event_id"], event["event_id"])

    def test_05_fake_formatted_ref_is_rejected_against_real_empty_world(self) -> None:
        SQLiteWorldStore(self.world_db)
        self.init_a()
        event = self.reveal("A")
        proc = self.ack("A", event, "fake_object@1", ok=False)
        self.assertEqual(proc.stdout, "")
        self.assertIn("exact durable ingest revision", proc.stderr)
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(state["next_sequence"], 1)

    def test_06_actual_ingest_returns_exact_durable_ref(self) -> None:
        event = self.event_projection(1)
        ingest = self.ingest(event)
        self.assertRegex(ingest["ingest_ref"], r"^obs_c14_fixture_[0-9a-f]{24}@1$")
        self.assertEqual(ingest["revision"], 1)
        self.assertGreaterEqual(ingest["world_revision"], 1)

    def test_07_reopen_world_proves_exact_revision_exists(self) -> None:
        event = self.event_projection(1)
        ingest = self.ingest(event)
        object_id, revision_text = ingest["ingest_ref"].rsplit("@", 1)
        reopened = SQLiteWorldStore(self.world_db)
        record = reopened.object_revision_record(
            object_id,
            revision=int(revision_text),
        )
        payload = reopened.get_payload(
            object_id,
            revision=int(revision_text),
        )
        self.assertEqual(record["subject_id"], "user_1")
        self.assertEqual(record["source_class"], "sensor")
        self.assertEqual(payload["metadata"]["fixture_event_id"], event["event_id"])
        self.assertEqual(payload["value"], event["resident_visible_payload"])

    def test_08_exact_ack_after_reopen_advances_one_cursor(self) -> None:
        self.init_a()
        event = self.reveal("A")
        ingest = self.ingest(event)
        SQLiteWorldStore(self.world_db).get_payload(
            ingest["object_id"],
            revision=ingest["revision"],
        )
        proc = self.ack("A", event, ingest["ingest_ref"])
        out = json.loads(proc.stdout)
        self.assertEqual(out["next_sequence"], 2)
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(state["last_acked_sequence"], 1)
        self.assertEqual(state["next_sequence"], 2)
        self.assertIsNone(state["pending_reveal"])
        receipt = state["receipts"][0]
        self.assertEqual(receipt["ingest_object_id"], ingest["object_id"])
        self.assertEqual(receipt["ingest_revision"], 1)
        self.assertEqual(receipt["ingest_ref"], ingest["ingest_ref"])

    def test_09_wrong_nonexistent_revision_is_rejected(self) -> None:
        self.init_a()
        event = self.reveal("A")
        ingest = self.ingest(event)
        wrong = ingest["ingest_ref"].rsplit("@", 1)[0] + "@2"
        proc = self.ack("A", event, wrong, ok=False)
        self.assertEqual(proc.stdout, "")
        self.assertIn("exact durable ingest revision", proc.stderr)

    def test_10_wrong_existing_revision_content_is_rejected(self) -> None:
        self.init_a()
        event = self.reveal("A")
        ingest = self.ingest(event)
        store = SQLiteWorldStore(self.world_db)
        payload = store.get_payload(ingest["object_id"], revision=1)
        observation = Observation.model_validate(payload).model_copy(
            update={
                "revision": 2,
                "value": "tampered revision content",
            }
        )
        store.commit(
            [observation],
            OperationRequest(
                operation_id="op_test_wrong_revision",
                operation_name="test.fixture.wrong_revision",
                arguments={"object_id": ingest["object_id"], "revision": 2},
                expected_world_revision=store.current_world_revision(),
                reason="mechanical regression setup",
                idempotency_key="test:fixture:wrong-revision",
                source_class=SourceClass.SENSOR,
            ),
        )
        proc = self.ack(
            "A",
            event,
            f"{ingest['object_id']}@2",
            ok=False,
        )
        self.assertEqual(proc.stdout, "")
        self.assertIn("payload mismatch", proc.stderr)

    def test_11_previous_event_ref_is_rejected_for_cursor_2(self) -> None:
        self.init_a()
        event1 = self.reveal("A")
        ingest1 = self.ingest(event1)
        self.ack("A", event1, ingest1["ingest_ref"])
        event2 = self.reveal("A")
        proc = self.ack("A", event2, ingest1["ingest_ref"], ok=False)
        self.assertEqual(proc.stdout, "")
        self.assertTrue(proc.stderr.startswith("release-operator-error: durable ingest "))
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(state["next_sequence"], 2)
        self.assertEqual(state["pending_reveal"]["event_id"], event2["event_id"])

    def test_12_other_event_ref_is_rejected(self) -> None:
        self.init_a()
        event1 = self.reveal("A")
        ingest2 = self.ingest(self.event_projection(2))
        proc = self.ack("A", event1, ingest2["ingest_ref"], ok=False)
        self.assertEqual(proc.stdout, "")
        self.assertTrue(proc.stderr.startswith("release-operator-error: durable ingest "))
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(state["next_sequence"], 1)
        self.assertEqual(state["pending_reveal"]["event_id"], event1["event_id"])

    def test_13_other_subject_real_observation_is_rejected(self) -> None:
        self.init_a()
        event = self.reveal("A")
        ingest = self.adapter_module.ingest_projection(
            self.world_db,
            event,
            subject_id="user_2",
        )
        proc = self.ack("A", event, ingest["ingest_ref"], ok=False)
        self.assertEqual(proc.stdout, "")
        self.assertIn("subject mismatch", proc.stderr)

    def _assert_modified_projection_rejected(
        self,
        field: str,
        value,
        expected_error: str,
    ) -> None:
        self.init_a()
        event = self.reveal("A")
        modified = dict(event)
        modified[field] = value
        ingest = self.ingest(modified)
        proc = self.ack("A", event, ingest["ingest_ref"], ok=False)
        self.assertEqual(proc.stdout, "")
        self.assertIn(expected_error, proc.stderr)

    def test_14_payload_mismatch_is_rejected(self) -> None:
        self._assert_modified_projection_rejected(
            "resident_visible_payload",
            "机械测试中的不同 payload",
            "payload mismatch",
        )

    def test_15_timestamp_mismatch_is_rejected(self) -> None:
        self._assert_modified_projection_rejected(
            "occurred_at",
            "2026-10-01T07:13:00-07:00",
            "timestamp mismatch",
        )

    def test_16_dimension_mismatch_is_rejected(self) -> None:
        self._assert_modified_projection_rejected(
            "dimension",
            "dim:wrong_dimension",
            "binding mismatch: dimension",
        )

    def test_17_source_kind_mismatch_is_rejected(self) -> None:
        self._assert_modified_projection_rejected(
            "source_kind",
            "wrong_source",
            "source_kind mismatch",
        )

    def test_18_source_class_mismatch_uses_commit_provenance(self) -> None:
        self._assert_modified_projection_rejected(
            "source_class",
            "USER",
            "source_class mismatch",
        )

    def test_19_modality_mismatch_is_rejected(self) -> None:
        self._assert_modified_projection_rejected(
            "modality",
            "wrong_modality",
            "modality mismatch",
        )

    def test_20_success_receipt_can_be_reverified_from_world(self) -> None:
        self.init_a()
        event = self.reveal("A")
        ingest = self.ingest(event)
        self.ack("A", event, ingest["ingest_ref"])
        state = json.loads(self.state.read_text(encoding="utf-8"))
        receipt = state["receipts"][0]
        reopened = SQLiteWorldStore(self.world_db)
        record = reopened.object_revision_record(
            receipt["ingest_object_id"],
            revision=receipt["ingest_revision"],
        )
        payload = reopened.get_payload(
            receipt["ingest_object_id"],
            revision=receipt["ingest_revision"],
        )
        self.assertEqual(record["world_revision"], receipt["ingest_world_revision"])
        self.assertEqual(payload["metadata"]["fixture_event_id"], receipt["event_id"])
        self.assertEqual(
            payload["metadata"]["fixture_payload_sha256"],
            receipt["fixture_payload_sha256"],
        )

    def test_21_skip_ack_is_rejected(self) -> None:
        self.init_a()
        event = self.reveal("A")
        ingest = self.ingest(event)
        proc = self.run_op(
            "ack",
            "--phase",
            "A",
            "--state",
            str(self.state),
            "--world-db",
            str(self.world_db),
            "--sequence",
            "2",
            "--event-id",
            self.fixture["events"][1]["event_id"],
            "--ingest-ref",
            ingest["ingest_ref"],
            ok=False,
        )
        self.assertEqual(proc.stdout, "")
        self.assertEqual(
            json.loads(self.state.read_text(encoding="utf-8"))["next_sequence"],
            1,
        )

    def test_22_repeat_ack_is_rejected(self) -> None:
        self.init_a()
        event = self.reveal("A")
        ingest = self.ingest(event)
        self.ack("A", event, ingest["ingest_ref"])
        proc = self.ack("A", event, ingest["ingest_ref"], ok=False)
        self.assertEqual(proc.stdout, "")
        self.assertEqual(
            json.loads(self.state.read_text(encoding="utf-8"))["next_sequence"],
            2,
        )

    def test_23_cursor_24_exact_durable_ack_moves_to_25(self) -> None:
        self.seed_a_state_with_real_world(23)
        event24 = self.reveal("A")
        self.assertEqual(event24["sequence"], 24)
        ingest24 = self.ingest(event24)
        self.ack("A", event24, ingest24["ingest_ref"])
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(state["last_acked_sequence"], 24)
        self.assertEqual(state["next_sequence"], 25)
        self.assertEqual(
            state["receipts"][23]["ingest_ref"],
            ingest24["ingest_ref"],
        )

    def test_24_phase_a_reveal_25_is_rejected(self) -> None:
        self.seed_a_state_with_real_world(23)
        event24 = self.reveal("A")
        ingest24 = self.ingest(event24)
        self.ack("A", event24, ingest24["ingest_ref"])
        proc = self.run_op(
            "reveal",
            "--phase",
            "A",
            "--state",
            str(self.state),
            ok=False,
        )
        self.assertEqual(proc.stdout, "")
        self.assertIn("cursor 25 is forbidden", proc.stderr)

    def test_25_phase_b_requires_exact_handoff_then_reveals_25(self) -> None:
        self.init_a()
        early = self.run_op(
            "init",
            "--phase",
            "B",
            "--state",
            str(self.state),
            ok=False,
        )
        self.assertEqual(early.stdout, "")
        self.assertIn("cursor 25", early.stderr)

        self.state.unlink()
        self.seed_a_state_with_real_world(23)
        event24 = self.reveal("A")
        ingest24 = self.ingest(event24)
        self.ack("A", event24, ingest24["ingest_ref"])
        init_b = self.run_op(
            "init",
            "--phase",
            "B",
            "--state",
            str(self.state),
        )
        self.assertEqual(json.loads(init_b.stdout)["next_sequence"], 25)
        event25 = self.reveal("B")
        self.assertEqual(event25["sequence"], 25)
        self.assertEqual(event25["event_id"], "c14resv2-025")
        self.assertNotIn("phase", event25)

    def test_26_future_payload_and_evaluator_content_never_reveal(self) -> None:
        marker = "EVALUATOR_SENTINEL_MUST_NEVER_BE_RELEASED"
        with self.evaluator_path.open("a", encoding="utf-8") as handle:
            handle.write("\n" + marker + "\n")
        self.init_a()
        proc = self.run_op(
            "reveal",
            "--phase",
            "A",
            "--state",
            str(self.state),
        )
        out = json.loads(proc.stdout)
        self.assertEqual(set(out), VISIBLE_KEYS)
        self.assertNotIn(marker, proc.stdout)
        self.assertNotIn(
            self.fixture["events"][1]["resident_visible_payload"],
            proc.stdout,
        )
        self.assertNotIn("phase", out)

    def test_27_digest_mismatch_fails_closed_without_changing_frozen_source(self) -> None:
        raw = self.fixture_path.read_text(encoding="utf-8")
        self.fixture_path.write_text(
            raw.replace("7小时44分", "7小时45分", 1),
            encoding="utf-8",
        )
        proc = self.run_op(
            "init",
            "--phase",
            "A",
            "--state",
            str(self.state),
            ok=False,
        )
        self.assertEqual(proc.stdout, "")
        self.assertIn("fixture digest mismatch", proc.stderr)

    def test_28_operator_or_adapter_version_mismatch_fails_closed(self) -> None:
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        manifest["release_operator_version"] = "wrong"
        self.manifest_path.write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )
        proc = self.run_op(
            "init",
            "--phase",
            "A",
            "--state",
            str(self.state),
            ok=False,
        )
        self.assertEqual(proc.stdout, "")
        self.assertIn("release operator version mismatch", proc.stderr)

    def test_29_manifest_fixture_subject_is_frozen_for_ack(self) -> None:
        self.assertEqual(self.manifest["subject_id"], "user_1")
        self.assertEqual(
            self.manifest["release_operator_version"],
            "c14-blind-release-operator-v3",
        )
        self.assertEqual(
            self.manifest["ingest_adapter_version"],
            "c14-mechanical-ingest-adapter-v1",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
