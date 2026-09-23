"""Operator single-writer orchestration over frozen release and Core entrypoints.

This increment is executable ONLY with synthetic release modules. It cannot
activate the real C15 fixture. It does not implement cognition or retry a model.
Clean event-boundary resume only; interrupted phases require operator review.
"""
from __future__ import annotations

import fcntl
import io
import json
import os
from contextlib import redirect_stdout
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from .audit import FIXTURE_HASH, digest
from .clock import ClockAdapter
from .transport import RuntimeRecorder, TransportError, encode, plain


class DriverBlocked(RuntimeError):
    pass


def moment(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise DriverBlocked("clock must be timezone-aware")
    return dt


def atomic_json(path: Path, value) -> None:
    temp = path.with_name(path.name + ".tmp")
    with temp.open("x", encoding="utf-8") as stream:
        os.chmod(temp, 0o600)
        stream.write(encode(value) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class ReleasePort:
    """Call the existing C15 bindings' release/canonical/mechanical functions.

    Tests supply C15 bindings configured to newly generated SYNTHETIC material.
    No fixture file is read by constructing this port. All release/receipt
    validation remains in the frozen infrastructure, not a replacement protocol.
    """
    def __init__(self, operator, canonical, mechanical, state: Path, world: Path, phase: str):
        if operator.FIXTURE_SHA256 == FIXTURE_HASH:
            raise DriverBlocked("real C15 release is disabled in preflight")
        if len({operator.FIXTURE_SHA256, canonical.FIXTURE_SHA256, mechanical.FIXTURE_SHA256}) != 1:
            raise DriverBlocked("inconsistent adapter pins")
        self.operator, self.canonical, self.mechanical = operator, canonical, mechanical
        self.state, self.world, self.phase = state, world, phase

    def read_state(self):
        return json.loads(self.state.read_text())

    def invoke(self, command, **kwargs):
        output = io.StringIO()
        with redirect_stdout(output):
            command(SimpleNamespace(state=str(self.state), phase=self.phase, **kwargs))
        return json.loads(output.getvalue())

    def reveal(self):
        return self.invoke(self.operator.cmd_reveal)

    @staticmethod
    def is_user(event):
        return (event.get("dimension"), event.get("source_kind"), event.get("source_class"), event.get("modality")) == (
            "dim:conversation", "conversation", "USER", "text")

    def ingest(self, event, *, session, turn):
        if self.is_user(event):
            return self.canonical.ingest_canonical_conversation(self.world, event, session_id=session, turn_index=turn)
        return self.mechanical.ingest_projection(self.world, event)

    def ack(self, event, receipt, *, session, turn):
        user = self.is_user(event)
        return self.invoke(self.operator.cmd_ack, world_db=str(self.world), sequence=event["sequence"],
                           event_id=event["event_id"], ingest_ref=receipt["ingest_ref"],
                           conversation_session_id=session if user else None,
                           conversation_turn_index=turn if user else None)


class Driver:
    """Serial event coordinator; mutex spans ingest, Core, checkpoints and freeze.

    The process must exclusively own its disposable run directory and World/index.
    Advisory lock prevents cooperating drivers, not a hostile same-UID process.
    Freeze adds real SQLite writer locks. An actual Resident gets no directory.
    """
    def __init__(self, runtime, trace, port: ReleasePort, directory: Path, *, session: str,
                 clock: datetime, stop_sequence: int, max_dispatches: int = 64):
        if not session.strip() or clock.tzinfo is None or max_dispatches < 1:
            raise DriverBlocked("invalid mechanical configuration")
        if trace.failure:
            raise DriverBlocked("failed transport cannot initialize driver")
        self.runtime, self.trace, self.port, self.directory = runtime, trace, port, directory
        self.recorder = RuntimeRecorder(runtime, trace)
        self.max_dispatches = max_dispatches
        self.state_path = directory / "driver_state.json"
        self.lock = (directory / "driver.lock").open("a+")
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            release = port.read_state()
            if release["pending_reveal"] is not None:
                raise DriverBlocked("interrupted reveal requires explicit review; no implicit replay")
            if self.state_path.exists():
                self.state = json.loads(self.state_path.read_text())
                if self.state["stage"] != "READY":
                    raise DriverBlocked("interrupted/failed/frozen phase cannot automatically resume")
                if self.state["session"] != session or self.state["stop_sequence"] != stop_sequence:
                    raise DriverBlocked("restart routing changed")
                if self.state["clock"] != clock.isoformat():
                    raise DriverBlocked("restart clock changed")
                self.verify_boundary()
            else:
                self.state = dict(format="c15-synthetic-driver-v1", stage="READY", session=session,
                                  clock=clock.isoformat(), next_turn=1, stop_sequence=stop_sequence,
                                  completed_sequence=release["last_acked_sequence"], due_work={},
                                  next_review_at=(clock+timedelta(hours=24)).isoformat())
                self.checkpoint()
            self.clock = ClockAdapter(self.recorder, clock=clock,
                                      next_review_at=moment(self.state["next_review_at"]))
        except BaseException:
            self.lock.close()
            raise

    def checkpoint(self):
        self.state.update(world_revision=int(self.runtime.store.current_world_revision()),
                          index_watermark=self.runtime.index.watermark(), release_sha256=digest(self.port.state))
        atomic_json(self.state_path, self.state)

    def transition(self, stage):
        self.state["stage"] = stage
        self.checkpoint()  # Persist BEFORE side effects; a crash never looks READY.

    def verify_boundary(self):
        release = self.port.read_state()
        if (digest(self.port.state) != self.state["release_sha256"]
                or int(self.runtime.store.current_world_revision()) != self.state["world_revision"]
                or self.runtime.index.watermark() != self.state["index_watermark"]
                or release["last_acked_sequence"] != self.state["completed_sequence"]
                or release["pending_reveal"] is not None):
            raise DriverBlocked("boundary state changed outside coordinator")

    def due_work(self, now):
        # No clock jumps, repeated summary drain, budget edits or fixed Claim logic.
        summary = self.recorder.call("run_due_dimension_summaries", now=now)
        if summary.truncated:
            raise DriverBlocked("Summary source/job cap reached; unresolved due work")
        dispatches = []
        for _ in range(self.max_dispatches):
            result = self.recorder.call("dispatch_next_pending_wake", now=now)
            if result is None:
                break
            dispatches.append({"wake_ref": plain(result.wake_ref), "state": result.wake.state,
                               "termination_reason": result.runtime.termination_reason if result.runtime else None,
                               "step0": plain(result.step0)})
            if result.runtime is None or result.wake.state != "completed":
                # Core may retain RUNNING under a budget gate. Never force-drain.
                break
        else:
            raise DriverBlocked("operator safety cap reached; not Core completion")
        # The reused clock owns Review cadence. Do not create an early Review
        # on every input and desynchronize its next_review_at from durable Core.
        review = (self.recorder.call("run_periodic_review", now=now)
                  if self.clock._next_review_at <= now else None)
        # Persist only scheduling/ref metadata in restart, never cockpit or directives.
        pending = [{"object_id": p["object_id"], "revision": p["revision"],
                    "wake_state": p["wake_state"], "wake_source": p["wake_source"]}
                   for p in self.runtime.store.list_payloads()
                   if p.get("object_type") == "wake" and p.get("wake_state") in {"new", "queued", "running"}]
        return {"clock": now.isoformat(), "summary_commits": plain(summary.commits),
                "summary_truncated": summary.truncated, "dispatches": dispatches,
                "review": None if review is None else {
                    "wake": plain(review.wake), "budget": plain(review.budget),
                    "termination_reason": review.runtime.termination_reason if review.runtime else None},
                "pending_wakes": pending}

    def step(self):
        if self.lock.closed or self.state["stage"] != "READY" or self.trace.failure:
            raise DriverBlocked("driver not at a clean boundary")
        self.verify_boundary()
        release = self.port.read_state()
        if release["next_sequence"] > self.state["stop_sequence"]:
            return False  # No reveal at/after the stop boundary.
        try:
            self.transition("RELEASING")
            event = self.port.reveal()
            if event["sequence"] != self.state["completed_sequence"] + 1:
                raise DriverBlocked("release sequence mismatch")
            now = moment(event["occurred_at"])
            if now < moment(self.state["clock"]):
                raise DriverBlocked("clock regression")
            self.trace.append("released_input", event)
            self.transition("ADVANCING_CLOCK")
            # Current event is not ingested yet: prior-deadline snapshots cannot
            # observe its future input. Existing habitation clock owns tick order.
            clock_result = self.clock.advance_to(now)
            self.trace.append("clock_advance", clock_result)
            self.state["next_review_at"] = self.clock._next_review_at.isoformat()
            self.transition("INGESTING")
            turn = self.state["next_turn"]
            receipt = self.port.ingest(event, session=self.state["session"], turn=turn)
            self.trace.append("durable_ingest", receipt)
            self.runtime.index.catch_up()
            self.transition("ACKING")
            ack = self.port.ack(event, receipt, session=self.state["session"], turn=turn)
            self.trace.append("durable_ack", ack)  # ACK is ingest, NOT processing completion.
            self.transition("PROCESSING")
            if self.port.is_user(event):
                result = self.recorder.call("run_turn", session_id=self.state["session"], turn_index=turn,
                    user_input=event["resident_visible_payload"], occurred_at=now)
                if result.conversation_commit.user_observation_id != receipt["object_id"]:
                    raise DriverBlocked("canonical/run_turn binding mismatch")
                if result.runtime.termination_reason not in {"responded", "silence"}:
                    raise DriverBlocked("user turn unfinished; not implicit silence")
                self.state["next_turn"] += 1
            self.state["due_work"] = self.due_work(now)
            self.runtime.index.catch_up()
            self.state.update(clock=now.isoformat(), completed_sequence=event["sequence"])
            self.trace.append("event_processing_complete", {"sequence": event["sequence"],
                              "due_work": self.state["due_work"]})
            self.transition("READY")
            return True
        except BaseException as exc:
            self.state["error_type"] = type(exc).__name__
            self.transition("FAILED")
            raise

    def close(self):
        self.lock.close()
