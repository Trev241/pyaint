# Pyaint API Reference

Complete API documentation for Pyaint's core components.

## Table of Contents

- [Bot Module](#bot-module)
- [Window Module](#window-module)
- [SetupWindow Module](#setupwindow-module)
- [Exceptions Module](#exceptions-module)
- [Utilities](#utilities)

---

## Bot Module

### Classes

#### `Palette`

Color palette handler for detecting and matching colors.

```python
class Palette:
    def __init__(self, colors_pos=None, box=None, rows=None, columns=None, 
                 valid_positions=None, manual_centers=None)
    def nearest_color(self, query):
        return min(self.colors, key=lambda color: Palette.dist(color, query))
    
    @staticmethod
    def dist(colx, coly):
        return sum((s - q) ** 2 for s, q in zip(colx, coly))
```

**Constructor Parameters:**

| Parameter | Type | Description |
|-----------|--------|-------------|
| `colors_pos` | dict | Pre-defined color positions {RGB: (x, y)}. Mutually exclusive with box/rows/columns |
| `box` | tuple | Palette bounding box (left, top, width, height) |
| `rows` | int | Number of rows in palette grid |
| `columns` | int | Number of columns in palette grid |
| `valid_positions` | set | Indices of valid palette cells |
| `manual_centers` | dict | Manual center points {index: (x, y)} |

**Attributes:**

| Attribute | Type | Description |
|-----------|--------|-------------|
| `colors_pos` | dict | Mapping of RGB tuples to screen coordinates |
| `colors` | set | Set of available RGB colors |
| `box` | tuple | Palette bounding box |
| `rows` | int | Number of rows |
| `columns` | int | Number of columns |
| `_csizex` | int | Width of each cell (internal) |
| `_csizey` | int | Height of each cell (internal) |

**Methods:**

##### `nearest_color(query)`

Find the nearest color in palette to the target color.

**Parameters:**
- `query` (tuple) - Target RGB color (r, g, b)

**Returns:** tuple - Nearest matching RGB color

##### `dist(colx, coly)` (static)

Calculate squared Euclidean distance between two RGB colors.

**Parameters:**
- `colx` (tuple) - First color (r, g, b)
- `coly` (tuple) - Second color (r, g, b)

**Returns:** float - Squared distance

**Note:** Square root is avoided for performance since comparison order is unchanged.

---

#### `Bot`

Main drawing engine handling image processing and mouse automation.

```python
class Bot:
    # Constants
    SLOTTED = 'slotted'
    LAYERED = 'layered'
    IGNORE_WHITE = 1 << 0
    USE_CUSTOM_COLORS = 1 << 1
    
    # Settings indices
    DELAY, STEP, ACCURACY, JUMP_DELAY = tuple(i for i in range(4))
    
    def __init__(self, config_file='config.json')
    def init_palette(self, colors_pos=None, prows=None, pcols=None,
                   pbox=None, valid_positions=None, manual_centers=None)
    def init_canvas(self, cabox)
    def init_custom_colors(self, ccbox)
    def _scan_spectrum(self, ccbox)
    def _find_nearest_spectrum_color(self, target_color)
    def calibrate_custom_colors(self, grid_box, preview_point, step=2)
    def save_color_calibration(self, filepath)
    def load_color_calibration(self, filepath)
    def get_calibrated_color_position(self, target_rgb, tolerance=20, k_neighbors=4)
    def process(self, file, flags=0, mode=LAYERED)
    def process_region(self, file, region, flags=0, mode=LAYERED, canvas_target=None)
    def draw(self, cmap)
    def test_draw(self, cmap, max_lines=20)
    def simple_test_draw(self)
    def precompute(self, image_path, flags=0, mode=LAYERED)
    def get_cache_filename(self, image_path, flags=0, mode=LAYERED)
    def load_cached(self, cache_file)
    def get_cached_status(self, image_path, flags=0, mode=LAYERED)
    def estimate_drawing_time(self, cmap)
    def _estimate_drawing_time_seconds(self, cmap)
    def _format_time(self, seconds)
```

**Constants:**

| Constant | Value | Description |
|----------|---------|-------------|
| `SLOTTED` | 'slotted' | Simple color-to-lines mode |
| `LAYERED` | 'layered' | Advanced color layering mode |
| `IGNORE_WHITE` | 1 << 0 | Flag to skip white pixels |
| `USE_CUSTOM_COLORS` | 1 << 1 | Flag to use custom colors |

**Settings Indices:**

| Index | Name | Default | Range | Description |
|-------|-------|---------|-------------|
| 0 | `DELAY` | 0.1 | 0.01-10.0s | Stroke timing delay |
| 1 | `STEP` | 12 | 3-50 | Pixel size step |
| 2 | `ACCURACY` | 0.9 | 0.0-1.0 | Color precision |
| 3 | `JUMP_DELAY` | 0.5 | 0.0-2.0s | Delay for cursor jumps > 5px |

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|--------|----------|-------------|
| `config_file` | str | 'config.json' | Path to configuration file |

**Instance Attributes:**

| Attribute | Type | Description |
|-----------|--------|-------------|
| `terminate` | bool | Flag to stop drawing |
| `paused` | bool | Pause/resume state |
| `pause_key` | str | Key for pause/resume (default: 'p') |
| `settings` | list | [delay, step, accuracy, jump_delay] |
| `progress` | float | Processing progress (0-100) |
| `options` | int | Drawing flags |
| `drawing` | bool | Flag indicating if bot is actively drawing |
| `draw_state` | dict | State for pause/resume recovery |
| `skip_first_color` | bool | Flag to skip first color when drawing (default: False) |
| `new_layer` | dict | New layer configuration |
| `color_button` | dict | Color button configuration |
| `color_button_okay` | dict | Color button okay configuration |
| `mspaint_mode` | dict | MSPaint mode configuration |
| `total_strokes` | int | Total number of strokes for progress tracking |
| `completed_strokes` | int | Number of completed strokes |
| `start_time` | float | Timestamp when drawing started |
| `estimated_time_seconds` | float | Estimated drawing time in seconds |
| `_canvas` | tuple | Canvas box (x, y, w, h) |
| `_palette` | Palette | Palette object |
| `_custom_colors` | tuple | Custom colors box |
| `_spectrum_map` | dict | Color spectrum mappings |
| `color_calibration_map` | dict | Color calibration data |

**New Layer Configuration:**

```python
bot.new_layer = {
    'enabled': bool,      # Whether feature is active
    'coords': (x, y),     # Button location
    'modifiers': {
        'ctrl': bool,
        'alt': bool,
        'shift': bool
    }
}
```

**Color Button Configuration:**

```python
bot.color_button = {
    'status': bool,        # Whether configured
    'coords': (x, y),     # Button location
    'enabled': bool,       # Whether active
    'delay': float,        # Delay after click (0.01-5.0s)
    'modifiers': {
        'ctrl': bool,
        'alt': bool,
        'shift': bool
    }
}
```

**Color Button Okay Configuration:**

```python
bot.color_button_okay = {
    'status': bool,        # Whether configured
    'coords': (x, y),     # Button location
    'enabled': bool,       # Whether active
    'delay': float,        # Delay after click (0.01-5.0s)
    'modifiers': {
        'ctrl': bool,
        'alt': bool,
        'shift': bool
    }
}
```

**Draw State for Pause/Resume:**

```python
bot.draw_state = {
    'color_idx': int,       # Current color index
    'line_idx': int,        # Current line index
    'segment_idx': int,     # Current segment index
    'current_color': tuple,  # Current RGB color
    'was_paused': bool      # Whether currently paused
}
```

**Methods:**

##### `init_palette(pbox, prows, pcols, valid_positions=None, manual_centers=None)`

Initialize color palette from screen capture.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|--------|-----------|-------------|
| `pbox` | tuple | Yes* | Palette box (left, top, width, height) |
| `prows` | int | Yes* | Number of rows |
| `pcols` | int | Yes* | Number of columns |
| `valid_positions` | set | Optional | Valid cell indices |
| `manual_centers` | dict | Optional | Manual center points |

\* Required if `colors_pos` not provided

**Returns:** `Palette` object

**Raises:** `NoPaletteError`

**Example:**
```python
palette = bot.init_palette(
    pbox=(100, 100, 200, 150),
    prows=4,
    pcols=8,
    valid_positions={0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11},
    manual_centers={0: (125, 125), 1: (175, 125)}
)
```

##### `init_canvas(cabox)`

Define canvas drawing area.

**Parameters:**
- `cabox` (tuple) - Canvas box (x1, y1, x2, y2)

**Raises:** `NoCanvasError`

**Example:**
```python
bot.init_canvas((300, 200, 1500, 900))
```

##### `init_custom_colors(ccbox)`

Configure custom color spectrum and scan for color map.

**Parameters:**
- `ccbox` (tuple) - Custom colors box (x1, y1, x2, y2)

**Side Effects:**
- Creates `_spectrum_map` attribute
- Samples spectrum at regular intervals

**Example:**
```python
bot.init_custom_colors((1800, 100, 1900, 400))
# Now bot._spectrum_map contains color → position mappings
```

##### `calibrate_custom_colors(grid_box, preview_point, step=2)`

Scan custom colors grid and record RGB values shown in preview point.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|--------|----------|-------------|
| `grid_box` | tuple/list | - | Spectrum box [x1, y1, x2, y2] |
| `preview_point` | tuple/list | - | Preview point [x, y] |
| `step` | int | 2 | Pixel step for scanning |

**Returns:** dict - RGB → (x, y) mapping

**Behavior:**
1. Resets `terminate` flag
2. Presses mouse down at grid start
3. Drags through entire spectrum
4. Captures RGB from preview point at each step
5. Stores mapping in `color_calibration_map`
6. Can be cancelled with ESC key

**Example:**
```python
calibration_map = bot.calibrate_custom_colors(
    grid_box=(1800, 100, 1900, 400),
    preview_point=(1850, 450),
    step=2
)
print(f"Calibrated {len(calibration_map)} colors")
```

##### `save_color_calibration(filepath)`

Save color calibration data to JSON file.

**Parameters:**
- `filepath` (str) - Path to save file

**Returns:** bool - True on success, False on failure

**Format:**
```json
{
    "r,g,b": [x, y],
    "255,0,0": [1825, 250],
    ...
}
```

**Example:**
```python
success = bot.save_color_calibration('color_calibration.json')
if success:
    print("Calibration saved successfully")
```

##### `load_color_calibration(filepath)`

Load color calibration data from JSON file.

**Parameters:**
- `filepath` (str) - Path to load file

**Returns:** bool - True on success, False on failure

**Example:**
```python
success = bot.load_color_calibration('color_calibration.json')
if success:
    print(f"Loaded {len(bot.color_calibration_map)} color mappings")
```

##### `get_calibrated_color_position(target_rgb, tolerance=20, k_neighbors=4)`

Find exact calibrated color position with tolerance fallback.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|--------|----------|-------------|
| `target_rgb` | tuple | - | Target color (r, g, b) |
| `tolerance` | int | 20 | Maximum color difference for match |
| `k_neighbors` | int | 4 | Number of nearest colors to use for interpolation |

**Returns:** tuple or None - (x, y) coordinates or None

**Behavior:**
1. First searches for exact match within tolerance
2. If no exact match, finds nearest color
3. Returns coordinates for best match

**Example:**
```python
pos = bot.get_calibrated_color_position((255, 128, 0), tolerance=20)
if pos:
    print(f"Click at: {pos}")
```

##### `process(file, flags=0, mode=LAYERED)`

Convert image to coordinate map for drawing.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|--------|----------|-------------|
| `file` | str | - | Path to image file |
| `flags` | int | 0 | Drawing options (IGNORE_WHITE \| USE_CUSTOM_COLORS) |
| `mode` | str | LAYERED | 'slotted' or 'layered' |

**Returns:** dict - Mapping of colors to line segments

**Processing Steps:**
1. Load image with Pillow
2. Calculate resize dimensions to fit canvas
3. Resize image to appropriate size
4. Scan pixels at step size intervals
5. For each pixel:
   - Map to nearest palette color (or calibrate)
   - Track line segments (horizontal runs)
6. In LAYERED mode:
   - Sort colors by frequency
   - Merge adjacent lines of lower-frequency colors

**Return Format:**
```python
{
    (r, g, b): [
        ((x1, y1), (x2, y2)),  # Line segment
        ((x3, y3), (x4, y4)),
        ...
    ],
    ...
}
```

**Example:**
```python
cmap = bot.process('image.png', flags=Bot.IGNORE_WHITE, mode=Bot.LAYERED)
for color, lines in cmap.items():
    print(f"Color {color}: {len(lines)} lines")
```

##### `process_region(file, region, flags=0, mode=LAYERED, canvas_target=None)`

Process specific region of an image for redraw.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|--------|----------|-------------|
| `file` | str | - | Path to image file |
| `region` | tuple | - | Image region (x1, y1, x2, y2) |
| `flags` | int | 0 | Drawing options |
| `mode` | str | LAYERED | Processing mode |
| `canvas_target` | tuple/dict | None | Target canvas area - either tuple `(x, y, w, h)` or dict with keys `'x'`, `'y'`, `'width'`, `'height'` |

**Returns:** dict - Color map for region

**Behavior:**
1. Crops image to specified region
2. Scales to fit canvas or canvas_target
3. Processes like full image
4. Centers on canvas or canvas_target

**Example:**
```python
region_cmap = bot.process_region(
    'image.png',
    region=(100, 100, 300, 300),
    canvas_target=(100, 100, 200, 200)
)
```

##### `draw(cmap)`

Execute full drawing from coordinate map.

**Parameters:**
- `cmap` (dict) - Color map from `process()` or `process_region()`

**Returns:** str - 'success', 'terminated', or 'paused'

**Drawing Process:**
1. Resets `terminate`, `paused`, `drawing` flags
2. Calculates estimated time
3. For each color:
   - If New Layer enabled: clicks new layer button
   - If Color Button enabled: clicks color button with delay
   - Selects color (palette or calibrated)
   - If Color Button Okay enabled: clicks confirmation
   - Draws all line segments
   - Supports jump delay for cursor movements > 5px
   - Segments long lines for smooth drawing
   - Supports pause/resume with state recovery
4. Reports actual vs estimated time

**Example:**
```python
result = bot.draw(cmap)
if result == 'success':
    print("Drawing completed!")
elif result == 'terminated':
    print("Drawing stopped by user")
elif result == 'paused':
    print("Drawing paused")
```

##### `test_draw(cmap, max_lines=20)`

Draw sample lines for brush calibration.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|--------|----------|-------------|
| `cmap` | dict | - | Color map |
| `max_lines` | int | 20 | Maximum lines to draw |

**Returns:** str - 'success' or 'terminated'

**Behavior:**
- Draws first `max_lines` lines across all colors
- Includes color switching
- Uses calibrated colors if available
- Shows time comparison

**Example:**
```python
result = bot.test_draw(cmap, max_lines=20)
if result == 'success':
    print("Test draw completed")
```

##### `simple_test_draw()`

Quick 5-line test for brush size calibration.

**Returns:** str - 'success' or 'terminated'

**Behavior:**
- No color picking (uses current brush color)
- Draws 5 horizontal lines from canvas upper-left
- Each line is 1/4 canvas width
- Lines spaced by pixel size setting

**Example:**
```python
result = bot.simple_test_draw()
if result == 'success':
    print("Simple test completed. Adjust brush size as needed.")
```

##### `precompute(image_path, flags=0, mode=LAYERED)`

Pre-process and cache image for faster subsequent runs.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|--------|----------|-------------|
| `image_path` | str | - | Path to image file |
| `flags` | int | 0 | Drawing options |
| `mode` | str | LAYERED | Processing mode |

**Returns:** str - Cache file path

**Cache File Format:**
```
cache/{image_hash}_{settings_hash}.json
```

**Cache Contents:**
```json
{
    "cmap": {...},
    "settings": [...],
    "flags": 0,
    "mode": "layered",
    "canvas": [...],
    "image_hash": "abc12345",
    "timestamp": 1234567890.0,
    "palette_info": {...}
}
```

**Example:**
```python
cache_file = bot.precompute('image.png', mode=Bot.LAYERED)
print(f"Cache saved to: {cache_file}")
```

##### `get_cache_filename(image_path, flags=0, mode=LAYERED)`

Generate cache file path based on image and settings.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|--------|----------|-------------|
| `image_path` | str | - | Path to image file |
| `flags` | int | 0 | Drawing options |
| `mode` | str | LAYERED | Processing mode |

**Returns:** str or None - Cache file path or None if canvas not initialized

**Example:**
```python
cache_path = bot.get_cache_filename('image.png', mode=Bot.LAYERED)
if cache_path:
    print(f"Cache path: {cache_path}")
```

##### `load_cached(cache_file)`

Load and validate cached computation.

**Parameters:**
- `cache_file` (str) - Path to cache file

**Returns:** dict or None - Cache data or None if invalid

**Validation:**
- Required keys present
- Cache age < 24 hours
- Settings match current configuration
- Canvas dimensions match

**Example:**
```python
cache_data = bot.load_cached('cache/abc123_456def.json')
if cache_data:
    cmap = cache_data['cmap']
    print(f"Loaded {len(cmap)} colors from cache")
```

##### `get_cached_status(image_path, flags=0, mode=LAYERED)`

Check if valid cache exists for image.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|--------|----------|-------------|
| `image_path` | str | - | Path to image file |
| `flags` | int | 0 | Drawing options |
| `mode` | str | LAYERED | Processing mode |

**Returns:** tuple - (bool, str or None) - (has_cache, cache_file)

**Example:**
```python
has_cache, cache_file = bot.get_cached_status('image.png')
if has_cache:
    print(f"Cache available: {cache_file}")
else:
    print("No cache found")
```

##### `estimate_drawing_time(cmap)`

Calculate estimated drawing time from coordinate map.

**Parameters:**
- `cmap` (dict) - Color map

**Returns:** str - Human-readable time string

**Format Examples:**
- "~15.3 seconds"
- "~2:30 minutes"
- "~1:45 hours"

**Calculation:**
- Sum of stroke delays
- Jump delays for movements > 5px
- Color switching overhead (~0.5s per color)

**Example:**
```python
eta = bot.estimate_drawing_time(cmap)
print(f"Estimated time: {eta}")
```

##### `_estimate_drawing_time_seconds(cmap)`

Internal method to calculate drawing time in seconds.

**Parameters:**
- `cmap` (dict) - Color map

**Returns:** float - Estimated time in seconds

##### `_format_time(seconds)`

Internal method to format seconds to human-readable string.

**Parameters:**
- `seconds` (float) - Time in seconds

**Returns:** str - Formatted time string

---

## Window Module

### `Window`

Main GUI application window.

```python
class Window:
    _SLIDER_TOOLTIPS = (...)
    _MISC_TOOLTIPS = (...)
    
    def __init__(self, title, bot, w, h, x, y)
    def setup(self)
    def start_precompute_thread(self)
    def start_test_draw_thread(self)
    def start_simple_test_draw_thread(self)
    def start_draw_thread(self)
    def start_calibration_thread(self)
    def load_config(self)
    def _on_search_img(self)
    def _on_redraw_pick(self)
    def _redraw_draw_thread(self)
    def redraw_region(self)
    def simple_test_draw(self)
    def start(self)
    def test_draw(self)
```

**Constructor Parameters:**

| Parameter | Type | Description |
|-----------|--------|-------------|
| `title` | str | Window title |
| `bot` | Bot | Bot instance |
| `w`, `h` | int | Window dimensions |
| `x`, `y` | int | Window position |

**UI Layout:**
- Left panel: Drawing settings and actions
- Right panel: Image preview
- Bottom panel: Status messages and progress

**Drawing Settings:**

| Setting | Range | Description |
|---------|--------|-------------|
| Delay | 0.01-10.0s | Stroke timing |
| Pixel Size | 3-50 | Detail level (integer) |
| Precision | 0.0-1.0 | Color accuracy |
| Jump Delay | 0.0-2.0s | Cursor jump delay |
| Calibration Step | 1-10 | Pixel step for calibration |

**Drawing Modes:**
- **Slotted**: Simple color-to-lines mapping
- **Layered**: Advanced color layering (default)

**Drawing Options:**
- Ignore White Pixels
- Use Custom Colors
- Skip First Color
- Enable New Layer
- Enable Color Button
- Enable Color Button Okay

**Action Buttons:**
- **Setup**: Configure tools
- **Run Calibration**: Scan custom colors
- **Pre-compute**: Cache image processing
- **Test Draw**: Draw sample lines
- **Simple Test Draw**: Quick brush test
- **Start**: Begin full drawing
- **Redraw Region**: Draw selected area

**Key Methods:**

##### `setup()`

Open setup configuration window for tool initialization.

##### `start_precompute_thread()`

Start pre-computation in background thread.

##### `start_test_draw_thread()`

Start test draw in background thread.

##### `start_simple_test_draw_thread()`

Start simple test draw in background thread.

##### `start_draw_thread()`

Start full drawing in background thread.

##### `start_calibration_thread()`

Start color calibration process in background thread.

##### `load_config()`

Load settings from `config.json` and apply to UI and bot.

**Loaded Settings:**
- Drawing settings (delay, pixel_size, precision, jump_delay)
- Drawing options (ignore_white, use_custom_colors)
- Pause key
- Calibration step size
- Tool configurations (palette, canvas, custom colors, new layer, color button, etc.)
- Last image URL

##### `_on_search_img()`

Load image from URL or local file path.

**Supports:**
- Remote URLs with proper headers
- Local file paths
- Error handling with user feedback

##### `_on_redraw_pick()`

Start region selection mode for redraw.

##### `_redraw_draw_thread()`

Start redraw region drawing in background thread.

##### `redraw_region()`

Process and draw selected image region.

##### `simple_test_draw()`

Execute simple test draw with user dialog.

##### `start()`

Execute full drawing with time tracking and comparison.

##### `test_draw()`

Execute test draw with cache support.

---

## SetupWindow Module

### `SetupWindow`

Configuration wizard for tool initialization.

```python
class SetupWindow:
    def __init__(self, parent, bot, tools, on_complete, 
                 title='Child Window', w=700, h=800, x=5, y=5)
    def _start_listening(self, name, tool)
    def _start_manual_color_selection(self, name, tool)
    def _open_color_selection_window(self)
    def _toggle_grid_cell(self, index)
    def _set_toggle_mode(self)
    def _set_pick_centers_mode(self)
    def _pick_center(self, index)
    def _auto_estimate_centers(self)
    def _start_precision_estimate(self)
    def _show_centers_overlay(self)
    def _show_custom_centers_overlay(self)
    def _select_all_colors(self)
    def _deselect_all_colors(self)
    def _on_color_selection_done(self)
    def _on_click(self, x, y, _, pressed)
    def _on_center_pick_click(self, x, y, _, pressed)
    def _on_precision_pick_click(self, x, y, _, pressed)
    def _calculate_precision_centers(self)
    def _show_precision_dialog(self, instructions_list)
    def _on_escape_press(self, event)
    def _validate_dimensions(self, value)
    def _on_invalid_dimensions(self)
    def _on_update_dimensions(self, event)
    def _validate_delay(self, value)
    def _on_invalid_delay(self)
    def _on_update_delay(self, event)
    def _on_enable_toggle(self, tool_name, intvar)
    def _on_modifier_toggle(self, tool_name, modifier_name, intvar)
    def close(self)
```

**Supported Tools:**
- Palette (with advanced color selection)
- Canvas
- Custom Colors
- New Layer
- Color Button
- Color Button Okay
- Color Preview Spot

**Palette Features:**
1. **Toggle Mode** - Mark cells valid/invalid
2. **Pick Centers Mode** - Click exact center points
3. **Auto-Estimate** - Calculate grid-based centers
4. **Precision Estimate** - Reference point calculation:
   - Single Column Mode (vertical palettes)
   - 1 Row Mode (horizontal palettes)
   - Multi-Row Mode (grid palettes)
5. **Select All / Deselect All** - Batch operations
6. **Show Custom Centers** - Overlay verification

**Modifier Keys:**
Supported for: New Layer, Color Button, Color Button Okay, Color Preview Spot
- CTRL
- ALT
- SHIFT

---

## Exceptions Module

### Exception Classes

```python
class NoToolError(Exception):
    pass

class CorruptConfigError(Exception):
    pass

class NoPaletteError(NoToolError):
    pass

class NoCanvasError(NoToolError):
    pass

class NoCustomColorsError(NoToolError):
    pass
```

**Exception Hierarchy:**

```
Exception
├── NoToolError
│   ├── NoPaletteError
│   ├── NoCanvasError
│   └── NoCustomColorsError
└── CorruptConfigError
```

**Usage:**

```python
from exceptions import NoPaletteError, NoCanvasError

try:
    bot.process('image.png')
except NoPaletteError:
    print("Please initialize palette first")
except NoCanvasError:
    print("Please initialize canvas first")
```

---

## Utilities

### `adjusted_img_size(img, ad)`

Calculate image dimensions to fit within available space.

**Parameters:**
- `img` (PIL.Image) - Source image
- `ad` (tuple) - Available dimensions (width, height)

**Returns:** tuple - (width, height)

**Behavior:**
- Maintains aspect ratio
- Shrinks if either dimension exceeds available space
- May result in dead space if aspect ratios don't match

**Example:**
```python
from PIL import Image
import utils

img = Image.open('large_image.png')
size = utils.adjusted_img_size(img, (500, 400))
# Returns (400, 300) maintaining aspect ratio
```

---

## Configuration File

### `config.json` Structure

```json
{
  "drawing_settings": {
    "delay": 0.15,
    "pixel_size": 12,
    "precision": 0.9,
    "jump_delay": 0.5
  },
  "drawing_options": {
    "ignore_white_pixels": true,
    "use_custom_colors": false
  },
  "pause_key": "p",
  "calibration_settings": {
    "step_size": 2
  },
  "Palette": {
    "status": true,
    "box": [x1, y1, x2, y2],
    "rows": 6,
    "cols": 8,
    "color_coords": {
      "(r,g,b)": [x, y]
    },
    "valid_positions": [0, 1, 2, ...],
    "manual_centers": {
      "0": [x, y]
    },
    "preview": "assets/Palette_preview.png"
  },
  "Canvas": {
    "status": true,
    "box": [x1, y1, x2, y2],
    "preview": "assets/Canvas_preview.png"
  },
  "Custom Colors": {
    "status": true,
    "box": [x1, y1, x2, y2],
    "preview": "assets/Custom Colors_preview.png"
  },
  "New Layer": {
    "status": true,
    "coords": [x, y],
    "enabled": false,
    "modifiers": {
      "ctrl": false,
      "alt": false,
      "shift": false
    }
  },
  "Color Button": {
    "status": true,
    "coords": [x, y],
    "enabled": false,
    "delay": 0.5,
    "modifiers": {
      "ctrl": false,
      "alt": false,
      "shift": false
    }
  },
  "Color Button Okay": {
    "status": true,
    "coords": [x, y],
    "enabled": false,
    "modifiers": {
      "ctrl": false,
      "alt": false,
      "shift": false
    }
  },
  "color_preview_spot": {
    "name": "Color Preview Spot",
    "status": true,
    "coords": [x, y],
    "enabled": false,
    "modifiers": {
      "ctrl": false,
      "alt": false,
      "shift": false
    }
  },
  "last_image_url": "https://..."
}
```

---

## Global Keyboard Handlers

### `on_pynput_key(key)` (main.py)

Global keyboard listener for pause/resume and termination.

**Behavior:**
- ESC: Sets `bot.terminate = True`
- Pause key: Toggles `bot.paused` when drawing

**Supported Keys:**
- Any regular key (a-z, 0-9)
- Function keys (F1-F12)
- Special keys (arrows, etc.)
