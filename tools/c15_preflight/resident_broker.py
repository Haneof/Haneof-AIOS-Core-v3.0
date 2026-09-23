"""Operator broker for Resident isolation - Architecture A.

Model only receives explicit serialized Runtime/模型输入,
not repo, filesystem, GitHub, arbitrary network or platform tools.

Deployable boundary: operator process owns repo, filesystem,
GitHub credentials, and calls external model via broker with explicit
packet. Model endpoint is synthetic for tests, real endpoint would be
external LLM API with no tool access.

Data flow:
  Driver -> RuntimeRecorder -> RuntimeSnapshot (plain) -> Broker -> HTTP POST -> External Model (synthetic endpoint)
  External Model -> ModelDirective (validated) -> Broker -> Driver

Permission boundary:
- Broker runs in operator host, has filesystem, but only emits plain(snapshot) from approved structure
- Model endpoint is transport test double; no sensitive info sent is verified, process read permission separately
- Logs owned by operator (trace.jsonl), not model
- Timeout and error handling fail-closed, no default silence
- Credentials stay in HTTP auth layer, not in model message or ordinary log
- Core provided legal AIOS capability calls retained via Runtime execution, not filtered
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any
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

    Based on approved input structure and source, not string blacklist.
    Operator private checkpoint, credentials, governance material must not enter model input.
    Core provided legal AIOS capability calls retained via Runtime execution.
    """
    def __init__(self, endpoint_url: str, *, timeout: int = 10, max_response_chars: int = 1_000_000, auth_token: str | None = None):
        if not endpoint_url.startswith(("http://", "https://")):
            raise ValueError("endpoint must be http(s)")
        if timeout < 1 or max_response_chars < 1:
            raise ValueError("invalid timeout/max_response")
        self.endpoint_url = endpoint_url
        self.timeout = timeout
        self.max_response_chars = max_response_chars
        self.auth_token = auth_token  # credentials stay in HTTP auth layer, not in model message
        self.emitted_log: list[dict] = []

    def _check_packet_boundary(self, packet: dict, snapshot: Any) -> None:
        """Ensure packet is from approved structure and source, no operator private material.

        Based on approved input structure: RuntimeSnapshot fields only,
        not filtering arbitrary strings, not rewriting semantic content.
        Operator private checkpoint, credentials, governance must not enter.
        """
        # Approved structure: packet must have protocol, request_id, kind, input_sha256, input
        require(set(packet.keys()) == {"protocol", "request_id", "kind", "input_sha256", "input"},
                f"packet has unapproved keys: {packet.keys()}")
        require(packet.get("protocol") == "c15-resident-broker-v1", "unapproved protocol")
        require(packet.get("kind") == "runtime", "unapproved kind")
        # Input must be plain(snapshot) from RuntimeSnapshot, not operator checkpoint
        # RuntimeSnapshot approved fields: user_input, wake_reason, cockpit, capability_catalog, capability_history, round_index, remaining_tool_rounds
        approved_snapshot_keys = {"user_input", "wake_reason", "cockpit", "capability_catalog", "capability_history", "round_index", "remaining_tool_rounds"}
        input_data = packet.get("input")
        require(isinstance(input_data, dict), "input must be dict")
        # Ensure input only contains approved snapshot keys (or subset), not operator private checkpoint fields
        # Operator private checkpoint fields that must NOT enter: world_revision, index_watermark, release_sha256, session, clock, driver_state, etc.
        forbidden_keys = {"world_revision", "index_watermark", "release_sha256", "driver_state", "session", "clock", "private_world", "world_index", "release_state", "operator", "git_metadata", "private_a"}
        for fk in forbidden_keys:
            require(fk not in input_data, f"operator private material must not enter model input: {fk}")
        # Ensure no governance material
        require("governance" not in json.dumps(input_data).lower(), "governance material must not enter")
        # Ensure input is from genuine RuntimeSnapshot source, not arbitrary
        # We already check isinstance in invoke(), here we check structure
        for k in input_data.keys():
            require(k in approved_snapshot_keys, f"unapproved snapshot field: {k} - must be from approved RuntimeSnapshot structure")

    def invoke(self, snapshot: Any) -> Any:
        """Call external model with explicit serialized snapshot, fail-closed."""
        from uuid import uuid4
        from aios_core.runtime.cognitive_runtime import RuntimeSnapshot
        if not isinstance(snapshot, RuntimeSnapshot):
            raise TypeError("genuine RuntimeSnapshot required")

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

        # Boundary check based on approved structure, not string blacklist
        self._check_packet_boundary(packet, snapshot)

        self.emitted_log.append({
            "request_id": request_id,
            "kind": "runtime",
            "input_sha256": input_sha256,
            "input_keys": list(serialized_input.keys()) if isinstance(serialized_input, dict) else [],
            "at": time.time(),
            "protocol": "c15-resident-broker-v1",
        })

        data = (encode(packet) + "\n").encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            # Credentials stay in HTTP auth layer, not in model message or ordinary log
            headers["Authorization"] = f"Bearer {self.auth_token}"

        req = urllib.request.Request(
            self.endpoint_url,
            data=data,
            headers=headers,
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
                # Request/reply binding validation
                value = json.loads(text)
                if not isinstance(value, dict) or set(value) != {"request_id", "kind", "input_sha256", "output"}:
                    raise BrokerError(f"response binding mismatch: keys {value.keys() if isinstance(value, dict) else type(value)}")
                if any(value[k] != packet[k] for k in ("request_id", "kind", "input_sha256")):
                    raise BrokerError(f"response request binding mismatch: expected {packet['request_id']}/{packet['kind']}/{packet['input_sha256'][:8]} got {value.get('request_id')}/{value.get('kind')}/{str(value.get('input_sha256'))[:8]}")
                # Validate output via directive() - only explicit choices, no default silence, error propagation
                try:
                    result = directive(value["output"])
                except Exception as e:
                    raise BrokerError(f"directive validation failed, error propagation: {e}") from e
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
    """Synthetic external model endpoint for boundary tests - transport test double.

    Only receives packet, logs what it received for verification.
    Does NOT claim 'no filesystem' unless OS permission verified.
    No sensitive info sent and process has no read permission are separately accounted.
    """
    received_log: list[dict] = []
    next_response: dict | None = None
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

        # Log received for boundary verification - separate accounting for no sensitive info vs no read permission
        has_auth = "Authorization" in self.headers
        # Check if packet contains only approved structure
        input_data = packet.get("input", {})
        has_forbidden = any(k in input_data for k in ["world_revision", "private_world", "operator", "git_metadata"])

        SyntheticModelEndpoint.received_log.append({
            "path": self.path,
            "has_auth_header": has_auth,  # credentials in HTTP auth layer, not in message
            "packet_keys": list(packet.keys()),
            "input_keys": list(input_data.keys()) if isinstance(input_data, dict) else [],
            "input_sha256": packet.get("input_sha256"),
            "has_forbidden_private": has_forbidden,
            "has_canary": "protected-canaries" in text,
            "has_token": "TOKEN" in text and "Authorization" not in text,  # backward compat
            "has_repo": "Haneof-AIOS-Core" in text,  # backward compat
            "has_token_in_body": "TOKEN" in text and "Authorization" not in text,
            "has_repo_in_body": "Haneof-AIOS-Core" in text,
            "size": len(raw),
            "protocol": packet.get("protocol"),
        })

        if SyntheticModelEndpoint.delay_seconds:
            time.sleep(SyntheticModelEndpoint.delay_seconds)

        if SyntheticModelEndpoint.next_response is not None:
            output = SyntheticModelEndpoint.next_response
        else:
            output = {"response": "synthetic model response for boundary test"}

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
        return


def start_synthetic_endpoint(port: int = 0) -> tuple[HTTPServer, threading.Thread, int]:
    server = HTTPServer(("0.0.0.0", port), SyntheticModelEndpoint)
    actual_port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    SyntheticModelEndpoint.received_log.clear()
    SyntheticModelEndpoint.next_response = None
    SyntheticModelEndpoint.delay_seconds = 0
    return server, thread, actual_port


def stop_synthetic_endpoint(server: HTTPServer):
    server.shutdown()
    server.server_close()
