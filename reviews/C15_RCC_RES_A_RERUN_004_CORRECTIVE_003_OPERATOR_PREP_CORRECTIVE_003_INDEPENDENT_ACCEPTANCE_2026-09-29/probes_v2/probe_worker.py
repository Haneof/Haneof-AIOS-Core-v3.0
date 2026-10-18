"""Reviewer-authored subprocess worker for cross-process / fault / crash probes.

Usage:
    python probe_worker.py <mode> --root R [options]

Modes:
    publish            publish a request (distinct body via --marker)
    publish-explicit   publish with --request-id
    publish-response   publish a valid response envelope for --request-id
    publish-raw        publish exact bytes from --body-file for --request-id
    consume            consume the response for --request-id
    handler            drive ExternalSessionModelHandler on a marker snapshot
    fault-publish      install dir fault (--fault-kind dir_fsync|dir_open,
                       --fault-path) then publish / append
    fault-retry        phase 1 fault publish, restore, optional visible-byte
                       mutation, then retry (request or response side)
    crash-publish      crash (exit 9) at --point during a request publication
    ledger-append      raw ExchangeLedger.append
    lock-nb            non-blocking flock contention probe
    lock-hold-stop     acquire the exchange lock, then SIGSTOP self (reports pid)

All output is one JSON object on stdout.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import signal
import sys
import time


def _json(payload: dict) -> None:
    print(json.dumps(payload, default=str), flush=True)


def _wait_gate(gate: str | None, token: str, timeout_s: float = 20.0) -> None:
    if not gate:
        return
    gate_path = pathlib.Path(gate)
    gate_path.mkdir(parents=True, exist_ok=True)
    (gate_path / f"ready-{token}").write_text("ready")
    deadline = time.monotonic() + timeout_s
    while not (gate_path / "go").exists():
        if time.monotonic() > deadline:
            raise SystemExit("gate timeout")
        time.sleep(0.002)


def _envelope(bridge, request_id: str, marker: str) -> dict:
    return {
        "response_version": 1,
        "request_id": request_id,
        "request_sha256": bridge.request_sha256(request_id),
        "authored_by": "EXTERNAL_CURRENT_RESIDENT_SESSION",
        "directive": {"capability_calls": [], "response": marker, "silence": False},
    }


def _snapshot(marker: str):
    from aios_core.runtime.cognitive_runtime import RuntimeSnapshot

    return RuntimeSnapshot(
        user_input=marker,
        wake_reason="reviewer-synthetic",
        cockpit={"reviewer": True},
        capability_catalog=(),
        capability_history=(),
        round_index=0,
        remaining_tool_rounds=1,
    )


def _install_crash_point(point: str) -> None:
    import aios_exchange.atomic as atomic_mod
    import aios_exchange.ledger as ledger_mod

    if point == "after_temp_fsync_before_replace":
        real_replace = os.replace

        def replace(src, dst, *a, **kw):
            os._exit(9)

        os.replace = replace
    elif point == "after_replace_before_dir_fsync":
        real_replace = os.replace

        def replace(src, dst, *a, **kw):
            real_replace(src, dst, *a, **kw)
            os._exit(9)

        os.replace = replace
    elif point == "after_artifact_before_ledger_append":
        real_append = ledger_mod.ExchangeLedger._append_locked

        def append_locked(self, *a, **kw):
            os._exit(9)

        ledger_mod.ExchangeLedger._append_locked = append_locked
    elif point == "after_ledger_file_fsync_before_dir_fsync":
        real_fsync = os.fsync

        def fsync(fd):
            real_fsync(fd)
            try:
                path = os.readlink(f"/proc/self/fd/{fd}")
            except OSError:
                return None
            if str(path).endswith("ledger.jsonl"):
                try:
                    if os.fstat(fd).st_size == 0:
                        os._exit(9)
                except OSError:
                    pass
            return None

        os.fsync = fsync
    elif point == "after_ledger_append_before_receipt":
        real_append = ledger_mod.ExchangeLedger._append_locked

        def append_locked(self, *a, **kw):
            record = real_append(self, *a, **kw)
            os._exit(9)

        ledger_mod.ExchangeLedger._append_locked = append_locked
    else:
        raise SystemExit(f"unknown crash point {point!r}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode")
    parser.add_argument("--root", required=True)
    parser.add_argument("--gate")
    parser.add_argument("--token", default="w0")
    parser.add_argument("--marker", default="reviewer-default")
    parser.add_argument("--request-id")
    parser.add_argument("--body-file")
    parser.add_argument("--fault-kind", choices=["dir_fsync", "dir_open"])
    parser.add_argument("--fault-path")
    parser.add_argument("--mutate-visible-after-fault", action="store_true")
    parser.add_argument("--second-marker")
    parser.add_argument("--point")
    parser.add_argument("--event", default="request_published")
    parser.add_argument("--side", choices=["request", "response"], default="request")
    parser.add_argument("--adopt-existing", action="store_true")
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args(argv)

    if args.mode in ("fault-publish", "fault-retry"):
        from fault_injection import FaultConfig, install, restore, visible_files
    if args.mode in ("crash-publish", "crash-handler"):
        _install_crash_point(args.point)

    from aios_exchange.bridge import ExchangeBridge

    try:
        if args.mode == "publish":
            _wait_gate(args.gate, args.token)
            bridge = ExchangeBridge(args.root)
            receipt = bridge.publish_request(
                kind="model_directive", body={"reviewer_marker": args.marker}
            )
            _json({"ok": True, "mode": args.mode, "receipt": receipt})

        elif args.mode == "publish-explicit":
            _wait_gate(args.gate, args.token)
            bridge = ExchangeBridge(args.root)
            receipt = bridge.publish_request(
                kind="model_directive",
                body={"reviewer_marker": args.marker},
                request_id=args.request_id,
            )
            _json({"ok": True, "mode": args.mode, "receipt": receipt})

        elif args.mode == "publish-response":
            _wait_gate(args.gate, args.token)
            bridge = ExchangeBridge(args.root)
            if args.body_file:
                data = pathlib.Path(args.body_file).read_bytes()
                receipt = bridge.responses.publish_bytes(
                    request_id=args.request_id,
                    response_bytes=data,
                    adopt_existing=args.adopt_existing,
                )
            else:
                receipt = bridge.responses.publish_object(
                    request_id=args.request_id,
                    response=_envelope(bridge, args.request_id, args.marker),
                    adopt_existing=args.adopt_existing,
                )
            _json({"ok": True, "mode": args.mode, "receipt": receipt})

        elif args.mode == "consume":
            _wait_gate(args.gate, args.token)
            bridge = ExchangeBridge(args.root)
            raw = bridge.consume_response(args.request_id)
            _json({"ok": True, "mode": args.mode, "bytes": len(raw)})

        elif args.mode == "handler":
            _wait_gate(args.gate, args.token)
            from aios_exchange.runner import (
                ExternalSessionConfig,
                ExternalSessionModelHandler,
            )

            handler = ExternalSessionModelHandler(
                ExternalSessionConfig(
                    pathlib.Path(args.root),
                    response_timeout_s=args.timeout,
                    poll_interval_s=0.01,
                )
            )
            directive = handler(_snapshot(args.marker))
            _json(
                {
                    "ok": True,
                    "mode": args.mode,
                    "response": directive.response,
                    "handoffs": handler.handoff_records(),
                }
            )

        elif args.mode == "ledger-append":
            _wait_gate(args.gate, args.token)
            from aios_exchange.ledger import ExchangeLedger

            ledger = ExchangeLedger(pathlib.Path(args.root) / "ledger.jsonl")
            record = ledger.append(
                args.event, request_id=args.marker, request_sha256="a" * 64
            )
            _json({"ok": True, "mode": args.mode, "record": record})

        elif args.mode in ("fault-publish", "fault-retry"):
            fault = install(
                FaultConfig(
                    dir_fsync_fail=(args.fault_path,) if args.fault_kind == "dir_fsync" else (),
                    dir_open_fail=(args.fault_path,) if args.fault_kind == "dir_open" else (),
                )
            )
            bridge = ExchangeBridge(args.root)
            first = {"status": "success"}
            try:
                if args.side == "request":
                    receipt = bridge.publish_request(
                        kind="model_directive", body={"reviewer_marker": args.marker}
                    )
                else:
                    request_id = args.request_id
                    if request_id is None:
                        request_id = bridge.publish_request(
                            kind="model_directive",
                            body={"reviewer_marker": "seed-for-response"},
                        )["request_id"]
                    receipt = bridge.responses.publish_object(
                        request_id=request_id,
                        response=_envelope(bridge, request_id, args.marker),
                    )
                first = {"status": "success", "receipt": receipt}
            except Exception as exc:
                first = {"status": "closed", "error": f"{type(exc).__name__}: {exc}"}
            visible_after_fault = visible_files(args.root)
            mutated = None
            if args.mutate_visible_after_fault:
                candidates = [
                    p
                    for p in pathlib.Path(args.root).rglob("*.json")
                    if "requests" in p.parts or "responses" in p.parts
                ]
                for path in candidates:
                    path.write_bytes(b'{"reviewer_mutation":true}\n')
                    mutated = str(path)
            restore_result = {"restored": True}
            if args.mode == "fault-retry":
                restore()
                # fresh objects: retry through a brand-new bridge
                retry_bridge = ExchangeBridge(args.root)
                try:
                    if args.side == "request":
                        retry = retry_bridge.publish_request(
                            kind="model_directive",
                            body={"reviewer_marker": args.second_marker or args.marker},
                        )
                    else:
                        request_id = args.request_id
                        if request_id is None:
                            state = retry_bridge.recovery_state()
                            request_id = (state["open_dispatched"] or state["durable_unconsumed"])[0]
                        retry = retry_bridge.responses.publish_object(
                            request_id=request_id,
                            response=_envelope(
                                retry_bridge, request_id, args.second_marker or args.marker
                            ),
                        )
                    retry_result = {"status": "success", "receipt": retry}
                except Exception as exc:
                    retry_result = {
                        "status": "closed",
                        "error": f"{type(exc).__name__}: {exc}",
                    }
            else:
                retry_result = None
            _json(
                {
                    "ok": True,
                    "mode": args.mode,
                    "first": first,
                    "visible_after_fault": visible_after_fault,
                    "mutated": mutated,
                    "fault": fault.as_dict(),
                    "retry": retry_result,
                }
            )

        elif args.mode == "crash-publish":
            bridge = ExchangeBridge(args.root)
            bridge.publish_request(
                kind="model_directive", body={"reviewer_marker": args.marker}
            )
            _json({"ok": True, "mode": args.mode, "note": "no crash occurred"})

        elif args.mode == "crash-handler":
            from aios_exchange.runner import (
                ExternalSessionConfig,
                ExternalSessionModelHandler,
            )

            handler = ExternalSessionModelHandler(
                ExternalSessionConfig(
                    pathlib.Path(args.root),
                    response_timeout_s=args.timeout,
                    poll_interval_s=0.01,
                )
            )
            directive = handler(_snapshot(args.marker))
            _json({"ok": True, "mode": args.mode, "response": directive.response})

        elif args.mode == "toctou-publish":
            import aios_exchange.requests as requests_mod

            real_write = requests_mod.atomic_write_json
            window = pathlib.Path(args.root) / "window-open"

            def delayed_write(path, payload, **kwargs):
                receipt = real_write(path, payload, **kwargs)
                window.write_text(str(path))
                time.sleep(3.0)
                return receipt

            requests_mod.atomic_write_json = delayed_write
            bridge = ExchangeBridge(args.root)
            receipt = bridge.publish_request(
                kind="model_directive", body={"reviewer_marker": args.marker}
            )
            _json({"ok": True, "mode": args.mode, "receipt": receipt, "window": str(window)})

        elif args.mode == "due-work":
            import datetime as dt

            from aios_core.contracts.enums import WakeSource
            from aios_core.headless.core import HeadlessConfig, HeadlessCore
            from aios_core.wake.service import WakeSignalRequest
            from aios_exchange.runner import run_due_work

            world = pathlib.Path(args.marker)  # --marker carries the world path
            index = pathlib.Path(args.body_file)  # --body-file carries the index path
            now = dt.datetime.fromisoformat(args.request_id or "2026-09-29T12:00:00+00:00")

            def forbidden(_snapshot):
                raise AssertionError("setup must not call a model")

            with HeadlessCore(
                config=HeadlessConfig(
                    world_path=world, index_path=index, subject_id="reviewer-due-work"
                ),
                model_handler=forbidden,
            ) as core:
                core.runtime.wake_bus.emit(
                    WakeSignalRequest(
                        wake_source=WakeSource.SAFETY,
                        rule_id="reviewer-synthetic-due",
                        observed_at=now,
                        priority=100,
                        dedupe_key="reviewer-synthetic-due",
                    )
                )
            _wait_gate(args.gate, args.token)
            result = run_due_work(
                world_path=world,
                index_path=index,
                subject_id="reviewer-due-work",
                exchange_root=args.root,
                now=now,
                max_wakes=1,
                include_periodic_review=False,
                response_timeout_s=args.timeout,
                poll_interval_s=0.01,
            )
            _json(
                {
                    "ok": True,
                    "mode": args.mode,
                    "wake_state": result["due_work_result"]["wakes"][0]["wake"]["state"],
                    "handoffs": result["handoffs"],
                    "integrity": result["exchange"]["integrity"]["ok"],
                }
            )

        elif args.mode == "user-turn":
            from aios_exchange.runner import run_user_turn

            world = pathlib.Path(args.marker)
            index = pathlib.Path(args.body_file)
            occurred = args.request_id or "2026-09-29T12:00:00+00:00"
            _wait_gate(args.gate, args.token)
            result = run_user_turn(
                world_path=world,
                index_path=index,
                exchange_root=args.root,
                subject_id="reviewer-user-turn",
                session_id="reviewer-session",
                turn_index=1,
                user_input="reviewer synthetic user input",
                occurred_at=occurred,
                response_timeout_s=args.timeout,
                poll_interval_s=0.01,
            )
            _json(
                {
                    "ok": True,
                    "mode": args.mode,
                    "handoffs": result["handoffs"],
                    "integrity": result["exchange"]["integrity"]["ok"],
                }
            )

        elif args.mode == "lock-nb":
            import fcntl

            lock_path = pathlib.Path(args.root) / "ledger.jsonl.lock"
            fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                _json({"ok": True, "mode": args.mode, "acquired": True})
            except OSError as exc:
                _json(
                    {
                        "ok": True,
                        "mode": args.mode,
                        "acquired": False,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
            finally:
                os.close(fd)

        elif args.mode == "lock-hold-stop":
            from aios_exchange.ledger import ExchangeLedger

            # v2: deterministic rendezvous. The holder signals readiness only
            # AFTER the lock is held, then keeps holding while it waits for
            # ``go``; the probe can SIGKILL it (death) or release it (contention).
            gate_path = None
            if args.gate:
                gate_path = pathlib.Path(args.gate)
                gate_path.mkdir(parents=True, exist_ok=True)
            ledger = ExchangeLedger(pathlib.Path(args.root) / "ledger.jsonl")
            with ledger.mutation():
                if gate_path is not None:
                    (gate_path / f"ready-{args.token}").write_text("ready")
                    deadline = time.monotonic() + 90.0
                    while not (gate_path / "go").exists():
                        if time.monotonic() > deadline:
                            break
                        time.sleep(0.005)
                else:
                    _json({"ok": True, "mode": args.mode, "pid": os.getpid(), "holding": True})
                    os.kill(os.getpid(), signal.SIGSTOP)
                    time.sleep(0.1)
            _json({"ok": True, "mode": args.mode, "pid": os.getpid(), "released": True})
        else:
            raise SystemExit(f"unknown mode {args.mode!r}")
    except Exception as exc:
        _json({"ok": False, "mode": args.mode, "error": f"{type(exc).__name__}: {exc}"})
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
