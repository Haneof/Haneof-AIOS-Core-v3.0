# C14-SEM-REPAIR-RES-001 PM Evidence Acceptance Review — 2026-09-22

> Reviewer role: Independent PM / Evidence Acceptance Reviewer (single governance window).
> Scope: freeze and formally accept the real Resident evidence of `C14-SEM-REPAIR-RES-001`, complete the governance handoff, and make `C14-SEM-REPAIR-EVAL-001` READY.
> Out of scope (explicitly NOT performed): any E1/E5 semantic validity verdict, any C14 closure, any Core change, any Resident re-run or evidence rewrite.

---

## 1. Authoritative main at review start

- `main` = `7611fa5059f5dc8a20835cab5b312be2f43d11e8` (re-fetched live from GitHub at review start; identical to the run's declared evaluated main).
- Task board state on that main: `C14-SEM-REPAIR-RES-001 = READY`, `C14-SEM-REPAIR-EVAL-001 = BLOCKED`. Acceptance / handoff had not yet been performed by any other window. Proceeded.

## 2. Resident evidence branch

- `arena/01a0c773-haneof-aios-core-v3-0` (20 commits on top of `7611fa5`).

## 3. Exact canonical evidence head

- `9e870514b57bf07c00018d7dcf7435f2702f8730` (branch head at review time; all checks below re-verified at this exact SHA).

## 4. Canonical evidence PR

- **PR #92** — "C14-SEM-REPAIR-RES-001 canonical Resident evidence [PINNED — DO NOT MERGE — evaluator must use this exact head only]".
- Base = current `main`; status OPEN / UNMERGED / PINNED. The Resident private World and evidence must never be squash-merged into main.

## 5. Evaluated main

- `7611fa5059f5dc8a20835cab5b312be2f43d11e8` (declared in `run_manifest.json`, `RESIDENT_RUN_REPORT.md`, and `resident_runner.py` `STARTING_MAIN`; equals the live main the run branched from — verified via merge-base).

## 6. Session / run identity

- Resident session: `resident-sem-repair-20260922`
- Run ID: `resident-repair-20260922`
- Run directory: `reviews/internal_habitation/c14-resident/semantic-repair-v1/runs/resident-repair-20260922/`
- Declared runtime identity: Arena.ai / Agent Mode (provider request attestation is not exposed to the repository harness; recorded as such in `run_manifest.json`).
- Subject: `user_1`.

## 7. Cursor completeness

- Release state (`release_state.json`): 15 receipts, sequences strictly `[1..15]`, monotonic, no skip, no reorder, `active_phase=B`, `last_acked=c14semrep-015`, `next_sequence=16`, `pending_reveal=null`.
- Phase A = cursors 1..6; Phase B = cursors 7..15; Phase B init only after the sealed 6→7 boundary (`phase_A_init` / `phase_B_init` receipts present).
- Per-cursor `lifecycle.json` cross-checked against release receipts: all 15 event IDs and durable `ingest_ref`s match; `world_revision_after_ack` strictly non-decreasing; every ack executed against the private SQLite World via the frozen release operator (receipt `status=acked`, durable `ingest_world_revision` recorded) — not receipt-string-only.
- Cursor 12 (USER conversation) used the canonical conversation ingest path (`obs_conv_user_366afd061716259aa...@1`, session/turn-index verified in ack argv); generic mechanical ingest correctly rejected for that envelope.

## 8. Final World revision / hash

- Final World revision: **83** (`MAX(world_revision)` in `private_world.sqlite` = 83 = `world_commits` row count).
- World SHA256 (recomputed independently by this window): `a7a7cd9f9166eb41d3b93d85820a9c7a4ab0aa57b81787d89f395482742bae57` — matches report, manifest, and `final/digests.json`.
- Index SHA256: `ae296ee44a000eb7ea5bf122184bfb9dd65c80f14f9e94e9fb64fce039658caf` — recomputed, matches.

## 9. Release-state hash

- Release-state SHA256 (recomputed): `4f41d709a76e0f40ce5b0093f540cc286dde84a1906a575019199cc7a7970081` — matches report, manifest, and `final/digests.json`.
- Fixture identity pinned inside the release state: `sha256:1095d5aef52061753db7d9dab558af1361b92976f2ded0e6956d70afe3e6527f` — equals the sealed fixture bytes on `main` (recomputed).

## 10. Semantic checkpoint count

- 16 checkpoints (`cp0001`..`cp0016`), each with `checkpoint.json` (session, released cursor, simulated timestamp, world_revision_before/after, declared provider/model), full `snapshot.json` (RuntimeSnapshot), and `directive.json` (ModelDirective).
- Checkpoint→cursor mapping is coherent and time-monotonic across the simulated life (2026-11-03 → 2026-11-13).

## 11. Summary count

- 20 Resident-authored summary requests/responses (`sum0001`..`sum0020`; dimension summaries and round summaries), each with the full request payload and non-blank authored response content. Count matches report and `run_state.json`.

## 12. Capability trace completeness

- 18 capability calls, all present with results in runtime `capability_history` (`call_id`, `name`, `ok`, `data`/`error_code`):
  - `inspect_world_object` × 15 (cp0003 ×3, cp0007 ×3, cp0011 ×4, cp0014 ×5);
  - `commit_claim` × 1 (cp0004);
  - `revise_claim` × 2 (cp0008, cp0015).
- 8 silence directives (cp0001, cp0002, cp0005, cp0006, cp0009, cp0010, cp0013, cp0016) and 1 user-facing response (cp0012, cursor-12 USER turn). Directive kinds are mutually exclusive and validated by the bridge.
- Resident-autonomous decision trace confirmed in durable World: single claim `clm_b4df2179bb8ffec020a39ede` revision chain rev1@world_rev20 (commit) → rev2@world_rev44 (revise) → rev3@world_rev77 (revise), final `@3` active, confidence 0.78; each revision's `support_evidence_set_refs` resolves to pinned leaf Observation sets (3 / 6 / 11 members) exactly matching the model-authored evidence refs in the directives. No retraction occurred; silence is a legal Resident result.
- Summary of counts vs report: semantic checkpoints 16/16, summaries 20/20, silences 8/8, capability calls 18/18, responses 1/1 — all consistent across `run_state.json`, `run_manifest.json`, `RESIDENT_RUN_REPORT.md`.

## 13. Real-Resident / no-pseudo-LLM assessment

- The only execution path is `resident_runner.py` (`LocalResidentBridge`): it persists the RuntimeSnapshot, writes a `SNAPSHOT` pending request, prints `RESIDENT_WAITING_FOR_DECISION`, and blocks in a poll loop until an externally authored `pending_response.json` appears; the response must be a valid ModelDirective (`capability_calls` XOR `response` XOR `silence`, else hard error). The same transport is used for summary requests. Summary/response content is stored verbatim; the bridge never generates, selects, scores, or rewrites content.
- Grep + full read of the bridge found **no** keyword→Claim mapping, no if/else cognition, no fixed expected answer, no fixed Claim text, no evaluator oracle, no automatic revise/retract, no pseudo-LLM, no future-aware semantic branching. The only `dim:conversation` conditionals are mechanical routing to the canonical conversation ingest path, as required by the release contract.
- The bridge executes Resident-selected capabilities through the real AIOS Core (`FusedTurnRuntime`, `ModelDirective`, `CapabilityCall`, `SQLiteWorldStore`, `WorldSearchIndex`); wakes and periodic reviews drain through the same real runtime with the same Resident decision transport.
- Conclusion: evidence is consistent with a real external Resident authoring every semantic decision. (Runtime identity attestation beyond the declared string is not exposed to the harness; recorded, not judged.)

## 14. Future-leak assessment

- All 16 snapshots scanned: fixture event IDs referenced are always ≤ the checkpoint's released cursor — **zero** future-event references.
- All 20 summary requests scanned: no future event references, no evaluator/design-note markers.
- Reveal projections contain exactly the 8 contract fields (`event_id`, `sequence`, `occurred_at`, `dimension`, `source_kind`, `source_class`, `modality`, `resident_visible_payload`); no labels, expected answers, or control tags.
- `fixture/`, `evaluator/`, `release/` directories on the evidence branch are byte-identical to `main` (0 diff); the sealed fixture bytes were read only inside the frozen release operator to validate and project the current cursor, which is explicitly allowed.

## 15. Core diff

- `git diff main..9e87051 -- src/aios_core/` = **0 files**. No Core modification.

## 16. Historical evidence diff

- `reviews/internal_habitation/c14-resident/v2/**` = **0 diff**.
- PR #75 head still `cb9b56b7039272d932158f33bfe979eff6749c9b`; PR #79 head still `546449a453e6e6dff3a2eeb2b52e7cf6786927be` — historical A/B evidence untouched.
- The only pre-existing files modified on the evidence branch are `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md` and `AIOS_v3.0_CURRENT_CHECKPOINT.md` (the Resident window's own completion note, commit `9e87051`). That self-recorded governance text is superseded by this window's official PM write-back on main; it changes no run artifact.

## 17. Old PR disposition table (#84–#91)

| PR | Trial | Final disposition | Action taken 2026-09-22 |
|---|---|---|---|
| #84 | r2 trial run, `runs/resident-repair-20260922-r2/`, reached cursor 004 only | **ABORTED / NON-CANONICAL / SUPERSEDED** | Retitled `[NON-CANONICAL — ABORTED TRIAL r2 — DO NOT USE]`, disposition comment, CLOSED |
| #85 | r3 isolated bridge trial, no complete run | **ABORTED / NON-CANONICAL / SUPERSEDED** | Retitled `[NON-CANONICAL — ABORTED TRIAL r3 — DO NOT USE]`, disposition comment, CLOSED |
| #86 | r6 output-channel scaffold, no run | **SCAFFOLD ONLY / SUPERSEDED** | Retitled `[SCAFFOLD ONLY — NO RUN — SUPERSEDED]`, disposition comment, CLOSED |
| #87 | r7 instrumented channel scaffold + cursor-001 control record, no run | **SCAFFOLD ONLY / SUPERSEDED** | Retitled `[SCAFFOLD ONLY — NO RUN — SUPERSEDED]`, disposition comment, CLOSED |
| #88 | r8 mechanically complete parallel run (`resident-repair-20260922-r8-3e8a71/`, session `resident-sem-repair-sol-20260922-r8-3e8a71`, declared OpenAI/GPT-5.6 Sol, claim `clm_457125b0d4422b2f159091e0@2`, World `b7a3a32a…`) | **NON-CANONICAL — DO NOT EVALUATE / SUPERSEDED** (not the designated formal handoff run) | Retitled `[NON-CANONICAL — PARALLEL TRIAL r8 — DO NOT EVALUATE]`, disposition comment, CLOSED |
| #89 | r4 run aborted by its own window ("abort contaminated r4") | **ABORTED (confirmed)** | Confirmation comment added; stays CLOSED |
| #90 | r5-8d41ac aborted by its own window ("resident future-contamination detection") | **ABORTED (confirmed)** | Retitled `[ABORTED — DO NOT MERGE — NON-CANONICAL]`, comment added; stays CLOSED |
| #91 | fresh sealed bridge/workflow scaffold (commits `c1d6a20`, `eb6d1d4`, `7775ab2`) | **SCAFFOLD ONLY / SUPERSEDED BY #92** (its commits are direct ancestors of canonical head `9e87051`; the formal run executed on top of this scaffold) | Retitled `[SCAFFOLD ONLY — SUPERSEDED BY #92]`, disposition comment, CLOSED |

- **Unique canonical evidence**: PR #92 at exact head `9e870514b57bf07c00018d7dcf7435f2702f8730` only. No history was deleted.

## 18. Explicit statement

**"This PM review accepts evidence completeness and provenance only. It does not judge E1/E5 semantic validity."**

- Semantic verdict for the replacement E1/E5 evidence: **NOT PERFORMED** (by design).
- `C14-SEM-REPAIR-RES-001 = DONE` (evidence accepted & frozen); `C14-SEM-REPAIR-EVAL-001 = READY`; `C14-CLOSE-001 = BLOCKED`; `C15-RCC-RULE-001 = BLOCKED`.
- The evaluator must use PR #92 at exact head `9e870514b57bf07c00018d7dcf7435f2702f8730` only, and must not use any of the dispositioned trial PRs #84–#91.
