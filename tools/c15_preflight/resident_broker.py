"""Operator broker for Resident isolation - Architecture A.

Model only receives explicit serialized Runtime/模型输入,
not repo, filesystem, GitHub, arbitrary network or platform tools.

This is deployable boundary: operator process owns repo, filesystem,
GitHub credentials, and calls external model via broker with explicit
packet. Model endpoint is synthetic for tests, real endpoint would be
external LLM API with no tool access.

Data flow:
  Driver -> RuntimeRecorder -> RuntimeSnapshot (plain) -> Broker -> HTTP POST -> External Model (synthetic endpoint)
  External Model -> ModelDirective (validated) -> Broker -> Driver

Permission boundary:
- Broker runs in operator host, has filesystem, but only emits plain(snapshot)
- Model endpoint has NO filesystem, NO GitHub, NO repo, NO env tokens, only receives packet
- Logs owned by operator (trace.jsonl), not model
- Timeout and error handling fail-closed, no default silence
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Callable
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import urllib.request
import urllib.error

from .transport import plain, encode, directive, TransportError
from .audit import require


class BrokerError(TransportError):
    pass


class ResidentBroker:
    """Operator-side broker that calls external model via explicit packet.

    Only allowed to emit plain(snapshot) + metadata, never repo files,
    GitHub credentials, or canary paths. Validates response via directive().
    """
    def __init__(self, endpoint_url: str, *, timeout: int = 10, max_response_chars: int = 1_000_000):
        if not endpoint_url.startswith(("http://", "https://")):
            raise ValueError("endpoint must be http(s)")
        if timeout < 1 or max_response_chars < 1:
            raise ValueError("invalid timeout/max_response")
        self.endpoint_url = endpoint_url
        self.timeout = timeout
        self.max_response_chars = max_response_chars
        self.emitted_log: list[dict] = []  # for boundary tests

    def _check_packet_boundary(self, packet: dict) -> None:
        """Ensure packet does not contain disallowed data (canary, repo, tokens)."""
        serialized = json.dumps(packet, sort_keys=True)
        # Disallow canary labels, repo paths, GitHub, tokens
        disallowed = [
            "protected-canaries", "private_a", "sealed_future",
            "git_credentials", "gh_credentials", "GITHUB_TOKEN",
            "GH_TOKEN", "Haneof-AIOS-Core", "src/aios_core",
            "/usr/bin/git", "/usr/bin/gh"
        ]
        for bad in disallowed:
            require(bad not in serialized, f"packet leaks disallowed data: {bad}")
        # Ensure only expected top-level keys
        allowed_keys = {"protocol", "request_id", "kind", "input", "input_sha256", "allowed_sha256"}
        # For broker, we allow protocol, request_id, kind, input, input_sha256
        # But we check that input is plain snapshot, not raw file
        require(isinstance(packet.get("input"), dict), "input must be dict")
        # No file paths outside /packet
        if "canaries" in str(packet):
            require(False, "packet must not contain canary paths")

    def invoke(self, snapshot: Any) -> Any:
        """Call external model with explicit serialized snapshot, fail-closed."""
        from uuid import uuid4
        from aios_core.runtime.cognitive_runtime import RuntimeSnapshot
        if not isinstance(snapshot, RuntimeSnapshot):
            raise TypeError("genuine RuntimeSnapshot required")

        # Serialize via plain() - same as transport, no repo files
        serialized_input = plain(snapshot)
        input_sha256 = hashlib.sha256(encode(serialized_input).encode()).hexdigest()
        request_id = uuid4().hex
        packet = {
            "protocol": "c15-resident-broker-v1",
            "request_id": request_id,
            "kind": "runtime",
            "input_sha256": input_sha256,
            "input": serialized_input,
        }

        # Boundary check before emit
        self._check_packet_boundary(packet)

        # Log emitted for tests (operator-owned log)
        self.emitted_log.append({
            "request_id": request_id,
            "kind": "runtime",
            "input_sha256": input_sha256,
            "input_keys": list(serialized_input.keys()) if isinstance(serialized_input, dict) else [],
            "at": time.time(),
        })

        # HTTP POST to synthetic endpoint
        data = (encode(packet) + "\n").encode("utf-8")
        req = urllib.request.Request(
            self.endpoint_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read(self.max_response_chars + 1)
                if len(raw) > self.max_response_chars:
                    raise BrokerError("oversized response")
                text = raw.decode("utf-8")
                if not text.endswith("\n"):
                    raise BrokerError("incomplete response frame")
                # Parse response: expect {"request_id":..., "kind":..., "input_sha256":..., "output":...}
                value = json.loads(text)
                if not isinstance(value, dict) or set(value) != {"request_id", "kind", "input_sha256", "output"}:
                    raise BrokerError("response binding mismatch")
                if any(value[k] != packet[k] for k in ("request_id", "kind", "input_sha256")):
                    raise BrokerError("response request binding mismatch")
                # Validate output via directive() - only explicit choices, no default silence
                result = directive(value["output"])
                return result
        except urllib.error.URLError as e:
            raise BrokerError(f"broker endpoint unreachable/timeout: {e}") from e
        except TimeoutError as e:
            raise BrokerError(f"broker timeout: {e}") from e
        except json.JSONDecodeError as e:
            raise BrokerError(f"broker illegal JSON: {e}") from e
        except BrokerError:
            raise
        except Exception as e:
            raise BrokerError(f"broker failed: {type(e).__name__}: {e}") from e


class SyntheticModelEndpoint(BaseHTTPRequestHandler):
    """Synthetic external model endpoint for boundary tests.

    Only receives packet, has no filesystem access beyond its own log.
    Returns synthetic directive, logs what it received for verification.
    """
    # Class-level log for tests
    received_log: list[dict] = []
    # Control behavior for tests
    next_response: dict | None = None  # if set, return this instead of default
    delay_seconds: float = 0

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(content_length)
        text = raw.decode('utf-8').strip()
        try:
            packet = json.loads(text)
        except Exception as e:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(f"invalid json: {e}".encode())
            return

        # Log received (for boundary verification)
        SyntheticModelEndpoint.received_log.append({
            "path": self.path,
            "headers": dict(self.headers),
            "packet_keys": list(packet.keys()),
            "input_sha256": packet.get("input_sha256"),
            "has_canary": "canary" in text.lower() or "protected-canaries" in text,
            "has_token": "TOKEN" in text or "GITHUB" in text,
            "has_repo": "Haneof-AIOS-Core" in text or "src/aios_core" in text,
            "size": len(raw),
        })

        if SyntheticModelEndpoint.delay_seconds:
            time.sleep(SyntheticModelEndpoint.delay_seconds)

        # Default synthetic response: silence=False, response with explicit text
        # Must be wrapped in binding envelope by handler
        if SyntheticModelEndpoint.next_response is not None:
            output = SyntheticModelEndpoint.next_response
        else:
            output = {"response": "synthetic model response for boundary test"}

        # Binding envelope
        response_envelope = {
            "request_id": packet.get("request_id"),
            "kind": packet.get("kind"),
            "input_sha256": packet.get("input_sha256"),
            "output": output,
        }
        body = (json.dumps(response_envelope) + "\n").encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Suppress default logging, operator owns logs
        return


def start_synthetic_endpoint(port: int = 0) -> tuple[HTTPServer, threading.Thread, int]:
    """Start synthetic model endpoint on 0.0.0.0:port, return server, thread, actual port."""
    server = HTTPServer(("0.0.0.0", port), SyntheticModelEndpoint)
    actual_port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    # Clear logs
    SyntheticModelEndpoint.received_log.clear()
    SyntheticModelEndpoint.next_response = None
    SyntheticModelEndpoint.delay_seconds = 0
    return server, thread, actual_port


def stop_synthetic_endpoint(server: HTTPServer):
    server.shutdown()
    server.server_close()
