# AIOS v3.0 P16 Convergence Control

> Status: ACTIVE
> Effective: 2026-09-20
> Scope: P16 multi-model long-horizon habitation through P17 entry
> Integration truth: `main`

## 1. Single active construction surface

From this control point forward, AIOS Core has one active engineering objective:

`P16 provider-backed real-model habitation`

No agent may restart or redesign P12/P13/P14/P15/C09/P16 harness foundations unless a new reproducible blocker is first demonstrated against current `main`.

P17 MUST NOT start until provider-backed runs and evaluator-only review produce auditable evidence.

## 2. Branch disposition

### A. Historical merged evidence — freeze, do not continue

- `p14/long-conversation-continuity-20260920` — merged via PR #4
- `hardening/p13-reality-ingest-20260920` — merged via PR #3
- `parallel/p16-habitation-harness-20260920` — merged via PR #1
- `fix/p16-c09-wake-bus-dispatch-v2-20260920` — merged via PR #7
- `fix/c09-dedupe-identity-hardening-20260920` — merged via PR #9
- `fix/p16-long-horizon-habitation-hardening-20260920` — merged via PR #10

Squash-merged branches may still appear ahead/diverged in Git history. That is NOT evidence that their old branch should be merged again.

### B. Closed/superseded/experimental evidence — freeze, never merge directly

- `parallel/p13-external-fact-ingest-20260920` — superseded, PR #2 closed
- `experiment/p16-self-resident-blind-replay-20260920` — experiment only, PR #5 closed
- `fix/p16-c09-wake-bus-dispatch-20260920` — stale baseline, PR #6 closed
- `verify/c09-main-postmerge-20260920` — verification-only, PR #8 closed

### C. Diverged unmerged branches — quarantine pending audit

- `p15/periodic-review-growth-20260920`
- `p16/habitation-integration-20260920`
- `hardening/p15-review-growth-redteam-20260920`

Rules for quarantined branches:

1. Do not merge, rebase, force-update, or resume feature development on them.
2. They may be read only to recover a specific missing test, invariant, or defect finding.
3. Any recovered item must be re-implemented from current `main`, not merged wholesale.
4. Recovery requires proof that current `main` does not already contain equivalent behavior.

## 3. Current verified anchor

- Last verified functional anchor: `1fc7b9f5c69b01f01dac8097efd29973bc4dbf4c`
- P16 merge-result Gate: `35503797730` / SUCCESS
- C09 dedupe hardening Gate: `35501301595` / SUCCESS
- Current blocker: no provider-backed GPT / Claude / Gemini-style resident model has yet completed an auditable habitation run.

## 4. Only allowed next implementation

The next implementation branch must start from current `main` and must be limited to:

- provider-backed `ModelHandler`;
- provider-backed `RoundSummaryHandler`;
- model/provider/run provenance;
- deterministic configuration capture;
- auditable run artifacts;
- retry/error classification that does not fake successful cognition;
- sealed resident/oracle separation;
- executing multiple real models independently against the same resident-visible life.

It MUST NOT introduce:

- a second WorldStore;
- a second Index;
- a second CognitiveRuntime;
- benchmark-specific cognition;
- expected answers in resident-visible input;
- keyword/rule logic that substitutes for model cognition;
- provider-specific semantics inside Core world contracts.

## 5. P16 exit evidence

P16 may be declared complete only when all of the following exist:

1. At least two real provider/model configurations run independently through the same sealed scenario bundle.
2. Each candidate receives a fresh private World.
3. Resident-visible input fingerprints are equal for equivalent lives.
4. Provider/model/config/version/timestamps/errors/tool calls are captured in run provenance.
5. Hidden oracle is inaccessible during residence and loaded only by evaluator.
6. Raw run artifacts are retained for independent review.
7. Evaluator reports cognition failures as failures; harness correctness is not treated as cognition success.
8. A red-team pass checks memory misuse, false cognition, revision behavior, summary misuse, meaningless dimension creation, and unsupported experience claims.

## 6. Authority

This file controls construction scope only. It does not amend constitutional semantics.

If this file conflicts with `docs/constitution/AIOS_v3.0_Fused_Baseline_Registry.md`, the fused baseline controls.
