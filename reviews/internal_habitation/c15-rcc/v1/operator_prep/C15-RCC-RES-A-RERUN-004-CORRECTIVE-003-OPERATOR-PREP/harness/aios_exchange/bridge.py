"""Exchange bridge: durable chronology, consumption and crash recovery.

The bridge is the single authority for exchange state. It enforces:

* ``request_published`` is the **semantic dispatch boundary**;
* a response may be consumed only when a durable ``response_published`` ledger
  record exists for that request;
* consumption is recorded once, after digest and request-id verification;
* ``not_submitted`` reconciliation is permitted **only** when no
  ``request_published`` record exists for the exchange.
"""

from __future__ import annotations

import json
import pathlib
import time
from typing import Any, Mapping

from .atomic import read_bytes
from .canonical import sha256_hex
from .ledger import (
    LEDGER_EVENT_REQUEST_PUBLISHED,
    LEDGER_EVENT_RESPONSE_CONSUMED,
    LEDGER_EVENT_RESPONSE_PUBLISHED,
    ExchangeLedger,
    LedgerError,
)
from .requests import RequestPublisher, RequestPublishError
from .responses import ResponsePublisher, ResponsePublishError
from . import verify as _verify_module
from .schema import (
    ModelDirective,
    SchemaContractError,
    parse_response_envelope,
    parse_model_directive,
)

__all__ = [
    "DISPATCH_BOUNDARY_EVENT",
    "DISPATCH_BOUNDARY_RULE",
    "CLASSIFICATION_NOT_SUBMITTED",
    "CLASSIFICATION_DISPATCHED_AWAITING_RESPONSE",
    "CLASSIFICATION_RESPONSE_DURABLE_UNCONSUMED",
    "CLASSIFICATION_COMPLETE",
    "ExchangeError",
    "ExchangeContractError",
    "ResponseTimeoutError",
    "ExchangeBridge",
]

#: A durable ``request_published`` record means the semantic request crossed the
#: dispatch boundary. Null provider/model fields can never undo this.
DISPATCH_BOUNDARY_EVENT = LEDGER_EVENT_REQUEST_PUBLISHED

DISPATCH_BOUNDARY_RULE = (
    "not_submitted reconciliation is allowed only when no request_published "
    "record exists; after request publication the exchange fails closed "
    "instead of declaring the request unsubmitted"
)

CLASSIFICATION_NOT_SUBMITTED = "NOT_SUBMITTED_BEFORE_DISPATCH_BOUNDARY"
CLASSIFICATION_DISPATCHED_AWAITING_RESPONSE = "DISPATCHED_AWAITING_RESPONSE"
CLASSIFICATION_RESPONSE_DURABLE_UNCONSUMED = "RESPONSE_DURABLE_UNCONSUMED"
CLASSIFICATION_COMPLETE = "COMPLETE"


class ExchangeError(RuntimeError):
    """Base class for exchange failures."""


class ExchangeContractError(ExchangeError):
    """The exchange violates the durable chronology contract (fail closed)."""


class ResponseTimeoutError(ExchangeError):
    """No durably published response appeared within the caller's budget."""


class ExchangeBridge:
    def __init__(self, exchange_root: str | pathlib.Path) -> None:
        self.root = pathlib.Path(exchange_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.ledger = ExchangeLedger(self.root / "ledger.jsonl")
        self.requests = RequestPublisher(self.root, self.ledger)
        self.responses = ResponsePublisher(self.root, self.ledger)

    # -- request side ----------------------------------------------------
    def publish_request(
        self,
        *,
        kind: str,
        body: Mapping[str, Any],
        request_id: str | None = None,
    ) -> dict[str, Any]:
        return self.requests.publish(kind=kind, body=body, request_id=request_id)

    def request_payload(self, request_id: str) -> dict[str, Any]:
        return self.requests.payload(request_id)

    def request_body(self, request_id: str) -> dict[str, Any]:
        return self.requests.body(request_id)

    def request_sha256(self, request_id: str) -> str:
        record = self.ledger.latest_event(request_id, LEDGER_EVENT_REQUEST_PUBLISHED)
        if record is None:
            raise ExchangeContractError(
                f"request {request_id!r} has no durable publication record"
            )
        return str(record["request_sha256"])

    # -- response side ---------------------------------------------------
    def published_response_record(self, request_id: str) -> dict[str, Any] | None:
        return self.ledger.latest_event(request_id, LEDGER_EVENT_RESPONSE_PUBLISHED)

    def wait_for_publication(
        self,
        request_id: str,
        *,
        timeout_s: float,
        poll_interval_s: float = 0.05,
    ) -> dict[str, Any]:
        """Block until the response is durably published (ledger record exists)."""

        if timeout_s is not None and timeout_s < 0:
            raise ExchangeError("timeout_s must be non-negative")
        deadline = time.monotonic() + float(timeout_s)
        while True:
            record = self.published_response_record(request_id)
            if record is not None:
                return record
            if time.monotonic() >= deadline:
                state = self.recovery_state(request_id)
                raise ResponseTimeoutError(
                    f"no durable response_published record for {request_id!r} within "
                    f"{timeout_s}s (classification={state['classification']})"
                )
            time.sleep(max(0.001, float(poll_interval_s)))

    def await_response_bytes(
        self,
        request_id: str,
        *,
        timeout_s: float,
        poll_interval_s: float = 0.05,
    ) -> bytes:
        self.wait_for_publication(
            request_id, timeout_s=timeout_s, poll_interval_s=poll_interval_s
        )
        return self.responses.published_bytes(request_id)

    def consume_response(self, request_id: str, *, allow_replay: bool = True) -> bytes:
        """Verify and record consumption of a durably published response."""

        with self.ledger.mutation():
            return self._consume_locked(request_id, allow_replay=allow_replay)

    def _consume_locked(self, request_id: str, *, allow_replay: bool) -> bytes:
        request_record = self.ledger.latest_event(request_id, LEDGER_EVENT_REQUEST_PUBLISHED)
        if request_record is None:
            raise ExchangeContractError(
                f"cannot consume {request_id!r}: no durable request_published record"
            )
        response_record = self.ledger.latest_event(request_id, LEDGER_EVENT_RESPONSE_PUBLISHED)
        if response_record is None:
            raise ExchangeContractError(
                f"cannot consume {request_id!r}: no durable response_published record"
            )
        previous_consumed = self.ledger.latest_event(request_id, LEDGER_EVENT_RESPONSE_CONSUMED)
        if previous_consumed is not None:
            if not allow_replay:
                raise ExchangeContractError(f"response for {request_id!r} was already consumed")
            if previous_consumed.get("response_sha256") != response_record.get("response_sha256"):
                raise ExchangeContractError(
                    f"consumed digest for {request_id!r} disagrees with the published digest"
                )
            return self.responses.published_bytes(request_id)

        try:
            data = self.responses.published_bytes(request_id)
        except (LedgerError, RequestPublishError, ResponsePublishError) as exc:
            raise ExchangeContractError(
                f"cannot consume {request_id!r}: durable response is not trustworthy: {exc}"
            ) from exc
        try:
            decoded = json.loads(data.decode("utf-8"))
            envelope = parse_response_envelope(decoded)
        except (UnicodeDecodeError, json.JSONDecodeError, SchemaContractError) as exc:
            raise ExchangeContractError(
                f"published response for {request_id!r} is not a valid envelope: {exc}"
            ) from exc
        if envelope["request_id"] != request_id:
            raise ExchangeContractError(
                f"published response request_id {envelope['request_id']!r} does not match "
                f"{request_id!r}"
            )
        if envelope["request_sha256"] != request_record.get("request_sha256"):
            raise ExchangeContractError(
                f"published response request digest does not match the durable request for {request_id!r}"
            )

        self.ledger._append_locked(
            LEDGER_EVENT_RESPONSE_CONSUMED,
            request_id=request_id,
            request_sha256=request_record.get("request_sha256"),
            response_sha256=response_record.get("response_sha256"),
        )
        return data

    def directive_for(self, request_id: str) -> ModelDirective:
        """Parse the durably published response into a real ModelDirective."""

        try:
            data = self.responses.published_bytes(request_id)
        except (LedgerError, RequestPublishError, ResponsePublishError) as exc:
            raise ExchangeContractError(
                f"cannot consume {request_id!r}: durable response is not trustworthy: {exc}"
            ) from exc
        try:
            decoded = json.loads(data.decode("utf-8"))
        except Exception as exc:
            raise ExchangeContractError(f"response is not valid JSON: {exc}") from exc
        try:
            return parse_model_directive(decoded)
        except SchemaContractError as exc:
            raise ExchangeContractError(f"response violates the directive contract: {exc}") from exc

    # -- recovery --------------------------------------------------------
    def _classify(self, request_id: str) -> dict[str, Any]:
        records = self.ledger.records_for(request_id)
        events = [record.get("event") for record in records]
        request_record = self.ledger.latest_event(request_id, LEDGER_EVENT_REQUEST_PUBLISHED)
        response_record = self.ledger.latest_event(request_id, LEDGER_EVENT_RESPONSE_PUBLISHED)
        consumed_record = self.ledger.latest_event(request_id, LEDGER_EVENT_RESPONSE_CONSUMED)
        if request_record is None:
            classification = CLASSIFICATION_NOT_SUBMITTED
            not_submitted_allowed = True
            dispatched = False
        elif response_record is None:
            classification = CLASSIFICATION_DISPATCHED_AWAITING_RESPONSE
            not_submitted_allowed = False
            dispatched = True
        elif consumed_record is None:
            classification = CLASSIFICATION_RESPONSE_DURABLE_UNCONSUMED
            not_submitted_allowed = False
            dispatched = True
        else:
            classification = CLASSIFICATION_COMPLETE
            not_submitted_allowed = False
            dispatched = True
        return {
            "request_id": request_id,
            "classification": classification,
            "not_submitted_allowed": not_submitted_allowed,
            "semantic_dispatch_occurred": dispatched,
            "request_sha256": (request_record or {}).get("request_sha256"),
            "response_sha256": (response_record or {}).get("response_sha256"),
            "events": [
                {"seq": record.get("seq"), "event": record.get("event")} for record in records
            ],
            "event_names": events,
        }

    @staticmethod
    def _aggregate_classification(classified: list[dict[str, Any]]) -> str:
        orders = [item["classification"] for item in classified]
        if not orders or all(item == CLASSIFICATION_NOT_SUBMITTED for item in orders):
            return CLASSIFICATION_NOT_SUBMITTED
        if all(item == CLASSIFICATION_COMPLETE for item in orders):
            return CLASSIFICATION_COMPLETE
        if CLASSIFICATION_RESPONSE_DURABLE_UNCONSUMED in orders:
            return CLASSIFICATION_RESPONSE_DURABLE_UNCONSUMED
        return CLASSIFICATION_DISPATCHED_AWAITING_RESPONSE

    def recovery_state(self, request_id: str | None = None) -> dict[str, Any]:
        # The multi-read classification must describe one validated prefix,
        # not a mixture of states across another writer's publication.
        with self.ledger.mutation():
            return self._recovery_state_locked(request_id)

    def _recovery_state_locked(self, request_id: str | None) -> dict[str, Any]:
        ids = [request_id] if request_id is not None else self.ledger.request_ids()
        classified = [self._classify(item) for item in ids]
        chain = self.ledger.verify_chain()
        aggregate = self._aggregate_classification(classified)
        return {
            "classification": aggregate,
            "semantic_dispatch_occurred": aggregate != CLASSIFICATION_NOT_SUBMITTED,
            "requests": classified,
            "dispatch_boundary_event": DISPATCH_BOUNDARY_EVENT,
            "dispatch_boundary_rule": DISPATCH_BOUNDARY_RULE,
            "not_submitted_allowed": all(
                item["not_submitted_allowed"] for item in classified
            )
            if classified
            else True,
            "open_dispatched": [
                item["request_id"]
                for item in classified
                if item["classification"] == CLASSIFICATION_DISPATCHED_AWAITING_RESPONSE
            ],
            "durable_unconsumed": [
                item["request_id"]
                for item in classified
                if item["classification"] == CLASSIFICATION_RESPONSE_DURABLE_UNCONSUMED
            ],
            "complete": [
                item["request_id"]
                for item in classified
                if item["classification"] == CLASSIFICATION_COMPLETE
            ],
            "ledger": chain,
        }

    # -- integrity -------------------------------------------------------
    def integrity(self) -> dict[str, Any]:
        return _verify_module.verify_exchange_integrity(self.root)

    def read_response_file_bytes(self, request_id: str) -> bytes | None:
        path = self.responses.path_for(request_id)
        if not path.exists():
            return None
        return read_bytes(path)

    def response_file_digest(self, request_id: str) -> str | None:
        data = self.read_response_file_bytes(request_id)
        return None if data is None else sha256_hex(data)


# Re-exported for callers that only import the bridge module.
LedgerError = LedgerError
