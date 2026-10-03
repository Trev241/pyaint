# Pyaint Documentation

Pyaint recreates an image by driving the mouse in a painting application. It
captures the palette and canvas from the screen, converts the image into
horizontal brush strokes, and replays them with `pyautogui`.

> This is the documentation index. The root [`README.md`](../README.md) is the
> quickest way to get started.

## Contents

- [Overview](#overview)
- [Install & run](#install--run)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Supported apps & recipes](#supported-apps--recipes)
- [Guides](#guides)
- [Development](#development)

## Overview

Pyaint is Windows-only screen-automation software. There is no API integration
with any drawing app — it works purely from screen pixels and synthetic input.

The pipeline:

1. **Teach / detect** where the palette, canvas, and (optionally) custom-colour
   dialog are on screen. The result is stored in a shared **`Profile`**.
2. **Process** an image: fit it to the canvas, downscale it, and map each pixel
   to the nearest palette colour.
3. **Encode** each row into horizontal runs → a colour-to-strokes map
   (`cmap`).
4. **Draw**: for each colour, select it in the app, then replay its strokes.

## Install & run

See the [root README](../README.md#quick-start) for the release `.exe`, `pipx`,
and source instructions. In short:

```bash
python -m pyaint     # or: python main.py
pyaint               # if installed via pip/pipx
```

## Architecture

All application code lives in the `pyaint/` package; the root `main.py` is a
launcher shim.

```
pyaint/
├── __main__.py        entry point (python -m pyaint)
├── bot.py             engine facade (Bot): process + draw
├── painter.py         screen-input driver (ScreenPainter, Capabilities)
├── palette.py         swatch sampling + nearest colour
├── profile.py         Profile: single source of truth for the environment
├── config.py          config.json I/O + env/prefs split
├── targets.py         target recipes + registry
├── locators.py        canvas/palette auto-detection
├── validation.py      recipe self-tests
├── calibration.py     custom-colour calibration (CalibrationMixin)
├── cache.py           pre-computation cache (CacheMixin)
├── ui/
│   ├── window.py      main Tk window, threads, config
│   └── setup.py       setup wizard
├── paths.py           runtime filesystem locations
├── utils.py           sizing + duration helpers
├── errors.py          exceptions
└── log.py             print-based logging shim
```

### Shared environment

`Profile` is the single source of truth for everything the user has taught
Pyaint (palette, canvas, custom colours, layer/colour buttons, MSPaint mode,
colour-selection strategy, selected target). `Window` creates it; `Bot` holds a
reference to the same instance, so there is nothing to merge back after setup.
Legacy `Bot` attributes (`new_layer`, `color_button`, `_canvas`, …) are
read-only views onto the profile.

### Configuration split

`config.json` mixes two concerns, separated on load:

- **Environment** (owned by `Profile`): tool geometry, `MSPaint Mode`,
  `color_selection`, `target`.
- **Preferences** (owned by `Window`): `pause_key`, `drawing_settings`,
  `drawing_options`, `skip_first_color`, `last_image_url`,
  `calibration_settings`.

See [`configuration.md`](configuration.md).

### Processing

`Bot.process()` opens the image, scales it to fit the canvas, downscales by the
pixel step, then `_encode_rows()` maps each pixel to a colour and closes a run
whenever the colour changes or a row ends.

- **Layered** (default): builds per-row colour tables, then `_merge_layers()`
  sorts colours by frequency and repaints lower layers, yielding fewer strokes.
- **Slotted**: a direct colour → list-of-runs map.

`process_region()` reuses the same encoder for partial redraws.

### Drawing

`Bot.draw(cmap)` iterates colours, optionally creates a new layer and/or clicks
the colour button(s), selects the colour through the `ScreenPainter` colour
chain, then replays each run as a segmented drag. It supports pause/resume
(state is kept in `draw_state`) and terminates on `ESC`.

### Colour selection

`Profile.color_selection` is one of `auto`, `palette`, or `custom`. The driver
resolves each colour to one of four sources — `palette` → `calibrated` →
`keyboard` → `none` — and clicks the corresponding swatch or types RGB values.

### Auto-detection

`locators.py` finds the canvas and palette from a screenshot using declarative
specs from the active recipe: `white_rect`, `color_rect`, `center_rect`,
`color_grid`, `color_signature`, and `window_relative`. Detection is pure over a
PIL image (headlessly testable); failures fall back to manual teaching.

### Caching

`cache/{image_hash}_{settings_hash}.json` stores a pre-computed `cmap`. A cache
is rejected when the settings, canvas, or age (> 24 h) no longer match.

## Configuration

`config.json` lives next to the executable (or in the repo root for a source
checkout). The full key reference is in
[`configuration.md`](configuration.md).

## Supported apps & recipes

Support is delivered through **recipes** (`pyaint/targets.py`), which are data,
not code. A recipe can be extended and overridden by dropping a JSON file in
`targets/` or `~/.pyaint/targets/`. The schema is documented in
[`../targets/README.md`](../targets/README.md).

## Guides

- [Usage guide](usage-guide.md)
- [Tutorial](tutorial.md)
- [Configuration](configuration.md)
- [Troubleshooting](troubleshooting.md)
- [API reference](api.md)
- [Architecture details](architecture.md)

## Development

```bash
pip install -e ".[dev,build]"
python -m pytest -q          # headless; no display required
python scripts/build_exe.py  # build dist/pyaint.exe
```

Tests live in `tests/` and never touch the screen: `Palette` is built from an
explicit colour map, and screen actions are replaced with fakes. See
[`../CONTRIBUTING.md`](../CONTRIBUTING.md).

### Dependencies

`PyAutoGUI` (input/screenshots), `Pillow` (images), `pynput` (global hotkeys),
and `pyscreeze`. `tkinter` ships with Python on Windows. There is no NumPy
dependency.
