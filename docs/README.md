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
- [Building](#building)

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
├── bot.py             facade (Bot.process) + executor (Bot.draw)
├── planner.py         pure planning: image → colour grid → cmap
├── painter.py         screen-input driver (ScreenPainter)
├── palette.py         swatch sampling + nearest colour
├── profile.py         Profile: single source of truth for the environment
├── config.py          config.json I/O + env/prefs split
├── targets.py         target recipes + registry
├── locators.py        canvas/palette auto-detection
├── annotate.py        palette/detection preview drawing (used by Setup + tests)
├── validation.py      recipe self-tests
├── cache.py           pre-computation cache (CacheMixin)
├── ui/                PySide6 (Qt) desktop UI
│   ├── main_window.py  hub: target bar, preview, inspector, action/status bars
│   ├── setup_dialog.py setup wizard (manual tool teaching)
│   ├── previews.py     render/save/load the region previews (Setup + auto-detect)
│   ├── capture.py      full-screen click-capture overlay
│   ├── overlay.py      detection-review overlay + progress overlay
│   ├── countdown.py    pre-capture countdown banner
│   ├── search_tasks.py threaded image-search/thumbnail tasks
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
- **Preferences** (owned by `MainWindow`): `pause_key`, `drawing_settings`,
  `drawing_options`, `drawing_by_target`, `environments`, `skip_first_color`,
  `last_image_url`, `theme`, `draw_mode`, `color_metric`,
  `image_search_provider`.

Legacy environment keys from older versions (`Custom Colors`,
`color_preview_spot`, `color_selection`) are dropped on load.

See [`configuration.md`](configuration.md).

### Processing

The pure planner (`planner.py`) does the work; `Bot.process()` just gathers the
environment and delegates. `fit_to_canvas()` insets the canvas by
`CANVAS_PADDING` px, then fits and centres the image,
`quantize_image()` supersamples each cell and majority-votes in palette space to
produce the shared colour grid (removing isolated compression / anti-aliasing
artifacts at the source), and `plan()` turns that grid into a stroke map.
Outline asks for `source_quality=True`, sampling at the source resolution so a
thin anti-aliased contour is resolved consistently rather than fragmented.

- **Layered**: builds per-row colour tables, then `_merge_layers()`
  sorts colours by frequency and repaints lower layers, yielding fewer strokes.
- **Slotted**: a direct colour → list-of-runs map.
- **Outline** (default, `plan_regions`): traces region boundaries into one
  closed polyline per contour in `OUTLINE_COLOUR`. `stroke_distance` is
  retained for compatibility and no longer changes the plan.

`process_region()` reuses `fit_region()` + the same quantize/plan steps for
partial redraws.

### Drawing

`Bot.draw(cmap)` iterates colours, optionally creates a new layer and/or clicks
the colour button(s), selects the swatch through the `ScreenPainter`, then
replays each run as a segmented drag. It supports pause/resume (state is kept in
`draw_state`) and terminates on `ESC`.

### Auto-detection

`locators.py` finds the canvas and palette from a screenshot using declarative
specs from the active recipe: `white_rect`, `color_rect`, `center_rect`,
`color_grid`, `color_signature`, and `window_relative`. A locator's `region`
crop can be anchored to the target window with `region_window`, so a tight
search area (e.g. Paint's Colors ribbon) follows the window instead of assuming
a fixed screen layout. Such window-relative crops are authored at 96 DPI and
scaled by the window's display factor, so detection also works at 125%/150%
scaling. Detection is pure over a PIL image (headlessly testable); failures fall
back to manual teaching. Applying a detection is non-destructive: a region the
recipe did not find is left alone, so a failed auto-detect can never wipe a
palette or canvas taught by hand. Review happens on screen: `overlay.py`
dims the desktop, spotlights the detected canvas/palette with palette
cell-centre dots, and offers Use / Try again / Teach manually / Not now.

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
- [Releasing](releasing.md)

## Development

```bash
pip install -e ".[dev,build]"
python -m pytest -q          # headless; no display required
python scripts/build_exe.py  # build dist/pyaint.exe
```

Tests live in `tests/` and never touch the screen: `Palette` is built from an
explicit colour map, and screen actions are replaced with fakes.

### Building

Building produces a single, self-contained `dist/pyaint.exe` that bundles
Python and the runtime dependencies, so end users don't need Python installed.
The build is **Windows-only** and requires the optional `build` extra:

```bash
pip install -e ".[build]"    # installs PyInstaller
python scripts/build_exe.py  # wraps: pyinstaller --noconfirm --clean pyaint.spec
```

The checked-in `pyaint.spec` drives the build, so the same result is produced
locally and in CI. When frozen, `config.json`, `cache/`, and `targets/` are
written **next to** the executable, so ship it in a writable folder. See
[Releasing](releasing.md) for the post-build smoke test and release steps.

### Dependencies

`PyAutoGUI` (input/screenshots), `Pillow` (images), `pynput` (global hotkeys),
`pyscreeze`, **PySide6** (Qt) for the desktop UI, and **NumPy + OpenCV
(`cv2`)** — the Outline planner uses `cv2.findContours`/`approxPolyDP` to trace
region contours.
