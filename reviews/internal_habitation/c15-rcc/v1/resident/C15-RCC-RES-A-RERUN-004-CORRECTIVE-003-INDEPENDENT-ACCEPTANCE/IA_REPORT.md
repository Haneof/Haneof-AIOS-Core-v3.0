# C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-INDEPENDENT-ACCEPTANCE — Formal IA Report

Reviewer role: Independent Fresh Resident A Evidence Acceptance Reviewer (not Resident, not PR author, not PM/Core/Op-Prep/persistence, not B/C, not evaluator).
Review date (UTC): 2026-09-29.  REVIEW-ONLY / EVIDENCE-ONLY / DO NOT MERGE.

## Verdict

```
ACCEPTANCE_PASS / blocker=0
READY_FOR_PM_INTEGRATION
```
Does NOT authorize Persistence Corrective-003, Resident B/C, evaluator, or C15 close.

**Durable publication status: `EVIDENCE_PUBLICATION_BLOCKED`** — the reviewer sandbox has read-only anonymous GitHub access (no token, no `gh`); the review commit exists locally and as a git bundle, but could not be pushed, no review PR could be opened, and no comment could be posted on PR #296. See §Publication.

## 1. Fresh fetch / identity
| item | expected | observed |
|---|---|---|
| live main | (PM saw e83b1aa7…) | `e83b1aa7e4321ba48a1cb390828e149350c2be71` |
| board/checkpoint | IA = READY | task board L9 + checkpoint L9: READY |
| PR #296 head | 317316299c33… | `317316299c332d82e0cbd0431b5c7d50f391bc17` (no drift) |
| tree | a64b60ad… | match |
| parent | f7bcec4e… | match; parent is ancestor of main |
| accepted Op Prep | PR #292 H2 `42a63ed4…`, H1 harness `77dac70e…` | packet at H2 sha256 `3c2d04c2…` ✓; harness manifest `2bc303cd…` ✓; H1→H2 harness/bootstrap diff empty; 30/30 manifest files hash-verify |
| frozen RC | f20f2edf / 1ac3a675 / 9adcbe07 (src/aios_core) / 7e33b5ef | all trees match |

## 2. Probe discipline
Probes frozen (source SHA-256 + enumeration + expected outcomes) before first execution against candidate evidence (`probes/PROBE_FREEZE_*.sha256`). Two reviewer probe defects found; old revision and old result preserved, corrected revision frozen and re-run; no expectation tuned:
- `ia_probes_rev1.py` P05/P08 FAIL → **probe defect**: generic English n-grams from a later payload (c15rcc-018 "authorization") matched frozen-Core capability schema text present in every RuntimeSnapshot. rev2 excludes n-grams occurring in frozen Core/harness source. Result: `raw/probes_rev1.json` (kept), `raw/probes_rev2.json` 8/8 PASS.
- `ia_restart_probe_rev1.py` FAIL → **probe defect**: compared raw SQLite bytes; frozen Core open rewrites SQLite header bytes with zero logical change (iterdump identical, 269 statements). rev2 compares logical dump. `raw/restart_rev1.json` (kept), `raw/restart_rev2.json` PASS.
- Supplementary probes `ia_probes_rev2_supp_chain.py`, `ia_world_inventory_supp.py` each frozen before first run.

## 3. Results by acceptance section
- **Scope (§4)**: 1 commit, 212 files, all `A` under evidence root; no src/tests/harness/fixture/evaluator/release/governance change. PASS.
- **Freshness (§5)**: run/process/session/conversation IDs unique to this run; World/index/exchange/release-state absent pre-cursor-1 (audit is evidence only); independently: exchange seq starts at genesis, World commits 1..38 contiguous, release receipts start at seq 1, no foreign IDs; no A-001..A-004 / B / C strings in any request/response (P06 0 hits). PASS.
- **Clean-room (§6)**: 42 request/response files scanned for task-board/checkpoint/governance/PM/PR#292/#294/prior-run/fixture/evaluator/release/future-ID markers: 0 hits. Every semantic item in all 21 responses traceable to already-revealed events. No material semantic contamination found. (Observation O1.)
- **Cursor chain (§7, §12, §13, §20)**: events 1..13 equal sealed fixture Phase A seq 1..13 (IDs, payloads, occurred_at; payload hashes 13/13; fixture sha `7ccb309d…`); ingest→ACK with ACK ref == ingest ref == receipt ref, strictly increasing ingest world revisions; each ref resolves in World to an Observation containing the exact payload; USER receipts `canonical_user_turn`, session `sess-resident-a-c003-7089564bdf1d`, turn_index 1..7 monotonic; each turn_result references its canonical Observation; 7 distinct USER Observations (no duplicate); 7 assistant outputs for 7 USER turns; PLATFORM receipts `fixture_observation`. release-state: 13 receipts, last_acked 13, next 14, pending_reveal null, no seq-14 receipt/projection anywhere. PASS.
- **Future leak (§8)**: per-cursor legal-reality construction; every request and response mapped to its cursor (21/21) and checked for later event IDs (any phase) and distinctive later-payload n-grams: 0 hits. World dump: 0 later IDs, 0 later n-grams, no object references a later revision, all learned_at ≤ cursor-13 time. PASS.
- **Semantic authenticity (§9) — all 21 exchanges manually read** (`raw/manual_21_responses.txt`): all `authored_by=EXTERNAL_CURRENT_RESIDENT_SESSION`, no deterministic/synthetic markers; directives are varied, context-specific, with evidence refs to real Observations; silences only on background review closure. No indication of scripted routing.
- **Exchange chronology (§10)**: 63 records, 21 × (published, response_published, consumed) in order, prev-hash chain and record hashes recomputed, request/response file digests bind, no orphan/unconsumed; head `7f8afff3…ebba691` recomputed. Frozen harness `integrity()` on reviewer copy: ok, 63, same head, COMPLETE. PASS.
- **Harness immutability (§11)**: freeze manifest records packet `3c2d04c2…`, harness manifest `2bc303cd…`, bootstrap `e98965d8…` = accepted H2 bytes. PASS.
- **Due work (§14)**: 13 due results at exact event times; periodic reviews at cursors 1, 6, 7, 13 each ran through durable Wake revisions (3 durable revisions each: new→running→completed, independently read from World) with bound model requests; cursors 9/11 due = no wakes, consistent with world state; no clock jumps (all learned_at = event times). PASS.
- **Final restart (§15)**: reviewer-built CPython 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2 / SQLite 3.45.1 / OpenSSL 3.0.13 via accepted bootstrap; `aios_core.__file__` = frozen RC worktree. World rev 38, watermark 38, lag 0; `process_due_work(now=2026-11-06T11:10-08:00)` → no wakes, no review, **0 model calls**; logical World/index unchanged across open and due; exchange COMPLETE, unconsumed 0, open dispatched 0; cursor 14 not revealed. PASS.
- **Cognition (§16-18)**: 3 cognitive policies (detail level, production-delete authorization, queued-vs-completed reporting) each sourced from an explicit USER statement with evidence set + dependencies; 1 communication experience backed by user feedback (c005) + platform outcome (c004); 1 Task (attention watch) remains waiting (single revision); 1 Claim typed `inference`, confidence 0.75, with explicit unknown_items. User-facing replies: c008 correctly says upload NOT done (queued, no tag/digest) and advises not notifying stores; c010 reports rejection with no completion; c012 states published only after durable PUBLISHED Observation (c011). No false completion, no unsupported fact. PASS.
- **World/index (§19)**: integrity_check ok both; SHA-256 `0d6970ed…` / `79c877a4…`; inventory 56 revisions (20 observation, 12 wake, 4 evidence_set, 3 cognitive_policy, 14 dependency, 1 comm-exp, 1 task, 1 claim); 0 dangling refs. PASS.
- **Checksums (§21)**: 212 files; SHA256SUMS covers 211, all match; SHA256SUMS `1eee5df0…`, ledger `3b2b9e90…`, release-state `6b90fc7a…`, FREEZE_MANIFEST `bc66ad55…` all recomputed equal. PASS.
- **Environment (§22)**: run environment_probe records exact pins and aios_core from frozen RC checkout; rc_identity checks all true; reviewer independently reproduced the same pinned runtime from the accepted bootstrap. PASS.

## 4. Non-blocking observations
- **O1** No shell/tool trace of the Resident session is in the package, so non-access to forbidden material is not positively provable; judged only by absence of any material semantic contamination in outputs (none found).
- **O2** Cursor-13 Claim says the outcome "was learned from the user's question"; c012 is a user statement, not a question. The claim is typed inference with unknowns; its factual core (watch still waiting, no watch Wake on c011) is verified. Wording imprecision, not unsupported fact.
- **O3** c010 reply promises proactive notification via the watch; the watch did not fire on c011 (frozen-Core mechanics). No false completion resulted, and the Resident self-calibrated durably at c013. Relevant input for later evaluation, not for this acceptance.
- **O4** Opening World under frozen Core changes SQLite file bytes without logical change; future reviewers should compare logically or work on copies.

## Publication
Local review commit (branch `review/c15-res-a-c003-ia`, based on live main `e83b1aa7…`) — see `REVIEW_IDENTITY.txt`; bundle `review.bundle`. Push/PR/comment impossible from this sandbox → `EVIDENCE_PUBLICATION_BLOCKED`. Required PR #296 comment text is in `PR296_COMMENT.md` for the operator to post.
