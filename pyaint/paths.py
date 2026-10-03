"""Filesystem locations used at runtime.

Centralises the paths that used to be recomputed with ``os.path.dirname`` calls
scattered through the UI, so moving modules inside the package cannot silently
shift them.
"""

import os

# ``<repo>/pyaint/paths.py`` -> ``<repo>``
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.json")
TARGETS_DIR = os.path.join(PROJECT_ROOT, "targets")
USER_TARGETS_DIR = os.path.join(os.path.expanduser("~"), ".pyaint", "targets")
