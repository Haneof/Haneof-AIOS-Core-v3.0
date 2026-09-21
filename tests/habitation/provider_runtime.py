"""Provider-backed P16 resident adapters.

This module is benchmark infrastructure. It translates AIOS RuntimeSnapshot and
CapabilitySpec metadata to provider APIs without changing Core world/runtime
semantics. API keys are read from process environment (or injected only in tests)
and are never serialized into provenance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from typing import Any, Callable, Mapping, Sequence
from urllib import error as urllib_error
from urllib import request as urllib_request

from aios_core.runtime.capabilities import CapabilityCall, CapabilityResult
from aios_core.runtime.cognitive_runtime import ModelCallProvenance, ModelDirective, ModelUsage, RuntimeSnapshot


SILENCE_TOKEN = "<AIOS_SILENCE>"
_SUPPORTED_PROVIDERS = frozenset({"openai", "anthropic", "gemini"})
_DEFAULT_ENDPOINTS = {
    "openai": "https://api.openai.com/v1/responses",
    "anthropic": "https://api.anthropic.com/v1/messages",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/interactions",
}
_DEFAULT_KEY_ENVS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


class ProviderProtocolError(RuntimeError):
    """Provider response or AIOS/provider contract is malformed."""


class ProviderTransportError(RuntimeError):
    """HTTP/transport failure with no secret-bearing request headers."""


JsonTransport = Callable[
    [str, Mapping[str, str], Mapping[str, Any], float],
    Mapping[str, Any],
]


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _safe_json_value(value: Any) -> Any:
    return json.loads(_canonical_json(value))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _split_top_level(text: str, separator: str = ",") -> list[str]:
    parts: list[str] = []
    depth_curly = 0
    depth_square = 0
    start = 0
    for index, char in enumerate(text):
        if char == "{":
            depth_curly += 1
        elif char == "}":
            depth_curly -= 1
        elif char == "[":
            depth_square += 1
        elif char == "]":
            depth_square -= 1
        elif (
            char == separator
            and depth_curly == 0
            and depth_square == 0
        ):
            parts.append(text[start:index].strip())
            start = index + 1
    parts.append(text[start:].strip())
    return [part for part in parts if part]


def _schema_from_expr(raw: str) -> tuple[dict[str, Any], bool]:
    """Translate AIOS capability shorthand to JSON Schema.

    Returns (schema, optional). Unknown shorthand fails closed so a provider adapter
    can never silently weaken a Core capability contract.
    """

    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("capability schema expression must be non-blank")
    expr = raw.strip()
    optional = expr.endswith("?")
    if optional:
        expr = expr[:-1].strip()

    if expr == "string":
        return {"type": "string"}, optional
    if expr == "integer":
        return {"type": "integer"}, optional
    if expr == "number":
        return {"type": "number"}, optional
    if expr == "boolean":
        return {"type": "boolean"}, optional
    if expr == "object":
        return {"type": "object", "additionalProperties": True}, optional
    if expr == "TemporalExtent object":
        return {
            "type": "object",
            "properties": {
                "start": {"type": "string", "format": "date-time"},
                "end": {"type": "string", "format": "date-time"},
                "precision": {"type": "string"},
                "timezone_name": {"type": "string"},
                "unknown": {"type": "boolean"},
            },
            "additionalProperties": False,
        }, optional
    if expr == "json value":
        return {
            "anyOf": [
                {"type": "string"},
                {"type": "number"},
                {"type": "boolean"},
                {"type": "object", "additionalProperties": True},
                {"type": "array"},
                {"type": "null"},
            ]
        }, optional
    if expr == "object[number]":
        return {
            "type": "object",
            "additionalProperties": {"type": "number"},
        }, optional
    if expr == "ISO-8601 datetime":
        return {"type": "string", "format": "date-time"}, optional
    if expr == "number[0,1]":
        return {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
        }, optional
    if expr == "string starting dim:":
        return {"type": "string", "pattern": "^dim:"}, optional

    if expr.startswith("array[") and expr.endswith("]"):
        inner = expr[6:-1].strip()
        item_schema, item_optional = _schema_from_expr(inner)
        if item_optional:
            raise ValueError("array item schema cannot be optional")
        return {"type": "array", "items": item_schema}, optional

    if expr.startswith("{") and expr.endswith("}"):
        inner = expr[1:-1].strip()
        properties: dict[str, Any] = {}
        required: list[str] = []
        for part in _split_top_level(inner):
            if ":" not in part:
                raise ValueError(f"invalid object schema field: {part!r}")
            name, field_expr = part.split(":", 1)
            field_name = name.strip()
            if not field_name:
                raise ValueError("object schema field name must not be blank")
            field_schema, field_optional = _schema_from_expr(field_expr.strip())
            properties[field_name] = field_schema
            if not field_optional:
                required.append(field_name)
        schema: dict[str, Any] = {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
        }
        if required:
            schema["required"] = required
        return schema, optional

    if "|" in expr:
        values = [item.strip() for item in expr.split("|")]
        if not values or any(not item for item in values):
            raise ValueError(f"invalid enum schema expression: {raw!r}")
        return {"type": "string", "enum": values}, optional

    raise ValueError(f"unsupported capability schema expression: {raw!r}")


def capability_input_json_schema(
    input_schema: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(input_schema, Mapping):
        raise TypeError("capability input_schema must be a mapping")
    properties: dict[str, Any] = {}
    required: list[str] = []
    for name, raw_expr in input_schema.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("capability input field names must be non-blank strings")
        if not isinstance(raw_expr, str):
            raise ValueError(
                f"capability field {name!r} must use a string shorthand schema"
            )
        schema, optional = _schema_from_expr(raw_expr)
        properties[name] = schema
        if not optional:
            required.append(name)
    result: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        result["required"] = required
    return result


def provider_tools(
    capability_catalog: Sequence[Mapping[str, Any]],
    *,
    provider: str,
) -> list[dict[str, Any]]:
    if provider not in _SUPPORTED_PROVIDERS:
        raise ValueError(f"unsupported provider: {provider}")
    tools: list[dict[str, Any]] = []
    for item in capability_catalog:
        name = item.get("name")
        description = item.get("description")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("capability catalog entry missing name")
        if not isinstance(description, str) or not description.strip():
            raise ValueError(f"capability {name} missing description")
        schema = capability_input_json_schema(item.get("input_schema", {}))
        if provider == "openai":
            tools.append(
                {
                    "type": "function",
                    "name": name,
                    "description": description,
                    "parameters": schema,
                    "strict": False,
                }
            )
        elif provider == "anthropic":
            tools.append(
                {
                    "name": name,
                    "description": description,
                    "input_schema": schema,
                }
            )
        else:
            tools.append(
                {
                    "type": "function",
                    "name": name,
                    "description": description,
                    "parameters": schema,
                }
            )
    return tools


@dataclass(frozen=True, slots=True)
class ProviderConfig:
    provider: str
    model: str
    endpoint: str | None = None
    api_key_env: str | None = None
    api_version: str | None = None
    max_output_tokens: int = 2048
    timeout_seconds: float = 120.0
    temperature: float | None = None
    store: bool = True

    def __post_init__(self) -> None:
        provider = self.provider.strip().lower() if isinstance(self.provider, str) else ""
        if provider not in _SUPPORTED_PROVIDERS:
            raise ValueError(f"unsupported provider: {self.provider!r}")
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("provider model must be non-blank")
        if self.max_output_tokens < 1:
            raise ValueError("max_output_tokens must be >= 1")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")
        if self.temperature is not None and not isinstance(
            self.temperature, (int, float)
        ):
            raise ValueError("temperature must be numeric when provided")
        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "model", self.model.strip())
        if self.endpoint is None:
            object.__setattr__(self, "endpoint", _DEFAULT_ENDPOINTS[provider])
        if self.api_key_env is None:
            object.__setattr__(self, "api_key_env", _DEFAULT_KEY_ENVS[provider])
        if provider == "anthropic" and self.api_version is None:
            object.__setattr__(self, "api_version", "2023-06-01")

    @property
    def model_id(self) -> str:
        return f"{self.provider}/{self.model}"

    def public_config(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "model_id": self.model_id,
            "endpoint": self.endpoint,
            "api_key_env": self.api_key_env,
            "api_version": self.api_version,
            "max_output_tokens": self.max_output_tokens,
            "timeout_seconds": self.timeout_seconds,
            "temperature": self.temperature,
            "store": self.store,
        }

    @property
    def config_fingerprint(self) -> str:
        raw = _canonical_json(self.public_config()).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class ProviderRequestRecord:
    sequence: int
    purpose: str
    requested_at: str
    completed_at: str
    response_id: str | None
    usage: Mapping[str, Any] = field(default_factory=dict)
    error_type: str | None = None
    error_message: str | None = None


def _non_negative_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _model_usage(
    provider: str,
    response: Mapping[str, Any],
    *,
    model: str,
) -> ModelUsage | None:
    """Normalize only exact provider-reported token usage.

    Unknown or incomplete shapes return None rather than estimating tokens.
    """

    raw = response.get("usage")
    if not isinstance(raw, Mapping):
        raw = response.get("usage_metadata")
    if not isinstance(raw, Mapping):
        return None

    if provider == "openai":
        input_tokens = _non_negative_int(raw.get("input_tokens"))
        output_tokens = _non_negative_int(raw.get("output_tokens"))
        total_tokens = _non_negative_int(raw.get("total_tokens"))
        if total_tokens is None and input_tokens is not None and output_tokens is not None:
            total_tokens = input_tokens + output_tokens
        if total_tokens is None:
            return None
        request_id = response.get("id")
        return ModelUsage(
            total_tokens=total_tokens,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            provider=provider,
            model=model,
            request_id=(
                request_id
                if isinstance(request_id, str) and request_id.strip()
                else None
            ),
        )

    if provider == "anthropic":
        base_input = _non_negative_int(raw.get("input_tokens"))
        cache_create = _non_negative_int(raw.get("cache_creation_input_tokens"))
        cache_read = _non_negative_int(raw.get("cache_read_input_tokens"))
        output_tokens = _non_negative_int(raw.get("output_tokens"))
        if base_input is None or output_tokens is None:
            return None
        input_tokens = base_input + (cache_create or 0) + (cache_read or 0)
        request_id = response.get("id")
        return ModelUsage(
            total_tokens=input_tokens + output_tokens,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            provider=provider,
            model=model,
            request_id=(
                request_id
                if isinstance(request_id, str) and request_id.strip()
                else None
            ),
        )

    if provider == "gemini":
        # Interactions API (current): usage.total_* fields.
        total_tokens = _non_negative_int(raw.get("total_tokens"))
        input_tokens = _non_negative_int(raw.get("total_input_tokens"))
        output_tokens = _non_negative_int(raw.get("total_output_tokens"))

        # Keep legacy generateContent usage_metadata readable for archived P16
        # artifacts, but never combine fields across the two schemas.
        if total_tokens is None:
            total_tokens = _non_negative_int(raw.get("total_token_count"))
            input_tokens = _non_negative_int(raw.get("prompt_token_count"))
            output_tokens = _non_negative_int(raw.get("candidates_token_count"))

        if total_tokens is None:
            return None
        request_id = response.get("id")
        return ModelUsage(
            total_tokens=total_tokens,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            provider=provider,
            model=model,
            request_id=(
                request_id
                if isinstance(request_id, str) and request_id.strip()
                else None
            ),
        )

    return None


def urllib_json_transport(
    url: str,
    headers: Mapping[str, str],
    payload: Mapping[str, Any],
    timeout: float,
) -> Mapping[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib_request.Request(
        url,
        data=body,
        headers=dict(headers),
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib_error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ProviderTransportError(
            f"provider HTTP {exc.code}: {detail[:2000]}"
        ) from exc
    except urllib_error.URLError as exc:
        raise ProviderTransportError(
            f"provider transport error: {exc.reason}"
        ) from exc

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProviderTransportError(
            "provider returned non-JSON response"
        ) from exc
    if not isinstance(parsed, Mapping):
        raise ProviderTransportError("provider response must be a JSON object")
    return parsed


class ProviderClient:
    """Secret-safe synchronous JSON client with auditable request provenance."""

    def __init__(
        self,
        config: ProviderConfig,
        *,
        transport: JsonTransport | None = None,
        api_key: str | None = None,
    ) -> None:
        self.config = config
        self._transport = transport or urllib_json_transport
        key = api_key if api_key is not None else os.getenv(config.api_key_env or "")
        if not isinstance(key, str) or not key.strip():
            raise ValueError(
                f"missing provider API key in {config.api_key_env}"
            )
        self._api_key = key.strip()
        self._records: list[ProviderRequestRecord] = []

    def _headers(self) -> dict[str, str]:
        base = {"Content-Type": "application/json"}
        if self.config.provider == "openai":
            base["Authorization"] = f"Bearer {self._api_key}"
        elif self.config.provider == "anthropic":
            base["x-api-key"] = self._api_key
            base["anthropic-version"] = str(self.config.api_version)
        else:
            base["x-goog-api-key"] = self._api_key
        return base

    def request(
        self,
        payload: Mapping[str, Any],
        *,
        purpose: str,
    ) -> Mapping[str, Any]:
        sequence = len(self._records) + 1
        started = _utc_now()
        try:
            response = self._transport(
                str(self.config.endpoint),
                self._headers(),
                payload,
                float(self.config.timeout_seconds),
            )
        except Exception as exc:
            self._records.append(
                ProviderRequestRecord(
                    sequence=sequence,
                    purpose=purpose,
                    requested_at=started,
                    completed_at=_utc_now(),
                    response_id=None,
                    error_type=type(exc).__name__,
                    error_message=str(exc)[:2000],
                )
            )
            raise

        response_id = response.get("id")
        if response_id is not None and not isinstance(response_id, str):
            response_id = str(response_id)
        usage = response.get("usage")
        if not isinstance(usage, Mapping):
            usage = response.get("usage_metadata")
        if not isinstance(usage, Mapping):
            usage = {}
        self._records.append(
            ProviderRequestRecord(
                sequence=sequence,
                purpose=purpose,
                requested_at=started,
                completed_at=_utc_now(),
                response_id=response_id,
                usage=_safe_json_value(dict(usage)),
            )
        )
        return response

    def complete_text(
        self,
        *,
        system_instruction: str,
        input_text: str,
        purpose: str,
    ) -> str:
        """One provider request that must terminate with plain text and no tools."""

        if not isinstance(system_instruction, str) or not system_instruction.strip():
            raise ValueError("system_instruction must be non-blank")
        if not isinstance(input_text, str) or not input_text.strip():
            raise ValueError("input_text must be non-blank")

        config = self.config
        if config.provider == "openai":
            body: dict[str, Any] = {
                "model": config.model,
                "instructions": system_instruction,
                "input": input_text,
                "max_output_tokens": config.max_output_tokens,
                "store": config.store,
            }
            if config.temperature is not None:
                body["temperature"] = config.temperature
            response = self.request(body, purpose=purpose)
            text = _openai_text(response)
        elif config.provider == "anthropic":
            body = {
                "model": config.model,
                "max_tokens": config.max_output_tokens,
                "system": system_instruction,
                "messages": [{"role": "user", "content": input_text}],
            }
            if config.temperature is not None:
                body["temperature"] = config.temperature
            response = self.request(body, purpose=purpose)
            text = _anthropic_text(response)
        else:
            body = {
                "model": config.model,
                "system_instruction": system_instruction,
                "input": input_text,
                "store": config.store,
                "generation_config": {
                    "max_output_tokens": config.max_output_tokens,
                },
            }
            if config.temperature is not None:
                body["generation_config"]["temperature"] = config.temperature
            response = self.request(body, purpose=purpose)
            text = _gemini_text(response)

        clean = text.strip()
        if not clean or clean == SILENCE_TOKEN:
            raise ProviderProtocolError(
                f"{purpose} provider returned no usable terminal text"
            )
        return clean

    def provenance_snapshot(self) -> dict[str, Any]:
        return {
            "artifact_schema": "aios.p16.provider-provenance.v1",
            **self.config.public_config(),
            "config_fingerprint": self.config.config_fingerprint,
            "requests": [
                {
                    "sequence": item.sequence,
                    "purpose": item.purpose,
                    "requested_at": item.requested_at,
                    "completed_at": item.completed_at,
                    "response_id": item.response_id,
                    "usage": dict(item.usage),
                    "error_type": item.error_type,
                    "error_message": item.error_message,
                }
                for item in self._records
            ],
        }


def _resident_system_instruction() -> str:
    return (
        "You are the resident model driving AIOS through the provided capability "
        "catalog. Treat cockpit data as bounded world context, not hidden truth. "
        "Use tools when more world evidence is needed. Never fabricate tool results. "
        "Do not reveal private chain-of-thought. When you have finished, return a "
        "concise user-facing response; if no outward response is appropriate, return "
        f"exactly {SILENCE_TOKEN}."
    )


def _summary_system_instruction() -> str:
    return (
        "Generate only the requested same-session continuity summary. Preserve what "
        "was said and done, do not infer personality, relationships, causality, or "
        "facts absent from the pinned raw messages. Return summary text only."
    )


def _dimension_summary_system_instruction() -> str:
    return (
        "Generate only the requested single-dimension temporal summary from the "
        "provided pinned sources. Describe what happened in that dimension and time "
        "window; preserve uncertainty and source boundaries. Do not infer cross-"
        "dimension causality, personality, relationships, or facts absent from the "
        "sources. Return summary text only."
    )


def _snapshot_prompt(snapshot: RuntimeSnapshot) -> str:
    return _canonical_json(
        {
            "wake_reason": snapshot.wake_reason,
            "user_input": snapshot.user_input,
            "cockpit": snapshot.cockpit,
        }
    )


def _result_payload(result: CapabilityResult) -> dict[str, Any]:
    return {
        "name": result.name,
        "ok": result.ok,
        "data": _safe_json_value(result.data),
        "error_code": result.error_code,
        "error_message": result.error_message,
        "call_id": result.call_id,
    }


def _arguments(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ProviderProtocolError(
                "provider tool arguments are not valid JSON"
            ) from exc
        if not isinstance(parsed, Mapping):
            raise ProviderProtocolError(
                "provider tool arguments must decode to an object"
            )
        return dict(parsed)
    raise ProviderProtocolError("provider tool arguments must be object or JSON string")


def _terminal_directive(
    text: str,
    *,
    usage: ModelUsage | None = None,
    provenance: ModelCallProvenance | None = None,
) -> ModelDirective:
    clean = text.strip()
    if clean == SILENCE_TOKEN:
        return ModelDirective(silence=True, usage=usage, provenance=provenance)
    if not clean:
        raise ProviderProtocolError("provider returned no terminal text or tool call")
    return ModelDirective(response=clean, usage=usage, provenance=provenance)


def _openai_text(response: Mapping[str, Any]) -> str:
    direct = response.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct
    pieces: list[str] = []
    output = response.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, Mapping):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, Mapping):
                    continue
                if block.get("type") in {"output_text", "text"}:
                    text = block.get("text")
                    if isinstance(text, str):
                        pieces.append(text)
    return "".join(pieces)


def _anthropic_text(response: Mapping[str, Any]) -> str:
    pieces: list[str] = []
    content = response.get("content")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, Mapping) and block.get("type") == "text":
                text = block.get("text")
                if isinstance(text, str):
                    pieces.append(text)
    return "".join(pieces)


def _gemini_text(response: Mapping[str, Any]) -> str:
    direct = response.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct
    pieces: list[str] = []
    steps = response.get("steps")
    if isinstance(steps, list):
        for step in steps:
            if not isinstance(step, Mapping):
                continue
            if step.get("type") not in {"model_output", "text"}:
                continue
            content = step.get("content")
            if isinstance(content, str):
                pieces.append(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, Mapping):
                        text = block.get("text")
                        if isinstance(text, str):
                            pieces.append(text)
    return "".join(pieces)


class ProviderResidentHandler:
    """Stateful adapter for one AIOS CognitiveRuntime invocation at a time."""

    def __init__(self, client: ProviderClient) -> None:
        self.client = client
        self.model_id = client.config.model_id
        self._state_id: str | None = None
        self._history_sent = 0
        self._anthropic_messages: list[dict[str, Any]] = []
        self._anthropic_last_content: list[Any] | None = None

    def provenance_snapshot(self) -> dict[str, Any]:
        return self.client.provenance_snapshot()

    def _reset_for_turn(self) -> None:
        self._state_id = None
        self._history_sent = 0
        self._anthropic_messages = []
        self._anthropic_last_content = None

    def __call__(self, snapshot: RuntimeSnapshot) -> ModelDirective:
        if snapshot.round_index == 0:
            self._reset_for_turn()
        elif self._state_id is None and self.client.config.provider != "anthropic":
            raise ProviderProtocolError(
                "provider continuation requested without prior response state"
            )

        provider = self.client.config.provider
        if provider == "openai":
            return self._openai(snapshot)
        if provider == "anthropic":
            return self._anthropic(snapshot)
        return self._gemini(snapshot)

    def _new_results(
        self,
        snapshot: RuntimeSnapshot,
    ) -> tuple[CapabilityResult, ...]:
        history = snapshot.capability_history
        if self._history_sent > len(history):
            raise ProviderProtocolError("capability history moved backwards")
        results = tuple(history[self._history_sent :])
        self._history_sent = len(history)
        return results

    def _openai(self, snapshot: RuntimeSnapshot) -> ModelDirective:
        tools = provider_tools(
            snapshot.capability_catalog,
            provider="openai",
        )
        body: dict[str, Any] = {
            "model": self.client.config.model,
            "instructions": _resident_system_instruction(),
            "tools": tools,
            "tool_choice": "auto",
            "parallel_tool_calls": False,
            "max_output_tokens": self.client.config.max_output_tokens,
            "store": self.client.config.store,
        }
        if self.client.config.temperature is not None:
            body["temperature"] = self.client.config.temperature

        if snapshot.round_index == 0:
            body["input"] = _snapshot_prompt(snapshot)
        else:
            body["previous_response_id"] = self._state_id
            input_items = []
            for result in self._new_results(snapshot):
                if not result.call_id:
                    raise ProviderProtocolError(
                        "OpenAI tool result is missing call_id"
                    )
                input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": result.call_id,
                        "output": _canonical_json(_result_payload(result)),
                    }
                )
            if not input_items:
                raise ProviderProtocolError(
                    "OpenAI continuation has no new capability results"
                )
            body["input"] = input_items

        response = self.client.request(body, purpose="resident")
        usage = _model_usage(
            "openai",
            response,
            model=self.client.config.model,
        )
        response_id = response.get("id")
        if not isinstance(response_id, str) or not response_id.strip():
            raise ProviderProtocolError("OpenAI response missing id")
        provenance = ModelCallProvenance(
            provider="openai",
            model=self.client.config.model,
            request_id=response_id,
        )
        self._state_id = response_id

        calls: list[CapabilityCall] = []
        output = response.get("output")
        if isinstance(output, list):
            for item in output:
                if not isinstance(item, Mapping) or item.get("type") != "function_call":
                    continue
                name = item.get("name")
                call_id = item.get("call_id")
                if not isinstance(name, str) or not name.strip():
                    raise ProviderProtocolError("OpenAI function_call missing name")
                if not isinstance(call_id, str) or not call_id.strip():
                    raise ProviderProtocolError("OpenAI function_call missing call_id")
                calls.append(
                    CapabilityCall(
                        name=name,
                        arguments=_arguments(item.get("arguments", {})),
                        call_id=call_id,
                    )
                )
        if calls:
            return ModelDirective(
                capability_calls=tuple(calls),
                usage=usage,
                provenance=provenance,
            )
        return _terminal_directive(
            _openai_text(response),
            usage=usage,
            provenance=provenance,
        )

    def _anthropic(self, snapshot: RuntimeSnapshot) -> ModelDirective:
        tools = provider_tools(
            snapshot.capability_catalog,
            provider="anthropic",
        )
        if snapshot.round_index == 0:
            self._anthropic_messages = [
                {"role": "user", "content": _snapshot_prompt(snapshot)}
            ]
        else:
            if self._anthropic_last_content is None:
                raise ProviderProtocolError(
                    "Anthropic continuation missing prior assistant content"
                )
            self._anthropic_messages.append(
                {
                    "role": "assistant",
                    "content": _safe_json_value(self._anthropic_last_content),
                }
            )
            result_blocks = []
            for result in self._new_results(snapshot):
                if not result.call_id:
                    raise ProviderProtocolError(
                        "Anthropic tool result is missing call_id"
                    )
                result_blocks.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": result.call_id,
                        "content": _canonical_json(_result_payload(result)),
                        "is_error": not result.ok,
                    }
                )
            if not result_blocks:
                raise ProviderProtocolError(
                    "Anthropic continuation has no new capability results"
                )
            self._anthropic_messages.append(
                {"role": "user", "content": result_blocks}
            )

        body: dict[str, Any] = {
            "model": self.client.config.model,
            "max_tokens": self.client.config.max_output_tokens,
            "system": _resident_system_instruction(),
            "messages": self._anthropic_messages,
            "tools": tools,
        }
        if self.client.config.temperature is not None:
            body["temperature"] = self.client.config.temperature

        response = self.client.request(body, purpose="resident")
        usage = _model_usage(
            "anthropic",
            response,
            model=self.client.config.model,
        )
        response_id = response.get("id")
        if not isinstance(response_id, str) or not response_id.strip():
            raise ProviderProtocolError("Anthropic response missing id")
        provenance = ModelCallProvenance(
            provider="anthropic",
            model=self.client.config.model,
            request_id=response_id,
        )
        self._state_id = response_id
        content = response.get("content")
        if not isinstance(content, list):
            raise ProviderProtocolError("Anthropic response content must be a list")
        self._anthropic_last_content = _safe_json_value(content)

        calls: list[CapabilityCall] = []
        for block in content:
            if not isinstance(block, Mapping) or block.get("type") != "tool_use":
                continue
            name = block.get("name")
            call_id = block.get("id")
            if not isinstance(name, str) or not name.strip():
                raise ProviderProtocolError("Anthropic tool_use missing name")
            if not isinstance(call_id, str) or not call_id.strip():
                raise ProviderProtocolError("Anthropic tool_use missing id")
            calls.append(
                CapabilityCall(
                    name=name,
                    arguments=_arguments(block.get("input", {})),
                    call_id=call_id,
                )
            )
        if calls:
            return ModelDirective(
                capability_calls=tuple(calls),
                usage=usage,
                provenance=provenance,
            )
        return _terminal_directive(
            _anthropic_text(response),
            usage=usage,
            provenance=provenance,
        )

    def _gemini(self, snapshot: RuntimeSnapshot) -> ModelDirective:
        tools = provider_tools(
            snapshot.capability_catalog,
            provider="gemini",
        )
        body: dict[str, Any] = {
            "model": self.client.config.model,
            "system_instruction": _resident_system_instruction(),
            "tools": tools,
            "store": self.client.config.store,
        }
        generation_config: dict[str, Any] = {
            "max_output_tokens": self.client.config.max_output_tokens,
        }
        if self.client.config.temperature is not None:
            generation_config["temperature"] = self.client.config.temperature
        body["generation_config"] = generation_config

        if snapshot.round_index == 0:
            body["input"] = _snapshot_prompt(snapshot)
        else:
            body["previous_interaction_id"] = self._state_id
            result_steps = []
            for result in self._new_results(snapshot):
                if not result.call_id:
                    raise ProviderProtocolError(
                        "Gemini function result is missing call_id"
                    )
                result_steps.append(
                    {
                        "type": "function_result",
                        "name": result.name,
                        "call_id": result.call_id,
                        "result": [
                            {
                                "type": "text",
                                "text": _canonical_json(_result_payload(result)),
                            }
                        ],
                    }
                )
            if not result_steps:
                raise ProviderProtocolError(
                    "Gemini continuation has no new capability results"
                )
            body["input"] = result_steps

        response = self.client.request(body, purpose="resident")
        usage = _model_usage(
            "gemini",
            response,
            model=self.client.config.model,
        )
        response_id = response.get("id")
        if not isinstance(response_id, str) or not response_id.strip():
            raise ProviderProtocolError("Gemini interaction response missing id")
        provenance = ModelCallProvenance(
            provider="gemini",
            model=self.client.config.model,
            request_id=response_id,
        )
        self._state_id = response_id

        calls: list[CapabilityCall] = []
        steps = response.get("steps")
        if isinstance(steps, list):
            for step in steps:
                if not isinstance(step, Mapping) or step.get("type") != "function_call":
                    continue
                name = step.get("name")
                call_id = step.get("id")
                if not isinstance(name, str) or not name.strip():
                    raise ProviderProtocolError("Gemini function_call missing name")
                if not isinstance(call_id, str) or not call_id.strip():
                    raise ProviderProtocolError("Gemini function_call missing id")
                calls.append(
                    CapabilityCall(
                        name=name,
                        arguments=_arguments(step.get("arguments", {})),
                        call_id=call_id,
                    )
                )
        if calls:
            return ModelDirective(
                capability_calls=tuple(calls),
                usage=usage,
                provenance=provenance,
            )
        return _terminal_directive(
            _gemini_text(response),
            usage=usage,
            provenance=provenance,
        )


class ProviderRoundSummaryHandler:
    """Provider-backed text-only continuity summarizer sharing request provenance."""

    def __init__(self, client: ProviderClient) -> None:
        self.client = client
        self.model_id = client.config.model_id

    def provenance_snapshot(self) -> dict[str, Any]:
        return self.client.provenance_snapshot()

    def __call__(self, request: Any) -> str:
        model_input = (
            request.as_model_input()
            if hasattr(request, "as_model_input")
            else _safe_json_value(request)
        )
        prompt = _canonical_json(model_input)
        purpose = (
            "dimension_summary"
            if hasattr(request, "granularity") and hasattr(request, "sources")
            else "round_summary"
        )
        return self.client.complete_text(
            system_instruction=(
                _dimension_summary_system_instruction()
                if purpose == "dimension_summary"
                else _summary_system_instruction()
            ),
            input_text=prompt,
            purpose=purpose,
        )


def make_provider_handlers(
    config: ProviderConfig,
    *,
    transport: JsonTransport | None = None,
    api_key: str | None = None,
) -> tuple[ProviderResidentHandler, ProviderRoundSummaryHandler]:
    client = ProviderClient(
        config,
        transport=transport,
        api_key=api_key,
    )
    return ProviderResidentHandler(client), ProviderRoundSummaryHandler(client)
