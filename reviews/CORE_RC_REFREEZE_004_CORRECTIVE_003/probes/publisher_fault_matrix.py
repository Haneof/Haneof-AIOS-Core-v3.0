#!/usr/bin/env python3
"""Fault-inject the exact inline publisher shell without network access."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

STEP = "      - name: Publish provisional exact candidate pin with pre/post identity checks"
CANDIDATE = "0123456789abcdef0123456789abcdef01234567"
BRANCH = "arena/01a10c8c-haneof-aios-core-v3-0"

MOCK_CURL = r'''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
out = next(args[i + 1] for i, arg in enumerate(args[:-1]) if arg == "-o")
url = next(arg for arg in args if arg.startswith("https://"))
if "/commits/" in url and os.environ.get("MOCK_POST_TRANSPORT") == "1":
    print("mocked POST transport reset", file=sys.stderr)
    sys.exit(7)
if url.endswith("/git/ref/heads/" + os.environ["CANONICAL_CORRECTIVE_BRANCH"]):
    Path(out).write_text(json.dumps({"object": {"sha": os.environ["GITHUB_SHA"]}}), encoding="utf-8")
    code = "200"
elif "/commits/" in url and url.endswith("/comments"):
    code = os.environ["MOCK_POST_CODE"]
    if code == "201":
        Path(out).write_text(json.dumps({"id": 777001}), encoding="utf-8")
    else:
        Path(out).write_text(json.dumps({"message": "injected status"}), encoding="utf-8")
else:
    print("unexpected URL: " + url, file=sys.stderr)
    sys.exit(91)
sys.stdout.write(code)
'''

MOCK_JQ = r'''#!/usr/bin/env python3
import json, sys
args = sys.argv[1:]
if args and args[0] == "-n":
    pos = args.index("--rawfile")
    key, path = args[pos + 1], args[pos + 2]
    print(json.dumps({key: open(path, encoding="utf-8").read()}))
    raise SystemExit(0)
raw = "-r" in args
expr = next((x for x in args if x.startswith(".")), None)
path = args[-1]
obj = json.load(open(path, encoding="utf-8"))
if expr == ".object.sha // empty": value = obj.get("object", {}).get("sha", "")
elif expr == ".id // empty": value = obj.get("id", "")
else: raise SystemExit("unsupported jq expression: " + str(expr))
if isinstance(value, (dict, list)): print(json.dumps(value))
else: print(value)
'''


def extract_shell(text: str) -> str:
    lines = text.splitlines()
    start = lines.index(STEP)
    run_line = next(i for i in range(start + 1, len(lines)) if lines[i] == "        run: |")
    block: list[str] = []
    for line in lines[run_line + 1 :]:
        if line.startswith("          "):
            block.append(line[10:])
        elif not line.strip():
            block.append("")
        else:
            break
    return "\n".join(block).rstrip() + "\n"


def run_case(shell: str, mode: str, code: str = "201") -> tuple[int, str]:
    with tempfile.TemporaryDirectory(prefix="w30-publisher-") as tmp_s:
        tmp = Path(tmp_s)
        bindir, runner = tmp / "bin", tmp / "runner"
        bindir.mkdir(); runner.mkdir()
        (bindir / "curl").write_text(MOCK_CURL, encoding="utf-8")
        (bindir / "jq").write_text(MOCK_JQ, encoding="utf-8")
        (bindir / "curl").chmod(0o755); (bindir / "jq").chmod(0o755)
        script = tmp / "publisher.sh"
        script.write_text(shell, encoding="utf-8")
        github_output = tmp / "github-output"
        github_output.touch()
        env = os.environ.copy()
        env.update({
            "PATH": str(bindir) + os.pathsep + env["PATH"],
            "RUNNER_TEMP": str(runner),
            "GITHUB_OUTPUT": str(github_output),
            "GITHUB_REPOSITORY": "Haneof/Haneof-AIOS-Core-v3.0",
            "GITHUB_WORKFLOW": "core-rc-refreeze-004-formal-gate",
            "GITHUB_SHA": CANDIDATE,
            "GITHUB_REF": "refs/heads/" + BRANCH,
            "GITHUB_RUN_ID": "900000777",
            "GITHUB_RUN_ATTEMPT": "1",
            "GH_TOKEN": "MOCK_ONLY",
            "CANONICAL_CORRECTIVE_BRANCH": BRANCH,
            "GATE_RESULT": "success",
            "GATE_KIND": "formal",
            "MOCK_POST_CODE": code,
            "MOCK_POST_TRANSPORT": "1" if mode == "transport" else "0",
        })
        result = subprocess.run(["bash", str(script)], env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                check=False)
        return result.returncode, result.stdout


def main() -> int:
    workflow = Path(sys.argv[1]).read_text(encoding="utf-8")
    shell = extract_shell(workflow)
    print(f"publisher_shell_sha256={__import__('hashlib').sha256(shell.encode()).hexdigest()}")
    ok = True
    for code in ("201", "200", "401", "403", "500"):
        rc, output = run_case(shell, "http", code)
        expected = code == "201"
        actual = rc == 0
        print(f"case=http-{code} expected={'PASS' if expected else 'FAIL'} actual={'PASS' if actual else 'FAIL'} exit={rc}")
        if output.strip():
            print("  " + output.strip().replace("\n", "\n  "))
        ok &= actual == expected
    rc, output = run_case(shell, "transport")
    print(f"case=post-transport-failure expected=FAIL actual={'FAIL' if rc else 'PASS'} exit={rc}")
    if output.strip():
        print("  " + output.strip().replace("\n", "\n  "))
    ok &= rc != 0 and "PIN_PUBLISH_TRANSPORT_FAILURE" in output
    print("PUBLISHER_FAULT_MATRIX=PASS" if ok else "PUBLISHER_FAULT_MATRIX=FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
