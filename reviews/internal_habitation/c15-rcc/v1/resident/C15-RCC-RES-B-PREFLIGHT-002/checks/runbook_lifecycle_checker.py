#!/usr/bin/env python3
"""Cross-document Phase-B lifecycle gate.

Production entrypoint and every mutation self-test call check_runbook_lifecycle().
The self-test writes disposable copies and invokes that same function; it does not
reimplement the comparison.

CORRECTIVE-014-FIXUP-003 / IA-BLK-004 retains the CORRECTIVE-013
shell-fence/heredoc rules and fails closed on disguised lifecycle operations.
Artifact-bound operations are recognized from their lifecycle path signature,
not merely a literal executable word, and every operational step has a frozen
shell-command cardinality. This closes wrapper, short-circuit, command-variable,
and split-indirection duplicate paths while still requiring one direct canonical
operation. Python heredoc call sites remain inspected separately from shell commands.
"""
from __future__ import annotations

import argparse
import ast
import re
import shutil
import tempfile
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
FINISH_CLAUSE = "Do not ACK until"

# Exact executable lines present in both active runbooks. Prose that merely
# mentions ".projection.json" does not match these lines.
INSTALL_CURRENT_EVENT_CMD = (
    'install -m 0400 "$RUN_ROOT/reveal.json" "$RUN_ROOT/current-event.json"'
)
PERSIST_INSTALL_CMD = (
    'install -m 0400 "$RUN_ROOT/current-event.json" '
    '"$RUN_ROOT/evidence/event-$(printf \'%03d\' "$SEQ").projection.json"'
)
PERSIST_SHA256_CMD = (
    'sha256sum "$RUN_ROOT/evidence/event-$(printf \'%03d\' "$SEQ").projection.json" '
    '>> "$RUN_ROOT/evidence/projection_digests.sha256"'
)
CLEAR_BINDING_CMD = (
    'rm -f "$RUN_ROOT/current-event.json" "$RUN_ROOT/binding/current-event-binding.json"'
)
RELEASE_OPERATOR_PATH = "reviews/internal_habitation/c15-rcc/v1/release/release_operator.py"
REVEAL_CMD_PREFIX = f"python3 {RELEASE_OPERATOR_PATH} reveal --phase B"
ACK_CMD_PREFIX = f"python3 {RELEASE_OPERATOR_PATH} ack --phase B"
_PRODUCTION_TURN_RE = re.compile(
    r"--model-handler\s+bridged_model_handler:headless_production_handler\s+turn\s+--session\b"
)
_SHELL_LANGUAGES = frozenset({"bash", "sh", "shell"})
_FENCE_OPEN_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_HEREDOC_RE = re.compile(
    r"(?<!<)<<(?!<)(-?)\s*(?:'([^']+)'|\"([^\"]+)\"|([A-Za-z_][A-Za-z0-9_]*))"
)
_PYTHON_STDIN_RE = re.compile(r"(?:^|\s)python(?:3(?:\.\d+)?)?\s+-\s*(?:<<|$)")
_ASSIGN_PREFIX = re.compile(r"^(?:[A-Za-z_][A-Za-z0-9_]*=(?:\"[^\"]*\"|'[^']*'|\S+)\s+)+")


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


def _step_bodies(name: str, text: str) -> dict[str, str]:
    spans = _step_spans(text)
    tokens = [tok for tok, _, _ in spans]
    if tokens != list(EXPECTED_TOKENS):
        raise LifecycleCheckError(
            f"{name}: cannot isolate operational step bodies: got={tokens!r}"
        )
    return {tok: text[start:end] for tok, start, end in spans}


def _is_echo_only(line: str) -> bool:
    """Drop only a simple echo command, never a compound line after echo."""
    raw = line.strip()
    if "$(" in raw or "`" in raw:
        return False
    body = _ASSIGN_PREFIX.sub("", raw)
    if not re.match(r"^echo(?:\s|$)", body):
        return False
    # A semicolon/pipeline/redirection/control operator means this is not
    # echo-only. Be conservative around quoted operators: retaining a harmless
    # echo line is safer than hiding a following executable command.
    return not re.search(r"&&|\|\||[;|<>]", body)


def _iter_fences(text: str) -> list[tuple[str, str]]:
    """Return only explicit bash/sh/shell fenced blocks as (language, body).

    Untagged fences and fences tagged text/json/python/etc. are intentionally
    invisible to the executable-command gate. The small Markdown scanner handles
    backtick and tilde fences; it does not interpret prose or execute shell.
    """
    lines = text.splitlines()
    fences: list[tuple[str, str]] = []
    i = 0
    while i < len(lines):
        opening = _FENCE_OPEN_RE.match(lines[i])
        if not opening:
            i += 1
            continue
        marker = opening.group(1)
        info = opening.group(2).strip()
        # CommonMark does not permit a backtick in the info string of a backtick fence.
        if marker.startswith("`") and "`" in info:
            i += 1
            continue
        language = info.split(None, 1)[0].lower() if info else ""
        close_re = re.compile(
            rf"^ {{0,3}}{re.escape(marker[0])}{{{len(marker)},}}[ \t]*$"
        )
        body_lines: list[str] = []
        i += 1
        closed = False
        while i < len(lines):
            if close_re.match(lines[i]):
                closed = True
                i += 1
                break
            body_lines.append(lines[i])
            i += 1
        if not closed:
            raise LifecycleCheckError("unterminated Markdown fenced block")
        if language in _SHELL_LANGUAGES:
            fences.append((language, "\n".join(body_lines)))
    return fences


def _parse_shell_fence(fence_body: str) -> tuple[list[str], list[str]]:
    """Extract shell logical commands and Python-stdin heredoc payloads.

    Here-document bodies are consumed by a delimiter state machine and are never
    added to the shell command list. For the two documented Python heredocs, the
    payload is returned separately so the checker can validate the specific
    Python call anchors without misclassifying them as shell commands.
    """
    lines = fence_body.splitlines()
    commands: list[str] = []
    python_payloads: list[str] = []
    i = 0
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        pieces: list[str] = []
        current = raw
        while True:
            rstripped = current.rstrip()
            if rstripped.endswith("\\"):
                pieces.append(rstripped[:-1].strip())
                i += 1
                if i >= len(lines):
                    current = ""
                    break
                current = lines[i]
                continue
            pieces.append(current.strip())
            i += 1
            break
        command = " ".join(piece for piece in pieces if piece).strip()
        if not command:
            continue

        heredoc_matches = list(_HEREDOC_RE.finditer(command))
        is_python_stdin = bool(_PYTHON_STDIN_RE.search(command))
        for heredoc in heredoc_matches:
            strip_tabs = heredoc.group(1) == "-"
            delimiter = next(group for group in heredoc.groups()[1:] if group is not None)
            payload: list[str] = []
            found_delimiter = False
            while i < len(lines):
                candidate = lines[i].lstrip("\t") if strip_tabs else lines[i]
                if candidate == delimiter:
                    i += 1
                    found_delimiter = True
                    break
                payload.append(lines[i])
                i += 1
            if not found_delimiter:
                raise LifecycleCheckError(
                    f"unterminated here-document delimiter {delimiter!r}"
                )
            if is_python_stdin:
                python_payloads.append("\n".join(payload))

        if not _is_echo_only(command):
            commands.append(command)
    return commands, python_payloads


def _shell_contents_in(text: str) -> tuple[list[str], list[str]]:
    commands: list[str] = []
    python_payloads: list[str] = []
    for _language, body in _iter_fences(text):
        fence_commands, fence_python = _parse_shell_fence(body)
        commands.extend(fence_commands)
        python_payloads.extend(fence_python)
    return commands, python_payloads


def _bash_commands_in(text: str) -> list[str]:
    """Compatibility helper: executable shell commands only, never heredoc data."""
    return _shell_contents_in(text)[0]



def _is_reveal_command(command: str) -> bool:
    return command.startswith(REVEAL_CMD_PREFIX)


def _is_ack_command(command: str) -> bool:
    return command.startswith(ACK_CMD_PREFIX)


def _is_production_turn_command(command: str) -> bool:
    return command.startswith("python3 -m aios_core.headless.cli ") and bool(
        _PRODUCTION_TURN_RE.search(command)
    )


def _has_shell_command_word(command: str, word: str) -> bool:
    """Conservative executable-word detector used only for fail-closed guards."""
    return bool(re.search(
        rf"(?:^|[\s;&|()])(?:/[^\s;&|()]+/)?{re.escape(word)}(?=\s|$)",
        command,
    ))


def _semantic_reveal(command: str) -> bool:
    return RELEASE_OPERATOR_PATH in command and bool(
        re.search(r"(?:^|\s)reveal\s+--phase\s+B(?:\s|$)", command)
    )


def _semantic_ack(command: str) -> bool:
    return RELEASE_OPERATOR_PATH in command and bool(
        re.search(r"(?:^|\s)ack\s+--phase\s+B(?:\s|$)", command)
    )


def _semantic_production_turn(command: str) -> bool:
    return (
        "aios_core.headless.cli" in command
        and "headless_production_handler" in command
        and bool(re.search(r"(?:^|\s)turn\s+--session(?:\s|$)", command))
    )


def _has_command_assignment(command: str, executable: str) -> bool:
    return bool(re.search(
        rf"(?:^|[\s;&|()])(?:[A-Za-z_][A-Za-z0-9_]*)="
        rf"{re.escape(executable)}(?=\s|;|&|\||$)",
        command,
    ))


def _semantic_install_current_event(command: str) -> bool:
    return (
        "reveal.json" in command
        and "current-event.json" in command
        and ".projection.json" not in command
        and (
            _has_shell_command_word(command, "install")
            or _has_shell_command_word(command, "cp")
            or _has_command_assignment(command, "install")
            or _has_command_assignment(command, "cp")
        )
    )


def _semantic_projection_install(command: str) -> bool:
    return (
        "current-event.json" in command
        and ".projection.json" in command
        and (
            _has_shell_command_word(command, "install")
            or _has_shell_command_word(command, "cp")
            or _has_command_assignment(command, "install")
            or _has_command_assignment(command, "cp")
        )
    )


def _semantic_projection_sha256(command: str) -> bool:
    return (
        ".projection.json" in command
        and "projection_digests.sha256" in command
        and (
            _has_shell_command_word(command, "sha256sum")
            or _has_command_assignment(command, "sha256sum")
        )
    )


def _semantic_clear_binding(command: str) -> bool:
    return (
        "current-event.json" in command
        and "binding/current-event-binding.json" in command
        and (
            _has_shell_command_word(command, "rm")
            or _has_command_assignment(command, "rm")
        )
    )


def _require_unique_semantic_operation(
    name: str,
    owner: str,
    by_token: dict[str, list[str]],
    semantic_predicate,
    canonical_predicate,
    detail: str,
) -> None:
    matches = [
        (token, command)
        for token, commands in by_token.items()
        for command in commands
        if semantic_predicate(command)
    ]
    if len(matches) != 1 or matches[0][0] != owner:
        raise LifecycleCheckError(
            f"{name}: semantic lifecycle operation {detail} must occur exactly once "
            f"in {owner}; found={matches!r}"
        )
    if not canonical_predicate(matches[0][1]):
        raise LifecycleCheckError(
            f"{name}: semantic lifecycle operation {detail} must use the direct "
            f"canonical shell form in {owner}; found={matches[0][1]!r}"
        )


def _require_operational_shell_shape(
    name: str,
    by_token: dict[str, list[str]],
) -> None:
    """Freeze executable-command cardinality for every operational owner step.

    The two canonical runbooks intentionally differ only where per_cursor keeps
    three exported binding paths in INSTALL_CURRENT_EVENT and exports
    CURRENT_OCCURRED_AT in DERIVE_OCCURRED_AT. Any additional shell command in
    these steps is fail-closed, including split variable-indirection attempts.
    """
    if name.endswith("b_startup_procedure.md"):
        expected = {
            "REVEAL": 1,
            "INSTALL_CURRENT_EVENT": 1,
            "PERSIST_PROJECTION_EVIDENCE": 3,
            "CREATE_BINDING_RECEIPT": 3,
            "VERIFY_BINDING": 1,
            "DERIVE_OCCURRED_AT": 2,
            "INGEST": 6,
            "MODEL_WORK": 1,
            "DURABLE_ACK": 1,
            "CLEAR_BINDING": 1,
        }
    elif name.endswith("per_cursor_interaction.md"):
        expected = {
            "REVEAL": 1,
            "INSTALL_CURRENT_EVENT": 4,
            "PERSIST_PROJECTION_EVIDENCE": 3,
            "CREATE_BINDING_RECEIPT": 3,
            "VERIFY_BINDING": 1,
            "DERIVE_OCCURRED_AT": 3,
            "INGEST": 6,
            "MODEL_WORK": 1,
            "DURABLE_ACK": 1,
            "CLEAR_BINDING": 1,
        }
    else:
        raise LifecycleCheckError(f"{name}: unknown canonical runbook identity")

    for token, expected_count in expected.items():
        actual = len(by_token[token])
        if actual != expected_count:
            raise LifecycleCheckError(
                f"{name}: {token} shell-command cardinality must be exactly "
                f"{expected_count}; found={actual} commands={by_token[token]!r}"
            )


def _is_receipt_command(text: str) -> bool:
    return (
        "create_current_event_binding_receipt" in text
        or "write_binding_receipt" in text
    )


def _is_event_install_command(text: str) -> bool:
    """True only for an executable install of current-event.json, not clear/rm/prose."""
    low = text.lower()
    if "current-event.json" not in text and "current-event" not in low:
        return False
    if any(token in low for token in (
        "clear ", "rm -f", "rm ", "ack --", "validate_current_event", "sha256sum", "persist ",
        ".projection.json",
    )):
        return False
    compact = re.sub(r"\s+", "", text.strip().strip("`"))
    if compact in {"current-event.json", "installcurrent-event.json"}:
        return True
    has_copy = (
        low.startswith("install ")
        or low.startswith("cp ")
        or " install " in f" {low} "
        or " cp " in f" {low} "
    )
    if not has_copy:
        return False
    if "reveal.json" in text and "current-event.json" in text:
        return True
    return "install" in low and "current-event" in low and "binding" not in low


def _sequence_is_receipt_before_install(commands: list[str]) -> bool:
    receipt_at = [i for i, cmd in enumerate(commands) if _is_receipt_command(cmd)]
    install_at = [i for i, cmd in enumerate(commands) if _is_event_install_command(cmd)]
    if not receipt_at or not install_at:
        return False
    return any(i > min(receipt_at) for i in install_at)


def assert_no_receipt_before_current_event(name: str, text: str) -> None:
    """Fail when one explicit shell fence creates a receipt before an install.

    Only bash/sh/shell fences are executable sources. Here-document payload is
    inert with respect to shell ordering and is excluded by _parse_shell_fence.
    """
    for index, (language, body) in enumerate(_iter_fences(text), 1):
        commands, _python_payloads = _parse_shell_fence(body)
        if _sequence_is_receipt_before_install(commands):
            raise LifecycleCheckError(
                f"{name}: executable {language} fence #{index} creates the binding receipt "
                f"before installing current-event.json: {commands!r}"
            )


def _require_command(name: str, token: str, commands: list[str], predicate, detail: str) -> None:
    if not any(predicate(cmd) for cmd in commands):
        raise LifecycleCheckError(
            f"{name}: {token} step body is missing executable contract: {detail}"
        )


def _forbid_command(name: str, token: str, commands: list[str], predicate, detail: str) -> None:
    hit = [cmd for cmd in commands if predicate(cmd)]
    if hit:
        raise LifecycleCheckError(
            f"{name}: {token} step body contains forbidden executable command ({detail}): {hit!r}"
        )


def _require_exactly_one(
    name: str,
    owner: str,
    by_token: dict[str, list[str]],
    predicate,
    detail: str,
    occurrence_count=None,
) -> None:
    matches: list[tuple[str, str]] = []
    for token, commands in by_token.items():
        for command in commands:
            if not predicate(command):
                continue
            count = occurrence_count(command) if occurrence_count else 1
            matches.extend((token, command) for _ in range(max(0, count)))
    if len(matches) != 1 or matches[0][0] != owner:
        found = [(token, command) for token, command in matches]
        raise LifecycleCheckError(
            f"{name}: executable contract {detail} must appear exactly once in {owner}; "
            f"found={found!r}"
        )


def _require_document_shell_occurrence(
    name: str,
    commands: list[str],
    predicate,
    detail: str,
    occurrence_count=None,
) -> None:
    matches: list[str] = []
    for command in commands:
        if predicate(command):
            count = occurrence_count(command) if occurrence_count else 1
            matches.extend(command for _ in range(max(0, count)))
    if len(matches) != 1:
        raise LifecycleCheckError(
            f"{name}: document-wide executable contract {detail} must appear exactly once; "
            f"found={matches!r}"
        )


def _python_call_positions(payload: str, function_name: str) -> list[tuple[int, int]]:
    """Locate actual AST calls in Python stdin, excluding comments and strings."""
    try:
        tree = ast.parse(payload)
    except SyntaxError as exc:
        raise LifecycleCheckError(f"invalid Python heredoc while checking {function_name}: {exc}") from exc
    return sorted(
        (node.lineno, node.col_offset)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == function_name
    )


def _python_call_count(payload: str, function_name: str) -> int:
    return len(_python_call_positions(payload, function_name))


def _require_document_python_call_once(
    name: str,
    payloads: list[str],
    function_name: str,
) -> None:
    matches = [
        payload
        for payload in payloads
        for _ in range(_python_call_count(payload, function_name))
    ]
    if len(matches) != 1:
        raise LifecycleCheckError(
            f"{name}: document-wide Python call {function_name}( must appear exactly once; "
            f"found={len(matches)}"
        )


def _require_exactly_one_python_call(
    name: str,
    owner: str,
    python_by_token: dict[str, list[str]],
    function_name: str,
) -> None:
    matches: list[tuple[str, str]] = []
    # These named operations are Python API calls in the documented Python-
    # stdin payloads, not shell command names or arbitrary text.
    for token, payloads in python_by_token.items():
        for payload in payloads:
            matches.extend((token, payload) for _ in range(_python_call_count(payload, function_name)))
    if len(matches) != 1 or matches[0][0] != owner:
        raise LifecycleCheckError(
            f"{name}: Python call {function_name}( must appear exactly once in {owner}; "
            f"found={[(token, source[:180]) for token, source in matches]!r}"
        )


def _require_shell_command_order(
    name: str,
    token: str,
    commands: list[str],
    first_predicate,
    second_predicate,
    detail: str,
) -> None:
    first = [i for i, command in enumerate(commands) if first_predicate(command)]
    second = [i for i, command in enumerate(commands) if second_predicate(command)]
    if len(first) != 1 or len(second) != 1 or first[0] >= second[0]:
        raise LifecycleCheckError(
            f"{name}: {detail} must occur once in order inside {token}; "
            f"first={first!r} second={second!r}"
        )


def _require_python_call_order(
    name: str,
    owner: str,
    python_by_token: dict[str, list[str]],
    first_function: str,
    second_function: str,
) -> None:
    locations: dict[str, list[tuple[int, int, int]]] = {
        first_function: [], second_function: [],
    }
    for payload_index, payload in enumerate(python_by_token[owner]):
        for function_name in locations:
            locations[function_name].extend(
                (payload_index, line, column)
                for line, column in _python_call_positions(payload, function_name)
            )
    first = locations[first_function]
    second = locations[second_function]
    if len(first) != 1 or len(second) != 1 or first[0] >= second[0]:
        raise LifecycleCheckError(
            f"{name}: Python calls {first_function} then {second_function} must occur once "
            f"in order in {owner}; first={first!r} second={second!r}"
        )


def assert_step_executable_contracts(name: str, text: str) -> None:
    bodies = _step_bodies(name, text)
    parsed = {token: _shell_contents_in(body) for token, body in bodies.items()}
    by_token = {token: parts[0] for token, parts in parsed.items()}
    python_by_token = {token: parts[1] for token, parts in parsed.items()}

    _require_operational_shell_shape(name, by_token)

    _require_unique_semantic_operation(
        name, "REVEAL", by_token,
        _semantic_reveal, _is_reveal_command, REVEAL_CMD_PREFIX,
    )
    _require_unique_semantic_operation(
        name, "INSTALL_CURRENT_EVENT", by_token,
        _semantic_install_current_event,
        lambda c: c == INSTALL_CURRENT_EVENT_CMD,
        INSTALL_CURRENT_EVENT_CMD,
    )
    _require_unique_semantic_operation(
        name, "PERSIST_PROJECTION_EVIDENCE", by_token,
        _semantic_projection_install,
        lambda c: c == PERSIST_INSTALL_CMD,
        "projection persist install",
    )
    _require_unique_semantic_operation(
        name, "PERSIST_PROJECTION_EVIDENCE", by_token,
        _semantic_projection_sha256,
        lambda c: c == PERSIST_SHA256_CMD,
        "projection digest append",
    )
    _require_unique_semantic_operation(
        name, "MODEL_WORK", by_token,
        _semantic_production_turn, _is_production_turn_command,
        "production headless turn --session",
    )
    _require_unique_semantic_operation(
        name, "DURABLE_ACK", by_token,
        _semantic_ack, _is_ack_command, ACK_CMD_PREFIX,
    )
    _require_unique_semantic_operation(
        name, "CLEAR_BINDING", by_token,
        _semantic_clear_binding,
        lambda c: c == CLEAR_BINDING_CMD,
        CLEAR_BINDING_CMD,
    )

    _require_exactly_one(
        name, "REVEAL", by_token,
        _is_reveal_command,
        REVEAL_CMD_PREFIX,
        lambda c: c.count(REVEAL_CMD_PREFIX),
    )
    _require_exactly_one(
        name, "INSTALL_CURRENT_EVENT", by_token,
        lambda c: c == INSTALL_CURRENT_EVENT_CMD,
        INSTALL_CURRENT_EVENT_CMD,
    )
    _require_exactly_one(
        name, "PERSIST_PROJECTION_EVIDENCE", by_token,
        lambda c: c == PERSIST_INSTALL_CMD,
        "install current-event.json -> evidence/event-%03d.projection.json",
    )
    _require_exactly_one(
        name, "PERSIST_PROJECTION_EVIDENCE", by_token,
        lambda c: c == PERSIST_SHA256_CMD,
        "sha256sum of that projection artifact appended to projection_digests.sha256",
    )
    _require_shell_command_order(
        name, "PERSIST_PROJECTION_EVIDENCE", by_token["PERSIST_PROJECTION_EVIDENCE"],
        lambda c: c == PERSIST_INSTALL_CMD,
        lambda c: c == PERSIST_SHA256_CMD,
        "projection install then digest append",
    )
    _require_exactly_one_python_call(
        name, "CREATE_BINDING_RECEIPT", python_by_token,
        "create_current_event_binding_receipt",
    )
    _require_exactly_one_python_call(
        name, "CREATE_BINDING_RECEIPT", python_by_token,
        "write_binding_receipt",
    )
    _require_python_call_order(
        name, "CREATE_BINDING_RECEIPT", python_by_token,
        "create_current_event_binding_receipt", "write_binding_receipt",
    )
    _forbid_command(
        name, "CREATE_BINDING_RECEIPT", by_token["CREATE_BINDING_RECEIPT"],
        _is_event_install_command,
        "install/cp of current-event.json belongs in INSTALL_CURRENT_EVENT, not after receipt creation",
    )
    _require_exactly_one_python_call(
        name, "VERIFY_BINDING", python_by_token,
        "validate_current_event_binding",
    )
    _require_command(
        name, "DERIVE_OCCURRED_AT", by_token["DERIVE_OCCURRED_AT"],
        lambda c: 'CURRENT_OCCURRED_AT="' in c and "current-event.json" in c and "occurred_at" in c,
        "CURRENT_OCCURRED_AT read from current-event.json",
    )
    _require_command(
        name, "INGEST", by_token["INGEST"],
        lambda c: "canonical_conversation_ingest.py" in c,
        "canonical_conversation_ingest.py",
    )
    _require_command(
        name, "INGEST", by_token["INGEST"],
        lambda c: "mechanical_ingest_adapter.py" in c,
        "mechanical_ingest_adapter.py",
    )
    _require_exactly_one(
        name, "MODEL_WORK", by_token,
        _is_production_turn_command,
        "production headless turn --session",
        lambda c: len(list(_PRODUCTION_TURN_RE.finditer(c))),
    )
    _require_exactly_one(
        name, "DURABLE_ACK", by_token,
        _is_ack_command,
        ACK_CMD_PREFIX,
        lambda c: c.count(ACK_CMD_PREFIX),
    )
    _require_exactly_one(
        name, "CLEAR_BINDING", by_token,
        lambda c: c == CLEAR_BINDING_CMD,
        CLEAR_BINDING_CMD,
    )

    # Owner-step checks above are not enough if a second active copy is placed
    # outside the operational headings. Require one document-wide shell/Python
    # occurrence as well, while the per-step checks enforce its unique owner.
    all_commands, all_python_payloads = _shell_contents_in(text)
    for predicate, detail, occurrence_count in (
        (_is_reveal_command,
         REVEAL_CMD_PREFIX,
         lambda c: c.count(REVEAL_CMD_PREFIX)),
        (lambda c: c == INSTALL_CURRENT_EVENT_CMD,
         INSTALL_CURRENT_EVENT_CMD, None),
        (lambda c: c == PERSIST_INSTALL_CMD,
         "projection persist install", None),
        (lambda c: c == PERSIST_SHA256_CMD,
         "projection digest append", None),
        (_is_production_turn_command,
         "production headless turn --session",
         lambda c: len(list(_PRODUCTION_TURN_RE.finditer(c)))),
        (_is_ack_command,
         ACK_CMD_PREFIX,
         lambda c: c.count(ACK_CMD_PREFIX)),
        (lambda c: c == CLEAR_BINDING_CMD,
         CLEAR_BINDING_CMD, None),
    ):
        _require_document_shell_occurrence(
            name, all_commands, predicate, detail, occurrence_count,
        )
    for function_name in (
        "create_current_event_binding_receipt",
        "write_binding_receipt",
        "validate_current_event_binding",
    ):
        _require_document_python_call_once(name, all_python_payloads, function_name)


def assert_finish_clause(name: str, text: str) -> None:
    spans = {tok: (start, end) for tok, start, end in _step_spans(text)}
    between = text[spans["MODEL_WORK"][0]:spans["DURABLE_ACK"][0]]
    if FINISH_CLAUSE not in between:
        raise LifecycleCheckError(
            f"{name}: missing finish-all-cursor-model-work clause between MODEL_WORK and DURABLE_ACK"
        )


def check_one(name: str, text: str) -> tuple[str, ...]:
    tokens = extract_token_block(name, text)
    headings = extract_heading_tokens(name, text)
    if tokens != headings:
        raise LifecycleCheckError(
            f"{name}: token block and operational headings diverge: {tokens!r} != {headings!r}"
        )
    assert_step_executable_contracts(name, text)
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


def _drop_exact_lines(text: str, exact_lines: list[str]) -> str:
    pending = list(exact_lines)
    kept: list[str] = []
    for line in text.splitlines(keepends=True):
        raw = line[:-1] if line.endswith("\n") else line
        if pending and raw == pending[0]:
            pending.pop(0)
            continue
        kept.append(line)
    if pending:
        raise AssertionError(f"executable lines not found for mutation: {pending!r}")
    return "".join(kept)


def _ack_fence_insert_at(text: str) -> int:
    idx = text.find("ack --phase B")
    if idx < 0:
        raise AssertionError("DURABLE_ACK command not found")
    close = text.find("\n```", idx)
    if close < 0:
        raise AssertionError("ACK fence close not found")
    insert_at = close + len("\n```")
    if text[insert_at:insert_at + 1] == "\n":
        insert_at += 1
    return insert_at


def _insert_after_ack_fence(text: str, exact_lines: list[str]) -> str:
    insert_at = _ack_fence_insert_at(text)
    block = "\n".join(exact_lines) + "\n"
    return text[:insert_at] + block + text[insert_at:]


def _insert_fenced_after_ack(text: str, exact_lines: list[str]) -> str:
    insert_at = _ack_fence_insert_at(text)
    block = "```bash\n" + "\n".join(exact_lines) + "\n```\n"
    return text[:insert_at] + block + text[insert_at:]


def _token_block(text: str) -> str:
    return text.split(START, 1)[1].split(END, 1)[0]


def _insert_fence_in_step(text: str, token: str, body: str, language: str) -> str:
    spans = {tok: (start, end) for tok, start, end in _step_spans(text)}
    if token not in spans:
        raise AssertionError(f"cannot find step {token} for mutation")
    _start, end = spans[token]
    block = f"\n```{language}\n{body.rstrip()}\n```\n"
    return text[:end] + block + text[end:]


def _duplicate_shell_command(text: str, token: str, predicate, label: str) -> str:
    body = _step_bodies(f"mutation:{token}", text)[token]
    commands = _bash_commands_in(body)
    matches = [command for command in commands if predicate(command)]
    if len(matches) != 1:
        raise AssertionError(f"{label}: expected one source command, found {matches!r}")
    return _insert_fence_in_step(text, token, matches[0], "bash")


def run_shell_semantics_mutation_tests(base: Path) -> int:
    """Run D/E/F and exact-once mutations through the production gate."""
    check_runbook_lifecycle(base)
    docs = read_docs(base)
    persist_commands = [PERSIST_INSTALL_CMD, PERSIST_SHA256_CMD]
    cases = 0
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for doc_rel in DOC_RELS:
            original = docs[doc_rel]
            prefix = doc_rel.stem

            # Mutation D: command-looking text in non-shell, Python, and untagged
            # fences is not evidence of an executable shell command.
            for label, language in (
                ("non_shell_text_fence", "text"),
                ("python_fence", "python"),
                ("untagged_fence", ""),
            ):
                deleted = _drop_exact_lines(original, persist_commands)
                body = "\n".join(persist_commands)
                mutated = _insert_fence_in_step(deleted, "PERSIST_PROJECTION_EVIDENCE", body, language)
                stage = root / f"D-{prefix}-{label}"
                _stage(base, stage, {doc_rel: mutated})
                _expect_red(f"IA-BLK-003-D:{label}:{doc_rel.name}", stage)
                cases += 1

            # Mutation E: command-shaped heredoc payloads are data, including
            # all required delimiter quoting/indentation forms.
            heredoc_forms = (
                ("quoted", "cat <<'EOF'", False),
                ("double_quoted", 'cat <<"EOF"', False),
                ("unquoted", "cat <<EOF", False),
                ("dash_tabs", "cat <<-EOF", True),
            )
            for label, opener, strip_tabs in heredoc_forms:
                deleted = _drop_exact_lines(original, persist_commands)
                payload_lines = [
                    "install -m 0400 current-event.json event-014.projection.json",
                    "sha256sum event-014.projection.json >> projection_digests.sha256",
                    "create_current_event_binding_receipt(...)",
                    "write_binding_receipt(receipt, path)",
                ]
                if strip_tabs:
                    heredoc_body = "\n".join("\t" + line for line in payload_lines + ["EOF"])
                else:
                    heredoc_body = "\n".join(payload_lines + ["EOF"])
                heredoc_fence = opener + "\n" + heredoc_body
                parsed_commands, parsed_python = _parse_shell_fence(heredoc_fence)
                payload_markers = (
                    "install -m 0400 current-event.json",
                    "sha256sum event-014.projection.json",
                    "create_current_event_binding_receipt(...)",
                    "write_binding_receipt(receipt, path)",
                )
                if any(any(marker in command for marker in payload_markers) for command in parsed_commands):
                    raise AssertionError(f"{doc_rel}: {label} heredoc payload leaked into shell commands")
                if parsed_python:
                    raise AssertionError(f"{doc_rel}: {label} cat heredoc was misclassified as Python stdin")
                mutated = _insert_fence_in_step(
                    deleted, "PERSIST_PROJECTION_EVIDENCE", heredoc_fence, "bash",
                )
                stage = root / f"E-{prefix}-{label}"
                _stage(base, stage, {doc_rel: mutated})
                _expect_red(f"IA-BLK-003-E:heredoc_{label}:{doc_rel.name}", stage)
                cases += 1

            # Mutation F: every required production operation must have one
            # unique occurrence in its owner step; same-step duplicates are red.
            duplicate_shell_specs = (
                ("REVEAL", _is_reveal_command, "reveal"),
                ("INSTALL_CURRENT_EVENT", lambda c: c == INSTALL_CURRENT_EVENT_CMD, "install_current_event"),
                ("PERSIST_PROJECTION_EVIDENCE", lambda c: c == PERSIST_INSTALL_CMD, "projection_install"),
                ("PERSIST_PROJECTION_EVIDENCE", lambda c: c == PERSIST_SHA256_CMD, "projection_sha256"),
                ("MODEL_WORK", _is_production_turn_command, "production_turn"),
                ("DURABLE_ACK", _is_ack_command, "ack"),
                ("CLEAR_BINDING", lambda c: c == CLEAR_BINDING_CMD, "clear_binding"),
            )
            for owner, predicate, label in duplicate_shell_specs:
                mutated = _duplicate_shell_command(original, owner, predicate, label)
                stage = root / f"F-{prefix}-duplicate-{label}"
                _stage(base, stage, {doc_rel: mutated})
                _expect_red(f"IA-BLK-003-F:duplicate_{label}:{doc_rel.name}", stage)
                cases += 1

            # IA-BLK-004: a shell dispatch prefix does not make a second
            # lifecycle operation semantically different. The production gate
            # must count the wrapped canonical signature and reject it.
            for owner, predicate, label in duplicate_shell_specs:
                body = _step_bodies(f"wrapper-mutation:{owner}", original)[owner]
                commands = _bash_commands_in(body)
                matches = [command for command in commands if predicate(command)]
                if len(matches) != 1:
                    raise AssertionError(
                        f"{label}: expected one canonical source command for wrapper mutation, "
                        f"found {matches!r}"
                    )
                wrapped = _insert_fence_in_step(
                    original, owner, "command " + matches[0], "bash",
                )
                stage = root / f"G-{prefix}-command-wrapper-{label}"
                _stage(base, stage, {doc_rel: wrapped})
                _expect_red(
                    f"IA-BLK-004-G:command_wrapper_duplicate_{label}:{doc_rel.name}",
                    stage,
                )
                cases += 1

            # FIXUP-001: command text behind a short-circuit control operator is
            # not executable evidence. Replace the sole canonical current-event
            # install with inert lookalikes and require the production gate red.
            for label, inert_prefix in (
                ("false_and", "false && "),
                ("true_or", "true || "),
            ):
                deleted = _drop_exact_lines(original, [INSTALL_CURRENT_EVENT_CMD])
                inert = _insert_fence_in_step(
                    deleted,
                    "INSTALL_CURRENT_EVENT",
                    inert_prefix + INSTALL_CURRENT_EVENT_CMD,
                    "bash",
                )
                stage = root / f"H-{prefix}-{label}-inert-install"
                _stage(base, stage, {doc_rel: inert})
                _expect_red(
                    f"IA-BLK-004-H:{label}_inert_install:{doc_rel.name}",
                    stage,
                )
                cases += 1

            # FIXUP-002: direct artifact signatures and step command counts
            # must also reject command-name and split variable indirection.
            indirect_specs = (
                (
                    "INSTALL_CURRENT_EVENT",
                    INSTALL_CURRENT_EVENT_CMD,
                    'cmd=install; "$cmd"' + INSTALL_CURRENT_EVENT_CMD[len("install"):],
                    "indirect_install_current_event",
                ),
                (
                    "PERSIST_PROJECTION_EVIDENCE",
                    PERSIST_INSTALL_CMD,
                    'cmd=install; "$cmd"' + PERSIST_INSTALL_CMD[len("install"):],
                    "indirect_projection_install",
                ),
                (
                    "PERSIST_PROJECTION_EVIDENCE",
                    PERSIST_SHA256_CMD,
                    'cmd=sha256sum; "$cmd"' + PERSIST_SHA256_CMD[len("sha256sum"):],
                    "indirect_projection_sha256",
                ),
                (
                    "CLEAR_BINDING",
                    CLEAR_BINDING_CMD,
                    'cmd=rm; "$cmd"' + CLEAR_BINDING_CMD[len("rm"):],
                    "indirect_clear_binding",
                ),
            )
            for owner, _canonical, indirect_command, label in indirect_specs:
                mutated = _insert_fence_in_step(
                    original, owner, indirect_command, "bash",
                )
                stage = root / f"I-{prefix}-{label}"
                _stage(base, stage, {doc_rel: mutated})
                _expect_red(
                    f"IA-BLK-004-I:{label}:{doc_rel.name}",
                    stage,
                )
                cases += 1

            split_indirect = _insert_fence_in_step(
                original,
                "INSTALL_CURRENT_EVENT",
                '\n'.join((
                    'src="$RUN_ROOT/reveal.json"',
                    'dst="$RUN_ROOT/current-event.json"',
                    'cmd=install',
                    '"$cmd" -m 0400 "$src" "$dst"',
                )),
                "bash",
            )
            stage = root / f"J-{prefix}-split-indirect-install"
            _stage(base, stage, {doc_rel: split_indirect})
            _expect_red(
                f"IA-BLK-004-J:split_indirect_install:{doc_rel.name}",
                stage,
            )
            cases += 1

            receipt_line = 'write_binding_receipt(receipt, os.environ["AIOS_CURRENT_EVENT_BINDING_PATH"])'
            if original.count(receipt_line) != 1:
                raise AssertionError(f"{doc_rel}: expected one receipt-write anchor")
            duplicated_write = original.replace(receipt_line, receipt_line + "\n" + receipt_line, 1)
            stage = root / f"F-{prefix}-duplicate-receipt-write"
            _stage(base, stage, {doc_rel: duplicated_write})
            _expect_red(f"IA-BLK-003-F:duplicate_receipt_write:{doc_rel.name}", stage)
            cases += 1

            receipt_variable = "proj" if doc_rel.name == "b_startup_procedure.md" else "projection"
            duplicate_create = (
                "receipt_duplicate = create_current_event_binding_receipt(\n"
                f"    {receipt_variable},\n"
                '    b_session_id=os.environ["AIOS_B_SESSION_ID"],\n'
                '    release_state_path=os.environ["AIOS_RELEASE_STATE_PATH"],\n'
                ")\n"
            )
            if receipt_line not in original:
                raise AssertionError(f"{doc_rel}: receipt-write anchor missing for create duplicate")
            duplicated_create = original.replace(receipt_line, duplicate_create + receipt_line, 1)
            stage = root / f"F-{prefix}-duplicate-receipt-create"
            _stage(base, stage, {doc_rel: duplicated_create})
            _expect_red(f"IA-BLK-003-F:duplicate_receipt_create:{doc_rel.name}", stage)
            cases += 1

            validate_anchor = 'print("CURRENT_EVENT_BINDING_VERIFIED'
            validate_at = original.find(validate_anchor)
            if validate_at < 0:
                raise AssertionError(f"{doc_rel}: verification print anchor missing")
            event_variable = "ev" if doc_rel.name == "b_startup_procedure.md" else "event"
            duplicate_validate = (
                "validate_current_event_binding(\n"
                f"    {event_variable}, os.environ[\"AIOS_B_SESSION_ID\"],\n"
                '    release_state_path=os.environ["AIOS_RELEASE_STATE_PATH"],\n'
                '    binding_receipt_path=os.environ["AIOS_CURRENT_EVENT_BINDING_PATH"],\n'
                ")\n"
            )
            duplicated_validate = original[:validate_at] + duplicate_validate + original[validate_at:]
            stage = root / f"F-{prefix}-duplicate-binding-validate"
            _stage(base, stage, {doc_rel: duplicated_validate})
            _expect_red(f"IA-BLK-003-F:duplicate_binding_validate:{doc_rel.name}", stage)
            cases += 1

    print(f"RUNBOOK_SHELL_SEMANTICS_MUTATION_RED_PASS cases={cases}")
    return cases


def run_mutation_self_tests(base: Path) -> int:
    check_runbook_lifecycle(base)
    docs = read_docs(base)
    rel = Path("procedure/per_cursor_interaction.md")
    original = docs[rel]
    count = 0
    executable_count = 0
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)

        swapped = _swap_steps(original, "INSTALL_CURRENT_EVENT", "CREATE_BINDING_RECEIPT")
        if _token_block(swapped) != _token_block(original):
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
            "\n```bash\n"
            "create_current_event_binding_receipt(...)\n"
            "write_binding_receipt(...)\n"
            "cp \"$RUN_ROOT/reveal.json\" \"$RUN_ROOT/current-event.json\"\n"
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

        persist_lines = [PERSIST_INSTALL_CMD, PERSIST_SHA256_CMD]
        # Mutation A — delete the two executable persist commands, keep token/heading/prose.
        for doc_rel in DOC_RELS:
            deleted = _drop_exact_lines(docs[doc_rel], persist_lines)
            if "PERSIST_PROJECTION_EVIDENCE" not in deleted or ".projection.json" not in deleted:
                raise AssertionError(f"{doc_rel}: delete mutation removed heading or prose")
            if _token_block(deleted) != _token_block(docs[doc_rel]):
                raise AssertionError(f"{doc_rel}: delete mutation rewrote the token block")
            if PERSIST_INSTALL_CMD in deleted or PERSIST_SHA256_CMD in deleted:
                raise AssertionError(f"{doc_rel}: executable persist lines still present")
            stage = root / f"mutA-{doc_rel.name}"
            _stage(base, stage, {doc_rel: deleted})
            _expect_red(f"IA-BLK-003-A:delete_executable_persist:{doc_rel.name}", stage)
            executable_count += 1

        # Mutation B — move the two executable persist commands to after DURABLE_ACK.
        for doc_rel in DOC_RELS:
            moved = _insert_after_ack_fence(_drop_exact_lines(docs[doc_rel], persist_lines), persist_lines)
            if _token_block(moved) != _token_block(docs[doc_rel]):
                raise AssertionError(f"{doc_rel}: move mutation rewrote the token block")
            if extract_heading_tokens(str(doc_rel), moved) != EXPECTED_TOKENS:
                raise AssertionError(f"{doc_rel}: move mutation rewrote headings")
            ack_at = moved.find("ack --phase B")
            persist_at = moved.find(PERSIST_INSTALL_CMD)
            if not (0 <= ack_at < persist_at):
                raise AssertionError(f"{doc_rel}: persist command was not moved after ACK")
            stage = root / f"mutB-{doc_rel.name}"
            _stage(base, stage, {doc_rel: moved})
            _expect_red(f"IA-BLK-003-B:persist_after_ack:{doc_rel.name}", stage)
            executable_count += 1

        # Mutation C — comment mentions current-event.json before a receipt-first cp.
        hidden = (
            "\n```bash\n"
            "# current-event.json must exist, but this chain is intentionally wrong\n"
            "create_current_event_binding_receipt(...)\n"
            "write_binding_receipt(...)\n"
            "cp \"$RUN_ROOT/reveal.json\" \"$RUN_ROOT/current-event.json\"\n"
            "```\n"
        )
        for doc_rel in DOC_RELS:
            stage = root / f"mutC-{doc_rel.name}"
            _stage(base, stage, {doc_rel: docs[doc_rel] + hidden})
            _expect_red(f"IA-BLK-003-C:comment_hidden_receipt_first:{doc_rel.name}", stage)
            executable_count += 1

        extras: list[tuple[str, Path, str]] = []
        receipt_line = 'write_binding_receipt(receipt, os.environ["AIOS_CURRENT_EVENT_BINDING_PATH"])'
        for doc_rel in DOC_RELS:
            extras.append((
                f"delete_sha256_keep_install:{doc_rel.name}",
                doc_rel,
                _drop_exact_lines(docs[doc_rel], [PERSIST_SHA256_CMD]),
            ))
            extras.append((
                f"delete_install_keep_sha256:{doc_rel.name}",
                doc_rel,
                _drop_exact_lines(docs[doc_rel], [PERSIST_INSTALL_CMD]),
            ))
            bad_dest = docs[doc_rel].replace(
                '"$RUN_ROOT/evidence/event-$(printf \'%03d\' "$SEQ").projection.json"',
                '"$RUN_ROOT/evidence/event-$(printf \'%03d\' "$SEQ").not-a-projection.json"',
                1,
            )
            if bad_dest == docs[doc_rel]:
                raise AssertionError(f"{doc_rel}: destination mutation did not edit the install line")
            extras.append((f"wrong_persist_destination:{doc_rel.name}", doc_rel, bad_dest))
            bad_source = docs[doc_rel].replace(
                PERSIST_INSTALL_CMD,
                PERSIST_INSTALL_CMD.replace('"$RUN_ROOT/current-event.json"', '"$RUN_ROOT/reveal.json"', 1),
                1,
            )
            if bad_source == docs[doc_rel]:
                raise AssertionError(f"{doc_rel}: source mutation did not edit the install line")
            extras.append((f"persist_source_reveal_not_current_event:{doc_rel.name}", doc_rel, bad_source))
            if receipt_line not in docs[doc_rel]:
                raise AssertionError(f"{doc_rel}: receipt command line missing")
            import_suffix = ", write_binding_receipt"
            if docs[doc_rel].count(import_suffix) != 1:
                raise AssertionError(f"{doc_rel}: expected exactly one receipt import suffix")
            without_receipt = docs[doc_rel].replace(import_suffix, "", 1).replace(receipt_line + "\n", "", 1)
            if receipt_line in without_receipt or import_suffix in without_receipt:
                raise AssertionError(f"{doc_rel}: receipt command was not fully moved")
            insert_at = without_receipt.find(PERSIST_INSTALL_CMD)
            if insert_at < 0:
                raise AssertionError(f"{doc_rel}: cannot place receipt command before projection")
            moved_receipt = without_receipt[:insert_at] + receipt_line + "\n" + without_receipt[insert_at:]
            extras.append((f"receipt_command_before_projection:{doc_rel.name}", doc_rel, moved_receipt))
            copied = _insert_fenced_after_ack(docs[doc_rel], [PERSIST_INSTALL_CMD])
            if copied.count(PERSIST_INSTALL_CMD) != docs[doc_rel].count(PERSIST_INSTALL_CMD) + 1:
                raise AssertionError(f"{doc_rel}: wrong-step copy did not keep the original persist command")
            if "release_operator.py ack --phase B" not in copied and "ack --phase B" not in copied:
                raise AssertionError(f"{doc_rel}: wrong-step copy destroyed the ACK command")
            extras.append((f"persist_command_also_in_ack_step:{doc_rel.name}", doc_rel, copied))

        for label, doc_rel, mutated in extras:
            stage = root / f"extra-{executable_count}"
            _stage(base, stage, {doc_rel: mutated})
            _expect_red(label, stage)
            executable_count += 1

    print(f"RUNBOOK_EXECUTABLE_MUTATION_RED_PASS cases={executable_count}")
    shell_semantics_count = run_shell_semantics_mutation_tests(base)
    return count + executable_count + shell_semantics_count


def main() -> int:
    parser = argparse.ArgumentParser(description="Cross-document Phase-B lifecycle checker")
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    tokens = check_runbook_lifecycle(args.base)
    print(
        "RUNBOOK_CROSS_DOCUMENT_ORDER_PASS "
        + ">".join(tokens)
        + " sources=token_block,headings,step_body_executables,executable_chains"
        + " finish_clause_between_model_work_and_ack=True"
        + " authority=b_startup_procedure.md§7"
    )
    if args.self_test:
        run_mutation_self_tests(args.base)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
