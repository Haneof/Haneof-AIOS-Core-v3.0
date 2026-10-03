# CARRY_FORWARD_MANIFEST — Window 22-RERUN-001

Generated **before** any Corrective-003 semantic modification, as required by contract §11.

## 1. Bases

| item | value |
|---|---|
| fresh construction base (branch tip at start) | `1541b1ec1a8b40bdc67debd52af986c2869ee00e` (live `origin/main`, "Merge PR #317 governance: reopen Corrective-003 as Window 22 rerun") |
| carry-forward byte source | `fec30bd1495017bf13f08b0ef5b1e241dfb0e247` (frozen failed Corrective-002 candidate = PR #310 head) |
| source's code-bearing parent | `7db79da54b26266c5ec519f3e70dd25dff4a95fb` ("fix(core): close Window 17 trust-mint, downgrade/migration and RSA blockers (Corrective-002)") |
| `git merge-base(base, source)` | `ca47087fb68c90d6ac380c11143a0e36e80fc04a` |
| branch base | **fresh live main**, NOT `fec30bd` (contract §11 honoured) |

`fec30bd` is a docs-only commit: for all 21 carried paths its blob equals `7db79da`'s blob, so the
carried engineering bytes are exactly the CI-validated Corrective-002 code head.

## 2. Losslessness proof

`git diff --name-status ca47087 1541b1e -- src/aios_core/runtime tests .github/workflows` → **empty**.
Main changed nothing under any carried directory since the merge base, therefore overwriting those
paths with the `fec30bd` bytes cannot destroy any main-side work.

## 3. Carried paths (21) — byte-exact verification

`src_blob` = blob id at `fec30bd`; `dst_blob` = `git hash-object` of the materialized file in the
working tree; `src_sha256`/`dst_sha256` = SHA-256 of the same two byte streams.
`match` requires **both** blob id equality **and** SHA-256 equality.

| path | src_blob | dst_blob | src_sha256 | dst_sha256 | bytes | match |
|---|---|---|---|---|---|---|
| `.github/workflows/core-background-late-trusted-return-001.yml` | `080e9d7c083dd6ddcdc3b365afdd6f34b9ee3cf4` | `080e9d7c083dd6ddcdc3b365afdd6f34b9ee3cf4` | `b9b72ab596785698e2f86b7221a6262d9a5d43397dbb339538856b48fa520852` | `b9b72ab596785698e2f86b7221a6262d9a5d43397dbb339538856b48fa520852` | 15108 | **BYTE_EXACT** |
| `src/aios_core/runtime/__init__.py` | `f46ef0326793f1f462d174cfc17994d388e2ea50` | `f46ef0326793f1f462d174cfc17994d388e2ea50` | `81c94113ce0811a53029bf5116d09d7520161d3778e572dfecbf1bbe035d046a` | `81c94113ce0811a53029bf5116d09d7520161d3778e572dfecbf1bbe035d046a` | 1727 | **BYTE_EXACT** |
| `src/aios_core/runtime/background_attempt.py` | `9c08cce87cf5d1e8e2c98324fec4a73051900055` | `9c08cce87cf5d1e8e2c98324fec4a73051900055` | `d536213533f929240689669694527c1b78fd58bd2316e36af982796d41a62d73` | `d536213533f929240689669694527c1b78fd58bd2316e36af982796d41a62d73` | 129752 | **BYTE_EXACT** |
| `src/aios_core/runtime/cognitive_runtime.py` | `2f153aa82de7f3de6a9f4604c756f21b0221c838` | `2f153aa82de7f3de6a9f4604c756f21b0221c838` | `524e27a9a659f8396de683d22cfd371b66e046f11b1b774ff70b001c948c266a` | `524e27a9a659f8396de683d22cfd371b66e046f11b1b774ff70b001c948c266a` | 22621 | **BYTE_EXACT** |
| `src/aios_core/runtime/late_return.py` | `835045418434d26514d8086439942c85598219a7` | `835045418434d26514d8086439942c85598219a7` | `f1302284400854afc06eab9f2baa42d676b87462d04eb63b1e9cfe51c20d9cb9` | `f1302284400854afc06eab9f2baa42d676b87462d04eb63b1e9cfe51c20d9cb9` | 13945 | **BYTE_EXACT** |
| `src/aios_core/runtime/live_return.py` | `191f30fb3e90683e3a3d122750e8a613673af731` | `191f30fb3e90683e3a3d122750e8a613673af731` | `35c3cbeced5706d03d05359166ea8ea5d55150e9a2632b050b491d425bac30e0` | `35c3cbeced5706d03d05359166ea8ea5d55150e9a2632b050b491d425bac30e0` | 10800 | **BYTE_EXACT** |
| `src/aios_core/runtime/turn_runtime.py` | `0f51d75b62040f4c06b02db71a566ac3131adf27` | `0f51d75b62040f4c06b02db71a566ac3131adf27` | `5fd0284c9f43e7066d5175e9af3eee57e972fd09f4baa1bd2dacfe4d143c041e` | `5fd0284c9f43e7066d5175e9af3eee57e972fd09f4baa1bd2dacfe4d143c041e` | 191313 | **BYTE_EXACT** |
| `tests/integration/test_core_background_late_trusted_return_consumption_001.py` | `df63fc2030c93475d9641f06d6287347138c91ec` | `df63fc2030c93475d9641f06d6287347138c91ec` | `0ba9d8ae4062041b16f43715a3a67dca496cf2eae18e6ae395ad4d7e08c23d84` | `0ba9d8ae4062041b16f43715a3a67dca496cf2eae18e6ae395ad4d7e08c23d84` | 2137 | **BYTE_EXACT** |
| `tests/integration/test_core_background_late_trusted_return_corrective_001.py` | `ed7813d3306b53b954ead4175f0743877d269823` | `ed7813d3306b53b954ead4175f0743877d269823` | `247162cbec1085e178e3268c5dc44666d78dd1f968c6b79b1cd09af0c92a4d07` | `247162cbec1085e178e3268c5dc44666d78dd1f968c6b79b1cd09af0c92a4d07` | 12708 | **BYTE_EXACT** |
| `tests/integration/test_core_background_late_trusted_return_corrective_002.py` | `f4b2ce36d039ba54013dc0961f6413258f8eb8a6` | `f4b2ce36d039ba54013dc0961f6413258f8eb8a6` | `be845c4c1d8e9bba0363240f5c9f2585ea3d8587d843f4662697fb6e64f9ee7f` | `be845c4c1d8e9bba0363240f5c9f2585ea3d8587d843f4662697fb6e64f9ee7f` | 41218 | **BYTE_EXACT** |
| `tests/integration/test_core_background_late_trusted_return_secret_upgrade_001.py` | `c5369fd45f0091a179d491de8aba91964d73edfe` | `c5369fd45f0091a179d491de8aba91964d73edfe` | `f644db8d85e5599fa51e22552d59a96c841156d8d4ff5e5b71db7afbe027f880` | `f644db8d85e5599fa51e22552d59a96c841156d8d4ff5e5b71db7afbe027f880` | 2943 | **BYTE_EXACT** |
| `tests/integration/test_core_background_late_trusted_return_sigkill_001.py` | `92a7182242b64364bd4633c68589b8a8b5045fc3` | `92a7182242b64364bd4633c68589b8a8b5045fc3` | `77bfa14507fee5d0fb7de3b6cd834b4d17dcae5ed3741325475874cc461b8ec8` | `77bfa14507fee5d0fb7de3b6cd834b4d17dcae5ed3741325475874cc461b8ec8` | 6097 | **BYTE_EXACT** |
| `tests/integration/test_core_background_response_recovery_001.py` | `7aeb551e5cad12f02943404ec5f9d259f6f80292` | `7aeb551e5cad12f02943404ec5f9d259f6f80292` | `8ff7730767f033863c1bd70719cf2369b0bf34f0b0a35d17fc6499bf73a1293f` | `8ff7730767f033863c1bd70719cf2369b0bf34f0b0a35d17fc6499bf73a1293f` | 52762 | **BYTE_EXACT** |
| `tests/integration/test_core_background_response_recovery_001_corrective_001.py` | `a3450fb9df07491e59e172dbb6914bd3fdfc0ae7` | `a3450fb9df07491e59e172dbb6914bd3fdfc0ae7` | `4108a1d8b58eb42b33b9ae95960b887e17f9573a54dfb80ee7fe7737ba326f3a` | `4108a1d8b58eb42b33b9ae95960b887e17f9573a54dfb80ee7fe7737ba326f3a` | 35331 | **BYTE_EXACT** |
| `tests/integration/test_core_background_trusted_return_adversarial_001.py` | `5219f1059292919301d0801923d64135dde15ad6` | `5219f1059292919301d0801923d64135dde15ad6` | `2260f50cccaf64661e0bc516d93e4be674ba5f2f0cfdbb68be99b3a43f4eccb6` | `2260f50cccaf64661e0bc516d93e4be674ba5f2f0cfdbb68be99b3a43f4eccb6` | 13780 | **BYTE_EXACT** |
| `tests/integration/test_core_gap_fix_002_background_attempts.py` | `29024d9ee26a0d4b6c829ad5c3120da39fe03dde` | `29024d9ee26a0d4b6c829ad5c3120da39fe03dde` | `50950ff76fadfb44997e39feaaa378bfb6514d5a56c2860b818abb0cbffd08c6` | `50950ff76fadfb44997e39feaaa378bfb6514d5a56c2860b818abb0cbffd08c6` | 21361 | **BYTE_EXACT** |
| `tests/runtime/test_background_late_return_route_b.py` | `56539fb0c5df7ef1dad2758bde708592ecbd0e92` | `56539fb0c5df7ef1dad2758bde708592ecbd0e92` | `f0375eaa55580ae577c8f32d384180cff6302ed4c081824d6f6f51de1912dac3` | `f0375eaa55580ae577c8f32d384180cff6302ed4c081824d6f6f51de1912dac3` | 4511 | **BYTE_EXACT** |
| `tests/runtime/test_background_model_attempt.py` | `2c6aaca28a5f5ffa45a6d45383b9beded02b5963` | `2c6aaca28a5f5ffa45a6d45383b9beded02b5963` | `ad140c999943238acaba515de45aeecff3c9d4f75ad3680223a7761a698b73d3` | `ad140c999943238acaba515de45aeecff3c9d4f75ad3680223a7761a698b73d3` | 11625 | **BYTE_EXACT** |
| `tests/runtime/test_cognitive_runtime_trusted_return.py` | `a657a2f643b5ed1209ab8a2a33b9882175d1583d` | `a657a2f643b5ed1209ab8a2a33b9882175d1583d` | `1ed71982dc273ec2e39b7f76e5ecb901b4919d964c4b5db081b2d622dde09eb1` | `1ed71982dc273ec2e39b7f76e5ecb901b4919d964c4b5db081b2d622dde09eb1` | 3391 | **BYTE_EXACT** |
| `tests/runtime/test_late_return_canonical_encoding_002.py` | `7312de533532ac138dff6de52eb29420bf5830b6` | `7312de533532ac138dff6de52eb29420bf5830b6` | `15658240211ccab3431ffc7dc8ae0f2df4ec8a5866a1b333a750b60eb6eb681f` | `15658240211ccab3431ffc7dc8ae0f2df4ec8a5866a1b333a750b60eb6eb681f` | 11128 | **BYTE_EXACT** |
| `tests/runtime/test_turn_execution_recovery.py` | `58f898779bb5b7ed04b6e0a26f4e4c10378454a1` | `58f898779bb5b7ed04b6e0a26f4e4c10378454a1` | `0cfb1c6f5051e76e00de77a070365e869ceac8337b4e5ecd81b91dc91dd0d4d7` | `0cfb1c6f5051e76e00de77a070365e869ceac8337b4e5ecd81b91dc91dd0d4d7` | 19258 | **BYTE_EXACT** |

Aggregate verification: `ALL_MATCH=YES` — 21/21 paths `BYTE_EXACT`, 0 mismatches.

## 4. Explicitly EXCLUDED paths

These paths differ between fresh main and `fec30bd` but are **forbidden** carry-forward material
(contract §11) and were therefore **not** carried. Main's versions are preserved untouched.

| excluded path | reason |
|---|---|
| `AIOS_v3.0_CURRENT_CHECKPOINT.md` | checkpoint material — forbidden carry-forward |
| `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md` | task board — forbidden carry-forward |
| `governance/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_002_ACCEPTANCE_FAILURE_ADJUDICATION_2026-10-03.md` | governance adjudication (deleted at source) — must not be deleted from main |
| `governance/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_003_PUBLICATION_RECOVERY_RELEASE_2026-10-03.md` | governance release (deleted at source) — must not be deleted from main |
| `governance/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_003_SCOPE_PUBLICATION_CLARIFICATION_2026-10-03.md` | governance clarification (deleted at source) — must not be deleted from main |
| `governance/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_003_WINDOW22_RERUN_RELEASE_2026-10-03.md` | **this window's own release authority** (deleted at source) — must not be deleted from main |
| `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_002/**` (16 files) | old author evidence — forbidden carry-forward |

The 16 excluded old-author-evidence files are:
`BASELINE_RED.md`, `BASELINE_RED_ON_CARRYFORWARD_RAW.txt`, `BASELINE_RED_RAW.txt`,
`CORRECTIVE_002_ATTACK_MATRIX.md`, `DESIGN_SECURITY_MODEL.md`, `FAILED_CANDIDATE_IDENTITY.md`,
`FINAL_HANDOFF.md`, `FORMAL_CI_RESULTS.md`, `GREEN_FROZEN_PROBE_RAW.txt`, `GREEN_RESULTS.md`,
`LEGACY_MIGRATION_AUDIT.md`, `NOT_SUBMITTED_REGRESSION.md`, `PROBE_FREEZE_MANIFEST.md`,
`RSA_VERIFIER_VALIDATION.md`, `SCOPE_MANIFEST.md`, `START_GROUND_TRUTH.md`,
`TRUST_MINT_PATH_AUDIT.md`, `WINDOW17_REVIEW_IDENTITY.md`.

Also excluded by category (never carried): Window 19 evidence docs, Window 20 reviewer evidence,
any historical review branch content, PR metadata, C15 material
(`tools/c15_persistence/**`, `tests/c15_persistence/**`, `tools/c15_preflight/**`), Resident
evidence, release artifacts, root `.gitignore`.

## 5. Post-carry-forward working-tree state

- 11 carried paths are modifications of existing main files (`M`)
- 10 carried paths are new files (`??` → added)
- 0 governance/checkpoint/review files touched by the carry-forward
- 0 build artifacts (`__pycache__`, `.egg-info`, `.pytest_cache`, `build/`, `dist/`) present

The commit that freezes this state is titled `BYTE_EXACT_CARRY_FORWARD_BASE` and is pushed to the
remote engineering branch **before** any Corrective-003 semantic modification, so the engineering
is durable from the very first step (contract §11 / §22).

## 6. Baseline expectation after carry-forward

The carry-forward must **not** silently fix or alter the frozen Window 20 failure. Contract §14
therefore requires frozen Suite A to still report `probes=4 failures=4` on the
`BYTE_EXACT_CARRY_FORWARD_BASE` commit. That run is recorded in `BASELINE_RED.md`.
