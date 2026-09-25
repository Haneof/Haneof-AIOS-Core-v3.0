#!/usr/bin/env python3
"""Cross-document Phase-B lifecycle gate.

Production entrypoint and mutation self-test both call check_runbook_lifecycle().
The self-test writes disposable copies and invokes that same function; it does not
reimplement the comparison.

A planted token block is not sufficient. Each active runbook must also expose the
same tokens on its operational step headings, the same executable-anchor order, and
no fenced/arrow chain that creates the binding receipt before current-event.json.
"""
from __future__ import annotations

import argparse
import re
import shutil
import tempfile
from pathlib import Path

# Exact mechanical sequence required by CORRECTIVE-011. Step "finish all cursor
# model work" stays inside this sequence as required prose between MODEL_WORK and
# DURABLE_ACK; it is not a second independent token that could diverge.
EXPECTED_TOKENS = (
    "REVEAL",
    "INSTALL_CURRENT_EVENT",
    "PERSIST_PROJECTION_EVIDENCE",
    "CREATE_BINDING_RECEIPT",
    "VERIFY_BINDING",
    "DERIVE_OCCURRED_AT",
    "INGEST",
    "MODEL_WORK",
    "DURABLE_ACK",
    "CLEAR_BINDING",
    "NEXT_REVEAL",
)
START = "<!-- C15_PHASE_B_LIFECYCLE_BEGIN -->"
END = "<!-- C15_PHASE_B_LIFECYCLE_END -->"
DOC_RELS = (
    Path("procedure/b_startup_procedure.md"),
    Path("procedure/per_cursor_interaction.md"),
)
_TOKEN_ALT = "|".join(EXPECTED_TOKENS)
HEADING_RE = re.compile(rf"^###\s+(?:7\.)?\d+\.?\s+({_TOKEN_ALT})\b", re.M)
STEP_HEADING_RE = re.compile(rf"^###\s+(?:7\.)?\d+\.?\s+({_TOKEN_ALT})\b.*$", re.M)
ANCHORS = (
    ("REVEAL", "reveal --phase B"),
    ("INSTALL_CURRENT_EVENT", 'install -m 0400 "$RUN_ROOT/reveal.json" "$RUN_ROOT/current-event.json"'),
    ("PERSIST_PROJECTION_EVIDENCE", ".projection.json"),
    ("CREATE_BINDING_RECEIPT", "write_binding_receipt"),
    ("VERIFY_BINDING", "validate_current_event_binding"),
    ("DERIVE_OCCURRED_AT", 'CURRENT_OCCURRED_AT="'),
    ("INGEST", "canonical_conversation_ingest.py"),
    ("MODEL_WORK", "turn --session"),
    ("DURABLE_ACK", "ack --phase B"),
    ("CLEAR_BINDING", 'rm -f "$RUN_ROOT/current-event.json"'),
)
FINISH_CLAUSE = "Do not ACK until"
_CURRENT_EVENT_JSON = re.compile(r"current-event\.json")
_RECEIPT_NEEDLES = ("create_current_event_binding_receipt", "write_binding_receipt")


class LifecycleCheckError(RuntimeError):
    pass


def extract_token_block(name: str, text: str) -> tuple[str, ...]:
    if text.count(START) != 1 or text.count(END) != 1:
        raise LifecycleCheckError(
            f"{name}: expected exactly one lifecycle token block, "
            f"got begin={text.count(START)} end={text.count(END)}"
        )
    body = text.split(START, 1)[1].split(END, 1)[0]
    tokens = tuple(line.strip() for line in body.splitlines() if line.strip())
    if tokens != EXPECTED_TOKENS:
        raise LifecycleCheckError(
            f"{name}: token block differs: got={tokens!r} expected={EXPECTED_TOKENS!r}"
        )
    if len(tokens) != len(set(tokens)):
        raise LifecycleCheckError(f"{name}: duplicate token in lifecycle block: {tokens!r}")
    return tokens


def extract_heading_tokens(name: str, text: str) -> tuple[str, ...]:
    tokens = tuple(HEADING_RE.findall(text))
    if tokens != EXPECTED_TOKENS:
        raise LifecycleCheckError(
            f"{name}: operational heading tokens differ: got={tokens!r} expected={EXPECTED_TOKENS!r}"
        )
    return tokens


def _step_spans(text: str) -> list[tuple[str, int, int]]:
    matches = list(STEP_HEADING_RE.finditer(text))
    if not matches:
        return []
    spans: list[tuple[str, int, int]] = []
    for i, match in enumerate(matches):
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            tail = text[match.end():]
            cut = re.search(r"\n## ", tail)
            end = match.end() + cut.start() + 1 if cut else len(text)
        spans.append((match.group(1), match.start(), end))
    return spans


def _step_region(name: str, text: str) -> str:
    spans = _step_spans(text)
    if [tok for tok, _, _ in spans] != list(EXPECTED_TOKENS):
        raise LifecycleCheckError(f"{name}: cannot isolate operational step region")
    return text[spans[0][1]:spans[-1][2]]


def assert_anchor_order(name: str, text: str) -> None:
    region = _step_region(name, text)
    positions: list[tuple[str, int]] = []
    for token, needle in ANCHORS:
        idx = region.find(needle)
        if idx < 0:
            raise LifecycleCheckError(f"{name}: missing executable anchor {token}: {needle!r}")
        positions.append((token, idx))
    indexes = [idx for _, idx in positions]
    if indexes != sorted(indexes) or len(set(indexes)) != len(indexes):
        raise LifecycleCheckError(
            f"{name}: executable anchors reordered or collapsed: {positions!r}"
        )
    by_token = dict(positions)
    if not (
        by_token["REVEAL"]
        < by_token["INSTALL_CURRENT_EVENT"]
        < by_token["PERSIST_PROJECTION_EVIDENCE"]
        < by_token["CREATE_BINDING_RECEIPT"]
        < by_token["VERIFY_BINDING"]
        < by_token["DERIVE_OCCURRED_AT"]
        < by_token["INGEST"]
        < by_token["MODEL_WORK"]
        < by_token["DURABLE_ACK"]
        < by_token["CLEAR_BINDING"]
    ):
        raise LifecycleCheckError(f"{name}: executable lifecycle order is not canonical")


def assert_finish_clause(name: str, text: str) -> None:
    spans = {tok: (start, end) for tok, start, end in _step_spans(text)}
    model_start = spans["MODEL_WORK"][0]
    ack_start = spans["DURABLE_ACK"][0]
    between = text[model_start:ack_start]
    if FINISH_CLAUSE not in between:
        raise LifecycleCheckError(
            f"{name}: missing finish-all-cursor-model-work clause between MODEL_WORK and DURABLE_ACK"
        )


def _current_event_positions(body: str) -> list[int]:
    positions = []
    for match in _CURRENT_EVENT_JSON.finditer(body):
        if body.startswith("current-event-binding.json", match.start()):
            continue
        positions.append(match.start())
    return positions


def _receipt_positions(body: str) -> list[int]:
    positions = []
    for needle in _RECEIPT_NEEDLES:
        start = 0
        while True:
            idx = body.find(needle, start)
            if idx < 0:
                break
            positions.append(idx)
            start = idx + len(needle)
    return positions


def _reversed_receipt_before_event(body: str) -> bool:
    events = _current_event_positions(body)
    receipts = _receipt_positions(body)
    if not events or not receipts:
        return False
    return min(receipts) < min(events)


def _fence_bodies(text: str) -> list[str]:
    return text.split("```")[1::2]


def assert_no_receipt_before_current_event(name: str, text: str) -> None:
    blocks = list(_fence_bodies(text))
    chain = "\n".join(line for line in text.splitlines() if "→" in line)
    if chain:
        blocks.append(chain)
    for body in blocks:
        if _reversed_receipt_before_event(body):
            raise LifecycleCheckError(
                f"{name}: operational chain places binding-receipt creation before current-event.json"
            )


def check_one(name: str, text: str) -> tuple[str, ...]:
    tokens = extract_token_block(name, text)
    headings = extract_heading_tokens(name, text)
    if tokens != headings:
        raise LifecycleCheckError(
            f"{name}: token block and operational headings diverge: {tokens!r} != {headings!r}"
        )
    assert_anchor_order(name, text)
    assert_finish_clause(name, text)
    assert_no_receipt_before_current_event(name, text)
    if "b_startup_procedure.md §7" not in text and "b_startup_procedure.md §7" not in text.replace("`", ""):
        raise LifecycleCheckError(f"{name}: missing startup §7 authority reference")
    return tokens


def read_docs(base: Path) -> dict[Path, str]:
    docs: dict[Path, str] = {}
    for rel in DOC_RELS:
        path = base / rel
        if not path.is_file():
            raise LifecycleCheckError(f"missing lifecycle document: {path}")
        docs[rel] = path.read_text(encoding="utf-8")
    return docs


def check_runbook_lifecycle_texts(docs: dict[Path, str]) -> tuple[str, ...]:
    tokens = []
    for rel in DOC_RELS:
        if rel not in docs:
            raise LifecycleCheckError(f"missing lifecycle document text: {rel}")
        tokens.append(check_one(str(rel), docs[rel]))
    if tokens[0] != tokens[1]:
        raise LifecycleCheckError(
            f"cross-document lifecycle mismatch: {tokens[0]!r} != {tokens[1]!r}"
        )
    return tokens[0]


def check_runbook_lifecycle(base: Path) -> tuple[str, ...]:
    """Production gate entrypoint. Mutation self-tests must call this function."""
    return check_runbook_lifecycle_texts(read_docs(base))


def _stage(base: Path, dest: Path, overrides: dict[Path, str] | None = None) -> None:
    overrides = overrides or {}
    for rel in DOC_RELS:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if rel in overrides:
            target.write_text(overrides[rel], encoding="utf-8")
        else:
            shutil.copyfile(base / rel, target)


def _replace_token_block(text: str, tokens: tuple[str, ...]) -> str:
    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    body = "\n" + "\n".join(tokens) + "\n"
    return before + START + body + END + after


def _swap_steps(text: str, token_a: str, token_b: str) -> str:
    spans = {tok: (start, end) for tok, start, end in _step_spans(text)}
    if token_a not in spans or token_b not in spans:
        raise AssertionError(f"cannot swap missing steps {token_a}/{token_b}")
    a0, a1 = spans[token_a]
    b0, b1 = spans[token_b]
    if a0 > b0:
        a0, a1, b0, b1 = b0, b1, a0, a1
    return text[:a0] + text[b0:b1] + text[a1:b0] + text[a0:a1] + text[b1:]


def _expect_red(label: str, base: Path) -> None:
    try:
        check_runbook_lifecycle(base)
    except LifecycleCheckError as exc:
        print(f"RUNBOOK_LIFECYCLE_MUTATION_RED_PASS {label} via=check_runbook_lifecycle: {exc}")
        return
    raise AssertionError(f"lifecycle mutation false-green: {label}")


def run_mutation_self_tests(base: Path) -> int:
    check_runbook_lifecycle(base)
    docs = read_docs(base)
    rel = Path("procedure/per_cursor_interaction.md")
    original = docs[rel]
    count = 0
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)

        swapped = _swap_steps(original, "INSTALL_CURRENT_EVENT", "CREATE_BINDING_RECEIPT")
        if START not in swapped or swapped.split(START, 1)[1].split(END, 1)[0] != original.split(START, 1)[1].split(END, 1)[0]:
            raise AssertionError("section swap unexpectedly rewrote the token block")
        stage = root / "swap-sections"
        _stage(base, stage, {rel: swapped})
        _expect_red("per_cursor:receipt_before_current_event", stage)
        count += 1

        missing = original.replace("### 3. PERSIST_PROJECTION_EVIDENCE\n", "### 3. Projection evidence omitted\n", 1)
        if missing == original:
            raise AssertionError("missing-projection mutation did not edit per_cursor headings")
        stage = root / "missing"
        _stage(base, stage, {rel: missing})
        _expect_red("per_cursor:missing_projection_evidence", stage)
        count += 1

        duplicate = original.replace(
            "### 3. PERSIST_PROJECTION_EVIDENCE\n",
            "### 3. PERSIST_PROJECTION_EVIDENCE\n### 3. PERSIST_PROJECTION_EVIDENCE\n",
            1,
        )
        stage = root / "duplicate"
        _stage(base, stage, {rel: duplicate})
        _expect_red("per_cursor:duplicate_projection_evidence", stage)
        count += 1

        old_chain = original + (
            "\n```\n"
            "release_operator reveal → create_current_event_binding_receipt(...)\n"
            "→ write_binding_receipt(...)\n"
            "→ current-event.json\n"
            "```\n"
        )
        stage = root / "old-chain"
        _stage(base, stage, {rel: old_chain})
        _expect_red("per_cursor:old_receipt_before_current_event_chain", stage)
        count += 1

        old_tokens = list(EXPECTED_TOKENS)
        i_current = old_tokens.index("INSTALL_CURRENT_EVENT")
        i_receipt = old_tokens.index("CREATE_BINDING_RECEIPT")
        old_tokens[i_current], old_tokens[i_receipt] = old_tokens[i_receipt], old_tokens[i_current]
        stage = root / "token-only"
        _stage(base, stage, {rel: _replace_token_block(original, tuple(old_tokens))})
        _expect_red("per_cursor:token_block_only_reorder", stage)
        count += 1

    print(f"RUNBOOK_CROSS_DOCUMENT_MUTATION_RED_PASS cases={count}")
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Cross-document Phase-B lifecycle checker")
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    tokens = check_runbook_lifecycle(args.base)
    print(
        "RUNBOOK_CROSS_DOCUMENT_ORDER_PASS "
        + ">".join(tokens)
        + " sources=token_block,headings,anchors,chains"
        + " finish_clause_between_model_work_and_ack=True"
    )
    if args.self_test:
        run_mutation_self_tests(args.base)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
