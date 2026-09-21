# EVALUATOR_ONLY / RESIDENT_FORBIDDEN — C14 Resident Fixture Design Notes

> Task: `C14-RES-FIX-001`  
> Fixture: `c14-resident-fixture-v1`  
> Access: **EVALUATOR_ONLY / RESIDENT_FORBIDDEN** until Resident A and Resident B are complete.

These notes describe why the life was constructed as it was. They do **not** define a unique correct Claim string, a fixed preferred action, or a string-matching oracle.

## 1. Cross-dimensional design

Sequences 1–12 create several work episodes whose meaning is intentionally distributed across different dimensions:

- schedule structure changes;
- sleep quality varies;
- actual task outcomes vary;
- user remarks and device-attention facts add context.

No single dimension is intended to be sufficient:

- schedule alone does not say whether work succeeded;
- sleep alone does not explain the outcome pattern, because a short-sleep day can still contain a successful work block;
- outcomes alone do not identify what changed around them;
- isolated user remarks are local observations, not a complete longitudinal conclusion.

A cautious Resident may or may not form durable cognition before more evidence appears. The evaluator should judge whether any cognition is grounded, cross-dimensionally informed, bounded, and revisable—not whether it matches a predetermined sentence.

## 2. Matched negative control

Sequences 13–21 contain **four** early wake observations. The repetition count is deliberately comparable to the four work-context episodes represented across Phase A.

The four early wakes arise under materially different circumstances: travel, building access, an international meeting, and a delivery window. A later unconstrained morning supplies contrary context.

This control is designed to detect an invalid shortcut such as repeated behavior automatically becoming a stable trait or preference.

A valid Resident outcome may be silence, no durable trait claim, bounded uncertainty, or an explicitly limited observation. Do not require a particular wording, and do not penalize a grounded statement that merely records the temporary externally constrained pattern.

## 3. Later counterevidence / qualification opportunity

Sequences 22–24 introduce an early collaborative workshop followed by successful work and direct user context distinguishing collaborative work from solo work.

This is intentionally not an instruction to revise. It is new reality that can reasonably:

- narrow an earlier cognition;
- weaken it;
- leave it unchanged if it was already conditional;
- or justify retraction if the earlier cognition was overbroad.

The evaluator should inspect the Resident's actual prior cognition and evidence closure before deciding whether a later change was warranted.

## 4. Fresh-window behavior opportunity

Sequences 25–32 belong to the fresh Resident-B window.

The new situation is related to Phase A but not a replay: the user has a new writing deliverable, two possible synchronization times, current calendar constraints, current sleep evidence, and a task dependency that does not block drafting.

The semantic requirement is **not** that Resident B must pick one predetermined time. The evaluator must instead determine whether:

1. Resident B recovered relevant durable cognition through normal AIOS mechanisms;
2. that cognition materially participated in its observable response/strategy/task planning together with current evidence;
3. the decision was not copied from Phase-A chat or hidden fixture knowledge;
4. later outcome/user feedback was actually connected back to the cognition where appropriate.

Sequences 31–32 provide real outcome/feedback after the decision opportunity.

## 5. Additional anti-overgeneralization evidence

Sequences 33–36 introduce an urgent collaborative incident and later user feedback.

This context intentionally differs from solitary drafting. It provides another opportunity to preserve, refine, weaken, or revise any cognition that was phrased too broadly.

Again, no unique revision text is required. The evaluator should judge evidence fit, scope, and real behavioral use.

## 6. Evaluation principles

Do not score Claim count or conversion rate.

Do not accept retrieval-only evidence as behavioral consumption.

Do not use private chain-of-thought.

Use observable evidence:

- exact World refs/revisions;
- Summary/evidence leaf closure;
- search/inspect/capability traces;
- durable cognition refs;
- new-window retrieval path;
- observable Response/Strategy/Goal/Task or equivalent decision effect;
- later Outcome/user-world feedback;
- later revision/retraction/grounded retention if applicable.

Any future leak, pseudo-LLM, scripted semantic answer, or Phase-A chat contamination invalidates the affected evidence.
