# CORRECTIVE-013-FIXUP-001 evidence report

Status: **FIXUP_001_HANDOFF_READY**. Fresh frozen E2E and required evidence scans passed; no push is attempted because PM must reconstruct from the remote parent. This fixup is limited to current evidence/canonical synchronization; no implementation bytes are changed.

- PM blocker review: `5319913802`
- PM task release: `5835591147`
- Remote parent: `86aafc1937b58071d4780c77cf2e8abe7fcbed5b`
- Remote parent tree: `a22f14753e0627a95b08cfb8e60ae3ad80304620`
- Local source commit: `4ad5f980c2a041c88f9c0fdec62753d7f8b38fb4` (same tree, different ancestry)

## Current exact gate

`EXPECTED_CHECKS=158`; required `ALL_CHECKS=158/158 FAILURES=0`; final marker `CORRECTIVE_013_E2E_PASS`. Required markers: `ENVIRONMENT_PASS`, `RAW_USAGE_NO_SYNTHESIS_PASS`, `CANONICAL_PIN_CONSISTENCY_PASS`, `CANONICAL_PIN_MUTATION_RED_PASS`, `CANONICAL_RUNBOOK_EXECUTABLE_PASS`, `CANONICAL_RUNBOOK_ORDER_PASS`, `RUNBOOK_CROSS_DOCUMENT_ORDER_PASS`, `RUNBOOK_CROSS_DOCUMENT_MUTATION_RED_PASS cases=5`, `RUNBOOK_EXECUTABLE_MUTATION_RED_PASS cases=18`, and `RUNBOOK_SHELL_SEMANTICS_MUTATION_RED_PASS cases=34`.

## Fresh frozen run evidence

- Runtime: Debian GNU/Linux 12 (bookworm), debootstrap rootfs `/tmp/CORRECTIVE_013_DEBIAN12/rootfs`, outside the repository; rootfs bind-mounted as the process root, with `/dev` and `/proc` mounted only inside a disposable mount namespace.
- E2E: `isolation/probe_e2e.sh`, exit `0`; `EXPECTED_CHECKS=158`; `ALL_CHECKS=158/158 FAILURES=0`; final `CORRECTIVE_013_E2E_PASS`.
- Raw log: `/tmp/CORRECTIVE_013_DEBIAN12/rootfs/tmp/c013-e2e-fresh-20260926-002/e2e.log`; size `79061` bytes; SHA-256 `1352c0208a3feb5d435f59f41b57c40b3e61880f778710b9676512f396e321cf`.
- Current committed evidence: `isolation/e2e_probe_output.txt`; size `79061` bytes; SHA-256 `1352c0208a3feb5d435f59f41b57c40b3e61880f778710b9676512f396e321cf`; verified byte-identical with `cmp`.
- Cursor-14 exact-byte scan against the fixture payload: fresh raw log `0` hits; committed evidence `0` hits. Payload bytes were not printed or included in this report.
- Lifecycle self-test: `RUNBOOK_CROSS_DOCUMENT_MUTATION_RED_PASS cases=5`, `RUNBOOK_EXECUTABLE_MUTATION_RED_PASS cases=18`, and `RUNBOOK_SHELL_SEMANTICS_MUTATION_RED_PASS cases=34`; all passed.
- Additional required E2E markers verified: `ENVIRONMENT_PASS`, `RAW_USAGE_NO_SYNTHESIS_PASS`, `CANONICAL_PIN_CONSISTENCY_PASS`, `CANONICAL_PIN_MUTATION_RED_PASS`, `CANONICAL_RUNBOOK_EXECUTABLE_PASS`, `CANONICAL_RUNBOOK_ORDER_PASS`, `RUNBOOK_CROSS_DOCUMENT_ORDER_PASS`, `NO_COMMITTED_CURSOR14_PAYLOAD_PASS`, `NO_FALSE_NO_REVEAL_PROSE_PASS`, `PORTABLE_CHECKOUT_PASS`, and `ISOLATION_PASS`.

## Frozen dependency contract

- `python3 --version` and `/usr/bin/python3 --version`: exactly `Python 3.11.2`
- Pydantic `2.13.5`; pydantic_core `2.46.5`; annotated-types `0.8.0`; typing-inspection `0.4.4`; typing_extensions `4.16.0`
- `requirements.freeze.txt` remains unchanged; its SHA-256 is `bd7a76d1171c137f9daee9c0a3dbff029b8cbbccef88f0a1aff7907710a82375`; its SHA check and every exact `pip freeze` line passed.

The prior report `corrective_012_report.md` remains byte-identical and is retained solely for historical lineage. The local source commit and remote parent have identical tree `a22f14753e0627a95b08cfb8e60ae3ad80304620` but different ancestry; PM must rebuild from remote parent `86aafc1937b58071d4780c77cf2e8abe7fcbed5b`. No force-push, rebase, or squash is authorized.

## Full-tree stale sweep and classification

The final sweep scanned all 37 regular files under `C15-RCC-RES-B-PREFLIGHT-002/**` for the prior check-count/result, final-marker, current-authority, and raw-log-digest patterns. It found 18 textual matches; every remaining match is explicitly historical or a cumulative marker. No active surface asserts an obsolete gate as current.

- `corrective_012_report.md` (4 matches; lines 39, 44, 46, 48): immutable historical count, result, prior raw-log digest, and final marker.
- `operator_manifest.md` (5 matches; lines 211, 224, 230 twice, 233): a historical C011-to-C012 file timeline, a superseded C012 section heading, and the historical count/digest/final-marker record.
- `checks/mechanical_checks.md` (5 matches; line 1 and line 221 four times): title identifies the historical-through-C012 boundary; the old gate is explicitly superseded and retained as history.
- `completion_report.md` (2 matches; lines 9, 109): historical-report pointer and explicit demotion of prior count/digest from current evidence.
- `isolation/e2e_probe_output.txt` (1 match; line 879): cumulative prior marker emitted by the immutable probe; the fresh final marker is C013.
- `isolation/probe_e2e.sh` (1 match; line 3252): cumulative marker retained in the protected, unchanged script.

## Immutable inputs and scope proof

The protected implementation blobs and freeze/history inputs match HEAD exactly: lifecycle checker `bfb9b0135987ea262682f5f7eee192c762aaab22`; E2E probe `d8215562721ef3bca14eb1a24c419cbd5aa3af41`; final-freeze procedure `d77a25c11304d142d8e3fc816f5dde78a6fafbb6`; historical report `cb4fcbdc487111bee7208ed36032efd154a1a107`; requirements freeze `4d12d6f4eee2285f3a059cc51339fbdca9ce5b34`. Only the six required active docs/evidence files plus this new report differ from the local base. No implementation, requirements, fixture, evaluator, governance, or PR #205 file changed.
