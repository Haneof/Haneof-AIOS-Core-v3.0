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

Provider-return authority (frozen, Core-owned)
---------------------------------------------
Core owns provider-return authenticity.  This operator layer may reattach an
already-dispatched provider request and may keep the exact bytes in its own
journal, but it can never mint, stage, relabel or assert authenticity.  Only
Core's own trusted-return callback produces the receipt/handoff that licenses
downstream application, and only Core's own accepted recovery surfaces
(``recover_trusted_handoff`` / exact-response recovery) may resume a round.

That yields exactly three post-crash shapes for a durable reply:

``attempt missing``
    Core never admitted this round's attempt (the operator staged the request
    before Core entered the turn).  The exact reply stays durable in the relay
    journal and the ordinary ``run_turn`` path re-admits the deterministic
    attempt identity; when the handler is reached again the relay re-presents
    those exact bytes, so Core's own trusted-return callback mints the receipt.
``provider boundary crossed without a durable trusted return``
    ``dispatching``/``in_doubt`` with no receipt.  No caller-supplied bytes may
    substitute for the trusted provider return, so this is a hard fail-closed
    stop: no second dispatch, no invented receipt, no progress, no ACK.
``durable trusted return exists``
    Core applies the exact return exactly once through its accepted recovery
    surface; the operator only records what Core proves.

Kill points (frozen enumeration, see ``KILL_POINTS``)
-----------------------------------------------------
``K1`` after the cursor is durably revealed, before ingest.
``K2`` after the event is durably ingested, before provider dispatch.
``K3`` after the exact provider request is durably staged/exposed/dispatched,
       before any provider reply exists.
``K3_TRUSTED_RETURN_DURABLE`` after Core's trusted-return boundary durably
       committed the exact reply (receipt + return handoff), before that reply
       is recorded/metered/applied.  This is the authenticatable provider-return
       barrier; bytes that never crossed it cannot be adopted.
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
    "K3_TRUSTED_RETURN_DURABLE",
    "K4_AFTER_REPLY_AUTHENTICATED",
    "K5_AFTER_APPLIED_BEFORE_ACK",
)
K3_POINTS: frozenset[str] = frozenset(
    {"K3_AFTER_REQUEST_DISPATCH", "K3_TRUSTED_RETURN_DURABLE"}
)

STATE_VERSION = "c15-operator-session-v1"
JOURNAL_VERSION = "c15-relay-journal-v1"
REMOTE_DURABILITY_CONFIG = "remote-durability.json"


class RemoteDurabilityAbort(BaseException):
    """Remote-authoritative persistence failed; ordinary capability wrapping must not swallow it."""


class AuthoritativePersistenceFailure(BackendError):
    """A remote-authoritative barrier write failed and was never published.

    This is deliberately distinct from an ordinary local error: the caller must
    treat the run as stopped until a later barrier publishes the state, and must
    never report the failed write as a successful persistence.
    """

    def __init__(self, *, barrier: str, detail: str) -> None:
        self.barrier = barrier
        self.detail = detail
        super().__init__(f"authoritative persistence failure at {barrier}: {detail}")


class DurableTrustedReturnMissing(BackendError):
    """Provider boundary was crossed without a Core-owned durable trusted return.

    Accepted Core deliberately has no legal path that lets a recovery caller turn
    externally supplied bytes into a trusted provider return.  The operator
    therefore stops fail-closed instead of redispatching, inventing evidence or
    making non-authoritative progress.
    """

    def __init__(self, *, attempt_id: str, state: str, round_index: int, detail: str) -> None:
        self.attempt_id = attempt_id
        self.attempt_state = state
        self.round_index = int(round_index)
        self.detail = detail
        super().__init__(
            "no durable trusted provider return for attempt "
            f"{attempt_id} (state={state}, round={round_index}): {detail}"
        )


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
        self._kill_round: int | None = None
        self._handler_rounds: list[int] = []
        self._remote_ref: str | None = None
        self._remote: str = "origin"
        self._remote_repo_dir: Path | None = None
        self._fail_barrier: str | None = None

    # ------------------------------------------------------ remote durability

    @property
    def remote_config_path(self) -> Path:
        return self.backend.root / REMOTE_DURABILITY_CONFIG

    @property
    def remote_durability_enabled(self) -> bool:
        return self._remote_ref is not None

    def _remote_binding_payload(self, *, remote_ref: str, remote: str) -> dict[str, str]:
        from .remote_backend import remote_ref_for_run

        run_id = str(self.backend.owner["run_id"])
        session_id = str(self.backend.owner["session_id"])
        require(bool(remote_ref), "remote durability requires a non-blank remote ref")
        require(bool(remote), "remote durability requires a non-blank remote")
        require(
            remote_ref == remote_ref_for_run(run_id),
            f"remote durability ref is not canonical for run {run_id}: {remote_ref}",
        )
        return {
            "run_id": run_id,
            "session_id": session_id,
            "remote_ref": remote_ref,
            "remote": remote,
            "version": "c15-remote-durability-v2",
        }

    def _configure_remote_durability(
        self,
        *,
        remote_ref: str,
        remote: str,
        repo_dir: Path | None,
        persist: bool,
    ) -> None:
        binding = self._remote_binding_payload(remote_ref=remote_ref, remote=remote)
        require(
            bool(self.backend.owner.get("remote_authoritative")),
            "backend was not created as remote-authoritative; refusing late promotion",
        )
        authority = self.backend.owner.get("remote_authority")
        require(isinstance(authority, dict), "backend remote authority binding is missing")
        require(authority.get("run_id") == binding["run_id"], "remote authority run mismatch")
        require(authority.get("session_id") == binding["session_id"], "remote authority session mismatch")
        require(authority.get("remote_ref") == remote_ref, "remote authority ref mismatch")
        require(authority.get("remote") == remote, "remote authority remote mismatch")
        payload = {**binding, "binding_sha256": digest(canonical_json(binding))}
        if self.remote_config_path.is_file():
            try:
                if (self.remote_config_path.stat().st_mode & 0o400) == 0:
                    raise PermissionError(f"remote durability config {self.remote_config_path} is unreadable (mode 000)")
                stored = json.loads(self.remote_config_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise BackendError(f"remote durability config is unreadable: {exc}") from exc
            require(stored == payload, "remote durability config/binding mismatch")
        elif persist:
            _write_json(self.remote_config_path, payload)
        else:
            raise BackendError("remote-authoritative backend is missing remote durability config")
        self._remote_ref = remote_ref
        self._remote = remote
        self._remote_repo_dir = repo_dir

    def _load_remote_durability(self, *, repo_dir: Path | None = None) -> bool:
        if not self.remote_config_path.is_file():
            require(
                not bool(self.backend.owner.get("remote_authoritative")),
                "remote-authoritative backend is missing remote durability config",
            )
            return False
        try:
            if (self.remote_config_path.stat().st_mode & 0o400) == 0:
                raise PermissionError(f"remote durability config {self.remote_config_path} is unreadable (mode 000)")
            payload = json.loads(self.remote_config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise BackendError(f"remote durability config is unreadable: {exc}") from exc
        require(
            isinstance(payload, dict)
            and set(payload)
            == {"binding_sha256", "remote", "remote_ref", "run_id", "session_id", "version"},
            "remote durability config has unexpected fields",
        )
        base = {k: payload[k] for k in ("run_id", "session_id", "remote_ref", "remote", "version")}
        require(
            payload.get("binding_sha256") == digest(canonical_json(base)),
            "remote durability config binding digest mismatch",
        )
        self._configure_remote_durability(
            remote_ref=str(payload["remote_ref"]),
            remote=str(payload["remote"]),
            repo_dir=repo_dir,
            persist=False,
        )
        return True
    def arm_fail_barrier(self, point: str | None) -> None:
        """Probe-only injection: fail the authoritative write for one barrier."""
        self._fail_barrier = point

    def _persist_remote_barrier(self, point: str, *, seal_label: str | None = None) -> tuple[str, str] | None:
        """Synchronously commit the current recoverable barrier to remote storage.

        This method is called by the normal operator loop *before* a frozen kill
        point may fire.  A failed remote write is an authoritative durability
        failure: it is recorded as durable failure evidence and raises a distinct
        error so the loop cannot cross the barrier or report success.
        """
        if not self.remote_durability_enabled:
            return None
        if seal_label is not None:
            self.seal(seal_label)
        cursor = int(self.journal.ledger_get("revealed_sequence") or 0)
        event_id = str(self.journal.ledger_get("revealed_event_id") or "")
        generation = int(self.journal.ledger_get("generation") or 0)
        _write_json(
            self.state / "remote-barrier.json",
            {
                "point": point,
                "cursor": cursor,
                "event_id": event_id,
                "generation": generation,
            },
        )
        if self._fail_barrier == point:
            self._record_failure(
                "AUTHORITATIVE_PERSISTENCE_FAILURE",
                {"barrier": point, "injected": True, "detail": "probe-injected barrier failure"},
            )
            raise AuthoritativePersistenceFailure(
                barrier=point, detail="probe-injected authoritative persistence failure"
            )
        try:
            return self._push_barrier(point, cursor=cursor, generation=generation)
        except BackendError as exc:
            self._record_failure(
                "AUTHORITATIVE_PERSISTENCE_FAILURE",
                {"barrier": point, "injected": False, "detail": str(exc)},
            )
            raise AuthoritativePersistenceFailure(barrier=point, detail=str(exc)) from exc

    def _push_barrier(
        self, point: str, *, cursor: int, generation: int
    ) -> tuple[str, str]:
        return self.backend.push_to_remote(
            remote_ref=self._remote_ref,
            remote=self._remote,
            repo_dir=self._remote_repo_dir,
            message=(
                f"operator durability barrier: run_id={self.backend.owner['run_id']} "
                f"point={point} cursor={cursor} generation={generation}"
            ),
        )

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
        remote_ref: str | None = None,
        remote: str = "origin",
        repo_dir: Path | None = None,
        require_remote_durability: bool = False,
    ) -> "OperatorSession":
        remote_enabled = require_remote_durability or remote_ref is not None
        effective_ref = remote_ref
        if remote_enabled:
            from .remote_backend import remote_ref_for_run
            effective_ref = effective_ref or remote_ref_for_run(run_id)
            require(
                effective_ref == remote_ref_for_run(run_id),
                f"remote durability ref is not canonical for run {run_id}: {effective_ref}",
            )
        backend = RunBackend.create(
            root,
            run_id=run_id,
            session_id=session_id,
            subject_id=SUBJECT_ID,
            phase="A",
            remote_authority=(
                None if not remote_enabled else {"remote": remote, "remote_ref": str(effective_ref)}
            ),
        )
        journal = RelayJournal(backend, create=True)
        release = SyntheticRelease(backend.state_dir / "synthetic-release", event_count=event_count, seed=seed)
        session = cls(backend, journal, release)
        if remote_enabled:
            require(effective_ref is not None, "remote durability ref was not resolved")
            session._configure_remote_durability(
                remote_ref=effective_ref,
                remote=remote,
                repo_dir=repo_dir,
                persist=True,
            )
        session.journal.ledger_set("session_version", STATE_VERSION)
        session.journal.ledger_set("journal_version", JOURNAL_VERSION)
        session.journal.ledger_set("created_at", _now())
        provider_module.ensure_provider_service(session.mailbox)
        pub_desc = provider_module.read_public_descriptor(session.mailbox)
        session.journal.ledger_set("provider_public_key_fingerprint", pub_desc["public_key_fingerprint"])
        session.journal.ledger_set("provider_instance_id", pub_desc["provider_instance_id"])
        session.prepare_world()
        session.ensure_release_initialized()
        session.seal("initial")
        if session.remote_durability_enabled:
            session._persist_remote_barrier("INITIAL")
        return session

    @classmethod
    def attach(
        cls,
        root: str | Path,
        *,
        run_id: str,
        session_id: str,
        remote_ref: str | None = None,
        remote: str | None = None,
        repo_dir: Path | None = None,
    ) -> "OperatorSession":
        backend = RunBackend.open(root, run_id=run_id, session_id=session_id, adopt_stale_owner=True)
        try:
            journal = RelayJournal(backend)
            release = SyntheticRelease(backend.state_dir / "synthetic-release")
            session = cls(backend, journal, release)
            loaded = session._load_remote_durability(repo_dir=repo_dir)
            if remote_ref is not None or remote is not None:
                require(
                    bool(session.backend.owner.get("remote_authoritative")),
                    "local-only backend cannot be promoted to remote-authoritative on attach",
                )
                requested_ref = remote_ref or session._remote_ref
                requested_remote = remote or session._remote
                require(requested_ref is not None, "remote ref required for remote-authoritative attach")
                session._configure_remote_durability(
                    remote_ref=requested_ref,
                    remote=requested_remote,
                    repo_dir=repo_dir,
                    persist=False,
                )
            elif bool(session.backend.owner.get("remote_authoritative")):
                require(loaded, "remote-authoritative attach did not load its binding")
            if bool(session.backend.owner.get("remote_authoritative")):
                from .remote_backend import verify_local_remote_authority

                require(session._remote_ref is not None, "remote-authoritative attach has no remote ref")
                verify_local_remote_authority(
                    session.backend,
                    remote_ref=session._remote_ref,
                    remote=session._remote,
                    repo_dir=session._remote_repo_dir,
                )
            provider_module.ensure_provider_service(session.mailbox)
            provider_module.read_public_descriptor(session.mailbox)
            backend.audit("session_attached", {"phase": "resume"})
            return session
        except BaseException:
            backend.release()
            raise

    @classmethod
    def materialize_and_attach(
        cls,
        root: str | Path,
        *,
        run_id: str,
        session_id: str,
        remote_ref: str | None = None,
        commit_sha: str | None = None,
        remote: str = "origin",
        repo_dir: Path | None = None,
    ) -> "OperatorSession":
        """Materialize remote run state into local cache and attach."""
        backend = RunBackend.materialize_from_remote(
            run_id=run_id,
            session_id=session_id,
            target_dir=root,
            remote_ref=remote_ref,
            commit_sha=commit_sha,
            remote=remote,
            repo_dir=repo_dir,
        )
        backend.release()
        effective_ref = remote_ref
        if effective_ref is None:
            from .remote_backend import remote_ref_for_run
            effective_ref = remote_ref_for_run(run_id)
        return cls.attach(
            root,
            run_id=run_id,
            session_id=session_id,
            remote_ref=effective_ref,
            remote=remote,
            repo_dir=repo_dir,
        )

    def push_to_remote(
        self,
        *,
        remote_ref: str | None = None,
        remote: str | None = None,
        repo_dir: Path | None = None,
        message: str | None = None,
    ) -> tuple[str, str]:
        """Persist authoritative run state to the configured remote Git storage."""
        effective_ref = remote_ref or self._remote_ref
        effective_remote = remote or self._remote
        effective_repo = repo_dir or self._remote_repo_dir
        return self.backend.push_to_remote(
            remote_ref=effective_ref,
            remote=effective_remote,
            repo_dir=effective_repo,
            message=message,
        )

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

    def kill_armed(self, point: str, *, round_index: int | None = None) -> bool:
        """True when this exact (point, round) is the armed probe barrier."""
        if self._kill_at != point:
            return False
        if self._kill_round is not None and round_index != self._kill_round:
            return False
        return True

    def maybe_kill(self, point: str, *, round_index: int | None = None) -> None:
        if not self.kill_armed(point, round_index=round_index):
            return
        self.backend.audit("kill_barrier", {"point": point, "round_index": round_index})
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
        if self.remote_durability_enabled:
            self._persist_remote_barrier("K1_AFTER_REVEAL", seal_label="remote-revealed")
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
        self._persist_remote_barrier("K2_AFTER_INGEST")
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
            dispatch_report = provider_module.dispatch(self.mailbox, request_id)
            if dispatch_report["dispatch"] == "dispatched":
                self.bump("provider_dispatches")
            else:
                self.bump("provider_reattachments")
            if self.remote_durability_enabled:
                self._persist_remote_barrier(
                    "K3_AFTER_REQUEST_DISPATCH",
                    seal_label="remote-request-dispatched",
                )
            self.maybe_kill("K3_AFTER_REQUEST_DISPATCH", round_index=round_index)
        else:
            raw = self.journal.outstanding_request(request_id)
            self._write_outbox(request_id, raw, round_index=round_index)
            self.backend.audit("request_represented", {"request_id": request_id, "round": round_index})
            record = self.journal.recovery(request_id)
            if record["state"] == "exposed":
                dispatch_report = provider_module.dispatch(self.mailbox, request_id, reattach=True)
                require(
                    dispatch_report["dispatch"] == "reattached",
                    "recovery attempted a second provider dispatch",
                )
                self.bump("provider_reattachments")
            elif record["state"] in {"reply-staged", "authenticated", "applying", "applied", "acked"}:
                return request_id, bytes(record["reply"])
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
        if target.is_file():
            return
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
        report = provider_module.collect(self.mailbox, request_id)
        _append_jsonl(
            self.mailbox_archive_path,
            {"direction": "inbox", "request_id": request_id, "report": report, "at": _now()},
        )
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
        # K4 lives here: the idempotency/result ledger is durable before the
        # runtime may continue beyond the capability boundary.  In remote mode
        # that exact recovery point is synchronously published before kill.
        if self.remote_durability_enabled:
            try:
                self._persist_remote_barrier(
                    "K4_AFTER_REPLY_AUTHENTICATED",
                    seal_label="remote-capability-boundary",
                )
            except Exception as exc:
                raise RemoteDurabilityAbort(
                    f"K4 remote-authoritative persistence failed: {type(exc).__name__}: {exc}"
                ) from exc
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

    def _trusted_return_barrier(self, snapshot) -> None:
        """Publish the authenticatable provider-return boundary for every round.

        ``model_response_recorder`` runs after Core's trusted-return callback has
        atomically committed the receipt + exact return handoff and before the
        reply is recorded, metered or applied.  Publishing the authoritative
        barrier here means the last durable authoritative state before any later
        crash already contains a Core-owned trusted return, so recovery can never
        be forced into the unauthenticatable in-flight window by a barrier that
        only recorded the dispatch.

        The frozen probe kill point at this same boundary stops the process here.
        """
        round_index = int(snapshot.round_index)
        if self.remote_durability_enabled:
            self._persist_remote_barrier(
                "K3_TRUSTED_RETURN_DURABLE",
                seal_label=f"remote-trusted-return-durable-r{round_index}",
            )
        self.maybe_kill("K3_TRUSTED_RETURN_DURABLE", round_index=round_index)

    def _install_trusted_return_probe(self, runtime: FusedTurnRuntime) -> None:
        cognitive = runtime.cognitive_runtime
        recorded = cognitive.model_response_recorder
        if recorded is None:  # pragma: no cover - Core always wires this callback
            raise BackendError("trusted-return barrier requires Core's response recorder")

        def probe_recorder(snapshot, response):
            round_index = int(snapshot.round_index)
            attempt_id = str(snapshot.model_attempt_id)
            request_id = self._request_id(attempt_id, round_index)
            provider_module.collect(self.mailbox, request_id)
            proof_dict = provider_module.read_proof(self.mailbox, request_id)
            if proof_dict is not None:
                raw_reply = self._collect_reply(request_id)
                runtime.background_model_attempts.attach_late_trusted_return(
                    attempt_id=attempt_id,
                    attached_at=datetime.now(timezone.utc),
                    directive_payload=raw_reply.decode("utf-8"),
                    late_return_proof=proof_dict["authenticity_proof"],
                    evidence="k3-trusted-return-barrier",
                )
                if request_id in self._known_requests():
                    if self.journal.recovery(request_id)["state"] == "reply-staged":
                        self.journal.mark_authenticated(request_id, proof_dict)
            else:
                recorded(snapshot, response)
            self._trusted_return_barrier(snapshot)
            if self.kill_armed("K3_TRUSTED_RETURN_DURABLE", round_index=round_index):
                return
            return None

        cognitive.model_response_recorder = probe_recorder

    def _build_runtime(self) -> FusedTurnRuntime:
        store, index = self._open_store()
        runtime = FusedTurnRuntime(
            store=store,
            index=index,
            model_handler=self._model_handler,
            late_return_verifier=provider_module.route_b_verifier(self.mailbox),
            external_return_observer=provider_module.get_provider_observer(self.mailbox),
        )
        self._install_trusted_return_probe(runtime)
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

    def _record_failure(self, point: str, detail: Mapping[str, Any]) -> None:
        """Durable non-authoritative failure evidence (never a success record)."""
        record = {"synthetic": True, "point": point, "at": _now(), **dict(detail)}
        _append_jsonl(self.failures_path, record)
        self.backend.audit("failure_evidence", {"point": point, **dict(detail)})

    def _record_fail_closed_stop(self, stop: DurableTrustedReturnMissing) -> None:
        self._record_failure(
            "FAIL_CLOSED_NO_DURABLE_TRUSTED_RETURN",
            {
                "attempt_id": stop.attempt_id,
                "attempt_state": stop.attempt_state,
                "round_index": stop.round_index,
                "detail": stop.detail,
                "acks": self.counters().get("acks", 0),
            },
        )
        if not self.remote_durability_enabled:
            return
        try:
            self._persist_remote_barrier(
                "FAIL_CLOSED_NO_DURABLE_TRUSTED_RETURN",
                seal_label="remote-fail-closed-no-trusted-return",
            )
        except Exception as exc:  # evidence publication must not mask the stop
            self.backend.audit(
                "failure_evidence_push_failed", {"error": f"{type(exc).__name__}: {exc}"}
            )

    def _recover_with_core(self, projection: Mapping[str, Any]) -> list[dict[str, Any]]:
        """Reattach durable provider work to Core's own accepted recovery surfaces.

        The operator never decides authenticity.  It reattaches an already
        dispatched provider request (never a second dispatch), reads Core's own
        trusted-return receipt and lets Core's accepted exact-response/handoff
        recovery drive the turn.  A reply whose provider boundary was crossed
        without a durable trusted return is a hard fail-closed stop.
        """
        actions: list[dict[str, Any]] = []
        attempts = self.runtime.background_model_attempts
        for request_id in self.journal.request_ids(cursor=int(projection["sequence"])):
            record = self.journal.recovery(request_id)
            if record["state"] == "staged":
                continue
            if record["state"] == "exposed":
                dispatch_report = provider_module.dispatch(self.mailbox, request_id)
                require(
                    dispatch_report["dispatch"] == "reattached",
                    "K3 recovery attempted a second provider dispatch",
                )
                self.bump("provider_reattachments")
                reply = self._collect_reply(request_id)
                self.journal.stage_reply(request_id, reply)
                record = self.journal.recovery(request_id)
                actions.append({"request_id": request_id, "action": "provider_reply_reattached"})
            if record["state"] in {"applied", "acked"}:
                continue
            attempt_id = str(record["metadata"]["attempt_id"])
            round_index = int(record["metadata"]["round"])
            payload = bytes(record["reply"]).decode("utf-8")
            directive = decode_model_directive(payload)
            attempt = attempts.get(attempt_id)
            if attempt is None:
                # K3 can fire after provider submission while the Core attempt
                # transaction is not present in the surviving/restored runtime DB.
                # Do not fabricate an attempt or an authenticity receipt. Keep the
                # exact provider reply durable, then let the normal run_turn path
                # re-admit the deterministic attempt identity. When model_handler
                # is reached again, _relay_exchange returns these exact staged bytes
                # without a second provider dispatch and Core's ordinary trusted
                # return callback mints the receipt.
                actions.append(
                    {
                        "request_id": request_id,
                        "action": "core_attempt_missing_safe_readmit",
                    }
                )
                if self.remote_durability_enabled:
                    self._persist_remote_barrier(
                        "K3_PROVIDER_RETURN_STAGED_CORE_READMIT_PENDING",
                        seal_label="remote-provider-return-staged",
                    )
                continue
            receipt = attempts.response_authenticity_receipt(attempt_id)
            if receipt is None:
                if attempt.state in {"admitted", "not_submitted"}:
                    # Dispatch provably did not start for this attempt: the ordinary
                    # path may still dispatch once, and the relay re-presents the
                    # durable bytes if this round's request was already staged.
                    actions.append(
                        {
                            "request_id": request_id,
                            "action": "core_dispatch_not_started",
                            "attempt_state": str(attempt.state),
                        }
                    )
                    continue
                # The provider boundary was crossed and no Core-owned trusted
                # return exists (e.g. killed during dispatching or in_doubt, or killed
                # before K3_TRUSTED_RETURN_DURABLE).
                # Accepted Core has no legal continuation here:
                # caller-supplied bytes cannot become a trusted provider
                # return, and blind redispatch is forbidden. Hard stop.
                stop = DurableTrustedReturnMissing(
                    attempt_id=attempt_id,
                    state=str(attempt.state),
                    round_index=round_index,
                    detail=(
                        "provider boundary crossed without a durable trusted "
                        "return; refusing redispatch and refusing invented "
                        "authenticity"
                    ),
                )
                self._record_fail_closed_stop(stop)
                raise stop
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
                if self.remote_durability_enabled:
                    self._persist_remote_barrier(
                        "K3_RECOVERED_PROVIDER_RETURN",
                        seal_label="remote-provider-return-recovered",
                    )
            actions.append(
                {
                    "request_id": request_id,
                    "action": "core_trusted_return_durable",
                    "attempt_state": str(attempt.state),
                    "model_round_index": round_index,
                    "staged": attempts.staged_response(attempt_id) is not None,
                }
            )
            if self.journal.recovery(request_id)["state"] == "authenticated":
                self.journal.begin_applying(request_id)
                actions.append({"request_id": request_id, "action": "applying"})
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
            if receipt is not None:
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
            else:
                attempt = attempts.get(attempt_id)
                if attempt is not None and attempt.state in {"response_returned", "metered"}:
                    if record["state"] in {"reply-staged", "authenticated", "applying"}:
                        self.journal.mark_applied(request_id)
                        actions.append({"request_id": request_id, "action": "applied"})
                else:
                    actions.append({"request_id": request_id, "action": "no_core_receipt"})
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
        self._persist_remote_barrier("K5_AFTER_APPLIED_BEFORE_ACK")
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
        self._persist_remote_barrier("ACKED")
        return report

    # ------------------------------------------------------------ the loop

    def process_one_cursor(
        self, *, kill_at: str | None = None, kill_round: int | None = None
    ) -> dict[str, Any]:
        self._kill_at = kill_at
        self._kill_round = kill_round
        if kill_round is not None:
            require(kill_at in K3_POINTS, "kill_round is only valid for the K3 boundaries")
            require(kill_round >= 0, "kill_round must be non-negative")
        if kill_at is not None and kill_at not in KILL_POINTS:
            raise BackendError(f"unknown kill point: {kill_at}")
        projection = self.reveal()
        receipt = self.ingest(projection)
        turn = self.run_turn(projection)
        ack = self.ack(projection, receipt)
        return {"projection": projection, "ingest": receipt, "turn": turn, "ack": ack}

    def resume(
        self, *, kill_at: str | None = None, kill_round: int | None = None
    ) -> dict[str, Any]:
        """Re-enter the same loop in a fresh process. Every step re-derives."""
        self.backend.audit("resume_started", {"kill_at": kill_at or "none", "kill_round": kill_round})
        return self.process_one_cursor(kill_at=kill_at, kill_round=kill_round)

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
