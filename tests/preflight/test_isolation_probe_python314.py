"""Ubuntu 26.04 Python 3.14 discovery regression tests for the isolation probe."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from tools.c15_preflight.isolation_probe import CONTROL_NAMES, LABELS, probe


_OLD_INTERPRETERS = {
    "/usr/bin/python3.11",
    "/usr/bin/python3",
    "/usr/bin/python3.12",
    "/usr/bin/python3.10",
}
_PY314 = "/usr/bin/python3.14"
_SETPRIV = "/usr/bin/setpriv"


def test_probe_selects_python314_on_ubuntu_2604_layout() -> None:
    """Only 3.14 is a real interpreter; python3 is a symlink like on 26.04."""
    real_is_file = Path.is_file
    real_is_symlink = Path.is_symlink
    real_is_dir = Path.is_dir
    run_command: list[str] = []

    def fake_is_file(path: Path) -> bool:
        value = str(path)
        if value == "/usr/bin/python3":
            return True
        if value in _OLD_INTERPRETERS:
            return False
        if value in {_PY314, _SETPRIV}:
            return True
        return real_is_file(path)

    def fake_is_symlink(path: Path) -> bool:
        value = str(path)
        if value == "/usr/bin/python3":
            return True
        if value in {_PY314, _SETPRIV}:
            return False
        if value in _OLD_INTERPRETERS:
            return False
        return real_is_symlink(path)

    def fake_is_dir(path: Path) -> bool:
        value = str(path)
        if value == "/usr/lib/python3.14":
            return True
        if value in {
            "/usr/lib/python3",
            "/usr/lib/python3.11",
            "/usr/lib/python3.12",
            "/usr/lib/python3.10",
        }:
            return False
        return real_is_dir(path)

    def fake_run(command, **kwargs):
        run_command.extend(command)
        payload = {
            "denied": {label: True for label in LABELS},
            "controls": {control: True for control in CONTROL_NAMES},
        }
        return SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")

    with (
        patch.object(Path, "is_file", fake_is_file),
        patch.object(Path, "is_symlink", fake_is_symlink),
        patch.object(Path, "is_dir", fake_is_dir),
        patch("tools.c15_preflight.isolation_probe.subprocess.check_output", return_value="") as mock_ldd,
        patch("tools.c15_preflight.isolation_probe.subprocess.run", side_effect=fake_run),
    ):
        report = probe()

    assert report["synthetic_boundary_status"] == "PASS"
    assert "/usr/bin/python3.14 -I -B /probe.py" in run_command[-1]
    assert "/usr/lib/python3.14" in run_command[-1]
    assert mock_ldd.call_args_list[0].args[0] == ["ldd", _PY314]


def test_probe_preserves_inconclusive_error_when_no_interpreter_candidate_exists() -> None:
    """No real interpreter candidates must retain the existing fail-closed error."""
    real_is_file = Path.is_file
    real_is_symlink = Path.is_symlink

    def no_interpreter_is_file(path: Path) -> bool:
        if str(path) in _OLD_INTERPRETERS | {_PY314}:
            return False
        return real_is_file(path)

    def no_interpreter_is_symlink(path: Path) -> bool:
        if str(path) in _OLD_INTERPRETERS | {_PY314}:
            return False
        return real_is_symlink(path)

    with (
        patch.object(Path, "is_file", no_interpreter_is_file),
        patch.object(Path, "is_symlink", no_interpreter_is_symlink),
    ):
        with pytest.raises(RuntimeError) as exc_info:
            probe()

    assert str(exc_info.value) == (
        "isolation probe INCONCLUSIVE: no suitable python interpreter found"
    )
