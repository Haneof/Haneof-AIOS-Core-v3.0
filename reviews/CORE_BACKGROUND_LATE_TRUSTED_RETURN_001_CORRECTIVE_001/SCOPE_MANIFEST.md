# SCOPE_MANIFEST

Allowed task changes are confined to Core runtime, Core tests, the task workflow and Corrective-001 evidence.

Production paths changed:
- `src/aios_core/runtime/background_attempt.py`
- `src/aios_core/runtime/late_return.py`
- `src/aios_core/runtime/turn_runtime.py`
- `src/aios_core/runtime/__init__.py`

Explicit zero-diff protected scopes:
- `tools/c15_persistence/**`
- `tools/c15_preflight/**`
- `evidence/w08/**`
- `reviews/internal_habitation/**`
- Resident run evidence / fixtures / evaluator material
- PR #305 branch
- canonical Window 14 review branch

No Resident was run.
