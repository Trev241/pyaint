"""Pytest root conftest.

Ensures the repository root is importable so the ``pyaint`` package can be
imported from tests regardless of the working directory.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
