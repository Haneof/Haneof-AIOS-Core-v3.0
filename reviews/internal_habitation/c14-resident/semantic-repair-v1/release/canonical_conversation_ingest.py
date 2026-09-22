#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bindings import load_canonical_adapter


if __name__ == "__main__":
    raise SystemExit(load_canonical_adapter().main())
