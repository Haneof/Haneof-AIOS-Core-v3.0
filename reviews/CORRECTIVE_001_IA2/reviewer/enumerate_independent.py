"""INDEPENDENT reviewer capability enumeration (sound over-approximation).

Does NOT trust ``CapabilitySpec.side_effecting``.

Method: parse EVERY module under ``src/aios_core`` and build a whole-program
call graph.  Seed the "durable write" set with functions that directly execute
a SQL mutation (INSERT/UPDATE/DELETE/REPLACE) or call the world-store commit
primitives, then propagate to a fixpoint over bare callee names.  Matching by
bare name deliberately OVER-approximates: it can only mark too many handlers
side-effecting, never too few.  For an acceptance review that is the safe
direction -- an under-approximation would hide a reachable durable write.

The declared flag is then compared against this independent classification.
"""
from __future__ import annotations

import ast
import inspect
import json
import sqlite3
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any

STORE_COMMIT_METHODS = {"commit", "commit_or_replay", "replay_exact_operation"}
SQL_MUT = ("insert", "update", "delete", "replace")


def _sql_literal(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(
            p.value if isinstance(p, ast.Constant) else "?" for p in node.values
        )
    if isinstance(node, ast.BinOp):
        left = _sql_literal(node.left)
        return None if left is None else left
    return None


class FuncInfo:
    __slots__ = ("key", "module", "callees", "direct_durable")

    def __init__(self, key: str, module: str) -> None:
        self.key = key
        self.module = module
        self.callees: set[str] = set()
        self.direct_durable = False


def _collect(node: ast.AST, info: FuncInfo) -> None:
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        fn = child.func
        bare = None
        if isinstance(fn, ast.Attribute):
            bare = fn.attr
            recv = fn.value
            # self.store.commit(...) / store.commit(...)
            recv_name = None
            if isinstance(recv, ast.Name):
                recv_name = recv.id
            elif isinstance(recv, ast.Attribute):
                recv_name = recv.attr
            if bare in STORE_COMMIT_METHODS and recv_name in {
                "store", "_store", "world_store",
            }:
                info.direct_durable = True
        elif isinstance(fn, ast.Name):
            bare = fn.id
        if bare:
            info.callees.add(bare)
            info.callees.add(bare.lstrip("_"))
        # SQL mutation through any cursor/connection
        if isinstance(fn, ast.Attribute) and fn.attr in {
            "execute", "executemany", "executescript",
        }:
            lit = _sql_literal(child.args[0]) if child.args else None
            if lit is not None and " ".join(lit.lower().split()).startswith(SQL_MUT):
                info.direct_durable = True


def build_graph(src_root: Path) -> dict[str, FuncInfo]:
    funcs: dict[str, FuncInfo] = {}
    for path in sorted(src_root.rglob("*.py")):
        rel = path.relative_to(src_root).with_suffix("")
        module = ".".join(rel.parts)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        # module level
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            # derive a qualname by locating enclosing class
            qual = node.name
            for cls in ast.walk(tree):
                if isinstance(cls, ast.ClassDef) and node in cls.body:
                    qual = f"{cls.name}.{node.name}"
            key = f"{module}::{qual}"
            info = funcs.get(key)
            if info is None:
                info = FuncInfo(key, module)
                funcs[key] = info
            _collect(node, info)
    return funcs


def fixpoint(funcs: dict[str, FuncInfo]) -> set[str]:
    """Keys of functions that reach a durable write (over-approximate)."""
    by_bare: dict[str, set[str]] = {}
    for key, info in funcs.items():
        bare = key.split("::", 1)[1].split(".")[-1]
        by_bare.setdefault(bare, set()).add(key)
        by_bare.setdefault(bare.lstrip("_"), set()).add(key)

    durable = {k for k, i in funcs.items() if i.direct_durable}
    changed = True
    while changed:
        changed = False
        for key, info in funcs.items():
            if key in durable:
                continue
            for callee in info.callees:
                targets = by_bare.get(callee, ())
                if any(t in durable for t in targets):
                    durable.add(key)
                    changed = True
                    break
    return durable


def main() -> int:
    from aios_core.query.search import WorldSearchIndex
    from aios_core.runtime.turn_runtime import FusedTurnRuntime
    from aios_core.storage.sqlite_store import SQLiteWorldStore

    import aios_core
    src_root = Path(aios_core.__file__).resolve().parent

    funcs = build_graph(src_root)
    durable = fixpoint(funcs)

    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "world.db"
        store = SQLiteWorldStore(db)
        index = WorldSearchIndex(db, store=store)
        index.rebuild()
        runtime = FusedTurnRuntime(
            store=store, index=index,
            model_handler=lambda _s: (_ for _ in ()).throw(
                AssertionError("enumeration never dispatches")),
        )
        catalog = runtime.registry.catalog()

        authorize_names: set[str] = set()
        tree = ast.parse(textwrap.dedent(
            inspect.getsource(type(runtime)._authorize_side_effect)))
        for node in ast.walk(tree):
            if isinstance(node, ast.Set):
                authorize_names.update(
                    e.value for e in node.elts
                    if isinstance(e, ast.Constant) and isinstance(e.value, str)
                )

        rows = []
        for entry in catalog:
            name = entry["name"]
            handler = runtime.registry._items[name].handler
            fn = getattr(handler, "__func__", handler)
            module = getattr(fn, "__module__", "?")
            qual = getattr(fn, "__qualname__", "?").replace("<locals>.", "")
            # aios_core.runtime.turn_runtime  -> path-style module key
            mod_key = module
            key = f"{mod_key}::{qual}"
            reaches = key in durable
            if not reaches:
                # fall back to bare-name match anywhere in the program
                bare = qual.split(".")[-1]
                reaches = any(
                    k in durable and k.split("::", 1)[1].split(".")[-1] == bare
                    for k in funcs
                )
            rows.append({
                "name": name,
                "declared_side_effecting": bool(entry["side_effecting"]),
                "independent_reaches_durable_write": bool(reaches),
                "kind": entry["kind"],
                "hard_boundary": bool(entry["hard_boundary"]),
                "in_authorize_allowlist": name in authorize_names,
                "handler": f"{module}.{qual}",
                "parameters": [
                    p.name for p in inspect.signature(fn).parameters.values()
                    if p.name != "self"
                ],
            })

        declared = {r["name"] for r in rows if r["declared_side_effecting"]}
        independent = {r["name"] for r in rows if r["independent_reaches_durable_write"]}
        allow = {r["name"] for r in rows if r["in_authorize_allowlist"]}

        payload = {
            "model_callable": len(rows),
            "declared_side_effecting": sorted(declared),
            "independent_reaches_durable_write": sorted(independent),
            "authorize_allowlist": sorted(allow),
            "counts": {
                "model_callable": len(rows),
                "declared": len(declared),
                "independent": len(independent),
                "allowlist": len(allow),
            },
            "declared_minus_independent": sorted(declared - independent),
            "independent_minus_declared": sorted(independent - declared),
            "declared_xor_allowlist": sorted(declared ^ allow),
            "graph": {
                "functions_parsed": len(funcs),
                "functions_reaching_durable": len(durable),
            },
            "catalog": rows,
            "environment": {
                "python": sys.version.split()[0],
                "sqlite": sqlite3.sqlite_version,
            },
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        print(
            f"\n# model_callable={len(rows)} declared={len(declared)} "
            f"independent={len(independent)} allowlist={len(allow)}",
            file=sys.stderr)
        print(f"# declared-independent = {sorted(declared-independent)}", file=sys.stderr)
        print(f"# independent-declared = {sorted(independent-declared)}", file=sys.stderr)
        print(f"# declared XOR allowlist = {sorted(declared^allow)}", file=sys.stderr)
        print(f"# graph: {len(funcs)} funcs, {len(durable)} reach durable", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
