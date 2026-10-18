# C15 RCC Anchor Reconciliation 2026-09-23

## Status

BLOCKED — canonical Resident A evidence acceptance pending anchor provenance resolution.

## Canonical frozen anchor

The only approved C15 cognition hardening release anchor is:

```
bcd6bf353126318f9a97076b52ec1740d43f35a4
```

All canonical Resident A/B/C/EVAL executions must bind to this frozen anchor.

## Current evidence package issue

PR #117 (`C15-RCC-RES-A-RERUN-001-CANONICAL`) is an evidence-only package and remains OPEN/UNMERGED/PINNED.

The package manifest declares:

```
anchor_commit: 30e0dca1f08c49ed9bacc66b49313ac536d512af
```

This SHA has not yet been proven as an equivalent Git execution anchor for the frozen C15 release baseline.

## Required resolution

One of the following must occur:

### Path A — Provenance confirmation

Demonstrate that the declared runtime anchor is only a metadata/reference mismatch and that the actual execution occurred on the frozen C15 semantics.

Required evidence:

- Git ancestry relationship;
- runtime Core SHA;
- no cognition/runtime semantic changes after frozen anchor.

### Path B — Evidence regeneration

If the runtime anchor cannot be proven equivalent, generate a new canonical evidence package bound explicitly to:

```
bcd6bf353126318f9a97076b52ec1740d43f35a4
```

## Restrictions until resolution

Do not:

- merge PR #117 as canonical evidence;
- start Resident B;
- create additional C15 execution anchors;
- modify Resident World artifacts.

## Future release rule

Canonical execution evidence must contain:

```
artifact_anchor_sha == frozen_release_anchor_sha
```

Any mismatch is automatically NON-CANONICAL until reconciled.
