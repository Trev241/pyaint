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
- [Calibration](#calibration)
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
    color_selection="auto",   # "auto" | "palette" | "custom"
    calibration=None,         # {(r, g, b): (x, y)} or None
    target="generic",         # selected recipe id
)
```

Tool keys: `Palette`, `Canvas`, `Custom Colors`, `New Layer`, `Color Button`,
`Color Button Okay`, `color_preview_spot`. Access via `profile["Palette"]`, and
check `profile.is_ready("Canvas")` for the `status` flag.

| Member | Description |
|--------|-------------|
| `from_config(config)` / `to_config()` | Environment subset of `config.json` (excludes calibration) |
| `to_dict()` / `from_dict(data)` | Full versioned, shareable preset (includes calibration) |
| `canvas_rect()` / `palette_rect()` / `custom_colors_rect()` | `(x, y, w, h)` or `None` (converts the stored corner box) |
| `box_to_wh(box)` | Module helper: `[x1,y1,x2,y2]` → `(x,y,w,h)` |
| `ENV_CONFIG_KEYS` | Keys owned by the profile (not preferences) |

## Bot

`pyaint.bot.Bot` — the drawing engine facade. Inherits `CalibrationMixin` and
`CacheMixin`.

```python
Bot(config_file="config.json", profile=None)
```

### Constants

| Name | Value | Meaning |
|------|-------|---------|
| `DELAY`, `STEP`, `ACCURACY`, `JUMP_DELAY` | `0..3` | Indices into `settings` |
| `SLOTTED`, `LAYERED` | `"slotted"`, `"layered"` | Processing modes |
| `IGNORE_WHITE` | `1` | Flag bit |
| `USE_CUSTOM_COLORS` | `2` | Flag bit |

### Attributes

`settings = [delay, pixel_size, precision, jump_delay]`, `terminate`, `paused`,
`pause_key`, `drawing`, `skip_first_color`, `jump_threshold`, `progress`,
`profile`, `painter`, `draw_state`, `progress_overlay_enabled`.

Legacy views onto the profile: `new_layer`, `color_button`,
`color_button_okay`, `mspaint_mode`, `color_calibration_map` (settable),
`_canvas`, `_custom_colors`.

### Environment

| Method | Description |
|--------|-------------|
| `init_palette(colors_pos=None, prows=None, pcols=None, pbox=None, valid_positions=None, manual_centers=None)` | Build the live `Palette`; `pbox` is `(x, y, w, h)` |
| `init_canvas(cabox)` | Store the canvas **corner** box and enable it |
| `init_custom_colors(ccbox)` | Store the custom-colour box and scan the spectrum |

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

`pyaint.palette.Palette` — swatches and their screen coordinates.

```python
Palette(colors_pos=None, box=None, rows=None, columns=None,
        valid_positions=None, manual_centers=None)
```

- `colors_pos`: explicit `{(r,g,b): (x,y)}` (no screen access).
- `box`: `(x, y, w, h)` screenshot region sampled at cell centres.
- `valid_positions`: indices to sample; `manual_centers`: `{index: (x, y)}`.

`nearest_color(rgb)` returns the closest swatch by **squared** Euclidean
distance; `Palette.dist(a, b)` exposes the metric.

## ScreenPainter

`pyaint.painter.ScreenPainter(bot)` — all app-specific synthetic input lives
here; `Bot` owns one as `bot.painter`.

| Member | Description |
|--------|-------------|
| `capabilities` | `Capabilities` flags derived from the profile |
| `resolve_color_source(target, force_custom=False)` | Choose `palette`/`calibrated`/`keyboard`/`none` without input |
| `select_color(target, force_custom=False)` | Perform the selection |
| `click_swatch(x, y)` | Click a swatch (honours MSPaint double-click mode) |
| `enter_rgb_keyboard(rgb)` | Type RGB into a colour dialog |
| `new_layer()` / `color_button()` / `color_button_okay()` | Optional modifier-clicks |
| `execute_stroke(start, end, delay)` / `execute_test_stroke(start, end)` | Draw a run |

`ColorSelectionChain` holds the ordered palette → calibrated → keyboard
strategies.

## Targets

`pyaint.targets` — declarative recipes.

| Member | Description |
|--------|-------------|
| `Recipe` | Dataclass: `tools`, `color_selection`, capability flags, `drawing_settings`, `drawing_options`, `detection`, `extends`, `hidden` |
| `RecipeRegistry` | `register`, `add_from_dict` (resolves `extends`), `get`, `all`, `load_dir` |
| `get_recipe(id)` / `list_recipes()` | Look up built-ins and loaded recipes |
| `load_user_recipes(paths=None)` | Load JSON from `targets/` and `~/.pyaint/targets/` |
| `apply_profile_defaults(profile, recipe)` | Apply a recipe's environment defaults in place |
| `validate_recipe(recipe)` / `recipe_is_valid(recipe)` | Static self-tests (`pyaint.validation`) |

## Locators

`pyaint.locators` — pure functions over a PIL image; `None` when not found.

- `find_white_rect`, `find_color_rect`, `find_center_rect`,
  `find_color_grid`, `find_color_signature`
- `window_relative_rect(window, normalized)`, `get_window_rect(title)`
- `detect_target(recipe, image, window_provider=None)` → `Detection`
- `Detection` — `canvas`, `palette`, `palette_rows`, `palette_cols`; falsy when
  empty

New locator types register with `register_locator(name, allowed_params)` and are
introspectable via `available_locators()` / `locator_params(name)`.

## Calibration

`pyaint.calibration.CalibrationMixin` (mixed into `Bot`).

| Method | Description |
|--------|-------------|
| `calibrate_custom_colors(grid_box, preview_point, step=2)` | Scan the spectrum → `{(r,g,b): (x,y)}`; cancellable via `terminate` |
| `save_color_calibration(filepath)` / `load_color_calibration(filepath)` | JSON form `{"r,g,b": [x, y]}` |
| `get_calibrated_color_position(target_rgb, tolerance=20, k_neighbors=4)` | Tolerance match, then inverse-distance-weighted kNN |

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
| `split_preferences(config)` | Non-environment keys |
| `build_payload(preferences, profile)` | Merge preferences with `profile.to_config()` |

## Utils & errors

`pyaint.utils`: `adjusted_img_size(img, (w, h))`, `format_duration(seconds)`,
`format_estimate(seconds)`, `estimate_drawing_seconds(cmap, delay, jump_delay,
jump_threshold)`.

`pyaint.errors`:

| Exception | Raised when |
|-----------|-------------|
| `NoToolError` | Base for "a required tool is missing" |
| `NoPaletteError` | Palette missing or has faulty dimensions |
| `NoCanvasError` | Canvas is not initialized |
| `NoCustomColorsError` | Custom colours are required but not initialized |
| `CorruptConfigError` | Reserved for invalid configuration |
