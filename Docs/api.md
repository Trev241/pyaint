# Pyaint API Reference

Reference for the public surface of the `pyaint` package. Imports are absolute
(`from pyaint.bot import Bot`). For how the pieces fit together, see
[architecture.md](architecture.md).

## Contents

- [Profile](#profile)
- [Bot](#bot)
- [Palette](#palette)
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
| `IGNORE_WHITE` | `1` | Flag bit |

### Attributes

`settings = [delay, pixel_size, jump_delay]`, `terminate`, `paused`,
`pause_key`, `drawing`, `skip_first_color`, `jump_threshold`, `profile`,
`painter`, `draw_state`, `progress_callback`, `progress_overlay_enabled`.

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
| `apply_detection(detection)` | Write a `Detection` into the profile/palette |

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

## Palette

`pyaint.palette.Palette` — a rectangular grid of swatches and their screen
coordinates.

```python
Palette(colors_pos=None, box=None, rows=None, columns=None)
```

- `colors_pos`: explicit `{(r,g,b): (x,y)}` (no screen access).
- `box`: `(x, y, w, h)` screenshot region sampled at the centre of each cell
  (using a small median neighbourhood for robustness).

`nearest_color(rgb)` returns the closest swatch by **squared** Euclidean
distance; `Palette.dist(a, b)` exposes the metric.

## ScreenPainter

`pyaint.painter.ScreenPainter(bot)` — all app-specific synthetic input lives
here; `Bot` owns one as `bot.painter`.

| Member | Description |
|--------|-------------|
| `resolve_color_source(target)` | `"palette"` if the swatch is known, else `"none"` |
| `select_color(target)` | Click the swatch for `target` |
| `click_swatch(x, y)` | Click a swatch (honours MSPaint double-click mode) |
| `new_layer()` / `color_button()` / `color_button_okay()` | Optional modifier-clicks |
| `execute_stroke(start, end, delay)` / `execute_test_stroke(start, end)` | Draw a run |

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
