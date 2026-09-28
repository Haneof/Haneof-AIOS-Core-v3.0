"""IA Gate D independent audit — REVISION 2 (probe-bug correction).

History: rev1 (`test_ia_gates_bcd_rc.py::test_ia_d_semantic_script_audit`,
sha256 262ec739...) FAILED on its own heuristic #3, which treated string
*subscript keys* such as ``mapping['name']`` as literal directive content.
That is a reviewer-probe bug, not a candidate finding. rev1 source and its
failing raw output are preserved unchanged. rev2 changes ONLY check #3:
a construction is flagged when a keyword/positional argument VALUE is itself a
string constant (or an f-string/concatenation of constants). Checks #1/#2 are
identical to rev1. The one known contract-probe construction in
``schema.assert_capability_result_contract`` is reported, and asserted to be
unreachable from publication (its result is never serialized).
"""
from __future__ import annotations

import ast
import json
import os
import pathlib

from ia_common import HARNESS_ROOT

RAW = pathlib.Path(os.environ.get("IA_RAW_DIR", "/tmp/ia/raw"))


def _const_str(node):
    return isinstance(node, ast.Constant) and isinstance(node.value, str) or isinstance(node, ast.JoinedStr)


def test_ia_d_rev2_semantic_script_audit():
    semantic_fields = {"user_input", "wake_reason", "cockpit", "capability_catalog"}
    literal_constructions, branch_hits, reads = [], [], []
    for p in sorted((HARNESS_ROOT / "aios_exchange").glob("*.py")):
        tree = ast.parse(p.read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.IfExp)):
                cond = ast.unparse(node.test)
                if any(f".{f}" in cond for f in semantic_fields | {"event", "cursor"}):
                    branch_hits.append(f"{p.name}:{node.lineno}: {cond}")
            if isinstance(node, ast.Attribute) and node.attr in semantic_fields:
                reads.append(f"{p.name}:{node.lineno}")
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") in ("ModelDirective", "CapabilityCall", "CapabilityResult"):
                vals = list(node.args) + [k.value for k in node.keywords]
                if any(_const_str(v) for v in vals):
                    literal_constructions.append(f"{p.name}:{node.lineno}: {ast.unparse(node)}")
    report = {"branch_hits": branch_hits, "semantic_field_reads": reads, "literal_constructions": literal_constructions}
    (RAW / "gate_d_independent_audit_rev2.json").write_text(json.dumps(report, indent=2))
    assert branch_hits == []
    assert all(r.startswith("schema.py:") for r in reads), reads
    assert literal_constructions == ["schema.py:126: CapabilityResult(name='contract-probe', ok=True, data=None)"], literal_constructions
    # the contract probe object is local to assert_capability_result_contract and never returned/serialized
    src = (HARNESS_ROOT / "aios_exchange" / "schema.py").read_text()
    fn = src[src.index("def assert_capability_result_contract"):src.index("def capability_result_to_mapping")]
    assert "return {" in fn and "probe" not in fn.split("return {", 1)[1]
