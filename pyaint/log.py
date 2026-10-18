"""Minimal logging shim.

A thin wrapper over ``print`` so output can be levelled or silenced without
pulling in the stdlib ``logging`` machinery (and without changing the existing
console format). The default level is ``debug`` so current behaviour — every
message printed — is preserved.

Set ``PYAINT_LOG_LEVEL`` to ``info``, ``warning`` or ``error`` to quieten it.
"""

import os

_LEVELS = {"debug": 10, "info": 20, "warning": 30, "error": 40, "critical": 50}


class _Log:
    def __init__(self, level=None):
        level = level if level is not None else os.environ.get("PYAINT_LOG_LEVEL", "debug")
        self.level = _LEVELS.get(str(level).lower(), _LEVELS["debug"])

    def _emit(self, level, *args, **kwargs):
        if _LEVELS[level] >= self.level:
            print(*args, **kwargs)

    def debug(self, *args, **kwargs):
        self._emit("debug", *args, **kwargs)

    def info(self, *args, **kwargs):
        self._emit("info", *args, **kwargs)

    def warning(self, *args, **kwargs):
        self._emit("warning", *args, **kwargs)

    def error(self, *args, **kwargs):
        self._emit("error", *args, **kwargs)


log = _Log()
