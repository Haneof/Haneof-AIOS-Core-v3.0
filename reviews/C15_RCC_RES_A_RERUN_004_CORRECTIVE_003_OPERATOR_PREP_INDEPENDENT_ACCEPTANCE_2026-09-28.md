# C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP — Independent Acceptance

> Review type: **Independent Resident Launch Infrastructure Acceptance** (review-only / evidence-only — DO NOT MERGE)
> Reviewer role: independent acceptance reviewer (not author, Resident, PM, Core engineer or evaluator)
> Date: 2026-09-28
> Candidate: PR #281 — head `10901d467679b70437ae112747eab81f889fd5cb`, parent `abb8b435e5187c7c6c2f4332aea37cd805b4a53c`, tree `db79761216529cf83f217ab00c937bc79806a510`
> Frozen RC software `f20f2edfa7af00d0286493fd15196ca9503bc315` · Core tree `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623` · tests tree `7e33b5ef8432370234965d3ccd61248c703c4019`
> Packet: `RESIDENT_SAFE_LAUNCH_PACKET.json` sha256 `dfab9270f811836f1aad77641a1ec007eb741d1c6ce1acb68f51763eb00bad73`
> Live `origin/main` at review time: `2884aa1b7c9f5e0be46478376e33938ee75d3c73` (fetched fresh at start and re-fetched before publication)
> Evidence directory: `reviews/C15_RCC_RES_A_RERUN_004_CORRECTIVE_003_OPERATOR_PREP_INDEPENDENT_ACCEPTANCE_2026-09-28/` (`probes/`, `raw/`, `env/`)

## 0. Verdict

```
ACCEPTANCE_FAIL / blocker=6
```

PR #281 head was checked at the start and again right before publication. Both times it was `10901d46…` and the PR was OPEN and unmerged, so `REVALIDATION_REQUIRED` does not apply. This verdict covers only that exact head. It does **not** move to any other SHA.

Scope, identity, freezing, the packet head rule, the clean bootstrap build, Gate B, Gate C, Gate D and isolation from the test callback all passed my independent checks. The candidate still fails. My own falsification probes found six binding defects in parts of the launch infrastructure that the author's gates do not exercise. These are recovery binding, operational ledger integrity, enforcement of frozen-RC identity, SQLite and wheel pinning, the clean-room startup boundary in the packet, and completeness of the harness entrypoint. §2 gives each blocker with its reproduction.

Nothing here is Resident `READY`. The packet status stays `PREP_REVIEW_READY`. I did not change it.

## 1. Method and discipline

* I did not rely on the PR description, the author's PASS claims, the author's `/opt/aios` runtime or the author's packet audit. Every conclusion below comes from git objects, a clean runtime I bootstrapped myself, and my own probes.
* **Probes were frozen before any candidate code ran.** Commit `49ca80807b393743d3cd83dffd04b8db1c193be4` holds the probe source, `EXPECTED_OUTCOMES.json` (my predictions), `PROBE_ENUMERATION.txt` (39 tests from collect-only) and `PROBE_SHA256SUMS_REV1`. I pushed it before running the author gates or my probes against the candidate. I never changed an expected outcome after seeing a result.
* **Probe bugs are kept, not hidden.** Two reviewer probes were defective. Both originals and their failing output are preserved unchanged:
  * *Gate D rev1* (`test_ia_gates_bcd_rc.py::test_ia_d_semantic_script_audit`) flagged string **subscript keys** such as `mapping['name']` as hard-coded semantic literals. That is a bug in my heuristic, not in the candidate. The correction is `test_ia_gate_d_rev2.py` (sha256 `2e2caad0…a6c6`). It was frozen in `PROBE_SHA256SUMS_REV2` together with its collect-only output, and committed and pushed in `5e99fbe` **before** it ran. It PASSED (`raw/ia_probe_gate_d_rev2_run1.txt`). I also reviewed the Gate D raw report by hand (§3.9).
  * *BA8 rev1/rev2/rev3*: running `git get-tar-commit-id` inside command substitution with a cwd inside this repository's work tree gave an empty string in this sandbox. Run interactively, or with cwd `/tmp`, it prints the id. This is an environment quirk in my probe, not a candidate defect. `ia_ba8_rev2.sh` (sha `45226c06…`) and `ia_ba8_rev3.sh` (sha `a18aabee…`) were hashed into `PROBE_SHA256SUMS_REV2` before execution. They were **not** committed before execution, which I disclose here. rev3 run from cwd `/tmp` PASSED (`raw/bootstrap_attacks/ba8_rev3_cwd_tmp.txt`). The empty outputs are kept as `ba8_rev2_RED_probe_bug.txt` and `ba8_rev3_cwd_repo_EMPTY_probe_env_quirk.txt`.
* Apart from those two probe bugs, every observed outcome matched the prediction frozen in `EXPECTED_OUTCOMES.json`. That includes every RED that became a blocker.
* **Synthetic and disposable data only.** I did not run a real Resident. I did not initialise real C15 release-state. I did not reveal any cursor, open a sealed fixture or view evaluator semantics. No Phase A was executed. All exchange and World artefacts were created under pytest `tmp_path` or `/tmp/ia`.
* The candidate checkout `/tmp/ia/clone` (detached at `10901d46`) was left unchanged: `git status --porcelain --ignored` returned **0** lines after every run. Mutation attacks used a separate throw-away clone, `/tmp/ia/mut`.

## 2. Blockers

### IA-OP-01 — The runner's recovery binds a durable or outstanding exchange to a different current RuntimeSnapshot, and silently picks the first of several

* **Path:** `…/OPERATOR-PREP/harness/aios_exchange/runner.py` lines 81–99 (`ExternalSessionModelHandler.__call__`: `request_id = durable_unconsumed[0]` / `outstanding[0]`, then `_resolve(request_id, body_digest=None, …)`).
* **Reproduction:** from the review `probes/` directory:
  `PYTHONDONTWRITEBYTECODE=1 IA_RAW_DIR=… <reviewer venv python> -m pytest -p no:cacheprovider -o addopts= --rootdir=. -v test_ia_gate_a_adversarial.py -k "a19b or a20b or a21"`
* **Observed** (`raw/ia_probes_run1.txt`):
  * a19b: the round-1 request was left dispatched after a crash. A new handler instance was then called with a **round-0** snapshot and returned the directive decided for round 1 (`'DECIDED_FOR_ROUND_1'`).
  * a20b: a durable, unconsumed response to the round-1 request was consumed and applied to the round-0 snapshot.
  * a21: two responses were durable and unconsumed. The runner silently picked `'FIRST'`.
  * The positive controls a19 and a20 (same snapshot) pass, so the defect is specifically the lack of any binding between the recovered request and the current snapshot.
* **Expected:** recovery should only resume when the durable request body matches the current `serialize_runtime_snapshot(snapshot)`, i.e. the request sha256 equals the digest of the current body. If they differ, or if more than one request is outstanding or durable-unconsumed, it should stop with a BLOCKED/ambiguity error.
* **Binding reason:** clean-room contract §7 says "Use only contemporaneous durable exchange evidence. If request/response state is ambiguous, stop `BLOCKED`. Never regenerate an uncertain semantic answer merely to continue". The IA brief says ambiguity must fail closed. As built, the runner can feed a semantic decision made for one snapshot into a different model call. That is cross-round contamination of the Resident's decisions, and it happens with no signal.
* **Minimal corrective scope:** `runner.py` only. Compare the digest of the recovered request body with the current snapshot body, fail closed on a mismatch or when more than one candidate exists, and add Gate A tests for the different-snapshot and multiple-outstanding cases.

### IA-OP-02 — The tamper-evident ledger chain is not enforced on the operational path

* **Paths:** `harness/aios_exchange/ledger.py` (`read_records` L62, `latest_event` L99, `append` L112; `verify_chain` L162 exists but is never called on these paths), `harness/aios_exchange/bridge.py` (`consume_response` L152, `recovery_state` L271), `runner.py`.
* **Reproduction:** `… -m pytest … test_ia_gate_a_adversarial.py -k "a09b or a13 or a13b or a14"`
* **Observed:**
  * a13: I mutated an interior ledger record so the hash chain broke. The runner accepted it and returned `'FORGED'`.
  * a13b: `consume_response` on a broken chain did not raise.
  * a14: after an interior record was deleted, the runner served the response again (`'IA_REVIEWER_SYNTHETIC_TERMINAL'`).
  * a09b: a duplicated `request_published` record for the same request id was accepted without raising.
  * Partial or torn tail lines *are* rejected (a06b and a15 PASS).
* **Expected:** every read that drives a decision should require `verify_chain().ok` and a unique event per (request_id, event). This covers recovery_state, consume, append and the runner. Chain breaks and duplicates should stop with BLOCKED.
* **Binding reason:** operator-prep prompt §5 (Gate A: "monotonic/hash-chained ledger", "fail-closed torn writes", "ID/digest mismatch fail-closed"), clean-room §7, and the IA brief's Gate A list ("ledger interior mutation/deletion … ambiguity fail closed"). The chain is only checked by the reporting helper, so it gives no protection when it matters.
* **Minimal corrective scope:** `ledger.py`, `bridge.py` and `runner.py`. Verify the chain and uniqueness before append, recovery and consume, and add the matching Gate A tests. Whole-record tail truncation (a15b, INFO) needs an external head anchor. PM may accept that as a documented limitation (O5).

### IA-OP-03 — The approved verify command does not enforce frozen-RC identity

* **Paths:** `…/OPERATOR-PREP/bootstrap/bootstrap_runtime.sh` L85 (`REPO_ROOT_DEFAULT="$(cd -- "$SCRIPT_DIR/../../../../../.." …)"`) and L381–393 (RC check); `harness/operator_tools/rc_identity.py`; `harness/aios_exchange/verify.py` L126 (`core_content_manifest`); packet `bootstrap_verify_command = "bash <bootstrap_path> --verify"`.
* **Reproduction:** `IA_RAW_DIR=… bash probes/ia_bootstrap_rc_attacks.sh`. Results are in `raw/bootstrap_attacks/SUMMARY.txt`, BA1–BA3.
* **Observed:**
  * **BA1:** the packet's verify command, run as written with no `AIOS_REPO_ROOT`, resolves the repo root to `<repo>/reviews` (`ba1_print_paths.json`). The script logs `WARNING: repo git metadata unavailable; frozen RC identity not machine-verified here`, then `VERIFY OK`, and exits 0. My own clean build hit the same thing (`env/bootstrap_build.log`; my env record `repo_root=/tmp/ia/clone/reviews`, `core_manifest=None`).
  * **BA2:** with no `.git` present, the check is skipped with a WARNING and exit 0 (fail-open).
  * **BA3:** in a throw-away clone I changed one line of working-tree Core (`src/aios_core/runtime/cognitive_runtime.py`, `max_tool_rounds` default 4→9). `bootstrap --verify` reported `frozen RC identity OK` and exited 0. `rc_identity.py` also exited 0. The harness then imported the mutated Core (`ba3_harness_imports_mutated_core.out`: default = 9). The working tree's content manifest became `32a93963…` against the packet's `3ca61cf1…`, and nothing compared the two.
  * The only packaged manifest function, `verify.core_content_manifest`, returns `220718d6…` on the unmodified frozen tree. That does not match the packet pin `3ca61cf1…`, which only the bootstrap's own formula reproduces, and that formula depends on filesystem walk order (O3). So no approved tool can check the packet's `frozen_core_content_manifest_sha256`.
  * With an explicit `AIOS_REPO_ROOT` and an unmodified tree, the result is correct (BA6 PASS).
* **Expected:** the command in the packet, run exactly as written, should machine-verify that the imported Core is byte-identical to frozen Core tree `9adcbe07…`. That means working tree against frozen tree, or the packet's content manifest computed with one canonical formula. It should exit 2 (BLOCKED) whenever it cannot verify.
* **Binding reason:** clean-room §4 says to "mechanically verify the launch packet hashes; run the approved mechanical verification command … If verification fails, stop `BLOCKED`". The IA brief asks for frozen RC identity from the reviewer runtime, not from live main, editable installs or system Python. As shipped, the approved command reports OK in the default case and fails open in both the missing-metadata case and the tampered case.
* **Minimal corrective scope:** `bootstrap_runtime.sh` (fix the default root depth, or require `AIOS_REPO_ROOT`; fail closed; compare `git diff --quiet <frozen tree> -- src/aios_core tests` or the canonical content manifest), `rc_identity.py` (compare the working tree, not just commits), `verify.py` (one canonical sorted manifest formula shared with bootstrap), and a regenerated packet, SHA256SUMS and freeze manifest.

### IA-OP-04 — Bootstrap does not enforce the SQLite pin, and the wheel closure is not pinned in the frozen script

* **Path:** `bootstrap/bootstrap_runtime.sh`:
  * L374: `sq` is read and logged but never compared with `SQLITE_VERSION`.
  * L284–292: `pip download` of `pydantic==` / `pytest==` resolves the transitive dependencies from the index. It falls back to host `python3 -m pip` when the venv pip is unavailable.
  * Wheel sha256s are generated at fetch time (trust on first use) and written to the evidence dir, not pinned in the script.
  * `--verify` does not check the installed wheel set against pins.
* **Reproduction:** BA4 and BA5 in `probes/ia_bootstrap_rc_attacks.sh`.
* **Observed:**
  * **BA4:** with the system `libsqlite3` (3.40.1) preloaded, `--verify` printed `version triple OK: … sqlite=3.40.1` and `VERIFY OK`, exit 0 (`ba4_verify_system_sqlite.out`).
  * **BA5:** the pinned pydantic wheel sha appears 0 times in the frozen bootstrap (`ba5_pydantic_hash_in_bootstrap.txt`).
  * Today my independent fetch produced wheels bit-identical to the author's 10 (`ba5_wheel_hash_compare.txt`: all true), so the build happens to be reproducible **now**. The frozen script does not guarantee it.
* **Expected:** `--verify` should exit 2 unless `sqlite3.sqlite_version == 3.45.1` (the packet pin), and ideally also check OpenSSL `3.0.13`. The full wheel closure (names, versions, sha256) should be pinned in the frozen bootstrap and installed with `--require-hashes`. `--verify` should check the installed distributions. There should be no host-pip fallback.
* **Binding reason:** operator-prep §3 and the IA brief ("SQLite 3.45.1 … no system-Python/sqlite fallback … no unpinned mutable URLs / silently downloading unpinned latest artifact"). The packet declares `sqlite_version: 3.45.1`, but the approved verification accepts a different SQLite.
* **Minimal corrective scope:** `bootstrap_runtime.sh` only (SQLite and OpenSSL comparison, embedded wheel lock with hashes, `--verify` distribution check, no host-pip fallback), plus a regenerated env record, packet and hashes.

### IA-OP-05 — The packet's `allowed_startup_inputs` contradicts the clean-room contract's startup boundary

* **Paths:** `RESIDENT_SAFE_LAUNCH_PACKET.json` (`allowed_startup_inputs`); `harness/operator_tools/build_launch_packet.py` L59–63 (`ALLOWED_STARTUP_INPUTS`); `harness/operator_tools/packet_audit.py`, which does not check this.
* **Reproduction:** `python3 probes/ia_packet_cleanroom_audit.py /tmp/ia/clone`. Output: `raw/ia_packet_cleanroom_audit.json`, where `_red == ["packet_allowed_inputs_include_clean_room_contract"]`.
* **Observed:** the packet lists `[packet, reviews/…/RESIDENT_A_RUN_CONTRACT.md, mechanical status]`. It leaves out `RESIDENT_A_CORRECTIVE_003_CLEAN_ROOM_CONTRACT.md` and adds the older run contract. Clean-room contract §2 says: "Before the first event, you may read only: 1. this clean-room contract; 2. the exact PM-approved Resident-safe launch packet …; 3. the mechanical environment/harness status". The run contract's own §3 forbids "any other Resident run contract", which read literally covers the clean-room contract (O8). Following the packet therefore means ignoring the governing clean-room contract, and following the clean-room contract means the packet's run-contract entry is outside the boundary.
* **Expected:** the startup set in the packet should be exactly the clean-room §2 set. If the run contract is needed (clean-room §5 refers to it), that should come from an explicit PM ruling recorded in the packet, not a silent substitution. The packet audit should check this.
* **Binding reason:** the IA brief says to judge the clean-room boundary (allowed: clean-room contract, packet, mechanical status) and to fail when the packet's steering of the Resident's startup reading is wrong. This is the Resident's first instruction on what it may read.
* **Minimal corrective scope:** `build_launch_packet.py` constant, `packet_audit.py` check, a regenerated packet, SHA256SUMS and freeze manifest. PM should also rule on how the clean-room contract and run contract relate.

### IA-OP-06 — No approved harness entrypoint for due Wake/Review/maintenance model decisions

* **Paths:**
  * Packet `harness_entrypoint = "aios_exchange.runner:run_user_turn"`. That is the only entrypoint.
  * `harness/aios_exchange/runner.py` L150–: `run_user_turn` only calls `HeadlessCore.submit_user_turn`.
  * Frozen Core has `HeadlessCore.process_due_work` (`src/aios_core/headless/core.py` L330). Frozen `turn_runtime.py` calls `CognitiveRuntime.run_turn` from Wake/Review paths (call sites L3633, L4360, L4651; `run_wake` L3750) using the same `model_handler`.
  * Gate C covers user turns only.
* **Reproduction:** `grep -n "process_due_work\|run_wake\|dispatch_next_pending_wake" -r …/OPERATOR-PREP/harness` finds nothing. Compare with the grep of frozen Core above.
* **Observed:** a Resident following RUN_CONTRACT §5 ("run only maintenance, Summary, Wake, derivation, and Review work actually due … when CognitiveRuntime asks for a model decision … personally choose") has no approved, gate-tested entrypoint for due work through the external exchange.
* **Expected:** an approved mechanical entrypoint, such as `run_due_work(world_path, exchange_root, subject_id, now, …)` built on `HeadlessCore.process_due_work` with `ExternalSessionModelHandler`, covered by a synthetic Gate C-style test in which a synthetic Wake requests a model decision through the exchange. It should be listed in the packet.
* **Binding reason:** clean-room §4 says "Use only the exact operator-prepared … harness identified by the accepted launch packet … After cursor 1 is revealed, harness mutation is forbidden". Clean-room §8 requires "all normally due work … complete". As shipped, the Resident would have to skip due work or write its own driver during the run. The first breaks the run contract. The second is harness design by the Resident, which the clean-room contract forbids.
* **Minimal corrective scope:** add one entrypoint in `runner.py`, one synthetic gate test, and packet, manifest and hash regeneration. No Core change.

## 3. Checks that passed (independent evidence)

### 3.1 Scope — PASS
`git diff --name-status $(git merge-base origin/main 10901d46)=0268105 10901d46` (PR commits `abb8b43`, `10901d4`) shows **56 files, all `A`, all under** `reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP/`. The PR changes nothing in `src/`, `tests/`, `.github/`, fixtures, evaluator, release or RC.

### 3.2 Git identity and packet head rule — PASS
* Commit, tree and parent match the brief.
* Packet `operator_prep_exact_head = abb8b435…` equals the parent.
* The packet is **absent** from the parent (`git cat-file` fails) and is added in `10901d46`.
* `src/aios_core` tree `9adcbe07` and `tests` tree `7e33b5ef` are identical in the candidate, in `origin/main` and in `f20f2edf`.

### 3.3 Independent clean bootstrap — build PASS (verify defects are in IA-OP-03/04)
I ran a fresh scratch root, `AIOS_RUNTIME_ROOT=/tmp/ia/rt`, from the candidate clone (`env/bootstrap_build.log`, `env/reviewer_runtime_evidence/*.json`, `env/env_probe.json`):

| item | observed |
|---|---|
| Python | CPython 3.12.14, built from pinned codeload tarball sha `5b8f5847…`; tar commit id `2abcf904…` = `PY_COMMIT_SHA` (BA8 rev3) |
| Pydantic / core | 2.13.5 / 2.46.5 |
| pytest | 8.4.2 |
| SQLite | 3.45.1, bundled `deps/lib` via RUNPATH (no system fallback in default operation) |
| OpenSSL | 3.0.13 (pinned tarball) |
| zlib | 1.3.1 (pinned tarball) |
| OS / kernel / arch | Debian 12 (glibc 2.36) / 6.1.158+ / x86_64 |
| `aios_core.__file__` | `/tmp/ia/clone/src/aios_core/__init__.py` (frozen tree, 68 loaded modules byte-identical, 0 mismatches — `raw/rc_import_identity.json`) |
| wheels | 10, bit-identical to the author's |
| source tree writes | none (BA7: 0 changed or untracked paths) |
| live-main reference | none; all source URLs pinned by sha256 |

The difference from the author's runtime (`/opt/aios` against `/tmp/ia/rt`) is path-only.

### 3.4 Frozen RC identity from the reviewer runtime — PASS (dynamic)
`test_ia_rc_imported_core_is_byte_identical_to_frozen_tree`: every loaded `aios_core` module file equals the blob in frozen tree `9adcbe07`, and the working tree has 0 diff against the frozen RC. The failure is in the *approved tool's* enforcement of this (IA-OP-03), not in the tree actually shipped.

### 3.5 Author gates rerun on the frozen harness — reproduced
`gate_runner.py --repo-root /tmp/ia/clone` → A 19, B 7, C 2, D 5, all PASS. The enumerations are identical to the author's (`raw/author_gates_rerun/gates/`). The clone stayed clean.

### 3.6 Gate A — 20 attack classes (reviewer probes, 28 tests)
PASS (fail closed as required):
* a01 request-id mismatch, a02 request-sha mismatch, a03 response-sha mismatch
* a04/a05 partial request/response, a06 torn temp write, a06b torn ledger tail
* a07/a08 orphan request/response files, a09 duplicate request id, a10 duplicate response publication, a11 overwrite refused
* a12 consumed-before-publish, a15 partial-line tail truncation
* a16 missing `request_published`, a17 missing `response_published`, a18 crash before request publish (RequestPublishError)
* a19/a20 same-snapshot resume / durable-unconsumed consumed exactly once
* **dispatch-boundary invariant:** after `request_published`, null provider/model/usage never produced a `not_submitted` classification

RED: a09b, a13, a13b, a14 → IA-OP-02; a19b, a20b, a21 → IA-OP-01. INFO: a15b (whole-record tail truncation not detectable; O5).

### 3.7 Gate B — PASS
* `CapabilityResult` fields are exactly `name, ok, data, error_code, error_message, call_id` (B0).
* B1 (empty), B2 (success with data), B3 (failure with error fields) and B4 (multiple, order preserved) all serialise faithfully.
* B5 AST scan: no `.arguments/.result/.error/.duration_seconds` access on `CapabilityResult` in the harness (`raw/gate_b_attribute_audit.json`). `CapabilityCall.arguments` usage is legal.

### 3.8 Gate C — PASS (non-vacuous, independent)
The raw artefacts are in `raw/gate_c_success/` and `raw/gate_c_failure/`.
* Round 0 has an empty capability history. The synthetic responder asks for a legal capability, which frozen Core executes.
* Round 1 (`round_index=1`) carries a real `CapabilityResult`:
  * success: `search_world` returned `ok=true` with data (`call_id ia-call-0001`);
  * failure: `CAPABILITY_NOT_FOUND`, `ok=false`, then silence terminal.
* The ledger for each run is `request_published → response_published → response_consumed ×2`, and the chain is ok.
* The responder is test-only (`harness/tests/synthetic/`), is never imported by `aios_exchange`, and has no enable switch. The response mode is `EXTERNAL_CURRENT_RESIDENT_SESSION`.
* The responder contains no real fixture content.

### 3.9 Gate D — PASS (rev2 + manual review)
I reviewed `raw/gate_d_independent_audit.json` and `_rev2.json` by hand.
* Every branch in `aios_exchange/*` is mechanical: sequence, digest, path, schema, timeouts and error codes.
* The only reads of semantic fields are the `schema.py` L211–215 serialisation.
* The only literal construction is `schema.py` L126, `CapabilityResult(name='contract-probe', …)`, a local contract probe that is never serialised to the exchange.
* No keyword, cursor or event-id routing, no hard-coded claims or replies, no default silence, no hidden callback and no expected answers.
* `runner.py` is a mechanical boundary, and `ExternalSessionModelHandler` is only an exchange adapter.

### 3.10 Packet values, contamination and freezing — PASS (except IA-OP-05)
* Status `PREP_REVIEW_READY` (not `READY_FOR_RESIDENT`), cursor 1..13, mode `EXTERNAL_CURRENT_RESIDENT_SESSION`.
* Pins 3.12.14/2.13.5/8.4.2/3.45.1.
* Recomputed and matching: bootstrap `b4960802…`, clean-room contract `1da3ed66…`, run contract `9b8a6cc5…`, env record `f771914b…`, harness manifest `a26f7616…` (26 files), core manifest `3ca61cf1…` (77 files, bootstrap formula), packet `dfab9270…`.
* `sha256sum -c evidence/SHA256SUMS` gives 55/55 OK. It excludes itself and does not claim to cover itself (acceptable).
* The FREEZE_MANIFEST is consistent.
* Contamination scan of the packet values and of the Resident-readable startup artefacts: marker hits are all prohibition or protocol vocabulary ("Never reveal cursor 14", category names like `evaluator_expected_semantics`). There is no fixture content, cursor payload, prior claim, release state or governance adjudication. The clean-room contract itself leaks no prior semantics.
* No `.sqlite`/`.db` World or release-state files are in the package. There is no Resident A Corrective-003 run directory in the candidate or on main, so I found no evidence of an accidental real run or cursor reveal.
* **Timeline:** the gates ran 18:37:03–18:37:09Z. The parent commit was committed at 18:37:13Z, and the head commit (packet only) does not touch the harness. So the committed harness post-dates the gate evidence by about 4 s. My independent rerun of the author gates on the committed harness reproduced identical enumerations and results, so the gate evidence corresponds behaviourally to the frozen harness. Gate evidence and harness are linked only by timestamps (O2).

## 4. Non-blocking observations
* **O1:** `gate_[a-d]_result.json` report `test_count: 0` and `test_ids: []` (gate_runner parser bug). The `*_tests.txt` enumerations are correct.
* **O2:** gate results do not embed the harness manifest sha they ran against, so the link between gates and harness is by timestamps only.
* **O3:** the bootstrap core-manifest walk is not sorted (`os.walk` order). It reproduced `3ca61cf1` here, but that is not guaranteed across filesystems. This is related to IA-OP-03.
* **O4:** `canonical.json_default` falls back to `str(value)`, which is silently lossy for unknown types.
* **O5:** truncating whole records from the ledger tail cannot be detected without an external anchor for the head hash.
* **O6:** a crash between writing the request file and appending to the ledger leaves the exchange permanently BLOCKED on restart (`RequestPublishError`). That is fail-closed, but there is no documented operator recovery.
* **O7:** the synthetic responder labels its output with the same `authored_by` string as a real session. Isolation holds, but the label is not an authenticator.
* **O8:** RUN_CONTRACT §3 "any other Resident run contract" conflicts literally with the clean-room contract. This needs a PM ruling (see IA-OP-05).
* **O9:** there is no single approved command for clean-room §4's "confirm real-run semantic callback/router is disabled". It is covered only through the Gate D tests.
* **O10:** the author's packet audit `task_id` omits `-OPERATOR-PREP`, and its scan scope is narrow.
* **O11:** the bootstrap does not verify `PY_TAG_OBJECT_SHA`. `PY_COMMIT_SHA` matches the tarball (BA8 rev3 PASS), and the tarball is sha-pinned.

## 5. Evidence index
* Probes rev1 (frozen in `49ca808`), listed in `probes/PROBE_SHA256SUMS_REV1`:
  * `00_bootstrap_reproduction_plan.md` `a48072e0…4017`
  * `ia_common.py` `d20ace45…69d6`
  * `test_ia_gate_a_adversarial.py` `6226ba3e…15e3`
  * `test_ia_gates_bcd_rc.py` `262ec739…d949`
  * `ia_packet_cleanroom_audit.py` `b3c90ac3…f572`
  * `ia_bootstrap_rc_attacks.sh` `680d0c49…15b2`
  * `EXPECTED_OUTCOMES.json` `c5f98318…2c18`
  * `PROBE_ENUMERATION.txt` `e0ca70b8…b3c7`
* Probe rev2, listed in `probes/PROBE_SHA256SUMS_REV2`:
  * `test_ia_gate_d_rev2.py` `2e2caad0846eb21780d9269a77630dba9418634bf78b955fc420ef5b7071a6c6` (frozen in `5e99fbe` before execution)
  * `ia_ba8_rev2.sh` `45226c06…3d3f`
  * `ia_ba8_rev3.sh` `a18aabee…6bb0`
* Raw outputs:
  * `raw/ia_probes_run1.txt` — 31 passed, 8 failed
  * `raw/ia_probe_gate_d_rev2_run1.txt` — 1 passed
  * `raw/author_gates_rerun/`
  * `raw/gate_c_success/`, `raw/gate_c_failure/`
  * `raw/gate_b_attribute_audit.json`, `raw/gate_d_independent_audit*.json`, `raw/rc_import_identity.json`
  * `raw/ia_packet_cleanroom_audit.json`
  * `raw/bootstrap_attacks/`, with `SUMMARY.txt` holding the BA1–BA8 rev1 lines
* Environment: `env/bootstrap_build.log`, `env/env_probe.json`, `env/reviewer_runtime_evidence/`.
* Full per-file hashes for this review: `REVIEW_SHA256SUMS` in the evidence directory. It excludes itself and does not claim to cover itself.

## 6. Actions not taken
I did not modify, fix, approve or merge #281. The packet status is unchanged. I did not touch #263 or #265. I did not start persistence Corrective-003, Resident B/C, evaluator work or C15 close. I did not create a tag or release. I did not run a real Resident, reveal a cursor, initialise real release-state, open a sealed fixture or view evaluator semantics.
