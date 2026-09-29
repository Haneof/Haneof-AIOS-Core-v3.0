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
