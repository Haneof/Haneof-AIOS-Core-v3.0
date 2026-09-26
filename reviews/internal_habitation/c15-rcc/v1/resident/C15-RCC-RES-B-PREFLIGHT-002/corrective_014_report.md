# CORRECTIVE-014-FIXUP-001 evidence contract

Status: **EXACT CANDIDATE — INDEPENDENT ACCEPTANCE REQUIRED BEFORE B RELEASE**

Source blocker: Independent Acceptance review `5320859635` / IA-BLK-004.

## Narrow corrective scope

CORRECTIVE-014-FIXUP-001 keeps the lifecycle scope narrow and hardens the production checker against both executable wrapper duplicates and inert shell-control lookalikes. A broad semantic guard identifies lifecycle-shaped shell commands anywhere in the active bash/sh/shell command, while qualification still requires the single semantic occurrence to use the direct canonical form. Thus `command <canonical>` duplicates, `false && <canonical>`, and `true || <canonical>` cannot satisfy or evade exact owner/document cardinality.

The production checker also adds frozen mutation-red probes for `command <canonical lifecycle operation>` duplicates for both active runbooks.

- lifecycle checker blob: `046c5af7feb21460b3d91a1ad2761a826a9f936e`
- E2E probe: unchanged from CORRECTIVE-013
- final-freeze procedure: unchanged from CORRECTIVE-013
- Core / handler / jail / binding / Scheme-A / usage / fixture / evaluator / PR #205: unchanged

## Exact current gate

- `EXPECTED_CHECKS=158`
- `RUNBOOK_CROSS_DOCUMENT_MUTATION_RED_PASS cases=5`
- `RUNBOOK_EXECUTABLE_MUTATION_RED_PASS cases=18`
- `RUNBOOK_SHELL_SEMANTICS_MUTATION_RED_PASS cases=52`
- `ALL_CHECKS=158/158 FAILURES=0`
- cumulative final probe marker remains `CORRECTIVE_013_E2E_PASS`

The exact committed `isolation/e2e_probe_output.txt` is the authoritative frozen-run evidence. It must come from a real Debian 12 environment with both `python3` and `/usr/bin/python3` at Python 3.11.2 and the frozen package subset. It must also retain the zero sealed cursor-14 payload-leak invariant.

No B release, Resident B/C run, merge, evaluator, or closure is authorized until fresh Independent Acceptance passes this exact candidate.
