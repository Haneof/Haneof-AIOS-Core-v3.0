# C15-RCC-RES-B-PREFLIGHT-002 — Known Limitations

These are disclosed transparently. None of them is a blocker for REVIEW_READY; each is called out so the independent release reviewer can assess risk.

1. **Trusted model-provider identity is UNKNOWN.**
   The sandbox provides OS-level filesystem isolation but does not attest that the model serving B is a specific provider or family. Provider identity will be captured as-reported by the API but is not independently attested. This is a known limitation for the future replacement-model gate (R6) and is not introduced by this preflight — it was already present for A-002.

2. **Sandbox requires sudo.**
   `resident_jail.py` must run as root to create the mount namespace and perform bind mounts. The Resident child drops privileges to `nobody` before executing any model code. The independent release reviewer must re-run the isolation probe before launching B.

3. **Network access inside sandbox is not restricted.**
   The sandbox inherits the host network namespace. This is needed so the operator-side model handler (or a model-provider client running on behalf of the Resident) can reach the provider API. The sandbox does not prevent a maliciously prompted Resident from attempting network calls; however the Resident only executes via the ModelHandler, and capability calls are Core-mediated, not arbitrary shell access. The chroot does not include arbitrary network tools (no curl/wget by default; Python `urllib` is available via /usr). If stronger network isolation is required, an intermediate network-namespace + proxy step can be added in a later hardening pass without changing the isolation filesystem contract.

4. **Operator sees sealed material by design.**
   Release_contract §2 explicitly allows the operator to read sealed fixture material internally in order to emit the 8-field resident-visible projection. This is not a limitation — it is the intended separation: operator is transport/mechanics, Resident is semantic decision-maker, and the two MUST run in separate contexts (corrective decision §3).

5. **Preflight did not execute a real model roundtrip.**
   Section 8.10 of the brief allows testing Phase-B init on disposable copies but prohibits running genuine Resident cognition. The mailbox bridge is unit-verified only in the structural sense (JSON shape, blocking on reply); a single structural end-to-end test with a trivial stub handler can be done by the release task during the B startup dry-run (before revealing cursor 14), but is not part of this preflight.

6. **Old #121 evidence preserved as historical.**
   The failed B #121 run (NON-CANONICAL / DIAGNOSTIC) remains in the repository under `reviews/internal_habitation/.../resident/C15-RCC-RES-B-001/` or similar historical path. Because the entire `reviews/internal_habitation/c14-resident/` and other historical resident directories are not mounted into the B sandbox, the Resident cannot read it. The operator sees it (operator is non-blind).

7. **Prompt-level prohibitions are retained as defense in depth only.**
   `RESIDENT_B_RUN_CONTRACT.md` §3 instructs the Resident not to search sealed paths. Because those paths do not exist in the sandbox, this is a redundant safeguard, not the primary isolation mechanism. The primary mechanism is OS-level (mount namespace + chroot + uid drop).

8. **The sandbox is a fresh implementation in this PR.**
   It was tested once during preflight (probe returned ISOLATION_PASS). It has not been used for a real Resident run. The release task is the first production use, and the independent release reviewer must treat the sandbox as part of what they review.

9. **/proc/1 is visible as a symlink target.**
   Reading `/proc/1/root` is denied (permission error, confirmed), but the symlink itself is visible in `/proc/1/root` listing. This is standard chroot behavior and does not constitute a leak because the Resident cannot traverse it.

10. **B index source policy.**
    The B runtime directory copies the synchronized index from A-002. Index rebuild from World is verified to work (checks.md §12) but the canonical startup uses the copied synchronized index (hash verified) to avoid redundant work. If the index is at all suspect the release task should rebuild before B init.
