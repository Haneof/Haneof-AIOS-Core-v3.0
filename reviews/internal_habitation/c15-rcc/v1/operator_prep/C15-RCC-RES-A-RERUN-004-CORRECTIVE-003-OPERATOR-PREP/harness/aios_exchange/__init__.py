"""Mechanical exchange harness for the AIOS Resident launch boundary.

This package is **transport, durability and verification only**.

It publishes a durable decision request, blocks until the *external* current
Resident session publishes the exact response bytes, verifies digests, records
an append-only hash-chained ledger, and returns the parsed directive to the
frozen Core runtime.

It contains no cognition:

* no keyword -> capability routing;
* no event/cursor -> response mapping;
* no prewritten reply, claim, policy or goal;
* no callback, provider adapter, fallback answer or expected-answer logic.

The only way a directive is produced is by parsing bytes that some other human
or model session decided and published through the mechanical publisher.
"""

from __future__ import annotations

__all__ = [
    "REAL_RESPONSE_MODE",
    "PACKAGE_NAME",
    "PACKAGE_VERSION",
]

PACKAGE_NAME = "aios_exchange"
PACKAGE_VERSION = "1.0.0"

#: The only supported real-run response mode. The response is authored by the
#: current external Resident session; this package never authors it.
REAL_RESPONSE_MODE = "EXTERNAL_CURRENT_RESIDENT_SESSION"
