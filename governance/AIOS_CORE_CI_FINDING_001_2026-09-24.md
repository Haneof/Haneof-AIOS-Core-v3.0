# CI Finding 001 — two mechanical gates fail for an infrastructure reason, not a policy violation

Date: 2026-09-24
Raised by: Core Delivery PM (integrating PM window)
Class: release / CI infrastructure defect. **Not** a Core semantic gap, **not** a new `CG-` audit item.
Status: OPEN → dispatched as `CORE-CI-FIX-001`

## 1. Observation

`c15-rcc-fixture-mechanical-gate` and `semantic-repair-mechanical-gate` reported **failure** on the documentation-only governance PRs #138 and #139.

Failing steps:

| Workflow | Failing step |
|---|---|
| `.github/workflows/c15-rcc-fixture.yml` | `Prove fixture task has zero Core diff` |
| `.github/workflows/c14-semantic-repair-fixture.yml` | `Prove fixture task did not modify Core or historical C14 evidence` |

Every preceding step in both jobs succeeded, including the actual mechanical gates, sealed-fixture SHA256 proofs and the regression suites.

## 2. Root cause

Both failing steps run:

```
git fetch origin main --depth=1
changed="$(git diff --name-only origin/main...HEAD)"
```

The three-dot form requires a merge base between `origin/main` and `HEAD`. With `actions/checkout` at its default shallow depth plus a `--depth=1` fetch of `main`, no common ancestor is present in the local object store, so **git itself fails**.

Evidence that this is a git failure rather than a policy rejection:

- the job annotation is `failure: Process completed with exit code 128` — git's fatal-error code;
- a real policy violation in these steps `echo`es an explicit message and exits `1`, which did not happen;
- the outcome depends on branch shape, not on content: the same two gates **failed** on PR #133 head `e812184c` and **succeeded** on PR #137 head `2619143f`, whose single commit happened to fall inside the shallow window.

## 3. Independent proof that the asserted invariant actually holds

The invariant these steps exist to protect is "this change must not modify `src/aios_core/**`". The PM verified that invariant directly instead of relying on the broken gate:

- `git diff --name-only e72a63874ed2c28798b00cec51f191caf1594a00 <current main>` lists only `AIOS_v3.0_CURRENT_CHECKPOINT.md`, `PROJECT_MASTER_MAP.md`, and five `governance/**` files;
- `git diff --stat e72a638 <current main> -- src/` is **empty**;
- `src/aios_core` tree on main is still `7db4f72e7b3c29c74082f9984141159f8f1d6071`, unchanged since `CORE-GAP-AUDIT-001` audited it.

So the merges of #138 and #139 did not violate the rule the red gates were meant to enforce.

## 4. PM ruling

1. The two red checks on #138 / #139 are recorded as **INFRASTRUCTURE_FAILURE**, not as accepted policy violations and not as passing gates. They are not marked green anywhere.
2. Merging those two documentation-only PRs with these checks red was a PM decision made on the direct evidence in §3. The checks are not branch-protection-required; nothing was bypassed or overridden.
3. This finding does **not** authorize ignoring these gates in future. Any PR that touches `src/aios_core/**` must not rely on this finding.
4. The defect is dispatched as `CORE-CI-FIX-001` (below). It does not block `CORE-GAP-FIX-001` / `-002`, but it **must be closed before `CORE-RC-FREEZE-001`**, because RC freeze requires a trustworthy full-gate story and a gate that fails for shape-dependent reasons cannot support a release verdict.
5. No historical red/green result is rewritten. PR #133's historical failure of these same gates stays as-is.

## 5. Dispatched task

`CORE-CI-FIX-001` — Release / CI Infrastructure Engineer, one window, independent acceptance by a different window.

Prompt: `governance/prompts/CORE_CI_FIX_001_2026-09-24.md`
State: READY / NOT_STARTED
Blocks: `CORE-RC-FREEZE-001`
Does not block: `CORE-GAP-FIX-001`, `CORE-GAP-FIX-002`
