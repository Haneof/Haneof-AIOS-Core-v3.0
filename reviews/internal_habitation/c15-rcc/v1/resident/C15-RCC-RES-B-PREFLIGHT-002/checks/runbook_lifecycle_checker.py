#!/usr/bin/env python3
"""Cross-document Phase-B lifecycle gate.

Production entrypoint and every mutation self-test call check_runbook_lifecycle().
The self-test writes disposable copies and invokes that same function; it does not
reimplement the comparison.

CORRECTIVE-012 / IA-BLK-003: a generic substring such as ".projection.json" and a
document-wide first occurrence are not executable proof. Each lifecycle step is
sliced from its own heading, and only executable commands inside that step body
satisfy that step. Fenced bash/arrow sequences are parsed after comments, blank
lines, and echo-only lines are removed, so a comment that mentions
current-event.json cannot hide a later receipt-first install.
"""
from __future__ import annotations

import argparse
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
_FENCE_LANG = re.compile(r"^(?:bash|sh|shell)\s*$", re.I)
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


def _join_continuations(lines: list[str]) -> list[str]:
    joined: list[str] = []
    buf = ""
    for line in lines:
        if line.rstrip().endswith("\\"):
            buf += line.rstrip()[:-1].strip() + " "
            continue
        buf += line.strip() if buf else line
        joined.append(buf)
        buf = ""
    if buf:
        joined.append(buf.strip())
    return joined


def _is_echo_only(line: str) -> bool:
    body = line.strip()
    body = _ASSIGN_PREFIX.sub("", body)
    return body == "echo" or body.startswith("echo ")


def _executable_bash_commands(fence_body: str) -> list[str]:
    lines = fence_body.splitlines()
    if lines and _FENCE_LANG.match(lines[0].strip()):
        lines = lines[1:]
    commands: list[str] = []
    for line in _join_continuations(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if _is_echo_only(stripped):
            continue
        commands.append(stripped)
    return commands


def _arrow_segments(fence_body: str) -> list[str]:
    segments: list[str] = []
    for part in fence_body.split("→"):
        stripped = part.strip().strip("`")
        if not stripped or stripped.startswith("#"):
            continue
        stripped = re.sub(r"^(?:bash|sh|shell)\s*", "", stripped, count=1, flags=re.I).strip()
        if not stripped or stripped.startswith("#"):
            continue
        segments.append(stripped)
    return segments


def _iter_fences(text: str) -> list[tuple[str, str]]:
    """Return (kind, body) for every fenced block. kind is 'arrow' or 'bash'."""
    parts = text.split("```")
    fences: list[tuple[str, str]] = []
    for body in parts[1::2]:
        kind = "arrow" if "→" in body else "bash"
        fences.append((kind, body))
    return fences


def _bash_commands_in(text: str) -> list[str]:
    commands: list[str] = []
    for kind, body in _iter_fences(text):
        if kind == "bash":
            commands.extend(_executable_bash_commands(body))
    return commands


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
    """Fail when one executable fence/chain installs current-event after receipt.

    Comments, blank lines, and echo-only lines are not commands. A comment that
    mentions current-event.json therefore cannot mask a later cp/install.
    """
    for index, (kind, body) in enumerate(_iter_fences(text), 1):
        if kind == "arrow":
            commands = _arrow_segments(body)
        else:
            commands = _executable_bash_commands(body)
        if _sequence_is_receipt_before_install(commands):
            raise LifecycleCheckError(
                f"{name}: executable {kind} fence #{index} creates the binding receipt "
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


def assert_step_executable_contracts(name: str, text: str) -> None:
    bodies = _step_bodies(name, text)
    by_token = {token: _bash_commands_in(body) for token, body in bodies.items()}

    _require_command(
        name, "REVEAL", by_token["REVEAL"],
        lambda c: "release_operator.py reveal --phase B" in c,
        "release_operator.py reveal --phase B",
    )
    _require_command(
        name, "INSTALL_CURRENT_EVENT", by_token["INSTALL_CURRENT_EVENT"],
        lambda c: c == INSTALL_CURRENT_EVENT_CMD,
        INSTALL_CURRENT_EVENT_CMD,
    )
    _require_command(
        name, "PERSIST_PROJECTION_EVIDENCE", by_token["PERSIST_PROJECTION_EVIDENCE"],
        lambda c: c == PERSIST_INSTALL_CMD,
        "install current-event.json -> evidence/event-%03d.projection.json",
    )
    _require_command(
        name, "PERSIST_PROJECTION_EVIDENCE", by_token["PERSIST_PROJECTION_EVIDENCE"],
        lambda c: c == PERSIST_SHA256_CMD,
        "sha256sum of that projection artifact appended to projection_digests.sha256",
    )
    _require_command(
        name, "CREATE_BINDING_RECEIPT", by_token["CREATE_BINDING_RECEIPT"],
        lambda c: "create_current_event_binding_receipt" in c,
        "create_current_event_binding_receipt",
    )
    _require_command(
        name, "CREATE_BINDING_RECEIPT", by_token["CREATE_BINDING_RECEIPT"],
        lambda c: "write_binding_receipt" in c,
        "write_binding_receipt",
    )
    _forbid_command(
        name, "CREATE_BINDING_RECEIPT", by_token["CREATE_BINDING_RECEIPT"],
        _is_event_install_command,
        "install/cp of current-event.json belongs in INSTALL_CURRENT_EVENT, not after receipt creation",
    )
    _require_command(
        name, "VERIFY_BINDING", by_token["VERIFY_BINDING"],
        lambda c: "validate_current_event_binding(" in c,
        "validate_current_event_binding(",
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
    _require_command(
        name, "MODEL_WORK", by_token["MODEL_WORK"],
        lambda c: "turn --session" in c,
        "production headless turn --session",
    )
    _require_command(
        name, "MODEL_WORK", by_token["MODEL_WORK"],
        lambda c: "headless_production_handler" in c,
        "headless_production_handler",
    )
    _require_command(
        name, "DURABLE_ACK", by_token["DURABLE_ACK"],
        lambda c: "release_operator.py ack --phase B" in c,
        "release_operator.py ack --phase B",
    )
    _require_command(
        name, "CLEAR_BINDING", by_token["CLEAR_BINDING"],
        lambda c: c == CLEAR_BINDING_CMD,
        CLEAR_BINDING_CMD,
    )

    # A command that still exists somewhere in the document does not satisfy the
    # step it was moved out of, and must not satisfy a different step either.
    exclusive = (
        ("INSTALL_CURRENT_EVENT", lambda c: c == INSTALL_CURRENT_EVENT_CMD, "install reveal.json -> current-event.json"),
        ("PERSIST_PROJECTION_EVIDENCE", lambda c: c == PERSIST_INSTALL_CMD, "projection persist install"),
        ("PERSIST_PROJECTION_EVIDENCE", lambda c: c == PERSIST_SHA256_CMD, "projection sha256sum"),
        ("CREATE_BINDING_RECEIPT", lambda c: "write_binding_receipt" in c, "write_binding_receipt"),
        ("CREATE_BINDING_RECEIPT", lambda c: "create_current_event_binding_receipt" in c, "create_current_event_binding_receipt"),
        ("VERIFY_BINDING", lambda c: "validate_current_event_binding(" in c, "validate_current_event_binding("),
        ("MODEL_WORK", lambda c: "turn --session" in c, "turn --session"),
        ("DURABLE_ACK", lambda c: "ack --phase B" in c, "ack --phase B"),
        ("CLEAR_BINDING", lambda c: c == CLEAR_BINDING_CMD, "rm current-event.json binding"),
        ("REVEAL", lambda c: "reveal --phase B" in c, "reveal --phase B"),
    )
    for owner, predicate, label in exclusive:
        found = [token for token, commands in by_token.items() if any(predicate(c) for c in commands)]
        if found != [owner]:
            raise LifecycleCheckError(
                f"{name}: executable command {label} must appear only in {owner} step body, found in {found!r}"
            )


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
    return count + executable_count


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
