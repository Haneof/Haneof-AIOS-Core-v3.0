#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
import inspect
from aios_core.runtime import FusedTurnRuntime, CognitiveRuntime, CapabilityRegistry
from aios_core.world_graph import SQLiteWorldStore, WorldSearchIndex
from aios_core.wake import WakeBus
from aios_core.review import PeriodicReviewService
classes=[FusedTurnRuntime,CognitiveRuntime,CapabilityRegistry,SQLiteWorldStore,WorldSearchIndex,WakeBus,PeriodicReviewService]
for cls in classes:
    print("CLASS",cls.__module__+"."+cls.__name__)
    for n in dir(cls):
        if n.startswith("_"): continue
        try: v=getattr(cls,n)
        except Exception: continue
        if callable(v):
            try: print(n, inspect.signature(v))
            except Exception: pass
PY
