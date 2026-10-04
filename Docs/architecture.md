# Architecture

How Pyaint is put together. For the API surface, see [api.md](api.md); for the
quick start, see the [root README](../README.md).

## Bird's-eye view

Pyaint is Windows-only screen-automation software. It has three conceptual
layers:

```
┌─────────────────────────────────────────────────────────┐
│ UI          pyaint/ui/window.py, pyaint/ui/setup.py     │
│             (Tk widgets, threads, config persistence)   │
├─────────────────────────────────────────────────────────┤
│ Planner     pyaint/bot.py                               │
│             image → cmap → ordered stroke execution     │
├─────────────────────────────────────────────────────────┤
│ Driver      pyaint/painter.py (ScreenPainter)           │
│             screen capture + synthetic mouse/keyboard   │
└─────────────────────────────────────────────────────────┘
```

Supporting data and helpers: `profile.py` (taught environment), `targets.py`
(recipes), `locators.py` (auto-detection), `annotate.py` (preview),
`palette.py`, `cache.py`, `config.py`, `utils.py`.

The key design rule: **the planner never branches on app identity.** App
differences live in a declarative recipe (data) and behind the `ScreenPainter`
seam (code).

## The shared Profile

Both the UI and the engine need the same environment geometry. Rather than
keeping two copies, `Window` creates one `Profile` and hands a reference to
`Bot`:

```
Window ─┐
        ├── self.profile ──▶ Profile (tools, mspaint_mode, target)
Bot ────┘
```

`SetupWindow` receives that same object and mutates it in place, so nothing has
to be merged back after setup. `Bot` exposes read-only `@property` views
(`new_layer`, `color_button`, `_canvas`, …) so the engine's historical
attribute access keeps working.

`Profile` is a `Mapping` over the tool entries, so UI code can still use
`profile["Palette"]`, `profile.items()`, and `profile.get(...)`.

## Configuration

`config.json` mixes two concerns and is split on load:

- **Environment** → `Profile`: the tool entries, `MSPaint Mode`, `target`.
- **Preferences** → `Window.tools`: `pause_key`, `drawing_settings`,
  `drawing_options`, `skip_first_color`, `last_image_url`, `theme`, `draw_mode`.

On save the two are merged: `{**preferences, **profile.to_config()}`. Legacy
environment keys from older versions are dropped on load.

### Box formats

Two shapes are in play:

- **Corner box** `[x1, y1, x2, y2]` — stored in `profile[tool]["box"]`.
- **Rect** `(x, y, w, h)` — used by `pyautogui` and `Palette`.

The `canvas_rect()` / `palette_rect()` helpers do the conversion (and tolerate
reversed corners).

## Processing pipeline

`Bot.process(file, flags, mode)`:

1. Open the image and convert to `RGBA`.
2. Read the canvas rect (`NoCanvasError` if unset).
3. Compute the fitted, centred size with `utils.adjusted_img_size()`.
4. Downscale by the pixel step with `Image.Resampling.NEAREST`.
5. Call `_encode_rows()`.

`_encode_rows(pix, w, h, xo, y, step, flags, mode)` walks the downsampled grid,
resolves each pixel's colour (memoised per RGB), and closes a run when the
colour changes or the row ends. Each run goes to `_emit_run()`.

- **Slotted**: `cmap.setdefault(color, []).append((start, end))`, honouring
  `IGNORE_WHITE`.
- **Layered**: accumulate per-row `(color, run)` tables and colour frequencies,
  then `_merge_layers()` sorts colours by descending frequency and merges
  lower-layer runs into fewer strokes.

`process_region()` crops, scales, and reuses the same encoder for partial
redraws.

## Drawing execution

`Bot.draw(cmap)`:

1. Compute total strokes and report progress through the callback.
2. For each colour: optionally create a new layer, optionally click the colour
   button, select the swatch via `ScreenPainter.select_color()`, optionally
   click the colour-dialog OK button.
3. For each run: insert a jump delay if the cursor moved more than
   `jump_threshold`; honour pause/terminate; replay the run as a segmented drag.
4. Report estimated vs actual time and reset state.

Pause/terminate is driven by the global `pynput` listener in
`pyaint/__main__.py`, which sets `bot.paused` / `bot.terminate`. Resume state
(`draw_state`) records the colour/line index, and the interrupted stroke is
replayed for a clean result.

## Colour selection

Colours are selected from the sampled palette. The driver's
`ColorSelectionChain` resolves each target to `palette` if the swatch is known,
otherwise `none` (the colour is skipped). `resolve` decides without performing
input; `apply` clicks the swatch. Arbitrary custom colours (colour-dialog
automation) are not supported.

## Target recipes

A recipe is data describing a target app:

- which `tools` Setup should show,
- the `drawing_settings` / `drawing_options` defaults,
- optional fixed `palette`,
- `detection` locator specs.

Built-ins live in `pyaint/targets.py`; user recipes load from `targets/` and
`~/.pyaint/targets/`. `extends` deep-merges a parent recipe (including the
hidden bases `desktop-base` and `browser-base`). `pyaint/validation.py`
self-checks recipes against the schema and the locator registry.

## Auto-detection

`pyaint/locators.py` is pure over a PIL image (headlessly testable), with a
registry of locator types:

| Type | Finds |
|------|-------|
| `white_rect` | a large near-white rectangle (canvas) |
| `color_rect` | a large solid-colour rectangle |
| `center_rect` | a solid rectangle grown from the image centre (border-aware) |
| `color_grid` | a grid of saturated swatches (bbox + rows/cols) |
| `color_signature` | the block covering the most distinct listed colours |
| `window_relative` | a sub-rectangle of an OS window |

A spec may be a single locator or an ordered chain (first success wins), and
every locator accepts a `region` crop. `detect_target()` returns a `Detection`;
failure is silent so the UI can fall back to manual teaching.

## UI and threading

The UI is built with **PySide6** (`pyaint/ui/`). `MainWindow` is a VS Code-style
shell: an activity rail selects a sidebar panel (Draw / Image / Settings), the
content area shows the image preview, and the status bar shows progress. Theme
tokens live in `theme.py` (VS Code "Dark Modern"), and icons are drawn in
`icons.py` so no image assets are shipped.

Long-running work (precompute, test draw, draw, region redraw) runs
on daemon `threading.Thread`s. `Bot` reports progress through
`progress_callback`, which the window connects to a Qt signal; Qt then queues
the update onto the main thread. This keeps all widget access on the UI thread
(the historical Tk overlay was updated from a worker thread and could be flaky).

Manual teaching ("click the palette corners") uses a translucent, always-on-top
`QDialog` that records global clicks (`capture.py`), so it is cross-platform and
does not depend on `pynput`.

## Runtime paths

`pyaint/paths.py` centralises locations. When frozen by PyInstaller it uses the
directory containing the executable so `config.json`, `cache/`, and `targets/`
persist; otherwise it uses the repository root.

## Boundaries

- No application APIs: everything is screen coordinates plus synthetic input.
- Windows-first; no cross-platform guarantees.
- Network access is limited to fetching an image the user supplies by URL, or
  searching Openverse / Wikimedia Commons when the Image field holds search
  words (`pyaint/image_search.py`).
- No anti-detection / input-spoofing code. Locating a target's UI is in scope;
  hiding automation is not.
