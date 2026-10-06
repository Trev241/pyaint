# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for a standalone Windows build of Pyaint.

Build with::

    pip install -e ".[build]"
    pyinstaller pyaint.spec

The result is ``dist/pyaint.exe`` (single file). User data (``config.json``,
``color_calibration.json``, ``cache/``, ``targets/``) is written next to the
executable — see ``pyaint/paths.py``.
"""

from PyInstaller.utils.hooks import collect_submodules

# pynput loads its platform backends lazily; collect them so the listener and
# the setup-wizard click capture work from a frozen build.
hiddenimports = collect_submodules("pynput")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # numpy + OpenCV (cv2) are real runtime dependencies: the Outline planner
    # uses cv2.findContours/approxPolyDP to trace region contours. Exclude the
    # other heavy scientific stacks that PyInstaller might otherwise pull in
    # from whatever happens to be installed in the build environment.
    excludes=[
        "scipy",
        "matplotlib",
        "pandas",
        "IPython",
        "pytest",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="pyaint",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    # Keep a console for v0.1.0: the app logs progress and errors there and it
    # makes bug reports actionable. Revisit before a polished 1.0.
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
