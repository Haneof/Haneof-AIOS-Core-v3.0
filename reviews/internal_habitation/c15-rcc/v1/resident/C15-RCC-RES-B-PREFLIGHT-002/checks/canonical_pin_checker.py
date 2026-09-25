#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

CANONICAL = {
    "World": "626c6bb32c7fdae90a068ee10dd2b4c9cdbc46b6feb2bf5b11cba9363401f6aa",
    "Index": "ecfabf4eb8261f306b5c9f8a59dae2ef8a1629ddc2823b4311d6adffc3c1e5f1",
    "Release": "eada20a0bf59d1cf25446c0153d1dc719b280627d9e0170364e690e1523391c8",
}
DOC_RELS = (
    Path("operator_manifest.md"),
    Path("source_pins_and_digests.md"),
    Path("procedure/b_startup_procedure.md"),
)
_HEX = r"(?P<hash>[0-9a-f]{64})"

_PATTERNS: dict[str, tuple[tuple[str, re.Pattern[str]], ...]] = {
    "World": (
        ("bare", re.compile(rf"(?i)\bWorld\s*:\s*`?{_HEX}`?")),
        ("lineage", re.compile(rf"(?i)\blineage\s+World\b[^\n]*?`?{_HEX}`?")),
        ("file_after", re.compile(rf"(?i)\b(?:private_world\.sqlite|world\.sqlite)\b[^\n]{{0,180}}?`?{_HEX}`?")),
        ("file_before", re.compile(rf"(?i)`?{_HEX}`?[^\n]{{0,180}}?\b(?:private_world\.sqlite|world\.sqlite)\b")),
    ),
    "Index": (
        ("bare", re.compile(rf"(?i)\bIndex\s*:\s*`?{_HEX}`?")),
        ("lineage", re.compile(rf"(?i)\blineage\s+Index\b[^\n]*?`?{_HEX}`?")),
        ("file_after", re.compile(rf"(?i)\b(?:world_index\.sqlite|index\.sqlite)\b[^\n]{{0,180}}?`?{_HEX}`?")),
        ("file_before", re.compile(rf"(?i)`?{_HEX}`?[^\n]{{0,180}}?\b(?:world_index\.sqlite|index\.sqlite)\b")),
    ),
    "Release": (
        ("bare", re.compile(rf"(?i)\bRelease\s*:\s*`?{_HEX}`?")),
        ("lineage", re.compile(rf"(?i)\blineage\s+Release\b[^\n]*?`?{_HEX}`?")),
        ("file_after", re.compile(rf"(?i)\brelease_state\.json\b[^\n]{{0,180}}?`?{_HEX}`?")),
        ("file_before", re.compile(rf"(?i)`?{_HEX}`?[^\n]{{0,180}}?\brelease_state\.json\b")),
    ),
}


@dataclass(frozen=True)
class Declaration:
    kind: str
    role: str
    line_no: int
    col_start: int
    col_end: int
    value: str
    line: str


class PinCheckError(RuntimeError):
    pass


def collect_declarations(text: str) -> list[Declaration]:
    out: list[Declaration] = []
    seen: set[tuple[str, int, int, int]] = set()
    for line_no, line in enumerate(text.splitlines(), 1):
        for kind, patterns in _PATTERNS.items():
            for role, pattern in patterns:
                for match in pattern.finditer(line):
                    start, end = match.span("hash")
                    key = (kind, line_no, start, end)
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append(Declaration(kind, role, line_no, start, end, match.group("hash"), line))
    return out


def check_doc_text(name: str, text: str) -> dict[str, list[Declaration]]:
    declarations = collect_declarations(text)
    by_kind: dict[str, list[Declaration]] = {kind: [] for kind in CANONICAL}
    for declaration in declarations:
        by_kind[declaration.kind].append(declaration)
    for kind, expected in CANONICAL.items():
        found = by_kind[kind]
        if not found:
            raise PinCheckError(f"{name}: missing authoritative {kind} declaration")
        wrong = [d for d in found if d.value != expected]
        if wrong:
            details = "; ".join(f"line {d.line_no} role={d.role} value={d.value}" for d in wrong)
            raise PinCheckError(
                f"{name}: contradictory authoritative {kind} declaration(s): {details}; expected {expected}"
            )
    return by_kind


def read_docs(base: Path) -> dict[Path, str]:
    docs: dict[Path, str] = {}
    for rel in DOC_RELS:
        path = base / rel
        if not path.is_file():
            raise PinCheckError(f"missing canonical pin document: {path}")
        docs[rel] = path.read_text(encoding="utf-8")
    return docs


def check_canonical_pin_docs_texts(docs: dict[Path, str]) -> dict[Path, dict[str, list[Declaration]]]:
    result: dict[Path, dict[str, list[Declaration]]] = {}
    for rel in DOC_RELS:
        if rel not in docs:
            raise PinCheckError(f"missing canonical pin document text: {rel}")
        result[rel] = check_doc_text(str(rel), docs[rel])
    return result


def check_canonical_pin_docs(base: Path) -> dict[Path, dict[str, list[Declaration]]]:
    return check_canonical_pin_docs_texts(read_docs(base))


def _flip_last_hex(value: str) -> str:
    return value[:-1] + ("0" if value[-1] != "0" else "1")


def _replace_decl(text: str, declaration: Declaration, new_value: str) -> str:
    lines = text.splitlines(keepends=True)
    idx = declaration.line_no - 1
    line = lines[idx]
    if line[declaration.col_start:declaration.col_end] != declaration.value:
        raise AssertionError("declaration span drifted")
    lines[idx] = line[:declaration.col_start] + new_value + line[declaration.col_end:]
    return "".join(lines)


def _mutate_one(text: str, kind: str, *, prefer_bare: bool) -> str:
    decls = [d for d in collect_declarations(text) if d.kind == kind]
    if not decls:
        raise AssertionError(f"no {kind} declaration available to mutate")
    target = next((d for d in decls if prefer_bare and d.role == "bare"), decls[0])
    return _replace_decl(text, target, _flip_last_hex(target.value))


def _remove_all_kind_declarations(text: str, kind: str) -> str:
    line_numbers = {d.line_no for d in collect_declarations(text) if d.kind == kind}
    if not line_numbers:
        raise AssertionError(f"no {kind} declarations available to remove")
    return "".join(
        line for i, line in enumerate(text.splitlines(keepends=True), 1) if i not in line_numbers
    )


def _expect_red(label: str, docs: dict[Path, str]) -> None:
    try:
        check_canonical_pin_docs_texts(docs)
    except PinCheckError as exc:
        print(f"PIN_MUTATION_RED_PASS {label}: {exc}")
        return
    raise AssertionError(f"mutation false-green: {label}")


def run_mutation_self_tests(base: Path) -> int:
    docs = read_docs(base)
    check_canonical_pin_docs_texts(docs)
    count = 0
    for rel in DOC_RELS:
        for kind in ("World", "Index", "Release"):
            mutated = dict(docs)
            mutated[rel] = _mutate_one(
                docs[rel], kind, prefer_bare=(rel == Path("operator_manifest.md"))
            )
            _expect_red(f"{rel}:{kind}:one_hex", mutated)
            count += 1

    wrong_world = _flip_last_hex(CANONICAL["World"])
    duplicate = dict(docs)
    duplicate[Path("operator_manifest.md")] = (
        docs[Path("operator_manifest.md")] + f"\n- World: `{wrong_world}`\n"
    )
    _expect_red("operator_manifest.md:World:duplicate_wrong", duplicate)
    count += 1

    missing = dict(docs)
    missing[Path("operator_manifest.md")] = _remove_all_kind_declarations(
        docs[Path("operator_manifest.md")], "World"
    )
    _expect_red("operator_manifest.md:World:missing_all", missing)
    count += 1

    print(f"CANONICAL_PIN_MUTATION_RED_PASS cases={count}")
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Strict canonical World/Index/Release declaration checker")
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    checked = check_canonical_pin_docs(args.base)
    summary = ", ".join(
        f"{rel.name}:W{len(kinds['World'])}/I{len(kinds['Index'])}/R{len(kinds['Release'])}"
        for rel, kinds in checked.items()
    )
    print(f"CANONICAL_PIN_CONSISTENCY_PASS {summary}")
    if args.self_test:
        run_mutation_self_tests(args.base)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
