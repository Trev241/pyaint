# Changelog

All notable changes to Pyaint are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project aims to follow [Semantic Versioning](https://semver.org/).

> **Maintenance note:** add new entries under `[Unreleased]` as work happens.
> When releasing, move those entries under a new version heading with the date.
> Internal agent notes live in the gitignored `AGENTS/` folder — see
> [`AGENTS/README.md`](AGENTS/README.md).

## [Unreleased]

### Added
- `pyaint_profile.py`: a `Profile` mapping that is the single source of truth
  for the taught environment (palette, canvas, custom colors, layer/color
  buttons, MSPaint mode, and the color-selection strategy). Includes
  `box_to_wh()`, config splitting (`ENV_CONFIG_KEYS`), and versioned
  `to_dict()` / `from_dict()` preset serialization.
- Headless test suite (`tests/test_profile.py`, `tests/test_pipeline.py`) and
  `conftest.py` so `bot`, `pyaint_profile`, etc. import regardless of cwd.
  Now 38 tests, all passing.
- `pyaint_painter.py`: the `ScreenPainter` seam — `Capabilities` (capability
  flags derived from the profile), `ColorSelectionChain` (palette / calibrated /
  keyboard strategies with the same semantics as the old `_color_source`), and
  all app-specific input actions (modifier clicks, new layer, color button /
  okay, swatch click, RGB keyboard entry, stroke execution).
- `tests/test_painter.py`: headless characterization tests for the seam using a
  fake `pyautogui`.
- `pyaint_targets.py`: a declarative **target recipe** registry so multi-app
  support is data, not code. `Recipe` (schema + `to_dict`/`from_dict`),
  `RecipeRegistry` (with `load_dir` for JSON recipes), and built-in recipes for
  `generic`, `mspaint`, `gimp`, and `skribbl`.
- Main window **Target App** dropdown: selecting a target applies its colour
  strategy and drawing defaults, disables tools it doesn't use, and persists
  the choice (`Profile.target`).
- `tests/test_targets.py`: recipe registry/validation plus `Profile.target`
  round-trip coverage.
- `pyaint_locators.py`: auto-detection engine — `white_rect`, `color_rect`
  (solid-colour canvas), `color_grid` (palette bbox + rows/cols),
  `color_signature`, and `window_relative` locators, plus `detect_target()`
  orchestration. Detection specs may be a single locator or an ordered **chain**
  (tried until one succeeds), and rectangle locators accept an optional
  `aspect`/`aspect_tolerance` filter. `color_signature` picks the blob covering
  the most *distinct* target colours (tie-broken by how densely it fills its
  bbox, with an optional `min_fill`), so a solid multi-colour palette is chosen
  over large single-colour panels and sparse colourful text. Pure over a PIL
  image, so it is testable headless.
- External recipe loading: `pyaint_targets.load_user_recipes()` scans
  `<repo>/targets` and `~/.pyaint/targets` (invalid files skipped); the main
  window loads them at startup so a target can be added with data only. See
  `targets/README.md`.
- `pyaint_palette.py`: the `Palette` class, moved out of `bot.py` (re-exported
  from `bot` for compatibility).
- `tests/test_draw.py`: headless characterization tests for `Bot.draw()` /
  `test_draw()` using a fake `ScreenPainter` (colour selection, stroke ordering,
  skip-first-colour, resume-skip, force-custom, termination, test-draw limit).
- Recipe-default helpers in `pyaint_targets.py` (`merge_drawing_settings`,
  `merge_drawing_options`, `disabled_tools`, `apply_profile_defaults`) with unit
  tests, so applying a target is no longer buried in the UI.
- `pyaint_calibration.py` (`CalibrationMixin`) and `pyaint_cache.py`
  (`CacheMixin`): the calibration and pre-computation cache code moved out of
  `bot.py` into cohesive mixins behind the unchanged `Bot` API.
- `tests/test_calibration.py` and `tests/test_timing.py`: characterization tests
  added before the move.
- `pyaint_log.py`: a tiny logging shim (`log.info/debug/...`) with a
  `PYAINT_LOG_LEVEL` env override; default level `debug` preserves the previous
  console output.
- `pyaint_config.py`: `config.json` I/O (`load_config`, `save_config`) and the
  environment/preferences split (`split_preferences`, `build_payload`); `Window`
  delegates to it. Covered by `tests/test_config.py`.
- `utils.format_duration`, `utils.format_estimate` and
  `utils.estimate_drawing_seconds`: drawing-time helpers extracted from `Bot`
  (which now delegates), covered by `tests/test_timing.py`.
- **Phase 3 — multi-app via recipes:**
  - Locator registry: `register_locator` / `available_locators` /
    `locator_params` in `pyaint/locators.py`; new locator types are additive and
    no longer require editing dispatch code.
  - Recipe `schema_version`, `extends` inheritance (deep-merged via
    `RecipeRegistry.add_from_dict`) and hidden base recipes (`desktop-base`,
    `browser-base`). Hidden recipes resolve for `extends` but are not shown in
    the dropdown.
  - `pyaint/validation.py`: `validate_recipe` / `recipe_is_valid` static
    self-tests (schema version, tools, colour strategy, settings/options keys,
    palette colours, and locator type/params). Built-ins are validated by the
    test suite; user recipes are validated (and logged) on load.
  - MS Paint recipe gains best-effort palette detection (`color_grid`); GIMP
    uses the colour-dialog (`custom`) path. `tests/test_validation.py` plus
    inheritance/locator-registry tests.
- Recipe `detection` specs: skribbl auto-detects its canvas (white 800x600 / 4:3,
  with a `color_rect` fallback that is also aspect-checked) and its exact 2x13
  palette (26 sampled colours, `gap: 0`); MS Paint auto-detects its canvas.
- Main window **Auto-detect** button: finds the target's regions, shows an
  annotated preview for confirmation, and falls back to manual teaching when it
  finds nothing. The window briefly minimizes with a 3-second countdown so the
  target app is in front when the screen is captured (one click, no manual
  screenshots).
- `tests/test_locators.py`: synthetic-image coverage for the locator algorithms,
  `detect_target`, and `Bot.apply_detection`.
- `_color_source()` / `_select_color()` color-selection strategy in `Bot`,
  driven by `Profile.color_selection` (`auto` | `palette` | `custom`) instead
  of ad-hoc conditionals.
- `AGENTS/` working documentation (analysis, architecture, specs, progress,
  notes) and this `CHANGELOG.md`.

### Changed
- `bot.py`: environment state now lives in the shared `Profile`; legacy
  `Bot` attributes are exposed as read-only `@property` views
  (`new_layer`, `color_button`, `color_button_okay`, `mspaint_mode`,
  `color_calibration_map`, `_canvas`, `_custom_colors`).
- `bot.py`: extracted the drawing pipeline core into `_encode_rows()`,
  `_emit_run()`, and `_merge_layers()`; `process()` is now I/O + scaling only,
  and `process_region()` reuses the same encoder.
- `bot.py`: app-specific input moved behind `Bot.painter` (`ScreenPainter`).
  `draw()` / `test_draw()` now call `painter.new_layer()`, `color_button()`,
  `color_button_okay()`, and `execute_stroke()` / `execute_test_stroke()`
  instead of inlining the click/modifier/stroke logic. Colour selection is
  delegated to the driver's `ColorSelectionChain`. Behaviour is unchanged
  (verified by the characterization tests).
- `ui/window.py`: creates/loads the shared `Profile`, saves `config.json` as
  preferences merged with `profile.to_config()`, and passes the shared Profile
  into `SetupWindow` so setup mutations need no merge-back.
- `.gitignore`: ignore `/AGENTS/`.
- `pyaint_profile.py`: added `target` (the selected recipe id) to the shared
  profile, `from_config`/`to_config`, and the preset `to_dict`/`from_dict`.
- `ui/setup.py`: the Setup window now only lists the tools the selected target
  recipe uses (e.g. skribbl shows just Palette and Canvas).
- `ui/window.py`: `_apply_recipe` now delegates to the pure helpers in
  `pyaint_targets` instead of inlining settings/option merging.
- `bot.py`: shrunk by moving `Palette` to `pyaint_palette.py`, then calibration
  (`pyaint_calibration.py`) and the cache (`pyaint_cache.py`) into mixins.
  `Bot` is now ~978 lines (from ~1475).
- Replaced 171 `print()` calls across `bot.py`, the extracted modules, `main.py`,
  `ui/window.py` and `ui/setup.py` with `pyaint_log` calls (identical default
  output; can be silenced with `PYAINT_LOG_LEVEL`).
- Housekeeping: fixed 16 bare `except:` clauses, removed dead code (the
  commented `RESOURCES`, the unused `Bot.options`, `_find_nearest_spectrum_color`)
  and unused imports; `ui/window.py` reads/writes config through
  `pyaint_config`.
- **Project restructured into the `pyaint/` package** (no behavior change):
  dropped the `pyaint_` module prefixes, moved `ui/` under `pyaint/ui/`, renamed
  `exceptions.py` → `pyaint/errors.py` and `utils.py` → `pyaint/utils.py`, and
  added `pyaint/__init__.py`, `pyaint/__main__.py` and `pyaint/paths.py`.
  Added `pyproject.toml` (metadata, deps, `pyaint` console script). Root
  `main.py` is now a launcher shim; `python main.py` and `python -m pyaint` both
  work, and imports are now `from pyaint.bot import Bot`.
- `bot.py`: added `capture_screen()`, `detect_target()`, and
  `apply_detection()` so a recipe's locators can populate the canvas/palette
  without manual teaching.

### Fixed
- `get_cache_filename()` no longer fails when the canvas is uninitialized; it
  returns `None` instead of raising.
- Auto-detection now finds skribbl's canvas and palette. The canvas is a **white
  800x600 (4:3)** region, so detection prefers `white_rect` filtered to 4:3 and
  only falls back to a `color_rect` (also 4:3) if the surface is filled — this
  stops a large dark *drawing* from being mistaken for the canvas. The page
  background is itself saturated, so the palette is found via `color_signature`
  over the real 2x13 swatch colours with `gap: 0` (dilation previously merged
  the palette into the white canvas panel).
- `Bot.draw()` now clears `self.drawing` on every termination path (the
  post-stroke path previously returned `'terminated'` but left `drawing` set).

### Removed
- Duplicated per-pixel run-length/layering logic between `process()` and
  `process_region()` (now shared).

## [0.0.0] - 2026-01-17

- Repository baseline at commit `9d1b5ef` on branch `rework`: Pyaint drawing
  automation engine (`bot.py`), Tkinter UI (`ui/window.py`, `ui/setup.py`),
  entry point (`main.py`), and tracked user documentation (`Docs/`, `README.md`).
