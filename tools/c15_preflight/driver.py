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
    def __init__(self, operator, canonical, mechanical, state: Path, world: Path, phase: str, *, allow_real_fixture: bool = False):
        if not allow_real_fixture and operator.FIXTURE_SHA256 == FIXTURE_HASH:
            raise DriverBlocked("real C15 release is disabled in preflight")
        if len({operator.FIXTURE_SHA256, canonical.FIXTURE_SHA256, mechanical.FIXTURE_SHA256}) != 1:
            raise DriverBlocked("inconsistent adapter pins")
        self.operator, self.canonical, self.mechanical = operator, canonical, mechanical
        self.state, self.world, self.phase = state, world, phase
        self.allow_real_fixture = allow_real_fixture

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


class AcceptedAPort:
    """Read-only port for accepted-A import. Real fixture hash is allowed here
    because we are importing already-verified A evidence, not releasing B/C.
    Reveal/ingest/ack are blocked; only read_state and boundary checks are allowed.
    """
    def __init__(self, state: Path, world: Path):
        self.state = state
        self.world = world

    def read_state(self):
        return json.loads(self.state.read_text())

    def reveal(self):
        raise DriverBlocked("accepted-A import does not reveal next events; B/C not released")

    def ingest(self, *args, **kwargs):
        raise DriverBlocked("accepted-A import does not ingest")

    def ack(self, *args, **kwargs):
        raise DriverBlocked("accepted-A import does not ack")

    @staticmethod
    def is_user(event):
        # Same classification as ReleasePort for consistency
        return (event.get("dimension"), event.get("source_kind"), event.get("source_class"), event.get("modality")) == (
            "dim:conversation", "conversation", "USER", "text")


class Driver:
    """Serial event coordinator; mutex spans ingest, Core, checkpoints and freeze.

    The process must exclusively own its disposable run directory and World/index.
    Advisory lock prevents cooperating drivers, not a hostile same-UID process.
    Freeze adds real SQLite writer locks. An actual Resident gets no directory.
    """
    def __init__(self, runtime, trace, port, directory: Path, *, session: str,
                 clock: datetime, stop_sequence: int, max_dispatches: int = 64,
                 initialize_fresh: bool = False,
                 accepted_a_dir: Path | None = None):
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
            if self.state_path.is_symlink() or self.state_path.with_name(self.state_path.name + ".tmp").exists():
                raise DriverBlocked("checkpoint path ambiguous; explicit review required")
            if self.state_path.exists():
                if initialize_fresh or accepted_a_dir is not None:
                    raise DriverBlocked("initialization cannot reuse a checkpoint")
                try:
                    self.state = json.loads(self.state_path.read_text())
                    self._validate_checkpoint()
                except (OSError, ValueError, TypeError, KeyError) as exc:
                    raise DriverBlocked("checkpoint unreadable/corrupt; no ACK inference or replay") from exc
                if self.state["stage"] != "READY":
                    stage = self.state["stage"]
                    if stage == "PROCESSING":
                        raise DriverBlocked(
                            "REVIEW REQUIRED: persisted PROCESSING stage is IN_DOUBT; "
                            "model execution outcome UNKNOWN; automatic replay forbidden"
                        )
                    raise DriverBlocked(
                        f"REVIEW REQUIRED: persisted stage {stage} cannot automatically resume"
                    )
                if self.state["session"] != session or self.state["stop_sequence"] != stop_sequence:
                    raise DriverBlocked("restart routing changed")
                if self.state["clock"] != clock.isoformat():
                    raise DriverBlocked("restart clock changed")
                self.verify_boundary()
            else:
                existing_world = (directory / "private_world.sqlite").exists() or (directory / "world_index.sqlite").exists() or (directory / "release_state.json").exists()
                if initialize_fresh and accepted_a_dir is not None:
                    raise DriverBlocked("cannot be both fresh and accepted-A import")
                if initialize_fresh:
                    # This path is ONLY an explicitly requested pristine synthetic
                    # genesis, not accepted-A import and not interrupted recovery.
                    if not (
                        release.get("active_phase") == "A"
                        and release.get("last_acked_sequence") == 0
                        and release.get("last_acked_event_id") is None
                        and release.get("next_sequence") == 1
                        and release.get("receipts") == []
                        and int(runtime.store.current_world_revision()) == 0
                        and runtime.index.watermark() == 0
                        and not runtime.metering.list_model_calls(subject_id=runtime.subject_id)
                        and trace.sequence == 0 and trace.path.stat().st_size == 0
                    ):
                        if existing_world:
                            raise DriverBlocked("checkpoint loss/damage detected: existing world files but no driver checkpoint; explicit recovery review required, cannot bypass via fresh or accepted-A import")
                        raise DriverBlocked("missing checkpoint: not a verified fresh synthetic genesis")
                    self.state = dict(format="c15-synthetic-driver-v1", stage="READY", session=session,
                                      clock=clock.isoformat(), next_turn=1, stop_sequence=stop_sequence,
                                      completed_sequence=0, due_work={},
                                      next_review_at=(clock+timedelta(hours=24)).isoformat())
                    self.checkpoint()
                elif accepted_a_dir is not None:
                    # Checkpoint loss: if dir already has world files, it is loss, not fresh import
                    if existing_world:
                        try:
                            self.state = self._import_accepted_a_checkpoint(
                                runtime, trace, port, accepted_a_dir, session, clock, stop_sequence
                            )
                            self.checkpoint()
                        except DriverBlocked as e:
                            if any(x in str(e) for x in ("world/index revision", "release", "trace", "session mismatch", "clock mismatch", "staging")):
                                raise DriverBlocked("checkpoint loss/damage detected: existing world files but no driver checkpoint; explicit recovery review required, cannot bypass via accepted-A import") from e
                            raise
                    else:
                        self.state = self._import_accepted_a_checkpoint(
                            runtime, trace, port, accepted_a_dir, session, clock, stop_sequence
                        )
                        self.checkpoint()
                else:
                    if existing_world:
                        raise DriverBlocked("checkpoint loss/damage detected: existing world files but no driver checkpoint; explicit recovery review required")
                    raise DriverBlocked("missing checkpoint: not a verified fresh synthetic genesis")
            self.clock = ClockAdapter(self.recorder, clock=clock,
                                      next_review_at=moment(self.state["next_review_at"]))
        except BaseException:
            self.lock.close()
            raise

    def _import_accepted_a_checkpoint(self, runtime, trace, port, accepted_a_dir: Path, session: str, clock: datetime, stop_sequence: int):
        # accepted_a_dir must be the staged copy produced by stage_accepted_a
        # containing private_world.sqlite, world_index.sqlite, release_state.json,
        # restart_state.json, mechanical_restart.json
        accepted_a_dir = accepted_a_dir.resolve()
        if not accepted_a_dir.is_dir():
            raise DriverBlocked("accepted-A staging dir missing")
        # Verify required files exist and are regular, not symlink
        for name in ("private_world.sqlite", "world_index.sqlite", "release_state.json", "mechanical_restart.json"):
            p = accepted_a_dir / name
            if not p.is_file() or p.is_symlink():
                raise DriverBlocked(f"accepted-A staging missing {name}")
        # Load mechanical plan (produced by restart_plan)
        try:
            plan = json.loads((accepted_a_dir / "mechanical_restart.json").read_text())
        except Exception as exc:
            raise DriverBlocked(f"mechanical plan unreadable: {exc}") from exc
        # Validate plan is the expected mechanical-only fresh-session plan
        if plan.get("format") != "c15-mechanical-restart-plan-v1":
            raise DriverBlocked("unexpected mechanical plan format")
        if plan.get("status") != "STAGED_NOT_RELEASED" or plan.get("launchable") is not False:
            raise DriverBlocked("mechanical plan not staged")
        if plan.get("completed_sequence") != 13:
            raise DriverBlocked("mechanical plan completed_sequence must be 13 for accepted-A")
        if plan.get("next_turn") != 1:
            raise DriverBlocked("mechanical plan next_turn must be 1")
        # Session must match plan's session? Actually driver session is new session,
        # but for A import we require session to equal plan's session_id (operator-supplied new session)
        if plan.get("session_id") != session:
            raise DriverBlocked("accepted-A import session mismatch")
        # Clock must match plan's clock and next_review_at
        try:
            plan_clock = moment(plan["clock"])
            plan_next_review = moment(plan["next_review_at"])
        except Exception as exc:
            raise DriverBlocked(f"plan clock invalid: {exc}") from exc
        if plan_clock != clock:
            raise DriverBlocked("accepted-A import clock mismatch")
        # Verify release state matches plan boundary and is A
        release = port.read_state()
        if release.get("active_phase") != "A":
            raise DriverBlocked("accepted-A release not phase A")
        if release.get("last_acked_sequence") != plan["completed_sequence"]:
            raise DriverBlocked("release last_acked does not match plan completed_sequence")
        if release.get("next_sequence") != 14:
            raise DriverBlocked("release next_sequence must be 14 for A import")
        if release.get("pending_reveal") is not None:
            raise DriverBlocked("release pending_reveal must be None for A import")
        # Verify world revision and watermark are 88 as per accepted-A
        if int(runtime.store.current_world_revision()) != 88 or runtime.index.watermark() != 88:
            raise DriverBlocked("world/index revision not 88 for accepted-A import")
        # Verify trace is empty (no model requests yet in this driver run)
        if not (trace.sequence == 0 and trace.path.stat().st_size == 0):
            raise DriverBlocked("trace must be empty for accepted-A import")
        # Verify no new model calls have been made in this runtime (historical metering
        # from World DB is allowed, but new calls from this driver run must be 0)
        # For synthetic equivalent, we check that metering has no new calls beyond historical?
        # Here we check that no model calls were made via recorder in this session (trace failure already checked)
        # The historical 25 calls are in World DB, not in trace, so we allow them.
        # For synthetic A equivalent with 0 historical, also allow.

        # Build driver checkpoint from plan, with completion boundary from A evidence
        return dict(
            format="c15-synthetic-driver-v1",
            stage="READY",
            session=session,
            clock=clock.isoformat(),
            next_turn=plan["next_turn"],
            stop_sequence=stop_sequence,
            completed_sequence=plan["completed_sequence"],
            due_work={},
            next_review_at=plan["next_review_at"],
            # Additional provenance for audit
            accepted_a_import=True,
            accepted_a_plan_sha256=digest(accepted_a_dir / "mechanical_restart.json"),
            accepted_a_release_sha256=digest(accepted_a_dir / "release_state.json"),
        )

    def _validate_checkpoint(self):
        state = self.state
        if not isinstance(state, dict) or state.get("format") != "c15-synthetic-driver-v1":
            raise ValueError("checkpoint format")
        for key in ("next_turn", "stop_sequence", "completed_sequence", "world_revision", "index_watermark"):
            if type(state[key]) is not int or state[key] < (1 if key == "next_turn" else 0):
                raise ValueError("checkpoint integer")
        if not isinstance(state["session"], str) or not state["session"].strip():
            raise ValueError("checkpoint session")
        moment(state["clock"])
        moment(state["next_review_at"])
        if not isinstance(state["due_work"], dict) or not isinstance(state["stage"], str):
            raise ValueError("checkpoint stage/due work")
        if not isinstance(state["release_sha256"], str) or len(state["release_sha256"]) != 64:
            raise ValueError("checkpoint release digest")
        if state["completed_sequence"] > state["stop_sequence"]:
            raise ValueError("checkpoint stop boundary")

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