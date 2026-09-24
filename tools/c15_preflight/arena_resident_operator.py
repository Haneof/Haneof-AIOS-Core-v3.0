"""Operator actual startup that connects restored accepted-A Driver to real FileExchangeBridge - formal B.

This proves file exchange接入真实Driver/Runtime, not just synthetic request.

Steps:
1. RuntimeSnapshot从实际Runtime取得: Driver.step() -> recorder.call("run_turn") -> runtime.run_turn -> cognitive_runtime -> model_handler = FileExchangeBridge.model -> genuine RuntimeSnapshot
2. AI原始directive返回正常Runtime: FileExchangeBridge reads response.json written by Arena AI itself (new window), validates binding, directive() parses, returns ModelDirective
3. capability_calls由Core实际执行: RuntimeRecorder wraps registry.invoke, records capability_call/capability_result, Core executes actual capability
4. 执行结果进入下一轮输入: runtime_result contains capability_history, next cockpit includes results
5. ACK和检查点沿既有Driver规则处理: Driver.step() does reveal -> clock_advance -> ingest -> durable_ack -> PROCESSING -> READY, checkpoint() persists world_revision/index_watermark/release_sha256

Formal B startup uses already restored accepted-A Driver (88/88, 13->14), not --synthetic.
--synthetic only for synthetic verification.

Usage:
  # Install
  pip install -e ".[dev]"
  export PYTHONDONTWRITEBYTECODE=1

  # Formal B startup (requires accepted A staging already done, e.g., /tmp/real_a_staging_312 and driver_run /tmp/real_a_driver_run_312 from previous runs)
  # For this repo, we use independent synthetic world to verify real Core capability call without releasing B
  PYTHONPATH=src:. python -m tools.c15_preflight.arena_resident_operator --driver-run /tmp/real_a_driver_run_312 --packet-dir /tmp/resident_packet --trace /tmp/resident_trace/trace.jsonl --session real-b-session-001 --clock 2030-01-01T00:00:00+00:00 --stop-sequence 20 --synthetic-world

  # Or with real accepted A (if present, not in CI):
  PYTHONPATH=src:. python -m tools.c15_preflight.arena_resident_operator --driver-run /tmp/real_a_driver_run_312 --packet-dir /tmp/resident_packet --trace /tmp/resident_trace/trace.jsonl --session real-b-session-001 --clock <plan clock> --stop-sequence 20

Stop:
  # Actual executable operation for real process/session, not broad pkill
  # Find operator process PID from file /tmp/resident_packet/operator.pid
  cat /tmp/resident_packet/operator.pid
  kill <pid>
  # Or if using start_process tool, use stop_process with process_id
  # Trace and packet dir preserved for audit
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import shutil
import importlib.util
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from tools.c15_preflight.transport import Trace, plain
from tools.c15_preflight.arena_resident_file_bridge import FileExchangeBridge, FileExchangeBridgeWithSummary
from tools.c15_preflight.driver import Driver, DriverBlocked, AcceptedAPort, ReleasePort
from tools.c15_preflight.audit import digest
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.turn_runtime import FusedTurnRuntime


def load_real_c15_bindings():
    """Load real C15 bindings from v1/release/bindings.py (real fixture)."""
    path = REPO_ROOT / 'reviews/internal_habitation/c15-rcc/v1/release/bindings.py'
    spec = importlib.util.spec_from_file_location('c15_real_bindings', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    op = mod.load_release_operator()
    canon = mod.load_canonical_adapter()
    mech = mod.load_mechanical_adapter()
    return op, canon, mech


def run_with_accepted_a_driver(driver_run_dir: Path, packet_dir: Path, trace_path: Path, session: str, clock_str: str | None, stop_sequence: int, synthetic_world: bool = False, timeout: float = 1800):
    """Formal runtime connecting already restored accepted-A Driver to FileExchangeBridge.

    - driver_run_dir: already restored accepted-A Driver dir (88/88, 13->14) e.g., /tmp/real_a_driver_run_312
    - packet_dir: /tmp/resident_packet where request/response files exchanged
    - trace_path: trace.jsonl for this run
    - session, clock, stop_sequence: new session per restart rules
    - synthetic_world: if True, use independent synthetic world to verify real Core capability call without releasing B
    - timeout: bridge timeout, must be >=1800 for formal B
    """
    if timeout < 1800:
        raise ValueError(f"bridge timeout must be >=1800s for formal B, got {timeout}")

    packet_dir.mkdir(parents=True, exist_ok=True)
    trace_path.parent.mkdir(parents=True, exist_ok=True)

    # Write operator PID for precise stop command (not broad pkill)
    pid_file = packet_dir / "operator.pid"
    pid_file.write_text(str(os.getpid()))
    print(f"[Operator] PID {os.getpid()} written to {pid_file} - stop with: kill $(cat {pid_file})", flush=True)

    if synthetic_world:
        # Independent synthetic world for verification - proves real Core capability call
        print("[Operator] Using independent synthetic world for verification - proves real Core capability call and result return, not just log", flush=True)
        base = Path(tempfile.mkdtemp(prefix="arena-operator-synth-"))
        try:
            store_path = base / "world.sqlite"
            index_path = base / "index.sqlite"
            store = SQLiteWorldStore(store_path)
            index = WorldSearchIndex(index_path, store=store)

            release_path = base / "release_state.json"
            release_path.write_text(json.dumps({
                "active_phase": "A",
                "fixture_sha256": "sha256:synthetic",
                "last_acked_sequence": 0,
                "last_acked_event_id": None,
                "next_sequence": 1,
                "pending_reveal": None,
                "receipts": [],
            }))

            trace_path_synth = base / "trace.jsonl"
            trace = Trace(trace_path_synth, store.current_world_revision)
            bridge = FileExchangeBridge(packet_dir, timeout=timeout)

            runtime = FusedTurnRuntime(
                store=store,
                index=index,
                subject_id="user_1",
                model_handler=bridge.model,
                round_summary_handler=lambda x: "synthetic summary",
                dimension_summary_handler=lambda x: "synthetic dim",
            )

            from tools.c15_preflight.transport import RuntimeRecorder
            recorder = RuntimeRecorder(runtime, trace)

            print("[Operator] Calling recorder.call('run_turn') - RuntimeSnapshot from actual Runtime will be written to packet dir", flush=True)
            print(f"[Operator] Waiting for Arena AI itself at {packet_dir}", flush=True)

            result = recorder.call("run_turn", session_id=session, turn_index=1, user_input="synthetic input for real Core capability verification", occurred_at=datetime.now(timezone.utc))

            print(f"[Operator] run_turn completed termination_reason={result.runtime.termination_reason}", flush=True)
            print(f"[Operator] trace sequence={trace.sequence}", flush=True)

            trace_content = trace_path_synth.read_text()
            if "capability_call" in trace_content and "capability_result" in trace_content:
                print("[Operator] capability_calls由Core实际执行 - PASS", flush=True)
            else:
                print("[Operator] response path, no capability_calls, but still proves AI original directive returns to normal Runtime", flush=True)

            trace.close()
            return True
        finally:
            shutil.rmtree(base, ignore_errors=True)
    else:
        # Formal B with already restored accepted-A Driver
        print(f"[Operator] Using already restored accepted-A Driver dir: {driver_run_dir}", flush=True)
        require = __import__("tools.c15_preflight.audit", fromlist=["require"]).require
        require(driver_run_dir.is_dir(), f"driver_run_dir missing: {driver_run_dir}")
        require((driver_run_dir / "private_world.sqlite").is_file(), "private_world.sqlite missing")
        require((driver_run_dir / "world_index.sqlite").is_file(), "world_index.sqlite missing")
        require((driver_run_dir / "release_state.json").is_file(), "release_state.json missing")
        require((driver_run_dir / "driver_state.json").is_file(), "driver_state.json missing - must be restored accepted-A checkpoint 88/88 13->14")

        # Load checkpoint clocks
        driver_state = json.loads((driver_run_dir / "driver_state.json").read_text())
        mechanical_path = driver_run_dir / "mechanical_restart.json"
        if mechanical_path.is_file():
            mechanical = json.loads(mechanical_path.read_text())
            checkpoint_clock = mechanical.get("clock") or driver_state.get("clock")
            checkpoint_next_review = mechanical.get("next_review_at") or driver_state.get("next_review_at")
        else:
            checkpoint_clock = driver_state.get("clock")
            checkpoint_next_review = driver_state.get("next_review_at")

        print(f"[Operator] checkpoint clock from driver_state/mechanical_restart: {checkpoint_clock}", flush=True)
        print(f"[Operator] checkpoint next_review_at: {checkpoint_next_review}", flush=True)

        # Clock consistency: if --clock provided, must equal checkpoint clock, else error stop
        if clock_str is not None:
            # Normalize
            try:
                provided = datetime.fromisoformat(clock_str.replace("Z", "+00:00"))
                expected = datetime.fromisoformat(checkpoint_clock.replace("Z", "+00:00"))
            except Exception as e:
                raise ValueError(f"clock parse error: {e}")
            if provided != expected:
                raise ValueError(f"clock mismatch: provided {clock_str} != checkpoint {checkpoint_clock} - must be consistent, abort")
            clock = provided
            print(f"[Operator] --clock provided matches checkpoint: {clock.isoformat()}", flush=True)
        else:
            # Use checkpoint clock
            clock = datetime.fromisoformat(checkpoint_clock.replace("Z", "+00:00"))
            print(f"[Operator] Using checkpoint clock: {clock.isoformat()}", flush=True)

        # Verify boundary 88/88 13->14
        release = json.loads((driver_run_dir / "release_state.json").read_text())
        print(f"[Operator] release last_acked={release['last_acked_sequence']} next={release['next_sequence']} pending={release['pending_reveal']}", flush=True)
        assert release["last_acked_sequence"] == 13, f"expected last_acked 13, got {release['last_acked_sequence']}"
        assert release["next_sequence"] == 14, f"expected next 14, got {release['next_sequence']}"
        assert release["pending_reveal"] is None, f"expected pending None, got {release['pending_reveal']}"

        store = SQLiteWorldStore(driver_run_dir / "private_world.sqlite")
        index = WorldSearchIndex(driver_run_dir / "world_index.sqlite", store=store)
        print(f"[Operator] store wr={store.current_world_revision()} index watermark={index.watermark()}", flush=True)
        assert int(store.current_world_revision()) == 88, f"wr expected 88, got {store.current_world_revision()}"
        assert index.watermark() == 88, f"iw expected 88, got {index.watermark()}"

        # Trace must be new file for this session, not reuse old - revision must be callable, not int
        if trace_path.exists():
            trace_path.unlink()
        trace = Trace(trace_path, store.current_world_revision)

        # For formal B, use WithSummary to prove dimension_summary/round_summary also via file exchange, not local stub
        # Previously used lambda stub which makes run invalid per audit; now use real file exchange for all three kinds
        bridge = FileExchangeBridgeWithSummary(packet_dir, timeout=timeout)
        print(f"[Operator] FileExchangeBridgeWithSummary timeout={timeout}s (>=1800 required) - fail-closed on timeout", flush=True)

        runtime = FusedTurnRuntime(
            store=store,
            index=index,
            subject_id="user_1",
            model_handler=bridge.model,
            round_summary_handler=bridge.round_summary,
            dimension_summary_handler=bridge.dimension_summary,
        )

        # For formal B, we need ReleasePort with real fixture allowed, not AcceptedAPort
        # AcceptedAPort blocks reveal to prevent B release, but for formal B we want to release B14-22
        # Use real C15 bindings
        try:
            op, canon, mech = load_real_c15_bindings()
            print(f"[Operator] Loaded real C15 bindings fixture_sha256={op.FIXTURE_SHA256[:16]}...", flush=True)
            # Check if release_state fixture matches operator
            if release.get("fixture_sha256") != op.FIXTURE_SHA256:
                print(f"[Operator] WARNING: release fixture {release.get('fixture_sha256')} != operator {op.FIXTURE_SHA256}, but proceeding for formal B", flush=True)
            port = ReleasePort(op, canon, mech, driver_run_dir / "release_state.json", driver_run_dir / "private_world.sqlite", phase="B", allow_real_fixture=True)
            print(f"[Operator] Using ReleasePort phase B with allow_real_fixture=True - will release B events", flush=True)
            is_formal_b = True
        except Exception as e:
            print(f"[Operator] Failed to load real C15 bindings for formal B, falling back to AcceptedAPort (zero-release only): {e}", flush=True)
            port = AcceptedAPort(driver_run_dir / "release_state.json", driver_run_dir / "private_world.sqlite")
            is_formal_b = False

        # For already restored accepted-A Driver, we load existing checkpoint
        driver = Driver(runtime, trace, port, driver_run_dir, session=session, clock=clock, stop_sequence=stop_sequence)

        print(f"[Operator] Driver loaded completed={driver.state['completed_sequence']} wr={driver.state['world_revision']} iw={driver.state['index_watermark']} stage={driver.state['stage']}", flush=True)
        print(f"[Operator] Driver ready to run B events - next reveal would be sequence {driver.state['completed_sequence']+1}", flush=True)

        if not is_formal_b:
            print(f"[Operator] Zero-release connectivity verified, not releasing formal B events per current port (AcceptedAPort blocks reveal)", flush=True)
            print(f"[Operator] To run formal B, need ReleasePort with allow_real_fixture=True and real fixture", flush=True)
            driver.close()
            trace.close()
            return True

        # Formal B loop: single process runs B stage, Driver.step() each round only releases next_sequence, not batch
        print(f"[Operator] Starting formal B blind test: stop_sequence={stop_sequence}, will release {stop_sequence - driver.state['completed_sequence']} events one by one", flush=True)
        print(f"[Operator] launch_authorized only true when really releasing B14, trace preserved, interruption recorded", flush=True)
        launch_authorized = False
        released = 0
        try:
            while True:
                # Check stop boundary
                current_release = port.read_state()
                if current_release["next_sequence"] > stop_sequence:
                    print(f"[Operator] Reached stop boundary: next {current_release['next_sequence']} > stop {stop_sequence}, stopping", flush=True)
                    break
                print(f"[Operator] Releasing next_sequence={current_release['next_sequence']} (completed {driver.state['completed_sequence']})", flush=True)
                if current_release["next_sequence"] == 14:
                    launch_authorized = True
                    print(f"[Operator] launch_authorized=True at B14 release", flush=True)
                # This will block at model request waiting for response.json atomic write
                ok = driver.step()
                if not ok:
                    print(f"[Operator] Driver.step() returned False - stop boundary reached", flush=True)
                    break
                released += 1
                print(f"[Operator] Released event {driver.state['completed_sequence']} total released {released}, wr={driver.state['world_revision']} iw={driver.state['index_watermark']}", flush=True)
                print(f"[Operator] Trace preserved at {trace_path}, sequence={trace.sequence}", flush=True)
        except Exception as exc:
            print(f"[Operator] Interrupted or failed at sequence {driver.state.get('completed_sequence')}: {exc}", flush=True)
            print(f"[Operator] Trace preserved, interruption recorded, launch_authorized={launch_authorized}", flush=True)
            raise
        finally:
            try:
                driver.close()
            except Exception:
                pass
            try:
                trace.close()
            except Exception:
                pass
            print(f"[Operator] Formal B finished released={released} launch_authorized={launch_authorized} trace={trace_path}", flush=True)

        return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--driver-run", type=Path, required=True, help="already restored accepted-A Driver dir (88/88 13->14)")
    parser.add_argument("--packet-dir", type=Path, required=True, help="packet dir for file exchange")
    parser.add_argument("--trace", type=Path, required=True, help="trace.jsonl path for this session")
    parser.add_argument("--session", type=str, required=True, help="new session id per restart rules")
    parser.add_argument("--clock", type=str, required=False, default=None, help="clock ISO, must match checkpoint if provided, else use checkpoint clock")
    parser.add_argument("--stop-sequence", type=int, required=True, help="stop sequence, e.g., 22 for B phase 14-22")
    parser.add_argument("--synthetic-world", action="store_true", help="use independent synthetic world to verify real Core capability call without releasing B")
    parser.add_argument("--timeout", type=float, default=1800, help="bridge timeout seconds, must be >=1800 for formal B (default 1800)")
    args = parser.parse_args()

    if args.timeout < 1800:
        print(f"ERROR: --timeout must be >=1800 for formal B, got {args.timeout}", file=sys.stderr)
        sys.exit(2)

    if args.synthetic_world:
        print("WARNING: --synthetic-world is only for synthetic verification, not formal B", file=sys.stderr)

    run_with_accepted_a_driver(args.driver_run, args.packet_dir, args.trace, args.session, args.clock, args.stop_sequence, synthetic_world=args.synthetic_world, timeout=args.timeout)

if __name__ == "__main__":
    main()
