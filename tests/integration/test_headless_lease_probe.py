from __future__ import annotations

import json
import multiprocessing
import os
import socket
from pathlib import Path

import pytest

from aios_core.headless import (
    HeadlessConfig,
    HeadlessCore,
    HeadlessWriterBusy,
)
from aios_core.headless.core import probe_writer_lease
from aios_core.headless.testing import deterministic_model_handler


def _hold_writer_lease(world_path: str, connection) -> None:
    """Child process used to prove the probe observes a genuinely live holder."""
    core = HeadlessCore(
        config=HeadlessConfig(world_path=Path(world_path)),
        model_handler=deterministic_model_handler,
    )
    try:
        with core:
            connection.send(core.status())
            while True:
                command = connection.recv()
                if command == "status":
                    connection.send(core.status())
                elif command == "stop":
                    break
    finally:
        connection.close()


def test_probe_writer_lease_missing_file_is_free_and_stays_missing(tmp_path):
    config = HeadlessConfig(world_path=tmp_path / "missing-world.sqlite")
    assert config.lock_path is not None
    assert not config.lock_path.exists()

    result = probe_writer_lease(config.lock_path)

    assert result == {
        "held_by_other": False,
        "holder_pid": None,
        "holder_host": None,
    }
    assert not config.lock_path.exists()

    # An existing but empty lock file is also free and must remain untouched.
    empty_lock = tmp_path / "empty.lock"
    empty_lock.touch()
    assert probe_writer_lease(empty_lock) == {
        "held_by_other": False,
        "holder_pid": None,
        "holder_host": None,
    }
    assert empty_lock.read_bytes() == b""


def test_probe_writer_lease_reads_live_holder_without_disturbing_it(tmp_path):
    world_path = tmp_path / "held-world.sqlite"
    config = HeadlessConfig(world_path=world_path)
    assert config.lock_path is not None

    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe()
    process = context.Process(
        target=_hold_writer_lease,
        args=(str(world_path), child),
    )
    process.start()
    child.close()

    try:
        assert parent.poll(20), "lease-holder process did not become ready"
        initial_status = parent.recv()
        assert initial_status["status"] == "ready"
        expected_holder = {
            "pid": process.pid,
            "host": socket.gethostname(),
        }
        assert initial_status["writer_lease_holder"] == expected_holder
        assert "writer_lease_held" not in initial_status

        original_lock_bytes = config.lock_path.read_bytes()
        result = probe_writer_lease(config.lock_path)

        assert result == {
            "held_by_other": True,
            "holder_pid": process.pid,
            "holder_host": socket.gethostname(),
        }
        assert config.lock_path.read_bytes() == original_lock_bytes

        # The original Core remains usable after the probe and still owns the lease.
        parent.send("status")
        assert parent.poll(10), "lease-holder process did not answer status request"
        status_after_probe = parent.recv()
        assert status_after_probe["writer_lease_holder"] == expected_holder
        assert "writer_lease_held" not in status_after_probe

        contender = HeadlessCore(
            config=config,
            model_handler=deterministic_model_handler,
        )
        with pytest.raises(HeadlessWriterBusy):
            contender.start()
    finally:
        if process.is_alive():
            try:
                parent.send("stop")
            except (BrokenPipeError, EOFError, OSError):
                pass
            process.join(timeout=20)
        if process.is_alive():
            process.terminate()
            process.join(timeout=10)
        parent.close()

    assert process.exitcode == 0
    assert config.lock_path.exists()
    assert probe_writer_lease(config.lock_path) == {
        "held_by_other": False,
        "holder_pid": None,
        "holder_host": None,
    }


def test_headless_status_reports_own_holder_and_removes_old_boolean(tmp_path):
    config = HeadlessConfig(world_path=tmp_path / "status-world.sqlite")
    core = HeadlessCore(
        config=config,
        model_handler=deterministic_model_handler,
    ).start()
    try:
        status = core.status()
        assert status["writer_lease_holder"] == {
            "pid": os.getpid(),
            "host": socket.gethostname(),
        }
        assert "writer_lease_held" not in status
    finally:
        core.stop()


def test_cli_lease_probe_does_not_start_core_or_create_files(tmp_path, capsys):
    from aios_core.headless.cli import main

    world_path = tmp_path / "cli-world.sqlite"
    lock_path = Path(str(world_path.resolve()) + ".writer.lock")

    result = main(["--world", str(world_path), "lease-probe"])

    assert result == 0
    assert json.loads(capsys.readouterr().out) == {
        "held_by_other": False,
        "holder_pid": None,
        "holder_host": None,
    }
    assert not world_path.exists()
    assert not lock_path.exists()
