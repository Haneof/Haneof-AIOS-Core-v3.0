"""Corrective-001 capability replay matrix enumeration artifact.

Authoritative source: the live ``FusedTurnRuntime.registry.catalog()``.
This script never hardcodes the capability inventory; it enumerates the real
runtime registry and resolves each side-effecting capability to its registered
handler and its durable write path.
"""
from __future__ import annotations

import inspect
import json
import sqlite3
import sys
import tempfile
from pathlib import Path

from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore


def build_runtime(db_path):
    store = SQLiteWorldStore(db_path)
    index = WorldSearchIndex(db_path, store=store)
    index.rebuild()

    def provider(_snapshot):
        raise AssertionError("enumeration never dispatches a provider")

    return FusedTurnRuntime(store=store, index=index, model_handler=provider)


def handler_location(handler) -> str:
    fn = getattr(handler, "__func__", handler)
    module = getattr(fn, "__module__", "?")
    qual = getattr(fn, "__qualname__", getattr(handler, "__qualname__", "?"))
    try:
        path = Path(inspect.getsourcefile(fn) or "?")
        line = inspect.getsourcelines(fn)[1]
        src = f"{path.name}:{line}"
    except (OSError, TypeError):
        src = "?"
    return f"{module}.{qual} @ {src}"


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "world.db"
        runtime = build_runtime(db)
        catalog = runtime.registry.catalog()
        rows = []
        for entry in catalog:
            name = entry["name"]
            handler = runtime.registry._items[name].handler
            sig = inspect.signature(getattr(handler, "__func__", handler))
            params = [
                p.name
                for p in sig.parameters.values()
                if p.name != "self"
            ]
            rows.append(
                {
                    "name": name,
                    "kind": entry["kind"],
                    "side_effecting": bool(entry["side_effecting"]),
                    "hard_boundary": bool(entry["hard_boundary"]),
                    "handler": handler_location(handler),
                    "parameters": params,
                    "input_schema": entry["input_schema"],
                }
            )
        side = [r for r in rows if r["side_effecting"]]
        payload = {
            "model_callable_capabilities": len(rows),
            "side_effecting_capabilities": len(side),
            "sqlite_version": sqlite3.sqlite_version,
            "python": sys.version.split()[0],
            "catalog": rows,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        print(
            f"\n# model_callable={len(rows)} side_effecting={len(side)}",
            file=sys.stderr,
        )
        print(
            "# side-effecting inventory:\n"
            + "\n".join(f"#   {i:2d}. {r['name']}  -> {r['handler']}" for i, r in enumerate(side, 1)),
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
