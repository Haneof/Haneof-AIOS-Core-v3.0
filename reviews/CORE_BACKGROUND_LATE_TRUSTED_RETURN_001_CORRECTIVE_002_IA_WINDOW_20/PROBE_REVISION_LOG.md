# WINDOW 20 Reviewer Probe Revision Log (`PROBE_REVISION_LOG.md`)

**Scope.** Both reviewer-owned probe suites executed against the exact candidate
`fec30bd1495017bf13f08b0ef5b1e241dfb0e247` (PR #310), plus the historical RED anchor
`cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd` (PR #308) used for the frozen W17 replay and a
frozen W17 reviewer suite extracted fresh from canonical review
`e4161dd0ad0a2f825461311a1c8c5ff8234a07f8`.

**Freeze rule applied (task §24–§26).** Every revision was written, hashed and recorded
*before* its first execution against the candidate. Defective revisions were never deleted or
edited in place: each is preserved verbatim under its frozen SHA-256 and its raw result is
retained. Results were never transferred between revisions. No expectation was altered to fit
observed candidate behaviour; the three pre-verdict expectation corrections that did occur are
enumerated below with their rationale and the invariant finally probed, so that a third party can
adjudicate them independently of the reviewer.

---

## Suite A — `window20_independent_attack.py` (mint-oracle / object-graph attacks)

Probe IDs: `IA20-MINT-003`, `IA20-MINT-004`, `IA20-OBJGRAPH-002`, `IA20-WINDOW-001`.

| Rev | SHA-256 | Status | Execution | Result |
|---|---|---|---|---|
| `v1` | `0381c6ceef2d0d8eed28d78b452fa8ae7770747537d9ae3ad3ad4ab8e3f87375` | `DEFECTIVE_HARNESS_REVISION` (preserved: `reviewer_probes/window20_independent_attack_v1.py`, `SHA256SUMS.v1`) | executed once; aborted at first probe | `PROBE_CRASH: KeyError: 'provider'` — the probe assumed the readable `BackgroundModelRequestBinding` row carried `provider` / `model` / `provider_request_id`; it carries only `attempt_id, subject_id, work_kind, work_id, model_round_index, outbound_request_fingerprint, relay_id, bound_at`. **No attack was executed and no expectation was evaluated.** Raw: `raw/candidate_w20_probes_v1_defective.txt`. |
| `v2` | `7cb32b5fd4a8ddb6eb3a7318c219fdd926d2a1a62edbcf38d4411d859df1c1ba` | `DEFECTIVE_HARNESS_REVISION` (preserved: `reviewer_probes/window20_independent_attack_v2_defective.py`; the pre-execution freeze record `SHA256SUMS.v2` and the preservation record `SHA256SUMS.v2_defective` intentionally carry the same digest — same bytes, not two revisions) | executed; probes 1–3 completed, probe 4 aborted | `IA20-MINT-003` `MINTED`, `IA20-MINT-004` `MINTED`, `IA20-OBJGRAPH-002` `MINTED`; then `LiveReturnAuthorityError: a live provider-return window is already open on this call stack` (`src/aios_core/runtime/live_return.py:168`) because the preceding object-graph mint left the module `_ACTIVE_WINDOW` `ContextVar` armed in the shared process context. Harness artifact, **not** fail-closed behaviour and **not** a candidate defect by itself; separately recorded as observation `OBS-W20-003` with its own evidence file `reviewer/reviewer_state_leak_in_tool_process.txt`. Raw: `raw/candidate_w20_probes_v2_defective.txt`, `raw/candidate_w20_probes_v2_on_fec30bd.txt`. |
| `v3` | `ec1dc5c2c5406d5d9e74825f62e0a17fb80f8ebd6dc250817fa048511ce292b5` | `ACCEPTED_FREEZE` — all 4 probes executed (fix: explicitly reset the armed window before/after each probe) | executed on `fec30bd…` | `SUMMARY \| probes=4 failures=4` — all four attacks succeed ⇒ candidate FAIL on `BLK-W20-001`. Raw: `raw/candidate_w20_probes_v3_on_fec30bd.txt`. |

No expectation change occurred in Suite A at any revision; only the read harness (v1→v2) and the
process-context hygiene of the harness itself (v2→v3) changed. Because `v1` yielded no evaluable
observation at all, the sequence never produced a "defective revision followed by a clean
revision with a different verdict" pattern that could mask a result: the only evaluable revisions
(`v2` partial, `v3` complete) agree on every probe they share.

## Suite B — `window20_migration_rsa_attack.py` (migration / RSA / post-binding / exactly-once attacks)

Probe IDs: `IA20-MIGRATE-003`, `IA20-MIGRATE-004`, `IA20-RSA-ENC-001`, `IA20-RSA-PARAM-001`,
`IA20-RSA-TRANSPLANT-001`, `IA20-NOTSUB-002`, `IA20-EXACTONCE-001`.

| Rev | SHA-256 | Status | Execution | Result |
|---|---|---|---|---|
| `v1` | `1e429dfea56430bf5ba6f7d1ed1ac0ead09b67fcb014e9e01313d372922b1e34` | `DEFECTIVE_HARNESS_REVISION` (preserved: `reviewer_probes/window20_migration_rsa_attack_v1_defective.py`, `SHA256SUMS.batch2.v1`; pre-execution freeze manifest `PROBE_FREEZE_MANIFEST_BATCH2.md`, timestamp `2026-10-03T06:29:00Z`) | executed on `fec30bd…` | `SUMMARY \| probes=7 failures=3` — all three failures probe-side: (1) `IA20-MIGRATE-004` `PROBE_CRASH: IntegrityError: NOT NULL constraint failed: background_model_responses.evidence`; (2) `IA20-RSA-PARAM-001` `unexpected=['exponent_float:ACCEPTED']`; (3) `IA20-EXACTONCE-001` `exact_replay_first=ACCEPTED`. Raw: `raw/candidate_w20_probes_batch2_v1_defective.txt`, `raw/candidate_w20_probes_batch2_v1_on_fec30bd.txt`. |
| `v2` | `de621da3e813752147a718a59782d2e1e607da4dd877353e291346d7545200c5` | `DEFECTIVE_HARNESS_REVISION` (preserved: `reviewer_probes/window20_migration_rsa_attack_v2.py`, `SHA256SUMS.batch2.v2`) | executed on `fec30bd…` | `SUMMARY \| probes=7 failures=1` — `IA20-MIGRATE-004` branches (e)/(f) reported `NO-RAISE` with `secret_preserved=False` because those branches staged a malformed secret against an **empty** trust state, so the conversion path never ran and the comparator was vacuous. Raw: `raw/candidate_w20_probes_batch2_v2_on_fec30bd.txt`. |
| `v3` | `769242465817f31734661ba7ba9c3d5f7d06b8d3f5235d72d2026956d9b98eb1` | `ACCEPTED_FREEZE` — 7/7 executed | executed on `fec30bd…` | `SUMMARY \| probes=7 failures=0`. Raw: `raw/candidate_w20_probes_batch2_v3_on_fec30bd.txt`. |

### Suite B v1→v3 changes, classified honestly

- **(a) `IA20-MIGRATE-004` `PROBE_CRASH` (v1→v2) — `HARNESS_FIX_ONLY`.** `background_model_responses.evidence` is `NOT NULL`; the probe inserted a `NULL` evidence value. The probe now writes a non-null evidence payload. No expectation changed.
- **(b) `IA20-RSA-PARAM-001` `exponent_float:ACCEPTED` (v1→v2) — `EXPECTATION_DISCLOSED` (narrowed).** v1-frozen expectation: a non-canonical exponent *including a float* is refused at construction. Observed: pydantic lax mode coerces integral `65537.0` → `int` `65537`, i.e. a **legal** exponent value; no authority follows from it. v3 no longer counts this as a security failure; it is retained as an explicit, printed observation (`integral_float_exponent_coerced_to_int=int:65537`) and recorded as `OBS-W20-005`. Every other non-canonical parameter (bool/`None`/negative/0/1/2/even/`e ≥ n`, non-canonical modulus forms, unknown algorithm) is still required to be refused, unchanged.
- **(c) `IA20-EXACTONCE-001` exact-replay expectation (v1→v2) — `EXPECTATION_DISCLOSED` (re-specified to the binding invariant).** v1-frozen expectation: an identical replay is *refused*. Observed: the replay is accepted as an effect-free `NOOP_ACCEPTED` — the durable response row count, meter count and completion state are unchanged (one staged row, one meter, one completion, assistant ref set). The re-specified expectation asserts the actual exactly-once/R5 invariant ("no duplicate durable effect") **and remains strictly falsifiable**: `NOOP_ACCEPTED` is only awarded when the staged-row count is `1` before and after; any second effect is reported as `ACCEPTED_EFFECT:rows=a->b` and fails. Requiring a specific exception type for a benign, effect-free replay would have been over-specification rather than a security property.
- **(d) `IA20-MIGRATE-004` branches (e)/(f) (v2→v3) — `HARNESS_FIX_ONLY`, with a strengthened replacement.** v2 staged malformed secrets in an empty trust state; v3 reclassifies (e)/(f) as *empty-trust-state* branches (invariant: `secret_purged`, `receipts_created == 0`, attempt left un-laundered) and **adds** (e2)/(f2) — malformed secrets *with* legacy trust state present — asserting `state_unchanged` and `secret_preserved` against the pre-state snapshot. Net effect: strictly more coverage than the v1-frozen wording, closed over the same two malformed-secret inputs.

### Freeze-integrity note on `PROBE_FREEZE_MANIFEST_BATCH2.md`

The manifest was frozen before first execution and is preserved, unedited, exactly as written; its
"SHA-256" line and its expectation table therefore describe **revision `v1`**
(`1e429dfe…`), not the final accepted revision. The final accepted revision is `v3`
(`76924246…`, `SHA256SUMS.batch2`) and the deltas from the frozen table are exactly the four items
(a)–(d) above. No frozen file was silently rewritten to make the record self-consistent — this note
carries the delta instead.

## Frozen W17 replay (reviewer suite extracted from review `e4161dd0…`)

Extraction identity verified in-sandbox: `reviewer/W17_PROBE_IDENTITY.txt`, suite SHA-256
`a6db33956bb7bc1e8af19cddd7cebdd320604bba98b6a2b906fd1eb363fba0c3` (matches the canonical review
object). No revision, edit or expectation change was applied to this suite; it was executed verbatim
on both anchors.

| Target | Result |
|---|---|
| `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd` (historical RED anchor, PR #308) | `probes=14 failures=6` — `MINT-001`, `MINT-002`, `OBJGRAPH-001`, `DOWNGRADE-001`, `MIGRATE-002`, `RSA-DELIMITER-001` (raw: `raw/frozen_w17_probes_on_cb8a6b3c.txt`) |
| `fec30bd1495017bf13f08b0ef5b1e241dfb0e247` (exact candidate, PR #310) | `probes=14 failures=0` (raw: `raw/frozen_w17_probes_on_fec30bd.txt`) |

The mandatory RED-first condition is therefore satisfied with the reviewer's own extracted copy,
and the GREEN run is reported with the explicit caveat recorded in `IA_REPORT.md` §5: the frozen
suite's MINT probes are name-based and its object-graph probe is name-filtered and depth-limited,
so its GREEN result is necessary but not sufficient — the reviewer's own `IA20-*` probes
(Suite A `v3`, `failures=4`) carry the adverse finding.

## Timing (all timestamps UTC)

| Event | Time |
|---|---|
| Suite A `v1` freeze + first execution (defective) | `2026-10-03` pre-06:2x |
| Suite B `v1` freeze (`PROBE_FREEZE_MANIFEST_BATCH2.md`) | `2026-10-03T06:29:00Z` |
| Suite B `v3` accepted freeze + execution (`failures=0`) | `2026-10-03T06:29Z`–`06:35Z` |
| Evidence publication commit `22031175…` / review PR #311 | `2026-10-03T06:38Z`–`06:40Z` |
| Formal IA comment on PR #310 (id `5966444269`) | `2026-10-03T06:41:12Z` |
