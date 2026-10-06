# Prototype: human-shaped continuous strokes

Branch: `prototype/human-strokes`

## Why

The bot used to emit one `mouseDown`/`mouseUp` per contour edge, each with a
burst of moves and a full `delay` sleep. Browser targets such as skribbl.io are
built for the input shape a human produces: **one button-down, a continuous
stream of moves at roughly display refresh, one button-up**. This prototype
emits that shape instead.

## Fix: MS Paint only drew a dot

`pyautogui.moveTo` uses `SetCursorPos` on Windows. MS Paint (and other GDI
apps) do **not** treat those moves as a drag: they see the button-down and
button-up but not the motion between them. The old per-edge code appeared to
work because each stroke started and ended at different points, so Paint drew
the chord. `execute_path` closes each contour, so the final `mouseUp` landed on
the `mouseDown` point, and Paint rendered a single dot.

`ScreenPainter._drag_move()` now sends a real
`mouse_event(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, ...)` while the button is
held, so the app receives `WM_MOUSEMOVE` with the button bit set and follows
the path. It falls back to `pyautogui.moveTo` off Windows. `execute_stroke`
also routes its segment moves through `_drag_move` for the same reason.

## What changed

- `pyaint/planner.py`
  - Strokes are now `List[Point]` (`Stroke`); `Cmap = {colour: [Stroke, ...]}`.
  - `plan_rows` emits 2-point strokes (runs), unchanged behaviour.
  - `_outline` emits **one closed polyline per contour** (no per-edge
    splitting, no dead boundary/segment code).
  - `stroke_distance` is retained for API/cache compatibility but ignored.
- `pyaint/painter.py`
  - New `ScreenPainter.execute_path(points, speed, frame_interval, settle)`:
    one drag per polyline, paced to at most one `moveTo` per `frame_interval`,
    always visiting every vertex so corners are never skipped.
  - `execute_stroke` is kept for `simple_test_draw` / legacy runs.
- `pyaint/bot.py`
  - New knobs: `human_strokes` (default `True`), `stroke_speed` (1500 px/s),
    `frame_interval` (1/60 s), `travel_delay` (0.05 s).
  - `draw()` replays multi-point strokes through `execute_path`; 2-point runs
    use it only when `human_strokes` is on.
  - `_estimate_drawing_time_seconds()` uses the path model when human strokes
    or polylines are present.
- `pyaint/utils.py`
  - New `estimate_path_seconds(cmap, speed, frame_interval, travel_delay,
    jump_threshold)`.

## Tuning

| knob | meaning | effect |
|------|---------|--------|
| `stroke_speed` | cursor px/s | faster = shorter total time, larger server load |
| `frame_interval` | seconds between `moveTo` events | larger = safer/slower, smaller = higher event rate |
| `travel_delay` | pause when jumping between strokes | replaces `jump_delay` for path strokes |
| `human_strokes` | `False` reverts 2-point runs to `execute_stroke` | A/B comparison for slotted/layered |

## A/B comparison

```python
bot.human_strokes = True
human = bot._estimate_drawing_time_seconds(cmap)
bot.human_strokes = False
legacy = bot._estimate_drawing_time_seconds(cmap)
```

(Sample numbers from the analysis: outline plans ~40% faster at 1500 px/s and
1/60 s, with 5-6x fewer button-down/up events.)

## Known limitations / next steps

- **No pause mid-stroke.** Pause/terminate is still checked between strokes, so
  granularity is coarser now. `draw_state["segment_idx"]` is the intended place
  to record a distance-along-path offset for resumable strokes.
- **No UI controls** for `stroke_speed` / `frame_interval` yet.
- **Not calibrated against skribbl.** Defaults are theoretical; a calibration
  pass (draw a line/circle/zigzag at increasing speed, screenshot, detect gaps)
  should set the real defaults.
- **Cache key** still includes `stroke_distance`; the strokes JSON shape is
  unchanged (lists of points), so old caches load but now mean the new shape.
- `docs/` were updated to describe the polyline outline; the sketch above is
  the working summary.
