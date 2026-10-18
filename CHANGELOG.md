# Changelog

All notable changes to Pyaint are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses calendar versioning with a
[`YYYY.MINOR.PATCH`](https://calver.org/) scheme for releases.

> **Maintenance note:** add new entries under `[Unreleased]` as work happens.
> When releasing, move those entries under a new version heading with the date.

## [Unreleased]

## [2026.1.1] - 2026-10-18

### Changed
- Docs: remove stale references.
- README now points to the
  [`legacy` branch](https://github.com/Trev241/pyaint/tree/legacy) for the
  original Tk-based app, so people who prefer it can still find the
  pre-rewrite version.

## [2026.1.0] - 2026-10-17

### Fixed
- **Pyaint now stays per-monitor DPI aware, so it reflows after a display
  change.** `pyautogui` and `pyscreeze` call `SetProcessDPIAware()` when they
  are imported, which pins the whole process to *system* DPI awareness before
  Qt can ask for per-monitor v2. Windows then bitmap-stretches the window after
  a scaling or monitor change: the layout keeps the old widths (wrapped text and
  dead space), Qt never receives `WM_DPICHANGED`, and screen metrics can stay in
  the scale that was active when the process started. The package now claims
  `PER_MONITOR_AWARE_V2` from `pyaint/__init__.py`, before `pyautogui` can run
  its import-time call, so the window and the physical cursor/screenshot space
  follow the display automatically. Startup logs the claimed level and warns if
  an unusual import order pinned a lesser one. Regression tests:
  `test_pyaint_claims_per_monitor_dpi_before_pyautogui_loads`,
  `test_claim_is_idempotent`.
- **Manual teaching no longer inherits a previous display's scale.** Picks were
  built from Qt's logical global point and mapped through
  `QGuiApplication.primaryScreen()`; after changing which monitor is primary (or
  its scaling) with the app still open, that geometry could lag. The taught box
  then carried the old scale into every later mouse move, and no amount of
  re-teaching could fix it until a restart. Picks now store the physical cursor
  position (`pyautogui.position()` / `GetCursorPos`), which is the same space as
  the screenshot and the synthetic input. A pick outside the captured primary
  screen is rejected with a warning instead of becoming a silently bad box.
- **Section headings sit centred in their own hover/focus box.** The header's
  vertical insets were 12px above the title and 2px below, so the accent focus
  ring and hover tint looked bottom-heavy. Both insets are now 8px.
- **Long notices no longer spill out of their card.** The card was sized from
  `sizeHint()`, which measures the wrapped label at the *hint's* width; a
  message that needed a third line at the real 460px width ran past the bottom
  edge (the `"…" is not set up yet` warning was the usual offender). The label
  is now measured at the width the layout actually gives it, and the card grows
  to fit, shrinking back for short messages. A notice raised **before the
  window is laid out** (startup warnings) is now measured from the card's fixed
  width and placed from `MainWindow.showEvent`, so it no longer appears
  compressed in the top-left corner. Regression tests:
  `test_notice_grows_to_fit_a_long_message`,
  `test_notice_raised_before_show_lands_bottom_right`.

### Changed
- **Releases now use calendar versioning (`YYYY.MINOR.PATCH`).** This is
  `2026.1.0`, the first feature release of 2026. `pyproject.toml` reads the
  version from `pyaint.__version__`, so the package, wheel and frozen build
  agree; see `CONTRIBUTING.md` for the release steps.
- **Edge tracing is the default; Outline is retired from the rail.** The mode
  rail now offers Layered, Slotted and Edge tracing. The Outline planner, its
  settings and its tests are untouched, and the hidden state holder still knows
  the constant, but fresh profiles start in Edge tracing and old configs that
  selected Outline load as Edge tracing. README and FAQ updated.
- **Inspector sections share one content rail and read as headings.** Section
  titles, hints, bodies and diagnostic buttons now all start on the same 12px
  inset; collapsible headers use the same dark title type as plain sections and
  carry a painted chevron at the trailing edge. Nested groups (`Matching`,
  `Input`, Sketch's `Advanced settings`) add no second indent, body-level notes
  use the field-hint style instead of double-padding a section hint, and the
  diagnostic buttons are left-aligned instead of centred. The separate
  `Fine-tune` disclosure is gone: `Drawing` is itself the collapsible section,
  so the knobs are one clearly named group rather than a group under a second
  heading. Regression tests: `test_collapsible_section_toggles_from_its_header`,
  `test_section_insets_share_one_content_rail`.
- **Docs collapsed back to one README.** Deleted the `docs/` tree (index, API
  reference, configuration, architecture, releasing, troubleshooting) and the
  duplicate summaries that came with it. The README is now the hook + how-to +
  FAQ + a short architecture/tools map; `CONTRIBUTING.md` carries setup, tests,
  build, release and demo instructions; `targets/README.md` keeps the recipe
  schema. Nothing tracked links into `docs/` any more.
- **Setup is now a disclosure row, and notices are opaque.** The status chip
  became a **full-width `Setup` row** under the top bar: the chevron lives in
  the surface it reveals, the whole 44px row is the click target, and the panel
  opens from the row's own bottom edge as an **overlay** (it stops at the tool
  column), so revealing setup never moves the desk. Readiness inside the row is
  **status only** — a drawn check for done, a hollow ring for pending, no
  fills, no borders, nothing that reads as a button — and the panel carries one
  sentence naming the blocker plus `Find the canvas` / `Pick the regions`. The
  panel auto-opens while something is missing, but only until you touch the
  row; after that your state wins and a readiness refresh can no longer
  re-open it under the pointer.
- **Notices are opaque cards at the bottom-right.** The old translucent toast
  (`rgba(…, 0.10–0.16)`) let the artwork show through its own text; notices now
  use solid warm tints with a hairline, a severity edge and a real drop shadow,
  and they stack above the voice bar instead of covering the centre of the
  artwork. Errors still persist; info/success still auto-dismiss.
- **Elevation is for sheets only.** `paint_paper` no longer draws two hard
  offset copies of the shape (which the widget rect clipped into a square
  slab); the hero sheet gets a real stroked falloff, and only roles in
  `paper.SHADOW_ROLES` carry a shadow at all. Buttons and the Look strip are
  flat with a hairline, so a rounded control can no longer cast a
  square-cornered shadow.

- **Desk layout pass: status up top, floating notices, real gutters.** Readiness
  moved out of the bottom bar into a **collapsible setup panel** under the top
  bar, toggled by a **status chip at the top-right** (`Not set up` / `Partly set
  up` / `Ready · N colours`); it auto-opens while something is missing and folds
  away once ready, carrying the readiness steps and `Find the canvas` / `Pick
  the regions`. The voice bar is now just the guide note + `Start drawing`.
  Notices and the capture countdown are **floating, top-anchored toasts**
  instead of layout rows, so showing one moves nothing: info/success
  auto-dismiss (~4s), warnings later (~8s), errors persist, hovering holds and
  clicking dismisses. The countdown bar animates smoothly off a monotonic
  deadline instead of stepping. The image source is now a **single strip**
  (`Image · field · Load/Search · Source`), with the duplicated meta line moved
  onto the stage header and `← Results` inline. The desk has a consistent
  gutter (`MARGIN` / `GAP`); the sheet-into-column tuck is gone, so the column
  and hero sit apart like the reference mockup.
- **Paper on a desk — the subtle pass + desk/UX pass.** Paper is now confined
  to the hero artwork sheet at reduced amplitude; every other surface (column,
  mode highlight, Look strip, buttons, docked bar) is a plain rounded rect, and
  the dog-ear fold is gone. `PAPER_AMOUNT` (env `PYAINT_PAPER`, `0`–`1` or
  `off`) scales the gesture and doubles as an off switch; seeds are stable
  (`zlib.crc32` over `(role, seed_key)`, never Python's salted `hash()`), so a
  shape is identical across construction orders and runs. The action cluster
  moved out of the top bar into a **docked bottom bar** (guide note · readiness
  · `Ready · N colours` · `Find the canvas` / `Pick the regions` ·
  `Start drawing`), using the previously empty bottom band; the floating voice
  card and `Finish setup` are gone and the top bar is the wordmark + target.
  Setup verbs are now `Find` / `Pick`. The inspector was regrouped: colour
  matching lives in Advanced, the target-specific MS Paint toggle in
  Environment, `Redraw region` is promoted out of Diagnostics, Appearance is
  top-level, and `Reset all settings` sits alone at the bottom. The app starts
  empty instead of preloading a sample. Keyboard focus is visible again (the
  global `outline: none` is gone; custom-painted buttons and the segmented
  control draw a focus ring and support arrow keys). `pyaint/ui/paper.py` was
  rewritten; unused desk widgets (`LookFan`, `LookTiles`, `LookSelector`,
  `StraddleBar`, `BadgeDisc`, `_BrushMark`) were deleted. The hero shape is
  pinned by render snapshots in `tests/snapshots/`.
- **Guide note + image-field polish.** The docked guide note now describes the
  control under the pointer or keyboard (its tooltip), reverting to the active
  mode's note when nothing is hovered — the "voice" finally does what the
  design promised. The image field splits `Load` (a URL or path) from `Search`
  (plain words) by relabelling its button, and the `Source` picker is hidden
  while loading a URL/path. Sketch's preset is now named only once (the
  segmented control); the duplicate title/description pair is gone. The docked
  bar has a fixed height (long tooltips wrap and clip, they no longer resize the
  pane) and its voice mark is a plain accent dot.
- **Paper on a desk: the surface language.** Chrome is no longer made of
  rectangles. Every panel, card, chip, bar and the selected-mode highlight is
  an irregular sheet — jittered corners, each edge bowed a different amount, no
  two sides parallel — tossed, overlapping and tucked under one another. The
  largest normal rectangle (the artwork pane) becomes the hero sheet with a
  single dog-ear fold; unselected modes carry no surface at all, so four shapes
  never sit side by side; the tool column is one tall sheet with an opaque
  header band and hairline so the scrollbar and first row are never clipped
  under it. Surfaces lean, information does not: text, icons and inputs stay
  square. Shapes are a fixed, deterministic silhouette library, not runtime
  randomness. New `pyaint/ui/paper.py` (`paper_path`, `paint_paper`,
  `PaperSurface`, `PaperButton`); Qt stylesheets cannot paint a non-rectangle,
  so chrome is custom-painted while inputs keep their QSS. Edges bow inward or
  flat (never outward), so a sheet never puffs at its middle; jitter/bow/radius
  scale with the surface's short side, so a chip collapses toward a rounded
  rectangle (its text stays legible) while a hero sheet gets the full
  silhouette and stands out. `PaperSurface.content_rect()` derives the safe
  inner rectangle from the role, so padding is computed rather than guessed,
  and the desk stacking is declared once in `DESK_ORDER`. The Look control is
  now a single segmented sheet (`PaperSegmented`) with a selected fill clipped
  to the sheet's irregular edge and each preset's tagline moved to a tooltip;
  the shadow is a theme token (soft dark gets a black shadow); paper buttons
  carry extra padding so the jittered edge never crowds a label; the voice-bar
  badge is gone and the readiness steps use short labels; and the duplicate
  mode/Look readouts are gone. The selected-mode highlight is irregular with
  **sharp** corners, and hovering a mode reuses that same quad in a quiet tone
  rather than a different rounded rectangle. The voice card is an irregular
  sheet resting on the hero's bottom-right corner. The `Pyaint` wordmark, the
  `Customize` column heading, the mode kicker and the stage hint line are all
  gone, and the readiness steps are restyled to muted/accent text so they match
  the theme. Top bar keeps only paper-chip buttons; `Start drawing` /
  `Finish setup` are paper buttons. Reference
  renders are the real window (`build/render_paper.py` →
  `build/paper_light.png` / `build/paper_dark.png`). Presentation only.
- **UI conformance pass: one desk, one voice.** The settings pane and the
  mode rail became a single persistent left column (`Mode` families → `Look`
  tiles → collapsed `Fine-tune` → `Advanced` → the global `Environment`),
  with the canvas beside it and an isolated voice card resting on the artwork.
  This removes the old split where the mode lived on the left and its knobs on
  the right. The top bar carries the readiness steps and `Start drawing`; the
  voice card carries only the guide note. `Customize`
  is now a `Fine-tune` disclosure inside the column, so mode selection can
  never be hidden. The shape and type scales are centralized (`RADIUS_CARD`,
  `RADIUS_INPUT`, `TYPE_*`) and applied across every surface; the
  tracked-uppercase `SETTINGS` title and the 2px buttons/inputs are gone. The
  dual-readout sliders drop their pip meters (the `value · band` read stays)
  and their hint sentences move to the voice panel. `Look` is a segmented paper
  strip whose `Custom` tab appears only while the live values match no preset. The
  dark theme becomes **soft dark**: panes sit above the desk instead of below
  it, ink is off pure-white, and the preview sheet is theme-aware rather than
  hard-coded white. The desk also gets its overlap layer: the selected mode
  carries the only irregular mode highlight, and the canvas sheet **tucks
  under** the column: the
  canvas spans the full width, the column floats over its left edge, and the
  preview sheet's content is indented so nothing hides. The Find-image panel
  (the canvas source strip) loses its card border and becomes a plain strip on
  the desk, matching every other surface. The rule throughout is
  *overlap surfaces, never ink*: card and highlight surfaces lean, but every
  label stays horizontal. The voice card is one flat floating sheet resting on
  the hero artwork's bottom-right corner, jutting past its right and bottom
  edges; the `Customize` column is a regular rounded quad, while the selected
  mode keeps the irregular highlight. The readiness checklist is hidden
  while everything is ready (the header chip already carries the summary) and
  appears only when something needs fixing, next to `Finish setup`. Switching
  Source/Preview/Compare eases the pane in (a 180ms settle). UI smoke
  assertions updated for the new `Custom` tile semantics. Presentation only —
  no planner, detection, or drawing changes.

### Added
- **First run opens with a bundled sample.** When there is no remembered image,
  the source pane loads `assets/koala.png`, so a new user can press Start
  immediately instead of hunting for a picture first. The fallback is never
  copied into `last_image.png` (it is not the user's "last image"), a remembered
  image always wins, and the sample is bundled in `pyaint.spec` so the frozen
  exe has it too. Art by Ahmed Hossam via Unsplash (Unsplash License).
  `DEFAULT_SAMPLE` is blanked by the UI test fixture, with regression tests for
  the fallback and for remembered-image precedence.
- `icons.chevron` and `SetupRow` (accessible name/description, focus ring,
  Space/Enter, 120ms chevron rotation); `SheetCard` for QSS cards that need
  elevation; `paper.soft_shadow`.

- **"Studio Warm" look and an "easel" layout.** The UI moves off the VS Code
  palette to warm-paper / warm-charcoal surfaces with a single clay accent
  (`#B8542F` / `#E07856`, AA-verified), 13px sentence-case type, 8px shapes, and
  a brush-stroke app icon (`assets/pyaint.ico`, wired into the window and the
  frozen exe). The window is now a left single-choice **Mode** rail (radio dots
  grouped under the **Runs** / **Contours** families), a frameless canvas with
  the mode-aware **Look** selector and a **Customize** action cluster, and a
  settings pane that stays hidden until **Customize** is pressed. Pane controls
  show both the value and a band word (`12 px · Balanced`) with a pip meter.
- **Drawing "Look" presets** (Balanced / Smooth / Fast draft) for the fill and
  Outline modes, matching the existing SKETCH presets; the Look selector swaps
  to Cartoon/Realistic in Edge tracing. Looks set pacing only, never planner
  internals.
- **Sketch presets and a friendlier Sketch panel.** SKETCH now opens with two
  immutable looks — **Cartoon** (flat, cel-shaded art; every stroke kept) and
  **Realistic** (photos and painterly art; weak edges pruned to tone shading
  down) — chosen to match the image you loaded. Every edge-detection knob moved
  under a collapsed **Advanced settings** section with an on-screen hint.
  Changing any knob leaves the presets and shows a read-only **Custom** caption,
  so the built-ins stay identical on every machine. Preset data lives in
  `pyaint/ui/presets.py`.
- **Live drawing preview.** The preview pane gained a **Source / Preview**
  toggle. *Preview* plans and renders the current image exactly as it will be
  drawn — thin black line art for Outline/Sketch, palette-coloured fills for
  Slotted/Layered — without touching the screen. Planning runs off the GUI
  thread and is debounced while sliders move; the frame dims and shows a small
  spinner while it updates, and stale results are dropped with a generation
  counter. Stroke/cell counts show in the preview meta. Backed by the pure
  `pyaint/render.py` renderer and the `pyaint/ui/plan_tasks.py` worker.
- **New Sketch stroke mode with a selectable edge source.** A fourth
  processing mode (`sketch`) traces the image's edges into black polylines —
  no segmentation, no region merge and no drawing palette. `edge_source`
  chooses **Edge drawing** (`cv2.ximgproc.createEdgeDrawing`, which returns
  long connected polylines; the default, needs opencv-contrib) or **Canny**
  (auto-Otsu or manual thresholds, traced with a straightest-continuation
  walk). Both share the cleanup: gap join, polygon simplification, an optional
  **hue merge** that drops strokes whose two sides share a hue (so shading and
  tonal edges are not traced while real colour boundaries stay), a weak-edge
  pruning step (`sketch_gradient_keep`), and a minimum-stroke filter. Every
  parameter is exposed in the inspector, round-trips through `config.json`, and
  is part of the precompute cache key (`SKETCH_PIPELINE_VERSION`).
  `PYAINT_DEBUG_SKETCH=1` dumps the edge map and a red overlay.
- **opencv-contrib-python replaces opencv-python.** The Sketch mode's default
  Edge drawing source needs `cv2.ximgproc`; the extra is otherwise drop-in.
- **Outline segments with its own adaptive palette and merges on region
  means.** Outline draws only black, so the target's drawing palette was
  erasing real boundaries before tracing (on a sample image, 64 adaptive
  colours collapsed to 9 MS Paint swatches). The label-map cleaner now
  k-means-clusters the smoothed source into `OUTLINE_SEGMENTATION_COLORS` (48)
  Lab colours (`_adaptive_segmentation`), decoupled from the target palette.
  The soft-boundary merge now compares the two components' **mean colours**
  instead of the local step across their shared edge: the old local-step
  union-find chained through soft edges and fused distinct regions (face,
  clothes, arms, background) into one blob. Merging on means keeps a soft edge
  between two different colours while still collapsing a smooth gradient. The
  bilateral level mapping was gentled as well (level 5 was `sigma_colour` 90;
  level 2 is now the spec's `(7, 40, 7)` and the ceiling is 70), so
  `outline_smoothing` defaults to 2 and `outline_step_threshold` to 10.0 (a
  mean-Lab-distance). `OUTLINE_PIPELINE_VERSION` is part of the precompute cache
  key so an old cached plan is never replayed. `scripts/debug_outline.py`
  renders the per-stage images, a `<stage>_contours.png` overlay that draws the
  traced strokes over the debug-coloured regions (plus a `contours_sheet.png`),
  the removed-boundary overlay and a black line-art overlay for any image
  without launching the GUI.
- **Outline now cleans the label map before tracing, fixing stroke
  fragmentation and tonal clutter.** A new `plan_outline` pipeline
  (`INSTRUCTIONS.md`) runs at the source resolution: bilateral smooth →
  weighted-Lab quantize → soft-boundary merge → selective small-region merge
  (twice) → full contours → geometric dedupe → simplify → join → drop tiny
  strokes. The soft-boundary merge removes touching boundaries whose mean Lab
  step is below the new **Shading cleanup** threshold (default 4.0; 0 keeps
  every tonal boundary), so shading, gradients and soft shadows are not traced,
  while thin features (outlines, lashes) are protected. A boundary shared by
  two regions is only cut where a long stretch (≥ `MIN_DROP_RUN` points)
  overlaps an already-accepted stroke, so strokes stay long while double
  drawing is thinned to a single line. The same run keeps high-contrast
  pupils/eyebrows. New **Smoothing** (default 5) and **Join distance** sliders
  expose the bilateral strength and endpoint-join threshold, and the
  now-redundant *Despeckle anti-aliased edges* control was removed. Lab is
  computed with `cv2` on float RGB so `L` is on the 0–100 scale (matching
  `skimage.color.rgb2lab`) without adding a dependency. `outline_step_threshold`
  joins `outline_small_area`, `outline_tiny_area` and `outline_similar_color`
  as per-target settings in the precompute cache key. `PYAINT_DEBUG_LABELS=1`
  now dumps every stage (`*_quantized.png`, `*_soft_merged.png`,
  `*_final.png`), a removed-boundary overlay and a random-colour stroke view,
  and prints the new/removed boundary pixel counts.
- **Outline can double-paint shared edges.** The *Double-paint shared edges*
  checkbox (off by default) opts out of the new geometric dedupe, so every
  region paints its full border instead of long duplicate stretches being
  thinned to one clean line. Stored per target and part of the precompute cache
  key.

### Changed
- **Preview is framed to its content.** The live preview and Compare no longer
  show baked-in canvas whitespace: the frame is cropped to the fitted source
  rectangle (fill modes) or the strokes' bounds (line modes), so Compare shows
  matching framing and the preview is no longer letterboxed inside its pane.
- **Friendly-guide copy**: *Find canvas*, *Set up manually*, *Finish setup*,
  *Save the plan for next time*, *Try 20 strokes*, *Check brush size*, *Reset
  all settings*, *Select area*, *Draw area*, and softer empty states.
- **UI smoke tests are an opt-in group.** `pytest` runs the fast headless suite
  (~7s); `pytest -m ui` runs the Qt widget tests (~23s). Closing a window now
  destroys it, which fixes the module-state stall that used to hang the run.
- **Sketch weak-edge pruning is one slider, not a toggle.** The redundant
  **Drop weak edges** checkbox is gone; **Keep strongest %** (10–100, default
  100 = keep every stroke) now controls gradient pruning on its own. The
  overloaded `sketch_gradient_gate` float is replaced by `sketch_gradient_keep`
  (a fraction, `1.0` = keep all), and `SKETCH_PIPELINE_VERSION` bumped so cached
  sketches recompute. Unreleased legacy configs are not migrated: the stale key
  is dropped on load.
- **The preview now offers Source / Preview / Compare.** *Compare* shows the
  loaded image and the planned result side by side as a before/after, so the
  live preview is obvious instead of hidden behind a toggle. The view choice
  persists in `config.json` (`preview_view` now also accepts `"split"`), and
  *Compare* stays disabled until a source image is loaded.
- **Simpler inspector.** Removed the **App behaviour** section: the
  New Layer / Color Button / Okay toggles duplicated Setup and recipe defaults,
  so teach and enable tools in Setup instead. The now-unused `ToolControls`
  widget and its handlers were deleted. The target-specific
  **MS Paint double-click** checkbox moved to the (now compact) Options section,
  where it is hidden unless the chosen recipe supports it.
- **The Options section is just Colour matching.** *Ignore white pixels* and
  *Ignore transparent pixels* are now always on (the latter was already the
  safe default), and *Skip first color* is recipe-driven with no UI toggle.
  Legacy `ignore_white_pixels` / `ignore_transparent_pixels` config keys are
  still read but the planner always receives both ignore flags; a target can
  still set `skip_first_color` in its recipe.

### Fixed
- **Outline no longer traces a shared edge twice.** When two colour regions
  meet, `cv2.findContours` returns the shared boundary in *both* region masks,
  so the edge was drawn once per side. The outline planner now labels every
  region, then drops the boundary cells that touch a lower-numbered region,
  emitting each shared curve exactly once (splitting a contour into open runs
  where it is dropped).
- **The standalone `.exe` no longer crashes on launch.** The Outline planner
  needs OpenCV (`cv2`), but the PyInstaller spec excluded it and it was never a
  declared dependency — so the frozen build died with `ModuleNotFoundError: No
  module named 'cv2'` before the window opened (now that Outline is the
  default). OpenCV is now listed in `requirements.txt`/`pyproject.toml` and
  bundled by `pyaint.spec` (numpy comes with it).
- **Manually teaching a palette (or canvas) now actually saves the clicks.**
  The point picker hid its modal overlay before calling `accept()`; hiding a
  modal `QDialog` exits its `exec()` loop immediately with `Rejected`, so
  `pick_points` returned `None` and Setup silently discarded the two taught
  corners — the status stayed "Not set" and the preview stayed blank. The
  overlay now accepts on the final click (the clean screenshot is already
  taken before it appears).
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
- **Outline region ids are ordered by brightness, not first appearance.** Dark
  colours get the lower ids and therefore own (trace) the edges they share with
  a lighter fill, so a dark outline is drawn rather than the fill side of it.
- **Outline now quantises at source resolution.** The shared quantiser samples
  a handful of pixels per output cell, which is fine for the run-based modes but
  can capture a thin anti-aliased outline in one cell and miss it in the next,
  so its contour fragmented into many tiny strokes. Outline now requests
  `source_quality=True`: the sample grid is scaled to the source resolution so
  every source pixel votes and thin edges are resolved consistently instead of
  being approximated into stray palette colours. The other modes keep the
  cheaper budgeted sampling.
- **Outline is now the default stroke mode.** New installs (and configs with no
  saved `draw_mode`) start in Outline instead of Layered. Existing configs keep
  whichever mode they had saved.
- **The bottom status bar is gone.** Its progress bar was unreadable while a
  draw is running (the window is minimized), and the floating click-through
  overlay already shows the same `strokes done / total` figure with an ETA.
  Drawing progress now lives only on that overlay; status text is still
  written to the log. The unused `QStatusBar` / `#StatusText` styles were
  removed too.
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
- **Pyaint remembers the last image you selected.** The loaded image is copied
  next to `config.json` as `last_image.png` and restored on the next launch, so
  a gallery pick or an upload no longer has to be reselected. Reset clears it.
- **Outline has an opt-in *Despeckle anti-aliased edges* cleanup.** It runs a
  morphological open/close on each colour's mask before contour tracing,
  removing 1px anti-aliasing specks and bridging 1px breaks so they do not each
  become a tiny stroke. Off by default because a 3x3 kernel also erases genuine
  1px detail; the checkbox lives in the Outline controls and is cached.
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
- The old colour-wheel demo image (`assets/sample.png`). It was only ever a
  README illustration and a sketch-mode fixture; the bundled koala replaces it
  in both roles.
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
