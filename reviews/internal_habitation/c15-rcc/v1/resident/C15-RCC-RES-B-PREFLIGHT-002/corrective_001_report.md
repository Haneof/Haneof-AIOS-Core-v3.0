# C15-RCC-RES-B-PREFLIGHT-002-CORRECTIVE-001 — Completion Report Addendum

Previous candidate SHA (preserved as historical failure per PM directive):
`37963774dc13b10862e9240f02a8e26238accbcc`

Verdict after corrective fix: **REVIEW_READY / AWAITING_PM_RE-REVIEW**

## Blockers addressed

| # | Blocker | Resolution |
| --- | --- | --- |
| 1 | NETWORK_SEAL_BYPASS | Added `CLONE_NEWNET`; loopback is the only interface (no routes); urllib connect to github/raw/api/8.8.8.8 returns ENETUNREACH errno=101. Verified inside probe. |
| 2 | PID_NAMESPACE_NOT_ISOLATED | Added `CLONE_NEWPID` + a PID-1 init helper that reaps children; /proc is mounted fresh inside the new PID namespace; only 3–4 PIDs visible, no host init comm present. False "pid 1 is sandbox init" claim in the old isolation report is removed; replaced with honest, verified description. |
| 3 | PRIVILEGE_DROP_FAIL_OPEN | Removed `except Exception: pass`; every step (`setgroups`/`setgid`/`setuid`/`chroot`) raises on failure; post-drop verification (cannot regain uid 0, cannot mount) runs BEFORE exec; any failure exits 98 without executing the command. |
| 4 | MAILBOX_PATH_NOT_PROVEN | Replaced private tmpfs inbox/outbox with bind-mounted host directories; chmod 0755 inbox (root:nogroup) / 01733 outbox (root:nogroup) allows operator→Resident read and Resident→operator file creation while preventing overwrite; archive is not mounted. Explicit IPC verified by E2E probe: operator sends → file appears in host mailbox dir → responder replies → operator receives reply → archive file created on host. |
| 5 | RESIDENT_ENVELOPE_NOT_FAIL_CLOSED | Added strict allowlist validation: top-level keys, event exactly-8-fields, forbidden substring scan, capability_history session-id restriction, phase/allowed_sequences enforcement. Extra fields / forbidden substrings / wrong-session refs are rejected BEFORE file write; 7 self-tests PASS. |
| 6 | READ_ONLY_BIND_NOT_PROVEN | Switched to canonical bind+remount-RO sequence (`MS_BIND` then `MS_BIND|MS_REMOUNT|MS_RDONLY|MS_NOSUID|MS_NODEV`); /proc/mounts inside sandbox shows `ro,nosuid,nodev`; both `touch` and direct `dd`/`os.open(O_WRONLY)+os.write` fail (EROFS / EACCES). |
| 7 | STARTUP_PROCEDURE_FILENAME_BUG | Fixed `b_startup_procedure.md` §1 to copy to `world.sqlite`/`index.sqlite`/`release_state.json` (matching headless CLI expectations) and verify digests against those names. Mailbox root is now created and passed as `--mailbox-root` in the sandbox launch; E2E probe step added as Step 4a. |
| 8 | REAL_TRANSPORT_E2E_PROBE | Added `isolation/probe_e2e.sh` + `isolation/resident_test_responder.py` (synthetic, deterministic, NO real B fixture, NO cursor 14 reveal, NO model): creates disposable runtime, runs isolation probe, launches responder inside sandbox as nobody, drives 3 normal mailbox rounds through the bridge, asserts replies arrive + archive exists, asserts malformed envelope is rejected without file write. Final line: `E2E_PROBE_PASS`. |

## Invariants re-verified

- Core tree `src/aios_core` = `fe77f8a0706acfaf369041d0882b6d0e6de39f22` (unchanged).
- #205 head still at `d17ae972ad1d312735c355f775ac024bc4cebdf7` (unchanged).
- lineage_copy/ SHA-256: World `626c6bb3...`, Index `ecfabf4...`, release-state `eada20a...` — all match accepted A freeze.
- release_state: last_ack=13, next_sequence=14, pending_reveal=null, active_phase=A (pre-init); Phase-B init was tested on disposable copies only; the lineage_copy in this PR is untouched Phase-A terminal state.
- Cursor 14 was NOT revealed: the only release_operator call made during this corrective was `init --phase B` on disposable copies (which validates the receipt chain and transitions active_phase without reading/emitting cursor 14's payload). `reveal` was never invoked.
- Resident B and Resident C were NOT run; the responder is a deterministic synthetic Python script, not a model.
- Core was NOT modified; no source file under `src/aios_core/` has changed since the prior candidate (0 diff lines).
- #205 was NOT modified; the canonical evidence PR remains OPEN / UNMERGED / PINNED.
- Previous candidate commit `37963774...` is preserved in Git history (no force-push, no rebase); this corrective commit is layered on top.

## Probe raw outputs

- `isolation/probe_output.txt` — ISOLATION_PASS (11 sealed paths absent, RO enforced, nobody uid confirmed, setuid/mount denied, network sealed, PID ns fresh).
- `isolation/e2e_probe_output.txt` — ends `E2E_PROBE_PASS` (3 round trips OK, malformed envelope rejected, no inbox write on bad envelope).

## Changed-file manifest (this corrective commit, on top of 3796377)

All changes confined to:
```
reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/
├── checks/mechanical_checks.md
├── completion_report.md
├── copied_lineage_hash_manifest.md
├── harness/resident_jail.py                 (rewritten: NET+PID NS, bind+remount RO, fail-closed privdrop, host bind-mailbox)
├── harness/mailbox_bridge.py                (rewritten: strict envelope allowlist, substring scan, self-tests)
├── identity_inventory.md
├── isolation/isolation_report.md            (rewritten: accurate OS-level claims)
├── isolation/probe_isolation.sh             (rewritten: network seal, PID-ns check, write-failure tests, RO write probe)
├── isolation/resident_test_responder.py     (new: synthetic responder for E2E probe)
├── isolation/probe_output.txt
├── isolation/e2e_probe_output.txt           (new)
├── known_limitations.md
├── procedure/b_startup_procedure.md         (fix filename bug, add --mailbox-root + E2E probe step)
├── procedure/final_freeze_procedure.md
├── procedure/per_cursor_interaction.md
├── operator_manifest.md
├── resident_safe_packet_manifest.md
├── source_pins_and_digests.md
└── lineage_copy/{private_world.sqlite, world_index.sqlite, release_state.json}
```

Zero files under `src/`, `governance/`, fixture/, evaluator/, release machinery, #205 paths, or prior Resident evidence have been modified.

## Exit boundary

This corrective ends at **REVIEW_READY / AWAITING_PM_RE-REVIEW**. I do not:
- merge #209
- run B or C
- reveal cursor 14
- modify Core
- accept this preflight myself
