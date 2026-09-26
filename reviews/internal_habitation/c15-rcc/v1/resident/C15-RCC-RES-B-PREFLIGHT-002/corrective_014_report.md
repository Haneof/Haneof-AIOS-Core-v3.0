# CORRECTIVE-014-FIXUP-002 evidence contract

Status: **EXACT CANDIDATE — INDEPENDENT ACCEPTANCE REQUIRED BEFORE B RELEASE**

Source blocker: Independent Acceptance review `5320859635` / IA-BLK-004.

## Narrow corrective scope

CORRECTIVE-014-FIXUP-002 keeps the lifecycle scope narrow and hardens the production checker against both executable wrapper duplicates and inert shell-control lookalikes. Artifact-bound semantic guards now key on the lifecycle path signature rather than a literal executable word, and every operational step has a frozen shell-command count. Thus `command <canonical>` duplicates, short-circuit lookalikes, command-name indirection (`cmd=install; "$cmd" ...`), and split variable-indirection attempts cannot satisfy or evade exact owner/document cardinality.

The production checker also adds frozen mutation-red probes for `command <canonical lifecycle operation>` duplicates for both active runbooks.

- lifecycle checker blob: `69c1fcb6cc5ba8f4fa5629c5943dc43233c5084f`
- E2E probe: unchanged from CORRECTIVE-013
- final-freeze procedure: unchanged from CORRECTIVE-013
- Core / handler / jail / binding / Scheme-A / usage / fixture / evaluator / PR #205: unchanged

## Exact current gate

- `EXPECTED_CHECKS=158`
- `RUNBOOK_CROSS_DOCUMENT_MUTATION_RED_PASS cases=5`
- `RUNBOOK_EXECUTABLE_MUTATION_RED_PASS cases=18`
- `RUNBOOK_SHELL_SEMANTICS_MUTATION_RED_PASS cases=62`
- `ALL_CHECKS=158/158 FAILURES=0`
- cumulative final probe marker remains `CORRECTIVE_013_E2E_PASS`

The exact committed `isolation/e2e_probe_output.txt` is the authoritative frozen-run evidence. It must come from a real Debian 12 environment with both `python3` and `/usr/bin/python3` at Python 3.11.2 and the frozen package subset. It must also retain the zero sealed cursor-14 payload-leak invariant.

No B release, Resident B/C run, merge, evaluator, or closure is authorized until fresh Independent Acceptance passes this exact candidate.
