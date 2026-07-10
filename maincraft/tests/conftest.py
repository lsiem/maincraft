"""Pytest config: ensure the maincraft package root is importable.

Lets tests do ``import config`` and ``from ingestion import ...`` regardless
of the directory pytest is invoked from. No network access is required by any
test in this suite.
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(__file__)
_ROOT = os.path.dirname(_HERE)  # .../maincraft

if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

FIXTURES = os.path.join(_HERE, "fixtures")
