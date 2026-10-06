#!/usr/bin/env python3
"""RED-first local reproduction of the #336 post-read seal TOCTOU.

This is explicitly a mocked-API shell test, not hosted GitHub Actions evidence.
It extracts and executes the candidate's exact final-seal Bash block.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile

A = "5a5d384f16798bfff46ffe03f87310b0eafb2321"
B = "e4e6e6d4825d67b2d674d9c2237d08d1c89f1781"
BRANCH = "release/core-rc-refreeze-004-corrective-002-window28"
RUN_ID = "900000001"
COMMENT_ID = "203496684"
STEP = "      - name: Final fresh canonical identity seal"

MOCK_CURL = r'''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
out = next(args[i + 1] for i, arg in enumerate(args[:-1]) if arg == "-o")
url = next(arg for arg in args if arg.startswith("https://"))
branch = os.environ["CANONICAL_CORRECTIVE_BRANCH"]
a = os.environ["PROBE_A"]
run_id = os.environ["GITHUB_RUN_ID"]
comment_id = os.environ["PIN_COMMENT_ID"]
if url.endswith("/git/ref/heads/" + branch):
    payload = {"object": {"sha": a}}
    Path(out).write_text(json.dumps(payload), encoding="utf-8")
    # Advance A->B immediately after the only canonical-branch read.
    Path(os.environ["PROBE_STATE"]).write_text(os.environ["PROBE_B"] + "\n", encoding="utf-8")
elif url.endswith("/actions/runs/" + run_id):
    payload = {"head_sha": a, "head_branch": branch,
               "run_attempt": int(os.environ["GITHUB_RUN_ATTEMPT"]),
               "status": "in_progress"}
    Path(out).write_text(json.dumps(payload), encoding="utf-8")
elif url.endswith("/comments/" + comment_id):
    body = (f"- run_id: {run_id}\n- exact_candidate_sha: {a}\n"
            f"- canonical_branch: {branch}\n"
            "- publication_state: PROVISIONAL_PENDING_FINAL_IDENTITY_SEAL\n")
    Path(out).write_text(json.dumps({"body": body}), encoding="utf-8")
else:
    print("unexpected URL: " + url, file=sys.stderr)
    sys.exit(91)
sys.stdout.write("200")
'''


def extract_final_seal(workflow: str) -> str:
    lines = workflow.splitlines()
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
    result = "\n".join(block).rstrip() + "\n"
    assert "WHOLE_RUN_IDENTITY_SEAL=PASS" in result
    return result


def main() -> int:
    workflow_path = Path(sys.argv[1])
    workflow = workflow_path.read_text(encoding="utf-8")
    shell = extract_final_seal(workflow)
    with tempfile.TemporaryDirectory(prefix="w30-red-seal-") as tmp_s:
        tmp = Path(tmp_s)
        bindir, runner = tmp / "bin", tmp / "runner"
        bindir.mkdir(); runner.mkdir()
        curl = bindir / "curl"
        curl.write_text(MOCK_CURL, encoding="utf-8"); curl.chmod(0o755)
        script = tmp / "final-seal.sh"
        script.write_text(shell, encoding="utf-8")
        state = tmp / "canonical-head"
        state.write_text(A + "\n", encoding="utf-8")
        env = os.environ.copy()
        env.update({
            "PATH": str(bindir) + os.pathsep + env["PATH"],
            "RUNNER_TEMP": str(runner), "GITHUB_REPOSITORY": "Haneof/Haneof-AIOS-Core-v3.0",
            "GH_TOKEN": "MOCK_ONLY", "GITHUB_SHA": A,
            "GITHUB_REF": "refs/heads/" + BRANCH,
            "GITHUB_RUN_ID": RUN_ID, "GITHUB_RUN_ATTEMPT": "1",
            "CANONICAL_CORRECTIVE_BRANCH": BRANCH, "PIN_COMMENT_ID": COMMENT_ID,
            "PROBE_A": A, "PROBE_B": B, "PROBE_STATE": str(state),
        })
        result = subprocess.run(["bash", str(script)], env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                check=False)
        final_head = state.read_text(encoding="utf-8").strip()
        print(f"source_workflow={workflow_path}")
        print(f"source_workflow_sha256={hashlib.sha256(workflow.encode()).hexdigest()}")
        print(f"extracted_shell_sha256={hashlib.sha256(shell.encode()).hexdigest()}")
        print(f"A={A}")
        print(f"canonical_response_sha={A}")
        print(f"mock_ref_after_last_read={final_head}")
        print("mock_api_order=branch(A)->advance(B)->run(A)->comment(A)")
        print("final_seal_output_begin")
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
        print("final_seal_output_end")
        print(f"final_seal_exit={result.returncode}")
        print("hosted_actions_concurrency=NOT_SIMULATED")
        reproduced = (result.returncode == 0 and final_head == B
                      and "WHOLE_RUN_IDENTITY_SEAL=PASS" in result.stdout)
        print("RED=POST_READ_FALSE_GREEN_REPRODUCED_LOCAL_MOCK" if reproduced
              else "RED=NOT_REPRODUCED")
        return 0 if reproduced else 1


if __name__ == "__main__":
    raise SystemExit(main())
