"""Build a standalone ``pyaint.exe`` with PyInstaller.

Usage (from the repo root, on Windows)::

    python scripts/build_exe.py

Requires the optional build dependencies::

    pip install -e ".[build]"

Produces ``dist/pyaint.exe``. This is a thin wrapper around the checked-in
``pyaint.spec`` so the same build is produced locally and in CI.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print(
            "PyInstaller is not installed.\n"
            'Install the build extras first:  pip install -e ".[build]"',
            file=sys.stderr,
        )
        return 1

    # Prefer the module form so the running interpreter is always the one used.
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "pyaint.spec"]
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        return result.returncode

    exe = ROOT / "dist" / ("pyaint.exe" if sys.platform == "win32" else "pyaint")
    if exe.exists():
        size_mb = exe.stat().st_size / (1024 * 1024)
        print(f"Built {exe} ({size_mb:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
