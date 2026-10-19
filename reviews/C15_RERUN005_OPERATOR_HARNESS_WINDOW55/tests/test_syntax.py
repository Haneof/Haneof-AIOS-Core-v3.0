"""Static syntax gate for all protected and Window 55 Python source."""
from __future__ import annotations

from pathlib import Path
import unittest

REPO = Path(__file__).resolve().parents[3]
ROOTS = (
    REPO / 'reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-005/harness',
    REPO / 'src/aios_core',
    REPO / 'tools/c15_persistence',
    Path(__file__).resolve().parent,
    Path(__file__).resolve().parents[1],
)


class SyntaxTests(unittest.TestCase):
    def test_all_protected_and_window55_python_sources_compile(self):
        checked = set()
        for root in ROOTS:
            for path in sorted(root.rglob('*.py')):
                if '__pycache__' in path.parts or path in checked:
                    continue
                compile(path.read_bytes(), str(path), 'exec', dont_inherit=True)
                checked.add(path)
        self.assertGreaterEqual(len(checked), 120)


if __name__ == '__main__':
    unittest.main()
