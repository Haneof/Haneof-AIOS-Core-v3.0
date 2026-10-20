#!/usr/bin/env python3
"""AIOS 基线漂移检查器 (M2)。

用途：把 governance/baseline.json 里钉住的实现基线变成 CI 强制检查，
防止「任务书声明 pinned baseline，但 main 上继续长代码」的漂移。

退出码：
  0 = 无漂移 / 漂移已被授权
  1 = 检测到未授权漂移或凭证泄漏

用法：
  python tools/governance/check_baseline.py --repo . --baseline governance/baseline.json
  python tools/governance/check_baseline.py --repo . --head HEAD --json report.json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SECRET_PATTERNS = [
    ("openai_like_key", re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}")),
]

TRAILER_RE = re.compile(r"^Authorized-Task:\s*(\S+)\s*$", re.MULTILINE)


def run_git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def changed_files(repo: Path, base: str, head: str) -> list[str]:
    out = run_git(repo, "diff", "--name-only", f"{base}..{head}")
    return [line.strip() for line in out.splitlines() if line.strip()]


def commits_in_range(repo: Path, base: str, head: str) -> list[tuple[str, str]]:
    out = run_git(repo, "log", "--format=%H%x1f%B%x1e", f"{base}..{head}")
    commits: list[tuple[str, str]] = []
    for chunk in out.split("\x1e"):
        chunk = chunk.strip()
        if not chunk:
            continue
        sha, _, body = chunk.partition("\x1f")
        commits.append((sha.strip(), body))
    return commits


def match_prefix(path: str, prefixes: list[str]) -> str | None:
    for prefix in prefixes:
        if prefix.endswith("/"):
            if path.startswith(prefix):
                return prefix
        elif path == prefix:
            return prefix
    return None


def scan_secrets(repo: Path, files: list[str], head: str, scan_prefixes: list[str]) -> list[dict]:
    findings: list[dict] = []
    for path in files:
        if match_prefix(path, scan_prefixes) is None:
            continue
        try:
            blob = run_git(repo, "show", f"{head}:{path}")
        except RuntimeError:
            continue
        for lineno, line in enumerate(blob.splitlines(), start=1):
            for name, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    findings.append({"file": path, "line": lineno, "pattern": name})
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".", help="仓库根目录")
    parser.add_argument("--baseline", default="governance/baseline.json")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--json", dest="json_out", default=None)
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    baseline_path = (repo / args.baseline).resolve()
    if not baseline_path.is_file():
        print(f"[FAIL] baseline not found: {baseline_path}")
        return 1

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    pinned = baseline["pinned_sha"]
    task_id = baseline["task_id"]
    # `task_id` may be a single string or a list; several authorised tasks can be
    # in flight at once (e.g. a stacked branch spanning two windows).
    expected_tasks = {task_id} if isinstance(task_id, str) else set(task_id)
    allowed = baseline.get("allowed_paths", [])
    protected = baseline.get("protected_paths", [])
    scan_prefixes = baseline.get("secret_scan_paths", [])
    require_trailer = baseline.get("require_trailer", True)

    files = changed_files(repo, pinned, args.head)
    commits = commits_in_range(repo, pinned, args.head)

    authorized_tasks: set[str] = set()
    for _sha, body in commits:
        authorized_tasks.update(TRAILER_RE.findall(body))

    unauthorized: list[dict] = []
    authorized: list[dict] = []
    governance_only: list[str] = []

    for path in files:
        if match_prefix(path, protected) is None:
            governance_only.append(path)
            continue
        entry = {"file": path, "reason": None}
        if require_trailer and not (expected_tasks & authorized_tasks):
            entry["reason"] = (
                f"none of {sorted(expected_tasks)} declared via 'Authorized-Task' "
                f"in commits {pinned[:7]}..{args.head}"
            )
            unauthorized.append(entry)
        else:
            authorized.append(entry)

    secrets = scan_secrets(repo, files, args.head, scan_prefixes)

    report = {
        "pinned_sha": pinned,
        "head": run_git(repo, "rev-parse", args.head).strip(),
        "expected_task": task_id,
        "authorized_tasks_found": sorted(authorized_tasks),
        "total_changed_files": len(files),
        "governance_only_changes": len(governance_only),
        "authorized_protected_changes": [e["file"] for e in authorized],
        "unauthorized_protected_changes": unauthorized,
        "secret_findings": secrets,
        "verdict": "PASS" if not unauthorized and not secrets else "FAIL",
    }

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=" * 68)
    print("AIOS BASELINE DRIFT CHECK")
    print("=" * 68)
    print(f"pinned_sha        : {pinned}")
    print(f"head              : {report['head']}")
    print(f"expected task     : {task_id}")
    print(f"tasks found       : {sorted(authorized_tasks) or '(none)'}")
    print(f"changed files     : {len(files)} (governance-only: {len(governance_only)})")
    print(f"protected changes : {len(authorized) + len(unauthorized)} (authorized: {len(authorized)})")
    print("-" * 68)

    if unauthorized:
        print("[FAIL] 未授权的受保护路径变更：")
        for entry in unauthorized:
            print(f"  - {entry['file']}  ({entry['reason']})")
    else:
        print("[OK] 受保护路径无未授权变更")

    if secrets:
        print("[FAIL] 凭证模式命中：")
        for item in secrets:
            print(f"  - {item['file']}:{item['line']}  ({item['pattern']})")
    else:
        print("[OK] 未发现凭证模式")

    print("-" * 68)
    print(f"VERDICT: {report['verdict']}")
    print("=" * 68)
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
