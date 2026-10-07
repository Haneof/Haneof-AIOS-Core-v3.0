"""Resident-visible surface: "the persistence layer changed nothing" proof.

Adding a durability layer underneath a live Core run is only safe if it leaves
the *Resident-visible* surface untouched.  This checker measures that surface
twice for the same synthetic event:

``wired``
    the production path - ``OperatorSession`` with ``RunBackend`` +
    ``RelayJournal`` + sealed generations, every provider request and reply
    durable and byte-exact.

``control``
    the same Core ``FusedTurnRuntime``, the same capability registry, the same
    model handler outcome, the same world and the same event - but with **no**
    ``RunBackend``, **no** ``RelayJournal``, **no** generation sealing and no
    kill barriers.

If the two agree byte-for-byte on everything the Resident (and the model) can
observe, the durability layer is proven non-semantic.

Usage::

    PYTHONPATH=src:. python3 -m tools.c15_persistence.resident_surface_check \\
        --out <evidence.json>            # writes the JSON evidence + prints a digest
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from aios_core.runtime.background_attempt import BackgroundModelAttemptStore  # noqa: E402
from aios_core.runtime.capabilities import CapabilityKind, CapabilitySpec  # noqa: E402
from aios_core.runtime import ModelDirective  # noqa: E402
from aios_core.runtime.turn_runtime import FusedTurnRuntime  # noqa: E402
from aios_core.storage.sqlite_store import SQLiteWorldStore  # noqa: E402
from aios_core.query.search import WorldSearchIndex  # noqa: E402

from . import provider as provider_module  # noqa: E402
from .backend import digest  # noqa: E402
from .operator_session import (  # noqa: E402
    MODEL_NAME,
    PROVIDER_NAME,
    OperatorSession,
    request_envelope,
)
from aios_core.runtime.background_attempt import decode_model_directive  # noqa: E402
from .runstate import REQUIRED_SLOTS  # noqa: E402
from .synthetic_release import SUBJECT_ID, SyntheticRelease  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
PINNED_PATHS = (
    "src/aios_core",
    "reviews/internal_habitation/c15-rcc/v1",
    "reviews/internal_habitation/c14-resident/v2/release",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _catalog(runtime: FusedTurnRuntime) -> list[dict[str, Any]]:
    """The model-facing capability catalog Core itself exposes."""
    return [
        {
            "name": str(row.get("name", "")),
            "description": str(row.get("description", "") or ""),
            "kind": str(row.get("kind", "")),
            "input_schema": json.loads(json.dumps(row.get("input_schema") or {}, sort_keys=True)),
            "hard_boundary": bool(row.get("hard_boundary", False)),
            "side_effecting": bool(row.get("side_effecting", False)),
        }
        for row in runtime.registry.catalog()
    ]


def _nonce(*, attempt_id: str, round_index: int, run_id: str) -> str:
    return hashlib.sha256(f"{attempt_id}:{round_index}:{run_id}".encode()).hexdigest()[:32]


def _request_id(attempt_id: str, round_index: int) -> str:
    return f"synthetic-request-{hashlib.sha256(f'{attempt_id}:{round_index}'.encode()).hexdigest()[:24]}"


# --------------------------------------------------------------------- control


class _ControlSession:
    """Canonical Core path with no operator durability layer at all."""

    def __init__(self, root: Path, run_id: str, session_id: str) -> None:
        self.root = root
        self.run_id = run_id
        self.session_id = session_id
        # Identical to OperatorSession: Core's conversation session is derived
        # from the run id, so the attempt ids (and therefore the exact request
        # bytes) line up with the wired path.
        self._session_id = f"{run_id}-conv"
        self.world_path = root / "runtime" / "world.sqlite"
        self.binding_path = root / "binding" / "current-event-binding.json"
        self.current_event_path = root / "current-event.json"
        self.mailbox = root / "mailbox"
        self.calls: list[dict[str, Any]] = []
        self.capability_calls: list[dict[str, Any]] = []
        self.world_path.parent.mkdir(parents=True, exist_ok=True)
        SQLiteWorldStore(self.world_path)
        self.release = SyntheticRelease(root / "synthetic-release")
        self.release_state_path = root / "runtime" / "release_state.json"
        self.release_state_path.parent.mkdir(parents=True, exist_ok=True)
        self.release.init_state(self.release_state_path)

    # -- the same three lifecycle steps, straight against the frozen operator
    def reveal(self) -> dict[str, Any]:
        projection = self.release.reveal(self.release_state_path)
        self.current_event_path.parent.mkdir(parents=True, exist_ok=True)
        self.current_event_path.write_text(json.dumps(projection, sort_keys=True) + "\n")
        return projection

    def ingest(self, projection: dict[str, Any]) -> dict[str, Any]:
        return self.release.ingest(self.world_path, projection)

    # -- Core runtime, wired exactly like the operator but with no relay
    def _build_runtime(self) -> FusedTurnRuntime:
        store = SQLiteWorldStore(self.world_path)
        index = WorldSearchIndex(self.world_path, store=store)
        index.rebuild()
        runtime = FusedTurnRuntime(
            store=store,
            index=index,
            model_handler=self._model_handler,
            late_return_verifier=provider_module.route_b_verifier(),
        )
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

    def _capability_handler(self, *, attempt_id: str, round: int) -> dict[str, Any]:
        key = f"{attempt_id}:{round}"
        self.capability_calls.append(key)
        return {"result": {"executed": key, "round": round}, "duplicate_suppressed": False}

    def _attempt_id(self, runtime: FusedTurnRuntime, turn_index: int, round_index: int) -> str:
        execution_id = runtime.turn_executions.execution_id_for(
            subject_id=runtime.subject_id,
            session_id=self._session_id,
            turn_index=turn_index,
        )
        return BackgroundModelAttemptStore.attempt_id_for(
            subject_id=runtime.subject_id,
            work_kind="user_turn",
            work_id=execution_id,
            model_round_index=round_index,
        )

    def _model_handler(self, snapshot) -> Any:
        round_index = int(snapshot.round_index)
        runtime = self.runtime
        attempt_id = str(snapshot.model_attempt_id)
        projection = json.loads(self.current_event_path.read_text())
        request_id = _request_id(attempt_id, round_index)
        binding_digest = (
            digest(self.binding_path.read_bytes()) if self.binding_path.is_file() else digest(b"{}")
        )
        request, _metadata = request_envelope(
            run_id=self.run_id,
            session_id=self.session_id,
            attempt_id=attempt_id,
            request_id=request_id,
            round_index=round_index,
            cursor=int(projection["sequence"]),
            event_id=str(projection["event_id"]),
            payload=str(projection["resident_visible_payload"]),
            nonce=_nonce(attempt_id=attempt_id, round_index=round_index, run_id=self.run_id),
            binding_digest=binding_digest,
        )
        # Same provider protocol as the wired path: exact request bytes into the
        # durable outbox, one answer per request id, reply read back verbatim.
        self.mailbox.mkdir(parents=True, exist_ok=True)
        outbox = provider_module.outbox_path(self.mailbox, request_id)
        outbox.parent.mkdir(parents=True, exist_ok=True)
        outbox.write_bytes(request)
        provider_module.serve(self.mailbox, request_id)
        reply = provider_module.inbox_path(self.mailbox, request_id).read_bytes()
        directive = decode_model_directive(reply.decode("utf-8"))
        self.calls.append(
            {
                "round": round_index,
                "attempt_id": attempt_id,
                "request_sha256": hashlib.sha256(request).hexdigest(),
                "reply_sha256": hashlib.sha256(reply).hexdigest(),
                "directive_sha256": hashlib.sha256(
                    json.dumps(_directive_shape(directive), sort_keys=True).encode()
                ).hexdigest(),
            }
        )
        return directive

    def run(self) -> dict[str, Any]:
        projection = self.reveal()
        receipt = self.ingest(projection)
        self.runtime = self._build_runtime()
        occurred_at = datetime.fromisoformat(str(projection["occurred_at"]))
        result = self.runtime.run_turn(
            session_id=self._session_id,
            turn_index=int(projection["sequence"]),
            user_input=str(projection["resident_visible_payload"]),
            occurred_at=occurred_at,
        )
        return {
            "projection": projection,
            "ingest": receipt,
            "response": str(result.runtime.response),
            "calls": self.calls,
            "capability_calls": self.capability_calls,
            "catalog": _catalog(self.runtime),
            "metering_rows": len(
                self.runtime.metering.list_model_calls(subject_id=self.runtime.subject_id)
            ),
            "world_revision": int(self.runtime.store.current_world_revision()),
        }


def _directive_shape(directive: Any) -> Any:
    """Everything the operator could observe about a directive - never interpreted."""
    return directive.model_dump(mode="json") if hasattr(directive, "model_dump") else str(directive)


# ----------------------------------------------------------------------- wired


def _run_wired(root: Path, run_id: str, session_id: str) -> dict[str, Any]:
    from .backend import RunBackend
    from .relay import RelayJournal

    backend = RunBackend.create(root, run_id=run_id, session_id=session_id,
                                subject_id=SUBJECT_ID, phase="A")
    journal = RelayJournal(backend, create=True)
    backend.release()
    session = OperatorSession(backend, journal, SyntheticRelease(root.parent / "synthetic-release"))
    session.prepare_world()
    session.ensure_release_initialized()
    projection = session.reveal()
    receipt = session.ingest(projection)
    turn = session.run_turn(projection)
    session.ack(projection, receipt)
    calls: list[dict[str, Any]] = []
    for request_id in journal.request_ids(cursor=int(projection["sequence"])):
        record = journal.recovery(request_id)
        calls.append(
            {
                "round": int(record["metadata"]["round"]),
                "attempt_id": str(record["metadata"]["attempt_id"]),
                "request_sha256": hashlib.sha256(bytes(record["request"])).hexdigest(),
                "reply_sha256": hashlib.sha256(bytes(record["reply"])).hexdigest(),
                "directive_sha256": hashlib.sha256(
                    json.dumps(
                        _directive_shape(decode_model_directive(bytes(record["reply"]).decode("utf-8"))),
                        sort_keys=True,
                    ).encode()
                ).hexdigest(),
            }
        )
    return {
        "projection": projection,
        "ingest": receipt,
        "response": turn.get("response") or "",
        "calls": sorted(calls, key=lambda row: row["round"]),
        "capability_calls": [
            str(row.get("key")) for row in _read_jsonl_rows(session.capability_ledger_path)
        ],
        "catalog": _catalog(session.runtime),
        "metering_rows": session.metering_rows(),
        "world_revision": int(session.runtime.store.current_world_revision()),
        "_session": session,
    }


# ------------------------------------------------------------------------ main


def _pinned_tree_digest(base: str) -> dict[str, Any]:
    verify_base = subprocess.run(
        ["git", "rev-parse", "--verify", f"{base}^{{commit}}"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if verify_base.returncode != 0:
        raise ValueError(
            f"base ref {base!r} does not resolve to a valid commit: {verify_base.stderr.strip()}"
        )
    out: dict[str, Any] = {"base": base}
    for scope in PINNED_PATHS:
        completed = subprocess.run(
            ["git", "diff", "--stat", f"{base}...HEAD", "--", scope],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"git diff failed for scope {scope}: {completed.stderr.strip()}"
            )
        out[scope] = {
            "diff": completed.stdout.strip(),
            "clean": completed.stdout.strip() == "",
        }
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="where to write the JSON evidence")
    parser.add_argument("--base", default="main", help="git ref to diff the pinned trees against")
    parser.add_argument(
        "--work-root",
        default=None,
        help="durable (non-ephemeral) scratch root for the two runs",
    )
    args = parser.parse_args(argv)

    work_root = Path(
        args.work_root
        or Path(os.environ.get("C15_PERSISTED_WORKSPACE") or Path.home())
        / "c15-persistence-runs"
        / "resident-surface"
    )
    if work_root.exists():
        shutil.rmtree(work_root, ignore_errors=True)
    work_root.mkdir(parents=True, exist_ok=True)

    run_id = f"synthetic-run-surface-{uuid.uuid4().hex[:8]}"
    session_id = f"synthetic-session-surface-{uuid.uuid4().hex[:8]}"

    control_root = work_root / "control"
    control_root.mkdir(parents=True, exist_ok=True)
    control = _ControlSession(control_root, run_id, session_id).run()

    wired_root = work_root / "wired"
    wired_root.mkdir(parents=True, exist_ok=True)
    wired = _run_wired(wired_root / "backend", run_id, session_id)

    comparisons = {
        "resident_visible_payload": (
            control["projection"]["resident_visible_payload"]
            == wired["projection"]["resident_visible_payload"]
        ),
        "projection": control["projection"] == wired["projection"],
        "ingest_receipt": control["ingest"] == wired["ingest"],
        "capability_catalog": control["catalog"] == wired["catalog"],
        "model_round_ordering": [c["round"] for c in control["calls"]]
        == [c["round"] for c in wired["calls"]],
        "provider_request_bytes": [c["request_sha256"] for c in control["calls"]]
        == [c["request_sha256"] for c in wired["calls"]],
        "provider_reply_bytes": [c["reply_sha256"] for c in control["calls"]]
        == [c["reply_sha256"] for c in wired["calls"]],
        "directive_semantics": [c["directive_sha256"] for c in control["calls"]]
        == [c["directive_sha256"] for c in wired["calls"]],
        "capability_side_effect_count": len(control["capability_calls"])
        == int(wired["_session"].counters().get("capability_side_effects", -1)),
        "assistant_output": control["response"] == str(
            wired["_session"].journal.ledger_get("assistant_output_1") or ""
        ),
        "metering_rows": control["metering_rows"] == wired["metering_rows"],
        "world_revision": control["world_revision"] == wired["world_revision"],
    }

    pinned = _pinned_tree_digest(args.base)
    ok = all(comparisons.values()) and all(scope["clean"] for scope in
                                           (v for k, v in pinned.items() if isinstance(v, dict)))

    evidence = {
        "check": "RESIDENT_VISIBLE_SURFACE_UNCHANGED",
        "run_id": run_id,
        "session_id": session_id,
        "control": {
            "calls": control["calls"],
            "catalog": control["catalog"],
            "metering_rows": control["metering_rows"],
            "world_revision": control["world_revision"],
            "response_sha256": hashlib.sha256(control["response"].encode()).hexdigest(),
            "capability_calls": control["capability_calls"],
        },
        "wired": {
            "calls": wired["calls"],
            "catalog": wired["catalog"],
            "metering_rows": wired["metering_rows"],
            "world_revision": wired["world_revision"],
            "counters": wired["_session"].counters(),
            "journal_states": {
                rid: wired["_session"].journal.recovery(rid)["state"]
                for rid in wired["_session"].journal.request_ids()
            },
        },
        "comparisons": comparisons,
        "pinned_tree_diff_vs_base": pinned,
        "pinned_slots": sorted(REQUIRED_SLOTS),
        "result": "RESIDENT_SURFACE_UNCHANGED" if ok else "RESIDENT_SURFACE_CHANGED",
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": evidence["result"], "evidence": str(out_path)}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
