# Pyaint API Reference

Reference for the public surface of the `pyaint` package. Imports are absolute
(`from pyaint.bot import Bot`). For how the pieces fit together, see
[architecture.md](architecture.md).

## Contents

- [Profile](#profile)
- [Bot](#bot)
- [Planner](#planner)
- [Palette](#palette)
- [Image search](#image-search)
- [ScreenPainter](#screenpainter)
- [Targets](#targets)
- [Locators](#locators)
- [Cache](#cache)
- [Config](#config)
- [Utils & errors](#utils--errors)

---

## Profile

`pyaint.profile.Profile` — the single source of truth for the taught
environment. It behaves as a `Mapping` over tool entries.

```python
Profile(
    tools=None,               # {tool_name: {...}} overrides
    mspaint_mode=None,        # {"enabled": bool, "delay": float}
    target="generic",         # selected recipe id
)
```

Tool keys: `Palette`, `Canvas`, `New Layer`, `Color Button`,
`Color Button Okay`. Access via `profile["Palette"]`, and check
`profile["Canvas"]["status"]` for the "configured" flag.

| Member | Description |
|--------|-------------|
| `from_config(config)` / `to_config()` | Environment subset of `config.json` |
| `canvas_rect()` / `palette_rect()` | `(x, y, w, h)` or `None` (converts the stored corner box) |
| `box_to_wh(box)` | Module helper: `[x1,y1,x2,y2]` → `(x,y,w,h)` |
| `ENV_CONFIG_KEYS` | Keys owned by the profile (not preferences) |

## Bot

`pyaint.bot.Bot` — the drawing engine facade. Inherits `CacheMixin`.

```python
Bot(profile=None)
```

### Constants

| Name | Value | Meaning |
|------|-------|---------|
| `DELAY`, `STEP`, `JUMP_DELAY` | `0..2` | Indices into `settings` |
| `SLOTTED`, `LAYERED` | `"slotted"`, `"layered"` | Processing modes |
| `IGNORE_WHITE` | `1` | Flag bit: skip pure-white runs |
| `IGNORE_TRANSPARENT` | `2` | Flag bit: skip pixels with alpha < `ALPHA_CUTOFF` (128) |

### Attributes

`settings = [delay, pixel_size, jump_delay]`, `terminate`, `paused`,
`pause_key`, `drawing`, `skip_first_color`, `jump_threshold`, `color_metric`,
`profile`, `painter`, `draw_state`, `progress_callback`,
`progress_overlay_enabled`.

`color_metric` selects palette matching: `"ciede2000"` (perceptual, default)
or `"rgb"` (legacy squared Euclidean). See
`pyaint.palette.METRIC_CIEDE2000` / `METRIC_RGB` / `DEFAULT_METRIC`.

Legacy views onto the profile: `new_layer`, `color_button`,
`color_button_okay`, `mspaint_mode`, `_canvas`.

### Environment

| Method | Description |
|--------|-------------|
| `init_palette(colors_pos=None, prows=None, pcols=None, pbox=None)` | Build the live `Palette`; `pbox` is `(x, y, w, h)` |
| `init_canvas(cabox)` | Store the canvas **corner** box and enable it |

### Detection

| Method | Description |
|--------|-------------|
| `capture_screen()` | Return the current screen as a PIL image |
| `detect_target(recipe=None)` | Run the recipe's locators → `Detection` |
| `apply_detection(detection, image=None)` | Write a `Detection` into the profile/palette |

### Processing

| Method | Description |
|--------|-------------|
| `process(file, flags=0, mode=LAYERED)` | Return `cmap: {(r,g,b): [((x1,y1),(x2,y2)), ...]}` |
| `process_region(file, region, flags=0, mode=LAYERED, canvas_target=None)` | Process a sub-region, optionally into a target rect |
| `estimate_drawing_time(cmap)` | Human-readable estimate |

### Drawing

| Method | Description |
|--------|-------------|
| `draw(cmap)` | Draw the full map; returns `"success"` or `"terminated"` |
| `test_draw(cmap, max_lines=20)` | Draw the first N strokes |
| `simple_test_draw()` | Draw five short lines to tune brush size |

## Planner

`pyaint.planner` — the **pure** planning half of the engine: no screen access,
no session state. `Bot.process()` / `process_region()` gather the environment
and delegate here, so the same functions are headlessly testable and cacheable.

| Function | Description |
|----------|-------------|
| `fit_to_canvas(image, canvas, step)` / `fit_region(image, region, canvas, step, canvas_target=None)` | Inset the canvas by `CANVAS_PADDING`, then fit/crop and centre → `(source, (tw, th), xo, yo)` |
| `quantize(pix, w, h, palette, metric, flags)` | Pixels → colour grid: `grid[row][col] -> colour \| None` (single-sample) |
| `quantize_image(image, (tw, th), palette, metric, flags)` | Palette-aware majority downsample of the full source → colour grid (numpy-accelerated) |
| `plan_rows(grid, xo, yo, step, flags, mode)` | Colour grid → `cmap` (slotted / layered) |
| `plan_regions(grid, xo, yo, step, flags, mode, stroke_distance=STROKE_DISTANCE)` | Colour grid → `cmap` of closed polylines, one per contour (outline mode) |
| `plan(grid, xo, yo, step, flags, mode, stroke_distance=STROKE_DISTANCE)` | Dispatch by mode (`OUTLINE` → `plan_regions`, else `plan_rows`) |
| `plan_image(...)` / `plan_region_image(...)` | Whole-image / sub-region entry points; both accept `stroke_distance` |
| `SLOTTED` / `LAYERED` / `OUTLINE`, `IGNORE_WHITE`, `IGNORE_TRANSPARENT`, `ALPHA_CUTOFF`, `STROKE_DISTANCE`, `CANVAS_PADDING` | Mode + flag constants (re-exported on `Bot`) |

`stroke_distance` (outline mode) is retained for API / cache compatibility and
no longer changes the plan: every traced contour is emitted as one polyline.
`Bot` still exposes it as `Bot.stroke_distance`, and the UI shows the control
only when Outline is selected.

`quantize_image` supersamples each output cell and takes the modal palette
colour, which votes out isolated compression / anti-aliasing artifacts at the
source. It uses numpy when available and falls back to single-sample
`quantize` otherwise.

`cmap` is `{(r, g, b): [((x1, y1), (x2, y2)), ...]}`.

## Palette

`pyaint.palette.Palette` — a rectangular grid of swatches and their screen
coordinates.

```python
Palette(colors_pos=None, box=None, rows=None, columns=None, image=None)
```

- `colors_pos`: explicit `{(r,g,b): (x,y)}` (no screen access).
- `box`: `(x, y, w, h)` screenshot region sampled at the centre of each cell
  (using a small median neighbourhood for robustness).
- `image`: sample from this PIL image instead of taking a fresh screenshot.

`nearest_color(rgb, metric=DEFAULT_METRIC)` returns the closest swatch.
`metric="ciede2000"` (default) compares perceptual CIELAB difference via
CIEDE2000; `metric="rgb"` uses the legacy squared Euclidean distance.
`Palette.dist(a, b)` exposes the legacy metric, and
`pyaint.palette.rgb_to_lab` / `ciede2000` expose the perceptual one.

## Image search

`pyaint.image_search` — keyless, paged lookup used when the Image field holds
search words instead of a URL or path. Two providers are supported and the UI
has a **Search source** selector: **Openverse** (default; broad, CC-licensed
coverage from Flickr, museums, and more) and **Wikimedia Commons**
(encyclopedic — strong for diagrams). Results come back in the engine's
relevance order (no drawing/photo bias). Openverse caps anonymous requests at
20 results per page; `_search_openverse` clamps `limit` to that so paging never
hits its HTTP 401 `page_size` error.

| Function | Description |
|----------|-------------|
| `search_page(query, *, provider="openverse", cont=None, limit=30, thumb_width=240)` | One page of results → `SearchPage` |
| `fetch_bytes(url)` | Download an image (thumbnails and commits) |
| `PROVIDERS` / `PROVIDER_IDS` / `provider_name(id)` | The selectable sources and their labels |

`SearchPage` has `candidates` (a list of `ImageCandidate`) and `next_continue`
(the provider's token for the next page — a MediaWiki continuation dict or an
Openverse page number — or `None`).
`ImageCandidate` carries `url` (full), `thumb_url`, `mime`, `title`,
`source_url`, `width`, and `height`. SVG and formats PIL cannot open are
filtered out. `provider` is persisted as `image_search_provider` in
`config.json`. The gallery's async fetching lives in `pyaint/ui/search_tasks.py`
(`SearchPageTask`, `ThumbnailTask`), which emit on the global `QThreadPool` so
browsing never blocks the drawing worker.

## ScreenPainter

`pyaint.painter.ScreenPainter(bot)` — all app-specific synthetic input lives
here; `Bot` owns one as `bot.painter`.

| Member | Description |
|--------|-------------|
| `resolve_color_source(target)` | `"palette"` if the swatch is known, else `"none"` |
| `select_color(target)` | Click the swatch for `target` |
| `click_swatch(x, y)` | Click a swatch (honours MSPaint double-click mode) |
| `new_layer()` / `color_button()` / `color_button_okay()` | Optional modifier-clicks |
| `execute_path(points, speed, frame_interval, settle)` / `execute_stroke(start, end, delay)` / `execute_test_stroke(start, end)` | Draw a continuous paced polyline / a single segmented run |

`ColorSelectionChain` resolves and applies palette-swish selection.

## Targets

`pyaint.targets` — declarative recipes.

| Member | Description |
|--------|-------------|
| `Recipe` | Dataclass: `tools`, capability flags, `drawing_settings`, `drawing_options`, `detection`, `extends`, `hidden` |
| `RecipeRegistry` | `register`, `add_from_dict` (resolves `extends`), `get`, `all`, `load_dir` |
| `get_recipe(id)` / `list_recipes()` | Look up built-ins and loaded recipes |
| `load_user_recipes(paths=None)` | Load JSON from `targets/` and `~/.pyaint/targets/` |
| `apply_profile_defaults(profile, recipe)` | Apply a recipe's environment defaults in place |
| `validate_recipe(recipe)` | Static self-tests (`pyaint.validation`) |

## Locators

`pyaint.locators` — pure functions over a PIL image; `None` when not found.

- `find_white_rect`, `find_color_rect`, `find_center_rect`,
  `find_color_grid`, `find_color_signature`
- `window_relative_rect(window, normalized)`, `get_window_rect(title)`
- `detect_target(recipe, image, window_provider=None)` → `Detection`
- `Detection` — `canvas`, `palette`, `palette_rows`, `palette_cols`; falsy when
  empty

`pyaint.annotate.annotate_detection(image, detection)` draws the regions and
palette swatch centres onto a screenshot copy.

New locator types register with `register_locator(name, allowed_params)` and are
introspectable via `available_locators()` / `locator_params(name)`.

## Cache

`pyaint.cache.CacheMixin` (mixed into `Bot`).

| Method | Description |
|--------|-------------|
| `get_cache_filename(image_path, flags=0, mode=LAYERED)` | `cache/{image}_{settings}.json`, or `None` without a canvas |
| `precompute(image_path, flags=0, mode=LAYERED)` | Process and write the cache |
| `load_cached(cache_file)` | Validated cache dict (settings, canvas, age) or `None` |
| `get_cached_status(image_path, flags=0, mode=LAYERED)` | `(bool, cache_file)` |

## Config

`pyaint.config` — `config.json` I/O.

| Function | Description |
|----------|-------------|
| `load_config(path)` | Dict, or `{}` if missing/invalid |
| `save_config(path, payload)` | Write JSON; `bool` success |
| `split_preferences(config)` | Non-environment keys (legacy keys dropped) |
| `build_payload(preferences, profile)` | Merge preferences with `profile.to_config()` |

## Utils & errors

`pyaint.utils`: `adjusted_img_size(img, (w, h))`, `grid_centers(box, rows, cols)`,
`format_duration(seconds)`, `format_estimate(seconds)`,
`estimate_drawing_seconds(cmap, delay, jump_delay, jump_threshold)`.

`pyaint.errors`:

| Exception | Raised when |
|-----------|-------------|
| `NoToolError` | Base for "a required tool is missing" |
| `NoPaletteError` | Palette missing or has faulty dimensions |
| `NoCanvasError` | Canvas is not initialized |
