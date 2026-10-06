# Changelog

All notable changes to Pyaint are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project aims to follow [Semantic Versioning](https://semver.org/).

> **Maintenance note:** add new entries under `[Unreleased]` as work happens.
> When releasing, move those entries under a new version heading with the date.
> Internal agent notes live in the gitignored `AGENTS/` folder — see
> [`AGENTS/README.md`](AGENTS/README.md).

## [Unreleased]

### Fixed
- **Manually teaching the palette now samples the right pixels.** The point
  picker grabbed its screenshot *after* hiding its translucent black veil, so
  the veil could still be composited into the shot — the palette preview came
  out dark/blank and the sampled colours were wrong. The picker now grabs a
  clean full-screen image before the overlay appears, and Setup refuses to
  sample a fresh screenshot (which would show its own dialog) if that capture
  failed.
- **Auto-detect no longer wipes a palette or canvas you taught by hand.** A
  failed detection used to clear an expected-but-missing region, so running
  Auto-detect on a target whose palette it couldn't find silently erased the
  manually taught palette (leaving status unset and the preview blank). Regions
  the recipe attempts but does not find are now left untouched; the app reports
  that the taught region was kept so the result is never mistaken for a silent
  success or a lost setup. Callers can still opt into the destructive behaviour
  with `apply_detection(..., clear_missing=True)`.
- **MS Paint palette detection works at any display scaling.** The palette
  locator searched a hard-coded absolute-pixel region authored for a 100%
  display, so on a 125%/150% screen (where the DWM frame is still measured in
  physical pixels) it cropped the wrong part of the ribbon and found nothing.
  Window-relative regions now scale by the window's DPI factor, and the swatch
  merge kernel (`gap`) scales with them, so the exact-colour signature still
  spans the whole grid. Verified on Windows 11 Paint at 125% scaling, where the
  palette is now found as a full 2x10 grid.
- **A failed palette sample is no longer reported as configured.** Setup marks
  the palette as set only after it actually samples the colours, refuses a
  zero-area box, and surfaces the reason in a dialog instead of silently
  logging it. The picker also makes its own windows fully transparent before
  grabbing the teaching screenshot, so the Windows minimize animation can't
  leak pyaint into the shot.
- **The captured region preview now persists and gives clear feedback.** The
  annotated canvas/palette crop was only kept in memory, so it went blank as
  soon as Setup was closed and reopened. Previews are now rendered and saved
  under `previews/`, restored on reopen, and shown with a caption and a
  colour-count/grid summary ("✓ 20 colours sampled (2 × 10).").
- **Auto-detect previews now carry into Setup.** Reviewing a detection and
  choosing Use / Teach manually left the Setup preview panes empty because the
  detection screenshot was discarded. The detected canvas and palette are now
  rendered through the same renderer as manual teaching, so Setup opens with
  the exact picture that was just approved.
- **The preview pane's placeholder no longer duplicates itself.** The canvas
  pane printed the same "no preview" sentence in both the image area and the
  feedback label; the image area now carries a single short placeholder and the
  label reports only the status. A 10px margin keeps the placeholder and scaled
  image clear of the frame.
- **Reset config now resets immediately.** The old button only deleted
  `config.json` and told the user to restart. It now also clears the cache and
  preview folders and rebuilds the live profile, drawing settings, target list,
  and preferences in place, so the app is back to defaults the moment the
  dialog is dismissed.
- **Strokes no longer land on the canvas border.** The planner now insets the
  taught canvas by `CANVAS_PADDING` (4px) before fitting, so edge strokes stay
  inside the drawable area. Targets like skribbl can register a click a hair
  outside the canvas as a miss, which dropped those strokes.
- **Openverse searches no longer fail with HTTP 401.** Openverse rejects
  anonymous requests above 20 results per page (`page_size may not exceed 20
  for anonymous requests`). The gallery reused the Commons-oriented default of
  30, so every Openverse search returned 401. The Openverse provider now caps
  its page size at 20, and `_fetch_json` surfaces the API's own explanation
  instead of a bare "HTTP Error 401: Unauthorized".
- **Images dragged from a browser now load.** Drop handling only accepted
  local files (`QUrl.isLocalFile()`), so a drag from a Google/Bing image result —
  which arrives as an `http(s)` URL, an HTML `<img>`, or a `data:` URI — was
  silently ignored. The window and preview now recognise remote URLs, `data:`
  URIs, and raw image bytes, unwrap search-engine `imgurl` redirects, and route
  them through the existing download path.
- **Manual teaching no longer strands the app.** The point picker
  (`pyaint/ui/capture.py`) hid the parent dialog to grab a clean palette
  screenshot, but hiding a `QDialog` ends its `exec()` loop — Setup dropped out
  of its modal loop mid-teach and the window became unresponsive. The picker now
  minimizes the window chain and restores it, and finishes the screenshot on a
  clean event-loop turn.
- **The drawing progress overlay can't block the target app.** It is
  click-through again (`Qt.WindowTransparentForInput`), so it no longer
  intercepts the bot's clicks (e.g. on a palette behind the card); Pause/Stop are
  keyboard-only because the bot owns the mouse.
- **Wheel-scrolling the settings panel** no longer changes the slider,
  combobox, or spinbox under the cursor.
- **Checkboxes show a check mark** instead of an unlabelled filled square.
- **The detection review overlay is focusable**, so *Teach manually…* opens
  Setup correctly, and Setup normalizes a minimized/background window before it
  opens.
- **Taught geometry survives restart, so auto-detect is no longer needed every
  launch.** The palette was restored by re-screenshotting the saved palette box,
  which usually failed (the target app was closed, moved, or covered) and came
  back as a one-colour palette. Startup now rebuilds the palette offline from the
  saved `Palette.color_coords`, falling back to sampling only when no
  coordinates exist.
- **Closing the window flushes pending settings** (`_save_config()` in
  `closeEvent`), so the last edits are persisted even if no slot saved them
  eagerly.

### Changed
- **The preview is now a framed card.** The image sits on a bordered
  `#PreviewStage` that mirrors the source header above it, with a recessed
  image surface and a small header showing the loaded dimensions. This gives
  light or transparent images a visible boundary instead of floating on the
  panel background.
- **Stroke-mode controls now match the selected method.** The inspector shows
  only the pacing controls that apply to the chosen mode: Slotted and Layered
  expose the run settings (time per stroke / pause after big moves), while
  **Outline (experimental)** exposes the continuous-stroke knobs from the
  human-strokes prototype — stroke speed, move-event interval, and pause
  between strokes — alongside a warning banner marking it experimental. Detail
  and trigger distance stay shared because every mode uses them.
- **Removed the stale Stroke distance slider.** The outline planner has emitted
  one polyline per contour since the human-strokes rework, so the slider no
  longer changed anything. It is gone from Stroke mode, per-target snapshots,
  and `config.json`; `Bot.stroke_distance` remains only for API/cache
  compatibility. The unused `#PreviewStage` / `#StageHeader` styles are now
  actually used by the preview card.
- **Artifacts are removed at the source, not patched up in the planner.**
  Image fitting used nearest-neighbour point sampling, so a single
  compression/anti-aliasing pixel could become a stray cell and the LAYERED,
  SLOTTED, and OUTLINE modes then painted/outlined it as a fragment. Fitting now
  supersamples each output cell and takes the **modal palette colour**
  (`planner.quantize_image`), which outvotes isolated noise and never invents
  blend colours. It uses numpy (new dependency) for the vectorised CIEDE2000
  matching and falls back to the old single-sample path if numpy is unavailable.
- **The Image panel header is now a single tidy card.** The title and search
  source share one line (source right-aligned), the source field and Load
  button share the next, and the resolution/source line sits quietly beneath.
  New `#ImageHeader`, `#ImageTitle`, `#SourceLabel`, `#ImageMeta`,
  `#SearchField`, and `#LoadButton` styles keep the spacing and alignment
  consistent across the dark and light themes.
- **Image source controls and the preview now live together.** The single-tab
  "Image" tab is gone (a leftover from the removed Detection tab). The preview
  is a plain panel whose header owns the URL/path/search field, browse, and
  Load, and the right-hand inspector keeps only the processing settings. The
  image search opens a selectable results grid in the same panel.
- **Detection review is now an on-screen overlay, not a tab.** Auto-detect keeps
  the window minimized and spotlights the detected canvas/palette on the live
  screen with palette cell-centre dots, plus a card offering **Use these
  regions / Try again / Teach manually… / Not now**. Leaving it makes no
  changes.
- **Settings inspector polish:** inputs and buttons no longer hug the panel edge,
  and the readiness checklist flags missing steps in warning colour with a
  tinted strip; the notice banner is more prominent (severity background and
  icon).
- **Image panel: one submit, not two.** `Load` and `Open file…` were peer
  buttons beside a generic URL/path field, so an empty field made both open the
  file dialog. The file picker is now a folder action *inside* the field (and
  mirrors the chosen path back into it), `Load` is the only submit button
  (disabled until the field has text), and an empty submit shows a hint instead
  of silently opening a dialog.
- **Modern flat scrollbars** replace the native Windows scrollbar.
- **Pause/Stop are keyboard-only:** the overlay buttons were unreachable while
  the bot controlled the mouse, so the overlay is click-through and shows the
  `ESC`/pause hints instead.
- **Main window is now a hub, not a toolbox:** the activity rail and the
  Setup/Image/Draw sidebar are gone. The image preview is the hero, settings
  live in a single right-hand inspector, and one always-visible top bar holds
  the target switcher. This makes the common "same target, new image" loop
  one-click instead of a march through panels.
- **Visible, seamless target switching:** the top bar always shows the current
  target; switching applies the recipe's defaults and **remembers each
  target's canvas/palette** (`Profile.snapshot_environment` /
  `apply_environment`, stored under `environments` in `config.json`). Switching
  back restores the previously taught geometry instantly; an unconfigured
  target offers Auto-detect / Set up in place.
- **Persistent severity-aware banner** (`NoticeBanner`) for the things a user
  must not miss: not-ready checklists, draw failures, and switch results.
  Replaces the transient status-bar messages and most blocking `QMessageBox`
  warnings.
- **No more silent waits or silent failures:** the pre-draw `time.sleep(3)` (and
  the test-draw/region-redraw equivalents) is now a visible countdown in the
  floating overlay ("Switch to MS Paint — drawing starts in 3…"), and worker
  errors are surfaced as a red banner when the window restores instead of
  vanishing with the overlay.
- **Start is always clickable** and runs a pre-flight check that names what is
  missing (no image / canvas / palette / one-colour palette) with a fix action,
  instead of a greyed-out button with no explanation.
- **Calibration aids demoted:** Prepare & cache, Test draw, Brush test, and the
  region redraw moved into a collapsible **Diagnostics** section in the
  inspector, leaving Start drawing as the single primary action.

### Added
- **A Clear button in the Setup window.** Each tool's row now has a Clear
  action that forgets the taught position (and its saved preview) without
  closing the dialog, so a wrong capture can be undone and retaught in place.
- **Openverse as a second image source, with a Source selector.** Online image
  search now supports Openverse (`api.openverse.org`, no API key) alongside
  Wikimedia Commons, and defaults to Openverse for its much broader coverage
  (CC-licensed Flickr, museum, and stock images). A **Search source** dropdown
  in the Image header switches providers, the choice persists as
  `image_search_provider` in `config.json`, and changing it re-runs the current
  query. The "no results" message now names the source and suggests switching.
- **Drawing settings are per target.** Each target remembers its own timing,
  detail, jump, and option flags under `drawing_by_target` in `config.json`, so
  a fast MS Paint tune no longer leaks into skribbl (which drops fast synthetic
  input). Switching targets saves the current values and restores that target's;
  a target with none uses its recipe defaults. The skribbl recipe defaults were
  set to the slower, safer timing (`delay` 0.05 s, `jump_delay` 0.5 s, matching
  the tuned `config.json`).
- **Search the web from the Image field.** When the field is neither a URL nor
  a file path, it opens a Pinterest-style results gallery: a masonry grid of
  thumbnails that pages in more results as you scroll. Click a tile (or press
  Enter twice) to commit it to the preview; a **← Results** button returns to the
  grid. Results come from the selected source — Openverse (default) or
  Wikimedia Commons, both keyless — in relevance order with no drawing/photo
  bias, and the chosen image shows its title/source under the preview. Path-shaped input still reports "file not found" instead of
  searching.
- **Transparent PNG backgrounds are no longer painted black.** The pipeline
  converted images to RGBA but ignored alpha, so fully transparent pixels
  (usually RGB `0,0,0`) matched the darkest swatch. A new `IGNORE_TRANSPARENT`
  flag — **Options → Ignore transparent pixels**, on by default — skips pixels
  whose alpha is below 128. In Layered mode a transparent run acts as an
  absolute span breaker, so merged strokes can't bridge across a transparent
  gap and paint it.
- **Perceptual colour matching (CIEDE2000), on by default.** A new
  **Options → Colour matching** choice maps each pixel to the visually closest
  swatch using CIELAB ΔE00 instead of squared RGB distance, which fixes visibly
  wrong picks for near-neutral colours. The legacy squared-RGB metric is still
  selectable (`color_metric: "rgb"`), and the metric is part of the cache key so
  the two methods never share cached stroke maps.
- **Drag-and-drop onto the preview:** `ImagePreview` accepts image files dropped
  on it (highlighting its frame while a valid file is hovered) and emits
  `fileDropped`; the preview shows a persistent "drag an image here" hint and
  drops are routed through the same local-path loader as the file picker.
- `DetectionOverlay` (`pyaint/ui/overlay.py`): a full-screen review of an
  auto-detection result with canvas/palette spotlights, palette cell-centre
  dots, and confirm/retry/teach/dismiss actions. `CheckBox`
  (`pyaint/ui/widgets.py`): a `QCheckBox` that draws a real check mark over the
  accent fill.
- `NoticeBanner` widget (`pyaint/ui/widgets.py`) and per-target environment
  snapshots in `Profile` (`pyaint/profile.py`). The floating overlay gained
  `show_message` / `show_error`.
- **Floating progress overlay** (`pyaint/ui/overlay.py`): a click-through,
  always-on-top card shown during drawing/region-redraw with the stroke count,
  ETA, a progress bar, and ESC/pause hints. `MainWindow` shows it around long
  tasks and hides it when they finish.
- **Per-tool controls in the main panel** (`ToolControls` in
  `pyaint/ui/widgets.py`): New Layer, Color Button, and Color Button Okay now
  expose enable, Ctrl/Alt/Shift modifiers, and delay — matching what Setup
  teaches. The enable/modifier controls stay disabled until the tool is
  configured.
- **Palette cell-centre overlay in the auto-detect preview** (`pyaint/annotate.py`):
  the detection preview now draws a white dot at every palette cell centre, in
  addition to the canvas/palette outlines, so the user can confirm colours will
  be sampled from the middle of each swatch before applying. Pure over PIL and
  unit-tested (`tests/test_annotate.py`).
- **Theme system (dark / light / auto):** `pyaint/ui/theme.py` now ships VS
  Code "Dark Modern" and "Light Modern" token sets, an `auto` mode that follows
  the OS colour scheme (`QGuiApplication.styleHints().colorScheme()`), and a
  Settings → Appearance selector. The choice persists as `theme` in
  `config.json`, and icons/stylesheet re-apply on change (including when the OS
  scheme changes while in `auto`).
- **PySide6 desktop UI (VS Code-inspired):** replaced the Tk interface with a
  Qt UI. New modules under `pyaint/ui/`: `main_window.py` (activity rail,
  sidebar panels, toolbar, status/progress), `setup_dialog.py` (manual tool
  teaching), `capture.py` (cross-platform click-capture overlay), `theme.py`
  (VS Code "Dark Modern" tokens + stylesheet), `icons.py` (QPainter icons),
  and `widgets.py` (reusable controls). Added `tests/test_ui_smoke.py`.
- **Phase 4 — distribution:**
  - `pyaint.spec` + `scripts/build_exe.py`: a PyInstaller build producing a
    standalone `dist/pyaint.exe` (user data stored next to the executable).
  - `pyproject.toml`: classifiers, keywords, project URLs, and `[build]` /
    `[dev]` optional dependency groups.
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
  - MS Paint recipe tuned against a real Windows 11 Paint screenshot: canvas
    via the new border-aware `center_rect` locator, palette via `color_signature`
    over the exact 10x2 swatch colours inside a `region`.
  - New `center_rect` locator and universal `region` support for all locators;
    `tests/test_validation.py` plus inheritance/locator-registry/region tests.
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
- **Clearer drawing controls:** "Delay between strokes" → **Time per stroke**
  (it's the time each stroke takes, not a gap between strokes); the "Prepare &
  cache" tooltip no longer claims Start becomes instant; "Skip first color"
  explains when it's useful; the **trigger distance** moved next to its matching
  "Pause after big moves" slider; and the MS Paint double-click delay is labelled.
- **App behaviour is easier to understand:** the optional New Layer / Color
  Button / Color Button Okay controls are now hidden when the selected target
  recipe doesn't use them, and an untaught tool shows "Not configured — teach
  it in Setup to enable." instead of a bare greyed checkbox. MS Paint
  double-click is hidden for targets that don't support it.
- **Onboarding & navigation pass:**
  - **Readiness strip** above the toolbar (Target › Canvas & palette › Image ›
    Draw) with ✓/○ state; **Start** is enabled only when the canvas/palette and
    an image are ready.
  - **Blank-canvas requirement surfaced** in the auto-detect countdown banner,
    the detection empty-state, the Setup panel note, and the docs.
  - **Sidebar regrouped by task:** Setup (target + detect/teach) · Image · Draw
    (speed & quality, drawing, options, app behaviour), with appearance/input/
    files tucked into a collapsible **Advanced** section.
  - **Plain-language labels** (Quality/Fast, Detail, Pause after big moves,
    Prepare & cache, Brush test) with tooltips; "Teach manually…" replaces the
    ambiguous "Setup…".
  - **Detection results shown as a checklist** (✓/✗ per region).
  - **Setup shows a palette preview** with a dot at every sampled swatch centre
    (`annotate.annotate_palette`), so manual teaching can be verified.
- **Auto-detect countdown:** the small status-bar hint was replaced with a
  large **in-window countdown banner** (`pyaint/ui/countdown.py`) that clearly
  warns the screen will be captured and the window minimized. It is non-modal —
  it never steals focus or floats over the target app — offers **Capture now**
  / **Cancel**, and auto-proceeds after a 4-second countdown. The window only
  minimizes after confirmation, and cancelling aborts cleanly.
- `Palette` is a plain evenly-divided grid again; `Bot.settings` is
  `[delay, pixel_size, jump_delay]`. `config.py` drops legacy environment keys
  (`Custom Colors`, `color_preview_spot`, `color_selection`) on load.
- **Auto-detect UX:** the annotated detection now opens in its own **Detection**
  tab next to the persistent **Image** tab, with in-tab **Apply / Retry /
  Cancel**. The source image is never replaced. The modal confirmation dialogs
  and the pre-detect message box are gone — the 3-second countdown now shows in
  the status bar, keeping the whole flow in-window. Tabs use VS Code-style
  editor-tab styling from `theme.py`.
- **Palette sampling robustness:** `Palette` now samples the median of a small
  (3×3 where cells are large enough) neighbourhood instead of a single pixel,
  making colour reads robust to anti-aliased borders/gaps. `utils.grid_centers()`
  centralises the cell-centre maths shared by sampling and the preview overlay.
- **Dropped the manual/precision palette-centering workflow.** It solved a
  loose-box problem that auto-detection already solves, at a high usability
  cost. The engine still accepts `valid_positions`/`manual_centers` for config
  compatibility, but there is no UI for centre calibration; the visible preview
  overlay replaces it.
- **PySide6 UI:**
  - `pyaint/bot.py` no longer imports `tkinter` or creates/manages progress
    overlays. It reports progress through `progress_callback`, removing the
    worker-thread Tk access that was a latent GUI-crash source.
  - `pyaint/__main__.py` now launches the PySide6 window; `PySide6>=6.5` was
    added to the dependencies.
  - User docs describe the Qt UI and its module layout.
- **Phase 4 — distribution & docs:**
  - Rewrote `README.md` as a front door: demo videos, supported-apps table,
    pip/source quick starts, a skribbl-focused 60-second quickstart, FAQ, and
    an intended-use disclaimer.
  - Refreshed the user docs (`Docs/README.md`, `Docs/api.md`,
    `Docs/architecture.md`) to match the current `pyaint/` package, and fixed
    stale launch commands and paths in the other guides.
  - `pyaint/paths.py` now resolves `PROJECT_ROOT` to the executable directory
    when frozen, so `config.json`, `cache/`, and `targets/` persist across runs
    of the packaged `.exe`.
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
- **Misleading stroke-mode labels.** The modes were labelled "Quality" /
  "Fast", but the difference is stroke count: **Layered merges runs** (~23%
  fewer strokes on a sample image, so it *draws faster* and has smoother joins),
  while **Slotted** draws every run exactly (no overdraw, more strokes). They are
  now labelled **Layered (fewer strokes)** / **Slotted (exact runs)** with
  accurate tooltips, and the section is "Stroke mode".
- **Pause/Stop were enabled for tasks that can't be interrupted** (Prepare &
  cache, Brush test, image download); they now enable only for draw-like tasks.
- Docs corrected: "Pre-compute … start instantly" overstated it (it skips
  processing, not drawing), the "never draws in the wrong place" claim was
  softened, and stale "Pixel Size"/"Delay" names were updated.
- **Icons rendered as tiny marks or looked missing** (`play`, `zap`, the
  download arrow, the refresh arrow, the trash handle): the shared `_poly()`
  helper did not scale its normalised coordinates by the icon size.
- **Pixelated icons on scaled displays**: icons are now rendered at the
  display's device-pixel-ratio and cached per-DPR, so they stay crisp at 125% /
  150% scaling.
- **Drawing a whole image in one colour (a filled square)**: the palette was
  re-screenshotted *after* pyaint was brought back in front, so every swatch
  sampled pyaint's own UI and the palette collapsed to a single colour. Palette
  sampling now uses the screenshot the detection (or corner-click) was captured
  on: `Palette(..., image=...)` samples a provided full-screen image,
  `Bot.init_palette`/`apply_detection` pass it through, the auto-detect flow
  keeps its capture, and manual Setup grabs a screenshot the instant the pick
  overlay closes (with pyaint hidden). A warning is shown if a palette resolves
  to a single colour, so it can't silently draw a solid square.
- **Pre-compute (and drawing) could crash with `IndexError: list index out of
  range`** when the draw mode came from `config.json`: `_encode_rows`/
  `_emit_run` compared the mode with `is` instead of `==`, so a JSON-loaded mode
  string was not recognised and the layered row tables were never built. All
  mode comparisons now use `==`, with a regression test.
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
- **Custom-colour capability retired.** The long-standing colour-dialog path
  (built for the Windows 10 Paint "Edit Colors" dialog) is gone: deleted
  `pyaint/calibration.py` (`calibrate_custom_colors`,
  `get_calibrated_color_position`, save/load), the dead `_scan_spectrum` /
  `_spectrum_map` screen scan, `ScreenPainter.enter_rgb_keyboard`, and the
  calibrated/keyboard colour strategies. Colours now come only from the sampled
  palette.
  - Also removed the `Custom Colors` and `color_preview_spot` tools, the
    `color_selection` field/strategy, `USE_CUSTOM_COLORS`, the `precision`
    setting (it only fed custom-colour quantisation), the GIMP recipe
    (colour-dialog only), and the unused `Capabilities` scaffold.
- Deleted the superseded Tk UI (`pyaint/ui/window.py`, `pyaint/ui/setup.py`,
  ~3.4k lines) and the now-unused `keyboard` dependency.
- Removed other dead code: `Bot.config_file`, `Bot.progress`, the
  `_click_swatch`/`_enter_rgb_keyboard` wrappers,
  `Profile.is_ready`/`to_dict`/`from_dict`, `RecipeRegistry.ids`,
  `BUILTIN_RECIPES`, `recipe_is_valid`, `theme.THEMES`/`mono_font`,
  `CorruptConfigError`, `NoCustomColorsError`, and `Palette`'s unused
  `valid_positions`/`manual_centers` support.
- Duplicated per-pixel run-length/layering logic between `process()` and
  `process_region()` (now shared).
- Deleted the stale `Docs/tutorial.md` and `Docs/usage-guide.md`; rewrote
  `README.md`, `Docs/README.md`, `Docs/api.md`, `Docs/architecture.md`,
  `Docs/configuration.md`, and `Docs/troubleshooting.md` for the palette-only
  design.

## [0.0.0] - 2026-01-17

- Repository baseline at commit `9d1b5ef` on branch `rework`: Pyaint drawing
  automation engine (`bot.py`), Tkinter UI (`ui/window.py`, `ui/setup.py`),
  entry point (`main.py`), and tracked user documentation (`Docs/`, `README.md`).
