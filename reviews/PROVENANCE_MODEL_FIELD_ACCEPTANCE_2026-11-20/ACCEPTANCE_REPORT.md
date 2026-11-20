# Provenance Model-Field Fix — Independent Acceptance Report

- **Task:** `PM-PROVENANCE-MODEL-FIELD-ACCEPTANCE-001`
- **Acceptance agent:** independent acceptance window (fresh window; no prior involvement with the provenance fix implementation, PM adjudication, the two reviews RV20261120-001 / RV20261120-002, Window80 wiring acceptance, G-1/G-2 implementation or acceptance, Operator, Core fixes, or merges)
- **Acceptance object:** commit `cf7d766` (`fix(runtime): record server-returned model in provenance, not the request`, `Haneof/Haneof-AIOS-Core-v3.0`)
- **Acceptance execution tree:** local `3b42a60` (2026-11-20 PM adjudication governance commit, not pushed; remote main still at `8317769`)
- **Date:** 2026-11-20 (UTC)
- **Overall exit:** **ACCEPTED** (all 5 items PASS; no FAIL; 3 non-blocking observations, see §4)

## 0. Independence declaration and baseline confirmation

This acceptance agent has no prior involvement with the fix, its implementation, or any earlier review/acceptance in this project. This acceptance only read the accepted commit and the code; it modified no code and no existing file, submitted nothing, pushed nothing, opened no PR, touched no `reviews/` frozen evidence or review outputs, touched no credentials, called no external model, started no Resident, and ran no live-provider test (they skip by default).

Baseline confirmation:

- `git log`: local HEAD `3b42a60`, beneath it `cf7d766` (fix commit), parent `0ab39b6` (PM adjudication governance commit).
- `git show --stat cf7d766`: 3 files, 252 insertions, 5 deletions — `src/aios_core/runtime/grok_provider.py` (+44/−5), `tests/runtime/test_provenance_model_field.py` (new, 207 lines), `tests/runtime/test_live_multimodel_habitation.py` (+6/−1, test_05 only).
- Trailer: `Authorized-Task: PM-PROVENANCE-MODEL-FIELD-001`, matching the task registered in `governance/baseline.json`.
- `git diff 8317769..cf7d766 --stat`: 13 files, of which 7 are PM adjudication governance/docs files and 3 are the G-1/G-2 fix files — the provenance fix itself is exactly the 3 files above, with no incidental changes.
- Working tree was clean apart from the pre-existing untracked `reviews/` review/acceptance directories. The unpatched control tree was a temporary `git worktree` of `cf7d766^`, removed after use (`git worktree list` shows only main at `3b42a60`).

## 1. Itemized conclusions

| # | Acceptance item | Verdict | One-line evidence |
|---|---|---|---|
| 1 | Server model field attribution, both streaming paths | **PASS** | Independent repro (own raw-socket server, synthetic names): request `model-alpha-req` / server `model-beta-srv` → provenance `model-beta-srv`; tools path request `model-delta-req` / server `model-epsilon-srv` → provenance `model-epsilon-srv`; request_id is the server chunk id in both |
| 2 | UNKNOWN case (omitted / blank model field) | **PASS** | No model field → provenance `UNKNOWN`, usage `UNKNOWN`, call completes; blank `"   "` → `UNKNOWN`; first-non-blank-wins and whitespace-strip also verified |
| 3 | Regression tests: 6 shipped tests pass and are genuine | **PASS** | Fixed tree 6/6 pass (3.82s); unpatched worktree 6/6 fail (2.39s) |
| 4 | Scope discipline + test_05 + live tests + usage/provenance sync | **PASS** | Only 3 files, trailer present; test_05 stub returns no model field so `UNKNOWN` is the correct new contract; live tests untouched and still skipped; `ModelUsage.model` sync is forced by `cognitive_runtime.py:115–124` |
| 5 | Full quick check | **PASS** | `tools/check.py --quick`: 558 passed, 3 skipped (live provider), governance PASS, VERDICT: PASS — matches the implementer's numbers exactly (+6 vs the 552 baseline) |

## 2. Evidence

### 2.1 Independent reproduction (item 1–2)

My reproduction script (`/tmp/repro_prov_accept.py`, ephemeral; the durable regression record is the shipped test file in the repo) differs from the shipped tests in server implementation, model names, and cases:

- **Server:** a raw `socket` one-shot server (no `http.server`), response sent in two halves with a 50 ms delay to exercise real streaming; the shipped tests use `http.server.HTTPServer` writing all chunks at once.
- **Model names:** synthetic and unlike the shipped `grok-4.7`/`grok-4.5` pair — requested `model-alpha-req` vs served `model-beta-srv`; tools path requested `model-delta-req` vs served `model-epsilon-srv`.
- **Extra cases the shipped tests do not cover:** first-non-blank-wins when two different model names appear in one stream (`model-first-wins` vs `model-second-ignored` → `model-first-wins`); whitespace-padded server model (`"  model-gamma-srv  "` → `model-gamma-srv`); end-to-end construction of a `ModelDirective(response, usage, provenance)` from the returned values, proving the usage/provenance consistency constraint holds on real return values.

Results on the fixed tree: **17/17 checks pass**. Results on the unpatched worktree (`cf7d766^`, same script via `ACCEPT_SRC`): **8/17 pass — exactly the 9 provenance-model assertions fail**, all echoing the request (`model-alpha-req` / `model-delta-req`); request payload, text aggregation, request_id, and the `ModelDirective` construction all still pass there. The reproduction discriminates fixed vs unpatched exactly on the fixed behaviour.

### 2.2 Shipped regression tests (item 3)

- Fixed tree: `pytest tests/runtime/test_provenance_model_field.py` → **6 passed in 3.82s**.
- Unpatched worktree (test file copied in, since it does not exist at `cf7d766^`): **6 failed in 2.39s**.
- The 6 tests are genuine regression tests, not tautologies.

### 2.3 Scope, test_05, live tests, usage/provenance sync (item 4)

- `git show cf7d766` contains a single hunk in `test_live_multimodel_habitation.py` (test_05, +6/−1). The live tests (`test_02`, `test_04`, `@live`, lines ~407/435) are untouched and still skipped by default.
- test_05's stub (`_SSEStubHandler`) returns chunks with `id`/`choices`/`usage` only — **no `"model"` field** — so under the new contract `provenance.model == "UNKNOWN"` (and `usage.model == "UNKNOWN"`) is the correct assertion; the old `== "grok-4.7"` encoded the echo behaviour. The change is a contract update, not a weakening: the stub genuinely carries no server model to record.
- The live tests still assert `provenance.model == "grok-4.7"` (test_02) and `directive.provenance.model == "grok-4.7"` (test_04). Under the new contract those assertions hold only if a real endpoint returns the `model` field — standard OpenAI-compatible behaviour, but unproven locally because the tests skip without a live endpoint. See observation N-1.
- `ModelUsage.model` sync: `cognitive_runtime.py:115–124` (`ModelDirective.__post_init__`) raises `ValueError: usage model conflicts with model-call provenance` when usage and provenance disagree (non-None values). Changing provenance alone would have broken `as_model_handler`; setting `ModelUsage.model` to the same server-returned value is the same attribution path and the same value, not scope creep. Verified end-to-end by constructing `ModelDirective` from the returned usage+provenance in my reproduction (checks 1f, 4d).
- Request-id: `grok_provider.py:791` / `:1026` derive `request_id = captured_id or f"grok-{int(time.time()*1000)}"` — server chunk `id` first, synthetic fallback only when absent. The implementer's statement that no request-id change was needed is correct; see observation N-3 on the fallback.

### 2.4 Coverage completeness (own check)

Full-repo grep for `ModelCallProvenance(` in `src/`: exactly 3 construction sites.

- `grok_provider.py:846` (`stream_chat`) and `:1061` (`stream_chat_with_tools`) — both fixed by `cf7d766`; after the fix no `model=chosen_model` remains in provenance/usage construction in that file (lines 848, 861, 1063, 1112 all use `server_model`). Lines 1472/1487 still pass `model=chosen_model` as the *request* parameter to the streaming calls, which is correct — that is the request, not the provenance.
- `background_attempt.py:223` — only rehydrates an already-stored provenance dict (validates stored exact-response fields), it constructs nothing from a request; correctly out of scope.
- `headless/testing.py:33` (`model="deterministic-v1"`) is a deterministic smoke helper, not a live path; untouched, correctly so.
- `extract_durable_facts` inherits the fix via `stream_chat` (calls at `:1487`); no separate change needed.

### 2.5 Full quick check (item 5)

Re-ran by this acceptance agent on local HEAD `3b42a60`: `tools/check.py --quick` → **tests 558 passed, 3 skipped; governance PASS; VERDICT: PASS** (35.94s total). The 3 skips are the live-provider tests. Numbers match the implementer's run exactly (+6 vs the 552 baseline = the 6 new tests).

## 3. What the fix does not do (and must not be read as doing)

- It produces **no live evidence**. R6 still needs a live re-capture with a server-returned `model` field, or trusted external attestation, on this fixed path. The fix only makes such evidence possible: before it, even a perfect live run could not have been attributed to a real model.
- It does not change the request path: the request still asks for the configured/chosen model (`chosen_model` in the payload, verified in reproduction checks 1a/6a).

## 4. Findings

No FAIL-level issues. Three non-blocking observations:

- **N-1 (low):** the two live tests' `grok-4.7` assertions now depend on the real endpoint returning the `model` field. That is standard OpenAI-compatible behaviour, but it is unproven locally (the tests skip by default) and was not part of this acceptance. First live re-capture will confirm or refute it; if a real endpoint ever omits the field, those tests will (correctly) start recording `UNKNOWN` instead of passing silently on an echo.
- **N-2 (low, pre-existing design boundary):** other `ModelUsage` fields remain request-side/estimated values (token-estimation branches). That is a metering question, not a provenance-attribution question; unifying it would be a separate task.
- **N-3 (low, pre-existing):** when the server omits the chunk `id`, `request_id` falls back to a synthetic `grok-<milliseconds>` value. A synthetic id is not server attestation. This predates the fix, is unchanged by it, and is outside this task's scope — but a future live re-capture should confirm the server actually returns chunk ids, so the recorded request-id is a real binding, not a locally minted one.

## 5. Recommendation to the PM

1. **Accept this fix (ACCEPTED).** Both streaming paths now record what the server says served the response, `UNKNOWN` is recorded explicitly when the server says nothing, the usage/provenance sync is sound, the 6 shipped tests are genuine, scope is disciplined, and the full quick check passes.
2. **Next is publication, not more engineering on this item.** `cf7d766`'s push touches `src/aios_core/**` and will trigger `p16-convergence-gate` on main — verify that CI run after it lands.
3. **Do not reopen the audit baseline on this account.** This acceptance verifies only the provenance fix; it does not touch R1–R9 semantic evidence. The audit exits stand on RV20261120-001 / RV20261120-002.
4. **Carry N-1 and N-3 into the live re-capture task** as checks to perform when a real endpoint is next used: confirm the endpoint returns both the `model` field and chunk `id`s.
