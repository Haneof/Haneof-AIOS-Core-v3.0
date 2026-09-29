#!/usr/bin/env python3
"""Generate REVIEWER_PROBE_FREEZE_v3.json + reviewer_probe_collection_v3.txt.

Revision 2 (corrected) of the reviewer probe suite. Revision 1 and its raw
results are preserved verbatim; nothing here reinterprets them. This script is
run BEFORE the first adversarial execution of revision 2 against the candidate.

Revision-2 corrections (each traced to an observed revision-1 probe defect, not
to candidate behavior):
  * execution method: pytest runs with ``-o pythonpath=`` (and from outside the
    product repository) so the product repo's ``pyproject.toml`` ini option
    ``pythonpath = ["src"]`` can no longer inject the live-main ``src`` tree
    ahead of the frozen RC. A conftest guard now fails loudly if any foreign
    ``aios_core`` is importable.
  * RA-01 duplicate-race probe no longer assumes implicit identity parity; it
    tests the declared-identity replay contract and records implicit-identity
    semantics separately.
  * RA-04 resume probe accepts both legal resume routes.
  * RA-05 holder rendezvous is deterministic (vh1 assumed an unspecified
    worker handshake).
  * RA-06 assertions corrected (ledger digest vs receipt fields; drift
    detection instead of artifact-aware linearity on a deliberately drifted
    artifact).
  * RA-07 C7 includes the import-purity assertion; C8 uses AST reachability
    instead of naive substring matching.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import sys

REV = pathlib.Path(sys.argv[1])
PROBES = REV / "probes_v3"

EXPECTED = {
    # RA-01 cross-process linearization (IA288-01)
    "test_ra01_cross_process.py::test_ra01_four_process_distinct_publishers":
        ("PASS", "Four independent OS processes publish distinct requests: all durable events unique, "
                 "sequence monotonic and contiguous, payload sequence == ledger ordinal, no deadlock."),
    "test_ra01_cross_process.py::test_ra01_two_process_explicit_identity_single_dispatch":
        ("PASS", "Two processes publishing the same declared request identity concurrently produce "
                 "exactly one durable request_published; the second is an idempotent replay of the "
                 "same request digest (no identity fork, no duplicate semantic dispatch)."),
    "test_ra01_cross_process.py::test_ra01_stale_prefix_identity_outside_lock_fails_closed":
        ("PASS", "Two processes derive an identity for sequence 1 (empty prefix) for different bodies "
                 "and publish concurrently: exactly one dispatch; the loser fails closed with no "
                 "artifact and no ledger record under its stale identity."),
    "test_ra01_cross_process.py::test_ra01_two_process_implicit_same_body_semantics":
        ("PASS", "Boundary semantics: implicit submissions without a declared identity are separate "
                 "requests; identities, sequences and artifacts stay unique and each durable digest "
                 "matches the exact on-disk bytes."),
    "test_ra01_cross_process.py::test_ra01_two_process_response_publish_race":
        ("PASS", "Two processes publishing different response bytes for one request yield at most one "
                 "durable response_published; the loser fails closed and durable bytes match the ledger digest."),
    "test_ra01_cross_process.py::test_ra01_two_process_consume_race":
        ("PASS", "Two consuming processes leave exactly one response_consumed."),
    "test_ra01_cross_process.py::test_ra01_publish_and_consume_race_across_processes":
        ("PASS", "Consume racing a distinct publication keeps a valid chain and one consume event."),
    "test_ra01_cross_process.py::test_ra01_handler_race_two_processes_same_snapshot":
        ("PASS", "Two handler processes on one snapshot: exactly one request_published, one "
                 "response_published, one response_consumed, identical returned directive."),
    # RA-02 directory durability (IA288-02)
    "test_ra02_directory_durability.py::test_ra02_request_dir_fsync_failure_is_not_dispatch":
        ("PASS", "Injected request-directory fsync failure raises and records no dispatch while "
                 "regular file fsync still succeeded."),
    "test_ra02_directory_durability.py::test_ra02_request_dir_open_failure_is_not_dispatch":
        ("PASS", "Injected request-directory open failure raises and records no dispatch."),
    "test_ra02_directory_durability.py::test_ra02_response_dir_fsync_failure_is_not_published":
        ("PASS", "Injected response-directory fsync failure raises before response_published."),
    "test_ra02_directory_durability.py::test_ra02_response_dir_open_failure_is_not_published":
        ("PASS", "Injected response-directory open failure raises before response_published."),
    "test_ra02_directory_durability.py::test_ra02_first_ledger_creation_dir_fsync_failure_is_not_durable":
        ("PASS", "First-ledger-creation directory fsync failure is not a durable ledger append; no "
                 "request_published record exists afterwards."),
    "test_ra02_directory_durability.py::test_ra02_first_ledger_creation_dir_open_failure_is_not_durable":
        ("PASS", "First-ledger-creation directory open failure is not a durable ledger append."),
    "test_ra02_directory_durability.py::test_ra02_ledger_append_file_fsync_failure_is_not_durable":
        ("PASS", "Control: with no real path faulted the same publication succeeds (probe sanity)."),
    # RA-03 visible-but-unproven retry
    "test_ra03_visible_unproven_retry.py::test_ra03_request_retry_after_unproven_dir_fsync":
        ("PASS", "After a visible-but-unproven request artifact, retry re-proves durability and yields "
                 "exactly one durable dispatch whose digest equals the on-disk bytes."),
    "test_ra03_visible_unproven_retry.py::test_ra03_request_retry_rejects_mutated_visible_bytes":
        ("PASS", "Mutating the visible unproven request bytes before retry must not be adopted as a "
                 "dispatch; retry fails closed and no request_published exists."),
    "test_ra03_visible_unproven_retry.py::test_ra03_response_retry_after_unproven_dir_fsync":
        ("PASS", "After a visible-but-unproven response artifact, retry yields exactly one "
                 "response_published with a matching digest."),
    "test_ra03_visible_unproven_retry.py::test_ra03_response_retry_with_different_bytes_fails_closed":
        ("PASS", "A different second response submission over an unproven visible artifact fails "
                 "closed and creates no response_published."),
    "test_ra03_visible_unproven_retry.py::test_ra03_first_ledger_retry_single_entry":
        ("PASS", "First-ledger retry after unproven creation converges to exactly one valid seq-1 entry."),
    # RA-04 crash boundaries
    "test_ra04_crash_boundaries.py::test_ra04_crash_then_retry_converges":
        ("PASS", "Every software-visible crash boundary (temp fsync/replace/dir fsync/append/receipt) "
                 "leaves a valid chain, unique events and bounded convergence after retry."),
    "test_ra04_crash_boundaries.py::test_ra04_crash_points_leave_no_orphan_dispatch":
        ("PASS", "Crash points before the ledger append record no dispatch at all."),
    "test_ra04_crash_boundaries.py::test_ra04_handler_crash_after_dispatch_resumes_without_second_dispatch":
        ("PASS", "A handler crashing immediately after the durable dispatch resumes that exact dispatch "
                 "on one legal route (resumed_dispatched_request or recovered_durable_response) and "
                 "never dispatches a second time."),
    # RA-05 lock boundary attacks
    "test_ra05_lock_attacks.py::test_ra05_lock_path_is_stable_and_dedicated":
        ("PASS", "The lock is a dedicated, stable, never-the-ledger path shared by independent objects."),
    "test_ra05_lock_attacks.py::test_ra05_lock_symlink_fails_closed":
        ("PASS", "A symlinked lock path fails closed."),
    "test_ra05_lock_attacks.py::test_ra05_lock_path_directory_fails_closed":
        ("PASS", "A directory at the lock path fails closed."),
    "test_ra05_lock_attacks.py::test_ra05_lock_inode_replacement_still_excludes":
        ("PASS", "Replacing the idle lock inode does not break mutual exclusion for later writers."),
    "test_ra05_lock_attacks.py::test_ra05_stale_lock_file_after_process_death":
        ("PASS", "A lock file left by a SIGKILLed holder does not starve a new writer."),
    "test_ra05_lock_attacks.py::test_ra05_contention_is_real_cross_process":
        ("PASS", "While a holder owns the lock an independent process observes exclusion (real "
                 "cross-process authority, not a process-local mutex) and no record appears until release."),
    "test_ra05_lock_attacks.py::test_ra05_nested_mutation_does_not_self_deadlock":
        ("PASS", "Nested transactions (same path, different objects, same process) neither deadlock "
                 "nor duplicate events."),
    "test_ra05_lock_attacks.py::test_ra05_lock_released_while_awaiting_external_response":
        ("PASS", "A handler blocked on external bytes does not hold the mutation lock (an independent "
                 "process can still acquire it)."),
    # RA-06 TOCTOU / mixed workloads
    "test_ra06_races_and_integration.py::test_ra06_tamper_between_artifact_write_and_ledger_append":
        ("PASS", "Bytes swapped inside the publication window are never dispatched, are reported by "
                 "integrity, are refused on the semantic read path, and a same-identity retry never "
                 "adopts the drifted bytes (fail closed)."),
    "test_ra06_races_and_integration.py::test_ra06_direct_consume_after_request_file_mutation":
        ("PASS", "#290 observation: direct consume remains bound to the durable response/ledger "
                 "digests; the mutated request file is unusable and cannot enter the semantic result."),
    "test_ra06_races_and_integration.py::test_ra06_two_processes_recover_same_dispatch":
        ("PASS", "Two recovery processes on one dispatch neither re-dispatch nor duplicate consume."),
    "test_ra06_races_and_integration.py::test_ra06_due_work_and_user_turn_share_exchange_root":
        ("PASS", "Simultaneous due-work and user-turn traffic on one exchange root stays linear, "
                 "consumed exactly once, with no cross-binding and no deadlock."),
    # RA-07 historical contracts
    "test_ra07_historical_contracts.py::test_c1_tampered_published_response_fails_closed":
        ("PASS", "C1: tampered published response is refused by replay, read and consume."),
    "test_ra07_historical_contracts.py::test_c1_missing_published_response_fails_closed":
        ("PASS", "C1: deleted published response fails closed on read, consume and replay."),
    "test_ra07_historical_contracts.py::test_c1_intact_replay_is_idempotent":
        ("PASS", "C1: an intact replay is idempotent and adds no second response event."),
    "test_ra07_historical_contracts.py::test_c2_wheel_trust_root_closed_set":
        ("PASS", "C2: qualified closure verifies; wrong bytes, missing wheel and extra unlocked wheel "
                 "each FAIL closed."),
    "test_ra07_historical_contracts.py::test_c2_install_uses_no_index_no_resolver":
        ("PASS", "C2: installation is offline and hash-pinned (--no-index, --no-deps)."),
    "test_ra07_historical_contracts.py::test_c4_recovery_snapshot_mismatch_fails_closed":
        ("PASS", "C4: a durable dispatch bound to another snapshot is refused (binding mismatch)."),
    "test_ra07_historical_contracts.py::test_c5_interior_mutation_detected":
        ("PASS", "C5: interior record mutation is detected."),
    "test_ra07_historical_contracts.py::test_c5_interior_deletion_detected":
        ("PASS", "C5: interior deletion is detected."),
    "test_ra07_historical_contracts.py::test_c5_duplicate_event_detected":
        ("PASS", "C5: duplicated event is detected."),
    "test_ra07_historical_contracts.py::test_c5_sequence_corruption_detected":
        ("PASS", "C5: sequence corruption is detected."),
    "test_ra07_historical_contracts.py::test_c5_digest_discontinuity_detected":
        ("PASS", "C5: hash-chain discontinuity is detected."),
    "test_ra07_historical_contracts.py::test_c5_illegal_event_order_detected":
        ("PASS", "C5: illegal event order (consume before publication) is detected."),
    "test_ra07_historical_contracts.py::test_c6_frozen_rc_identity_checks":
        ("PASS", "C6: the exact frozen RC verifies; missing git metadata, mutated Core working bytes "
                 "and a foreign repository are each BLOCKED."),
    "test_ra07_historical_contracts.py::test_c7_exact_runtime_pins":
        ("PASS", "C7: exact CPython/Pydantic/pytest/SQLite/OpenSSL pins, frozen Core tree, no foreign "
                 "aios_core on sys.path and Core imported from the verified working tree."),
    "test_ra07_historical_contracts.py::test_c8_clean_room_startup_boundary":
        ("PASS", "C8: exactly four approved startup inputs, status PREP_REVIEW_READY, run package "
                 "imports/reaches no test/synthetic/fixture/evaluator module (AST reachability)."),
}

BLOCKER_RULES = [
    "Any duplicate durable seq/event, broken chain, or two successful mutations over one prefix.",
    "Any success receipt or durable dispatch record produced while required directory durability failed.",
    "Any adoption of visible-but-unproven bytes as an already-durable dispatch.",
    "Any second semantic dispatch for one intended request (runner or publisher level).",
    "Any lock authority that is process-local only, or any lock anomaly accepted silently.",
    "Any tampered/mutated bytes entering a semantic result or being accepted as the durable request/response.",
    "Any real Resident/C15 fixture/evaluator/release-state artifact reachable or used.",
    "Any regression of C1-C9 guarantees listed in the historical tier.",
    "Any candidate source or packet change relative to the frozen H1/H2 identities.",
]

EXECUTION_METHOD = {
    "interpreter": "/home/user/ia_review/runtime/runtime/3.12.14/venv/bin/python",
    "env": {
        "PYTHONPATH": "<package_root>/harness:<frozen_rc>/src",
        "AIOS_REVIEW_REPO_ROOT": "<frozen_rc>",
        "AIOS_REVIEW_PACKAGE_ROOT": "<package_root>",
        "AIOS_REVIEW_RUNTIME_ROOT": "/home/user/ia_review/runtime",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    },
    "collect": "pytest --collect-only -q -p no:cacheprovider -o addopts= -o pythonpath= "
               "--rootdir=<probes_v2> <probes_v2>",
    "execute": "pytest -vv -p no:cacheprovider -o addopts= -o pythonpath= --rootdir=<probes_v2> "
               "<probes_v2> --junitxml=<raw>/reviewer_probes_v2.xml",
    "cwd": "outside the product repository (reviewer scratch root)",
    "why_overrides": "The product repository's pyproject.toml sets ini pythonpath=['src']; running the "
                     "probes from a path below it silently put the live-main src tree ahead of the "
                     "frozen RC in sys.path. Revision 2 pins the execution method with -o pythonpath= "
                     "and asserts import purity in conftest.",
}

VERSION = "3"
pins = json.loads(
    (pathlib.Path("/home/user/ia_review/raw/candidate_pins.json")).read_text()
) if pathlib.Path("/home/user/ia_review/raw/candidate_pins.json").exists() else {}

prev = json.loads((REV / "probes_v2" / "REVIEWER_PROBE_FREEZE_v2.json").read_text())
prev_results = {
    "raw_result_file": "raw/reviewer_probes_v2.raw.txt",
    "result": "49 passed / 0 failed",
    "raw_result_sha256": hashlib.sha256(
        (REV / "raw" / "reviewer_probes_v2.raw.txt").read_bytes()
    ).hexdigest(),
}

sources = {}
for path in sorted(PROBES.rglob("*")):
    if path.is_file() and path.name not in {"REVIEWER_PROBE_FREEZE_v3.json", "reviewer_probe_collection_v3.txt"}:
        sources[path.relative_to(PROBES).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()

enumeration = sorted(
    f"{file}::{name}"
    for file, name in (
        (path.name, line.split("(")[0].removeprefix("def ").strip())
        for path in sorted(PROBES.glob("test_ra0*.py"))
        for line in path.read_text().splitlines()
        if line.startswith("def test_")
    )
)
missing = [t for t in enumeration if t not in EXPECTED]
extra = [t for t in EXPECTED if t not in enumeration]
if missing or extra:
    raise SystemExit(f"freeze incomplete: missing={missing} extra={extra}")

freeze = {
    "probe_suite": "C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-003 independent reviewer probes",
    "probe_suite_revision": VERSION,
    "supersedes": {
        "revision": "2",
        "freeze_file": "probes_v2/REVIEWER_PROBE_FREEZE_v2.json",
        "sources_preserved_in": "probes_v2/",
        "enumeration_sha256": prev["enumeration_sha256"],
        "probe_source_hashes_sha256": prev["probe_source_hashes_sha256"],
        "raw_result_file": prev_results["raw_result_file"],
        "result": prev_results["result"],
        "raw_result_sha256": prev_results["raw_result_sha256"],
        "correction_reasons": [
            "execution environment: live-main src injected by product pyproject pythonpath ini option "
            "(observed as RA-07 C7 foreign import); fixed by -o pythonpath= plus conftest import-purity guard",
            "RA-01 duplicate probe conflated implicit identity semantics with a declared-identity contract",
            "RA-04 resume probe assumed one of two legal resume routes",
            "RA-05 holder rendezvous assumed an unspecified worker handshake (FileNotFoundError x2, "
            "and RA-05 nested test used an artifact-aware helper on a record with no artifact)",
            "RA-06 assertions compared receipt fields against the wrong digests and used artifact-aware "
            "linearity on a deliberately drifted artifact",
            "RA-07 C8 used naive substring matching and matched a prohibition sentence in a docstring",
        ],
        "revision_3_addition": "Adds one probe required by the task text §7(c): a stale-prefix identity "
                                "computed outside the mutation lock must fail closed rather than "
                                "dispatch a second artifact. Revision-2 expectations are unchanged; "
                                "the revision-2 result remains valid evidence for the unchanged probes.",
    },
    "frozen_before_execution": True,
    "frozen_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "role": "Independent Resident Launch Infrastructure Acceptance Reviewer (not author, not Resident, not PM)",
    "candidate_pins": pins,
    "freeze_generator_sha256": hashlib.sha256(
        pathlib.Path(__file__).read_bytes()
    ).hexdigest(),
    "execution_method": EXECUTION_METHOD,
    "probe_source_sha256": sources,
    "probe_source_hashes_sha256": hashlib.sha256(
        json.dumps(sources, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest(),
    "enumeration": enumeration,
    "enumeration_sha256": hashlib.sha256(
        ("\n".join(enumeration) + "\n").encode()
    ).hexdigest(),
    "expected_outcomes": [
        {"test_id": test_id, "expected": EXPECTED[test_id][0], "invariant": EXPECTED[test_id][1]}
        for test_id in enumeration
    ],
    "decision_rules": BLOCKER_RULES,
    "notes": [
        "Revision 2 expectations were written and hashed before the first adversarial execution of "
        "revision 2 against the candidate; revision 1 and its raw results are preserved unchanged.",
        "A failed probe is a finding only when the failure is a candidate behavior; probe-defect "
        "classification is recorded in the review report with the exact failing assertion.",
        "Author suites (C1-C11, Gates A-D) are regression evidence only and do not substitute for these probes.",
    ],
}

(REV / "probes_v2" / "REVIEWER_PROBE_FREEZE_v3.json").write_text(json.dumps(freeze, indent=2) + "\n")
(REV / "probes_v2" / "reviewer_probe_collection_v3.txt").write_text("\n".join(enumeration) + "\n")
print("frozen revision:", VERSION, "probes:", len(enumeration))
print("enumeration_sha256:", freeze["enumeration_sha256"])
print("probe_source_hashes_sha256:", freeze["probe_source_hashes_sha256"])
