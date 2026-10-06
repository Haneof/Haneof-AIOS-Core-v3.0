#!/usr/bin/env python3
"""Reviewer-owned local mock of candidate #336's exact final-seal shell block.

This intentionally does not contact GitHub and does not simulate Actions
concurrency cancellation. It tests only the shell's check-to-completion gap.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

CANDIDATE = "5a5d384f16798bfff46ffe03f87310b0eafb2321"
WORKFLOW = ".github/workflows/core-rc-refreeze-004-formal-gate.yml"
BRANCH = "release/core-rc-refreeze-004-corrective-002-window28"
A = CANDIDATE
B = "e4e6e6d4825d67b2d674d9c2237d08d1c89f1781"
RUN_ID = "999000001"
COMMENT_ID = "203496684"


def git_show(ref: str) -> str:
    return subprocess.check_output(["git", "show", f"{ref}:{WORKFLOW}"], text=True)


def final_step_script(workflow: str) -> str:
    lines = workflow.splitlines()
    marker = "      - name: Final fresh canonical identity seal"
    try:
        start = lines.index(marker)
    except ValueError as exc:
        raise SystemExit(f"final-seal step not found in {CANDIDATE}") from exc
    run_line = next(i for i in range(start + 1, len(lines)) if lines[i] == "        run: |")
    out: list[str] = []
    for line in lines[run_line + 1 :]:
        if line.startswith("          "):
            out.append(line[10:])
        elif not line.strip():
            out.append("")
        else:
            break
    script = "\n".join(out).rstrip() + "\n"
    if "WHOLE_RUN_IDENTITY_SEAL=PASS" not in script:
        raise SystemExit("extracted shell block did not contain final seal")
    return script


MOCK_CURL = r'''#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys

args = sys.argv[1:]
out = None
url = None
skip_value = {"-o", "-w", "-H", "-X", "--data"}
i = 0
while i < len(args):
    item = args[i]
    if item in skip_value:
        if item == "-o":
            out = args[i + 1]
        i += 2
    elif item.startswith("https://"):
        url = item
        i += 1
    else:
        i += 1
if not out or not url:
    print("mock curl: missing output path or URL", file=sys.stderr)
    sys.exit(90)
A = os.environ["PROBE_A"]
B = os.environ["PROBE_B"]
branch = os.environ["CANONICAL_CORRECTIVE_BRANCH"]
run_id = os.environ["GITHUB_RUN_ID"]
comment_id = os.environ["PIN_COMMENT_ID"]
trace = Path(os.environ["PROBE_TRACE"])
with trace.open("a", encoding="utf-8") as stream:
    stream.write(url + "\n")
if url.endswith("/git/ref/heads/" + branch):
    payload = {"object": {"sha": A}}
    Path(out).write_text(json.dumps(payload), encoding="utf-8")
    # Model the canonical ref advancing immediately after the one final-seal
    # branch response. The subsequent run/comment reads still refer to A.
    Path(os.environ["PROBE_STATE"]).write_text(B + "\n", encoding="utf-8")
elif url.endswith("/actions/runs/" + run_id):
    payload = {
        "head_sha": A,
        "head_branch": branch,
        "run_attempt": int(os.environ["GITHUB_RUN_ATTEMPT"]),
        "status": "in_progress",
    }
    Path(out).write_text(json.dumps(payload), encoding="utf-8")
elif url.endswith("/comments/" + comment_id):
    body = (
        f"- run_id: {run_id}\n"
        f"- exact_candidate_sha: {A}\n"
        f"- canonical_branch: {branch}\n"
        "- publication_state: PROVISIONAL_PENDING_FINAL_IDENTITY_SEAL\n"
    )
    Path(out).write_text(json.dumps({"body": body}), encoding="utf-8")
else:
    print("mock curl: unexpected URL " + url, file=sys.stderr)
    sys.exit(91)
sys.stdout.write("200")
'''


def main() -> int:
    workflow = git_show(CANDIDATE)
    shell = final_step_script(workflow)
    with tempfile.TemporaryDirectory(prefix="ia28-final-seal-") as tmp_s:
        tmp = Path(tmp_s)
        (tmp / "bin").mkdir()
        (tmp / "runner").mkdir()
        curl = tmp / "bin" / "curl"
        curl.write_text(MOCK_CURL, encoding="utf-8")
        curl.chmod(0o755)
        shell_path = tmp / "final-seal.sh"
        shell_path.write_text(shell, encoding="utf-8")
        state = tmp / "current-head"
        state.write_text(A + "\n", encoding="utf-8")
        trace = tmp / "api-trace.txt"
        env = os.environ.copy()
        env.update(
            {
                "PATH": str(tmp / "bin") + os.pathsep + env["PATH"],
                "RUNNER_TEMP": str(tmp / "runner"),
                "GITHUB_REPOSITORY": "Haneof/Haneof-AIOS-Core-v3.0",
                "GH_TOKEN": "MOCK_ONLY",
                "GITHUB_SHA": A,
                "GITHUB_REF": "refs/heads/" + BRANCH,
                "GITHUB_RUN_ID": RUN_ID,
                "GITHUB_RUN_ATTEMPT": "1",
                "CANONICAL_CORRECTIVE_BRANCH": BRANCH,
                "PIN_COMMENT_ID": COMMENT_ID,
                "PROBE_A": A,
                "PROBE_B": B,
                "PROBE_STATE": str(state),
                "PROBE_TRACE": str(trace),
            }
        )
        result = subprocess.run(
            ["bash", str(shell_path)],
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        final_head = state.read_text(encoding="utf-8").strip()
        print(f"candidate_sha={CANDIDATE}")
        print(f"workflow_sha256={hashlib.sha256(workflow.encode()).hexdigest()}")
        print(f"extracted_final_seal_sha256={hashlib.sha256(shell.encode()).hexdigest()}")
        print(f"branch_response_sha={A}")
        print(f"mock_ref_advanced_to={final_head}")
        print("mocked_api_calls:")
        print(trace.read_text(encoding="utf-8"), end="")
        print("final_seal_stdout:")
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
        print(f"final_seal_exit_code={result.returncode}")
        print("actions_concurrency_cancellation=NOT_SIMULATED")
        reproduced = (
            result.returncode == 0
            and "WHOLE_RUN_IDENTITY_SEAL=PASS" in result.stdout
            and final_head == B
        )
        print(
            "RESULT=POST_READ_FALSE_GREEN_REPRODUCED_WITH_MOCKED_API"
            if reproduced
            else "RESULT=COUNTEREXAMPLE_NOT_REPRODUCED"
        )
        return 0 if reproduced else 1


if __name__ == "__main__":
    raise SystemExit(main())
