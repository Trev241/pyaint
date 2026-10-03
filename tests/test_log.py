"""Tests for the logging shim."""

import pyaint_log
from pyaint_log import _Log


def test_default_level_shows_everything(capsys):
    log = _Log()
    assert log.level == pyaint_log._LEVELS["debug"]
    log.debug("dbg")
    log.info("inf")
    out = capsys.readouterr().out
    assert "dbg" in out and "inf" in out


def test_level_filters_lower_levels(capsys):
    log = _Log(level="warning")
    log.info("hidden")
    log.warning("shown")
    out = capsys.readouterr().out
    assert "hidden" not in out
    assert "shown" in out
