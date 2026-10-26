"""check_baseline.py 安全门回归测试。

覆盖 T0' 修复的三个缺陷：
1. nvapi- 凭证模式识别（此前 SECRET_PATTERNS 缺失该模式）。
2. src/ 纳入 secret 扫描范围 + secret_allowlist 显式例外放行。
3. 逐提交 + 逐路径授权（此前「区间内任意 trailer 放行全部路径」可被绕过）。

所有场景都在 tmp_path 下构造独立 git 仓库，不依赖真实 main 历史。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

CHECK_BASELINE = Path(__file__).resolve().parents[2] / "tools" / "governance" / "check_baseline.py"

BASELINE_TEMPLATE = {
    "_comment": "test",
    "pinned_sha": "PENDING",
    "pinned_at": "2026-10-26T00:00:00Z",
    "pinned_by": "PM",
    "task_id": ["T1"],
    "allowed_paths": ["governance/", "reviews/", "docs/", "release/"],
    "protected_paths": ["src/", "tests/", "tools/"],
    "secret_scan_paths": ["governance/", "reviews/", "docs/", "src/"],
    "require_trailer": True,
}


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    return repo


def _write(repo: Path, path: str, content: str) -> None:
    p = repo / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def _commit(repo: Path, msg: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", msg)
    return _git(repo, "rev-parse", "HEAD").strip()


def _run_check(repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(CHECK_BASELINE),
            "--repo",
            str(repo),
            "--baseline",
            str(repo / "governance" / "baseline.json"),
            "--head",
            "HEAD",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _make_base(repo: Path, src_files: dict[str, str]) -> str:
    """提交 pinned 基线（含 baseline.json 占位 + 初始 src 文件），返回 pinned sha。

    之后调用方把 baseline.json 的 pinned_sha 填为返回值，再提交一次基线修正。
    """
    _write(repo, "governance/baseline.json", json.dumps(BASELINE_TEMPLATE, indent=2))
    for path, content in src_files.items():
        _write(repo, path, content)
    return _commit(repo, "base: seed baseline + src")


def _pin_baseline(repo: Path, pinned_sha: str, *, allowlist: list[dict] | None = None) -> None:
    baseline = dict(BASELINE_TEMPLATE)
    baseline["pinned_sha"] = pinned_sha
    if allowlist is not None:
        baseline["secret_allowlist"] = allowlist
    _write(repo, "governance/baseline.json", json.dumps(baseline, indent=2))
    _commit(repo, "governance: pin baseline (governance-only change)")


def _report(repo: Path) -> dict:
    proc = subprocess.run(
        [
            sys.executable,
            str(CHECK_BASELINE),
            "--repo",
            str(repo),
            "--baseline",
            str(repo / "governance" / "baseline.json"),
            "--head",
            "HEAD",
            "--json",
            str(repo / "report.json"),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode in (0, 1), proc.stderr
    return json.loads((repo / "report.json").read_text(encoding="utf-8"))


def test_nvapi_key_detected_in_src_without_allowlist(tmp_path):
    """修复点1+2：src/ 里的 nvapi- key 必须被识别为未授权凭证。"""
    repo = _init_repo(tmp_path)
    pinned = _make_base(repo, {"src/a.py": "x = 1\n"})
    _pin_baseline(repo, pinned)

    _write(repo, "src/a.py", 'KEY = "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"\n')
    _commit(repo, "feat: add key\n\nAuthorized-Task: T1")

    proc = _run_check(repo)
    assert proc.returncode == 1
    assert "nvidia_nim_key" in proc.stdout
    assert "VERDICT: FAIL" in proc.stdout


def test_nvapi_key_allowlisted_in_src(tmp_path):
    """修复点2：登记在 secret_allowlist 的 key 是显式例外，应放行。"""
    repo = _init_repo(tmp_path)
    pinned = _make_base(repo, {"src/a.py": "x = 1\n"})
    _pin_baseline(
        repo,
        pinned,
        allowlist=[
            {
                "file": "src/a.py",
                "pattern": "nvidia_nim_key",
                "note": "owner-authorized",
                "authorized_by": "owner",
            }
        ],
    )

    _write(repo, "src/a.py", 'KEY = "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"\n')
    _commit(repo, "feat: add key\n\nAuthorized-Task: T1")

    report = _report(repo)
    assert report["verdict"] == "PASS", report
    assert report["secret_findings"] == []


def test_per_path_authorization_blocks_cross_path_bypass(tmp_path):
    """修复点3：区间内一个提交带 trailer，不能放行另一个无 trailer 提交所改的路径。"""
    repo = _init_repo(tmp_path)
    pinned = _make_base(repo, {"src/a.py": "a = 1\n", "src/b.py": "b = 1\n"})
    _pin_baseline(repo, pinned)

    _write(repo, "src/a.py", "a = 2\n")
    _commit(repo, "feat: touch a\n\nAuthorized-Task: T1")

    _write(repo, "src/b.py", "b = 2\n")
    _commit(repo, "feat: touch b (no trailer)")

    report = _report(repo)
    assert report["verdict"] == "FAIL", report
    unauthorized_files = [e["file"] for e in report["unauthorized_protected_changes"]]
    authorized_files = report["authorized_protected_changes"]
    assert "src/b.py" in unauthorized_files
    assert "src/a.py" in authorized_files
    assert "src/b.py" not in authorized_files


def test_authorized_path_passes_when_trailer_touches_it(tmp_path):
    """修复点3（正向）：带 trailer 且触碰该路径的提交，正确授权该路径。"""
    repo = _init_repo(tmp_path)
    pinned = _make_base(repo, {"src/a.py": "a = 1\n"})
    _pin_baseline(repo, pinned)

    _write(repo, "src/a.py", "a = 2\n")
    _commit(repo, "feat: touch a\n\nAuthorized-Task: T1")

    report = _report(repo)
    assert report["verdict"] == "PASS", report
    assert report["authorized_protected_changes"] == ["src/a.py"]
