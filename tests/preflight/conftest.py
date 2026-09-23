"""Operator tools are intentionally outside the frozen/installable Core package."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
