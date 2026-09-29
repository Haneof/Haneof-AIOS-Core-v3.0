"""IA Gate B / Gate C / Gate C-isolation / Gate D / frozen-RC import probes.

Reviewer-authored; synthetic disposable data only. Raw artifacts are written to
``IA_RAW_DIR`` (default /tmp/ia/raw).
"""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import threading
import time

import pytest

from ia_common import CANDIDATE_ROOT, CORE_SRC, HARNESS_ROOT, PREP_ROOT, snapshot
from aios_core.runtime.capabilities import CapabilityCall, CapabilityResult
from aios_core.runtime.cognitive_runtime import RuntimeSnapshot
from aios_exchange import runner
from aios_exchange.bridge import ExchangeBridge
from aios_exchange.canonical import canonical_json_bytes
from aios_exchange.schema import serialize_runtime_snapshot

FROZEN_SOFTWARE = "f20f2edfa7af00d0286493fd15196ca9503bc315"
RAW = pathlib.Path(os.environ.get("IA_RAW_DIR", "/tmp/ia/raw"))
RAW.mkdir(parents=True, exist_ok=True)
LEGAL = ("name", "ok", "data", "error_code", "error_message", "call_id")


# ---------------------------------------------------------------- frozen RC import
def _git(*args):
    return subprocess.run(["git", "-C", str(CANDIDATE_ROOT), *args], capture_output=True, text=True, check=True).stdout


def test_ia_rc_imported_core_is_byte_identical_to_frozen_tree():
    import aios_core

    assert pathlib.Path(aios_core.__file__).resolve() == (CORE_SRC / "aios_core" / "__init__.py").resolve()
    frozen = {}
    for line in _git("ls-tree", "-r", FROZEN_SOFTWARE, "src/aios_core").splitlines():
        meta, path = line.split("\t", 1)
        frozen[path] = meta.split()[2]
    loaded = [m for m in list(sys.modules.values()) if getattr(m, "__name__", "").startswith("aios_core") and getattr(m, "__file__", None)]
    assert loaded
    mismatches = []
    for m in loaded:
        rel = pathlib.Path(m.__file__).resolve().relative_to(CANDIDATE_ROOT.resolve()).as_posix()
        data = pathlib.Path(m.__file__).read_bytes()
        blob = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
        if frozen.get(rel) != blob:
            mismatches.append(rel)
    # working tree == frozen tree for the whole Core directory
    wt = subprocess.run(["git", "-C", str(CANDIDATE_ROOT), "diff", "--quiet", FROZEN_SOFTWARE, "--", "src/aios_core", "tests"])
    (RAW / "rc_import_identity.json").write_text(json.dumps({
        "aios_core__file__": aios_core.__file__, "loaded_modules": len(loaded),
        "mismatches": mismatches, "worktree_diff_vs_frozen_rc": wt.returncode,
        "frozen_core_tree": _git("rev-parse", f"{FROZEN_SOFTWARE}:src/aios_core").strip(),
        "frozen_tests_tree": _git("rev-parse", f"{FROZEN_SOFTWARE}:tests").strip(),
        "frozen_repo_tree": _git("rev-parse", f"{FROZEN_SOFTWARE}^{{tree}}").strip(),
    }, indent=2))
    assert mismatches == []
    assert wt.returncode == 0


# ---------------------------------------------------------------- Gate B
def test_ia_b0_capability_result_exact_surface():
    assert tuple(f.name for f in dataclasses.fields(CapabilityResult)) == LEGAL
    for bad in ("arguments", "result", "error", "duration_seconds"):
        assert not hasattr(CapabilityResult(name="x", ok=True), bad)
    assert tuple(f.name for f in dataclasses.fields(CapabilityCall)) == ("name", "arguments", "call_id")


def test_ia_b1_empty_history():
    s = serialize_runtime_snapshot(snapshot(0))
    assert s["capability_history"] == [] and s["round_index"] == 0
    json.dumps(s)


def test_ia_b2_success_with_data():
    r = CapabilityResult(name="ia_read", ok=True, data={"rows": [1, 2], "nested": {"k": "v"}}, call_id="c1")
    s = serialize_runtime_snapshot(snapshot(1, (r,)))
    assert s["capability_history"] == [{"name": "ia_read", "ok": True, "data": {"rows": [1, 2], "nested": {"k": "v"}},
                                        "error_code": None, "error_message": None, "call_id": "c1"}]


def test_ia_b3_failure_with_error_fields():
    r = CapabilityResult(name="ia_write", ok=False, error_code="IA_E", error_message="ia synthetic failure")
    s = serialize_runtime_snapshot(snapshot(1, (r,)))
    e = s["capability_history"][0]
    assert set(e) == set(LEGAL) and e["ok"] is False and e["error_code"] == "IA_E" and e["error_message"] == "ia synthetic failure"


def test_ia_b4_multiple_results_order_preserved():
    rs = tuple(CapabilityResult(name=f"ia_{i}", ok=bool(i % 2), data=i, error_code=None if i % 2 else "E", call_id=f"c{i}") for i in range(5))
    s = serialize_runtime_snapshot(snapshot(2, rs))
    assert [e["name"] for e in s["capability_history"]] == [f"ia_{i}" for i in range(5)]
    assert all(set(e) == set(LEGAL) for e in s["capability_history"])
    json.loads(canonical_json_bytes(s))


def test_ia_b5_no_illegal_capabilityresult_attribute_access():
    """Independent AST audit: list every attribute access to arguments/result/
    error/duration_seconds in the real-run package and classify its receiver."""
    findings = []
    for p in sorted((HARNESS_ROOT / "aios_exchange").glob("*.py")):
        tree = ast.parse(p.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in ("arguments", "result", "error", "duration_seconds"):
                findings.append({"file": p.name, "line": node.lineno, "attr": node.attr, "receiver": ast.unparse(node.value)})
    (RAW / "gate_b_attribute_audit.json").write_text(json.dumps(findings, indent=2))
    # the only permitted one: CapabilityCall.arguments (receiver named `call` in model_directive_to_mapping)
    illegal = [f for f in findings if not (f["attr"] == "arguments" and f["receiver"] == "call")]
    assert illegal == [], illegal


# ---------------------------------------------------------------- Gate C (independent)
class _IAStructuralResponder(threading.Thread):
    """Reviewer-authored content-blind responder. Round with empty history ->
    one capability call named by ``call_name``; otherwise terminal."""

    def __init__(self, root, call_name, call_args, terminal):
        super().__init__(daemon=True)
        self.root, self.call_name, self.call_args, self.terminal = root, call_name, call_args, terminal
        self.stop_evt = threading.Event()
        self.errors = []
        self.served = []

    def run(self):
        while not self.stop_evt.is_set():
            try:
                b = ExchangeBridge(self.root)
                for rid in b.recovery_state()["open_dispatched"]:
                    body = b.request_body(rid)
                    if not body["capability_history"]:
                        d = {"capability_calls": [{"name": self.call_name, "arguments": self.call_args, "call_id": "ia-call-0001"}]}
                    else:
                        d = dict(self.terminal)
                    env = {"response_version": 1, "request_id": rid, "request_sha256": b.request_sha256(rid),
                           "authored_by": "EXTERNAL_CURRENT_RESIDENT_SESSION", "directive": d}
                    b.responses.publish_bytes(request_id=rid, response_bytes=canonical_json_bytes(env) + b"\n")
                    self.served.append(rid)
            except Exception as exc:
                self.errors.append(repr(exc))
            time.sleep(0.01)


def _run_two_round(tmp_path, tag, call_name, call_args, terminal):
    root = tmp_path / "exchange"
    resp = _IAStructuralResponder(root, call_name, call_args, terminal)
    resp.start()
    try:
        result = runner.run_user_turn(
            world_path=tmp_path / "ia_world.sqlite", index_path=tmp_path / "ia_world.search.sqlite",
            exchange_root=root, subject_id="ia_synthetic_subject", session_id="ia-synthetic-session",
            turn_index=1, user_input="IA synthetic two-round probe", occurred_at="2026-09-28T00:00:00Z",
            response_timeout_s=60, poll_interval_s=0.01,
        )
    finally:
        resp.stop_evt.set(); resp.join(10)
    b = ExchangeBridge(root)
    ids = b.ledger.request_ids()
    reqs = [b.request_payload(i) for i in ids]
    out = RAW / f"gate_c_{tag}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "round_requests.json").write_text(json.dumps(reqs, indent=2, sort_keys=True))
    (out / "turn_result.json").write_text(json.dumps(result, indent=2, sort_keys=True, default=str))
    (out / "exchange_ledger.jsonl").write_bytes((root / "ledger.jsonl").read_bytes())
    for i in ids:
        (out / f"response_{i}.json").write_bytes(b.responses.published_bytes(i))
    return result, reqs, b, resp


def test_ia_c1_two_round_success_history(tmp_path):
    result, reqs, b, resp = _run_two_round(
        tmp_path, "success", "search_world", {"query": "ia synthetic probe", "limit": 2},
        {"response": "IA_SYNTHETIC_TERMINAL"})
    assert resp.errors == []
    assert len(reqs) == 2
    r0, r1 = reqs[0]["body"], reqs[1]["body"]
    assert r0["round_index"] == 0 and r0["capability_history"] == []
    assert r1["round_index"] == 1 and len(r1["capability_history"]) == 1
    h = r1["capability_history"][0]
    assert set(h) == set(LEGAL) and h["name"] == "search_world" and h["call_id"] == "ia-call-0001" and h["ok"] is True
    rt = result["turn_result"]["runtime"]
    assert rt["termination_reason"] == "responded" and rt["model_rounds"] == 2
    assert rt["capability_history"][0]["name"] == "search_world"
    assert b.integrity()["ok"] is True and b.ledger.verify_chain()["ok"] is True
    assert [r["event"] for r in b.ledger.read_records()] == ["request_published", "response_published", "response_consumed"] * 2


def test_ia_c2_two_round_failure_result_history_then_silence(tmp_path):
    result, reqs, b, resp = _run_two_round(
        tmp_path, "failure", "ia_nonexistent_capability", {}, {"silence": True})
    assert resp.errors == []
    r1 = reqs[1]["body"]
    assert r1["round_index"] == 1
    h = r1["capability_history"][0]
    assert set(h) == set(LEGAL) and h["ok"] is False and h["error_code"]
    rt = result["turn_result"]["runtime"]
    assert rt["termination_reason"] == "silence" and rt["silenced"] is True and rt["model_rounds"] == 2


# ---------------------------------------------------------------- Gate C isolation
def test_ia_isolation_runner_cannot_reach_synthetic_responder():
    code = (
        "import sys; sys.path[:0]=[%r,%r]\n"
        "import aios_exchange, aios_exchange.runner, aios_exchange.bridge, aios_exchange.verify\n"
        "bad=[m for m in sys.modules if m.startswith(('synthetic','tests','operator_tools','deterministic'))]\n"
        "print(bad); raise SystemExit(1 if bad else 0)\n" % (str(HARNESS_ROOT), str(CORE_SRC))
    )
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    src = {f.name: f.read_text() for f in (HARNESS_ROOT / "aios_exchange").glob("*.py")}
    for name, text in src.items():
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mods = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                for m in mods:
                    assert not m.startswith(("synthetic", "tests", "operator_tools")), (name, m)
            if isinstance(node, ast.Attribute) and node.attr == "environ":
                pytest.fail(f"{name} reads os.environ (possible mode switch)")
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") in ("__import__", "eval", "exec"):
                pytest.fail(f"{name} dynamic import/eval")
            if isinstance(node, ast.Attribute) and node.attr == "import_module":
                pytest.fail(f"{name} importlib dynamic import")
    assert runner.REAL_RESPONSE_MODE == "EXTERNAL_CURRENT_RESIDENT_SESSION"
    pk = json.loads((PREP_ROOT / "RESIDENT_SAFE_LAUNCH_PACKET.json").read_text())
    assert pk["real_response_mode"] == "EXTERNAL_CURRENT_RESIDENT_SESSION"


# ---------------------------------------------------------------- Gate D (independent)
def test_ia_d_semantic_script_audit():
    """Independent audit, different logic from the author scanner: enumerate every
    branch condition and every string literal used outside docstrings, and every
    read of RuntimeSnapshot semantic fields, then require that no branch depends
    on snapshot/user/event content and no directive is built from literals."""
    report = {"branch_conditions": [], "string_literals": {}, "semantic_field_reads": [], "directive_constructions": []}
    semantic_fields = {"user_input", "wake_reason", "cockpit", "capability_catalog"}
    for p in sorted((HARNESS_ROOT / "aios_exchange").glob("*.py")):
        tree = ast.parse(p.read_text())
        doc_nodes = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) and node.body \
                    and isinstance(node.body[0], ast.Expr) and isinstance(getattr(node.body[0], "value", None), ast.Constant):
                doc_nodes.add(id(node.body[0].value))
        lits = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.IfExp)):
                report["branch_conditions"].append(f"{p.name}:{node.lineno}: {ast.unparse(node.test)}")
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in doc_nodes:
                lits.add(node.value)
            if isinstance(node, ast.Attribute) and node.attr in semantic_fields:
                report["semantic_field_reads"].append(f"{p.name}:{node.lineno}: {ast.unparse(node)}")
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") in ("ModelDirective", "CapabilityCall", "CapabilityResult"):
                report["directive_constructions"].append(f"{p.name}:{node.lineno}: {ast.unparse(node)[:160]}")
        report["string_literals"][p.name] = sorted(lits)
    (RAW / "gate_d_independent_audit.json").write_text(json.dumps(report, indent=2))
    # 1) no branch condition references snapshot semantic content / user text
    for cond in report["branch_conditions"]:
        for f in semantic_fields | {"user_input", "event", "cursor"}:
            assert f".{f}" not in cond.split(":", 2)[2], cond
    # 2) semantic fields are only read for serialization (schema.py) — never in runner decisions
    for read in report["semantic_field_reads"]:
        assert read.startswith("schema.py:"), read
    # 3) directive objects are only built from parsed payload variables, never literals
    for c in report["directive_constructions"]:
        assert "'" not in c.split("(", 1)[1] and '"' not in c.split("(", 1)[1] or c.startswith("schema.py") and "contract-probe" in c, c
