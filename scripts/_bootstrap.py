"""Garante que a raiz do projeto esteja no sys.path ao rodar scripts/*.py direto."""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_root = str(_PROJECT_ROOT)
if _root not in sys.path:
    sys.path.insert(0, _root)
