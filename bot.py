import pyautogui
import time
import utils
import hashlib
import json
import os

from exceptions import (
    NoCustomColorsError,
    NoCanvasError,
    NoPaletteError
)
from PIL import Image

class Palette:
    def __init__(self, colors_pos=None, box=None, rows=None, columns=None):
        if colors_pos is not None:
            self.colors_pos = colors_pos
            self.colors = colors_pos.keys()
            return

        # Validate required parameters
        if box is None or rows is None or columns is None:
            raise ValueError("box, rows, and columns must be provided when colors_pos is None")

        self.box = box
        self.rows = rows
        self.columns = columns

        self._csizex = int(box[2] // columns)  # type: ignore[operator,union-attr]
        self._csizey = int(box[3] // rows)  # type: ignore[operator,union-attr]

        pix = pyautogui.screenshot(region=box).load()
        x, y = self._csizex // 2, self._csizey // 2
        xend = columns * self._csizex

        # Obtain RGB values of palette colors along with their coordinates
        # COLOR LAYOUT    :    ((r, g, b) : (x, y))
        self.colors_pos = dict()
        self.colors = set()
        for i in range(columns * rows):
            col = (pix[x, y][:3])
            self.colors_pos[col] = (box[0] + x, box[1] + y)
            self.colors.add(col)

            x = (x + self._csizex) % xend
            y = y + (self._csizey if (i + 1) % columns == 0 else 0)

    def nearest_color(self, query):
        return min(self.colors, key=lambda color: Palette.dist(color, query))

    @staticmethod
    def dist(colx, coly):
        '''
        Returns the squared distance between two RGB triplets. Since finding the root of 
        the distances has no effect on the sorting order of the final distances, it has 
        been avoided altogether for the sake of performance
        '''
        return sum((s - q) ** 2 for s, q in zip(colx, coly))
    
class Bot:
    DELAY, STEP, ACCURACY, JUMP_DELAY = tuple(i for i in range(4))
    # RESOURCES = (
    #     'assets/palette.png',
    #     'assets/canvas.png',
    #     'assets/custom_cols_mspaint.png'
    # )
    
    SLOTTED = 'slotted'
    LAYERED = 'layered'

    IGNORE_WHITE = 1 << 0
    USE_CUSTOM_COLORS = 1 << 1

    def __init__(self, config_file='config.json'):
        self.terminate = False
        self.paused = False
        self.pause_key = 'p'
        self.settings = [.1, 12, .9, 0.5]  # Added jump delay default
        self.progress = 0
        self.options = Bot.IGNORE_WHITE
        self.config_file = config_file
        self.drawing = False  # Flag to indicate if currently drawing

        # Drawing state for pause/resume
        self.draw_state = {
            'color_idx': 0,
            'line_idx': 0,
            'segment_idx': 0,
            'current_color': None,
            'cmap': None
        }

        # New Layer feature state
        self.new_layer = {
            'enabled': False,
            'coords': None,           # (x, y)
            'modifiers': {
                'ctrl': False,
                'alt': False,
                'shift': False
            }
        }

        pyautogui.PAUSE = 0.0
        pyautogui.MINIMUM_DURATION = 0.01

    def init_palette(self, colors_pos=None, prows=None, pcols=None, pbox=None) -> Palette:

        # pbox = pyautogui.locateOnScreen(Bot.RESOURCES[0], confidence=self.settings[Bot.CONF])

        # Previously, the pbox was located using screenshots, this functionality is being phased out in favour of another method.
        # pyautogui's box format is (topleftx, toplefty, width, height). Likewise, palette expects and operates on this legacy format.
        # Therefore, pbox must be adjusted to fit the required format

        try:
            if colors_pos is not None:
                self._palette = Palette(colors_pos=colors_pos)
            elif pbox is not None and prows is not None and pcols is not None:
                pbox_adj = pbox[0], pbox[1], pbox[2] - pbox[0], pbox[3] - pbox[1]
                self._palette = Palette(box=pbox_adj, rows=prows, columns=pcols)
            else:
                raise ValueError('Invalid parameters for palette initialization')
        except Exception as e:
            raise NoPaletteError(f'Bot could not continue because palette is either missing or its dimensions are faulty: {e}')

        return self._palette

    def init_canvas(self, cabox):
        # self._canvas = pyautogui.locateOnScreen(Bot.RESOURCES[1], confidence=self.settings[Bot.CONF])

        # Just like the old pbox, the bot works on the assumption that the canvas box is stored using the format
        # (topleftx, toplefty, width, height). Adjustments have been made below to conform with this standard.
        self._canvas = cabox[0], cabox[1], cabox[2] - cabox[0], cabox[3] - cabox[1]

    def init_custom_colors(self, ccbox):
        # self._custom_colors = pyautogui.locateOnScreen(Bot.RESOURCES[2], confidence=self.settings[Bot.CONF])
        self._custom_colors = ccbox[0], ccbox[1], ccbox[2] - ccbox[0], ccbox[3] - ccbox[1]
    
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
        except:
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
        size = w * h
        start = xo, y

        nearest_colors = dict()
        cmap = dict()

        col_freq = dict()
        table_lines = list()
        table_colors = list()

        old_col = None

        # Create interval size from normalized accuracy value
        # Also setting a lower bound value of 1 to prevent interval_size from reaching 0
        interval_size = max((1 - self.settings[Bot.ACCURACY]) * 255, 1)

        for i in range(h):
            if mode is Bot.LAYERED:
                table_lines.append(list())
                table_colors.append(set())

            for j in range(w): 
                r, g, b = pix[j, i][:3]
                col = near = (r, g, b)

                # DESIGNATING COLOR OF THE CURRENT PIXEL
                # Deciding what to do with new RGB triplet
                if (r, g, b) not in nearest_colors:
                    if flags & Bot.USE_CUSTOM_COLORS:
                        # # Find the nearest custom color previously used, if any
                        # if len(cmap.keys()) > 0:
                        #     near = min(cmap.keys(), key=lambda c : Palette.dist(c, near))
                        # # Find the euclidean distance of the furthest color
                        # max_dist = sum( max( 255 - col[i], col[i] - 0) ** 2 for i in range(len(col)) ) 
                        # col = near if (max_dist - Palette.dist(near, col)) / max_dist >= self.settings[Bot.ACCURACY] else col

                        # Obtain the closest color
                        # round(color_component / interval_size) * interval_size
                        col = tuple(int(round(v / interval_size) * interval_size) for v in col)
                    else:
                        # Find the nearest color from the palette
                        col = self._palette.nearest_color((r, g, b))

                    # Save the nearest color for this RGB triplet to avoid recomputing it
                    nearest_colors[(r, g, b)] = col
                else:
                    col = nearest_colors[(r, g, b)]

                # DESIGNATING COLOR LINES
                # End brush stroke when...
                # 1. a new color is encountered 
                # 2. the brush is at the end of the row
                if j == w - 1 or (old_col != None and old_col != col):
                    end = (x, y)
                    if mode is Bot.SLOTTED and not (old_col == (255, 255, 255) and flags & Bot.IGNORE_WHITE):
                        lines = cmap.get(old_col, [])
                        lines.append( (start, end) )
                        cmap[old_col] = lines
                    if mode is Bot.LAYERED:
                        table_lines[i].append((old_col, (start, end)))
                        table_colors[i].add(old_col)
                        col_freq[old_col] = col_freq.get(old_col, 0) + end[0] - start[0] + 1
                    start = (xo, y + step) if j == w - 1 else (x + step, y)
                
                self.progress = 100 * (i * w + (j + 1)) / size

                old_col = col
                x += step

            x = xo
            y += step
        
        if mode is Bot.SLOTTED:
            return cmap

        # Sort colors in decreasing order of their frequency and maintain a height level index for each color
        col_freq = tuple(k for k, _ in sorted(col_freq.items(), key=lambda item : item [1], reverse=True))
        col_index = {col_freq[i]: i for i in range(len(col_freq))}     
    
        # This loop will attempt to merge lines in favour of reducing the number of brush strokes when drawing.
        # Lines of lower layer colors can be easily merged into fewer strokes since they will be repainted over
        # again by colors from a higher layer
        for idc, col in enumerate(col_freq):
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
                            lines = cmap.get(col, [])
                            lines.append((start, end))
                            cmap[col] = lines
                        start, exposed = None, False

        return cmap

    def draw(self, cmap):
        '''
        Draws the image as per the coordinates of the processed cmap table.
        Depending upon the selection of colors used, the bot will choose
        from either the standard palette or custom color option accordingly.
        Supports pause/resume functionality and configurable jump delays.
        '''

        # Reset bot state for fresh drawing session
        self.terminate = False
        self.paused = False
        self.drawing = True  # Mark as actively drawing
        last_stroke_end = None  # Track last stroke position for jump detection

        # Calculate total strokes for progress tracking
        self.total_strokes = sum(len(lines) for lines in cmap.values())
        self.start_time = time.time()
        self.completed_strokes = 0

        for color_idx, (c, lines) in enumerate(cmap.items()):
            # Skip colors already drawn if resuming
            if color_idx < self.draw_state['color_idx']:
                continue

            # If resuming and we have a specific color to resume with, use that instead
            if self.draw_state['current_color'] is not None and color_idx == self.draw_state['color_idx']:
                c = self.draw_state['current_color']
                print(f"Resuming with saved color {c}")

            # Log color change with cached coordinate info
            num_strokes = len(lines)
            print(f"Switching to color {c} - {num_strokes} cached coordinate points")

            # If New Layer is enabled, click the new-layer button with modifiers
            try:
                nl = self.new_layer
                if nl.get('enabled') and nl.get('coords'):
                    nx, ny = nl['coords']
                    print(f"[NewLayer] attempting click at {(nx, ny)} with mods={nl.get('modifiers')}")
                    # Hold modifiers
                    if nl['modifiers'].get('ctrl'):
                        pyautogui.keyDown('ctrl')
                    if nl['modifiers'].get('alt'):
                        pyautogui.keyDown('alt')
                    if nl['modifiers'].get('shift'):
                        pyautogui.keyDown('shift')

                    # Give the OS a moment to register modifier keydowns
                    time.sleep(0.12)

                    # Use explicit mouseDown/mouseUp for better reliability in some apps
                    print(f"[NewLayer] performing mouseDown at {(nx, ny)}")
                    pyautogui.mouseDown(nx, ny, button='left')
                    time.sleep(0.06)
                    pyautogui.mouseUp(nx, ny, button='left')
                    print(f"[NewLayer] mouse click performed at {(nx, ny)}")

                    # Short delay to ensure the target app processes the click before releasing modifiers
                    time.sleep(0.18)

                    # Release modifiers
                    if nl['modifiers'].get('shift'):
                        pyautogui.keyUp('shift')
                    if nl['modifiers'].get('alt'):
                        pyautogui.keyUp('alt')
                    if nl['modifiers'].get('ctrl'):
                        pyautogui.keyUp('ctrl')

                    # Give a bit more time for UI to update before selecting color
                    time.sleep(0.12)
            except Exception:
                pass

            if c in self._palette.colors:
                pyautogui.click(self._palette.colors_pos[c], clicks=3, interval=.15)
            else:
                try:
                    cc_box = self._custom_colors
                    pyautogui.click( (cc_box[0] + cc_box[2] // 2, cc_box[1] + cc_box[3] // 2 ), clicks=3, interval=.15)
                except:
                    raise NoCustomColorsError('Bot could not continue because custom colors are not initialized')
                pyautogui.press('tab', presses=7, interval=.05)
                for val in c:
                    numbers = (d for d in str(val))
                    for n in numbers:
                        pyautogui.press(str(n))
                    pyautogui.press('tab')
                pyautogui.press('tab')
                pyautogui.press('enter')
                pyautogui.PAUSE = 0.0

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
                print(f"Drawing stroke {line_idx + 1}/{len(lines)} for color {c} - {progress_percent:.1f}% complete")
                print(f"Total progress: {self.completed_strokes}/{self.total_strokes} strokes - {time_remaining} remaining")

                # Check for large cursor jumps and add delay
                start_pos = line[0]
                if last_stroke_end is not None:
                    jump_distance = ((start_pos[0] - last_stroke_end[0]) ** 2 + (start_pos[1] - last_stroke_end[1]) ** 2) ** 0.5
                    if jump_distance > 5:  # More than 5 pixels apart
                        print(f"Large jump detected ({jump_distance:.1f} pixels) - adding {self.settings[Bot.JUMP_DELAY]}s delay")
                        time.sleep(self.settings[Bot.JUMP_DELAY])

                # Wait if paused - detect when we come out of pause for stroke replay
                was_paused = False
                while self.paused and not self.terminate:
                    was_paused = True
                    time.sleep(0.1)  # Small delay to avoid busy waiting

                # If we just came out of pause, mark for stroke replay
                if was_paused:
                    self.draw_state['was_paused'] = True

                if self.terminate:
                    pyautogui.mouseUp()
                    self.drawing = False  # Clear drawing flag on termination
                    return 'terminated'

                # Draw line with pause support
                end_pos = (line[1][0], line[1][1])

                # Calculate distance
                dx = end_pos[0] - start_pos[0]
                dy = end_pos[1] - start_pos[1]
                distance = (dx**2 + dy**2)**0.5

                if distance < 1:  # Very short line
                    pyautogui.moveTo(start_pos)
                    pyautogui.dragTo(end_pos[0], end_pos[1], self.settings[Bot.DELAY], button='left')
                else:
                    # Break into segments for pause support
                    segments = max(2, min(10, int(distance / 10)))  # 2-10 segments based on length
                    segment_delay = self.settings[Bot.DELAY] / segments

                    pyautogui.moveTo(start_pos)
                    pyautogui.mouseDown(button='left')

                    # Always replay the current stroke when resuming from pause
                    start_segment = 1
                    if self.draw_state.get('was_paused', False):
                        print(f"Replaying stroke after pause - ensuring clean result")
                        self.draw_state['was_paused'] = False

                    for i in range(start_segment, segments + 1):
                        if self.paused or self.terminate:
                            # Save current state for resume
                            self.draw_state['color_idx'] = color_idx
                            self.draw_state['line_idx'] = line_idx
                            self.draw_state['segment_idx'] = i - 1  # Current segment being drawn
                            self.draw_state['current_color'] = c  # Save current color
                            pyautogui.mouseUp()
                            if self.terminate:
                                return 'terminated'
                            # Wait for resume
                            while self.paused and not self.terminate:
                                time.sleep(0.1)
                            if self.terminate:
                                return 'terminated'
                            # Resume the stroke - ensure we're using the correct color
                            if self.draw_state['current_color'] != c:
                                print(f"Resuming with color {self.draw_state['current_color']} (was {c})")
                                c = self.draw_state['current_color']
                                # Re-select the correct color
                                if c in self._palette.colors:
                                    pyautogui.click(self._palette.colors_pos[c], clicks=3, interval=.15)
                                else:
                                    try:
                                        cc_box = self._custom_colors
                                        pyautogui.click((cc_box[0] + cc_box[2] // 2, cc_box[1] + cc_box[3] // 2), clicks=3, interval=.15)
                                    except:
                                        raise NoCustomColorsError('Bot could not continue because custom colors are not initialized')
                                    pyautogui.press('tab', presses=7, interval=.05)
                                    for val in c:
                                        numbers = (d for d in str(val))
                                        for n in numbers:
                                            pyautogui.press(str(n))
                                        pyautogui.press('tab')
                                    pyautogui.press('tab')
                                    pyautogui.press('enter')
                                pyautogui.PAUSE = 0.0
                            pyautogui.mouseDown(button='left')

                        # Calculate next position
                        t = i / segments
                        next_x = start_pos[0] + dx * t
                        next_y = start_pos[1] + dy * t

                        pyautogui.moveTo(next_x, next_y)
                        time.sleep(segment_delay / segments)  # Distribute delay

                    pyautogui.mouseUp()

                # Update last stroke position for jump detection
                last_stroke_end = end_pos

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

        for color_idx, (c, lines) in enumerate(cmap.items()):
            if lines_drawn >= max_lines:
                break

            # Log color change
            print(f"Switching to color {c} for test draw")

            if c in self._palette.colors:
                pyautogui.click(self._palette.colors_pos[c], clicks=3, interval=.15)
            else:
                try:
                    cc_box = self._custom_colors
                    pyautogui.click((cc_box[0] + cc_box[2] // 2, cc_box[1] + cc_box[3] // 2), clicks=3, interval=.15)
                except:
                    raise NoCustomColorsError('Bot could not continue because custom colors are not initialized')
                pyautogui.press('tab', presses=7, interval=.05)
                for val in c:
                    numbers = (d for d in str(val))
                    for n in numbers:
                        pyautogui.press(str(n))
                    pyautogui.press('tab')
                pyautogui.press('tab')
                pyautogui.press('enter')
                pyautogui.PAUSE = 0.0

            for line_idx, line in enumerate(lines):
                if lines_drawn >= max_lines:
                    break

                # Log progress
                lines_drawn += 1
                print(f"Drawing test line {lines_drawn}/{max_lines} for color {c}")

                # Check for pause/terminate
                if self.terminate:
                    pyautogui.mouseUp()
                    self.drawing = False  # Clear drawing flag on termination
                    return 'terminated'

                # Draw the line (simplified, no segmentation for test draw)
                start_pos, end_pos = line
                distance = ((end_pos[0] - start_pos[0]) ** 2 + (end_pos[1] - start_pos[1]) ** 2) ** 0.5

                if distance < 1:  # Very short line
                    pyautogui.moveTo(start_pos)
                    pyautogui.dragTo(end_pos[0], end_pos[1], self.settings[Bot.DELAY], button='left')
                else:
                    # Simple drag for test draw
                    pyautogui.moveTo(start_pos)
                    pyautogui.dragTo(end_pos[0], end_pos[1], self.settings[Bot.DELAY], button='left')

        print(f"Test draw completed: {lines_drawn} lines drawn")
        self.drawing = False  # Clear drawing flag
        return 'success'

    def get_cache_filename(self, image_path, flags=0, mode=LAYERED):
        """Generate a unique cache filename based on image and settings"""
        # Read image file to compute hash
        with open(image_path, 'rb') as f:
            image_data = f.read()
        image_hash = hashlib.md5(image_data).hexdigest()[:8]

        # Create settings hash - handle case where canvas isn't initialized yet
        canvas_info = getattr(self, '_canvas', None)
        if canvas_info is None:
            # Canvas not initialized, can't generate cache filename
            return None

        settings_str = f"{self.settings}_{flags}_{mode}_{canvas_info}"
        settings_hash = hashlib.md5(settings_str.encode()).hexdigest()[:8]

        # Create cache directory if it doesn't exist
        cache_dir = 'cache'
        os.makedirs(cache_dir, exist_ok=True)

        return f"{cache_dir}/{image_hash}_{settings_hash}.json"

    def estimate_drawing_time(self, cmap):
        """Estimate how long drawing might take based on coordinate data"""
        try:
            total_strokes = sum(len(lines) for lines in cmap.values())
            estimated_seconds = 0

            # Calculate time for each color's strokes
            for color, lines in cmap.items():
                last_end_pos = None

                for i, line in enumerate(lines):
                    start_pos, end_pos = line

                    # Calculate stroke distance
                    distance = ((end_pos[0] - start_pos[0]) ** 2 + (end_pos[1] - start_pos[1]) ** 2) ** 0.5

                    # Add normal delay for each stroke
                    estimated_seconds += self.settings[Bot.DELAY]

                    # Check for jump delay if this isn't the first stroke in this color
                    if last_end_pos is not None:
                        jump_distance = ((start_pos[0] - last_end_pos[0]) ** 2 + (start_pos[1] - last_end_pos[1]) ** 2) ** 0.5
                        if jump_distance > 5:  # Same threshold as in draw method
                            estimated_seconds += self.settings[Bot.JUMP_DELAY]

                    # Update last position for next jump check
                    last_end_pos = end_pos

            # Add color switching overhead (~0.5 seconds per color)
            num_colors = len(cmap)
            estimated_seconds += num_colors * 0.5

            # Format nicely
            if estimated_seconds < 10:
                return f"~{estimated_seconds:.1f} seconds"
            elif estimated_seconds < 60:
                return f"~{estimated_seconds:.0f} seconds"
            elif estimated_seconds < 3600:
                minutes = int(estimated_seconds // 60)
                seconds = estimated_seconds % 60
                return f"~{minutes}:{seconds:02.0f} minutes"
            else:
                hours = int(estimated_seconds // 3600)
                minutes = int((estimated_seconds % 3600) // 60)
                return f"~{hours}:{minutes:02.0f} hours"

        except Exception:
            return "Unknown (unable to analyze)"

    def precompute(self, image_path, flags=0, mode=LAYERED):
        """Pre-compute the image processing and save to cache"""
        cache_file = self.get_cache_filename(image_path, flags, mode)
        if cache_file is None:
            raise RuntimeError("Cannot precompute: canvas not initialized")

        print("Pre-computing image...")

        start_time = time.time()

        # Process the image
        cmap = self.process(image_path, flags, mode)

        # Prepare cache data - convert tuple keys to strings for JSON serialization
        cmap_json = {str(k): v for k, v in cmap.items()}
        cache_data = {
            'cmap': cmap_json,
            'settings': self.settings.copy(),
            'flags': flags,
            'mode': mode,
            'canvas': self._canvas,
            'image_hash': hashlib.md5(open(image_path, 'rb').read()).hexdigest()[:8],
            'timestamp': time.time(),
            'palette_info': {
                'colors_pos': {str(k): v for k, v in dict(self._palette.colors_pos).items()} if hasattr(self, '_palette') and self._palette else None,
                'colors': [list(c) for c in self._palette.colors] if hasattr(self, '_palette') and self._palette else None
            } if hasattr(self, '_palette') else None
        }

        # Save to cache file
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)

        actual_time = time.time() - start_time
        print(f"Pre-computation completed in {actual_time:.2f} seconds")
        print(f"Cache saved to: {cache_file}")

        return cache_file

    def load_cached(self, cache_file):
        """Load and validate cached computation results"""
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)

            # Basic validation
            required_keys = ['cmap', 'settings', 'flags', 'mode', 'canvas', 'timestamp']
            if not all(key in cache_data for key in required_keys):
                return None

            # Check if cache is recent (within 24 hours)
            if time.time() - cache_data['timestamp'] > 24 * 3600:
                return None

            # Validate settings match
            if cache_data['settings'] != self.settings:
                return None

            # Validate canvas matches
            if tuple(cache_data['canvas']) != tuple(self._canvas):
                return None

            # Convert string keys back to tuples for cmap
            cmap_restored = {}
            for k, v in cache_data['cmap'].items():
                # Parse tuple from string like "(255, 0, 0)"
                try:
                    # Remove parentheses and split by comma
                    tuple_str = k.strip('()')
                    tuple_parts = [int(x.strip()) for x in tuple_str.split(',')]
                    tuple_key = tuple(tuple_parts)
                    cmap_restored[tuple_key] = v
                except (ValueError, TypeError):
                    # Skip invalid keys
                    continue

            cache_data['cmap'] = cmap_restored
            return cache_data

        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return None

    def get_cached_status(self, image_path, flags=0, mode=LAYERED):
        """Check if valid cached computation exists"""
        cache_file = self.get_cache_filename(image_path, flags, mode)
        if cache_file is None:
            return False, None
        cache_data = self.load_cached(cache_file)
        return cache_data is not None, cache_file
