# CORRECTIVE-014 evidence contract

Status: **EXACT CANDIDATE — INDEPENDENT ACCEPTANCE REQUIRED BEFORE B RELEASE**

Source blocker: Independent Acceptance review `5320859635` / IA-BLK-004.

## Narrow corrective scope

CORRECTIVE-014 changes only the Phase-B lifecycle checker semantics needed to reject real executable duplicates hidden behind shell-dispatch prefixes. A required lifecycle executable signature now counts even when an active bash/sh/shell command prefixes it with dispatch/control text such as `command`, `exec`, `env`, or an equivalent shell prefix. Exact owner-step and document-wide cardinality therefore cannot be satisfied by keeping one bare canonical command while adding a wrapped duplicate.

The production checker also adds frozen mutation-red probes for `command <canonical lifecycle operation>` duplicates for both active runbooks.

- lifecycle checker blob: `259e53def41b4d71e68d6481c6cc8842fdd05bba`
- E2E probe: unchanged from CORRECTIVE-013
- final-freeze procedure: unchanged from CORRECTIVE-013
- Core / handler / jail / binding / Scheme-A / usage / fixture / evaluator / PR #205: unchanged

## Exact current gate

- `EXPECTED_CHECKS=158`
- `RUNBOOK_CROSS_DOCUMENT_MUTATION_RED_PASS cases=5`
- `RUNBOOK_EXECUTABLE_MUTATION_RED_PASS cases=18`
- `RUNBOOK_SHELL_SEMANTICS_MUTATION_RED_PASS cases=48`
- `ALL_CHECKS=158/158 FAILURES=0`
- cumulative final probe marker remains `CORRECTIVE_013_E2E_PASS`

The exact committed `isolation/e2e_probe_output.txt` is the authoritative frozen-run evidence. It must come from a real Debian 12 environment with both `python3` and `/usr/bin/python3` at Python 3.11.2 and the frozen package subset. It must also retain the zero sealed cursor-14 payload-leak invariant.

No B release, Resident B/C run, merge, evaluator, or closure is authorized until fresh Independent Acceptance passes this exact candidate.
