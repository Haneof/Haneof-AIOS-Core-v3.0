# Resident Wire Protocol (Mechanical, Frozen)

**File:** `harness/resident_wire_protocol.json`
**SHA-256:** `5067701b003f99c141ecef1874ae8195ea2faf1ef5caa87cae092b57cad38b38`
**Version:** 1.0.0
**Purpose:** Machine wire format for Resident B model output. This artifact is **separate** from `RESIDENT_B_RUN_CONTRACT.md` (semantic contract) and contains **only** mechanical schema.

The model must output JSON with exact binding fields `round`, `request_id`, `request_digest` echoed from the request, plus `action` in `invoke_capability|end_turn|silence|summary_response` and per-action allowlisted fields. No fixture hint, expected answer, evaluator semantics, or future cursor knowledge is present.

This protocol is pinned by SHA-256 above and is purely mechanical. Changing it requires re-freeze and re-audit.

See `resident_wire_protocol.json` for exact JSON Schema.
