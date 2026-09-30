"""The durability layer must not change anything the Resident can observe.

This is the suite-level entry point for
``tools/c15_persistence/resident_surface_check.py``; the check itself runs in a
fresh interpreter so what is measured is the real production wiring, not an
in-process import of it.

Corrective-003 validation split
-------------------------------
``resident_surface_check`` returns a single ``result`` that is the conjunction of
two different kinds of constraint:

1. the twelve wired-vs-control **behavioural** comparisons, which are a genuine,
   generally applicable Resident-visible behaviour contract; and
2. a **historical scope tripwire** requiring ``git diff <base>...HEAD --
   src/aios_core`` to be empty, whose purpose is to prove that
   ``C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003`` itself did not modify Core.

Constraint 2 is *not* a general Core invariant: it is scoped to the Persistence
Corrective-003 construction range. A later, separately authorised Core change
(for example ``CORE-BACKGROUND-LATE-TRUSTED-RETURN-001``) legitimately makes it
report dirty, which says nothing about the Resident-visible surface.

Binding both together into one dynamic ``main...HEAD`` verdict therefore produces
a false negative for any legitimate Core work, while a shallow checkout in which
``main`` does not resolve produces a false *positive*, because the empty diff is
read as "clean". This module asserts the two constraints separately and
mechanically, so that neither mistake is possible:

* the twelve behavioural comparisons must be ``True`` (unchanged, never weakened);
* the two frozen Resident review trees must stay clean against the current base;
* the ``src/aios_core`` zero-diff must hold for the frozen Persistence
  Corrective-003 range, not for whatever ``HEAD`` happens to be today; and
* every ref the above depends on must actually resolve, so a shallow clone is
  reported as **skipped** rather than passing vacuously.

The checker tool and the committed historical evidence are read-only here.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "killpoints"))

from harness import REPO_ROOT, new_root, repo_python_env  # noqa: E402

# Corrective-003 evidence re-anchor: the committed artifact lives under this
# corrective's own evidence root instead of the frozen Corrective-001 WIP path.
EVIDENCE_DIR = REPO_ROOT / "reviews" / "C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_003" / "evidence"

# The twelve Resident-visible behavioural comparisons. This is the binding
# behaviour contract; it is asserted exhaustively and must never be weakened.
RESIDENT_BEHAVIOURAL_COMPARISONS = (
    "resident_visible_payload",
    "projection",
    "ingest_receipt",
    "capability_catalog",
    "model_round_ordering",
    "provider_request_bytes",
    "provider_reply_bytes",
    "directive_semantics",
    "capability_side_effect_count",
    "assistant_output",
    "metering_rows",
    "world_revision",
)

# Frozen Resident review trees. These must stay clean against the current base
# for any task; the Persistence Corrective-003 run did not own them and neither
# does a later Core corrective.
FROZEN_RESIDENT_REVIEW_TREES = (
    "reviews/internal_habitation/c15-rcc/v1",
    "reviews/internal_habitation/c14-resident/v2/release",
)

# The Core tree itself. Its zero-diff requirement belongs to Persistence
# Corrective-003's own accepted construction range, not to arbitrary HEAD.
CORE_SCOPE = "src/aios_core"

# Window 06 frozen identity of the Persistence Corrective-003 construction.
HISTORICAL_PERSISTENCE_BASE = "016a2f7db5ed01b41fc614701079c507d2c2c02e"
HISTORICAL_PERSISTENCE_CANDIDATE = "19476641be95e666068e6299f42df9a411f4c0ba"


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


def _require_full_history() -> None:
    """Skip, loudly and non-vacuously, when the checkout cannot support the diffs.

    A shallow checkout is the precise condition under which the original combined
    verdict lied: the base ref does not resolve, ``git diff`` returns empty
    output, and the tripwire reads "clean". Rather than fail every
    shallow-checkout job in the repository, this reports **skipped**, which is
    visibly not a pass, and names why the invariant was not evaluated.

    The formal gate for this window checks out full history (``fetch-depth: 0``)
    and separately asserts the repository is not shallow, so the invariant is
    genuinely enforced there rather than waived everywhere.
    """
    if _git("rev-parse", "--is-shallow-repository").stdout.strip() == "true":
        pytest.skip(
            "shallow checkout: the three-dot diffs this gate depends on cannot be "
            "evaluated, and an unresolvable base ref makes an empty diff read as "
            "'clean'. Skipped, NOT passed. The "
            "core-background-late-trusted-return-001 formal gate checks out full "
            "history (fetch-depth: 0) and fails the build if this repository is "
            "shallow, so the invariant is enforced there rather than waived."
        )


def _resolve_base(preferred: str) -> str:
    """Return a base ref that actually resolves in this checkout.

    A pull-request checkout commonly has no local ``main`` branch even with full
    history, so fall back to the remote-tracking ref before giving up.
    """
    for candidate in (preferred, f"origin/{preferred}", "origin/main", "main"):
        if _git("rev-parse", "--verify", f"{candidate}^{{commit}}").returncode == 0:
            return candidate
    return pytest.fail(
        f"no resolvable base ref for {preferred!r}; the resident-visible surface "
        "cannot be compared against anything"
    )


def _require_resolvable(ref: str, why: str) -> None:
    """Fail loudly when a ref is missing, so history gaps cannot pass vacuously.

    Only reached once full history is confirmed, so an unresolvable ref here is a
    genuine misconfiguration rather than an artefact of a shallow fetch.
    """
    completed = _git("rev-parse", "--verify", f"{ref}^{{commit}}")
    assert completed.returncode == 0, (
        f"git ref {ref!r} does not resolve, so {why} cannot be proven. "
        f"History looks complete, so this is a real configuration error. "
        f"git said: {completed.stderr.strip()!r}"
    )


def _scope_diff(base: str, ref: str, scope: str) -> str:
    return _git("diff", "--stat", f"{base}...{ref}", "--", scope).stdout.strip()


def test_historical_resident_surface_gate(tmp_path: Path) -> None:
    # The checked-in evidence file is produced by an explicit, logged invocation
    # of the checker so that the suite never rewrites reviewed evidence; this
    # test writes to a scratch path and asserts on that.
    base = os.environ.get("C15_SURFACE_BASE", "main")

    # -- 0. History precondition -------------------------------------------------
    # Asserted first so that an unevaluable checkout reports the real cause
    # instead of a downstream symptom. Shallow => skipped, not passed.
    _require_full_history()
    base = _resolve_base(base)
    _require_resolvable(base, "the current-base Resident review tree comparison")
    _require_resolvable(
        HISTORICAL_PERSISTENCE_BASE,
        "the historical Persistence Corrective-003 scope comparison",
    )
    _require_resolvable(
        HISTORICAL_PERSISTENCE_CANDIDATE,
        "the historical Persistence Corrective-003 scope comparison",
    )

    out = tmp_path / "resident-surface-no-change.json"
    work_root = new_root("resident-surface")
    env = dict(repo_python_env())
    env["C15_SURFACE_BASE"] = base
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.c15_persistence.resident_surface_check",
            "--out",
            str(out),
            "--base",
            base,
            "--work-root",
            str(work_root / "runs"),
        ],
        capture_output=True,
        text=True,
        timeout=900,
        cwd=str(REPO_ROOT),
        env=env,
    )

    # The checker must always emit parseable evidence, whatever its verdict, so
    # the two constraints can be adjudicated separately below.
    assert out.is_file(), (
        "resident surface check produced no evidence file:\\n"
        f"stdout: {completed.stdout}\\nstderr: {completed.stderr}"
    )
    evidence = json.loads(out.read_text())

    # -- 1. Behavioural contract (binding, exhaustive) --------------------------
    comparisons = evidence["comparisons"]
    missing = [name for name in RESIDENT_BEHAVIOURAL_COMPARISONS if name not in comparisons]
    assert not missing, f"checker stopped reporting required comparisons: {missing}"
    for name in RESIDENT_BEHAVIOURAL_COMPARISONS:
        assert comparisons[name] is True, f"resident-visible surface differs: {name}"

    # -- 2. The audit is only meaningful if the surface was actually exercised --
    assert len(evidence["control"]["calls"]) >= 2, evidence["control"]["calls"]
    assert evidence["control"]["catalog"], "empty capability catalog"

    # -- 3. Frozen Resident review trees must stay clean -----------------------
    for scope in FROZEN_RESIDENT_REVIEW_TREES:
        detail = evidence["pinned_tree_diff_vs_base"][scope]
        assert detail["clean"] is True, f"{scope} was modified: {detail['diff']}"
        # Re-derived independently so the checker's own report cannot be the only
        # source of the verdict.
        assert _scope_diff(base, "HEAD", scope) == "", (
            f"{scope} differs from {base}, confirmed independently of the checker"
        )

    # -- 4. Historical Persistence Corrective-003 scope gate -------------------
    # The real invariant: that corrective changed no Core code. Bound to its own
    # frozen construction range rather than to today's HEAD.
    historical_core_diff = _scope_diff(
        HISTORICAL_PERSISTENCE_BASE, HISTORICAL_PERSISTENCE_CANDIDATE, CORE_SCOPE
    )
    assert historical_core_diff == "", (
        "Persistence Corrective-003 modified Core, which its construction scope "
        f"forbids: {historical_core_diff}"
    )

    # -- 5. Adjudicate the checker's combined verdict ---------------------------
    # A non-zero exit is tolerated only when its single cause is the Core change
    # this repository's current work is explicitly authorised to make. Any other
    # dirty scope, or any behavioural difference, is a real failure.
    current_core_diff = _scope_diff(base, "HEAD", CORE_SCOPE)
    reported_core = evidence["pinned_tree_diff_vs_base"][CORE_SCOPE]
    assert (reported_core["clean"] is True) == (current_core_diff == ""), (
        "checker and this test disagree about the current Core diff: "
        f"checker clean={reported_core['clean']}, "
        f"independent diff={current_core_diff!r}"
    )

    if current_core_diff == "":
        # No authorised Core change in flight: the combined verdict must hold.
        assert completed.returncode == 0, (
            "resident surface check failed with no Core diff to explain it:\\n"
            f"stdout: {completed.stdout}\\nstderr: {completed.stderr}"
        )
        assert evidence["result"] == "RESIDENT_SURFACE_UNCHANGED", evidence["comparisons"]
    else:
        # An authorised Core change is in flight. The tripwire is expected to be
        # dirty; assert the *only* dirty scope is the Core tree and that the
        # behavioural half is still fully green, then classify it explicitly
        # rather than letting it surface as a behavioural red.
        assert evidence["result"] == "RESIDENT_SURFACE_CHANGED", evidence
        assert completed.returncode != 0, "checker should report the Core scope tripwire"
        dirty = [
            scope
            for scope, detail in evidence["pinned_tree_diff_vs_base"].items()
            if isinstance(detail, dict) and not detail["clean"]
        ]
        assert dirty == [CORE_SCOPE], (
            "resident-surface scope tripwire is dirty for a reason beyond the "
            f"authorised Core change: {dirty}"
        )

    # -- 6. Committed historical evidence is read-only and unchanged ------------
    committed = EVIDENCE_DIR / "resident-surface-no-change.json"
    assert committed.is_file(), f"missing committed evidence: {committed}"
    assert json.loads(committed.read_text())["result"] == "RESIDENT_SURFACE_UNCHANGED"
