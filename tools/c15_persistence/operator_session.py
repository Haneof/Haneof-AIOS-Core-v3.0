"""Durable operator session: the production wiring the frozen WIP never had.

This module is the seam between three things that previously were never joined:

* the **real release operator** (cursor reveal / ack + durable world binding),
* the **real Core runtime** (``FusedTurnRuntime``: background model attempt
  admission, dispatch binding, trusted-return boundary, capability execution,
  metering, assistant output),
* the **operator durability layer** (``RunBackend`` + ``RelayJournal`` +
  sealed checkpoint generations).

It is operator-side only:

* it stores bytes and state labels, never interprets a ``ModelDirective``;
* it never executes capability semantics outside Core's own registry invocation;
* it never declares a reply authentic - it reads Core's receipt and hands it
  back to Core;
* it never declares a reply applied - ``applied`` is recorded only after Core's
  own ``run_turn`` returned;
* it never rewrites ``in_doubt`` to ``not_submitted`` and never resets an
  attempt ledger.

Kill points (frozen enumeration, see ``KILL_POINTS``)
-----------------------------------------------------
``K1`` after the cursor is durably revealed, before ingest.
``K2`` after the event is durably ingested, before provider dispatch.
``K3`` after the exact provider request is durably staged/exposed/dispatched,
       before any provider reply exists.
``K4`` after Core's trusted-return boundary durably authenticated the exact
       reply, before downstream application completed (operator seam: the
       operator-provided capability invoked by Core inside the same round).
``K5`` after model/capability work is durably applied, before the cursor ACK.

Every step is idempotent and re-derives its next action from durable state, so
``resume`` is literally the same loop re-entered in a fresh process.
"""

from __future__ import annotations

import hashlib
import json
import os
import signal
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from . import provider as provider_module
from .backend import BackendError, GenerationStore, RunBackend, canonical_json, digest, fsync_dir, require, sqlite_snapshot
from .relay import RelayJournal
from .runstate import capture_manifest, write_manifest
from .synthetic_release import SUBJECT_ID, SyntheticRelease

PROVIDER_NAME = "c15-synthetic-relay"
MODEL_NAME = "c15-synthetic-model"

KILL_POINTS: tuple[str, ...] = (
    "K1_AFTER_REVEAL",
    "K2_AFTER_INGEST",
    "K3_AFTER_REQUEST_DISPATCH",
    "K4_AFTER_REPLY_AUTHENTICATED",
    "K5_AFTER_APPLIED_BEFORE_ACK",
)

STATE_VERSION = "c15-operator-session-v1"
JOURNAL_VERSION = "c15-relay-journal-v1"


def _bootstrap_src() -> None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "src" / "aios_core").is_dir():
            if str(parent / "src") not in sys.path:
                sys.path.insert(0, str(parent / "src"))
            return


_bootstrap_src()

from aios_core.contracts.time import canonical_utc_iso  # noqa: E402
from aios_core.query.search import WorldSearchIndex  # noqa: E402
from aios_core.runtime import ModelDirective  # noqa: E402
from aios_core.runtime.background_attempt import (  # noqa: E402
    BackgroundModelAttemptStore,
    decode_model_directive,
    encode_model_directive,
)
from aios_core.runtime.capabilities import CapabilityKind, CapabilitySpec  # noqa: E402
from aios_core.runtime.turn_runtime import FusedTurnRuntime  # noqa: E402
from aios_core.storage.sqlite_store import SQLiteWorldStore  # noqa: E402


def request_envelope(
    *,
    run_id: str,
    session_id: str,
    attempt_id: str,
    request_id: str,
    round_index: int,
    cursor: int,
    event_id: str,
    payload: str,
    nonce: str,
    binding_digest: str,
) -> tuple[bytes, dict[str, Any]]:
    """Pure builder for the exact provider request bytes.

    Lives at module level so the resident-surface check can build the *same*
    envelope without any durability layer and compare the two byte-for-byte.
    """
    envelope = {
        "run_id": run_id,
        "session_id": session_id,
        "provider": PROVIDER_NAME,
        "model": MODEL_NAME,
        "model_request_id": request_id,
        "attempt_id": attempt_id,
        "round": round_index,
        "cursor": cursor,
        "event_id": event_id,
        "resident_visible_payload": payload,
        "nonce": nonce,
    }
    metadata = {
        "run_id": run_id,
        "session_id": session_id,
        "provider": PROVIDER_NAME,
        "model": MODEL_NAME,
        "model_request_id": request_id,
        "attempt_id": attempt_id,
        "nonce": nonce,
        "event_id": event_id,
        "cursor": int(cursor),
        "round": int(round_index),
        "request_fingerprint": digest(canonical_json(envelope)),
        "binding_digest": binding_digest,
    }
    return canonical_json(envelope), metadata


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_jsonl(path: Path, record: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    fd = os.open(temp, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)
    dir_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


class OperatorSession:
    """One owned, single-writer operator run over a durable backend."""

    def __init__(self, backend: RunBackend, journal: RelayJournal, release: SyntheticRelease) -> None:
        self.backend = backend
        self.journal = journal
        self.release = release
        self.generations = GenerationStore(backend)
        self.state = backend.state_dir
        self.mailbox = backend.mailbox_dir
        self.runtime: FusedTurnRuntime | None = None
        self._kill_at: str | None = None
        self._handler_rounds: list[int] = []

    # ------------------------------------------------------------ lifecycle

    @classmethod
    def create(
        cls,
        root: str | Path,
        *,
        run_id: str,
        session_id: str,
        event_count: int = 30,
        seed: str = "c15-synthetic",
    ) -> "OperatorSession":
        backend = RunBackend.create(
            root, run_id=run_id, session_id=session_id, subject_id=SUBJECT_ID, phase="A"
        )
        journal = RelayJournal(backend, create=True)
        release = SyntheticRelease(backend.state_dir / "synthetic-release", event_count=event_count, seed=seed)
        session = cls(backend, journal, release)
        session.journal.ledger_set("session_version", STATE_VERSION)
        session.journal.ledger_set("journal_version", JOURNAL_VERSION)
        session.journal.ledger_set("created_at", _now())
        session.prepare_world()
        session.ensure_release_initialized()
        session.seal("initial")
        return session

    @classmethod
    def attach(cls, root: str | Path, *, run_id: str, session_id: str) -> "OperatorSession":
        backend = RunBackend.open(root, run_id=run_id, session_id=session_id, adopt_stale_owner=True)
        journal = RelayJournal(backend)
        release = SyntheticRelease(backend.state_dir / "synthetic-release")
        session = cls(backend, journal, release)
        backend.audit("session_attached", {"phase": "resume"})
        return session

    # ------------------------------------------------------------- locations

    @property
    def world_path(self) -> Path:
        return self.state / "runtime" / "world.sqlite"

    @property
    def index_path(self) -> Path:
        return self.state / "runtime" / "index.sqlite"

    @property
    def release_state_path(self) -> Path:
        return self.state / "runtime" / "release_state.json"

    @property
    def current_event_path(self) -> Path:
        return self.state / "current-event.json"

    @property
    def binding_path(self) -> Path:
        return self.state / "binding" / "current-event-binding.json"

    @property
    def projection_path(self) -> Path:
        return self.state / "evidence" / "projection.json"

    @property
    def failures_path(self) -> Path:
        return self.state / "evidence" / "failures.jsonl"

    @property
    def mailbox_archive_path(self) -> Path:
        return self.mailbox / "archive.jsonl"

    @property
    def capability_ledger_path(self) -> Path:
        return self.state / "capability-ledger.jsonl"

    @property
    def counters_path(self) -> Path:
        return self.state / "counters.json"

    # ---------------------------------------------------------------- world

    def _open_store(self):
        store = SQLiteWorldStore(self.world_path)
        index = WorldSearchIndex(self.world_path, store=store)
        index.rebuild()
        return store, index

    def prepare_world(self) -> None:
        self.world_path.parent.mkdir(parents=True, exist_ok=True)
        SQLiteWorldStore(self.world_path)
        self._open_store()
        # The search index lives inside the World database in this Core version;
        # the live `runtime/index.sqlite` slot holds a coherent backup copy so a
        # re-attach can open and hash it independently of the writer.
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.index_path) as target:
            with sqlite3.connect(self.world_path.as_uri() + "?mode=ro", uri=True) as source:
                source.backup(target)
        if not self.failures_path.is_file():
            _append_jsonl(self.failures_path, {"synthetic": True, "note": "failure evidence slot initialised"})
        if not self.mailbox_archive_path.is_file():
            _append_jsonl(self.mailbox_archive_path, {"synthetic": True, "note": "mailbox archive slot initialised"})

    def ensure_release_initialized(self) -> None:
        if self.release_state_path.is_file():
            return
        report = self.release.init_state(self.release_state_path)
        self.journal.ledger_set("release_initialized", json.dumps(report, sort_keys=True))

    # ---------------------------------------------------------- generations

    def collect_artifacts(self) -> dict[str, bytes]:
        """Coherent byte snapshots of every slot the re-attach manifest pins."""
        artifacts: dict[str, bytes] = {
            "runtime/world.sqlite": sqlite_snapshot(self.world_path),
            "runtime/index.sqlite": sqlite_snapshot(self.world_path),
            "current-event.json": self.current_event_path.read_bytes()
            if self.current_event_path.is_file()
            else b"{}\n",
            "binding/current-event-binding.json": self.binding_path.read_bytes()
            if self.binding_path.is_file()
            else b"{}\n",
            "evidence/projection.json": self.projection_path.read_bytes()
            if self.projection_path.is_file()
            else b"{}\n",
            "evidence/failures.jsonl": self.failures_path.read_bytes()
            if self.failures_path.is_file()
            else b"",
            "mailbox/archive.jsonl": self.mailbox_archive_path.read_bytes()
            if self.mailbox_archive_path.is_file()
            else b"",
            "journal.sqlite": self.backend.journal_path.read_bytes(),
        }
        if self.release_state_path.is_file():
            artifacts["runtime/release_state.json"] = self.release_state_path.read_bytes()
        current_request = provider_module.current_request_path(self.mailbox)
        current_reply = provider_module.current_reply_path(self.mailbox)
        if current_request.is_file():
            artifacts["mailbox/outbox/current.request"] = current_request.read_bytes()
        if current_reply.is_file():
            artifacts["mailbox/inbox/current.reply"] = current_reply.read_bytes()
        return artifacts

    def seal(self, label: str) -> int:
        generation = self.generations.seal(self.collect_artifacts(), label=label)
        self.journal.ledger_set("generation", str(generation))
        return generation

    # ------------------------------------------------------------- counters

    def bump(self, name: str) -> int:
        counters = json.loads(self.counters_path.read_text()) if self.counters_path.is_file() else {}
        counters[name] = int(counters.get(name, 0)) + 1
        _write_json(self.counters_path, counters)
        return counters[name]

    def counters(self) -> dict[str, int]:
        if not self.counters_path.is_file():
            return {}
        return {k: int(v) for k, v in json.loads(self.counters_path.read_text()).items()}

    # --------------------------------------------------------- kill barrier

    def maybe_kill(self, point: str) -> None:
        if self._kill_at != point:
            return
        self.backend.audit("kill_barrier", {"point": point})
        sys.stdout.flush()
        sys.stderr.flush()
        os.kill(os.getpid(), signal.SIGKILL)

    # ------------------------------------------------------------- step 1

    def reveal(self) -> dict[str, Any]:
        before = self.release_state_path.read_bytes() if self.release_state_path.is_file() else b""
        projection = self.release.reveal(self.release_state_path)
        after = self.release_state_path.read_bytes()
        sequence = int(projection["sequence"])
        already = self.journal.ledger_get(f"revealed_sequence_{sequence}")
        if already is None:
            self.bump("reveals")
            self.journal.ledger_set(f"revealed_sequence_{sequence}", str(sequence))
            self.journal.ledger_set(f"revealed_event_id_{sequence}", str(projection["event_id"]))
            self.journal.ledger_set("revealed_sequence", str(sequence))
            self.journal.ledger_set("revealed_event_id", str(projection["event_id"]))
            _write_json(self.current_event_path, projection)
            _write_json(self.projection_path, projection)
        else:
            # A second reveal must be a pure re-read of the same durable cursor.
            require(
                already == str(projection["sequence"])
                and self.journal.ledger_get(f"revealed_event_id_{sequence}")
                == str(projection["event_id"]),
                "resumed reveal produced a different cursor",
            )
            require(before == after, "resumed reveal mutated the durable release state")
            self.backend.audit("reveal_replayed_without_state_change", {"sequence": projection["sequence"]})
        self.maybe_kill("K1_AFTER_REVEAL")
        return projection

    # ------------------------------------------------------------- step 2

    def ingest(self, projection: Mapping[str, Any]) -> dict[str, Any]:
        sequence = int(projection["sequence"])
        stored = self.journal.ledger_get(f"ingest_ref_{sequence}")
        store, _index = self._open_store()
        world_revision_before = int(store.current_world_revision())
        receipt = self.release.ingest(self.world_path, dict(projection))
        if stored is None:
            self.bump("ingests")
            self.journal.ledger_set(f"ingest_ref_{sequence}", str(receipt["ingest_ref"]))
            self.journal.ledger_set(
                f"ingest_world_revision_{sequence}", str(receipt["world_revision"])
            )
            self.journal.ledger_set("ingest_ref", str(receipt["ingest_ref"]))
            _write_json(
                self.binding_path,
                {
                    "event_id": projection["event_id"],
                    "sequence": projection["sequence"],
                    "fixture_sha256": self.release.manifest["fixture_sha256"],
                    "payload_sha256": receipt["fixture_payload_sha256"],
                    "projection_sha256": receipt["fixture_projection_sha256"],
                    "ingest_ref": receipt["ingest_ref"],
                    "object_id": receipt["object_id"],
                    "revision": receipt["revision"],
                    "world_revision": receipt["world_revision"],
                    "reused_existing": bool(receipt.get("reused_existing")),
                },
            )
        else:
            require(
                stored == str(receipt["ingest_ref"]),
                "resumed ingest produced a different durable object identity",
            )
            require(
                self.journal.ledger_get(f"ingest_world_revision_{sequence}")
                == str(receipt["world_revision"]),
                "resumed ingest moved the durable world revision",
            )
            require(
                int(store.current_world_revision()) == world_revision_before,
                "resumed ingest mutated the world revision (duplicate ingest)",
            )
            require(bool(receipt.get("reused_existing")), "resumed ingest created a new observation")
            self.backend.audit("ingest_replayed_without_duplicate", {"ingest_ref": stored})
        self.seal("ingested")
        self.maybe_kill("K2_AFTER_INGEST")
        return receipt

    # ------------------------------------------------------------- step 3

    def _attempt_id(self, *, turn_index: int, round_index: int) -> str:
        execution_id = self.runtime.turn_executions.execution_id_for(
            subject_id=self.runtime.subject_id,
            session_id=self._session_id,
            turn_index=turn_index,
        )
        return BackgroundModelAttemptStore.attempt_id_for(
            subject_id=self.runtime.subject_id,
            work_kind="user_turn",
            work_id=execution_id,
            model_round_index=round_index,
        )

    def _request_id(self, attempt_id: str, round_index: int) -> str:
        return f"synthetic-request-{hashlib.sha256(f'{attempt_id}:{round_index}'.encode()).hexdigest()[:24]}"

    def _request_bytes(
        self,
        *,
        attempt_id: str,
        request_id: str,
        round_index: int,
        cursor: int,
        event_id: str,
        payload: str,
        nonce: str,
        binding_digest: str,
    ) -> tuple[bytes, dict[str, Any]]:
        return request_envelope(
            run_id=str(self.backend.owner["run_id"]),
            session_id=str(self.backend.owner["session_id"]),
            attempt_id=attempt_id,
            request_id=request_id,
            round_index=round_index,
            cursor=cursor,
            event_id=event_id,
            payload=payload,
            nonce=nonce,
            binding_digest=binding_digest,
        )

    def _binding_digest(self) -> str:
        raw = self.binding_path.read_bytes() if self.binding_path.is_file() else b"{}"
        return digest(raw)

    def _relay_exchange(
        self,
        *,
        attempt_id: str,
        round_index: int,
        cursor: int,
        event_id: str,
        payload: str,
    ) -> tuple[str, bytes]:
        """Stage/expose the exact request once and return durable reply bytes."""
        request_id = self._request_id(attempt_id, round_index)
        existing = self._known_requests().get(request_id)
        if existing is None:
            nonce = hashlib.sha256(
                f"{attempt_id}:{round_index}:{self.backend.owner['run_id']}".encode()
            ).hexdigest()[:32]
            request, metadata = self._request_bytes(
                attempt_id=attempt_id,
                request_id=request_id,
                round_index=round_index,
                cursor=cursor,
                event_id=event_id,
                payload=payload,
                nonce=nonce,
                binding_digest=self._binding_digest(),
            )
            generation = int(self.journal.ledger_get("generation") or 0)
            self.journal.stage(metadata, request, generation=generation)
            raw = self.journal.expose(request_id)
            self.journal.ledger_set("round_hint", str(round_index))
            self._write_outbox(request_id, raw, round_index=round_index)
            self.bump("dispatches")
            self.maybe_kill("K3_AFTER_REQUEST_DISPATCH")
        else:
            # Re-presenting the outstanding request after a restart.  The bytes
            # come from the journal and the outbox is left untouched, so the
            # provider dispatch ledger keeps exactly one entry.
            raw = self.journal.outstanding_request(request_id)
            self.backend.audit("request_represented", {"request_id": request_id, "round": round_index})
        reply = self._collect_reply(request_id)
        self.journal.stage_reply(request_id, reply)
        return request_id, reply

    def _known_requests(self) -> dict[str, str]:
        value = self.journal.ledger_get("requests")
        return json.loads(value) if value else {}

    def _remember_request(self, request_id: str, round_index: int) -> None:
        known = self._known_requests()
        known[request_id] = str(round_index)
        self.journal.ledger_set("requests", json.dumps(known, sort_keys=True))

    def _write_outbox(self, request_id: str, raw: bytes, *, round_index: int) -> None:
        target = provider_module.outbox_path(self.mailbox, request_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        dir_fd = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
        provider_module._mirror(self.mailbox, target, provider_module.current_request_path(self.mailbox))
        self._remember_request(request_id, round_index)
        _append_jsonl(
            self.mailbox_archive_path,
            {"direction": "outbox", "request_id": request_id, "sha256": digest(raw), "at": _now()},
        )

    def _collect_reply(self, request_id: str) -> bytes:
        report = provider_module.serve(self.mailbox, request_id)
        _append_jsonl(
            self.mailbox_archive_path,
            {"direction": "inbox", "request_id": request_id, "report": report, "at": _now()},
        )
        if report["dispatch"] == "dispatched":
            self.bump("provider_dispatches")
        else:
            self.bump("provider_reattachments")
        reply = provider_module.inbox_path(self.mailbox, request_id).read_bytes()
        require(digest(reply) == report["reply_sha256"], "provider reply bytes changed after delivery")
        return reply

    # ------------------------------------------------------------- step 4

    def _capability_handler(self, *, attempt_id: str, round: int) -> dict[str, Any]:
        ledger = _read_jsonl(self.capability_ledger_path)
        key = f"{attempt_id}:{round}"
        for row in ledger:
            if row.get("key") == key:
                self.backend.audit("capability_replayed_idempotent", {"key": key})
                return {"result": row.get("result"), "duplicate_suppressed": True}
        result = {"executed": key, "round": round}
        _append_jsonl(self.capability_ledger_path, {"key": key, "result": result, "at": _now()})
        self.bump("capability_side_effects")
        # K4 lives here: Core has already durably authenticated the exact reply
        # for this round (trusted-return receipt committed) and is now executing
        # the directive's capability.  Downstream application is not complete.
        self.maybe_kill("K4_AFTER_REPLY_AUTHENTICATED")
        return {"result": result, "duplicate_suppressed": False}

    def _model_handler(self, snapshot) -> ModelDirective:
        self._handler_rounds.append(int(snapshot.round_index))
        attempt_id = str(snapshot.model_attempt_id)
        cursor = int(self.journal.ledger_get("revealed_sequence") or 0)
        event_id = str(self.journal.ledger_get("revealed_event_id") or "")
        payload = json.loads(self.current_event_path.read_text())["resident_visible_payload"]
        _request_id, reply = self._relay_exchange(
            attempt_id=attempt_id,
            round_index=int(snapshot.round_index),
            cursor=cursor,
            event_id=event_id,
            payload=payload,
        )
        directive = decode_model_directive(reply.decode("utf-8"))
        # The operator returns the exact durable provider bytes and nothing else.
        # It never edits, re-decides or summarises them.
        return directive

    def _build_runtime(self) -> FusedTurnRuntime:
        store, index = self._open_store()
        runtime = FusedTurnRuntime(store=store, index=index, model_handler=self._model_handler)
        runtime.registry.register(
            CapabilitySpec(
                name=provider_module.CAPABILITY_NAME,
                description="C15 persistence probe capability (idempotent, operator provided)",
                kind=CapabilityKind.READ,
                input_schema={"attempt_id": "string", "round": "integer"},
                side_effecting=False,
            ),
            lambda **kwargs: self._capability_handler(
                attempt_id=str(kwargs["attempt_id"]), round=int(kwargs["round"])
            ),
        )
        return runtime

    # ------------------------------------------------- Core recovery handoff

    def _turn_identity(self, projection: Mapping[str, Any]) -> tuple[int, str, str]:
        """Read-only introspection of Core's deterministic turn identity."""
        turn_index = int(projection["sequence"])
        occurred_iso = canonical_utc_iso(
            datetime.fromisoformat(str(projection["occurred_at"])), "occurred_at"
        )
        assistant_id = self.runtime.ingestor._turn_identity(self._session_id, turn_index)[2]
        return turn_index, occurred_iso, assistant_id

    def _recover_with_core(self, projection: Mapping[str, Any]) -> list[dict[str, Any]]:
        """Hand every durable reply back to Core through the accepted API.

        The operator never decides authenticity: it reads Core's own
        trusted-return receipt, stages the exact bytes through
        ``stage_exact_background_response`` and lets Core revalidate them.
        """
        actions: list[dict[str, Any]] = []
        attempts = self.runtime.background_model_attempts
        for request_id in self.journal.request_ids(cursor=int(projection["sequence"])):
            record = self.journal.recovery(request_id)
            if record["state"] in {"staged", "exposed", "applied", "acked"}:
                continue
            attempt_id = str(record["metadata"]["attempt_id"])
            receipt = attempts.response_authenticity_receipt(attempt_id)
            if receipt is None:
                actions.append({"request_id": request_id, "action": "no_core_receipt"})
                continue
            payload = bytes(record["reply"]).decode("utf-8")
            directive = decode_model_directive(payload)
            fingerprint = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            require(
                fingerprint == attempts._response_fingerprint(directive),
                "operator-computed response fingerprint disagrees with Core",
            )
            proof = {
                "attempt_id": str(receipt.attempt_id),
                "authenticity_proof": str(receipt.authenticity_proof),
                "provider": str(receipt.provider),
                "model": str(receipt.model),
                "provider_request_id": str(receipt.provider_request_id),
                "response_fingerprint": fingerprint,
                "relay_id": str(receipt.relay_id),
            }
            if record["state"] == "reply-staged":
                self.journal.mark_authenticated(request_id, proof)
            attempt = attempts.get(attempt_id)
            if attempt is not None and attempts.staged_response(attempt_id) is None:
                if attempt.state in {"dispatching", "in_doubt", "response_returned", "metered"}:
                    self.runtime.stage_exact_background_response(
                        work_kind="user_turn",
                        work_id=self.runtime.turn_executions.execution_id_for(
                            subject_id=self.runtime.subject_id,
                            session_id=self._session_id,
                            turn_index=int(projection["sequence"]),
                        ),
                        model_round_index=int(record["metadata"]["round"]),
                        provider=str(receipt.provider),
                        model=str(receipt.model),
                        provider_request_id=str(receipt.provider_request_id),
                        response_fingerprint=fingerprint,
                        directive_payload=payload,
                        staged_at=datetime.now(timezone.utc),
                        evidence="operator relay journal exact bytes + Core trusted receipt",
                        authenticity_proof=str(receipt.authenticity_proof),
                    )
                    actions.append({"request_id": request_id, "action": "staged_into_core"})
            if self.journal.recovery(request_id)["state"] == "authenticated":
                self.journal.begin_applying(request_id)
                actions.append({"request_id": request_id, "action": "applying"})
        if actions and any(a["action"] in {"staged_into_core", "applying"} for a in actions):
            turn_index, occurred_iso, assistant_id = self._turn_identity(projection)
            try:
                status = self.runtime.turn_executions.authorize_exact_response_recovery(
                    subject_id=self.runtime.subject_id,
                    session_id=self._session_id,
                    turn_index=turn_index,
                    user_input=str(projection["resident_visible_payload"]),
                    occurred_at=occurred_iso,
                    assistant_id=assistant_id,
                    evidence="operator relay journal: exact durable reply + Core receipt",
                )
                actions.append(
                    {
                        "request_id": None,
                        "action": "authorized_exact_response_recovery",
                        "state": status.state,
                        "disposition": status.recovery_disposition,
                    }
                )
            except Exception as exc:  # already completed / nothing to authorise
                actions.append(
                    {
                        "request_id": None,
                        "action": "authorize_skipped",
                        "reason": f"{type(exc).__name__}: {exc}",
                    }
                )
        return actions

    def _finalise_requests(self, cursor: int | None = None) -> list[dict[str, Any]]:
        """Record Core's receipt and the completed application for every round."""
        attempts = self.runtime.background_model_attempts
        actions: list[dict[str, Any]] = []
        for request_id in self.journal.request_ids(cursor=cursor):
            record = self.journal.recovery(request_id)
            if record["state"] in {"applied", "acked"}:
                continue
            attempt_id = str(record["metadata"]["attempt_id"])
            receipt = attempts.response_authenticity_receipt(attempt_id)
            if receipt is None:
                actions.append({"request_id": request_id, "action": "no_core_receipt"})
                continue
            payload = bytes(record["reply"]).decode("utf-8")
            fingerprint = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            proof = {
                "attempt_id": str(receipt.attempt_id),
                "authenticity_proof": str(receipt.authenticity_proof),
                "provider": str(receipt.provider),
                "model": str(receipt.model),
                "provider_request_id": str(receipt.provider_request_id),
                "response_fingerprint": fingerprint,
                "relay_id": str(receipt.relay_id),
            }
            if record["state"] == "reply-staged":
                self.journal.mark_authenticated(request_id, proof)
            self.journal.mark_applied(request_id)
            actions.append({"request_id": request_id, "action": "applied"})
        return actions

    def run_turn(self, projection: Mapping[str, Any]) -> dict[str, Any]:
        turn_index = int(projection["sequence"])
        if self.journal.ledger_get(f"applied_{turn_index}") is not None:
            # K5 resume: model/capability work is already durable in Core.
            self.backend.audit("turn_not_rerun", {"reason": "already applied"})
            return {"skipped": True, "reason": "already_applied", "recovery_actions": []}

        self.runtime = self._build_runtime()
        self._session_id = f"{self.backend.owner['run_id']}-conv"
        recovery_actions = self._recover_with_core(projection)
        for action in recovery_actions:
            self.backend.audit("core_recovery", action)
        occurred_at = datetime.fromisoformat(str(projection["occurred_at"]))

        # Round 0's exact provider request/reply is durable BEFORE Core's turn
        # starts, so a crash before the turn never leaves Core in a state that
        # cannot be re-entered without a redispatch.
        attempt_id = self._attempt_id(turn_index=turn_index, round_index=0)
        self._prime_round_zero(
            attempt_id=attempt_id,
            cursor=turn_index,
            event_id=str(projection["event_id"]),
            payload=str(projection["resident_visible_payload"]),
        )

        result = self.runtime.run_turn(
            session_id=self._session_id,
            turn_index=turn_index,
            user_input=str(projection["resident_visible_payload"]),
            occurred_at=occurred_at,
        )
        self.journal.ledger_set(f"applied_{turn_index}", _now())
        for action in self._finalise_requests(cursor=turn_index):
            self.backend.audit("request_finalised", action)
        self.journal.ledger_set(
            f"recovered_attempts_{turn_index}",
            json.dumps([str(a) for a in result.runtime.recovered_response_attempts]),
        )
        self.journal.ledger_set(f"assistant_output_{turn_index}", str(result.runtime.response))
        self.bump("turns_completed")
        self.seal("applied")
        self.maybe_kill("K5_AFTER_APPLIED_BEFORE_ACK")
        return {
            "skipped": False,
            "response": result.runtime.response,
            "recovered_response_attempts": [str(a) for a in result.runtime.recovered_response_attempts],
            "handler_rounds": list(self._handler_rounds),
            "recovery_actions": recovery_actions,
        }

    def _prime_round_zero(self, *, attempt_id: str, cursor: int, event_id: str, payload: str) -> None:
        self._relay_exchange(
            attempt_id=attempt_id,
            round_index=0,
            cursor=cursor,
            event_id=event_id,
            payload=payload,
        )

    # ------------------------------------------------------------- step 5

    def ack(self, projection: Mapping[str, Any], ingest_receipt: Mapping[str, Any]) -> dict[str, Any]:
        stored = self.journal.ledger_get(f"ack_receipt_{int(projection['sequence'])}")
        if stored is not None:
            self.backend.audit("ack_not_repeated", {"sequence": projection["sequence"]})
            return json.loads(stored)
        report = self.release.ack(
            self.release_state_path,
            world_db=self.world_path,
            sequence=int(projection["sequence"]),
            event_id=str(projection["event_id"]),
            ingest_ref=str(ingest_receipt["ingest_ref"]),
        )
        self.bump("acks")
        self.journal.ledger_set(
            f"ack_receipt_{int(projection['sequence'])}", json.dumps(report, sort_keys=True)
        )
        request_id = self.journal.terminal_request_id(cursor=int(projection["sequence"]))
        if request_id is not None:
            self.journal.mark_acked(request_id, {"sequence": report["sequence"], "next": report["next_sequence"]})
        self.seal("acked")
        return report

    # ------------------------------------------------------------ the loop

    def process_one_cursor(self, *, kill_at: str | None = None) -> dict[str, Any]:
        self._kill_at = kill_at
        if kill_at is not None and kill_at not in KILL_POINTS:
            raise BackendError(f"unknown kill point: {kill_at}")
        projection = self.reveal()
        receipt = self.ingest(projection)
        turn = self.run_turn(projection)
        ack = self.ack(projection, receipt)
        return {"projection": projection, "ingest": receipt, "turn": turn, "ack": ack}

    def resume(self, *, kill_at: str | None = None) -> dict[str, Any]:
        """Re-enter the same loop in a fresh process. Every step re-derives."""
        self.backend.audit("resume_started", {"kill_at": kill_at or "none"})
        return self.process_one_cursor(kill_at=kill_at)

    # ---------------------------------------------------------- observation

    def observation_counts(self, event_id: str) -> dict[str, int]:
        store, _index = self._open_store()
        db = sqlite3.connect(self.world_path.as_uri() + "?mode=ro", uri=True, timeout=10)
        try:
            rows = db.execute(
                "SELECT object_id, revision, payload_json FROM object_revisions "
                "WHERE object_type='observation'"
            ).fetchall()
        finally:
            db.close()
        import json as _json

        matches = 0
        assistant_outputs = 0
        for _object_id, _revision, payload in rows:
            try:
                body = _json.loads(payload)
            except (TypeError, ValueError):
                continue
            metadata = body.get("metadata") or {}
            if metadata.get("fixture_event_id") == event_id:
                matches += 1
            if str(metadata.get("source_kind") or "") == "assistant" or (
                str(body.get("object_type") or "") == "observation"
                and str(metadata.get("role") or "") == "assistant"
            ):
                assistant_outputs += 1
        return {
            "observations_total": len(rows),
            "observations_for_event": matches,
            "assistant_outputs": assistant_outputs,
            "world_revision": int(store.current_world_revision()),
        }

    def metering_rows(self) -> int:
        runtime = self.runtime or self._build_runtime()
        return len(runtime.metering.list_model_calls(subject_id=runtime.subject_id))

    def report(self) -> dict[str, Any]:
        ledger = provider_module.read_ledger(self.mailbox)
        return {
            "run_id": self.backend.owner["run_id"],
            "session_id": self.backend.owner["session_id"],
            "counters": self.counters(),
            "dispatch_ledger": ledger,
            "capability_ledger": _read_jsonl(self.capability_ledger_path),
            "journal_state": self.journal.ledger(),
            "generations": self.generations.verify_all(),
            "audit": self.backend.audit_trail(),
        }
