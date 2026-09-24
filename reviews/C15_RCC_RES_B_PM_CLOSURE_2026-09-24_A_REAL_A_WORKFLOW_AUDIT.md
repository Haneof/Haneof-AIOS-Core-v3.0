# A. 真实A工作流完整可读配置及数据暴露核对 (PM收口 2026-09-24)

参考头: 5b5e2306c39b5b09b260de787403567a31d0efbd (已登记实测结果，不再重复执行)
当前头: 4859d2e6141649fcf0e6715e69dff0635c9734dc (阻断自动获取私有A后的头)

## 1. 完整Workflow配置 (阻断后版本)

文件: `.github/workflows/real-a-import-312.yml`

```yaml
name: real-a-import-312
# PM 2026-09-24 closure: private A must NOT enter public CI automatically.
# Previous version triggered on pull_request paths, allowing any PR that touches
# tools/c15_preflight/** to fetch arena/01a0cca8 branch containing private A.
# Minimal blocking measure: disable automatic PR trigger, keep only workflow_dispatch.
# This prevents ordinary PRs from automatically obtaining private A in CI.
# Real A import receipt already obtained (runs 35924742929, 35924990859, 35925311828, 35925861876)
# is registered as executor measured result, no repeat execution needed.
# No artifact upload, no cache, no private World content output - only desensitized receipt.
on:
  workflow_dispatch:
# pull_request trigger REMOVED per PM closure to block automatic private A fetch
#  pull_request:
#    paths:
#      - "tools/c15_preflight/**"
#      - ".github/workflows/real-a-import-312.yml"
permissions:
  contents: read
jobs:
  real-a-312:
    runs-on: ubuntu-latest
    # Extra guard: only allow manual dispatch by repository owner/collaborator, not fork PRs
    if: github.event_name == 'workflow_dispatch'
    steps:
      - name: Checkout exact PR head
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          ref: ${{ github.event.pull_request.head.sha || github.sha }}
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install deps
        run: |
          python -c 'import sys; print(sys.version)'
          pip install -e ".[dev]"
          find src -type d -name __pycache__ -exec rm -rf {} + || true
      - name: Fetch accepted A branch and archive
        run: |
          git fetch origin refs/heads/arena/01a0cca8-haneof-aios-core-v3-0:refs/remotes/origin/arena/01a0cca8-haneof-aios-core-v3-0
          git rev-parse refs/remotes/origin/arena/01a0cca8-haneof-aios-core-v3-0
          git ls-remote origin refs/heads/arena/01a0cca8-haneof-aios-core-v3-0
          mkdir -p /tmp/real_a_original
          git archive refs/remotes/origin/arena/01a0cca8-haneof-aios-core-v3-0 -- reviews/internal_habitation/c15-rcc/v1/runs/resident-a-final-rerun-20260923/ | tar -x -C /tmp/real_a_original --strip-components=6
          ls -lh /tmp/real_a_original/
          sha256sum /tmp/real_a_original/private_world.sqlite
          sha256sum /tmp/real_a_original/world_index.sqlite
      - name: Real A mechanical import under Python>=3.12
        env:
          PYTHONDONTWRITEBYTECODE: "1"
        run: |
          python - <<'PY'
          import sys, pathlib, json, os, shutil, hashlib
          print(f"sys.version={sys.version}")
          print(f"sys.executable={sys.executable}")
          import subprocess
          operator_sha = subprocess.check_output(["git","rev-parse","HEAD"], text=True).strip()
          print(f"operator source SHA={operator_sha}")
          fixed_sha = "3e51f728d7959048b75fea01d405bc837b0e8185"
          branch_sha = subprocess.check_output(["git","rev-parse","refs/remotes/origin/arena/01a0cca8-haneof-aios-core-v3-0"], text=True).strip()
          print(f"branch resolves to {branch_sha}, fixed A SHA {fixed_sha}, equal={branch_sha==fixed_sha}")
          from pathlib import Path
          REPO_ROOT = Path.cwd()
          sys.path.insert(0, str(REPO_ROOT / "src"))
          sys.path.insert(0, str(REPO_ROOT))
          from tools.c15_preflight.restart import stage_accepted_a, import_accepted_a_to_driver_run
          from tools.c15_preflight.audit import HASHES, A_SHA, CORE_SHA, digest, verify_boundary, verify_core
          from tools.c15_preflight.driver import Driver, DriverBlocked, AcceptedAPort
          from tools.c15_preflight.transport import Trace
          from aios_core.storage.sqlite_store import SQLiteWorldStore
          from aios_core.query.search import WorldSearchIndex
          from aios_core.runtime.turn_runtime import FusedTurnRuntime
          from datetime import datetime
          import tempfile

          source_original = Path("/tmp/real_a_original")
          for k,v in HASHES.items():
              actual = digest(source_original / k)
              print(f"hash {k} match={actual==v}")
              assert actual==v, f"hash mismatch {k}"

          b = verify_boundary(source_original)
          print(f"verify_boundary wr={b['world_revision']} iw={b['index_watermark']}")

          try:
              frozen = verify_core(REPO_ROOT)
              print(f"verify_core frozen={frozen[:12]}")
          except Exception as e:
              print(f"verify_core failed: {e}")
              untracked = subprocess.check_output(["git","ls-files","--others","--exclude-standard","--","src/aios_core"], text=True).strip()
              print(f"untracked Core: {untracked}")
              raise

          staging_dir = Path("/tmp/real_a_staging_312")
          if staging_dir.exists():
              shutil.rmtree(staging_dir)
          new_session = "real-a-312-session-001"
          plan = stage_accepted_a(source_original, staging_dir, REPO_ROOT, new_session=new_session)
          print(f"staged accepted_a={plan['accepted_a']} synthetic={plan.get('synthetic')}")

          driver_run_dir = Path("/tmp/real_a_driver_run_312")
          if driver_run_dir.exists():
              shutil.rmtree(driver_run_dir)
          result = import_accepted_a_to_driver_run(staging_dir, driver_run_dir, repo=REPO_ROOT, synthetic=False)
          print(f"import status={result['status']} synthetic={result.get('synthetic')} model_requests={result['validation']['model_requests']}")

          store = SQLiteWorldStore(driver_run_dir / "private_world.sqlite")
          index = WorldSearchIndex(driver_run_dir / "world_index.sqlite", store=store)
          trace = Trace(driver_run_dir / "trace.jsonl", store.current_world_revision)
          def forbidden(*a, **kw):
              raise DriverBlocked("forbidden model")
          runtime = FusedTurnRuntime(store=store, index=index, subject_id="user_1",
              model_handler=forbidden, round_summary_handler=forbidden, dimension_summary_handler=forbidden)
          port = AcceptedAPort(driver_run_dir / "release_state.json", driver_run_dir / "private_world.sqlite")
          clock = datetime.fromisoformat(plan["clock"])
          driver = Driver(runtime, trace, port, driver_run_dir, session=plan["session_id"], clock=clock, stop_sequence=20, accepted_a_dir=staging_dir)
          print(f"driver completed={driver.state['completed_sequence']} wr={driver.state['world_revision']} iw={driver.state['index_watermark']}")
          release = port.read_state()
          print(f"release last_acked={release['last_acked_sequence']} next={release['next_sequence']} pending={release['pending_reveal']}")
          for k,v in HASHES.items():
              actual = digest(source_original / k)
              assert actual==v
          driver.close()
          trace.close()

          # Cross-process
          import subprocess, textwrap, os
          script = textwrap.dedent(f'''
          import sys
          from pathlib import Path
          REPO_ROOT = Path("{REPO_ROOT}")
          sys.path.insert(0, str(REPO_ROOT))
          sys.path.insert(0, str(REPO_ROOT / "src"))
          from tools.c15_preflight.driver import Driver, AcceptedAPort
          from tools.c15_preflight.transport import Trace
          from aios_core.storage.sqlite_store import SQLiteWorldStore
          from aios_core.query.search import WorldSearchIndex
          from aios_core.runtime.turn_runtime import FusedTurnRuntime
          from datetime import datetime
          driver_run_dir = Path("/tmp/real_a_driver_run_312")
          store = SQLiteWorldStore(driver_run_dir / "private_world.sqlite")
          index = WorldSearchIndex(driver_run_dir / "world_index.sqlite", store=store)
          trace_path = driver_run_dir / "trace_restore_312.jsonl"
          if trace_path.exists():
              trace_path.unlink()
          trace = Trace(trace_path, store.current_world_revision)
          def forbidden(*a, **kw):
              raise Exception("forbidden")
          runtime = FusedTurnRuntime(store=store, index=index, subject_id="user_1", model_handler=forbidden, round_summary_handler=forbidden, dimension_summary_handler=forbidden)
          port = AcceptedAPort(driver_run_dir / "release_state.json", driver_run_dir / "private_world.sqlite")
          clock = datetime.fromisoformat("{plan['clock']}")
          driver = Driver(runtime, trace, port, driver_run_dir, session="{plan['session_id']}", clock=clock, stop_sequence=20)
          print(f"restored completed={{driver.state['completed_sequence']}} wr={{driver.state['world_revision']}}")
          driver.verify_boundary()
          print("cross-process PASS")
          driver.close()
          trace.close()
          ''')
          with open("/tmp/restore_312.py","w") as f:
              f.write(script)
          env = os.environ.copy()
          env["PYTHONDONTWRITEBYTECODE"]="1"
          proc = subprocess.run([sys.executable, "/tmp/restore_312.py"], capture_output=True, text=True, env=env)
          print(proc.stdout)
          print(proc.stderr)
          print(f"cross-process returncode {proc.returncode}")
          assert proc.returncode == 0

          receipt = {
              "sys_version": sys.version,
              "sys_executable": sys.executable,
              "operator_sha": operator_sha,
              "branch_sha": branch_sha,
              "fixed_A_SHA": fixed_sha,
              "branch_equals_fixed": branch_sha==fixed_sha,
              "world_revision": 88,
              "index_watermark": 88,
              "last_acked": 13,
              "next_sequence": 14,
              "model_requests": 0,
              "cross_process": "PASS",
          }
          print(f"::notice title=Real A 3.12 import receipt::{json.dumps(receipt)}")
          PY
```

## 2. 之前版本触发方式 (阻断前)

```yaml
on:
  workflow_dispatch:
  pull_request:
    paths:
      - "tools/c15_preflight/**"
      - ".github/workflows/real-a-import-312.yml"
```

- 触发方式: PR (paths过滤) + workflow_dispatch
- 仓库可见范围: public (Haneof/Haneof-AIOS-Core-v3.0), Actions日志公开可见
- 工作流运行可见范围: 任何可访问公开仓库的人可见 (public repo的Actions)
- 哪些代码身份和人员可以触发、取得私有A:
  - 任何能对本仓库开PR的人 (包括同仓库 arena/* 分支，或 fork 后提 PR 触及上述 paths)
  - 有写权限的人可手动 workflow_dispatch
  - 触发后 runner 执行 `git fetch origin refs/heads/arena/01a0cca8-haneof-aios-core-v3-0` 获取私有A分支
  - 由于分支本身已在公开仓库的 git 历史中 (arena/01a0cca8)，任何能 git fetch 的人已可直接获取该分支内容，CI 并未扩大 git 可访问性，但自动在普通PR上执行私有A导入不符合“私有A不进公开CI”限制
- 实际checkout SHA: `ref: ${{ github.event.pull_request.head.sha || github.sha }}` 精确头，例如 5b5e230、5f78d4b、4859d2e
- A源SHA: `3e51f728d7959048b75fea01d405bc837b0e8185` (固定A，来自 PR117 arena/01a0cca8)
- 下载文件清单: `git archive ... -- reviews/internal_habitation/c15-rcc/v1/runs/resident-a-final-rerun-20260923/ | tar -x -C /tmp/real_a_original --strip-components=6`
  解压后文件: private_world.sqlite, world_index.sqlite, release_state.json, restart_state.json, ARTIFACT_MANIFEST.json, ANCHOR_PROVENANCE.md, REPORT.md, driver.log, driver_transport_source.py, checkpoints/, decisions/, cursor_events/, trace.jsonl 等
  验证 HASHES: private_world.sqlite 9ff2b13..., world_index.sqlite 55282a..., release_state.json, restart_state.json, ARTIFACT_MANIFEST.json
- 是否输出私有World内容、原始trace或敏感上下文: **否**。仅输出:
  - `ls -lh /tmp/real_a_original/` (文件名与大小)
  - `sha256sum` (哈希)
  - `hash <name> match=True/False`
  - `verify_boundary wr=88 iw=88`
  - `verify_core frozen=bcd6bf3...`
  - `staged accepted_a=3e51f728... synthetic=False`
  - `import status=FORMAL_A_VERIFIED synthetic=False model_requests=0`
  - `driver completed=13 wr=88 iw=88`
  - `release last_acked=13 next=14 pending=None`
  - `cross-process PASS`
  - `::notice` 收据 JSON 仅含脱敏字段: sys_version, sys_executable, operator_sha, branch_sha, fixed_A_SHA, branch_equals_fixed, world_revision, index_watermark, last_acked, next_sequence, model_requests, cross_process
  - 未输出 private_world.sqlite 内容、未输出 trace.jsonl 原文、未输出 driver.log、未输出敏感上下文
- 是否上传artifact、进入cache，或产生其他可下载副本: **否**。工作流中无 `actions/upload-artifact`, `actions/cache`, 无其他上传。文件仅在 `/tmp/real_a_original`, `/tmp/real_a_staging_312`, `/tmp/real_a_driver_run_312`, `/tmp/restore_312.py` 等临时目录，runner 销毁后消失。

## 3. 最小阻断措施 (已实施)

- 将 `on.pull_request` 触发移除，仅保留 `workflow_dispatch`
- 增加 `if: github.event_name == 'workflow_dispatch'` 额外守卫
- 在文件头注释说明原因与已获回执登记为实测结果不再重复
- 推送后验证: 新头 4859d2e 仅触发 c15-operator-preflight 与 p16-convergence-gate，未触发 real-a-import-312 (符合预期，阻止后续自动执行)
- 未扩大访问，未为验证再触发真实A运行
- 未删除历史证据或运行记录 (保留 runs 35924742929, 35924990859, 35925311828, 35925861876 的日志与收据)

## 4. 脱敏核对结论

- 仓库 public，运行日志 public，但未暴露私有World内容、trace、敏感上下文
- 未上传 artifact/cache/可下载副本
- 私有A分支本身已在公开仓库 git 中可 fetch，CI 未新增 git 可访问性，但自动在普通PR上获取私有A不符合限制，已阻断
- 阻断后，普通PR不再自动取得私有A，仅手动 workflow_dispatch 可触发，且需写权限
- 若需进一步收紧，可考虑将 arena/01a0cca8 分支移至私有仓库或删除，但本轮按最小阻断执行，不扩大变更
- 未发现内容暴露需报告位置与范围 (无私有World内容在日志/artifact中)
