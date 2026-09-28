# CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001 — handoff

Role: **Core Runtime Corrective Engineer**.
Binding blocker under correction: **`IA-BLK-TRUSTED-RETURN-001`**.
Result: **`READY_FOR_INDEPENDENT_ACCEPTANCE`**.

This document is the corrective's own report. It is not an acceptance, not an IA
adjudication, and not a release action.

---

## 1. Fresh governance fetch (no SHA taken on trust)

Fetched live at the start of this task:

| ref | SHA |
|---|---|
| `origin/main` (live) | `5288822e751df185f3abab79f969609f31859617` |
| PR #258 head / failed exact candidate | `1ebf51c4cb905e2a2578a09b64007b50bca0d4ac` |
| PR #261 head | `b9d692ddca055b13fb29e646186e929a08bf8955` |
| merge-base(main, #258) | `7b207362a0b148c5d49bb586f1c878583661a5a9` |

Governance state read: RECOVERY-001 = `FAILED EXACT CANDIDATE`; IA = `DONE /
ACCEPTANCE_FAIL` with `IA-BLK-TRUSTED-RETURN-001` BINDING; CORRECTIVE-001 =
`READY`. No drift from the three required states, so no `GOVERNANCE_DRIFT` stop.

History preserved intact: the later-round RED `cca64dca`, the frozen R5 RED
`d3fa0490`, the failed exact `1ebf51c4`, the author greens, the reviewer REDs and
the #261 evidence history are all reachable and unmodified. No historical FAIL was
rewritten into a PASS.

## 2. Carry-forward of #258's trusted-return recovery body

Live main does **not** contain #258's implementation, so a fresh-main-only
corrective would have been a fake. The 7 non-merge commits of #258 were
cherry-picked onto the fresh main base (`cca64dc`, `913c537`, `b9481b3`,
`1336e5e`, `0de7b2f`, `d3fa049`, `1ebf51c`; the merge `17b7d1f` skipped), then the
corrective was built on top.

Auditable lineage proof:

```
$ git diff --stat refs/remotes/pr/258 HEAD -- <#258's 12 files>
 src/aios_core/execution/service.py    | 146 ++++++++++-----
 src/aios_core/storage/sqlite_store.py | 178 ++++++++++++++++++
 2 files changed, 287 insertions(+), 37 deletions(-)
```

Ten of #258's twelve files are **byte-identical** to #258, including the whole
trusted-return path:

```
$ git diff --quiet refs/remotes/pr/258 HEAD -- \
    src/aios_core/runtime/background_attempt.py \
    src/aios_core/runtime/turn_runtime.py \
    <all trusted-return / R5 test files>
YES
```

Carry-forward checklist, all still present and unchanged:

- trusted provider-return handoff — `background_attempt.py`, byte-identical to #258
- receipt + exact payload atomic durability — byte-identical to #258
- `recover_trusted_handoff(...)` — byte-identical to #258
- no caller-supplied arbitrary directive bytes — byte-identical to #258
- no receipt / signing authority exposure — byte-identical to #258
- stronger terminal output/delivery short-circuit — byte-identical to #258
- R1–R5 recovery behaviour — 111 focused probes pass (§7)
- original authenticity / transplant / corruption fail-closed — byte-identical tests, pass
- operation lookup stays read-only and never authorizes a write — pinned by a new probe

## 3. Frozen capability replay matrix (built before any Core change)

Enumerated dynamically from `FusedTurnRuntime.registry.catalog()` via
`tools/corrective001_enumerate_capabilities.py` — never hardcoded:
**43 model-callable / 22 side-effecting**, identical on live main, on the failed
exact candidate, and on this candidate (`enum_candidate.json`; drift check
`main == candidate: True`).

The 22: `commit_ai_world_claim`, `commit_claim`, `commit_operation_experience`,
`create_attention_watch`, `create_task`, `form_event`, `propose_action`,
`propose_cognitive_policy`, `propose_dimension`, `propose_entity`,
`propose_goal`, `record_communication_experience`, `retract_claim`,
`revise_claim`, `revise_entity`, `rollback_cognitive_policy`,
`transition_dimension`, `transition_event`, `transition_goal`, `transition_task`,
`update_cognitive_policy`, `upsert_relation`.

No capability was marked `NON_APPLICABLE`; all 22 are reachable and all 22 are
probed. The matrix carries an inventory guard test that fails if the live
registry and the frozen matrix ever diverge.

Frozen probe revisions and SHA-256 (`evidence/probe_hashes.txt`):

| rev | SHA-256 | role |
|---|---|---|
| rev1 | `a9a99230…` | first draft |
| rev2 | `84d67e19…` | harness fixes |
| rev3 | `86d3860b…` | harness fixes |
| rev4 | `0dabdaea…` | harness fixes |
| **rev5** | **`15bc7a93…`** | **frozen baseline matrix, preserved verbatim** |
| **rev6** | **`01258503…`** | 3 documented reclassifications only |
| **rev7** | **`835f2740…`** | current; adds the same-`call_id` probe, no expectation changed |

## 4. Baseline RED against the failed exact candidate

`evidence/baseline_red_against_1ebf51c4.txt` — rev5 run against
`1ebf51c4` in an isolated worktree: **20 FAILED / 44 passed**.

Reproduced byte-identically on the carry-forward *before* any Core change; the
failing id list is identical to `evidence/baseline_red_test_ids.txt`
(`diff` → empty).

- **17 exact-replay RED**: `form_event`, `propose_action`,
  `propose_cognitive_policy`, `propose_dimension`, `propose_entity`,
  `propose_goal`, `record_communication_experience`, `retract_claim`,
  `revise_claim`, `revise_entity`, `rollback_cognitive_policy`,
  `transition_dimension`, `transition_event`, `transition_goal`,
  `transition_task`, `update_cognitive_policy`, `upsert_relation`
- **3 same-key-conflict RED**: `rollback_cognitive_policy`,
  `update_cognitive_policy`, `upsert_relation` — these *silently wrote a second
  revision* instead of failing closed
- All five reviewer-proven families reproduced verbatim:
  `propose_goal` / `form_event` / `propose_action` /
  `record_communication_experience` → "idempotency key was already used for a
  different request"; `propose_entity` → "entity_key already exists";
  `propose_dimension` → "dimension_key already exists";
  `propose_cognitive_policy` → "policy already registered"
- 5 converged on the baseline: `create_task`, `create_attention_watch`,
  `commit_claim`, `commit_ai_world_claim`, `commit_operation_experience`

## 5. Root cause and the implemented mechanism

**Root cause.** Durable operation identity was derived from *mutable world
state*: the next object revision, the current Claim revision, the latest policy
version, the relation revision. After the first application advanced the world, a
mechanically identical recovered replay derived a *different* identity, so it
could not match the original durable operation and could not converge. Where the
key happened to still collide, the second application silently wrote a duplicate
revision.

**Mechanism — smallest correct, no universal idempotency layer.**

1. `SQLiteWorldStore.replay_exact_operation(operation)` — normalises the key,
   reads the durable `operations` row (`None` → ordinary first commit), verifies
   the `idempotency_records` agreement, decodes the durable `CommitResult`,
   reloads the **originally committed** objects, restores the original
   `operation_id` and the original `expected_world_revision`, and replays them
   through the **unchanged** `commit()` request-fingerprint verifier.
   `commit_or_replay()` is the narrow helper for services that share exactly this
   replay identity contract. `commit()` and `request_fingerprint()` are
   **untouched**.
2. `canonical_request_identity(*parts)` (`storage/idempotency.py`) — a SHA-256
   over the complete canonical request, published inside
   `OperationRequest.arguments` so the *existing* verifier compares the whole
   logical request. The only change to `idempotency.py` is this addition; the
   fingerprint's inputs are unchanged and `expected_world_revision` remains in
   the fingerprint (independently confirmed, per the task instruction — not fixed
   by deletion).
3. Revision-advancing mutators resolve the durable identity from the **pinned**
   target revision, and probe it **before** the current-revision guards that a
   legitimate replay would otherwise trip (`transition_goal`, `transition_task`,
   `transition_dimension`, `transition_event`, `revise_entity`, `revise_claim`,
   `retract_claim`, `propose_entity`, `propose_dimension`,
   `propose_cognitive_policy`).
4. Three capabilities whose key embedded state now key on the request:
   `relation-upsert:{relation_id}:{identity[:24]}`,
   `policy-update:{object_id}:{identity[:24]}`,
   `policy-rollback:{object_id}:{identity[:24]}`.
5. `propose_entity` / `propose_dimension` / `propose_cognitive_policy` keep their
   domain-level "already exists" error: only a genuine `IDEMPOTENCY_CONFLICT` is
   translated, corrupt or skewed durable state still fails closed. This preserved
   `test_duplicate_dimension_key_is_rejected_deterministically`, the one
   regression the full suite surfaced.

None of the prohibited patterns were used: `request_fingerprint` not disabled,
`expected_world_revision` not removed, `commit()` does not accept a changed
request under an existing key, "already exists" is not globally converted to
success, no silent overwrite, no second truth store, no generic post-application
state machine, no new generic recovery journal. The trusted-return signing
authority, receipt/HMAC ownership and recovery trust boundary are untouched — no
`BLOCKED` condition was reached.

## 6. Disclosed expectation change (rev5 → rev6)

rev7 additionally adds 22 same-`call_id` probes (additive; no expectation changed), which prove that reusing the original `call_id` with different arguments never overwrites the original durable object — `call_id` is only echoed into `CapabilityResult` and takes no part in durable identity.

Three scenarios moved their changed-field mutations from `conflicts` to
`identity_shifts`: `upsert_relation`, `update_cognitive_policy`,
`rollback_cognitive_policy`. Full rationale, mechanical proof and the compensating
store-level fail-closed suite are in
`evidence/rev6_reclassification_rationale.md`. rev5 is preserved verbatim.

In short: their request contracts carry no pinned target revision, so the
state-derived key that made rev5's conflict case reachable *was* the defect. After
keying on the complete canonical request, an identical replay converges and a
changed request is a distinct auditable operation — proven by direct SQL:
zero key reuse, all original revisions intact, a new revision rather than a
silent overwrite. The shared-key fail-closed guarantee is now pinned directly at
the store layer by 17 new probes.

## 7. Test results on this candidate (all re-run fresh)

| suite | result |
|---|---|
| Frozen capability replay matrix (rev7) | **83 passed** (1 inventory guard + 22 exact replay + 16 same-key conflict + 22 identity shift + 22 same-`call_id`) |
| Store-level fail-closed | **17 passed** |
| Real process-loss R5-C (3 runtime modes) | **3 passed** |
| Historical focused regression (R1–R5 A/B/C/D, authenticity matrix, transplant + corruption, terminal conflict, operation replay, recovery) | **111 passed** (`evidence/candidate_regression_focused_suites.txt`) |
| **Complete pytest** | **919 passed, 0 failed** in 187.32 s (`evidence/candidate_full_pytest.txt`) |
| `--collect-only` | 919 tests collected |

Historical numbers (24/24 R5, 99/99 focused, 816/816 full) were treated as
evidence only; everything above was re-executed against this candidate.

### Real process-loss R5-C (the required non-`create_task` proof)

`tests/integration/test_core_background_trusted_return_corrective_001_process_loss.py`.
Each probe forks a child that dispatches a real model round, returns a real
trusted provider directive, applies the capability so its side effect is durable,
then `SIGKILL`s itself before the outer completion lands; the parent asserts
`exitcode == -SIGKILL`, reopens the World in a brand new runtime, and replays the
identical recovered directive.

| work kind | capability | family |
|---|---|---|
| `wake` | `revise_claim` | revision-advancing mutator, **non-`create_task`** |
| `user_turn` | `transition_goal` | revision-advancing mutator |
| `periodic_review` | `form_event` | one of the five reviewer-proven RED families |

Each asserts: no provider redispatch for the recovered round, exactly one meter
row for that round **with the same `record_id`**, one durable effect with the
original object/revision identity, one operation identity, and a converging turn.

Exactly-once is asserted **per recovered model round**, not per turn: a
`ModelDirective` cannot both request capabilities and terminate (the contract
rejects it), so a recovered capability round is always followed by a legitimately
new round. Runtime-mode rationale: `_authorize_side_effect` gives C14 wakes a
four-name allowlist while user turns, Periodic Review and other wakes share the
twenty-name set, and background attempts are keyed by `work_kind`.

## 8. Environment (recorded, never faked)

`evidence/environment.txt`:

- CPython **3.12.14** (built from source in this sandbox)
- Pydantic **2.13.5**
- pytest **8.4.2**
- SQLite **3.49.1** — **differs** from the author's 3.45.1 and the reviewer's
  3.51.1. Disclosed, not faked. `python.org` and the PyPI-hosted interpreter
  indexes were unreachable from this sandbox, so 3.12.14 was compiled from the
  official cpython tarball and SQLite from an amalgamation tarball.
- OS Linux 6.1.158+ x86_64

## 9. Branch and PR

- Session branch (platform-fixed, disclosed here as required):
  `arena/01a0e76f-haneof-aios-core-v3-0`, based on fresh live main `5288822`.
- PR #258 untouched: no rewrite, no force-push, no hash-swap, no merge, and the
  corrective was **not** pushed into it.
- PR #261 untouched: not modified, not merged, and no reviewer-only artifact was
  carried into the candidate (`tests/independent_acceptance` is absent from this
  branch).

## 10. Explicitly not done (out of role)

No self-acceptance, no Corrective-001 IA, no merging of #258 / #261 / this PR, no
PM integration, no `CORE-RC-REFREEZE-003`, no `C15-RCC-RES-A-RERUN-004`, no
persistence Corrective-003 resume, no Resident B/C, no RELEASE-003, no evaluator
or closure action.

**Exit: `READY_FOR_INDEPENDENT_ACCEPTANCE`.**
