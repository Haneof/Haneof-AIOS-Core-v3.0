# Window 28 late TOCTOU GREEN control branch advance

This tracked evidence commit intentionally advances the canonical Corrective-002 branch while old formal run `37267746540` is inside the whole-run cancellation propagation guard, after:

- Job A / `rc004-freeze-gate` completed SUCCESS;
- Job B / `rc004-mandatory-pin-publisher` completed SUCCESS;
- Job C / `Pre-seal fresh canonical identity` completed SUCCESS.

Purpose: mechanically test that a post-publication, post-pre-seal branch drift cannot leave the stale old run authoritative SUCCESS.

The resulting old-run conclusion and successor-run identity are recorded in `REAL_GITHUB_TOCTOU_CONTROL.md` before final candidate freeze.
