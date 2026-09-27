"""Production operator relay journal for C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001.

Scope and authority
-------------------
This is the *operator* durability layer that the frozen WIP prototype
(``tools/c15_persistence/journal.py``, preserved verbatim for the historical red
evidence) was never wired into.  It stores **bytes** and **state labels**.  It is
explicitly not a second semantic engine:

* it never interprets a ``ModelDirective``;
* it never executes capability semantics;
* it never produces assistant output;
* it never declares a response authentic - only Core validates the authoritative
  receipt (``verify_with_core`` below is a *read-only* cross-check that asks Core
  and refuses when Core disagrees);
* it never declares a response applied - ``applied`` means "Core's own runtime
  completed the turn against this attempt", recorded by the operator from Core's
  result, never asserted by the journal;
* it never rewrites ``in_doubt`` into ``not_submitted`` and never rewrites an
  attempt's state.

State machine (fail-closed, forward only)::

    staged -> exposed -> reply-staged -> authenticated -> applying -> applied -> acked

``staged``        exact request bytes are durable, nothing has left the operator.
``exposed``       request bytes were handed to the provider channel; a lost
                  delivery acknowledgement is NOT permission to expose again.
``reply-staged``  exact reply bytes are durable but NOT authenticated.
``authenticated`` the exact reply bytes were accepted by Core's trusted-return
                  boundary; the Core-issued authenticity proof is stored.
``applying``      Core is applying the directive through normal runtime.
``applied``       Core completed application (assistant output / capability work
                  and metering are durable in World).
``acked``         the release operator durably advanced the cursor.

An interrupted ``applying`` row is ``IN_DOUBT_STOP`` forever unless Core itself
proves the attempt reached ``response_returned``/``metered``; the operator may
not relabel it.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import PurePosixPath
from typing import Any, Iterator, Mapping, Sequence

from .backend import BackendError, RunBackend, canonical_json, digest, fsync_dir, require

STATES: tuple[str, ...] = (
    "staged",
    "exposed",
    "reply-staged",
    "authenticated",
    "applying",
    "applied",
    "acked",
)

#: Dispositions reported to the operator. None of these is a convergence claim.
DISPOSITIONS: dict[str, str] = {
    "staged": "EXPOSURE_PERMITTED",
    "exposed": "REPRESENT_OUTSTANDING_REQUEST",
    "reply-staged": "AUTHENTICATE_WITH_CORE",
    "authenticated": "APPLY_THROUGH_CORE",
    "applying": "IN_DOUBT_STOP",
    "applied": "ACK_PERMITTED",
    "acked": "CURSOR_ACKED",
}

#: Metadata required for every staged request. Missing/incomplete metadata is a
#: hard failure: an anonymous request cannot be proven unique on resume.
REQUEST_FIELDS: tuple[str, ...] = (
    "run_id",
    "session_id",
    "cursor",
    "event_id",
    "round",
    "model_request_id",
    "attempt_id",
    "nonce",
    "request_fingerprint",
    "binding_digest",
    "provider",
    "model",
)

REQUIRED_ARTIFACT_SLOTS: frozenset[str] = frozenset(
    {
        "runtime/world.sqlite",
        "runtime/index.sqlite",
        "runtime/release_state.json",
        "current-event.json",
        "binding/current-event-binding.json",
        "evidence/projection.json",
        "evidence/failures.jsonl",
        "mailbox/archive.jsonl",
    }
)

SCHEMA = """
CREATE TABLE identity(
    run TEXT NOT NULL,
    session TEXT NOT NULL,
    backend_version TEXT NOT NULL,
    created_at_epoch REAL NOT NULL
);
CREATE TABLE relay(
    request_id TEXT PRIMARY KEY,
    attempt_id TEXT NOT NULL,
    round_index INTEGER NOT NULL,
    metadata BLOB NOT NULL,
    metadata_sha TEXT NOT NULL,
    generation INTEGER NOT NULL,
    request BLOB NOT NULL,
    request_sha TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN
        ('staged','exposed','reply-staged','authenticated','applying','applied','acked')),
    reply BLOB,
    reply_sha TEXT,
    core_receipt BLOB,
    core_receipt_sha TEXT,
    ack_receipt BLOB,
    ack_receipt_sha TEXT,
    updated_at_epoch REAL NOT NULL,
    exposures INTEGER NOT NULL DEFAULT 0,
    dispatches INTEGER NOT NULL DEFAULT 0,
    UNIQUE(attempt_id, round_index)
);
CREATE TABLE audit(
    id INTEGER PRIMARY KEY,
    request_id TEXT NOT NULL,
    state TEXT NOT NULL,
    at_epoch REAL NOT NULL,
    pid INTEGER NOT NULL,
    note TEXT
);
CREATE TABLE ledger(
    name TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class RelayJournal:
    """Durable provider relay journal over an owned :class:`RunBackend`."""

    def __init__(self, backend: RunBackend, *, create: bool = False) -> None:
        require(isinstance(backend, RunBackend), "relay journal requires an owned backend")
        self.backend = backend
        self.path = backend.journal_path
        if create:
            require(not self.path.exists(), "journal already exists; creation never adopts")
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
            with self._connect() as db:
                db.executescript(SCHEMA)
                db.execute(
                    "INSERT INTO identity VALUES (?,?,?,?)",
                    (
                        backend.owner["run_id"],
                        backend.owner["session_id"],
                        "c15-persistence-relay-v1",
                        time.time(),
                    ),
                )
            fsync_dir(self.backend.root)
        require(self.path.is_file() and not self.path.is_symlink(), "journal missing")
        with self._connect() as db:
            require(
                db.execute("PRAGMA quick_check").fetchall() == [("ok",)],
                "journal corruption",
            )
            row = db.execute("SELECT run, session FROM identity").fetchone()
            require(row is not None, "journal identity missing")
            require(
                (row[0], row[1]) == (backend.owner["run_id"], backend.owner["session_id"]),
                "journal run/session identity mismatch",
            )

    # ------------------------------------------------------------ connection

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=30)
        try:
            db.execute("PRAGMA journal_mode=DELETE")
            db.execute("PRAGMA synchronous=EXTRA")
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    # -------------------------------------------------------------- internal

    @staticmethod
    def _row(db: sqlite3.Connection, request_id: str) -> sqlite3.Row:
        db.row_factory = sqlite3.Row
        row = db.execute("SELECT * FROM relay WHERE request_id=?", (request_id,)).fetchone()
        require(row is not None, "unknown relay request")
        require(digest(bytes(row["request"])) == row["request_sha"], "request corruption")
        require(
            digest(bytes(row["metadata"])) == row["metadata_sha"], "relay metadata corruption"
        )
        if row["reply"] is not None:
            require(digest(bytes(row["reply"])) == row["reply_sha"], "reply corruption")
        if row["core_receipt"] is not None:
            require(
                digest(bytes(row["core_receipt"])) == row["core_receipt_sha"],
                "core receipt corruption",
            )
        if row["ack_receipt"] is not None:
            require(
                digest(bytes(row["ack_receipt"])) == row["ack_receipt_sha"],
                "ack receipt corruption",
            )
        return row

    def _transition(
        self,
        db: sqlite3.Connection,
        request_id: str,
        state: str,
        *,
        note: str | None = None,
    ) -> None:
        require(state in STATES, "unknown relay state")
        db.execute(
            "UPDATE relay SET state=?, updated_at_epoch=? WHERE request_id=?",
            (state, time.time(), request_id),
        )
        db.execute(
            "INSERT INTO audit(request_id,state,at_epoch,pid,note) VALUES (?,?,?,?,?)",
            (request_id, state, time.time(), os.getpid(), note),
        )

    def _ledger_get(self, db: sqlite3.Connection, name: str) -> str | None:
        row = db.execute("SELECT value FROM ledger WHERE name=?", (name,)).fetchone()
        return None if row is None else str(row[0])

    def _ledger_put(self, db: sqlite3.Connection, name: str, value: str) -> None:
        db.execute(
            "INSERT INTO ledger(name,value) VALUES (?,?) "
            "ON CONFLICT(name) DO UPDATE SET value=excluded.value",
            (name, value),
        )

    # ----------------------------------------------------------------- write

    def stage(
        self,
        metadata: Mapping[str, Any],
        request: bytes,
        *,
        generation: int,
    ) -> None:
        """Durably stage exact outbound request bytes before any exposure."""
        missing = [key for key in REQUEST_FIELDS if key not in metadata]
        require(not missing, f"incomplete relay metadata: {sorted(missing)}")
        extra = sorted(set(metadata) - set(REQUEST_FIELDS))
        require(not extra, f"unexpected relay metadata: {extra}")
        for key in REQUEST_FIELDS:
            value = metadata[key]
            if key == "cursor":
                require(type(value) is int and value > 0, f"relay {key} must be a positive int")
            elif key == "round":
                # Core model rounds are zero-indexed; round 0 is the first round.
                require(type(value) is int and value >= 0, f"relay {key} must be a non-negative int")
            else:
                require(isinstance(value, str) and bool(value.strip()), f"relay {key} must be non-blank")
        require(type(request) is bytes and bool(request), "request must be exact bytes")
        require(
            metadata["run_id"] == self.backend.owner["run_id"],
            "relay run identity does not match backend",
        )
        require(
            metadata["session_id"] == self.backend.owner["session_id"],
            "relay session identity does not match backend",
        )
        request_id = metadata["model_request_id"]
        blob = canonical_json(metadata)
        with self._connect() as db:
            self._row_or_none(db, request_id)
            clash = db.execute(
                "SELECT request_id FROM relay WHERE attempt_id=? AND round_index=?",
                (str(metadata["attempt_id"]), int(metadata["round"])),
            ).fetchone()
            require(
                clash is None,
                "relay request already exists for this attempt/round; "
                "no restaging and no second dispatch",
            )
            db.execute(
                "INSERT INTO relay(request_id,attempt_id,round_index,metadata,metadata_sha,"
                "generation,request,request_sha,state,updated_at_epoch) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    request_id,
                    str(metadata["attempt_id"]),
                    int(metadata["round"]),
                    blob,
                    digest(blob),
                    int(generation),
                    request,
                    digest(request),
                    "staged",
                    time.time(),
                ),
            )
            self._transition(db, request_id, "staged", note="exact request bytes durable")
        fsync_dir(self.backend.root)

    def _row_or_none(self, db: sqlite3.Connection, request_id: str) -> None:
        row = db.execute(
            "SELECT request_id FROM relay WHERE request_id=?", (request_id,)
        ).fetchone()
        require(row is None, "relay request identity already exists")

    def expose(self, request_id: str) -> bytes:
        """Mark the request exposed and return its exact bytes, once."""
        with self._connect() as db:
            row = self._row(db, request_id)
            require(row["state"] == "staged", "request is not staged; refusing second exposure")
            db.execute(
                "UPDATE relay SET exposures=exposures+1, dispatches=dispatches+1 "
                "WHERE request_id=?",
                (request_id,),
            )
            self._transition(db, request_id, "exposed", note="bytes may leave the operator")
            raw = bytes(row["request"])
        return raw

    def outstanding_request(self, request_id: str) -> bytes:
        """Re-present an already-exposed request. Never a second dispatch."""
        with self._connect() as db:
            row = self._row(db, request_id)
            require(
                row["state"] in {"exposed", "reply-staged", "authenticated", "applying", "applied", "acked"},
                "request was never exposed; refusing to invent an outstanding request",
            )
            db.execute(
                "UPDATE relay SET updated_at_epoch=? WHERE request_id=?",
                (time.time(), request_id),
            )
            db.execute(
                "INSERT INTO audit(request_id,state,at_epoch,pid,note) VALUES (?,?,?,?,?)",
                (request_id, row["state"], time.time(), os.getpid(), "re-presented after restart"),
            )
            raw = bytes(row["request"])
        return raw

    def stage_reply(self, request_id: str, reply: bytes) -> None:
        """Durably store exact reply bytes. Authentication is Core's job, not ours."""
        require(type(reply) is bytes and bool(reply), "reply must be exact bytes")
        with self._connect() as db:
            row = self._row(db, request_id)
            if row["reply"] is not None:
                require(
                    bytes(row["reply"]) == reply,
                    "conflicting reply bytes; preserving the original",
                )
                return  # identical redelivery is not a second semantic event
            require(row["state"] == "exposed", "reply arrived before exposure")
            db.execute(
                "UPDATE relay SET reply=?,reply_sha=? WHERE request_id=?",
                (reply, digest(reply), request_id),
            )
            self._transition(db, request_id, "reply-staged", note="exact reply bytes durable")
        fsync_dir(self.backend.root)

    def mark_authenticated(self, request_id: str, core_receipt: Mapping[str, Any]) -> None:
        """Record the Core-issued authenticity proof.

        The operator *stores* the receipt; it does not validate it.  Only Core
        can attest that these exact bytes crossed the trusted return path.
        """
        blob = canonical_json(core_receipt)
        with self._connect() as db:
            row = self._row(db, request_id)
            require(row["state"] == "reply-staged", "authentication requires a staged reply")
            if row["core_receipt"] is not None:
                require(
                    bytes(row["core_receipt"]) == blob,
                    "conflicting Core authenticity receipt",
                )
                return
            db.execute(
                "UPDATE relay SET core_receipt=?,core_receipt_sha=? WHERE request_id=?",
                (blob, digest(blob), request_id),
            )
            self._transition(db, request_id, "authenticated", note="core receipt recorded")
        fsync_dir(self.backend.root)

    def begin_applying(self, request_id: str) -> bytes:
        with self._connect() as db:
            row = self._row(db, request_id)
            require(row["state"] == "authenticated", "application requires an authenticated reply")
            self._transition(db, request_id, "applying", note="core application started")
            raw = bytes(row["reply"])
        return raw

    def mark_applied(self, request_id: str, *, note: str = "core application completed") -> None:
        with self._connect() as db:
            row = self._row(db, request_id)
            require(
                row["state"] in {"authenticated", "applying", "applied"},
                "application was not authorised by Core; refusing to assert it",
            )
            if row["state"] == "applied":
                return  # idempotent; never a second application
            self._transition(db, request_id, "applied", note=note)
        fsync_dir(self.backend.root)

    def mark_acked(self, request_id: str, ack_receipt: Mapping[str, Any]) -> None:
        blob = canonical_json(ack_receipt)
        with self._connect() as db:
            row = self._row(db, request_id)
            require(row["state"] == "applied", "ack requires a durable application")
            if row["ack_receipt"] is not None:
                require(
                    bytes(row["ack_receipt"]) == blob,
                    "conflicting ack receipt; cursor already advanced",
                )
                return
            db.execute(
                "UPDATE relay SET ack_receipt=?,ack_receipt_sha=? WHERE request_id=?",
                (blob, digest(blob), request_id),
            )
            self._transition(db, request_id, "acked", note="cursor advanced exactly once")
        fsync_dir(self.backend.root)

    # ------------------------------------------------------------------ read

    def recovery(self, request_id: str) -> dict[str, Any]:
        """Report durable recovery state. Never a convergence claim by itself."""
        with self._connect() as db:
            row = self._row(db, request_id)
            state = str(row["state"])
            return {
                "state": state,
                "disposition": DISPOSITIONS[state],
                "metadata": json.loads(bytes(row["metadata"]).decode("utf-8")),
                "generation": int(row["generation"]),
                "request": bytes(row["request"]),
                "request_sha256": str(row["request_sha"]),
                "reply": None if row["reply"] is None else bytes(row["reply"]),
                "reply_sha256": None if row["reply_sha"] is None else str(row["reply_sha"]),
                "core_receipt": None
                if row["core_receipt"] is None
                else json.loads(bytes(row["core_receipt"]).decode("utf-8")),
                "ack_receipt": None
                if row["ack_receipt"] is None
                else json.loads(bytes(row["ack_receipt"]).decode("utf-8")),
                "exposures": int(row["exposures"]),
                "dispatches": int(row["dispatches"]),
            }

    def terminal_request_id(self) -> str | None:
        """Highest-round request: the one whose directive produced the output."""
        with self._connect() as db:
            row = db.execute(
                "SELECT request_id FROM relay ORDER BY round_index DESC, rowid DESC LIMIT 1"
            ).fetchone()
            return None if row is None else str(row[0])

    def request_ids(self) -> list[str]:
        with self._connect() as db:
            return [str(r[0]) for r in db.execute(
                "SELECT request_id FROM relay ORDER BY round_index, rowid").fetchall()]

    def current_request_id(self) -> str | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT request_id FROM relay ORDER BY rowid DESC LIMIT 1"
            ).fetchone()
            return None if row is None else str(row[0])

    def audit_trail(self, request_id: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as db:
            if request_id is None:
                rows = db.execute(
                    "SELECT request_id,state,at_epoch,pid,note FROM audit ORDER BY id"
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT request_id,state,at_epoch,pid,note FROM audit "
                    "WHERE request_id=? ORDER BY id",
                    (request_id,),
                ).fetchall()
        return [
            {
                "request_id": r[0],
                "state": r[1],
                "at_epoch": r[2],
                "pid": r[3],
                "note": r[4],
            }
            for r in rows
        ]

    # --------------------------------------------------------- Core handoff

    def verify_with_core(self, request_id: str, attempts: Any) -> dict[str, Any]:
        """Cross-check the recorded receipt against Core. Core is the authority.

        ``attempts`` is a ``BackgroundModelAttemptStore``.  This method asks Core
        what it knows and refuses on any disagreement; it never upgrades the
        journal state and never mints a receipt.
        """
        record = self.recovery(request_id)
        attempt_id = str(record["metadata"]["attempt_id"])
        receipt = attempts.response_authenticity_receipt(attempt_id)
        require(receipt is not None, "Core holds no authenticity receipt for this attempt")
        core_proof = getattr(receipt, "authenticity_proof", None)
        require(isinstance(core_proof, str) and core_proof.strip(), "Core receipt proof is blank")
        stored = record["core_receipt"] or {}
        require(
            str(stored.get("authenticity_proof", "")) == core_proof,
            "operator-stored receipt does not match Core's authoritative receipt",
        )
        staged = attempts.staged_response(attempt_id)
        require(staged is not None, "Core holds no staged exact response for this attempt")
        require(
            str(getattr(staged, "response_fingerprint", "")) == str(stored.get("response_fingerprint", "")),
            "Core staged response fingerprint does not match the operator record",
        )
        return {
            "attempt_id": attempt_id,
            "core_proof": core_proof,
            "core_state": str(getattr(attempts.get(attempt_id), "state", "unknown")),
            "verified": True,
        }

    def ledger(self) -> dict[str, str]:
        with self._connect() as db:
            return {name: value for name, value in db.execute("SELECT name,value FROM ledger")}

    def ledger_set(self, name: str, value: str) -> None:
        with self._connect() as db:
            self._ledger_put(db, name, value)

    def ledger_get(self, name: str) -> str | None:
        with self._connect() as db:
            return self._ledger_get(db, name)
