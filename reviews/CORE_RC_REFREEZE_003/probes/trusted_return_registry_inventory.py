#!/usr/bin/env python3
"""Freshly bind the trusted-return replay matrix to the reachable Core registry."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile

import aios_core
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore

MATRIX_MODULE = "test_core_background_trusted_return_corrective_001_capability_replay"


def main() -> int:
    raw_target = os.environ.get("AIOS_RC_TARGET_ROOT")
    if not raw_target:
        raise RuntimeError("AIOS_RC_TARGET_ROOT must identify the exact frozen software worktree")
    target = Path(raw_target).resolve()
    module_path = Path(aios_core.__file__).resolve()
    if target not in module_path.parents:
        raise RuntimeError(f"wrong Core import {module_path}; expected below {target}")

    integration_tests = target / "tests" / "integration"
    sys.path.insert(0, str(integration_tests))
    matrix = __import__(MATRIX_MODULE, fromlist=["SCENARIO_BY_NAME"])
    expected = sorted(matrix.SCENARIO_BY_NAME)

    with tempfile.TemporaryDirectory(prefix="aios-rc003-registry-") as raw:
        root = Path(raw)
        store = SQLiteWorldStore(root / "world.sqlite")
        index = WorldSearchIndex(root / "index.sqlite", store=store)
        index.rebuild()
        runtime = FusedTurnRuntime(
            store=store,
            index=index,
            model_handler=lambda _snapshot: (_ for _ in ()).throw(
                AssertionError("registry inventory must never dispatch a model")
            ),
        )
        catalog = runtime.registry.catalog()

    reachable = sorted(item["name"] for item in catalog if item["side_effecting"])
    if reachable != expected:
        raise AssertionError(
            "live Core side-effecting registry differs from the frozen R5-C matrix: "
            f"registry_only={sorted(set(reachable) - set(expected))}; "
            f"matrix_only={sorted(set(expected) - set(reachable))}"
        )
    if len(catalog) != 43 or len(reachable) != 22:
        raise AssertionError(
            f"accepted registry surface changed: total={len(catalog)}, side_effecting={len(reachable)}"
        )

    print(
        "RESULT="
        + json.dumps(
            {
                "status": "REGISTRY_MATRIX_PASS",
                "target_sha": "f20f2edfa7af00d0286493fd15196ca9503bc315",
                "core_import": str(module_path),
                "total_reachable_capabilities": len(catalog),
                "side_effecting_capabilities": len(reachable),
                "matrix_rows": len(expected),
                "registry_matches_matrix": True,
                "provider_dispatched": False,
                "side_effecting_registry": reachable,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
