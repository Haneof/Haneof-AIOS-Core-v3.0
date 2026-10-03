# Window 20 — Candidate Identity & Lineage (`CANDIDATE_IDENTITY.md`)

```text
reviewed_exact_candidate   fec30bd1495017bf13f08b0ef5b1e241dfb0e247
candidate_parent           7db79da54b26266c5ec519f3e70dd25dff4a95fb
candidate_tree             42708fdeb51b27a01358c9dc8e29482b01acd8e4
construction_base          ca47087fb68c90d6ac380c11143a0e36e80fc04a   (= fresh live main)
carry_forward_commit       f088ce1067f412313a8e7fd85f37a2d7363b392e
head_branch                arena/01a10010-haneof-aios-core-v3-0
remote_branch_tip_at_review fec30bd1495017bf13f08b0ef5b1e241dfb0e247   (no drift)
pr                         #310  OPEN / UNMERGED / DO NOT MERGE
```

## Evidence-only final commit proof

`git rev-list --count 7db79da5…..fec30bd1… == 1`.

That single commit (`fec30bd1`, `docs(reviews): publish Corrective-002 evidence
package at the CI-validated code head`) touches exactly:

```text
A  reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_002/FINAL_HANDOFF.md
A  reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_002/FORMAL_CI_RESULTS.md
M  reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_002/SCOPE_MANIFEST.md
```

Subtree hash equality across `7db79da5 → fec30bd1` (byte-identical, no
implementation or test byte changed):

```text
src      8215987192cee9d5cffd7ed8d53e6051682e32e8   (both)
tests    1d69b9076591f209badfbc73aea8900261797322   (both)
.github  7220a4b67b4e06c4592c2e3f8e102949dc3589ab   (both)
```

→ The formal CI result on `fec30bd…` therefore also covers the exact
`src/**`/`tests/**`/`.github/**` bytes reviewed here; `7db79da5` is the
CI-validated code head and `fec30bd1` is the evidence-only final head.

## Historical anchors

```text
window17_failed_candidate  cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd   (PR #308)
window17_failed_tree       a762df979826d3a599b93d937c53b633d0cb8466
window17_canonical_review  e4161dd0ad0a2f825461311a1c8c5ff8234a07f8   (sole parent cb8a6b3c…)
window14_failed_candidate  5ad0524c425592210ff184e00ad52abb2c14e366   (PR #305; used by the formal red-first job)
window14_canonical_review  84457badc562416f59fb25ca41103700276e0df2
```

All values above were re-derived in this window from live git objects and the
GitHub API; none were inherited from the Window 19 handoff.
