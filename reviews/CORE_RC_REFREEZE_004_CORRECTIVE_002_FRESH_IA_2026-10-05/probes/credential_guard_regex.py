#!/usr/bin/env python3
"""Non-binding probe of candidate #336's checkout-extraheader audit regex."""
from __future__ import annotations

from pathlib import Path
import re
import subprocess
import tempfile

CANDIDATE = "5a5d384f16798bfff46ffe03f87310b0eafb2321"
WORKFLOW = ".github/workflows/core-rc-refreeze-004-formal-gate.yml"


def main() -> int:
    source = subprocess.check_output(["git", "show", f"{CANDIDATE}:{WORKFLOW}"], text=True)
    found = []
    pattern = None
    for number, line in enumerate(source.splitlines(), 1):
        if "git config --local --get-regexp" not in line or "extraheader" not in line:
            continue
        found.append(number)
        match = re.search(r"get-regexp '([^']+)'", line)
        if pattern is None and match:
            pattern = match.group(1)
    if not pattern:
        raise SystemExit("credential regex not found")

    with tempfile.TemporaryDirectory(prefix="ia28-credential-regex-") as tmp_s:
        config = Path(tmp_s) / "config"
        config.write_text(
            '[http "https://github.com/"]\n\textraheader = Bearer MOCK_ONLY\n',
            encoding="utf-8",
        )
        current = subprocess.run(
            ["git", "config", "--file", str(config), "--get-regexp", pattern],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        intended = r"^http\..*\.extraheader$"
        corrected = subprocess.run(
            ["git", "config", "--file", str(config), "--get-regexp", intended],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    print(f"candidate_sha={CANDIDATE}")
    print(f"credential_guard_source_lines={found}")
    print(f"candidate_ere={pattern!r}")
    print(f"candidate_ere_backslash_count={pattern.count(chr(92))}")
    print(f"mock_config_key=http.https://github.com/.extraheader")
    print(f"candidate_guard_exit={current.returncode}")
    print(f"candidate_guard_output={current.stdout.strip()!r}")
    print(f"one_escape_ere={intended!r}")
    print(f"one_escape_guard_exit={corrected.returncode}")
    print(f"one_escape_guard_output={corrected.stdout.strip()!r}")
    missed = current.returncode == 1 and corrected.returncode == 0
    print("RESULT=CREDENTIAL_REGEX_MISSES_EXTRAHEADER" if missed else "RESULT=NO_MISS")
    return 0 if missed else 1


if __name__ == "__main__":
    raise SystemExit(main())
