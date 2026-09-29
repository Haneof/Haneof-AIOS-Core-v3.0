# C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-003 — Independent Acceptance (review-only)

**REVIEW-ONLY / EVIDENCE-ONLY / DO NOT MERGE.**
This directory is an Independent Acceptance review artifact. It is not an implementation change,
not a Resident authorization, and not a PM integration.

- Task: `C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-003-INDEPENDENT-ACCEPTANCE`
- Role: Independent Resident Launch Infrastructure Acceptance Reviewer
- Candidate: PR #292, final freeze H2 `42a63ed4416585fc0a02045e0bd5190f32a01a2b`
- Not: author, prior corrective author, Resident A/B/C, PM, Core engineer, semantic evaluator
- No real Resident was run. All execution state is disposable and synthetic.

## Frozen reviewer probes (declared before execution)

The reviewer probe suite is authored independently of the candidate's own C10/C11 probes and was
hashed and committed **before the first adversarial execution against the candidate**:

- `probes/REVIEWER_PROBE_FREEZE.json` — suite identity, candidate pins, per-probe expected outcome
  and invariant, blocker decision rules.
- `probes/reviewer_probe_collection.txt` — frozen enumeration, 48 probe node IDs.
- `probes/*.py` — probe sources (hash list inside the freeze file).

Frozen identity (recomputed from these files):

| Artifact | SHA-256 |
| --- | --- |
| probe source hash list | `778d48e0e6cf9e0c6c04057eab1684e5d4dd0d4b22e621611cf1e0a9b060ae2f` |
| probe enumeration (48 IDs) | `cc2d805c22a6ffc2683252d6a1b5183d53fceec81275e4f35d0b88be5ae9fab1` |

### Revision 2 (corrected) — see `REVISION_NOTES_v2.md`

Revision 1 executed against the candidate: **39 passed / 9 failed**
(`raw/reviewer_probes_v1.raw.txt`, sha `18cdf362cb5e5ac09bf240071851ca13fa86cef013ee1a6a6522b495133f064b`). All nine failures were triaged to probe or
execution-method defects (table in `REVISION_NOTES_v2.md`); no candidate defect was
concluded from them. Revision 1 sources, freeze and raw results are preserved unchanged.

- `probes_v2/REVIEWER_PROBE_FREEZE_v2.json` — revision-2 identity, execution method
  (reviewer runtime, `-o pythonpath=`, cwd outside the product repository), per-probe
  expected outcome, lineage to revision 1.
- `probes_v2/reviewer_probe_collection_v2.txt` — frozen enumeration, 49 probe node IDs.
- Revision-2 result: **49 passed / 0 failed, rc=0, 154.31 s**
  (`raw/reviewer_probes_v2.raw.txt`; enumeration diff empty; no post-run source change,
  `raw/reviewer_probes_v2_integrity.json`).

| Revision | Probe sources SHA-256 | Enumeration SHA-256 | Result |
| --- | --- | --- | --- |
| 1 (`probes/`) | `778d48e0e6cf9e0c6c04057eab1684e5d4dd0d4b22e621611cf1e0a9b060ae2f` | `cc2d805c22a6ffc2683252d6a1b5183d53fceec81275e4f35d0b88be5ae9fab1` | 39/48 passed |
| 2 (`probes_v2/`) | `a4e8b0e58b9636ba4e41124507da39c2c235b58761111d0c1e4a12ac1f22f47d` | `83d2ab281d6e046e9175437e087f624434d6f5de1d1dc80559b0ec69958d4231` | 49/49 passed |
| 3 (`probes_v3/`, final) | `0d299c288169e27a9068c15e9cbd3a2e8da372f6c815e640b84695c235c1db29` | `fdad15300e65e069eea365dfdd3af8e3a2f0a3fe3fdc2d43ef5ddef440730ad9` | **50/50 passed** |

Revision 3 adds one probe (§7(c) stale-prefix identity outside the lock) and changes no
revision-2 expectation; `REVISION_NOTES_v3.md` records the freeze/commit ordering for all
revisions transparently.

Rules honored in this review:

1. Expectations were frozen before observing any candidate behavior; no expectation was tuned after
   results were seen.
2. A defective probe is corrected only by publishing a new revision while preserving the previous
   revision, its hash and its raw results.
3. The candidate's own C1–C11 suites and gates are regression evidence only; they do not substitute
   for these probes.
4. The author runtime (`/home/user/.cache/c003/final-runtime-001`) is not used as acceptance
   evidence. A separate reviewer runtime is built from a fresh, absent scratch root.

## Method

- `probes/` — reviewer probe sources and frozen expectations.
- `env/` — independently built reviewer runtime evidence (pins, wheel hashes, interpreter).
- `raw/` — raw outputs of every execution tier (probe tier, regression tier, gate tier).
- `REPORT.md` — formal Independent Acceptance report and verdict.
- `REVIEW_SHA256SUMS` — self-excluding checksum listing of this review directory.
