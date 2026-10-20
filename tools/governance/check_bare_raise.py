#!/usr/bin/env python3
"""扫描裸 `raise` 是否位于 except 处理块内。

背景：Python 的裸 `raise` 只能在 except 块内使用，否则抛
`RuntimeError: No active exception to reraise`。这类缺陷在
`os.name == "nt"` 的分支里会被 Windows 完全跳过，导致
「本机绿 / Linux CI 红」的假象（2026-10-20 的 publication.py:392 即此例）。

本脚本用 AST 静态检查，不执行代码，可跨平台运行。

用法：
  python tools/governance/check_bare_raise.py src tools tests
退出码：0 无问题 / 1 发现问题
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


class BareRaiseVisitor(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.except_depth = 0
        self.findings: list[tuple[int, int]] = []

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.except_depth += 1
        self.generic_visit(node)
        self.except_depth -= 1

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function_like(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function_like(node)

    def _visit_function_like(self, node) -> None:
        # A nested function resets the handler context: `raise` inside a nested
        # def is NOT inside the enclosing except handler at runtime.
        saved = self.except_depth
        self.except_depth = 0
        self.generic_visit(node)
        self.except_depth = saved

    def visit_Raise(self, node: ast.Raise) -> None:
        if node.exc is None and self.except_depth == 0:
            self.findings.append((node.lineno, node.col_offset))
        self.generic_visit(node)


def scan(paths: list[Path]) -> list[tuple[Path, int]]:
    problems: list[tuple[Path, int]] = []
    for root in paths:
        if not root.exists():
            continue
        files = [root] if root.is_file() else sorted(root.rglob("*.py"))
        for file in files:
            if ".venv" in file.parts or ".git" in file.parts:
                continue
            try:
                tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
            except (SyntaxError, UnicodeDecodeError):
                continue
            visitor = BareRaiseVisitor(file)
            visitor.visit(tree)
            problems.extend((file, lineno) for lineno, _ in visitor.findings)
    return problems


def main(argv: list[str]) -> int:
    targets = [Path(p) for p in (argv[1:] or ["src", "tools", "tests"])]
    problems = scan(targets)
    if problems:
        print("[FAIL] 裸 raise 位于 except 块之外（Linux 上会抛 RuntimeError）：")
        for file, lineno in problems:
            print(f"  - {file}:{lineno}")
        return 1
    print(f"[OK] 已扫描 {len(targets)} 个路径，未发现 except 块之外的裸 raise")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
