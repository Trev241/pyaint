from pyaint.log import log
import pyautogui
import time
from pyaint import utils

from pyaint.errors import (
    NoCanvasError,
    NoPaletteError
)
from PIL import Image

from pyaint.profile import Profile
from pyaint.painter import ScreenPainter
from pyaint.locators import detect_target
from pyaint.palette import Palette
from pyaint.cache import CacheMixin

class Bot(CacheMixin):
    DELAY, STEP, JUMP_DELAY = tuple(i for i in range(3))

    SLOTTED = 'slotted'
    LAYERED = 'layered'

    IGNORE_WHITE = 1 << 0

    def __init__(self, profile=None):
        self.terminate = False
        self.paused = False
        self.pause_key = 'p'
        self.settings = [.1, 12, 0.5]  # [delay, pixel_size, jump_delay]
        self.drawing = False  # Flag to indicate if currently drawing
        self.skip_first_color = False  # Skip first color when drawing
        self.jump_threshold = 5  # Pixel distance threshold for jump detection (default 5)

        # The taught environment lives in one shared Profile (pyaint/profile.py).
        # The UI and this bot reference the same instance, giving a single
        # source of truth for palette/canvas/colour-selection configuration.
        self.profile = profile if profile is not None else Profile()

        # Drawing state for pause/resume
        self.draw_state = {
            'color_idx': 0,
            'line_idx': 0,
            'segment_idx': 0,
            'current_color': None,
            'cmap': None
        }

        # Live palette object, derived from the profile's Palette geometry.
        self._palette = None

        # Screen-input driver: the app-specific half of the engine. The
        # planner keeps app-agnostic logic; all synthetic input goes through
        # this object so other transports can be substituted later.
        self.painter = ScreenPainter(self)

        # Progress reporting. The UI assigns ``progress_callback``; it is
        # invoked from the worker thread, so the UI must marshal it onto its
        # own event loop (the Qt UI emits a signal from it).
        self.progress_callback = None
        self.progress_overlay_enabled = True

        pyautogui.PAUSE = 0.0
        pyautogui.MINIMUM_DURATION = 0.01

    # ------------------------------------------------------------------
    # Environment views. The single source of truth is ``self.profile``;
    # these keep the engine's attribute-style access working unchanged.
    # ------------------------------------------------------------------
    @property
    def new_layer(self):
        return self.profile['New Layer']

    @property
    def color_button(self):
        return self.profile['Color Button']

    @property
    def color_button_okay(self):
        return self.profile['Color Button Okay']

    @property
    def mspaint_mode(self):
        return self.profile.mspaint_mode

    @property
    def _canvas(self):
        return self.profile.canvas_rect()

    # ------------------------------------------------------------------
    # Colour selection (palette swatches only)
    # ------------------------------------------------------------------
    def _color_source(self, target):
        """Decide how ``target`` should be selected, without performing input.

        Returns ``'palette'`` or ``'none'``.
        """
        return self.painter.resolve_color_source(target)

    def _select_color(self, target):
        """Select ``target`` in the painting app (from the sampled palette)."""
        return self.painter.select_color(target)

    def init_palette(self, colors_pos=None, prows=None, pcols=None, pbox=None) -> Palette:
        # ``pbox`` is (left, top, width, height) — pyautogui's format.
        try:
            if colors_pos is not None:
                self._palette = Palette(colors_pos=colors_pos)
            elif pbox is not None and prows is not None and pcols is not None:
                self._palette = Palette(box=pbox, rows=prows, columns=pcols)
            else:
                raise ValueError('Invalid parameters for palette initialization')
        except Exception as e:
            raise NoPaletteError(f'Bot could not continue because palette is either missing or its dimensions are faulty: {e}')

        return self._palette

    def init_canvas(self, cabox):
        # Store the taught canvas box (corners) in the shared profile. The
        # ``_canvas`` property derives the (x, y, w, h) view used by the engine.
        self.profile['Canvas']['box'] = list(cabox)

    # ------------------------------------------------------------------
    # Auto-detection (Phase 2)
    # ------------------------------------------------------------------
    def capture_screen(self):
        """Return the current full-screen image as a PIL image."""
        return pyautogui.screenshot()

    def detect_target(self, recipe=None):
        """Run the target recipe's locators against the current screen.

        Returns a ``pyaint.locators.Detection`` (falsy if nothing was found).
        """
        if recipe is None:
            from pyaint.targets import get_recipe
            recipe = get_recipe(self.profile.target)
        return detect_target(recipe, self.capture_screen())

    def apply_detection(self, detection):
        """Apply a Detection to the live profile/palette; return what was used."""
        applied = []
        if detection.canvas:
            x, y, w, h = detection.canvas
            self.init_canvas((x, y, x + w, y + h))
            self.profile['Canvas']['status'] = True
            applied.append('canvas')
        if detection.palette and detection.palette_rows and detection.palette_cols:
            x, y, w, h = detection.palette
            palette = self.init_palette(
                pbox=(x, y, w, h),
                prows=detection.palette_rows,
                pcols=detection.palette_cols,
            )
            entry = self.profile['Palette']
            entry['box'] = [x, y, x + w, y + h]
            entry['rows'] = detection.palette_rows
            entry['cols'] = detection.palette_cols
            entry['color_coords'] = {str(k): v for k, v in palette.colors_pos.items()}
            entry['status'] = True
            applied.append('palette')
        return applied

    
    
    
    
    
    
    # def test(self):
    #     box = self._canvas
    #     locs = [p for p in self._palette.colors_pos.values()] + [(box[0], box[1]), (box[0] + box[2], box[1] + box[3])]
    #     for l in locs:
    #         pyautogui.moveTo(l)
    #         time.sleep(.25)

    def process(self, file, flags=0, mode=LAYERED):
        '''
        Processes the requested file as per the flags submitted and returns 
        a table mapping each color to a list of lines that are to be drawn on 
        the canvas. Each line contains both starting and terminating coordinates.
        '''
        
        self.terminate = False
        step = int(self.settings[Bot.STEP])
        img = Image.open(file).convert('RGBA')

        try:
            x, y, cw, ch = self._canvas  # type: ignore[union-attr]
        except Exception:
            raise NoCanvasError('Bot could not continue because canvas is not initialized')

        tw, th = tuple(int(p // step) for p in utils.adjusted_img_size(img, (cw, ch)))
        xo = x = x + ((cw - tw * step) // 2)    # Center the drawing correctly
        y += ((ch - th * step) // 2)
    
        try:
            # Try newer PIL syntax
            img_small = img.resize((tw, th), resample=Image.Resampling.NEAREST)
        except AttributeError:
            # Fallback to older PIL syntax
            img_small = img.resize((tw, th), resample=Image.NEAREST)  # type: ignore
        pix = img_small.load()
        w, h = img_small.size
        return self._encode_rows(pix, w, h, xo, y, step, flags, mode)

    # ------------------------------------------------------------------
    # Shared run-length / layering engine
    # ------------------------------------------------------------------
    def _emit_run(self, cmap, table_lines, table_colors, col_freq, row, color, start, end, mode, flags):
        """Record one horizontal run as a stroke (or a layer-table row)."""
        if color is None:
            return
        if mode is Bot.SLOTTED:
            if color == (255, 255, 255) and flags & Bot.IGNORE_WHITE:
                return
            cmap.setdefault(color, []).append((start, end))
        else:
            table_lines[row].append((color, (start, end)))
            table_colors[row].add(color)
            col_freq[color] = col_freq.get(color, 0) + end[0] - start[0] + 1

    def _merge_layers(self, cmap, table_lines, table_colors, col_freq, flags):
        """Merge lower-layer runs into fewer strokes (LAYERED mode only)."""
        # Sort colors in decreasing order of their frequency and maintain a
        # height level index for each color.
        col_order = tuple(
            k for k, _ in sorted(col_freq.items(), key=lambda item: item[1], reverse=True)
        )
        col_index = {col_order[i]: i for i in range(len(col_order))}

        # Lines of lower layer colors can be merged into fewer strokes since
        # they will be repainted again by colors from a higher layer.
        for idc, col in enumerate(col_order):
            for idr, row in enumerate(table_lines):
                if col not in table_colors[idr] or (col == (255, 255, 255) and flags & Bot.IGNORE_WHITE):
                    continue

                start, end, exposed = None, None, False
                for idl, line in enumerate(row):
                    if idc <= col_index[line[0]]:
                        start = line[1][0] if start is None else start
                        end = line[1][1]
                        exposed = exposed or idc == col_index[line[0]]
                    if start is not None and (idc > col_index[line[0]] or idl == len(row) - 1):
                        if exposed:
                            cmap.setdefault(col, []).append((start, end))
                        start, exposed = None, False
        return cmap

    def _encode_rows(self, pix, w, h, xo, y0, step, flags, mode):
        """Run-length encode a downsampled pixel grid into a stroke map.

        A run is closed when the colour changes (ending on the previous pixel)
        and again at the end of each row (so the final pixel is included).
        Shared by process() and process_region().
        """
        nearest_colors = {}
        cmap = {}
        col_freq = {}
        table_lines = []
        table_colors = []
        y = y0

        for i in range(h):
            if mode is Bot.LAYERED:
                table_lines.append(list())
                table_colors.append(set())

            x = xo
            start = (x, y)
            old_col = None
            for j in range(w):
                r, g, b = pix[j, i][:3]

                if (r, g, b) not in nearest_colors:
                    nearest_colors[(r, g, b)] = self._palette.nearest_color((r, g, b))
                col = nearest_colors[(r, g, b)]

                if old_col is not None and old_col != col:
                    self._emit_run(cmap, table_lines, table_colors, col_freq,
                                   i, old_col, start, (x - step, y), mode, flags)
                    start = (x, y)

                old_col = col
                x += step

            # Close the run that contains the final pixel of the row.
            self._emit_run(cmap, table_lines, table_colors, col_freq,
                           i, old_col, start, (x - step, y), mode, flags)
            y += step

        if mode is Bot.SLOTTED:
            return cmap
        return self._merge_layers(cmap, table_lines, table_colors, col_freq, flags)

    def draw(self, cmap):
        '''
        Draws the image as per the coordinates of the processed cmap table.
        Supports pause/resume functionality and configurable jump delays.
        '''

        # Calculate total strokes for progress tracking (must be before overlay creation)
        self.total_strokes = sum(len(lines) for lines in cmap.values())
        self.start_time = time.time()
        self.completed_strokes = 0

        self._report_progress(0, self.total_strokes, 0)

        # Reset bot state for fresh drawing session
        self.terminate = False
        self.paused = False
        self.drawing = True  # Mark as actively drawing
        last_stroke_end = None  # Track last stroke position for jump detection
        self.estimated_time_seconds = self._estimate_drawing_time_seconds(cmap)
        estimated_str = self._format_time(self.estimated_time_seconds)
        log.info(f"Estimated drawing time: {estimated_str}")

        for color_idx, (c, lines) in enumerate(cmap.items()):
            # Skip the first color if skip_first_color is enabled
            if color_idx == 0 and self.skip_first_color:
                log.info(f"[Skip First Color] Skipping first color: {c}")
                continue

            # Skip colors already drawn if resuming
            if color_idx < self.draw_state['color_idx']:
                continue

            # If resuming and we have a specific color to resume with, use that instead
            if self.draw_state['current_color'] is not None and color_idx == self.draw_state['color_idx']:
                c = self.draw_state['current_color']
                log.info(f"Resuming with saved color {c}")

            # Log color change with cached coordinate info
            num_strokes = len(lines)
            log.info(f"Switching to color {c} - {num_strokes} cached coordinate points")

            # If New Layer is enabled, click the new-layer button with modifiers.
            # Skip on first color when skip_first_color is enabled.
            if not (color_idx == 0 and self.skip_first_color):
                self.painter.new_layer()

            # If Color Button Mode is enabled, click the color button with modifiers before palette selection
            self.painter.color_button()

            # Select the colour from the sampled palette.
            self._select_color(c)

            # If Color Button Okay Mode is enabled, click "Set Okay" button after color selection
            self.painter.color_button_okay()

            for line_idx, line in enumerate(lines):
                # Skip lines already drawn if resuming
                if color_idx == self.draw_state['color_idx'] and line_idx < self.draw_state['line_idx']:
                    continue

                # Update progress and calculate estimates
                self.completed_strokes += 1
                strokes_remaining = self.total_strokes - self.completed_strokes

                # Calculate elapsed time and estimate remaining time
                elapsed_time = time.time() - self.start_time
                if self.completed_strokes > 0:
                    avg_time_per_stroke = elapsed_time / self.completed_strokes
                    estimated_remaining = strokes_remaining * avg_time_per_stroke

                    # Format time remaining
                    if estimated_remaining < 60:
                        time_remaining = f"{estimated_remaining:.1f}s"
                    elif estimated_remaining < 3600:
                        minutes = int(estimated_remaining // 60)
                        seconds = estimated_remaining % 60
                        time_remaining = f"{minutes}:{seconds:02.0f}"
                    else:
                        hours = int(estimated_remaining // 3600)
                        minutes = int((estimated_remaining % 3600) // 60)
                        time_remaining = f"{hours}:{minutes:02.0f}h"
                else:
                    time_remaining = "calculating..."

                # Log stroke progress with time remaining and strokes left
                progress_percent = ((line_idx + 1) / len(lines)) * 100
                log.info(f"Drawing stroke {line_idx + 1}/{len(lines)} for color {c} - {progress_percent:.1f}% complete")
                log.info(f"Total progress: {self.completed_strokes}/{self.total_strokes} strokes - {time_remaining} remaining")

                self._report_progress(self.completed_strokes, self.total_strokes, estimated_remaining)

                # Check for large cursor jumps and add delay
                start_pos = line[0]
                if last_stroke_end is not None:
                    jump_distance = ((start_pos[0] - last_stroke_end[0]) ** 2 + (start_pos[1] - last_stroke_end[1]) ** 2) ** 0.5
                    if jump_distance > self.jump_threshold:
                        log.info(f"Large jump detected ({jump_distance:.1f} pixels) - adding {self.settings[Bot.JUMP_DELAY]}s delay")
                        time.sleep(self.settings[Bot.JUMP_DELAY])

                # Wait if paused - detect when we come out of pause for stroke replay
                was_paused = False
                while self.paused and not self.terminate:
                    was_paused = True
                    # Ensure any stuck modifier keys are released during pause
                    try:
                        pyautogui.keyUp('shift')
                        pyautogui.keyUp('alt')
                        pyautogui.keyUp('ctrl')
                    except Exception:
                        pass  # Ignore errors if keys are already released
                    time.sleep(0.1)  # Small delay to avoid busy waiting

                # If we just came out of pause, mark for stroke replay
                if was_paused:
                    self.draw_state['was_paused'] = True

                if self.terminate:
                    pyautogui.mouseUp()
                    self.drawing = False  # Clear drawing flag on termination
                    return 'terminated'

                # Draw line with pause support (complete each stroke before checking pause)
                end_pos = (line[1][0], line[1][1])
                self.painter.execute_stroke(start_pos, end_pos, self.settings[Bot.DELAY])

                # Check for pause after completing the stroke
                if self.paused or self.terminate:
                    # Save current state for resume
                    self.draw_state['color_idx'] = color_idx
                    self.draw_state['line_idx'] = line_idx
                    self.draw_state['segment_idx'] = 0  # Stroke completed, so reset segment
                    self.draw_state['current_color'] = c  # Save current color
                    if self.terminate:
                        self.drawing = False  # Clear drawing flag on termination
                        return 'terminated'
                    # Wait for resume
                    log.info("Paused after completing stroke - press resume to continue")
                    while self.paused and not self.terminate:
                        time.sleep(0.1)
                    if self.terminate:
                        self.drawing = False  # Clear drawing flag on termination
                        return 'terminated'
                    # Resume - replay the current stroke to ensure clean result
                    log.info(f"Resuming - replaying current stroke for color {c}")
                    self.draw_state['was_paused'] = True

                # Update last stroke position for jump detection
                last_stroke_end = end_pos

        # Calculate actual time and show comparison
        actual_time = time.time() - self.start_time
        actual_str = self._format_time(actual_time)
        estimated_str = self._format_time(self.estimated_time_seconds)
        
        # Calculate difference (positive = saved time, negative = extra time)
        diff_seconds = self.estimated_time_seconds - actual_time
        if diff_seconds >= 0:
            diff_str = f"Saved: {self._format_time(diff_seconds)}"
        else:
            diff_str = f"Extra: {self._format_time(abs(diff_seconds))}"
        
        log.info("=" * 50)
        log.info(f"Drawing completed!")
        log.info(f"Estimated: {estimated_str}")
        log.info(f"Actual:   {actual_str}")
        log.info(f"{diff_str}")
        log.info("=" * 50)
        
        # Reset draw state on successful completion
        self.drawing = False  # Clear drawing flag
        self.draw_state['color_idx'] = 0
        self.draw_state['line_idx'] = 0
        self.draw_state['segment_idx'] = 0
        self.draw_state['current_color'] = None
        self.draw_state['was_paused'] = False
        return 'success'

    def test_draw(self, cmap, max_lines=20):
        '''
        Test draw the first max_lines from the coordinate map.
        Useful for calibrating brush size before full drawing.
        '''
        # Set drawing flag for pause/resume support during test draw
        self.drawing = True
        lines_drawn = 0
        self.start_time = time.time()  # Track start time for test draw

        self._report_progress(0, min(max_lines, sum(len(lines) for lines in cmap.values())), 0)

        # Estimate time for the full cmap (not just test lines)
        self.estimated_time_seconds = self._estimate_drawing_time_seconds(cmap)
        estimated_str = self._format_time(self.estimated_time_seconds)
        log.info(f"Estimated drawing time (full): {estimated_str}")

        for color_idx, (c, lines) in enumerate(cmap.items()):
            if lines_drawn >= max_lines:
                break

            # Log color change
            log.debug(f"[DEBUG] Color Button Okay enabled: {self.color_button_okay.get('enabled', False)}")
            log.info(f"Switching to color {c} for test draw")

            self._select_color(c)

            # Only click okay button if Color Button Okay is enabled
            self.painter.color_button_okay()

            for line_idx, line in enumerate(lines):
                if lines_drawn >= max_lines:
                    break

                # Log progress
                lines_drawn += 1
                log.info(f"Drawing test line {lines_drawn}/{max_lines} for color {c}")

                self._report_progress(lines_drawn, max_lines, 0)

                # Check for pause/terminate
                if self.terminate:
                    pyautogui.mouseUp()
                    self.drawing = False  # Clear drawing flag on termination
                    return 'terminated'

                # Draw the line (simplified, no segmentation for test draw)
                start_pos, end_pos = line
                self.painter.execute_test_stroke(start_pos, end_pos)

        # Show time comparison for test draw
        actual_time = time.time() - self.start_time
        actual_str = self._format_time(actual_time)
        
        # Calculate difference (positive = saved time, negative = extra time)
        diff_seconds = self.estimated_time_seconds - actual_time
        if diff_seconds >= 0:
            diff_str = f"Saved: {self._format_time(diff_seconds)}"
        else:
            diff_str = f"Extra: {self._format_time(abs(diff_seconds))}"
        
        log.info("=" * 50)
        log.info(f"Test draw completed: {lines_drawn} lines drawn")
        log.info(f"Estimated (full): {self._format_time(self.estimated_time_seconds)}")
        log.info(f"Actual (test):   {actual_str}")
        log.info(f"{diff_str}")
        log.info("=" * 50)
        
        self.drawing = False  # Clear drawing flag
        return 'success'


    def _estimate_drawing_time_seconds(self, cmap):
        """Estimate drawing time in seconds (internal helper method)."""
        return utils.estimate_drawing_seconds(
            cmap,
            self.settings[Bot.DELAY],
            self.settings[Bot.JUMP_DELAY],
            self.jump_threshold,
        )

    def _format_time(self, seconds):
        """Format seconds into a human-readable time string."""
        return utils.format_duration(seconds)

    def estimate_drawing_time(self, cmap):
        """Estimate how long drawing might take based on coordinate data."""
        try:
            return utils.format_estimate(self._estimate_drawing_time_seconds(cmap))
        except Exception:
            return "Unknown (unable to analyze)"



    def process_region(self, file, region, flags=0, mode=LAYERED, canvas_target=None):
        '''
        Processes a specific region of an image as per the flags submitted and returns
        a table mapping each color to a list of lines that are to be drawn on
        the canvas. Each line contains both starting and terminating coordinates.

        region: (x1, y1, x2, y2) - coordinates in the reference image space
        canvas_target: (x, y, w, h) - target canvas area where drawing should happen (optional)
        '''

        self.terminate = False
        step = int(self.settings[Bot.STEP])
        img = Image.open(file).convert('RGBA')

        # Crop the image to the specified region
        x1, y1, x2, y2 = region
        img_cropped = img.crop((x1, y1, x2, y2))

        try:
            canvas_x, canvas_y, canvas_w, canvas_h = self._canvas  # type: ignore[union-attr]
        except Exception:
            raise NoCanvasError('Bot could not continue because canvas is not initialized')

        # Determine where to position the drawing on the canvas
        if canvas_target is not None:
            # Use the specified target area
            target_x, target_y, target_w, target_h = canvas_target
            # Scale the cropped image to fit the target area while maintaining aspect ratio
            cropped_w, cropped_h = img_cropped.size
            scale = min(target_w / cropped_w, target_h / cropped_h)
            scaled_w = int(cropped_w * scale)
            scaled_h = int(cropped_h * scale)
            # Position at the target location
            xo = target_x
            y_start = target_y
        else:
            # Default behavior: scale to fit canvas and center
            cropped_w, cropped_h = img_cropped.size
            scale = min(canvas_w / cropped_w, canvas_h / cropped_h)
            scaled_w = int(cropped_w * scale)
            scaled_h = int(cropped_h * scale)
            # Center on canvas
            offset_x = (canvas_w - scaled_w) // 2
            offset_y = (canvas_h - scaled_h) // 2
            xo = canvas_x + offset_x
            y_start = canvas_y + offset_y

        # Calculate pixel step for the scaled image
        tw, th = scaled_w // step, scaled_h // step

        try:
            # Try newer PIL syntax
            img_small = img_cropped.resize((tw, th), resample=Image.Resampling.NEAREST)
        except AttributeError:
            # Fallback to older PIL syntax
            img_small = img_cropped.resize((tw, th), resample=Image.NEAREST)  # type: ignore
        pix = img_small.load()
        w, h = img_small.size
        return self._encode_rows(pix, w, h, xo, y_start, step, flags, mode)

    def simple_test_draw(self):
        '''
        Simple test draw that draws 5 horizontal lines starting from the
        upper-left corner of the canvas. Each line is 1/4 of the canvas width.
        No color picking - user should manually set their desired color first.
        Useful for quickly adjusting brush size.
        '''
        try:
            canvas_x, canvas_y, canvas_w, canvas_h = self._canvas
        except Exception:
            raise NoCanvasError('Bot could not continue because canvas is not initialized')

        self.drawing = True
        log.info("Starting simple test draw...")

        # Calculate 1/4 of canvas width
        quarter_width = canvas_w // 4

        # Draw 5 horizontal lines
        for i in range(5):
            # Calculate vertical position (start at 0, move down by pixel_size)
            y_offset = i * self.settings[Bot.STEP]

            start_x = canvas_x
            start_y = canvas_y + y_offset
            end_x = canvas_x + quarter_width
            end_y = canvas_y + y_offset

            log.info(f"Drawing line {i + 1}/5: from ({start_x}, {start_y}) to ({end_x}, {end_y})")

            # Move to start position
            pyautogui.moveTo(start_x, start_y)
            time.sleep(0.1)

            # Draw the line
            pyautogui.mouseDown(button='left')
            pyautogui.dragTo(end_x, end_y, 0.2, button='left')
            pyautogui.mouseUp()

            # Small delay between lines
            time.sleep(0.2)

        log.info("Simple test draw completed!")
        self.drawing = False
        return 'success'

    def _report_progress(self, completed, total, eta_seconds):
        """Report drawing progress to the UI, if one has attached a callback.

        Called from the drawing worker thread. The callback must not touch UI
        objects directly; the Qt UI connects it to a signal so the update is
        queued onto the main thread.
        """
        if not self.progress_overlay_enabled:
            return
        callback = getattr(self, "progress_callback", None)
        if callback is None:
            return
        try:
            callback(completed, total, eta_seconds)
        except Exception as e:  # never let progress reporting break a draw
            log.info(f"[Progress] callback error: {e}")
