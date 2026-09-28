"""CORRECTIVE-001 store-level fail-closed proofs for durable replay identity.

The capability replay matrix
(``test_core_background_trusted_return_corrective_001_capability_replay.py``)
proves R5-C convergence per capability. Three of its scenarios --
``upsert_relation``, ``update_cognitive_policy`` and ``rollback_cognitive_policy``
-- carry no pinned target revision in their request contract, so their durable
operation identity had to become the complete canonical request. That moves the
"same key, different request" case out of those capabilities and into the layer
that has always owned it: ``SQLiteWorldStore``.

These probes pin that layer directly. They prove the corrective did NOT weaken
anything:

  * an identical request replays the original durable result and writes nothing;
  * a changed request under an existing key is a hard ``IDEMPOTENCY_CONFLICT``;
  * corrupt or skewed durable state is a hard ``STORAGE_FAILURE``;
  * the replay lookup is read-only and never authorizes a write by itself;
  * a reused operation identity under another key still fails closed.

Nothing here touches ``request_fingerprint``, ``expected_world_revision`` or the
trusted-return path.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from aios_core.contracts.enums import ErrorCode
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import CommitResult, OperationRequest
from aios_core.contracts.time import TemporalExtent
from aios_core.storage.idempotency import canonical_request_identity
from aios_core.storage.sqlite_store import SQLiteWorldStore, StoreError

T = datetime(2026, 9, 28, 6, tzinfo=timezone.utc)
SUBJECT = "user_1"
KEY = "corrective001:probe-op"


def new_store(tmp_path: Path, name: str = "world.db") -> SQLiteWorldStore:
    return SQLiteWorldStore(tmp_path / name)


def observation(object_id: str, *, value: str, at: datetime = T) -> Observation:
    moment = at - timedelta(hours=2)
    return Observation(
        object_id=object_id,
        subject_id=SUBJECT,
        occurred=TemporalExtent.point(moment),
        learned_at=moment,
        recorded_at=moment,
        created_by="corrective001:seed",
        source_kind="conversation",
        modality="text",
        value=value,
        metadata={"dimension": "dim:corrective001"},
    )


def request(*, value: str, identity: str | None = None) -> OperationRequest:
    """One stable-idempotency-key request whose fingerprint follows ``value``."""

    return OperationRequest(
        operation_name="corrective001.probe",
        arguments={
            "value": value,
            "canonical_request_sha256": (
                identity
                if identity is not None
                else canonical_request_identity("corrective001.probe", value, T.isoformat())
            ),
        },
        expected_world_revision=0,
        reason="corrective001 store-level probe",
        idempotency_key=KEY,
    )


def apply_once(store: SQLiteWorldStore) -> CommitResult:
    """First application of the probe operation."""

    return store.commit_or_replay([observation("probe_obs", value="first")], request(value="first"))


def snapshot(store: SQLiteWorldStore) -> tuple[int, list, list]:
    with sqlite3.connect(store.db_path) as conn:
        revision = conn.execute(
            "SELECT COALESCE(MAX(revision), 0) FROM object_revisions"
        ).fetchone()[0]
        revisions = conn.execute(
            "SELECT object_id, revision FROM object_revisions ORDER BY object_id, revision"
        ).fetchall()
        rows = conn.execute(
            "SELECT operation_id, idempotency_key, status, result_world_revision "
            "FROM operations ORDER BY rowid"
        ).fetchall()
    return int(revision), revisions, rows


def test_identical_request_replays_the_original_durable_result(tmp_path):
    store = new_store(tmp_path)
    first = apply_once(store)
    assert first.idempotent_replay is False

    before = snapshot(store)
    replay = store.commit_or_replay(
        [observation("probe_obs", value="first")], request(value="first")
    )

    assert replay.idempotent_replay is True
    assert replay.operation_id == first.operation_id
    assert replay.world_revision == first.world_revision
    assert replay.object_refs == first.object_refs
    # Exactly-once durable effect: no new revision, no new operation row.
    assert snapshot(store) == before


def test_replay_exact_operation_is_read_only_when_the_key_is_unused(tmp_path):
    store = new_store(tmp_path)
    before = snapshot(store)

    assert store.replay_exact_operation(request(value="first")) is None
    assert snapshot(store) == before, "the replay lookup wrote durable state"


def test_changed_request_under_an_existing_key_fails_closed(tmp_path):
    store = new_store(tmp_path)
    apply_once(store)
    before = snapshot(store)

    with pytest.raises(StoreError) as exc:
        store.replay_exact_operation(request(value="changed"))
    assert exc.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    assert snapshot(store) == before, "a rejected replay still wrote durable state"


def test_changed_request_fails_closed_through_commit_too(tmp_path):
    """The unchanged ``commit()`` verifier is still the fail-closed authority."""

    store = new_store(tmp_path)
    apply_once(store)
    before = snapshot(store)

    with pytest.raises(StoreError) as exc:
        store.commit([observation("probe_obs", value="changed")], request(value="changed"))
    assert exc.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    assert snapshot(store) == before


def test_replay_never_persists_caller_supplied_objects(tmp_path):
    """A replay reloads the ORIGINAL objects; caller-supplied ones are ignored."""

    store = new_store(tmp_path)
    apply_once(store)
    before = snapshot(store)

    same_request = request(value="first")
    replay = store.commit_or_replay(
        [observation("probe_obs", value="tampered")], same_request
    )

    assert replay.idempotent_replay is True
    assert replay.object_refs == [("probe_obs", 1)]
    assert snapshot(store) == before, "a replay wrote durable state"
    with sqlite3.connect(store.db_path) as conn:
        stored = conn.execute(
            "SELECT payload_json FROM object_revisions WHERE object_id=?", ("probe_obs",)
        ).fetchone()[0]
    assert "tampered" not in stored, "caller-supplied objects reached the durable world"


def test_changed_objects_under_an_existing_key_fail_closed_at_commit(tmp_path):
    """Directly through ``commit()`` the objects are still fingerprinted."""

    store = new_store(tmp_path)
    apply_once(store)
    before = snapshot(store)

    with pytest.raises(StoreError) as exc:
        store.commit([observation("probe_obs", value="tampered")], request(value="first"))
    assert exc.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    assert snapshot(store) == before


def test_operation_idempotency_skew_fails_closed(tmp_path):
    store = new_store(tmp_path)
    apply_once(store)
    before = snapshot(store)

    with sqlite3.connect(store.db_path) as conn:
        conn.execute(
            "UPDATE idempotency_records SET operation_id=? WHERE idempotency_key=?",
            ("op_transplanted", KEY),
        )

    with pytest.raises(StoreError) as exc:
        store.replay_exact_operation(request(value="first"))
    assert exc.value.code is ErrorCode.STORAGE_FAILURE
    assert (exc.value.context or {}).get("reason") == "operation_idempotency_skew"
    assert snapshot(store) == before


def test_missing_idempotency_record_fails_closed(tmp_path):
    store = new_store(tmp_path)
    apply_once(store)
    before = snapshot(store)

    with sqlite3.connect(store.db_path) as conn:
        conn.execute("DELETE FROM idempotency_records WHERE idempotency_key=?", (KEY,))

    with pytest.raises(StoreError) as exc:
        store.replay_exact_operation(request(value="first"))
    assert exc.value.code is ErrorCode.STORAGE_FAILURE
    assert (exc.value.context or {}).get("reason") == "operation_idempotency_skew"
    assert snapshot(store) == before


def test_corrupt_idempotency_result_fails_closed(tmp_path):
    store = new_store(tmp_path)
    apply_once(store)
    before = snapshot(store)

    with sqlite3.connect(store.db_path) as conn:
        conn.execute(
            "UPDATE idempotency_records SET result_json=? WHERE idempotency_key=?",
            ("{not json", KEY),
        )

    with pytest.raises(StoreError) as exc:
        store.replay_exact_operation(request(value="first"))
    assert exc.value.code is ErrorCode.STORAGE_FAILURE
    assert (exc.value.context or {}).get("reason") == "corrupt_idempotency_result"
    assert snapshot(store) == before


def test_idempotency_result_that_is_not_a_commit_result_fails_closed(tmp_path):
    store = new_store(tmp_path)
    apply_once(store)
    before = snapshot(store)

    with sqlite3.connect(store.db_path) as conn:
        conn.execute(
            "UPDATE idempotency_records SET result_json=? WHERE idempotency_key=?",
            (json.dumps({"operation_id": "x"}), KEY),
        )

    with pytest.raises(StoreError) as exc:
        store.replay_exact_operation(request(value="first"))
    assert exc.value.code is ErrorCode.STORAGE_FAILURE
    assert (exc.value.context or {}).get("reason") == "corrupt_idempotency_result"
    assert snapshot(store) == before


def test_missing_committed_object_revision_fails_closed(tmp_path):
    store = new_store(tmp_path)
    apply_once(store)

    with sqlite3.connect(store.db_path) as conn:
        conn.execute("DELETE FROM object_revisions WHERE object_id=?", ("probe_obs",))
    # Snapshotted after the deliberate corruption: only the failed replay must be
    # a no-op, not the corruption the probe itself performs.
    before = snapshot(store)

    with pytest.raises(StoreError) as exc:
        store.replay_exact_operation(request(value="first"))
    assert exc.value.code is ErrorCode.STORAGE_FAILURE
    assert (exc.value.context or {}).get("reason") == "replay_object_missing"
    assert snapshot(store) == before


def test_transplanted_object_payload_fails_closed(tmp_path):
    store = new_store(tmp_path)
    apply_once(store)

    with sqlite3.connect(store.db_path) as conn:
        conn.execute(
            "UPDATE object_revisions SET payload_json=? WHERE object_id=?",
            ("{\"object_type\": \"observation\"}", "probe_obs"),
        )
    before = snapshot(store)

    with pytest.raises(StoreError) as exc:
        store.replay_exact_operation(request(value="first"))
    assert exc.value.code is ErrorCode.STORAGE_FAILURE
    assert (exc.value.context or {}).get("reason") in {
        "corrupt_replay_object_payload",
        "corrupt_replay_object",
    }
    assert snapshot(store) == before


def test_reused_operation_id_under_another_key_fails_closed(tmp_path):
    store = new_store(tmp_path)
    first = apply_once(store)
    before = snapshot(store)

    hijacked = request(value="first").model_copy(
        update={"operation_id": first.operation_id, "idempotency_key": f"{KEY}:other"}
    )
    with pytest.raises(StoreError):
        store.commit([observation("probe_obs", value="first")], hijacked)
    assert snapshot(store) == before, "a reused operation identity wrote durable state"


def test_reused_idempotency_key_under_another_operation_fails_closed(tmp_path):
    """A different operation may not inherit an existing key's durable result."""

    store = new_store(tmp_path)
    apply_once(store)
    before = snapshot(store)

    other = request(value="first").model_copy(update={"operation_name": "corrective001.other"})
    with pytest.raises(StoreError) as exc:
        store.commit([observation("probe_obs", value="first")], other)
    assert exc.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    assert snapshot(store) == before


def test_invalid_idempotency_key_fails_closed(tmp_path):
    store = new_store(tmp_path)
    apply_once(store)
    before = snapshot(store)

    bad = request(value="first").model_copy(update={"idempotency_key": ""})
    with pytest.raises(StoreError) as exc:
        store.replay_exact_operation(bad)
    assert exc.value.code is ErrorCode.INVALID_ARGUMENT
    assert snapshot(store) == before


def test_unrelated_later_world_revision_does_not_break_exact_replay(tmp_path):
    """The crash window: the durable effect landed, then the world moved on."""

    store = new_store(tmp_path)
    first = apply_once(store)

    later = store.current_world_revision()
    store.commit(
        [observation("unrelated_obs", value="unrelated", at=T + timedelta(minutes=5))],
        OperationRequest(
            operation_name="corrective001.unrelated",
            expected_world_revision=int(later),
            reason="unrelated later world revision",
            idempotency_key="corrective001:unrelated",
        ),
    )
    advanced = int(store.current_world_revision())
    assert advanced > int(first.world_revision)

    # A brand new store handle over the same durable world (fresh process).
    replayed = new_store(tmp_path)
    replay = replayed.commit_or_replay(
        [observation("probe_obs", value="first")], request(value="first")
    )
    assert replay.idempotent_replay is True
    assert replay.operation_id == first.operation_id
    assert replay.world_revision == first.world_revision
    assert int(replayed.current_world_revision()) == advanced


def test_replay_returns_the_originally_committed_object_revision(tmp_path):
    store = new_store(tmp_path)
    first = apply_once(store)

    replay = store.commit_or_replay(
        [observation("probe_obs", value="first")], request(value="first")
    )
    assert replay.object_refs == first.object_refs
    assert dict(replay.object_refs)["probe_obs"] == 1
