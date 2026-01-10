import pyautogui
import time
import utils
import hashlib
import json
import os
import math
from typing import Optional, Tuple, Dict, List, Any
from PIL import ImageGrab

from exceptions import (
    NoCustomColorsError,
    NoCanvasError,
    NoPaletteError
)
from PIL import Image

class Palette:
    def __init__(self, colors_pos=None, box=None, rows=None, columns=None, valid_positions=None, manual_centers=None):
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
        
        # Obtain RGB values of palette colors along with their coordinates
        # COLOR LAYOUT    :    ((r, g, b) : (x, y))
        self.colors_pos = dict()
        self.colors = set()
        
        # If valid_positions is None, assume all positions are valid
        if valid_positions is None:
            valid_positions = set(range(columns * rows))
        
        # If manual_centers is None, use automatic center calculation
        if manual_centers is None:
            manual_centers = {}
        
        for i in range(columns * rows):
            # Skip invalid positions
            if i not in valid_positions:
                continue
            
            # Use manual center if provided, otherwise calculate automatic center
            if i in manual_centers:
                # Use manually picked center coordinates (relative to palette box)
                center_x, center_y = manual_centers[i]
                # Convert to absolute screen coordinates
                x = center_x
                y = center_y
            else:
                # Calculate automatic center of the grid cell
                row = i // columns
                col = i % columns
                x = col * self._csizex + self._csizex // 2
                y = row * self._csizey + self._csizey // 2
            
            # Clamp coordinates to valid range to prevent index out of bounds
            x = max(0, min(x, box[2] - 1))
            y = max(0, min(y, box[3] - 1))
            col = (pix[x, y][:3])
            self.colors_pos[col] = (box[0] + x, box[1] + y)
            self.colors.add(col)

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
        self.skip_first_color = False  # Skip first color when drawing

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

        # Color Button Mode state
        self.color_button = {
            'status': False,          # whether the feature is configured
            'coords': None,           # [x, y] or null - the location to click first
            'enabled': False,         # whether the feature is active
            'delay': 0.1,             # delay in seconds (0.01 to 5.0)
            'modifiers': {            # optional modifier keys
                'ctrl': False,
                'alt': False,
                'shift': False
            }
        }

        # Color Button Okay Mode state (clicked AFTER color selection)
        self.color_button_okay = {
            'status': False,          # whether the feature is configured
            'coords': None,           # [x, y] or null - the location to click
            'enabled': False,         # whether the feature is active
            'delay': 0.1,             # delay in seconds (0.01 to 5.0)
            'modifiers': {            # optional modifier keys
                'ctrl': False,
                'alt': False,
                'shift': False
            }
        }

        # Canvas and palette will be initialized later
        self._canvas = None
        self._palette = None
        self._custom_colors = None
        
        # Color calibration map for custom colors: {(r,g,b): (x,y)}
        self.color_calibration_map = None

        pyautogui.PAUSE = 0.0
        pyautogui.MINIMUM_DURATION = 0.01

    def init_palette(self, colors_pos=None, prows=None, pcols=None, pbox=None, valid_positions=None, manual_centers=None) -> Palette:

        # pbox = pyautogui.locateOnScreen(Bot.RESOURCES[0], confidence=self.settings[Bot.CONF])

        # Previously, pbox was located using screenshots, this functionality is being phased out in favour of another method.
        # pyautogui's box format is (topleftx, toplefty, width, height). Likewise, palette expects and operates on this legacy format.
        # pbox should already be in (left, top, width, height) format when passed in

        try:
            if colors_pos is not None:
                self._palette = Palette(colors_pos=colors_pos)
            elif pbox is not None and prows is not None and pcols is not None:
                # pbox should already be in correct format (left, top, width, height), pass through directly
                self._palette = Palette(box=pbox, rows=prows, columns=pcols, valid_positions=valid_positions, manual_centers=manual_centers)
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
        
        # Scan the custom colors spectrum to create a color-to-position map
        # This allows clicking on specific colors in the spectrum instead of using keyboard input
        self._spectrum_map = self._scan_spectrum(ccbox)
        print(f"[Spectrum] Scanned {len(self._spectrum_map)} unique colors from custom colors spectrum")
    
    def _scan_spectrum(self, ccbox):
        """
        Scan the custom colors spectrum to create a color-to-position map.
        The spectrum typically shows a gradient of colors, so we sample it
        to find the closest match for any requested color.
        """
        # Get the box coordinates in (left, top, width, height) format
        left, top, width, height = ccbox[0], ccbox[1], ccbox[2] - ccbox[0], ccbox[3] - ccbox[1]
        
        # Capture the spectrum region
        spectrum_img = pyautogui.screenshot(region=(left, top, width, height))
        pix = spectrum_img.load()
        
        # Sample the spectrum at regular intervals to build a color map
        # Higher sampling = more accurate but slower
        sample_step = 4  # Sample every 4th pixel
        spectrum_map = {}
        
        print(f"[Spectrum] Scanning spectrum box: ({left}, {top}, {width}, {height})")
        
        for y in range(0, height, sample_step):
            for x in range(0, width, sample_step):
                try:
                    # Get RGB color at this position
                    r, g, b = pix[x, y][:3]
                    color = (r, g, b)
                    
                    # Store the screen coordinates for this color
                    screen_x = left + x
                    screen_y = top + y
                    spectrum_map[color] = (screen_x, screen_y)
                except (IndexError, TypeError):
                    # Skip invalid pixels
                    continue
        
        print(f"[Spectrum] Created spectrum map with {len(spectrum_map)} color positions")
        return spectrum_map
    
    def _find_nearest_spectrum_color(self, target_color):
        """
        Find the nearest color in the spectrum map to the target color.
        Returns the screen coordinates to click.
        """
        if not hasattr(self, '_spectrum_map') or not self._spectrum_map:
            return None
        
        # Find the color with minimum distance to target
        nearest_color = min(
            self._spectrum_map.keys(),
            key=lambda c: Palette.dist(c, target_color)
        )
        
        distance = Palette.dist(nearest_color, target_color)
        print(f"[Spectrum] Target: {target_color}, Nearest found: {nearest_color}, Distance: {distance:.1f}")
        
        return self._spectrum_map[nearest_color]
    
    def calibrate_custom_colors(self, grid_box: Any, preview_point: Any, step: int = 2) -> Dict[Tuple[int, int, int], Tuple[int, int]]:
        """
        Calibrate custom colors by scanning the color spectrum grid and recording
        the RGB values shown in the preview point at each grid position.
        
        Parameters:
            grid_box: list/tuple [x1, y1, x2, y2] defining the color spectrum area
            preview_point: list/tuple [x, y] defining where the selected color is shown
            step: pixel step size for scanning (default 2)
        
        Returns:
            Dictionary mapping RGB tuples to (x, y) coordinates on the grid
        """
        # Reset terminate flag to allow new calibration runs
        self.terminate = False
        self.color_calibration_map = {}
        
        # Store grid parameters for re-scanning if needed
        self._calibration_grid_box = grid_box
        self._calibration_preview_point = preview_point
        
        # Extract grid coordinates
        if isinstance(grid_box, (list, tuple)):
            grid_x = grid_box[0]
            grid_y = grid_box[1]
            # Calculate width/height assuming [x1, y1, x2, y2] format from setup
            grid_width = grid_box[2] - grid_box[0]
            grid_height = grid_box[3] - grid_box[1]
        else:
            # Fallback for dict if passed programmatically with named keys
            grid_x = grid_box['x']
            grid_y = grid_box['y']
            grid_width = grid_box['width']
            grid_height = grid_box['height']
        
        # Extract preview point coordinates
        if isinstance(preview_point, (list, tuple)):
            preview_x = preview_point[0]
            preview_y = preview_point[1]
        else:
            preview_x = preview_point['x']
            preview_y = preview_point['y']
        
        # Define the bbox for 1x1 pixel capture at preview point
        preview_bbox = (preview_x, preview_y, preview_x + 1, preview_y + 1)
        
        print(f"[Calibration] Starting calibration of custom colors grid...")
        print(f"[Calibration] Grid area: ({grid_x}, {grid_y}, {grid_width}, {grid_height})")
        print(f"[Calibration] Preview point: ({preview_x}, {preview_y})")
        print(f"[Calibration] Step size: {step}")
        
        # Press mouse down at the start of grid (to grab the slider)
        start_x = grid_x
        start_y = grid_y
        pyautogui.mouseDown(start_x, start_y, button='left')
        time.sleep(0.1)  # Small delay to ensure mouse is pressed
        
        # Track progress for console output
        total_steps = ((grid_width // step) + 1) * ((grid_height // step) + 1)
        current_step = 0
        last_progress = 0
        
        # Loop through grid coordinates with step size
        for y in range(grid_y, grid_y + grid_height, step):
            for x in range(grid_x, grid_x + grid_width, step):
                # Increment step counter
                current_step += 1
                
                # Print progress every 10% or every 100 steps, whichever is more frequent
                progress_percent = (current_step / total_steps) * 100
                if (progress_percent - last_progress >= 10) or (current_step % 100 == 0):
                    print(f"[Calibration] Progress: {current_step}/{total_steps} ({progress_percent:.1f}%) - {len(self.color_calibration_map)} colors mapped")
                    last_progress = progress_percent
                # Check for termination (ESC key pressed)
                if self.terminate:
                    print("[Calibration] Calibration cancelled by user")
                    # Release mouse before exiting
                    try:
                        pyautogui.mouseUp(button='left')
                    except:
                        pass
                    return self.color_calibration_map
                
                # Move mouse to the current grid position
                pyautogui.moveTo(x, y)
                time.sleep(0.01)  # Small delay to allow UI to update
                
                # Capture 1x1 pixel at preview point
                try:
                    pixel_img = ImageGrab.grab(bbox=preview_bbox)
                    r, g, b = pixel_img.getpixel((0, 0))
                    color = (r, g, b)
                    
                    # Store the calibration data
                    self.color_calibration_map[color] = (x, y)
                except Exception as e:
                    print(f"[Calibration] Error capturing pixel at ({x}, {y}): {e}")
                    continue
        
        # Release mouse up at the end
        pyautogui.mouseUp(button='left')
        
        print(f"[Calibration] Calibration complete. Mapped {len(self.color_calibration_map)} colors.")
        
        return self.color_calibration_map
    
    def save_color_calibration(self, filepath: str) -> bool:
        """
        Save the color calibration map to a JSON file.
        
        Parameters:
            filepath: Path to the JSON file to save
        
        Returns:
            True on success, False on failure
        """
        if self.color_calibration_map is None:
            print("[Calibration] No calibration data to save.")
            return False
        
        try:
            # Convert tuple keys to string format for JSON compatibility
            calibration_json = {}
            for (r, g, b), (x, y) in self.color_calibration_map.items():
                key = f"{r},{g},{b}"
                calibration_json[key] = [x, y]
            
            # Save to file
            with open(filepath, 'w') as f:
                json.dump(calibration_json, f, indent=2)
            
            print(f"[Calibration] Calibration data saved to: {filepath}")
            return True
        except Exception as e:
            print(f"[Calibration] Error saving calibration data: {e}")
            return False
    
    def load_color_calibration(self, filepath: str) -> bool:
        """
        Load color calibration data from a JSON file.
        
        Parameters:
            filepath: Path to the JSON file to load
        
        Returns:
            True on success, False on failure
        """
        try:
            with open(filepath, 'r') as f:
                calibration_json = json.load(f)
            
            # Convert string keys back to tuples
            self.color_calibration_map = {}
            for key, value in calibration_json.items():
                # Parse the key "r,g,b" back to tuple
                r, g, b = map(int, key.split(','))
                self.color_calibration_map[(r, g, b)] = tuple(value)
            
            print(f"[Calibration] Calibration data loaded from: {filepath}")
            print(f"[Calibration] Loaded {len(self.color_calibration_map)} color mappings.")
            return True
        except FileNotFoundError:
            print(f"[Calibration] Calibration file not found: {filepath}")
            return False
        except Exception as e:
            print(f"[Calibration] Error loading calibration data: {e}")
            return False
    
    def get_calibrated_color_position(self, target_rgb: Tuple[int, int, int], tolerance: int = 20) -> Optional[Tuple[int, int]]:
        """
        Find the exact calibrated color position for a target RGB value.
        Uses exact match with tolerance before falling back to nearest color.
        This solves the issue where the bot picks wrong colors (e.g., white instead of yellow).
        
        Parameters:
            target_rgb: Tuple (r, g, b) representing the target color
            tolerance: Maximum color difference to consider a match (default 20)
        
        Returns:
            (x, y) coordinates of the best match, or None if no calibration data exists
        """
        if self.color_calibration_map is None or not self.color_calibration_map:
            return None
        
        # First, try to find exact match within tolerance
        for color, pos in self.color_calibration_map.items():
            diff = abs(color[0] - target_rgb[0]) + abs(color[1] - target_rgb[1]) + abs(color[2] - target_rgb[2])
            if diff <= tolerance:
                # Found exact match within tolerance
                print(f"[Calibration] Exact match found: {target_rgb} ~ {color} (diff={diff}) at {pos}")
                return pos
        
        # If no exact match, find the nearest color (original fallback behavior)
        best_color = min(
            self.color_calibration_map.keys(),
            key=lambda c: math.sqrt(
                (c[0] - target_rgb[0]) ** 2 +
                (c[1] - target_rgb[1]) ** 2 +
                (c[2] - target_rgb[2]) ** 2
            )
        )
        
        # Calculate and log the distance
        distance = math.sqrt(
            (best_color[0] - target_rgb[0]) ** 2 +
            (best_color[1] - target_rgb[1]) ** 2 +
            (best_color[2] - target_rgb[2]) ** 2
        )
        
        print(f"[Calibration] Target: {target_rgb}, Nearest fallback: {best_color}, Distance: {distance:.2f}")
        
        return self.color_calibration_map[best_color]
    
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

            x = xo  # Reset x to start of row
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

        # Load calibration data if file exists but not yet loaded
        if os.path.exists('color_calibration.json') and (self.color_calibration_map is None or not self.color_calibration_map):
            print("[Calibration] Loading calibration data from color_calibration.json")
            self.load_color_calibration('color_calibration.json')

        # Calculate total strokes for progress tracking
        self.total_strokes = sum(len(lines) for lines in cmap.values())
        self.start_time = time.time()
        self.completed_strokes = 0
        
        # Store estimated time in seconds for comparison
        self.estimated_time_seconds = self._estimate_drawing_time_seconds(cmap)
        estimated_str = self._format_time(self.estimated_time_seconds)
        print(f"Estimated drawing time: {estimated_str}")

        for color_idx, (c, lines) in enumerate(cmap.items()):
            # Skip the first color if skip_first_color is enabled
            if color_idx == 0 and self.skip_first_color:
                print(f"[Skip First Color] Skipping first color: {c}")
                continue

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
            # Skip on first color when skip_first_color is enabled
            try:
                nl = self.new_layer
                if nl.get('enabled') and nl.get('coords') and not (color_idx == 0 and self.skip_first_color):
                    nx, ny = nl['coords']
                    print(f"[NewLayer] attempting click at {(nx, ny)} with mods={nl.get('modifiers')}")

                    # Track which modifiers were pressed so we can release them in reverse order
                    pressed_modifiers = []

                    # Press modifiers immediately before the click
                    modifier_keys = [('ctrl', 'ctrl'), ('alt', 'alt'), ('shift', 'shift')]
                    for mod_key, pygui_key in modifier_keys:
                        if nl['modifiers'].get(mod_key):
                            pyautogui.keyDown(pygui_key)
                            pressed_modifiers.append(pygui_key)
                            print(f"[NewLayer] pressed modifier: {pygui_key}")

                    # Click the button with modifiers active
                    print(f"[NewLayer] performing mouseDown at {(nx, ny)}")
                    pyautogui.mouseDown(nx, ny, button='left')
                    time.sleep(0.08)
                    pyautogui.mouseUp(nx, ny, button='left')
                    print(f"[NewLayer] mouse click performed at {(nx, ny)}")

                    # Release modifiers immediately after the click with robust handling
                    for pygui_key in reversed(pressed_modifiers):
                        pyautogui.keyUp(pygui_key)
                        print(f"[NewLayer] released modifier: {pygui_key}")
                        time.sleep(0.05)  # Small delay to ensure each key release is registered

                    # Brute-force release all modifiers as backup (in case tracked list missed any)
                    try:
                        pyautogui.keyUp('shift')
                        time.sleep(0.05)
                        pyautogui.keyUp('alt')
                        time.sleep(0.05)
                        pyautogui.keyUp('ctrl')
                        time.sleep(0.05)
                        print(f"[NewLayer] force-released all modifiers as backup")
                    except:
                        pass

                    # Additional delay to ensure OS processes all key release events
                    time.sleep(0.1)

                    # Wait for the target app to process the click (without modifiers active)
                    time.sleep(0.75)

                    # Wait at least 0.75 seconds before starting to paint to ensure new layer is ready
                    print(f"[NewLayer] waiting 0.75 seconds before painting...")
                    time.sleep(0.75)

            except Exception as e:
                print(f"[NewLayer] Error during new layer creation: {e}")
                # Ensure modifiers are released even if there's an error
                try:
                    pyautogui.keyUp('shift')
                    pyautogui.keyUp('alt')
                    pyautogui.keyUp('ctrl')
                except:
                    pass

            # If Color Button Mode is enabled, click the color button with modifiers before palette selection
            try:
                cb = self.color_button
                if cb.get('enabled') and cb.get('coords'):
                    cx, cy = cb['coords']
                    print(f"[ColorButton] attempting click at {(cx, cy)} with mods={cb.get('modifiers')}, delay={cb.get('delay')}")

                    # Track which modifiers were pressed so we can release them in reverse order
                    pressed_modifiers = []

                    # Press modifiers immediately before the click
                    modifier_keys = [('ctrl', 'ctrl'), ('alt', 'alt'), ('shift', 'shift')]
                    for mod_key, pygui_key in modifier_keys:
                        if cb['modifiers'].get(mod_key):
                            pyautogui.keyDown(pygui_key)
                            pressed_modifiers.append(pygui_key)
                            print(f"[ColorButton] pressed modifier: {pygui_key}")

                    # Click the button with modifiers active
                    print(f"[ColorButton] performing mouseDown at {(cx, cy)}")
                    pyautogui.mouseDown(cx, cy, button='left')
                    time.sleep(0.08)
                    pyautogui.mouseUp(cx, cy, button='left')
                    print(f"[ColorButton] mouse click performed at {(cx, cy)}")

                    # Release modifiers immediately after the click with robust handling
                    for pygui_key in reversed(pressed_modifiers):
                        pyautogui.keyUp(pygui_key)
                        print(f"[ColorButton] released modifier: {pygui_key}")
                        time.sleep(0.05)  # Small delay to ensure each key release is registered

                    # Brute-force release all modifiers as backup (in case tracked list missed any)
                    try:
                        pyautogui.keyUp('shift')
                        time.sleep(0.05)
                        pyautogui.keyUp('alt')
                        time.sleep(0.05)
                        pyautogui.keyUp('ctrl')
                        time.sleep(0.05)
                        print(f"[ColorButton] force-released all modifiers as backup")
                    except:
                        pass

                    # Additional delay to ensure OS processes all key release events
                    time.sleep(0.1)

                    # Wait for the configured delay after clicking the color button
                    delay = cb.get('delay', 0.1)
                    print(f"[ColorButton] waiting {delay} seconds before palette selection...")
                    time.sleep(delay)

            except Exception as e:
                print(f"[ColorButton] Error during color button click: {e}")
                # Ensure modifiers are released even if there's an error
                try:
                    pyautogui.keyUp('shift')
                    pyautogui.keyUp('alt')
                    pyautogui.keyUp('ctrl')
                except:
                    pass

            # DEBUG: Log color selection details
            print(f"[DEBUG] Selecting color: {c}")
            print(f"[DEBUG] Color in palette: {self._palette is not None and c in self._palette.colors}")
            print(f"[DEBUG] Color Button enabled: {self.color_button.get('enabled', False)}")
            print(f"[DEBUG] Custom colors box: {self._custom_colors}")
            
            # Check if palette exists and color is in palette before accessing it
            if self._palette is not None and c in self._palette.colors:
                print(f"[DEBUG] Using palette click at: {self._palette.colors_pos[c]}")
                pyautogui.click(self._palette.colors_pos[c])
            else:
                # Try to find the color in the spectrum map with tolerance
                # Use tolerance of 20 (same as calibration default) to ensure accurate color selection
                spectrum_pos = self.get_calibrated_color_position(c, tolerance=20)
                if spectrum_pos:
                    print(f"[DEBUG] Using spectrum click at: {spectrum_pos}")
                    pyautogui.click(spectrum_pos)
                    # Wait for the application to register the color selection (use same delay as color button)
                    delay = self.color_button.get('delay', 0.1)
                    print(f"[DEBUG] Waiting {delay} seconds after spectrum click...")
                    time.sleep(delay)
                else:
                    # Check if manual color selection occurred (color_button_okay enabled)
                    # If so, skip the keyboard input method since user already selected the color
                    # Also skip if color_calibration.json exists (calibration data available)
                    if not self.color_button_okay.get('enabled', False) and not os.path.exists('color_calibration.json'):
                        # Fallback to keyboard input method
                        try:
                            cc_box = self._custom_colors
                            center_x = cc_box[0] + cc_box[2] // 2
                            center_y = cc_box[1] + cc_box[3] // 2
                            print(f"[DEBUG] Spectrum not available - clicking center of box at: ({center_x}, {center_y})")
                            pyautogui.click((center_x, center_y), clicks=3, interval=.15)
                        except:
                            raise NoCustomColorsError('Bot could not continue because custom colors are not initialized')
                        print(f"[DEBUG] Using keyboard input method - typing RGB: {c}")
                        pyautogui.press('tab', presses=7, interval=.05)
                        for val in c:
                            numbers = (d for d in str(val))
                            for n in numbers:
                                pyautogui.press(str(n))
                            pyautogui.press('tab')
                        pyautogui.press('tab')
                        pyautogui.press('enter')
                        pyautogui.PAUSE = 0.0
                    else:
                        if os.path.exists('color_calibration.json'):
                            print(f"[DEBUG] Color calibration file exists - skipping keyboard input method")
                        else:
                            print(f"[DEBUG] Manual color selection detected - skipping keyboard input method")

            # If Color Button Okay Mode is enabled, click "Set Okay" button after color selection
            try:
                cbo = self.color_button_okay
                if cbo.get('enabled') and cbo.get('coords'):
                    cx, cy = cbo['coords']
                    print(f"[ColorButtonOkay] attempting click at {(cx, cy)} with mods={cbo.get('modifiers')}")

                    # Track which modifiers were pressed so we can release them in reverse order
                    pressed_modifiers = []

                    # Press modifiers immediately before the click
                    modifier_keys = [('ctrl', 'ctrl'), ('alt', 'alt'), ('shift', 'shift')]
                    for mod_key, pygui_key in modifier_keys:
                        if cbo['modifiers'].get(mod_key):
                            pyautogui.keyDown(pygui_key)
                            pressed_modifiers.append(pygui_key)
                            print(f"[ColorButtonOkay] pressed modifier: {pygui_key}")

                    # Click the button with modifiers active
                    print(f"[ColorButtonOkay] performing mouseDown at {(cx, cy)}")
                    pyautogui.mouseDown(cx, cy, button='left')
                    time.sleep(0.08)
                    pyautogui.mouseUp(cx, cy, button='left')
                    print(f"[ColorButtonOkay] mouse click performed at {(cx, cy)}")

                    # Release modifiers immediately after the click with robust handling
                    for pygui_key in reversed(pressed_modifiers):
                        pyautogui.keyUp(pygui_key)
                        print(f"[ColorButtonOkay] released modifier: {pygui_key}")
                        time.sleep(0.05)  # Small delay to ensure each key release is registered

                    # Brute-force release all modifiers as backup (in case tracked list missed any)
                    try:
                        pyautogui.keyUp('shift')
                        time.sleep(0.05)
                        pyautogui.keyUp('alt')
                        time.sleep(0.05)
                        pyautogui.keyUp('ctrl')
                        time.sleep(0.05)
                        print(f"[ColorButtonOkay] force-released all modifiers as backup")
                    except:
                        pass

                    # Additional delay to ensure OS processes all key release events
                    time.sleep(0.1)

                    # Wait for the configured delay after clicking the "Set Okay" button (use same delay as Color Button)
                    delay = self.color_button_okay.get('delay', 0.1)
                    print(f"[ColorButtonOkay] waiting {delay} seconds before starting to draw...")
                    time.sleep(delay)

            except Exception as e:
                print(f"[ColorButtonOkay] Error during color button okay click: {e}")
                # Ensure modifiers are released even if there's an error
                try:
                    pyautogui.keyUp('shift')
                    pyautogui.keyUp('alt')
                    pyautogui.keyUp('ctrl')
                except:
                    pass

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
                    # Ensure any stuck modifier keys are released during pause
                    try:
                        pyautogui.keyUp('shift')
                        pyautogui.keyUp('alt')
                        pyautogui.keyUp('ctrl')
                    except:
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

                # Calculate distance
                dx = end_pos[0] - start_pos[0]
                dy = end_pos[1] - start_pos[1]
                distance = (dx**2 + dy**2)**0.5

                if distance < 1:  # Very short line
                    pyautogui.moveTo(start_pos)
                    pyautogui.dragTo(end_pos[0], end_pos[1], 0, button='left')
                else:
                    # Break into segments for smooth drawing
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
                        # Calculate next position
                        t = i / segments
                        next_x = start_pos[0] + dx * t
                        next_y = start_pos[1] + dy * t

                        pyautogui.moveTo(next_x, next_y)
                        time.sleep(segment_delay / segments)  # Distribute delay

                    pyautogui.mouseUp()

                # Check for pause after completing the stroke
                if self.paused or self.terminate:
                    # Save current state for resume
                    self.draw_state['color_idx'] = color_idx
                    self.draw_state['line_idx'] = line_idx
                    self.draw_state['segment_idx'] = 0  # Stroke completed, so reset segment
                    self.draw_state['current_color'] = c  # Save current color
                    if self.terminate:
                        return 'terminated'
                    # Wait for resume
                    print("Paused after completing stroke - press resume to continue")
                    while self.paused and not self.terminate:
                        time.sleep(0.1)
                    if self.terminate:
                        return 'terminated'
                    # Resume - replay the current stroke to ensure clean result
                    print(f"Resuming - replaying current stroke for color {c}")
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
        
        print("=" * 50)
        print(f"Drawing completed!")
        print(f"Estimated: {estimated_str}")
        print(f"Actual:   {actual_str}")
        print(f"{diff_str}")
        print("=" * 50)
        
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

        # Load calibration data if file exists but not yet loaded
        if os.path.exists('color_calibration.json') and (self.color_calibration_map is None or not self.color_calibration_map):
            print("[Calibration] Loading calibration data from color_calibration.json")
            self.load_color_calibration('color_calibration.json')

        # Estimate time for the full cmap (not just test lines)
        self.estimated_time_seconds = self._estimate_drawing_time_seconds(cmap)
        estimated_str = self._format_time(self.estimated_time_seconds)
        print(f"Estimated drawing time (full): {estimated_str}")

        for color_idx, (c, lines) in enumerate(cmap.items()):
            if lines_drawn >= max_lines:
                break

            # Log color change
            print(f"Switching to color {c} for test draw")

            # Check if palette exists and color is in palette before accessing it
            if self._palette is not None and c in self._palette.colors:
                pyautogui.click(self._palette.colors_pos[c])
            else:
                # Try to find the color in the spectrum map
                spectrum_pos = self._find_nearest_spectrum_color(c)
                if spectrum_pos:
                    pyautogui.click(spectrum_pos)
                    # Wait for the application to register the color selection (use same delay as color button)
                    delay = self.color_button.get('delay', 0.1)
                    time.sleep(delay)
                else:
                    # Check if manual color selection occurred (color_button_okay enabled)
                    # If so, skip the keyboard input method since user already selected the color
                    # Also skip if color_calibration.json exists (calibration data available)
                    if not self.color_button_okay.get('enabled', False) and not os.path.exists('color_calibration.json'):
                        # Fallback to keyboard input method
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
                    else:
                        if os.path.exists('color_calibration.json'):
                            print(f"[DEBUG] Color calibration file exists - skipping keyboard input method")
                        else:
                            print(f"[DEBUG] Manual color selection detected - skipping keyboard input method")

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
                    pyautogui.dragTo(end_pos[0], end_pos[1], 0.2, button='left')
                else:
                    # Simple drag for test draw with moderate speed
                    pyautogui.moveTo(start_pos)
                    pyautogui.dragTo(end_pos[0], end_pos[1], 0.2, button='left')
                    time.sleep(0.2)  # Delay between strokes

        # Show time comparison for test draw
        actual_time = time.time() - self.start_time
        actual_str = self._format_time(actual_time)
        
        # Calculate difference (positive = saved time, negative = extra time)
        diff_seconds = self.estimated_time_seconds - actual_time
        if diff_seconds >= 0:
            diff_str = f"Saved: {self._format_time(diff_seconds)}"
        else:
            diff_str = f"Extra: {self._format_time(abs(diff_seconds))}"
        
        print("=" * 50)
        print(f"Test draw completed: {lines_drawn} lines drawn")
        print(f"Estimated (full): {self._format_time(self.estimated_time_seconds)}")
        print(f"Actual (test):   {actual_str}")
        print(f"{diff_str}")
        print("=" * 50)
        
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

    def _estimate_drawing_time_seconds(self, cmap):
        """Estimate drawing time in seconds (internal helper method)"""
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

            return estimated_seconds

        except Exception:
            return 0.0

    def _format_time(self, seconds):
        """Format seconds into a human-readable time string"""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}:{secs:02d}"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}:{minutes:02d}h"

    def estimate_drawing_time(self, cmap):
        """Estimate how long drawing might take based on coordinate data"""
        try:
            estimated_seconds = self._estimate_drawing_time_seconds(cmap)

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
        except:
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
            x = xo  # Initialize x for the loop
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
            x = xo  # Initialize x for the loop

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
        start = xo, y_start

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
                    end = (x, y_start)
                    if mode is Bot.SLOTTED and not (old_col == (255, 255, 255) and flags & Bot.IGNORE_WHITE):
                        lines = cmap.get(old_col, [])
                        lines.append( (start, end) )
                        cmap[old_col] = lines
                    if mode is Bot.LAYERED:
                        table_lines[i].append((old_col, (start, end)))
                        table_colors[i].add(old_col)
                        col_freq[old_col] = col_freq.get(old_col, 0) + end[0] - start[0] + 1
                    start = (xo, y_start + step) if j == w - 1 else (x + step, y_start)

                self.progress = 100 * (i * w + (j + 1)) / (w * h)

                old_col = col
                x += step

            x = xo
            y_start += step

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

    def simple_test_draw(self):
        '''
        Simple test draw that draws 5 horizontal lines starting from the
        upper-left corner of the canvas. Each line is 1/4 of the canvas width.
        No color picking - user should manually set their desired color first.
        Useful for quickly adjusting brush size.
        '''
        try:
            canvas_x, canvas_y, canvas_w, canvas_h = self._canvas
        except:
            raise NoCanvasError('Bot could not continue because canvas is not initialized')

        self.drawing = True
        print("Starting simple test draw...")

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

            print(f"Drawing line {i + 1}/5: from ({start_x}, {start_y}) to ({end_x}, {end_y})")

            # Move to start position
            pyautogui.moveTo(start_x, start_y)
            time.sleep(0.1)

            # Draw the line
            pyautogui.mouseDown(button='left')
            pyautogui.dragTo(end_x, end_y, 0.2, button='left')
            pyautogui.mouseUp()

            # Small delay between lines
            time.sleep(0.2)

        print("Simple test draw completed!")
        self.drawing = False
        return 'success'

    def get_cached_status(self, image_path, flags=0, mode=LAYERED):
        """Check if valid cached computation exists"""
        cache_file = self.get_cache_filename(image_path, flags, mode)
        if cache_file is None:
            return False, None
        cache_data = self.load_cached(cache_file)
        return cache_data is not None, cache_file
