# Window 54 — Fresh Independent Acceptance (REVIEW ONLY)

FORMAL_TASK: `C15-RCC-RES-A-RERUN-005-OPERATOR-HARNESS-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE`

Verdict: **ACCEPTANCE_FAIL / 3 binding security & durability blockers**. No authorization to merge PR #361 or resume Resident A. This is a reviewer verdict for PM adjudication, not PM integration.

## Exact candidate freeze

- Repository: `Haneof/Haneof-AIOS-Core-v3.0`
- PR: [#361](https://github.com/Haneof/Haneof-AIOS-Core-v3.0/pull/361) **OPEN / UNMERGED** at review; reviewer did not modify it
- Frozen HEAD: `67da1125c4902380dafde98a0ccf01c42e590864`
- Exact tree: `5fe6d60cbea2b0725e7f2f7e37ef85611220b9c5`
- Parent / fresh main: `271fa28d695efaeb1c888d93024eeddac9c8aa9f`
- Changed file count: **48**, all `reviews/**` (GitHub API)
- Accepted integration baseline: `703a8967878d8eaee70a8a8fce9df068204f5f76`
- `src/aios_core` subtree: `16f1487e291b009c55bee402abfd79fdacbae960`
- `tools/c15_persistence` subtree: `b8a62370e6ffe80730b2ef4c17d625fab50446d4`
- Independent SHA256 of exact GitHub blob: Harness IDENTITY.json `63f8e692d5f5121c4afb92d0f25e747b08dca6b764c6d8ef8a04e13654a4a04c`; tar.gz `689bdc3ea1fe4c7192006f89869fe2280bf92887af78e0ba78e151e175f32a4d` (36,999 bytes); safe packet `a87fc5cd926f9695cac359a77748903f5bbc48ad484ce630a3d4ff421d1c70c6`; RED.json `9ea5bc3e4a263f195664364eb5f62defb38ed978ccfdd8fb2f6d2cdaadd14c53`.

GitHub REST Git tree was independently examined to confirm the two protected software subtrees at the candidate's exact commit. None of the GitHub source claims are inferred from the author report.

## IA54-BLK-001 — Importable native module outside frozen identity

**Severity:** Binding. **Gates:** A01/A03/A04. **Exact source:** `reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-005/harness/r005/checks.py`, SHA256 `f5f93a8cf88a3b6b09b38007a231d5d4ba70e521ff2b91aaa7ca1edee9c1cef4`.

`verify()` inventories only `*.py` in the Core, C15, and Harness trees and hashes those paths. `loaded_modules()` checks imported module **location** under the approved source path, not signed/manifested bytes or module format. A native extension named `src/aios_core/headless/core.cpython-312-x86_64-linux-gnu.so` can shadow the authorized Python module without changing any approved `.py` byte. The checked Python interpreter prefers extension modules over `.py` modules. The frozen reviewer attack creates the extension in a synthetic source tree and confirms (1) baseline verification succeeds, (2) after injection verification still succeeds, (3) unauthorized native module is actually imported and executed, (4) `loaded_modules` returns PASS. This is an exact-source `checks.py` logic probe, not a full production Core checkout run.

**Reproduce:** approved Python 3.12.14 plus GCC; run `ia54_a01_native_shadow.py`. Its prewritten plan and SHA are frozen. Raw failing test log and JUnit record this exploit success as a **defense failure**. Minimal fix boundary: close all executable/importable content types (including native extension and package-path overlays), fail closed on unexpected files/symlinks, and bind every executable module to exact bytes before and during execution.

## IA54-BLK-002 — Forged caller_pid grants unauthorized Publisher registration

**Severity:** Binding. **Gate:** A05 (with signing-context scope). **Exact source:** `.../harness/r005/publisher_service.py`, SHA256 `37506ee7113acc30c02d3dfced92e92d8e73f1e77eca8c081b0af072534f3ac3`.

The file-IPC service executes `peer=int(command['caller_pid']); os.kill(peer,0)` then trusts `peer==runner_pid` when registering `{request_id, request_sha256, context}`. `caller_pid` is an attacker-controlled JSON field, not a kernel-authenticated sender credential. A disposable synthetic process, while the separately started `sleep` Runner PID remained live and performed no registration, supplied its PID in a forged JSON command. The exact Publisher script returned `{"ok":true,"result":{"registered":"req-synthetic-a05", ...}}`. The forged context included an arbitrary attacker-selected attempt/scope. This establishes **unauthorized registration and context poisoning**, not proof of unauthenticated `publish`, uncredentialed RSA signing, or a successful real Core semantic application. The latter paths were not independently completed.

**Reproduce:** approved Python 3.12.14; run frozen `ia54_a05_forged_pid_v3.py`, which imports the exact byte-verified Publisher script with synthetic Core/exchange stubs; raw probe output and regression JUnit are included. Minimal fix boundary: replace asserted caller PID with OS peer-credential authentication or another unforgeable, least-privilege Runner registration capability, and bind signer context to actually issued Core attempt metadata.

## IA54-BLK-003 — Local completion marker before final remote CAS barrier

**Severity:** Binding pending PM adjudication; **Gates:** A10/A11. **Exact source order:** `.../harness/r005/safe_runner.py:267-272`: `atomic_write_bytes(marker, {state: completed, result})` **line 270**, `barrier(..., 'operation-completed')` **line 271**. Recovery path at `:202` verifies remote authority, then `:210-214` returns any local `completed` result without requiring its presence in a committed remote generation. Accepted C15's `tools/c15_persistence/remote_backend.py:131-170` compares expected remote head and immutable `GenerationStore.HEAD` bytes, but does not check the *live mailbox operation marker* against that remote commit. `RunBackend.open` verifies prior immutable generations (`backend.py:340-395`) but does not prove unsealed live `operation.json` is remote committed.

**Crash schedule:** (i) previous remote generation HEAD matches local; (ii) apply completes; (iii) local completed marker is successfully written/fsynced; (iv) process SIGKILL **before** final completion barrier; (v) remote and local generation heads still match the old authority; (vi) on restart, local marker's `completed` fast path returns result without proving its final CAS/remote durability. Exception rollback at `safe_runner.py:273-278` is not executed for SIGKILL. The frozen `ia54_a10_completion_gap.py` models this exact window in disposable state and records `COMPLETION_AUTHORITY_GAP_WITNESS`. **Limitation:** the A10 witness is an independent state-machine reproduction grounded in exact-source ordering, not a full Core/C15 integration execution. It is therefore distinguishable from the direct exact-source A01/A05 attacks. Minimal fix boundary: do not expose a replayable `completed` state until the corresponding authoritative remote commit is durably verified; bind replay to exact remote operation-completion commit/proof or leave uncertain state blocked.

## Reviewer-owned execution

- Approved artifact ZIP SHA256: `cc6b72631e000fa161f027c3daf946805d41022a25725ead040d26c5509d155a`; runtime tar SHA256: `ecfe4b4b6e9dee1a08342974e816f739dcd77fcd3f25f3ad7626cc7102e5673e`. Approved Python reports CPython `3.12.14`; Pydantic `2.13.5`; pytest `8.4.2`; SQLite `3.45.1`; OpenSSL `3.0.13`.
- Reviewer-owned actual pytest rerun: **2 tests, 2 failed as expected because defenses were breached**, exit code **1**; fresh JUnit `IA54_RED_FRESH.xml`, file SHA256 `7f4cae6da2ae9c518791ef26ea48487f49566755ce4c45c0c456b554b0bf9452`; raw log SHA256 `339d459be0badf77b3849d1c39f839d75a37e5f9269d2811b42d48655a7092da`.
- A10 model witness actual exit **0**, but successful attack witness **does not mean security PASS**; frozen source SHA256 `675bc33655cff6ff9bd337b5501581e51b5455d0bbae933b8f3fe37883a509ae` and plan SHA256 `ab742caf71791d3131dc9903816168212f979548f7f0778514111f50295c3519`.
- `git fetch --all --prune` attempted in fresh reviewer checkout and failed **128** (`Could not resolve host: github.com`). GitHub connector was used for separate authenticated exact-commit, subtree, source and SHA verification.
- **Author's 38 tests were NOT rerun.** Attempted pytest collection from the unmaterialized fresh checkout: exit **4**, no tests collected; not a candidate test failure. Independent full artifact extraction and complete USER/Publisher/Core/C15 semantic path also **NOT verified**; do not substitute author results or CI SUCCESS for these requirements.
- RED-first: Window53's `RED.json` SHA was independently verified. Reviewer authored and hashed attack preconditions and source before executing the final frozen probes; prior exploratory corrections remain labeled, not silently replaced.

## Attack matrix and stop boundary

- A01/A03: FAIL, native executable shadow. A02: Git blob tar SHA PASS, member safety/full materialization NOT VERIFIED. A04: core source scan reviewed, cannot establish full no-scripted-cognition execution. A05: FAIL, forged registration. A06/A07/A08/A09: not fully independently executed; no false PASS. A10/A11: completion pre-barrier crash gap witnessed via source + synthetic schedule; remote C15 CAS full test not rerun. A12/A13: full independently materialized Core/C15 execution NOT VERIFIED. A14: safe packet hash verified, semantic leakage not comprehensively retested. A15: **Reviewer never ran actual Resident A, never accessed real Window51 state or sealed fixture**; no real cursor/event/ACK operations triggered by review.
- Protected PR #361 unchanged; all reviewer work belongs only to a new `reviews/C15_RERUN005_OPERATOR_HARNESS_WINDOW54` evidence path on a **REVIEW_ONLY** branch. No candidate repair, merge, PM action, evaluator, or Resident execution.

**Reviewer verdict: `WINDOW_54 = ACCEPTANCE_FAIL / BLOCKER_COUNT = 3 / DO NOT MERGE`.** Open claims about untested criteria remain **NOT_VERIFIED**, not PASS. PM should treat all three as release/launch blockers while commissioning separate corrective engineering, with a fresh IA after repair.
