#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

EXPECTED_TOKENS = (
    "REVEAL",
    "INSTALL_CURRENT_EVENT",
    "PERSIST_PROJECTION_EVIDENCE",
    "CREATE_BINDING_RECEIPT",
    "VERIFY_BINDING",
    "DERIVE_OCCURRED_AT",
    "INGEST",
    "MODEL_WORK",
    "FINISH_CURSOR_MODEL_WORK",
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


class LifecycleCheckError(RuntimeError):
    pass


def extract_lifecycle_tokens(name: str, text: str) -> tuple[str, ...]:
    if text.count(START) != 1 or text.count(END) != 1:
        raise LifecycleCheckError(
            f"{name}: expected exactly one lifecycle token block, got begin={text.count(START)} end={text.count(END)}"
        )
    body = text.split(START, 1)[1].split(END, 1)[0]
    tokens = tuple(line.strip() for line in body.splitlines() if line.strip())
    if tokens != EXPECTED_TOKENS:
        raise LifecycleCheckError(
            f"{name}: lifecycle tokens differ: got={tokens!r} expected={EXPECTED_TOKENS!r}"
        )
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
        tokens.append(extract_lifecycle_tokens(str(rel), docs[rel]))
    if tokens[0] != tokens[1]:
        raise LifecycleCheckError(f"cross-document lifecycle mismatch: {tokens[0]!r} != {tokens[1]!r}")
    return tokens[0]


def check_runbook_lifecycle(base: Path) -> tuple[str, ...]:
    return check_runbook_lifecycle_texts(read_docs(base))


def _replace_token_block(text: str, tokens: tuple[str, ...]) -> str:
    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    body = "\n" + "\n".join(tokens) + "\n"
    return before + START + body + END + after


def _expect_red(label: str, docs: dict[Path, str]) -> None:
    try:
        check_runbook_lifecycle_texts(docs)
    except LifecycleCheckError as exc:
        print(f"RUNBOOK_LIFECYCLE_MUTATION_RED_PASS {label}: {exc}")
        return
    raise AssertionError(f"lifecycle mutation false-green: {label}")


def run_mutation_self_tests(base: Path) -> int:
    docs = read_docs(base)
    check_runbook_lifecycle_texts(docs)
    rel = Path("procedure/per_cursor_interaction.md")
    count = 0

    old_order = list(EXPECTED_TOKENS)
    i_current = old_order.index("INSTALL_CURRENT_EVENT")
    i_receipt = old_order.index("CREATE_BINDING_RECEIPT")
    old_order[i_current], old_order[i_receipt] = old_order[i_receipt], old_order[i_current]
    mutated = dict(docs)
    mutated[rel] = _replace_token_block(docs[rel], tuple(old_order))
    _expect_red("per_cursor:receipt_before_current_event", mutated)
    count += 1

    missing_tokens = tuple(t for t in EXPECTED_TOKENS if t != "PERSIST_PROJECTION_EVIDENCE")
    mutated = dict(docs)
    mutated[rel] = _replace_token_block(docs[rel], missing_tokens)
    _expect_red("per_cursor:missing_projection_evidence", mutated)
    count += 1

    duplicate_tokens = EXPECTED_TOKENS[:3] + ("PERSIST_PROJECTION_EVIDENCE",) + EXPECTED_TOKENS[3:]
    mutated = dict(docs)
    mutated[rel] = _replace_token_block(docs[rel], duplicate_tokens)
    _expect_red("per_cursor:duplicate_projection_evidence", mutated)
    count += 1

    print(f"RUNBOOK_CROSS_DOCUMENT_MUTATION_RED_PASS cases={count}")
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Cross-document Phase-B lifecycle checker")
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    tokens = check_runbook_lifecycle(args.base)
    print("RUNBOOK_CROSS_DOCUMENT_ORDER_PASS " + ">".join(tokens))
    if args.self_test:
        run_mutation_self_tests(args.base)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
