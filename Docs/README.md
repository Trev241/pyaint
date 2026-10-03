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

1. **Teach / detect** where the palette and canvas are on screen. The result is
   stored in a shared **`Profile`**.
2. **Process** an image: fit it to the canvas, downscale it, and map each pixel
   to the nearest palette colour.
3. **Encode** each row into horizontal runs → a colour-to-strokes map (`cmap`).
4. **Draw**: for each colour, click its palette swatch, then replay its strokes.

Colours are chosen from the sampled **palette**; arbitrary custom colours
(colour-dialog automation) are intentionally not supported.

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
├── painter.py         screen-input driver (ScreenPainter)
├── palette.py         swatch sampling + nearest colour
├── profile.py         Profile: single source of truth for the environment
├── config.py          config.json I/O + env/prefs split
├── targets.py         target recipes + registry
├── locators.py        canvas/palette auto-detection
├── annotate.py        detection preview drawing (regions + swatch centres)
├── validation.py      recipe self-tests
├── cache.py           pre-computation cache (CacheMixin)
├── ui/                PySide6 (Qt) desktop UI
│   ├── main_window.py  main window: panels, tabs, toolbar, status bar
│   ├── setup_dialog.py setup wizard (manual tool teaching)
│   ├── capture.py      full-screen click-capture overlay
│   ├── theme.py        VS Code-style design tokens + stylesheet
│   ├── icons.py        QPainter-drawn line icons
│   └── widgets.py      reusable widgets
├── paths.py           runtime filesystem locations
├── utils.py           sizing + duration helpers
├── errors.py          exceptions
└── log.py             print-based logging shim
```

### Shared environment

`Profile` is the single source of truth for everything the user has taught
Pyaint (palette, canvas, layer/colour buttons, MSPaint mode, selected target).
The main window creates it; the Setup dialog mutates it in place, and `Bot`
holds a reference to the same instance, so there is nothing to merge back.
`Bot` exposes read-only `@property` views (`new_layer`, `color_button`,
`_canvas`, …) onto the profile.

### Configuration split

`config.json` mixes two concerns, separated on load:

- **Environment** (owned by `Profile`): the tool entries, `MSPaint Mode`,
  `target`.
- **Preferences** (owned by `Window`): `pause_key`, `drawing_settings`,
  `drawing_options`, `skip_first_color`, `last_image_url`, `theme`, `draw_mode`.

Legacy environment keys from older versions (`Custom Colors`,
`color_preview_spot`, `color_selection`) are dropped on load.

See [`configuration.md`](configuration.md).

### Processing

`Bot.process()` opens the image, scales it to fit the canvas, downscales by the
pixel step, then `_encode_rows()` maps each pixel to the nearest palette colour
and closes a run whenever the colour changes or a row ends.

- **Layered** (default): builds per-row colour tables, then `_merge_layers()`
  sorts colours by frequency and repaints lower layers, yielding fewer strokes.
- **Slotted**: a direct colour → list-of-runs map.

`process_region()` reuses the same encoder for partial redraws.

### Drawing

`Bot.draw(cmap)` iterates colours, optionally creates a new layer and/or clicks
the colour button(s), selects the swatch through the `ScreenPainter`, then
replays each run as a segmented drag. It supports pause/resume (state is kept in
`draw_state`) and terminates on `ESC`.

### Auto-detection

`locators.py` finds the canvas and palette from a screenshot using declarative
specs from the active recipe: `white_rect`, `color_rect`, `center_rect`,
`color_grid`, `color_signature`, and `window_relative`. `annotate.py` draws the
detected regions and the palette swatch centres into the **Detection** tab so
the result can be confirmed visually. Detection is pure over a PIL image
(headlessly testable); failures fall back to manual teaching.

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
explicit colour map, and screen actions are replaced with fakes.

### Dependencies

`PyAutoGUI` (input/screenshots), `Pillow` (images), `pynput` (global hotkeys),
`pyscreeze`, and **PySide6** (Qt) for the desktop UI. There is no NumPy
dependency.
