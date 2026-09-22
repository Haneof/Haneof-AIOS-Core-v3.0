#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
import inspect, importlib
mods=["aios_core.runtime","aios_core.ai_world","aios_core.wake","aios_core.review","aios_core.world_graph"]
for mn in mods:
    m=importlib.import_module(mn)
    print("MODULE",mn)
    for n,v in sorted(vars(m).items()):
        if n.startswith("_"): continue
        if inspect.isclass(v) or inspect.isfunction(v):
            try: sig=str(inspect.signature(v))
            except Exception: sig="(?)"
            print(n,sig)
PY
