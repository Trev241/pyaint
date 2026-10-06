# Architecture

How Pyaint is put together. For the API surface, see [api.md](api.md); for the
quick start, see the [root README](../README.md).

## Bird's-eye view

Pyaint is Windows-only screen-automation software. It has four conceptual
layers, separated by a purity boundary (the planner has no screen access and no
session state):

| Layer | Module | Responsibility |
|-------|--------|----------------|
| UI | `pyaint/ui/` | PySide6 window, worker threads, config persistence |
| Planner | `pyaint/planner.py` | **pure** — image → colour grid → `cmap` |
| Executor | `pyaint/bot.py` | `Bot` facade + `Bot.draw`: pause/resume, progress, strokes |
| Driver | `pyaint/painter.py` | `ScreenPainter`: screen capture + synthetic input |

Supporting data and helpers: `profile.py` (taught environment), `targets.py`
(recipes), `locators.py` (auto-detection), `annotate.py` (preview),
`palette.py`, `cache.py`, `config.py`, `utils.py`.

The key design rule: **the planner never branches on app identity.** App
differences live in a declarative recipe (data) and behind the `ScreenPainter`
seam (code).

## The shared Profile

Both the UI and the engine need the same environment geometry. Rather than
keeping two copies, `MainWindow` creates one `Profile` and hands a reference to
`Bot`:

```
MainWindow ─┐
            ├── self.profile ──▶ Profile (tools, mspaint_mode, target)
Bot ────────┘
```

`SetupDialog` receives that same object and mutates it in place, so nothing has
to be merged back after setup. `Bot` exposes read-only `@property` views
(`new_layer`, `color_button`, `_canvas`, …) so the engine's historical
attribute access keeps working.

`Profile` is a `Mapping` over the tool entries, so UI code can still use
`profile["Palette"]`, `profile.items()`, and `profile.get(...)`.

## Configuration

`config.json` mixes two concerns and is split on load:

- **Environment** → `Profile`: the tool entries, `MSPaint Mode`, `target`.
- **Preferences** → `MainWindow.tools`: `pause_key`, `drawing_settings`,
  `drawing_options`, `drawing_by_target`, `environments`, `skip_first_color`,
  `last_image_url`, `theme`, `draw_mode`, `color_metric`,
  `image_search_provider`.

On save the two are merged: `{**preferences, **profile.to_config()}`. Legacy
environment keys from older versions are dropped on load.

### Box formats

Two shapes are in play:

- **Corner box** `[x1, y1, x2, y2]` — stored in `profile[tool]["box"]`.
- **Rect** `(x, y, w, h)` — used by `pyautogui` and `Palette`.

The `canvas_rect()` / `palette_rect()` helpers do the conversion (and tolerate
reversed corners).

## Processing pipeline

The pure half lives in `pyaint/planner.py`; `Bot.process()` is a thin facade
that opens the image, reads the canvas, and hands the rest over:

1. `fit_to_canvas()` — inset the canvas by `CANVAS_PADDING` px, then
   fit/centre the image and report the output grid size
   (`utils.adjusted_img_size`). It no longer downsamples.
2. `quantize_image(image, (tw, th), palette, metric, flags)` — supersample each
   output cell, map every sample to the nearest palette colour, and take the
   **majority**. Voting in palette space removes isolated compression /
   anti-aliasing artifacts without inventing blend colours, producing the
   colour grid; transparent cells become `None` when `IGNORE_TRANSPARENT` is
   set. This is the **shared boundary**: every planning mode consumes the same
   grid. (`quantize()` remains the single-sample fallback.)
3. `plan(grid, xo, yo, step, flags, mode)` — dispatch to the mode planner:
   - **Slotted** / **Layered** (`plan_rows`): run-length encode the grid.
     Slotted appends every run directly; Layered accumulates per-row tables and
     then `_merge_layers()` sorts colours by frequency and merges lower-layer
     runs into fewer strokes.
   - **Outline** (`plan_regions`): traces region boundaries and emits one
     closed polyline per contour in `OUTLINE_COLOUR`. `stroke_distance` is kept
     for API/cache compatibility but no longer affects the plan.

`process_region()` uses `fit_region()` + the same quantize/plan steps for
partial redraws.

## Drawing execution

`Bot.draw(cmap)`:

1. Compute total strokes and report progress through the callback.
2. For each colour: optionally create a new layer, optionally click the colour
   button, select the swatch via `ScreenPainter.select_color()`, optionally
   click the colour-dialog OK button.
3. For each stroke: insert a jump/travel delay if the cursor moved more than
   `jump_threshold`; honour pause/terminate; replay it either as a continuous
   human-paced path (`human_strokes`, the default) or as one segmented run
   (`execute_stroke`). Polylines always take the path route.
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

The UI is built with **PySide6** (`pyaint/ui/`). `MainWindow` is a hub: a top
bar switches the target app, the preview is the hero content, and a right-hand
inspector holds the drawing/environment settings, with a readiness strip, an
action bar, and a status bar. Image search opens a results gallery in the
content area, and detection review is an on-screen overlay (`overlay.py`).
Manual click-teaching lives in `setup_dialog.py`/`capture.py`, the auto-detect
countdown in `countdown.py`, and the gallery's async fetch in `search_tasks.py`.
Theme tokens live in `theme.py` (VS Code "Dark Modern"/"Light Modern"), and
icons are drawn in `icons.py` so no image assets are shipped.

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
