"""Only synthetic subprocess coordination for frozen C10; no Resident input."""
from __future__ import annotations

import json
import pathlib
import sys
import time

from aios_exchange.bridge import ExchangeBridge


def main(root: pathlib.Path, rendezvous: pathlib.Path, token: str) -> None:
    bridge = ExchangeBridge(root)
    original = bridge.requests.next_sequence

    def rendezvous_after_prefix_read() -> int:
        sequence = original()
        (rendezvous / f"ready-{token}").write_text(str(sequence))
        deadline = time.monotonic() + 1.5
        while len(list(rendezvous.glob("ready-*"))) < 2 and time.monotonic() < deadline:
            time.sleep(0.005)
        return sequence

    # This only controls a legal scheduling interleaving; it does not edit the
    # candidate implementation or the durable exchange files.
    bridge.requests.next_sequence = rendezvous_after_prefix_read
    try:
        receipt = bridge.publish_request(kind="model_directive", body={"synthetic_process": token})
        print(json.dumps({"status": "success", "receipt": receipt}), flush=True)
    except Exception as exc:
        print(json.dumps({"status": "closed", "error": f"{type(exc).__name__}: {exc}"}), flush=True)


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3])
