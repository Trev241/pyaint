"""The process must be per-monitor DPI aware before pyautogui can pin it.

``pyautogui``/``pyscreeze`` call ``SetProcessDPIAware()`` on import and Qt
cannot upgrade past that, so the claim has to happen from ``pyaint/__init__``.
A fresh subprocess is the only honest way to test the import ordering; the
pytest process has long since imported pyaint.
"""

import os
import subprocess
import sys

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="Windows-only DPI awareness APIs"
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run_script(code: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_pyaint_claims_per_monitor_dpi_before_pyautogui_loads():
    result = _run_script(
        "import pyaint\n"
        "from pyaint import dpi\n"
        "before = dpi.current_awareness()\n"
        "import pyautogui\n"
        "after = dpi.current_awareness()\n"
        "print(before, after)\n"
    )
    assert result.returncode == 0, result.stderr
    before, after = result.stdout.split()
    assert before.startswith("per-monitor"), before
    # Importing pyautogui must not downgrade the claim.
    assert after == before


def test_claim_is_idempotent():
    from pyaint import dpi

    first = dpi.enable_per_monitor_dpi()
    assert first == dpi.enable_per_monitor_dpi()
    assert dpi.current_awareness().startswith("per-monitor")
