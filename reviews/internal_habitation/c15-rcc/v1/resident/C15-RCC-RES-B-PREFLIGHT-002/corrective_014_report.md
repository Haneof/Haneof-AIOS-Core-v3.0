# CORRECTIVE-014-FIXUP-006 evidence contract

Status: **EXACT CANDIDATE — INDEPENDENT ACCEPTANCE REQUIRED BEFORE B RELEASE**

Source blocker: Independent Acceptance review `5320859635` / IA-BLK-004.

## Narrow corrective scope

CORRECTIVE-014-FIXUP-006 keeps the lifecycle scope narrow and hardens the production checker against both executable wrapper duplicates and inert shell-control lookalikes. Artifact-bound semantic guards accept either the direct executable word or an explicit command-name assignment (`cmd=install`, `cmd=rm`, `cmd=sha256sum`) together with the lifecycle artifact signature, while every operational step has a frozen shell-command count. Thus `command <canonical>` duplicates, short-circuit lookalikes, command-name indirection (`cmd=install; "$cmd" ...`), and split variable-indirection attempts cannot satisfy or evade exact owner/document cardinality.

The production checker also adds frozen mutation-red probes for `command <canonical lifecycle operation>` duplicates for both active runbooks.

- lifecycle checker blob: `72f674b2d430262a5eff9cb66c7004917c0f4ae4`
- E2E probe: unchanged from CORRECTIVE-013
- final-freeze procedure: unchanged from CORRECTIVE-013
- Core / handler / jail / binding / Scheme-A / usage / fixture / evaluator / PR #205: unchanged

## Exact current gate

- `EXPECTED_CHECKS=158`
- `RUNBOOK_CROSS_DOCUMENT_MUTATION_RED_PASS cases=5`
- `RUNBOOK_EXECUTABLE_MUTATION_RED_PASS cases=18`
- `RUNBOOK_SHELL_SEMANTICS_MUTATION_RED_PASS cases=82`
- `ALL_CHECKS=158/158 FAILURES=0`
- cumulative final probe marker remains `CORRECTIVE_013_E2E_PASS`

The exact committed `isolation/e2e_probe_output.txt` is the authoritative frozen-run evidence. It must come from a real Debian 12 environment with both `python3` and `/usr/bin/python3` at Python 3.11.2 and the frozen package subset. It must also retain the zero sealed cursor-14 payload-leak invariant.

No B release, Resident B/C run, merge, evaluator, or closure is authorized until fresh Independent Acceptance passes this exact candidate.


FIXUP-004 additionally freezes the complete normalized shell form for REVEAL, production MODEL_WORK, and DURABLE_ACK. Same-logical-command compound duplicates with quote-concatenated executable tokens are mutation-red; a canonical prefix is no longer sufficient.


FIXUP-005 extends the same semantic exact-once rule document-wide. Executable wrapper duplicates placed before or outside all operational step headings are mutation-red and cannot evade owner-step checks.

FIXUP-006 adds a final exact-byte release backstop after semantic validation. Frozen active runbook blobs: startup `c56f528f4ea181ae002ed22d3e810ab6022ddb17`; per-cursor `17f27956152f4edd49b57f72c7546eef668406fa`. Known adversarial mutations still execute the semantic production gate first; unforeseen shell-equivalent or byte drift cannot qualify modified runbooks.
