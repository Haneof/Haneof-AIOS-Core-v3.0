from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from aios_core.contracts.enums import ObjectType, SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent
from aios_core.ingest import ConversationIngestor
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore


FROZEN_FIXTURE_SHA256 = (
    "sha256:1fb973499664d0d71d94a7b94071e3d7210395ea6a54ec4dcbb1ba115d069253"
)
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
LEGACY_OPERATOR_VERSION = "c14-blind-release-operator-v3"
CURRENT_OPERATOR_VERSION = "c14-blind-release-operator-v4"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CanonicalConversationReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.release_dir = Path(__file__).resolve().parent
        cls.v2_root = cls.release_dir.parent
        cls.repo_root = Path(__file__).resolve().parents[5]
        cls.operator = cls.release_dir / "release_operator.py"
        cls.generic_adapter = cls.release_dir / "mechanical_ingest_adapter.py"
        cls.conversation_adapter = cls.release_dir / "canonical_conversation_ingest.py"
        cls.fixture_path = cls.v2_root / "fixture" / "sealed_fixture.json"
        cls.manifest_path = cls.v2_root / "fixture" / "fixture_manifest.json"
        cls.fixture = json.loads(cls.fixture_path.read_text(encoding="utf-8"))
        cls.manifest = json.loads(cls.manifest_path.read_text(encoding="utf-8"))

        cls.env = os.environ.copy()
        src = str(cls.repo_root / "src")
        cls.env["PYTHONPATH"] = src + (
            os.pathsep + cls.env["PYTHONPATH"]
            if cls.env.get("PYTHONPATH")
            else ""
        )

        cls.generic_module = _load_module(
            "c14_generic_adapter_for_bfix",
            cls.generic_adapter,
        )
        cls.canonical_module = _load_module(
            "c14_canonical_adapter_for_bfix",
            cls.conversation_adapter,
        )

        cls.base_temp = tempfile.TemporaryDirectory()
        base = Path(cls.base_temp.name)
        cls.base_world_a = base / "world-a-handoff.db"
        cls.base_state_a = base / "state-a-handoff.json"

        receipts = []
        for sequence in range(1, 25):
            event = cls._projection(sequence)
            ingest = cls.generic_module.ingest_projection(cls.base_world_a, event)
            object_id, revision_text = ingest["ingest_ref"].rsplit("@", 1)
            revision = int(revision_text)
            record = SQLiteWorldStore(cls.base_world_a).object_revision_record(
                object_id,
                revision=revision,
            )
            receipts.append(
                {
                    "fixture_sha256": cls.manifest["fixture_sha256"],
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
            )

        legacy_state = {
            "state_version": "c14-release-state-v3",
            "fixture_version": "c14-resident-fixture-v2",
            "schema_version": "c14-resident-event-v2",
            "release_contract_version": "c14-sequential-release-v2",
            "release_operator_version": LEGACY_OPERATOR_VERSION,
            "fixture_sha256": cls.manifest["fixture_sha256"],
            "active_phase": "A",
            "last_acked_sequence": 24,
            "last_acked_event_id": cls.fixture["events"][23]["event_id"],
            "next_sequence": 25,
            "pending_reveal": None,
            "receipts": receipts,
        }
        cls.base_state_a.write_text(
            json.dumps(legacy_state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        cls.base_world_b = base / "world-b-before-conversation.db"
        cls.base_state_b = base / "state-b-before-conversation.json"
        shutil.copy2(cls.base_world_a, cls.base_world_b)
        shutil.copy2(cls.base_state_a, cls.base_state_b)

        cls._run_static_op(
            "init",
            "--phase",
            "B",
            "--state",
            str(cls.base_state_b),
        )
        event25 = cls._run_static_reveal(cls.base_state_b)
        if event25["sequence"] != 25:
            raise AssertionError("base Phase-B state did not reveal cursor 25")
        ingest25 = cls.generic_module.ingest_projection(cls.base_world_b, event25)
        cls._run_static_op(
            "ack",
            "--phase",
            "B",
            "--state",
            str(cls.base_state_b),
            "--world-db",
            str(cls.base_world_b),
            "--sequence",
            "25",
            "--event-id",
            event25["event_id"],
            "--ingest-ref",
            ingest25["ingest_ref"],
        )
        base_state = json.loads(cls.base_state_b.read_text(encoding="utf-8"))
        if base_state["next_sequence"] != 26:
            raise AssertionError("base Phase-B state did not advance to cursor 26")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.base_temp.cleanup()

    @classmethod
    def _projection(cls, sequence: int) -> dict:
        event = cls.fixture["events"][sequence - 1]
        return {key: event[key] for key in VISIBLE_KEYS}

    @classmethod
    def _run_static_op(
        cls,
        *args: str,
        ok: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        proc = subprocess.run(
            [sys.executable, str(cls.operator), *args],
            text=True,
            capture_output=True,
            check=False,
            env=cls.env,
        )
        if ok and proc.returncode != 0:
            raise AssertionError(f"operator failed: {proc.stderr}")
        if not ok and proc.returncode == 0:
            raise AssertionError(f"operator unexpectedly succeeded: {proc.stdout}")
        return proc

    @classmethod
    def _run_static_reveal(cls, state: Path) -> dict:
        proc = cls._run_static_op(
            "reveal",
            "--phase",
            "B",
            "--state",
            str(state),
        )
        return json.loads(proc.stdout)

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.world_db = root / "world.db"
        self.state = root / "release-state.json"
        shutil.copy2(self.base_world_b, self.world_db)
        shutil.copy2(self.base_state_b, self.state)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_op(self, *args: str, ok: bool = True) -> subprocess.CompletedProcess[str]:
        return self._run_static_op(*args, ok=ok)

    def reveal26(self) -> dict:
        proc = self.run_op(
            "reveal",
            "--phase",
            "B",
            "--state",
            str(self.state),
        )
        event = json.loads(proc.stdout)
        self.assertEqual(event["sequence"], 26)
        self.assertEqual(set(event), VISIBLE_KEYS)
        return event

    def canonical_ingest(
        self,
        event: dict,
        *,
        session_id: str = "resident-b-mechanical-session",
        turn_index: int = 1,
    ) -> dict:
        proc = subprocess.run(
            [
                sys.executable,
                str(self.conversation_adapter),
                "--world-db",
                str(self.world_db),
                "--session-id",
                session_id,
                "--turn-index",
                str(turn_index),
                "--event-file",
                "-",
            ],
            input=json.dumps(event, ensure_ascii=False),
            text=True,
            capture_output=True,
            check=False,
            env=self.env,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def generic_ingest(self, event: dict) -> dict:
        return self.generic_module.ingest_projection(self.world_db, event)

    def ack_conversation(
        self,
        event: dict,
        ingest_ref: str,
        *,
        session_id: str = "resident-b-mechanical-session",
        turn_index: int = 1,
        ok: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        return self.run_op(
            "ack",
            "--phase",
            "B",
            "--state",
            str(self.state),
            "--world-db",
            str(self.world_db),
            "--sequence",
            str(event["sequence"]),
            "--event-id",
            event["event_id"],
            "--ingest-ref",
            ingest_ref,
            "--conversation-session-id",
            session_id,
            "--conversation-turn-index",
            str(turn_index),
            ok=ok,
        )

    def _manual_generic_fixture_observation(
        self,
        event: dict,
        *,
        object_id: str = "obs_bfix_generic_fixture_masquerade",
    ) -> str:
        when = datetime.fromisoformat(event["occurred_at"])
        payload_sha = self.generic_module._sha256_text(
            event["resident_visible_payload"]
        )
        projection_sha = self.generic_module._projection_sha256(event)
        obs = Observation(
            object_id=object_id,
            subject_id="user_1",
            occurred=TemporalExtent.point(when),
            learned_at=when,
            recorded_at=when,
            created_by="c14_fixture_ingest:c14-mechanical-ingest-adapter-v1",
            source_kind="conversation",
            modality="text",
            value=event["resident_visible_payload"],
            metadata={
                "dimension": "dim:conversation",
                "source_class": "user",
                "fixture_version": "c14-resident-fixture-v2",
                "fixture_sha256": FROZEN_FIXTURE_SHA256,
                "fixture_binding_version": "c14-fixture-event-binding-v1",
                "fixture_event_id": event["event_id"],
                "fixture_sequence": event["sequence"],
                "fixture_payload_sha256": payload_sha,
                "fixture_projection_sha256": projection_sha,
                "external_record_id": event["event_id"],
                "external_revision": "1",
                "occurred_at_original": event["occurred_at"],
                "mechanical_ingest": True,
            },
        )
        store = SQLiteWorldStore(self.world_db)
        store.commit(
            [obs],
            OperationRequest(
                operation_id=f"op_{object_id}",
                operation_name="test.bfix.generic_fixture_masquerade",
                arguments={"object_id": object_id},
                expected_world_revision=store.current_world_revision(),
                reason="C14-RES-B-FIX-001 generic fixture masquerade regression",
                idempotency_key=f"bfix:{object_id}",
                source_class=SourceClass.USER,
            ),
        )
        return f"{object_id}@1"

    def _manual_conversation_observation(
        self,
        event: dict,
        *,
        object_id: str,
        session_id: str,
        turn_index: int,
        role: str,
        source_class: SourceClass,
        subject_id: str = "user_1",
        text: str | None = None,
        occurred_at: datetime | None = None,
    ) -> str:
        when = occurred_at or datetime.fromisoformat(event["occurred_at"])
        obs = Observation(
            object_id=object_id,
            subject_id=subject_id,
            occurred=TemporalExtent.point(when),
            learned_at=when,
            recorded_at=when,
            created_by=f"bfix-test:{role}",
            source_kind="user_ai_interaction",
            modality="text",
            value=event["resident_visible_payload"] if text is None else text,
            metadata={
                "dimension": "dim:interaction",
                "session_id": session_id,
                "turn_index": turn_index,
                "turn_key": f"bfix-{object_id}",
                "role": role,
            },
        )
        store = SQLiteWorldStore(self.world_db)
        store.commit(
            [obs],
            OperationRequest(
                operation_id=f"op_{object_id}",
                session_id=session_id,
                operation_name="test.bfix.manual_conversation",
                arguments={"object_id": object_id},
                expected_world_revision=store.current_world_revision(),
                reason="C14-RES-B-FIX-001 fail-closed mechanical fixture",
                idempotency_key=f"bfix:{object_id}",
                source_class=source_class,
            ),
        )
        return f"{object_id}@1"

    def test_01_legacy_a_handoff_upgrades_only_at_exact_24_to_25_boundary(self) -> None:
        root = Path(self.temp.name)
        state = root / "legacy-a.json"
        shutil.copy2(self.base_state_a, state)
        out = json.loads(
            self.run_op(
                "init",
                "--phase",
                "B",
                "--state",
                str(state),
            ).stdout
        )
        self.assertEqual(out["next_sequence"], 25)
        upgraded = json.loads(state.read_text(encoding="utf-8"))
        self.assertEqual(upgraded["active_phase"], "B")
        self.assertEqual(upgraded["release_operator_version"], CURRENT_OPERATOR_VERSION)

        bad = dict(json.loads(self.base_state_a.read_text(encoding="utf-8")))
        bad["receipts"] = bad["receipts"][:23]
        bad["last_acked_sequence"] = 23
        bad["last_acked_event_id"] = self.fixture["events"][22]["event_id"]
        bad["next_sequence"] = 24
        bad_path = root / "legacy-not-handoff.json"
        bad_path.write_text(json.dumps(bad), encoding="utf-8")
        proc = self.run_op(
            "init",
            "--phase",
            "B",
            "--state",
            str(bad_path),
            ok=False,
        )
        self.assertEqual(proc.stdout, "")

    def test_02_canonical_adapter_writes_exact_user_observation(self) -> None:
        event = self.reveal26()
        ingest = self.canonical_ingest(event)
        self.assertEqual(ingest["binding_mode"], "canonical_user_turn")
        self.assertFalse(ingest["idempotent_replay"])

        reopened = SQLiteWorldStore(self.world_db)
        record = reopened.object_revision_record(ingest["object_id"], revision=1)
        payload = reopened.get_payload(ingest["object_id"], revision=1)
        self.assertEqual(record["source_class"], "user")
        self.assertEqual(payload["source_kind"], "user_ai_interaction")
        self.assertEqual(payload["modality"], "text")
        self.assertEqual(payload["metadata"]["role"], "user")
        self.assertEqual(payload["metadata"]["session_id"], "resident-b-mechanical-session")
        self.assertEqual(payload["metadata"]["turn_index"], 1)
        self.assertEqual(payload["value"], event["resident_visible_payload"])

    def test_03_exact_ack_then_run_turn_reuses_user_commit_without_duplicate(self) -> None:
        event = self.reveal26()
        session_id = "resident-b-idempotency-session"
        ingest = self.canonical_ingest(
            event,
            session_id=session_id,
            turn_index=1,
        )
        ack = self.ack_conversation(
            event,
            ingest["ingest_ref"],
            session_id=session_id,
            turn_index=1,
        )
        self.assertEqual(json.loads(ack.stdout)["next_sequence"], 27)

        store = SQLiteWorldStore(self.world_db)
        before_runtime_revision = store.current_world_revision()
        index = WorldSearchIndex(self.world_db, store=store)
        index.rebuild()

        runtime = FusedTurnRuntime(
            store=store,
            index=index,
            subject_id="user_1",
            model_handler=lambda snapshot: ModelDirective(
                response="mechanical transport response"
            ),
        )
        captured_user_commits = []
        real_commit_user_input = runtime.ingestor.commit_user_input

        def capture_commit_user_input(**kwargs):
            result = real_commit_user_input(**kwargs)
            captured_user_commits.append(result)
            return result

        runtime.ingestor.commit_user_input = capture_commit_user_input
        result = runtime.run_turn(
            session_id=session_id,
            turn_index=1,
            user_input=event["resident_visible_payload"],
            occurred_at=datetime.fromisoformat(event["occurred_at"]),
            current_topic=None,
        )

        self.assertEqual(len(captured_user_commits), 1)
        self.assertTrue(captured_user_commits[0].idempotent_replay)
        self.assertEqual(
            captured_user_commits[0].observation_id,
            ingest["object_id"],
        )
        self.assertEqual(
            result.conversation_commit.user_observation_id,
            ingest["object_id"],
        )
        self.assertEqual(
            result.conversation_commit.user_world_revision,
            ingest["world_revision"],
        )
        self.assertEqual(
            result.conversation_commit.assistant_world_revision,
            before_runtime_revision + 1,
        )
        self.assertEqual(store.current_world_revision(), before_runtime_revision + 1)

        observations = store.list_payloads(
            object_type=ObjectType.OBSERVATION,
            subject_id="user_1",
        )
        canonical_users = [
            item
            for item in observations
            if item.get("source_kind") == "user_ai_interaction"
            and (item.get("metadata") or {}).get("role") == "user"
            and (item.get("metadata") or {}).get("session_id") == session_id
            and (item.get("metadata") or {}).get("turn_index") == 1
        ]
        self.assertEqual(len(canonical_users), 1)
        self.assertEqual(canonical_users[0]["object_id"], ingest["object_id"])

        duplicate_fixture = [
            item
            for item in observations
            if (item.get("metadata") or {}).get("fixture_event_id")
            == event["event_id"]
        ]
        self.assertEqual(duplicate_fixture, [])

        assistants = [
            item
            for item in observations
            if item.get("source_kind") == "user_ai_interaction"
            and (item.get("metadata") or {}).get("role") == "assistant"
            and (item.get("metadata") or {}).get("session_id") == session_id
            and (item.get("metadata") or {}).get("turn_index") == 1
        ]
        self.assertEqual(len(assistants), 1)
        assistant_record = store.object_revision_record(
            assistants[0]["object_id"],
            revision=1,
        )
        self.assertEqual(assistant_record["source_class"], "ai_cognition")

    def test_04_generic_fixture_observation_cannot_ack_phase_b_conversation(self) -> None:
        event = self.reveal26()

        with self.assertRaisesRegex(
            Exception,
            "must use canonical_conversation_ingest.py",
        ):
            self.generic_ingest(event)

        generic_ref = self._manual_generic_fixture_observation(event)
        proc = self.ack_conversation(event, generic_ref, ok=False)
        self.assertEqual(proc.stdout, "")
        self.assertIn("canonical conversation mismatch", proc.stderr)

    def test_05_conversation_event_cannot_ack_without_canonical_fields(self) -> None:
        event = self.reveal26()
        ingest = self.canonical_ingest(event)
        proc = self.run_op(
            "ack",
            "--phase",
            "B",
            "--state",
            str(self.state),
            "--world-db",
            str(self.world_db),
            "--sequence",
            str(event["sequence"]),
            "--event-id",
            event["event_id"],
            "--ingest-ref",
            ingest["ingest_ref"],
            ok=False,
        )
        self.assertEqual(proc.stdout, "")
        self.assertIn("requires canonical conversation ack fields", proc.stderr)

    def test_06_wrong_session_and_turn_are_rejected(self) -> None:
        event = self.reveal26()
        ingest = self.canonical_ingest(event, session_id="correct-session", turn_index=3)

        wrong_session = self.ack_conversation(
            event,
            ingest["ingest_ref"],
            session_id="wrong-session",
            turn_index=3,
            ok=False,
        )
        self.assertIn("session id", wrong_session.stderr)

        wrong_turn = self.ack_conversation(
            event,
            ingest["ingest_ref"],
            session_id="correct-session",
            turn_index=4,
            ok=False,
        )
        self.assertIn("turn index", wrong_turn.stderr)

    def test_07_wrong_text_and_timestamp_are_rejected(self) -> None:
        event = self.reveal26()
        when = datetime.fromisoformat(event["occurred_at"])
        store = SQLiteWorldStore(self.world_db)

        wrong_text = ConversationIngestor(store, subject_id="user_1").commit_user_input(
            session_id="wrong-text-session",
            turn_index=1,
            user_text="different text",
            occurred_at=when,
        )
        proc_text = self.ack_conversation(
            event,
            f"{wrong_text.observation_id}@1",
            session_id="wrong-text-session",
            turn_index=1,
            ok=False,
        )
        self.assertIn("mismatch: text", proc_text.stderr)

        wrong_time = ConversationIngestor(store, subject_id="user_1").commit_user_input(
            session_id="wrong-time-session",
            turn_index=1,
            user_text=event["resident_visible_payload"],
            occurred_at=when + timedelta(minutes=1),
        )
        proc_time = self.ack_conversation(
            event,
            f"{wrong_time.observation_id}@1",
            session_id="wrong-time-session",
            turn_index=1,
            ok=False,
        )
        self.assertIn("timestamp mismatch", proc_time.stderr)

    def test_08_wrong_subject_is_rejected(self) -> None:
        event = self.reveal26()
        commit = ConversationIngestor(
            SQLiteWorldStore(self.world_db),
            subject_id="user_2",
        ).commit_user_input(
            session_id="other-subject-session",
            turn_index=1,
            user_text=event["resident_visible_payload"],
            occurred_at=datetime.fromisoformat(event["occurred_at"]),
        )
        proc = self.ack_conversation(
            event,
            f"{commit.observation_id}@1",
            session_id="other-subject-session",
            turn_index=1,
            ok=False,
        )
        self.assertIn("durable subject", proc.stderr)

    def test_09_assistant_role_with_user_authority_is_rejected(self) -> None:
        event = self.reveal26()
        ref = self._manual_conversation_observation(
            event,
            object_id="obs_bfix_assistant_role_user_authority",
            session_id="assistant-role-session",
            turn_index=1,
            role="assistant",
            source_class=SourceClass.USER,
        )
        proc = self.ack_conversation(
            event,
            ref,
            session_id="assistant-role-session",
            turn_index=1,
            ok=False,
        )
        self.assertIn("mismatch: role", proc.stderr)

    def test_10_ai_cognition_authority_with_user_role_is_rejected(self) -> None:
        event = self.reveal26()
        ref = self._manual_conversation_observation(
            event,
            object_id="obs_bfix_ai_authority_user_role",
            session_id="ai-authority-session",
            turn_index=1,
            role="user",
            source_class=SourceClass.AI_COGNITION,
        )
        proc = self.ack_conversation(
            event,
            ref,
            session_id="ai-authority-session",
            turn_index=1,
            ok=False,
        )
        self.assertIn("durable source authority", proc.stderr)

    def test_11_other_conversation_event_is_rejected(self) -> None:
        event = self.reveal26()
        other_event = self._projection(32)
        other = self.canonical_module.ingest_canonical_conversation(
            self.world_db,
            other_event,
            session_id="other-event-session",
            turn_index=2,
        )
        proc = self.ack_conversation(
            event,
            other["ingest_ref"],
            session_id="other-event-session",
            turn_index=2,
            ok=False,
        )
        self.assertTrue(
            "mismatch: text" in proc.stderr
            or "timestamp mismatch" in proc.stderr
        )

    def test_12_nonexistent_ref_and_revision_are_rejected(self) -> None:
        event = self.reveal26()
        fake = self.ack_conversation(
            event,
            "fake_conversation@1",
            ok=False,
        )
        self.assertIn("exact canonical conversation revision", fake.stderr)

        ingest = self.canonical_ingest(event)
        wrong_revision = self.ack_conversation(
            event,
            ingest["object_id"] + "@2",
            ok=False,
        )
        self.assertIn(
            "exact canonical conversation revision",
            wrong_revision.stderr,
        )

    def test_13_repeat_skip_and_reordered_ack_are_rejected(self) -> None:
        event = self.reveal26()
        ingest = self.canonical_ingest(event)
        self.ack_conversation(event, ingest["ingest_ref"])

        repeat = self.ack_conversation(
            event,
            ingest["ingest_ref"],
            ok=False,
        )
        self.assertEqual(repeat.stdout, "")

        self.state.write_bytes(self.base_state_b.read_bytes())
        self.world_db.write_bytes(self.base_world_b.read_bytes())
        event = self.reveal26()
        ingest = self.canonical_ingest(event)

        skipped = self.run_op(
            "ack",
            "--phase",
            "B",
            "--state",
            str(self.state),
            "--world-db",
            str(self.world_db),
            "--sequence",
            "27",
            "--event-id",
            self.fixture["events"][26]["event_id"],
            "--ingest-ref",
            ingest["ingest_ref"],
            "--conversation-session-id",
            "resident-b-mechanical-session",
            "--conversation-turn-index",
            "1",
            ok=False,
        )
        self.assertEqual(skipped.stdout, "")

        reordered = self.run_op(
            "ack",
            "--phase",
            "B",
            "--state",
            str(self.state),
            "--world-db",
            str(self.world_db),
            "--sequence",
            "26",
            "--event-id",
            self.fixture["events"][31]["event_id"],
            "--ingest-ref",
            ingest["ingest_ref"],
            "--conversation-session-id",
            "resident-b-mechanical-session",
            "--conversation-turn-index",
            "1",
            ok=False,
        )
        self.assertEqual(reordered.stdout, "")

    def test_14_canonical_fields_are_forbidden_for_nonconversation_event(self) -> None:
        root = Path(self.temp.name)
        state = root / "state-at-25.json"
        world = root / "world-at-25.db"
        shutil.copy2(self.base_state_a, state)
        shutil.copy2(self.base_world_a, world)
        self.run_op("init", "--phase", "B", "--state", str(state))
        event25 = json.loads(
            self.run_op(
                "reveal",
                "--phase",
                "B",
                "--state",
                str(state),
            ).stdout
        )
        ingest25 = self.generic_module.ingest_projection(world, event25)
        proc = self.run_op(
            "ack",
            "--phase",
            "B",
            "--state",
            str(state),
            "--world-db",
            str(world),
            "--sequence",
            "25",
            "--event-id",
            event25["event_id"],
            "--ingest-ref",
            ingest25["ingest_ref"],
            "--conversation-session-id",
            "not-applicable",
            "--conversation-turn-index",
            "1",
            ok=False,
        )
        self.assertIn("forbidden for non-conversation event", proc.stderr)

    def test_15_fixture_digest_and_manifest_versions_are_unchanged_or_expected(self) -> None:
        import hashlib

        digest = "sha256:" + hashlib.sha256(self.fixture_path.read_bytes()).hexdigest()
        self.assertEqual(digest, FROZEN_FIXTURE_SHA256)
        self.assertEqual(self.manifest["fixture_sha256"], FROZEN_FIXTURE_SHA256)
        self.assertEqual(
            self.manifest["release_operator_version"],
            CURRENT_OPERATOR_VERSION,
        )
        self.assertEqual(
            self.manifest["canonical_conversation_adapter_version"],
            "c14-canonical-conversation-adapter-v1",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
