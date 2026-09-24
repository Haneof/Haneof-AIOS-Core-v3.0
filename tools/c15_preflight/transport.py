"""Synchronous, transport-only model callback and operator evidence observer.

No provider, answers, default silence, replay, scheduler, release operator, or
Resident launcher is implemented here. Stream handles must be supplied by a
separately reviewed host. Same-user streams are NOT an isolation boundary.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import os
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, TextIO
from uuid import uuid4

from pydantic import BaseModel
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective, RuntimeSnapshot


def plain(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: plain(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, Enum):
        return plain(value.value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        if any(not isinstance(k, str) for k in value):
            raise TypeError("non-string JSON key")
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise TypeError(f"unsupported evidence type: {type(value).__name__}")


def encode(value: Any) -> str:
    return json.dumps(plain(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


class Trace:
    """Exclusive new operator log; fsync before further execution; no resume fiction.

    Hash chaining detects accidental edits, not a malicious operator. Keep private
    traces outside Git. Runtime crash recovery/final freeze are NOT implemented.
    """
    def __init__(self, path: Path, revision: Callable[[], int]):
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        # Unbuffered journal: close after a failure must not flush pending text
        # behind our back. No uncertain tail is retried or repaired.
        self.file = os.fdopen(fd, "wb", buffering=0)
        self.path = path
        self.revision = revision
        self.previous = "0" * 64
        self.sequence = 0
        self.failure: str | None = None
        self.io_failure: str | None = None

    def append(self, kind: str, data: Any) -> None:
        if self.io_failure is not None:
            raise JournalPoisoned("journal I/O outcome uncertain; no further appends")
        body = {"sequence": self.sequence + 1, "kind": kind,
                "at": datetime.now(timezone.utc).isoformat(),
                "world_revision": int(self.revision()), "previous": self.previous,
                "data": plain(data)}
        digest = hashlib.sha256(encode(body).encode()).hexdigest()
        frame = (encode({**body, "sha256": digest}) + "\n").encode("utf-8")
        try:
            count = self.file.write(frame)
            if type(count) is not int or count != len(frame):
                raise OSError("incomplete journal write; tail is uncertain")
            self.file.flush()
            os.fsync(self.file.fileno())
        except BaseException as exc:
            self.io_failure = self.failure = f"{type(exc).__name__}: {exc}"
            raise
        self.previous = digest
        self.sequence += 1

    def close(self) -> None:
        try:
            self.file.close()
        except BaseException:
            # If journal already poisoned, close must not raise or repair tail.
            if self.io_failure is None:
                raise
            try:
                # Best-effort raw close without second flush attempt.
                import os as _os
                _os.close(self.file.fileno())
            except BaseException:
                pass


class JournalPoisoned(RuntimeError):
    pass


class TransportError(ValueError):
    pass


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise TransportError("duplicate JSON key")
        result[key] = value
    return result


def reject_constant(_):
    raise TransportError("non-finite JSON number")


def directive(body: Any) -> ModelDirective:
    """Only explicit structural choices. Self-declared usage/identity is rejected."""
    if not isinstance(body, dict) or len(body) != 1:
        raise TransportError("exactly one response, silence or capability_calls required")
    if "response" in body:
        text = body["response"]
        if not isinstance(text, str) or not text.strip():
            raise TransportError("response must be non-blank text")
        return ModelDirective(response=text)
    if body.get("silence") is True:
        return ModelDirective(silence=True)
    calls = body.get("capability_calls")
    if not isinstance(calls, list) or not calls:
        raise TransportError("missing explicit directive")
    parsed = []
    for call in calls:
        if not isinstance(call, dict) or not {"name", "arguments"} <= set(call) <= {"name", "arguments", "call_id"}:
            raise TransportError("invalid capability shape")
        if not isinstance(call["name"], str) or not call["name"].strip() or not isinstance(call["arguments"], dict):
            raise TransportError("invalid capability name/arguments")
        cid = call.get("call_id")
        if cid is not None and (not isinstance(cid, str) or not cid.strip()):
            raise TransportError("invalid call_id")
        parsed.append(CapabilityCall(**call))
    return ModelDirective(capability_calls=tuple(parsed))


class StreamBridge:
    """Blocks on a genuine callback; EOF/invalid return aborts, never synthesizes."""
    def __init__(self, incoming: TextIO, outgoing: TextIO, trace: Trace, *, max_reply_chars: int = 1_000_000):
        if max_reply_chars < 1:
            raise ValueError("max_reply_chars must be positive")
        self.incoming, self.outgoing, self.trace = incoming, outgoing, trace
        self.max_reply_chars = max_reply_chars

    def _request(self, kind: str, payload: Any, parse: Callable) -> Any:
        if self.trace.failure is not None:
            raise TransportError("transport poisoned; explicit operator recovery required")
        request_id = uuid4().hex
        serialized = plain(payload)
        input_sha256 = hashlib.sha256(encode(serialized).encode()).hexdigest()
        request = {"protocol": "c15-transport-v2", "request_id": request_id,
                   "kind": kind, "input_sha256": input_sha256, "input": serialized}
        try:
            self.trace.append("model_request", request)
            frame = encode(request) + "\n"
            offset = 0
            # Strict positive progress bounds iterations by frame length. Never
            # resend a prefix; no reply read until the entire frame is flushed.
            while offset < len(frame):
                try:
                    count = self.outgoing.write(frame[offset:])
                except BaseException as write_exc:
                    raise TransportError(f"send failed: {type(write_exc).__name__}: {write_exc}") from write_exc
                if type(count) is not int or not 0 < count <= len(frame) - offset:
                    raise TransportError("invalid send progress")
                offset += count
            try:
                self.outgoing.flush()
            except BaseException as flush_exc:
                raise TransportError(f"flush failed: {type(flush_exc).__name__}: {flush_exc}") from flush_exc
            raw = self.incoming.readline(self.max_reply_chars + 1)
            if not raw:
                raise TransportError("missing response: EOF")
            if len(raw) > self.max_reply_chars or not raw.endswith("\n"):
                raise TransportError("oversized or incomplete response frame")
            self.trace.append("model_return_raw", {"request_id": request_id, "raw": raw})
            value = json.loads(raw, object_pairs_hook=strict_object, parse_constant=reject_constant)
            if (not isinstance(value, dict) or set(value) != {"request_id", "kind", "input_sha256", "output"}
                    or any(value[k] != request[k] for k in ("request_id", "kind", "input_sha256"))):
                raise TransportError("response request binding mismatch")
            result = parse(value["output"])
            self.trace.append("model_return_validated", {"request_id": request_id, "output": result,
                              "provider_identity": "UNKNOWN", "usage": "UNKNOWN"})
            return result
        except BaseException as exc:
            if self.trace.failure is None:
                self.trace.failure = f"{type(exc).__name__}: {exc}"
            if self.trace.io_failure is None:
                try:
                    self.trace.append("model_error", {"request_id": request_id, "error_type": type(exc).__name__, "message": str(exc)})
                except BaseException:
                    pass
            if isinstance(exc, TransportError):
                raise
            raise TransportError(f"{type(exc).__name__}: {exc}") from exc

    def model(self, snapshot: RuntimeSnapshot) -> ModelDirective:
        if not isinstance(snapshot, RuntimeSnapshot):
            raise TypeError("a genuine RuntimeSnapshot is required")
        return self._request("runtime", snapshot, directive)

    @staticmethod
    def _summary(output: Any) -> str:
        if not isinstance(output, dict) or set(output) != {"text"} or not isinstance(output["text"], str) or not output["text"].strip():
            raise TransportError("explicit summary text required")
        return output["text"]

    def round_summary(self, request) -> str:
        from aios_core.context.continuity import RoundSummaryRequest
        if not isinstance(request, RoundSummaryRequest):
            raise TypeError("RoundSummaryRequest required")
        return self._request("round_summary", request, self._summary)

    def dimension_summary(self, request) -> str:
        from aios_core.summaries.dimension_summary import DimensionSummaryInput
        if not isinstance(request, DimensionSummaryInput):
            raise TypeError("DimensionSummaryInput required")
        return self._request("dimension_summary", request, self._summary)


class RuntimeRecorder:
    """Observe existing Runtime entrypoints, not a clock/release driver.

    Core keeps all capability policy, budgets and metering. Registry interception
    records actual invocations; Core-denied calls remain in snapshots/final result.
    Single-threaded use only. The surrounding host owns timeout/cancellation.
    """
    METHODS = {"run_turn", "run_due_dimension_summaries", "dispatch_next_pending_wake", "run_periodic_review", "run_wake"}

    def __init__(self, runtime, trace: Trace):
        self.runtime, self.trace = runtime, trace

    def call(self, method: str, **kwargs):
        if method not in self.METHODS:
            raise ValueError("unsupported runtime entrypoint")
        runtime, trace = self.runtime, self.trace
        if trace.failure is not None:
            raise TransportError("failed callback/phase prohibits subsequent execution")
        trace.append("runtime_input", {"method": method, "arguments": kwargs})
        registry = runtime.cognitive_runtime.registry
        original = registry.invoke

        def invoke(call):
            trace.append("capability_call", call)
            result = original(call)
            trace.append("capability_result", result)
            return result

        registry.invoke = invoke
        try:
            result = getattr(runtime, method)(**kwargs)
            if trace.failure is not None or getattr(result, "continuity_summary_error", None):
                if trace.io_failure is None:
                    trace.append("runtime_return_failed", {"method": method, "result": result})
                raise TransportError("Core caught callback failure; phase is not complete")
            trace.append("runtime_result", {"method": method, "result": result})
            return result
        except BaseException as exc:
            trace.failure = f"{type(exc).__name__}: {exc}"
            if trace.io_failure is None:
                trace.append("runtime_error", {"method": method, "error_type": type(exc).__name__, "message": str(exc)})
            raise
        finally:
            registry.invoke = original
            if trace.io_failure is None:
                trace.append("runtime_state", {
                    "index_watermark": runtime.index.watermark(),
                    "metering": runtime.metering.list_model_calls(subject_id=runtime.subject_id),
                })
