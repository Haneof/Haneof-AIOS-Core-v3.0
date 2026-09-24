"""Synthetic mechanics only. Scripted peer outputs below are TEST DOUBLE DATA,
not Resident choices or evidence. Never load accepted A or the sealed fixture.
"""
import hashlib
import io
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from aios_core.ingest.conversation import ConversationIngestor
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.cognitive_runtime import RuntimeSnapshot
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.summaries.dimension_summary import DimensionSummaryInput
from tools.c15_preflight.audit import (
    AuditError, FIXTURE_HASH, RESTART_KEYS, digest, verify_boundary, verify_files,
)
from tools.c15_preflight.transport import (
    RuntimeRecorder, StreamBridge, Trace, TransportError, directive, encode, plain,
)

NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)


class SyntheticPeer:
    """In-memory test double, NOT an implementation of a model/provider."""
    def __init__(self, outbound, outputs):
        self.outbound = outbound
        self.outputs = iter(outputs)

    def readline(self, limit):
        request = json.loads(self.outbound.getvalue().splitlines()[-1])
        output = next(self.outputs)
        return encode({**{k: request[k] for k in ("request_id", "kind", "input_sha256")}, "output": output}) + "\n"


def setup(tmp_path, outputs=(), incoming=None):
    store = SQLiteWorldStore(tmp_path / "world.sqlite")
    index = WorldSearchIndex(tmp_path / "index.sqlite", store=store)
    trace = Trace(tmp_path / "trace.jsonl", store.current_world_revision)
    outbound = io.StringIO()
    bridge = StreamBridge(incoming if incoming is not None else SyntheticPeer(outbound, outputs), outbound, trace)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=bridge.model,
                               round_summary_handler=bridge.round_summary,
                               dimension_summary_handler=bridge.dimension_summary)
    return store, index, trace, outbound, bridge, runtime


def records(tmp_path):
    return [json.loads(line) for line in (tmp_path / "trace.jsonl").read_text().splitlines()]


def turn(runtime, trace):
    return RuntimeRecorder(runtime, trace).call("run_turn", session_id="synthetic-session", turn_index=1,
                                              user_input="SYNTHETIC input only", occurred_at=NOW)


@pytest.mark.parametrize("output", [
    {"response": "synthetic explicit answer"}, {"silence": True},
    {"capability_calls": [{"name": "search_world", "arguments": {"query": "synthetic"}, "call_id": "test-1"}]},
])
def test_valid_explicit_directives_no_telemetry_invention(output):
    parsed = directive(output)
    assert parsed.usage is None and parsed.provenance is None


@pytest.mark.parametrize("output", [None, {}, [], "silence", {"silence": False}, {"silence": 1},
    {"response": ""}, {"response": 4}, {"response": " "},
    {"response": "x", "silence": True}, {"capability_calls": []},
    {"response": "x", "usage": {"total_tokens": 12}},
    {"provenance": {"provider": "unverified"}},
    {"capability_calls": [{"name": "x"}]},
    {"capability_calls": [{"name": "", "arguments": {}}]},
    {"capability_calls": [{"name": "x", "arguments": []}]},
    {"capability_calls": [{"name": "x", "arguments": {}, "extra": True}]},
    {"capability_calls": [{"name": "x", "arguments": {}, "call_id": 3}]},
])
def test_malformed_directives_fail_closed(output):
    with pytest.raises(TransportError):
        directive(output)


def test_real_fused_user_path_canonical_ingest_and_metering(tmp_path):
    store, index, trace, outbound, _, runtime = setup(tmp_path, [{"response": "SYNTHETIC test response"}])
    canonical = ConversationIngestor(store).commit_user_input(
        session_id="synthetic-session", turn_index=1, user_text="SYNTHETIC input only", occurred_at=NOW)
    result = turn(runtime, trace)
    assert result.conversation_commit.user_observation_id == canonical.observation_id
    assert result.conversation_commit.user_world_revision == canonical.world_revision
    calls = runtime.metering.list_model_calls(subject_id="user_1")
    assert len(calls) == 1 and not calls[0].usage_complete
    assert calls[0].total_tokens is calls[0].model is calls[0].provider is None
    assert index.watermark() == store.current_world_revision()
    request = json.loads(outbound.getvalue())
    assert request["input"]["capability_catalog"]
    assert request["input"]["user_input"] == "SYNTHETIC input only"
    trace.close()
    log = records(tmp_path)
    assert log[0]["kind"] == "runtime_input"
    assert log[-1]["kind"] == "runtime_state"
    assert log[-1]["data"]["metering"][0]["usage_complete"] is False
    assert next(r for r in log if r["kind"] == "model_request")["world_revision"] == canonical.world_revision


def test_missing_reply_is_not_success_or_silence(tmp_path):
    store, _, trace, _, _, runtime = setup(tmp_path, incoming=io.StringIO(""))
    with pytest.raises(TransportError, match="EOF"):
        turn(runtime, trace)
    assert not runtime.metering.list_model_calls(subject_id="user_1")
    assert store.current_world_revision() == 1  # input is durable; no assistant delivery
    trace.close()
    kinds = [r["kind"] for r in records(tmp_path)]
    assert "runtime_error" in kinds and "runtime_result" not in kinds
    assert "model_error" in kinds and "model_return_validated" not in kinds


@pytest.mark.parametrize("raw", ["{}\n", "{bad\n", '{"x":1,"x":2}\n', '{"x":NaN}\n', '{}', 'x' * 102])
def test_invalid_stream_frames_abort_runtime(tmp_path, raw):
    _, _, trace, _, bridge, runtime = setup(tmp_path, incoming=io.StringIO(raw))
    bridge.max_reply_chars = 100
    with pytest.raises((TransportError, json.JSONDecodeError)):
        turn(runtime, trace)
    assert not runtime.metering.list_model_calls(subject_id="user_1")
    trace.close()


@pytest.mark.parametrize("name,args,ok", [
    ("search_world", {"query": "SYNTHETIC"}, True),
    ("search_world", {"invalid_argument": "x"}, False),
    ("nonexistent_capability", {}, False),
])
def test_capabilities_run_only_via_core_with_real_result_trace(tmp_path, name, args, ok):
    _, _, trace, outbound, _, runtime = setup(tmp_path, [
        {"capability_calls": [{"name": name, "arguments": args, "call_id": "synthetic-call"}]},
        {"silence": True},
    ])
    result = turn(runtime, trace)
    assert result.runtime.silenced and result.runtime.capability_history[0].ok is ok
    second = json.loads(outbound.getvalue().splitlines()[1])
    assert second["input"]["capability_history"][0]["ok"] is ok
    assert len(runtime.metering.list_model_calls(subject_id="user_1")) == 2
    trace.close()
    log = records(tmp_path)
    kinds = [r["kind"] for r in log]
    assert kinds.index("capability_call") < kinds.index("capability_result")
    assert next(r for r in log if r["kind"] == "capability_result")["data"]["ok"] is ok


def test_frozen_core_budget_is_not_overridden(tmp_path):
    _, _, trace, _, _, runtime = setup(tmp_path, [{"capability_calls": [{"name": "search_world", "arguments": {"query": "x"}}]}])
    runtime.cognitive_runtime.max_tool_rounds = 0  # synthetic Core budget boundary
    result = turn(runtime, trace)
    assert result.runtime.termination_reason == "tool_round_budget_exhausted"
    assert not result.runtime.silenced
    trace.close()
    assert "capability_call" not in [r["kind"] for r in records(tmp_path)]


def test_summary_callback_transports_actual_typed_input_without_default(tmp_path):
    _, _, trace, outbound, bridge, _ = setup(tmp_path, [{"text": "SYNTHETIC summary test data"}])
    request = DimensionSummaryInput(dimension="dim:synthetic", granularity="day", window_start=NOW,
                                    window_end=NOW + timedelta(days=1), source_world_revision=0, sources=())
    assert bridge.dimension_summary(request) == "SYNTHETIC summary test data"
    sent = json.loads(outbound.getvalue())
    assert sent["kind"] == "dimension_summary" and sent["input"] == request.model_dump(mode="json")
    trace.close()


@pytest.mark.parametrize("output", [{}, {"text": ""}, {"text": 3}, {"silence": True}])
def test_missing_summary_never_becomes_success(output):
    with pytest.raises(TransportError):
        StreamBridge._summary(output)


def test_no_fabricated_snapshot_or_summary_request(tmp_path):
    _, _, trace, _, bridge, _ = setup(tmp_path)
    for handler in (bridge.model, bridge.round_summary, bridge.dimension_summary):
        with pytest.raises(TypeError):
            handler({})
    trace.close()


def test_trace_exclusive_hash_chain_and_fail_closed_serialization(tmp_path):
    path = tmp_path / "trace.jsonl"
    trace = Trace(path, lambda: 3)
    with pytest.raises(FileExistsError):
        Trace(path, lambda: 3)
    for i in range(3):
        trace.append("synthetic", {"i": i})
    with pytest.raises(TypeError):
        trace.append("unsupported", object())
    trace.close()
    previous = "0" * 64
    for i, row in enumerate(records(tmp_path), 1):
        actual = row.pop("sha256")
        assert row["previous"] == previous and row["sequence"] == i
        assert actual == hashlib.sha256(encode(row).encode()).hexdigest()
        previous = actual
    assert path.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("value", [object(), {1: "x"}, float("nan")])
def test_evidence_serialization_never_uses_repr(value):
    with pytest.raises((ValueError, TypeError)):
        encode(value)


def test_artifact_verifier_rejects_changed_missing_symlink_and_live_wal(tmp_path):
    artifact = tmp_path / "world.sqlite"
    artifact.write_bytes(b"synthetic bytes, not a private World")
    pins = {artifact.name: digest(artifact)}
    assert verify_files(tmp_path, pins) == pins
    wal = tmp_path / "world.sqlite-wal"
    wal.touch()
    with pytest.raises(AuditError, match="sidecar"):
        verify_files(tmp_path, pins)
    wal.unlink()
    artifact.write_bytes(b"changed")
    with pytest.raises(AuditError, match="hash"):
        verify_files(tmp_path, pins)
    artifact.unlink()
    with pytest.raises(AuditError, match="missing"):
        verify_files(tmp_path, pins)
    other = tmp_path / "other"
    other.write_bytes(b"changed")
    artifact.symlink_to(other)
    with pytest.raises(AuditError, match="non-regular"):
        verify_files(tmp_path, pins)


def synthetic_boundary(tmp_path):
    """Standalone metadata schema double; no A data and no real fixture contents."""
    world = sqlite3.connect(tmp_path / "private_world.sqlite")
    world.executescript("CREATE TABLE world_meta(key,value); INSERT INTO world_meta VALUES('world_revision','88');"
                       "CREATE TABLE object_revisions(object_id,revision,world_revision,object_type,subject_id);"
                       "CREATE TABLE metering_records(usage_complete,provider,model);")
    receipts = []
    for n in range(1, 14):
        world.execute("INSERT INTO object_revisions VALUES(?,1,?,'observation','user_1')", (f"synthetic-{n}", n))
        receipts.append(dict(sequence=n, fixture_sha256=FIXTURE_HASH, ingest_object_id=f"synthetic-{n}",
                             ingest_revision=1, ingest_ref=f"synthetic-{n}@1", ingest_world_revision=n))
    world.commit(); world.close()
    index = sqlite3.connect(tmp_path / "world_index.sqlite")
    index.executescript("CREATE TABLE search_meta(key,value); INSERT INTO search_meta VALUES('search_watermark_world_revision','88');")
    index.close()
    release = dict(active_phase="A", fixture_sha256=FIXTURE_HASH, last_acked_sequence=13,
                   next_sequence=14, pending_reveal=None, receipts=receipts)
    restart = dict.fromkeys(RESTART_KEYS, "synthetic")
    restart.update(done_at_cursor=13, release_state_next_sequence=14, subject_id="user_1",
                   final_world_revision=88, final_index_watermark=88)
    (tmp_path / "release_state.json").write_text(json.dumps(release))
    (tmp_path / "restart_state.json").write_text(json.dumps(restart))
    return release, restart


def test_synthetic_boundary_refs_and_no_side_effects(tmp_path):
    synthetic_boundary(tmp_path)
    before = {p.name: digest(p) for p in tmp_path.iterdir()}
    result = verify_boundary(tmp_path)
    assert result["durable_receipt_refs"] == 13
    assert {p.name: digest(p) for p in tmp_path.iterdir()} == before


@pytest.mark.parametrize("mutation", ["lag", "missing_ref", "duplicate_ref", "pending", "restart_extra"])
def test_boundary_negative_checks(tmp_path, mutation):
    release, restart = synthetic_boundary(tmp_path)
    if mutation == "lag":
        with sqlite3.connect(tmp_path / "world_index.sqlite") as conn:
            conn.execute("UPDATE search_meta SET value='87'")
    elif mutation == "missing_ref":
        release["receipts"][0]["ingest_world_revision"] = 999
    elif mutation == "duplicate_ref":
        release["receipts"][1] = {**release["receipts"][0], "sequence": 2}
    elif mutation == "pending":
        release["pending_reveal"] = {"synthetic": True}
    else:
        restart["transcript"] = "forbidden"
    (tmp_path / "release_state.json").write_text(json.dumps(release))
    (tmp_path / "restart_state.json").write_text(json.dumps(restart))
    with pytest.raises(AuditError):
        verify_boundary(tmp_path)


def test_normal_summary_scheduler_uses_bridge_and_persists_core_summary(tmp_path):
    store, _, trace, outbound, _, runtime = setup(tmp_path, [{"text": "SYNTHETIC scheduler summary"}])
    ConversationIngestor(store).commit_user_input(session_id="synthetic-summary", turn_index=1,
                                                user_text="SYNTHETIC yesterday input", occurred_at=NOW)
    result = RuntimeRecorder(runtime, trace).call("run_due_dimension_summaries",
        now=NOW + timedelta(days=1, hours=1), scales=("day",), max_jobs=1,
        dimensions=("dim:user_ai_interaction",))
    assert result is not None
    requests = [json.loads(line) for line in outbound.getvalue().splitlines()]
    assert requests and requests[0]["kind"] == "dimension_summary"
    assert requests[0]["input"]["sources"]
    assert any(p.get("content") == "SYNTHETIC scheduler summary" for p in store.list_payloads())
    trace.close()


def test_normal_periodic_review_uses_runtime_and_core_metering(tmp_path):
    store, _, trace, outbound, _, runtime = setup(tmp_path, [{"silence": True}])
    ConversationIngestor(store).commit_user_input(session_id="synthetic-review", turn_index=1,
                                                user_text="SYNTHETIC review input", occurred_at=NOW)
    result = RuntimeRecorder(runtime, trace).call("run_periodic_review", now=NOW + timedelta(hours=1))
    assert result is not None
    request = json.loads(outbound.getvalue())
    assert request["input"]["wake_reason"] == "periodic_review"
    meters = runtime.metering.list_model_calls(subject_id="user_1")
    assert len(meters) == 1 and meters[0].execution_class == "periodic_review"
    assert meters[0].total_tokens is None
    trace.close()


def test_normal_wake_dispatch_without_due_work_does_not_invent_model_call(tmp_path):
    _, _, trace, outbound, _, runtime = setup(tmp_path)
    result = RuntimeRecorder(runtime, trace).call("dispatch_next_pending_wake", now=NOW)
    assert result is None and outbound.getvalue() == ""
    assert runtime.metering.list_model_calls(subject_id="user_1") == ()
    trace.close()
