"""Gate D — mechanical no-semantic-script scan of the real-run package.

Operator tooling: it lives outside ``aios_exchange`` on purpose, so the run
package itself contains none of the denylist vocabulary it is scanned for.

Rules applied to every file of the real-run package:

R1 no semantic-router/agent module names;
R2 no cursor / fixture / event-id / phase / run-lineage literals in *code*
   (comments and docstrings are documentation, not behaviour, and are excluded
   from pattern scanning; they are printed separately for human review);
R3 no capability-name literals (derived from the frozen Core source) => no
   hard-coded capability decision;
R4 AST policy:
   * no ``eval`` / ``exec`` / ``compile`` / ``__import__`` / dynamic import;
   * no ``lambda``;
   * no callback-shaped parameter name and no callable default;
   * ``ModelDirective`` constructed at exactly one whitelisted site and never
     from literal content;
   * ``CapabilityResult`` / ``CapabilityCall`` constructions whitelisted, and
     never from literal content (no fabricated capability evidence);
   * no attribute access that does not exist on the frozen types;
   * no comparison against a string outside the mechanical protocol vocabulary
     (no branching on keywords, event ids or fixture text);
R5 import policy: stdlib and ``aios_core`` imports only (never tests);
R6 response-mode proof: the single supported mode is the external session mode.
"""

from __future__ import annotations

import ast
import hashlib
import io
import json
import pathlib
import re
import tokenize
from typing import Any, Iterable

#: Mechanical protocol vocabulary the run package may branch on. Anything else
#: compared against a value would be content-driven branching.
ALLOWED_STRING_CONSTANTS = {
    # response mode / protocol enum values
    "EXTERNAL_CURRENT_RESIDENT_SESSION",
    # ledger events
    "request_published",
    "response_published",
    "response_consumed",
    # request kind
    "model_directive",
    # encodings
    "utf-8",
    "ascii",
    "rb",
    "ab",
    "wb",
    # request/response envelope keys
    "request_version",
    "response_version",
    "request_id",
    "request_sha256",
    "response_sha256",
    "authored_by",
    "directive",
    "body",
    "kind",
    "sequence",
    "wall_clock",
    "response_mode",
    "response_contract",
    # directive keys
    "capability_calls",
    "arguments",
    "call_id",
    "silence",
    "response",
    "usage",
    "provenance",
    "total_tokens",
    "input_tokens",
    "output_tokens",
    "provider",
    "model",
    # capability-result field names (frozen contract)
    "name",
    "ok",
    "data",
    "error_code",
    "error_message",
    # ledger record fields
    "seq",
    "event",
    "record_sha256",
    "prev_sha256",
    # verification report keys / path markers
    "path",
    "sha256",
    "size",
    "files",
    "file_count",
    "__pycache__",
    "ok",
}

FORBIDDEN_FILE_STEMS = (
    "resident_agent",
    "router",
    "brain",
    "policy_engine",
    "decider",
    "responder",
    "expected",
    "fixture",
)

FORBIDDEN_SOURCE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("cursor_literal", r"cursor[\s_-]*\d+"),
    ("cursor_word", r"\bcursor\b"),
    ("fixture_word", r"\bfixture"),
    ("evaluator_word", r"\bevaluator"),
    ("event_id_literal", r"\bevent[\s_-]*id\b"),
    ("phase_a_literal", r"\bphase[\s_-]*a\b"),
    ("run_lineage_c15", r"\bC15\b"),
    ("run_lineage_run_id", r"\bA-00\d\b"),
    ("keyword_router", r"\bkeyword"),
    ("expected_answer", r"expected[\s_-]*(answer|response|reply|output|learning)"),
    ("prewritten", r"\bprewritten|hard[\s_-]?coded"),
    ("fallback_branch", r"\bfallback\b"),
    ("claim_generation", r"\bclaim"),
    ("semantic_tuning", r"\bsemantic\b"),
)

FORBIDDEN_CALL_NAMES = {"eval", "exec", "compile", "__import__"}
FORBIDDEN_IMPORT_MODULES = {"importlib", "subprocess", "tests", "operator_tools", "resident_agent", "synthetic"}

FORBIDDEN_PARAMETER_NAMES = {
    "callback",
    "cb",
    "handler",
    "provider",
    "responder",
    "on_decision",
    "decide",
    "model_handler",
}

DIRECTIVE_CONSTRUCTION_WHITELIST = {("schema.py", "parse_model_directive")}

#: (class name) -> allowed (file, function) construction sites.
CORE_VALUE_CONSTRUCTION_WHITELIST: dict[str, set[tuple[str, str]]] = {
    "CapabilityResult": {
        ("schema.py", "assert_capability_result_contract"),
        ("schema.py", "capability_result_from_mapping"),
    },
    "CapabilityCall": {("schema.py", "parse_model_directive")},
}

#: construction sites where literal keyword content is explicitly a probe.
LITERAL_KWARG_PROBE_ALLOWLIST = {
    ("CapabilityResult", "assert_capability_result_contract"),
}

FORBIDDEN_ATTRIBUTES = ("duration_seconds",)

#: ``.arguments`` only ever exists on ``CapabilityCall`` (the model's own chosen
#: action), never on ``CapabilityResult`` (evidence).
ARGUMENTS_ALLOWLIST = {("schema.py", "parse_model_directive"), ("schema.py", "model_directive_to_mapping")}


def _sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def code_only_text(path: pathlib.Path) -> str:
    """Source text with comments and docstrings masked (documentation is not behaviour)."""

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    masked = list(lines)
    try:
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.type == tokenize.COMMENT:
                row = token.start[0] - 1
                masked[row] = masked[row][: token.start[1]] + "\n"
    except tokenize.TokenError:  # pragma: no cover - defensive
        pass
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.body:
                continue
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                end = getattr(first.value, "end_lineno", first.value.lineno)
                for row in range(first.value.lineno - 1, end):
                    if 0 <= row < len(masked):
                        masked[row] = "\n"
    return "".join(masked)


def capability_names_from_frozen_core(core_source: pathlib.Path) -> list[str]:
    names: set[str] = set()
    text = core_source.read_text(encoding="utf-8")
    for match in re.finditer(r"CapabilitySpec\((.*?)\n\s*\)", text, flags=re.S):
        found = re.search(r'name="([^"]+)"', match.group(1))
        if found:
            names.add(found.group(1))
    return sorted(names)


class _PackageVisitor(ast.NodeVisitor):
    def __init__(self, path: pathlib.Path, findings: list[dict[str, Any]]) -> None:
        self.path = path
        self.findings = findings
        self.function_stack: list[str] = []
        self.prose_literals: list[dict[str, Any]] = []

    def _flag(self, rule: str, node: ast.AST, detail: str) -> None:
        self.findings.append(
            {
                "rule": rule,
                "file": self.path.name,
                "line": getattr(node, "lineno", None),
                "detail": detail,
            }
        )

    @property
    def location(self) -> tuple[str, str]:
        return (self.path.name, self.function_stack[-1] if self.function_stack else "")

    # -- functions --------------------------------------------------------
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_stack.append(node.name)
        self._check_signature(node)
        self.generic_visit(node)
        self.function_stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    def _check_signature(self, node: ast.FunctionDef) -> None:
        args = list(node.args.posonlyargs) + list(node.args.args) + list(node.args.kwonlyargs)
        for arg in args:
            if arg.arg in FORBIDDEN_PARAMETER_NAMES:
                self._flag("callback_parameter", node, f"{node.name}({arg.arg}=...)")
            if arg.annotation is not None and "Callable" in ast.unparse(arg.annotation):
                self._flag("callback_parameter", node, f"{node.name}({arg.arg}: Callable)")
        for default in list(node.args.defaults) + [d for d in node.args.kw_defaults if d is not None]:
            if isinstance(default, (ast.Lambda, ast.Name)):
                self._flag(
                    "callable_default",
                    default,
                    f"{node.name} has a callable-shaped default: {ast.unparse(default)}",
                )

    # -- statements -------------------------------------------------------
    def visit_Lambda(self, node: ast.Lambda) -> None:
        self._flag("lambda_expression", node, "lambda expressions are not allowed in the run package")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        name = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else None)
        if isinstance(func, ast.Name) and name in FORBIDDEN_CALL_NAMES:
            self._flag("dynamic_execution", node, f"call to {name}()")
        if isinstance(func, ast.Attribute) and func.attr == "import_module":
            self._flag("dynamic_import", node, "dynamic module import is not allowed")
        if isinstance(func, ast.Attribute) and func.attr == "arguments" and self.location not in ARGUMENTS_ALLOWLIST:
            self._flag("forbidden_result_field_access", node, ".arguments outside the CapabilityCall whitelist")
        if isinstance(func, ast.Attribute) and func.attr in FORBIDDEN_ATTRIBUTES:
            self._flag("forbidden_result_field_access", node, f".{func.attr} does not exist on frozen types")

        if isinstance(func, ast.Name) and func.id in CORE_VALUE_CONSTRUCTION_WHITELIST:
            allowed = CORE_VALUE_CONSTRUCTION_WHITELIST[func.id]
            if self.location not in allowed:
                self._flag("fabricated_core_value", node, f"{func.id} constructed in {self.location[1]}")
            literal_allowed = (func.id, self.location[1]) in LITERAL_KWARG_PROBE_ALLOWLIST
            if not literal_allowed:
                for keyword in node.keywords:
                    if isinstance(keyword.value, ast.Constant):
                        self._flag(
                            "literal_core_value",
                            node,
                            f"literal constant passed to {func.id}({keyword.arg}=...)",
                        )

        if isinstance(func, ast.Name) and func.id == "ModelDirective":
            if self.location not in DIRECTIVE_CONSTRUCTION_WHITELIST:
                self._flag("directive_construction_site", node, f"ModelDirective constructed in {self.location[1]}")
            for keyword in node.keywords:
                if keyword.arg in {"response", "silence", "capability_calls"} and isinstance(
                    keyword.value, ast.Constant
                ):
                    self._flag("literal_directive_content", node, f"literal constant passed as {keyword.arg}=")
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name.split(".")[0] in FORBIDDEN_IMPORT_MODULES:
                self._flag("forbidden_import", node, f"import {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        root = module.split(".")[0]
        if root in FORBIDDEN_IMPORT_MODULES and module != "aios_exchange":
            self._flag("forbidden_import", node, f"from {module} import ...")
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        operands = [node.left, *node.comparators]
        for left, right in zip(operands, operands[1:]):
            for candidate, other in ((left, right), (right, left)):
                if not isinstance(candidate, ast.Constant) or not isinstance(candidate.value, str):
                    continue
                if isinstance(other, ast.Constant):
                    continue
                if candidate.value not in ALLOWED_STRING_CONSTANTS:
                    self._flag(
                        "semantic_string_branching",
                        node,
                        f"comparison against {candidate.value!r}",
                    )
        self.generic_visit(node)


def scan_run_package(package_root: str | pathlib.Path, *, core_source: str | pathlib.Path) -> dict[str, Any]:
    """Scan the real-run package. Returns a full, reviewable report."""

    root = pathlib.Path(package_root)
    core_source = pathlib.Path(core_source)
    findings: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []
    prose: list[dict[str, Any]] = []
    capability_names = capability_names_from_frozen_core(core_source)
    imports_by_module: dict[str, list[str]] = {}

    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        code = code_only_text(path)
        files.append({"path": relative, "sha256": _sha256_file(path), "bytes": path.stat().st_size})

        if path.stem in FORBIDDEN_FILE_STEMS:
            findings.append({"rule": "semantic_module_name", "file": relative, "line": None, "detail": path.stem})

        for rule, pattern in FORBIDDEN_SOURCE_PATTERNS:
            for match in re.finditer(pattern, code, flags=re.I):
                line = code[: match.start()].count("\n") + 1
                findings.append({"rule": rule, "file": relative, "line": line, "detail": match.group(0)})

        for name in capability_names:
            for marker in (f'"{name}"', f"'{name}'"):
                if marker in code:
                    findings.append(
                        {"rule": "capability_name_literal", "file": relative, "line": None, "detail": name}
                    )
                    break

        tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        visitor = _PackageVisitor(path, findings)
        visitor.visit(tree)
        seen_prose: set[tuple[int, str]] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                key = (node.lineno, node.value)
                if key in seen_prose:
                    continue
                seen_prose.add(key)
                if len(node.value) >= 24 and " " in node.value:
                    prose.append({"file": relative, "line": node.lineno, "literal": node.value})

        modules: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                modules.append(node.module or "")
        imports_by_module[relative] = sorted(set(modules))

    mode_file = root / "__init__.py"
    mode_ok = False
    if mode_file.exists():
        mode_ok = 'REAL_RESPONSE_MODE = "EXTERNAL_CURRENT_RESIDENT_SESSION"' in mode_file.read_text(encoding="utf-8")
    if not mode_ok:
        findings.append(
            {"rule": "response_mode_missing", "file": "__init__.py", "line": None, "detail": "mode not declared"}
        )

    import_rules_violated = any(f["rule"] == "forbidden_import" for f in findings)
    runner_path = root / "runner.py"
    runner_code = code_only_text(runner_path) if runner_path.exists() else ""
    runner_callback_free = "callback" not in runner_code and not any(
        f["rule"] in {"callback_parameter", "callable_default"} for f in findings
    )
    return {
        "package_root": str(root),
        "file_count": len(files),
        "files": files,
        "capability_names_checked": capability_names,
        "findings": findings,
        "prose_literal_inventory": prose,
        "imports": imports_by_module,
        "allowed_string_constants": sorted(ALLOWED_STRING_CONSTANTS),
        "checks": {
            "response_mode_declared": mode_ok,
            "no_semantic_module_names": not any(f["rule"] == "semantic_module_name" for f in findings),
            "no_capability_name_literals": not any(f["rule"] == "capability_name_literal" for f in findings),
            "no_content_literals": not any(
                f["rule"]
                in {
                    "cursor_literal",
                    "cursor_word",
                    "fixture_word",
                    "evaluator_word",
                    "event_id_literal",
                    "phase_a_literal",
                    "run_lineage_c15",
                    "run_lineage_run_id",
                    "keyword_router",
                    "expected_answer",
                    "prewritten",
                    "fallback_branch",
                    "claim_generation",
                    "semantic_tuning",
                }
                for f in findings
            ),
            "no_ast_policy_violations": not any(
                f["rule"]
                in {
                    "lambda_expression",
                    "dynamic_execution",
                    "dynamic_import",
                    "callback_parameter",
                    "callable_default",
                    "literal_directive_content",
                    "literal_core_value",
                    "fabricated_core_value",
                    "semantic_string_branching",
                    "directive_construction_site",
                    "forbidden_result_field_access",
                }
                for f in findings
            ),
            "import_policy_ok": not import_rules_violated,
            "runner_has_no_callback_interface": runner_callback_free,
        },
        "pass": not findings,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "GATE D — NO SEMANTIC SCRIPT SCAN",
        f"package_root: {report['package_root']}",
        f"files scanned: {report['file_count']}",
        f"capability names checked: {len(report['capability_names_checked'])}",
        f"findings: {len(report['findings'])}",
        f"pass: {report['pass']}",
        "",
        "checks:",
    ]
    for name, value in report["checks"].items():
        lines.append(f"  - {name}: {value}")
    lines.append("")
    lines.append(f"protocol string vocabulary ({len(report['allowed_string_constants'])}):")
    lines.append("  " + ", ".join(report["allowed_string_constants"]))
    lines.append("")
    lines.append(f"prose literals ({len(report['prose_literal_inventory'])}, documentation and error text):")
    for item in report["prose_literal_inventory"]:
        lines.append(f"  {item['file']}:{item['line']} {item['literal']!r}")
    lines.append("")
    lines.append("findings:")
    for item in report["findings"]:
        lines.append(f"  [{item['rule']}] {item['file']}:{item['line']} {item['detail']}")
    return "\n".join(lines) + "\n"


def main(argv: Iterable[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--package", required=True)
    parser.add_argument("--core-source", required=True)
    parser.add_argument("--report", required=False)
    args = parser.parse_args(list(argv) if argv is not None else None)
    report = scan_run_package(args.package, core_source=args.core_source)
    if args.report:
        pathlib.Path(args.report).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(render_report(report))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
