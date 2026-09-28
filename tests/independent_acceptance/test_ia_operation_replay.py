"""IA rev1 — §18/§19 direct attack on the candidate's operation replay fix.

Candidate additions under attack:
  * SQLiteWorldStore.operation_for_idempotency_key(...)  (new read surface)
  * GoalTaskActionService.create_task original operation identity/revision reuse

Frozen expectation: the lookup is a mechanical identity read only. It must never
authorise a write, never bypass the exact request fingerprint, and never let a
changed replay masquerade as identical. Corrupt/missing/inconsistent durable
state must fail closed.
"""
from __future__ import annotations

import sqlite3

import pytest

from aios_core.contracts.enums import ObjectType, SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent
from aios_core.contracts.refs import ObjectRef
from aios_core.execution.service import GoalTaskActionService, TaskCreateRequest
from aios_core.storage.sqlite_store import SQLiteWorldStore, StoreError
from aios_core.contracts.enums import ErrorCode

from ia_harness import ANCHOR, NOW, idem_rows, q, seed_anchor, world

KEY = "ia-op-key"


def _obs(oid, value="v1"):
    return Observation(
        object_id=oid, subject_id="user_1",
        occurred=TemporalExtent.point(NOW), learned_at=NOW, recorded_at=NOW,
        created_by="ia:op", source_kind="conversation", modality="text",
        value=value, metadata={"dimension": "dim:ia"},
    )


def _store(tmp_path, name="w.db"):
    store, _ = world(tmp_path / name)
    return store


def _expected(store, key=KEY):
    """The original operation's recorded expected_world_revision."""
    rows = q(store.db_path, "SELECT expected_world_revision FROM operations "
                            "WHERE idempotency_key=?", (key,))
    return int(rows[0]["expected_world_revision"])


def _op(**over):
    base = dict(
        operation_id="op_ia_fixed",
        operation_name="ia.op",
        arguments={"a": 1},
        expected_world_revision=0,
        reason="ia",
        idempotency_key=KEY,
        source_class=SourceClass.USER,
    )
    base.update(over)
    return OperationRequest(**base)


# ------------------------------------------------------- 1 exact same retry

def test_ia_op01_exact_retry_is_idempotent_replay(tmp_path):
    store = _store(tmp_path)
    first = store.commit([_obs("o1")], _op())
    # an exact replay reuses the original operation identity AND expected revision
    replay_op = _op(expected_world_revision=_expected(store))
    second = store.commit([_obs("o1")], replay_op)
    assert second.idempotent_replay is True
    assert second.world_revision == first.world_revision
    assert len(q(store.db_path, "SELECT * FROM operations")) == 1
    assert len(q(store.db_path, "SELECT * FROM idempotency_records")) == 1


# ------------------------------------- 2-6 same key + changed request/objects

@pytest.mark.parametrize("mutate", ["arguments", "operation_name", "reason",
                                    "objects", "object_value", "operation_id"])
def test_ia_op02_same_key_changed_request_fails_closed(tmp_path, mutate):
    store = _store(tmp_path)
    store.commit([_obs("o1")], _op())
    before = q(store.db_path, "SELECT * FROM idempotency_records")
    over, objs = {}, [_obs("o1")]
    if mutate == "arguments":
        over["arguments"] = {"a": 2}
    elif mutate == "operation_name":
        over["operation_name"] = "ia.op.changed"
    elif mutate == "reason":
        over["reason"] = "changed reason"
    elif mutate == "operation_id":
        over["operation_id"] = "op_ia_changed"
    elif mutate == "objects":
        objs = [_obs("o2")]
    elif mutate == "object_value":
        objs = [_obs("o1", value="v2")]
    with pytest.raises(StoreError) as exc:
        store.commit(objs, _op(**over))
    assert exc.value.code in {ErrorCode.IDEMPOTENCY_CONFLICT, ErrorCode.VERSION_CONFLICT}, \
        f"{mutate} produced {exc.value.code}"
    assert q(store.db_path, "SELECT * FROM idempotency_records") == before
    assert len(q(store.db_path, "SELECT * FROM object_revisions")) == 1


# ---------------------------------------- 7 altered key must not duplicate

def test_ia_op07_altered_key_creates_distinct_durable_object(tmp_path):
    store = _store(tmp_path)
    store.commit([_obs("o1")], _op())
    with pytest.raises(StoreError):
        # different key, same object id -> store must refuse the object collision
        store.commit([_obs("o1")], _op(idempotency_key=KEY + "-alt"))
    assert len(q(store.db_path, "SELECT * FROM idempotency_records")) == 1


# ------------------------------------------- 8 missing operation row, §19

def test_ia_op08_missing_operation_row_does_not_fake_replay(tmp_path):
    store = _store(tmp_path)
    store.commit([_obs("o1")], _op())
    with sqlite3.connect(store.db_path) as conn:
        conn.execute("DELETE FROM operations")
        conn.commit()
    # The new read surface must report absence, never invent an identity.
    # The new read surface must report absence and must never invent an identity.
    assert store.operation_for_idempotency_key(KEY) is None
    # Whatever happens next, the already-durable effect must not be duplicated.
    try:
        store.commit([_obs("o1")], _op())
    except StoreError:
        pass
    assert len(q(store.db_path, "SELECT * FROM object_revisions")) == 1, \
        "missing operations row led to a duplicate durable effect"


# ------------------------------------- 9 corrupt / missing idempotency record

def test_ia_op09_missing_idempotency_record_fails_closed(tmp_path):
    store = _store(tmp_path)
    store.commit([_obs("o1")], _op())
    with sqlite3.connect(store.db_path) as conn:
        conn.execute("DELETE FROM idempotency_records")
        conn.commit()
    with pytest.raises(StoreError) as exc:
        store.commit([_obs("o1")], _op())
    # fail-closed is the contract; the precise refusal code is an implementation detail
    assert exc.value.code in {ErrorCode.IDEMPOTENCY_CONFLICT, ErrorCode.VERSION_CONFLICT}
    assert len(q(store.db_path, "SELECT * FROM object_revisions")) == 1


def test_ia_op09b_corrupt_idempotency_record_fails_closed(tmp_path):
    store = _store(tmp_path)
    store.commit([_obs("o1")], _op())
    with sqlite3.connect(store.db_path) as conn:
        conn.execute("UPDATE idempotency_records SET result_json='{not json'")
        conn.commit()
    with pytest.raises(StoreError):
        store.commit([_obs("o1")], _op())
    assert len(q(store.db_path, "SELECT * FROM object_revisions")) == 1


# --------------------------------- 10 operations vs idempotency_records skew

def test_ia_op10_operation_vs_idempotency_skew_fails_closed(tmp_path):
    store = _store(tmp_path)
    store.commit([_obs("o1")], _op())
    other = _op(idempotency_key="ia-other", operation_id="op_other",
                expected_world_revision=int(store.current_world_revision()))
    store.commit([_obs("o2")], other)
    with sqlite3.connect(store.db_path) as conn:      # point KEY at the wrong op
        conn.execute("UPDATE idempotency_records SET operation_id='op_other' "
                     "WHERE idempotency_key=?", (KEY,))
        conn.commit()
    try:
        store.commit([_obs("o1")], _op())
    except StoreError:
        pass
    assert len(q(store.db_path, "SELECT * FROM object_revisions")) == 2, \
        "operations/idempotency skew led to an extra durable effect"


# ------------------------------------------- 11 reused operation_id, other key

def test_ia_op11_reused_operation_id_other_key_fails_closed(tmp_path):
    store = _store(tmp_path)
    store.commit([_obs("o1")], _op(operation_id="op_shared"))
    rev = int(store.current_world_revision())
    with pytest.raises(StoreError) as exc:
        store.commit([_obs("o2")],
                     _op(operation_id="op_shared", idempotency_key="ia-second",
                         expected_world_revision=rev))
    assert exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    assert len(q(store.db_path, "SELECT * FROM object_revisions")) == 1


# --------------------------- 12 exact replay after unrelated later revisions

def test_ia_op12_exact_replay_after_unrelated_revisions(tmp_path):
    store = _store(tmp_path)
    first = store.commit([_obs("o1")], _op())
    for i in range(2, 6):                              # unrelated world movement
        store.commit([_obs(f"x{i}")],
                     _op(idempotency_key=f"unrelated-{i}", operation_id=f"op_un_{i}",
                         expected_world_revision=int(store.current_world_revision())))
    rev_now = int(store.current_world_revision())
    assert rev_now > first.world_revision
    replay = store.commit([_obs("o1")], _op(expected_world_revision=_expected(store)))
    assert replay.idempotent_replay is True
    assert replay.world_revision == first.world_revision, \
        "replay must return the ORIGINAL exact result, not the current revision"
    assert int(store.current_world_revision()) == rev_now
    assert len(q(store.db_path, "SELECT * FROM idempotency_records")) == 5


# ------------------------------------- 13 near-simultaneous identical retry

def test_ia_op13_near_simultaneous_identical_retry_single_commit(tmp_path):
    import threading
    store, _ = world(tmp_path / "w.db")
    results, errors = [], []

    def attempt():
        try:
            results.append(store.commit([_obs("o1")], _op()))
        except Exception as exc:                        # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=attempt) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(results) + len(errors) == 6
    assert len(q(store.db_path, "SELECT * FROM idempotency_records")) == 1
    assert len(q(store.db_path, "SELECT * FROM object_revisions")) == 1, \
        "two World commits from concurrent identical retries"
    assert len(results) >= 1


# ------------------------------------------------- §19 authority surface

def test_ia_op19_lookup_is_read_only_and_grants_no_write(tmp_path):
    store = _store(tmp_path)
    store.commit([_obs("o1")], _op())
    before_rev = int(store.current_world_revision())
    before_rows = q(store.db_path, "SELECT * FROM operations")
    found = store.operation_for_idempotency_key(KEY)
    assert found is not None and found["idempotency_key"] == KEY
    # Arbitrary lookup of an unknown key is inert.
    assert store.operation_for_idempotency_key("ia-does-not-exist") is None
    # Lookup must not mutate anything.
    assert int(store.current_world_revision()) == before_rev
    assert q(store.db_path, "SELECT * FROM operations") == before_rows
    # Knowing operation_id must not let a caller overwrite the original operation.
    with pytest.raises(StoreError):
        store.commit([_obs("o1", value="hijack")], _op(operation_id=found["operation_id"]))
    assert len(q(store.db_path, "SELECT * FROM object_revisions")) == 1


def test_ia_op19b_reused_revision_cannot_smuggle_changed_request(tmp_path):
    """expected_world_revision reuse must not bypass conflict checking."""
    store = _store(tmp_path)
    store.commit([_obs("o1")], _op())
    row = store.operation_for_idempotency_key(KEY)
    with pytest.raises(StoreError) as exc:
        store.commit([_obs("o1", value="changed")],
                     _op(operation_id=row["operation_id"],
                         expected_world_revision=int(row["expected_world_revision"])))
    assert exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    assert len(q(store.db_path, "SELECT * FROM object_revisions")) == 1


# ------------------------------- service-level replay of the patched path

def test_ia_service_task_create_replay_is_exactly_once(tmp_path):
    store, index = world(tmp_path / "w.db")
    seed_anchor(store)
    index.catch_up()
    svc = GoalTaskActionService(store=store, subject_id="user_1", index=index)
    req = TaskCreateRequest(title="IA service task", task_type="follow_up",
                            reason_refs=(ObjectRef(object_id=ANCHOR, revision=1),))
    first = svc.create_task(req, created_at=NOW)
    second = svc.create_task(req, created_at=NOW)
    assert (second.task_id, second.revision) == (first.task_id, first.revision)
    assert second.world_revision == first.world_revision
    tasks = [p for p in store.list_payloads(object_type=ObjectType.TASK, subject_id="user_1")]
    assert len(tasks) == 1
    keys = [r["idempotency_key"] for r in idem_rows(store.db_path)]
    assert len([k for k in keys if k.startswith("task-create:")]) == 1


def test_ia_service_task_create_changed_payload_is_a_distinct_task(tmp_path):
    """A genuinely different request must not be swallowed as an identical replay."""
    store, index = world(tmp_path / "w.db")
    seed_anchor(store)
    index.catch_up()
    svc = GoalTaskActionService(store=store, subject_id="user_1", index=index)
    ref_ = ObjectRef(object_id=ANCHOR, revision=1)
    a = svc.create_task(TaskCreateRequest(title="IA service A", task_type="follow_up",
                                          reason_refs=(ref_,)), created_at=NOW)
    b = svc.create_task(TaskCreateRequest(title="IA service B", task_type="follow_up",
                                          reason_refs=(ref_,)), created_at=NOW)
    assert a.task_id != b.task_id
    assert int(store.current_world_revision()) > a.world_revision
