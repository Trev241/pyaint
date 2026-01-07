# Pyaint API Reference

This document provides a comprehensive API reference for all public classes and methods in Pyaint.

## Table of Contents

- [Bot Module](#bot-module)
  - [Palette Class](#palette-class)
  - [Bot Class](#bot-class)
- [UI Module](#ui-module)
  - [Window Class](#window-class)
  - [SetupWindow Class](#setupwindow-class)
- [Exceptions](#exceptions)
- [Utils](#utils)

## Bot Module

### Palette Class

Located in [`bot.py`](../bot.py:16).

#### `__init__(self, colors_pos=None, box=None, rows=None, columns=None, valid_positions=None, manual_centers=None)`

Initialize palette from pre-defined color positions or by scanning a grid.

**Parameters:**
- `colors_pos` (dict, optional) - Pre-defined color positions `{(r,g,b): (x,y)}`
- `box` (tuple, optional) - Palette box `(left, top, width, height)`
- `rows` (int, optional) - Number of grid rows
- `columns` (int, optional) - Number of grid columns
- `valid_positions` (set, optional) - Valid cell indices
- `manual_centers` (dict, optional) - Manual center points `{index: (x,y)}`

**Raises:** `ValueError` if `box`, `rows`, or `columns` missing when `colors_pos` is None

**Attributes:**
- `colors_pos` (dict) - RGB to coordinate mapping
- `colors` (set) - Available RGB tuples
- `box` (tuple) - Palette bounding box
- `rows`, `columns` (int) - Grid dimensions
- `_csizex`, `_csizey` (int) - Cell dimensions

#### `nearest_color(self, query)`

Find the nearest palette color to a target RGB value.

**Parameters:**
- `query` (tuple) - Target RGB color `(r, g, b)`

**Returns:** `tuple` - RGB tuple of nearest color

**Example:**
```python
palette = Palette(box=(0, 0, 100, 100), rows=2, cols=2)
nearest = palette.nearest_color((128, 0, 255))
```

#### `dist(colx, coly)` (static)

Calculate squared Euclidean distance between two RGB colors.

**Parameters:**
- `colx` (tuple) - First RGB color
- `coly` (tuple) - Second RGB color

**Returns:** `int` - Squared distance

**Note:** Square root avoided for performance (order preservation).

---

### Bot Class

Located in [`bot.py`](../bot.py:87).

#### Class Constants

```python
SLOTTED = 'slotted'      # Simple color-to-lines mode
LAYERED = 'layered'      # Advanced color layering mode

IGNORE_WHITE = 1 << 0      # Skip drawing white pixels
USE_CUSTOM_COLORS = 1 << 1  # Enable custom color mixing

# Settings indices
DELAY = 0       # Stroke timing delay
STEP = 1        # Pixel size step
ACCURACY = 2    # Color precision
JUMP_DELAY = 3   # Cursor jump delay
```

#### `__init__(self, config_file='config.json')`

Initialize Bot with default settings.

**Parameters:**
- `config_file` (str) - Path to config file

**Attributes:**
- `terminate` (bool) - Stop drawing when True
- `paused` (bool) - Pause/resume state
- `pause_key` (str) - Key for pause/resume (default: 'p')
- `settings` (list) - `[delay, step, accuracy, jump_delay]`
- `progress` (float) - Processing progress (0-100)
- `options` (int) - Drawing flags
- `drawing` (bool) - Currently drawing flag
- `draw_state` (dict) - State for pause/resume recovery
- `new_layer` (dict) - New layer configuration
- `color_button` (dict) - Color button configuration
- `color_button_okay` (dict) - Color button okay configuration
- `_canvas` (tuple) - Canvas box
- `_palette` (Palette) - Palette instance
- `_custom_colors` (tuple) - Custom colors box
- `_spectrum_map` (dict) - Custom color spectrum mapping

---

#### Initialization Methods

##### `init_palette(self, colors_pos=None, prows=None, pcols=None, pbox=None, valid_positions=None, manual_centers=None)`

Initialize color palette from screen region or pre-defined positions.

**Parameters:**
- `colors_pos` (dict, optional) - Pre-defined color positions
- `prows` (int, optional) - Number of rows
- `pcols` (int, optional) - Number of columns
- `pbox` (tuple, optional) - Palette box `(left, top, width, height)`
- `valid_positions` (set, optional) - Valid cell indices
- `manual_centers` (dict, optional) - Manual center points

**Returns:** [`Palette`](#palette-class) object

**Raises:** [`NoPaletteError`](#exceptions)

**Box Format:** `(left, top, width, height)`

##### `init_canvas(self, cabox)`

Define canvas drawing area.

**Parameters:**
- `cabox` (tuple) - Canvas box `(x1, y1, x2, y2)`

**Raises:** [`NoCanvasError`](#exceptions)

**Box Format:** Converted to `(left, top, width, height)` internally

##### `init_custom_colors(self, ccbox)`

Configure custom color spectrum.

**Parameters:**
- `ccbox` (tuple) - Custom colors box `(x1, y1, x2, y2)`

**Side Effect:** Scans spectrum and creates [`_spectrum_map`](#bot-class) attribute

---

#### Image Processing Methods

##### `process(self, file, flags=0, mode=LAYERED)`

Convert image to coordinate map.

**Parameters:**
- `file` (str) - Path to image file
- `flags` (int) - Drawing options (IGNORE_WHITE | USE_CUSTOM_COLORS)
- `mode` (str) - 'slotted' or 'layered'

**Returns:** `dict` - Color map `{color: [(start, end), ...]}`

**Processing Steps:**
1. Load image with PIL
2. Resize to fit canvas (maintaining aspect ratio)
3. Scan pixels at step size intervals
4. Map each pixel to nearest palette color
5. Generate line segments (horizontal runs of same color)
6. In LAYERED mode: sort colors by frequency and merge lines

##### `process_region(self, file, region, flags=0, mode=LAYERED, canvas_target=None)`

Process specific region of an image.

**Parameters:**
- `file` (str) - Path to image file
- `region` (tuple) - Image region `(x1, y1, x2, y2)`
- `flags` (int) - Drawing options
- `mode` (str) - Processing mode
- `canvas_target` (tuple, optional) - Target canvas area `(x, y, w, h)`

**Returns:** `dict` - Color map for region

---

#### Drawing Methods

##### `draw(self, cmap)`

Execute full drawing from coordinate map with pause/resume support.

**Parameters:**
- `cmap` (dict) - Color map from [`process()`](#processself-file-flags0-modelayered)

**Returns:** `'success'`, `'terminated'`, or `'paused'`

**Features:**
- Progress tracking with time estimation
- Jump delay for cursor movements > 5px
- Stroke segmentation for smooth drawing
- Pause/resume with state recovery
- New layer support (if enabled)
- Color button support (if enabled)
- Color button okay support (if enabled)

**State Recovery:**
```python
self.draw_state = {
    'color_idx': 0,        # Resume from this color
    'line_idx': 0,         # Resume from this line
    'segment_idx': 0,       # Resume from this segment
    'current_color': None,   # Saved color for resume
    'cmap': None             # Saved coordinate map
}
```

##### `test_draw(self, cmap, max_lines=20)`

Draw first N lines for brush calibration.

**Parameters:**
- `cmap` (dict) - Color map
- `max_lines` (int) - Maximum lines to draw (default: 20)

##### `simple_test_draw(self)`

Draw 5 horizontal lines for quick brush calibration.

**Features:**
- No color picking
- Lines drawn at canvas upper-left corner
- Each line is 1/4 of canvas width

---

#### Caching Methods

##### `precompute(self, image_path, flags=0, mode=LAYERED)`

Pre-process and cache image for faster subsequent runs.

**Parameters:**
- `image_path` (str) - Path to image file
- `flags` (int) - Drawing options
- `mode` (str) - Processing mode

**Returns:** `str` - Cache file path

**Cache File:** `cache/{img_hash}_{settings_hash}.json`

##### `get_cache_filename(self, image_path, flags=0, mode=LAYERED)`

Generate unique cache filename based on image and settings.

**Returns:** `str` or `None` (if canvas not initialized)

##### `load_cached(self, cache_file)`

Load and validate cached computation.

**Parameters:**
- `cache_file` (str) - Path to cache file

**Returns:** `dict` or `None` (if invalid)

**Validation:**
- File exists
- Age < 24 hours
- Settings match
- Canvas dimensions match

##### `get_cached_status(self, image_path, flags=0, mode=LAYERED)`

Check if valid cache exists.

**Returns:** `(bool, str or None)` - (has_cache, cache_file_path)

---

#### Estimation Methods

##### `estimate_drawing_time(self, cmap)`

Calculate estimated drawing time based on coordinate data.

**Parameters:**
- `cmap` (dict) - Color map

**Returns:** `str` - Human-readable time string

**Calculation:**
- Sum of stroke delays
- Jump delays for movements > 5px
- Color switching overhead (~0.5s per color)

##### `_estimate_drawing_time_seconds(self, cmap)`

Internal method - returns estimated time in seconds.

##### `_format_time(self, seconds)`

Format seconds to human-readable string.

**Returns:** `str` - e.g., "5:30", "1:45h"

---

## UI Module

### Window Class

Located in [`ui/window.py`](../ui/window.py:58).

#### Class Constants

```python
_SLIDER_TOOLTIPS = (
    # Delay, Pixel Size, Precision, Jump Delay tooltips
)
_MISC_TOOLTIPS = (
    # Ignore white pixels, Use custom colors tooltips
)
```

#### `__init__(self, title, bot, w, h, x, y)`

Create main application window.

**Parameters:**
- `title` (str) - Window title
- `bot` (Bot) - Bot instance
- `w`, `h` (int) - Window dimensions
- `x`, `y` (int) - Window position

**Key Components:**
- Control Panel - Settings and action buttons
- Image Preview Panel - Image loading and display
- Tooltip Panel - Status messages

#### Drawing Settings

**Settings Array:**
```python
self.bot.settings = [
    DELAY,      # [0] 0.01-10.0s
    STEP,        # [1] 3-50 pixels
    ACCURACY,    # [2] 0.0-1.0
    JUMP_DELAY   # [3] 0.0-2.0s
]
```

#### Drawing Options

```python
self.draw_options = 0

# Flags
Bot.IGNORE_WHITE      # Skip white pixels
Bot.USE_CUSTOM_COLORS # Enable custom colors
```

#### Action Methods

##### `setup(self)`

Open setup configuration window.

##### `start_precompute_thread(self)`

Start pre-computation in background thread.

##### `start_test_draw_thread(self)`

Start test draw in background thread.

##### `start_simple_test_draw_thread(self)`

Start simple test draw in background thread.

##### `start_draw_thread(self)`

Start full drawing in background thread.

##### `start(self)`

Begin full drawing process.

**Flow:**
1. Check for cached computation
2. Load cached or process image
3. Show time estimate
4. Minimize window
5. Execute drawing
6. Restore window on completion

#### Redraw Methods

##### `_on_redraw_pick(self)`

Start region selection for redraw.

##### `_redraw_draw_thread(self)`

Draw selected region only.

##### `redraw_region(self)`

Process and draw selected image region.

##### `_canvas_to_image_region(self, canvas_region)`

Convert canvas coordinates to reference image coordinates.

---

### SetupWindow Class

Located in [`ui/setup.py`](../ui/setup.py:29).

#### `__init__(self, parent, bot, tools, on_complete, title='Child Window', w=700, h=800, x=5, y=5)`

Create setup configuration window.

**Parameters:**
- `parent` (Tk) - Parent window
- `bot` (Bot) - Bot instance
- `tools` (dict) - Tool configuration
- `on_complete` (callable) - Callback on completion
- `title` (str) - Window title
- `w`, `h` (int) - Window dimensions
- `x`, `y` (int) - Window position

#### Color Selection Methods

##### `_start_manual_color_selection(self, name, tool)`

Open manual color selection window for palette.

##### `_open_color_selection_window(self)`

Create color selection grid interface.

##### `_toggle_grid_cell(self, index)`

Toggle a grid cell between valid and invalid.

##### `_set_pick_centers_mode(self)`

Set mode to pick exact center points.

##### `_pick_center(self, index)`

Pick a center point for a specific color cell.

##### `_auto_estimate_centers(self)`

Automatically estimate centers for all valid colors.

##### `_start_precision_estimate(self)`

Start precision estimate using reference point selection.

##### `_calculate_precision_centers(self)`

Calculate all centers based on precision estimate reference points.

**Modes:**
- `single_column` - Vertical palettes (3 reference points)
- `1_row` - Horizontal palettes (3 reference points)
- `multi_row` - Grid palettes (5-6 reference points)

##### `_show_centers_overlay(self)`

Display overlay circles showing estimated center positions.

##### `_show_custom_centers_overlay(self)`

Display overlay circles showing manually picked center positions.

---

## Exceptions

Located in [`exceptions.py`](../exceptions.py).

### Exception Hierarchy

```
NoToolError (base)
    ├── NoPaletteError
    ├── NoCanvasError
    └── NoCustomColorsError
CorruptConfigError
```

### Exception Classes

#### `NoToolError(Exception)`

Base exception for tool initialization errors.

#### `CorruptConfigError(Exception)`

Raised when configuration file is invalid or corrupted.

#### `NoPaletteError(NoToolError)`

Raised when palette is not initialized or its dimensions are faulty.

#### `NoCanvasError(NoToolError)`

Raised when canvas is not initialized.

#### `NoCustomColorsError(NoToolError)`

Raised when custom colors are not initialized.

---

## Utils

Located in [`utils.py`](../utils.py).

### `adjusted_img_size(img, ad)`

Recalculate image dimensions to fit within available space while maintaining aspect ratio.

**Parameters:**
- `img` (PIL.Image) - Source image
- `ad` (tuple) - Available space `(width, height)`

**Returns:** `(int, int)` - `(adjusted_width, adjusted_height)`

**Algorithm:**
```python
aratio = img.size[0] / img.size[1]
ew = min(aratio * ad[1], ad[0])
eh = min(ad[0] / aratio, ad[1])
return int(ew), int(eh)
```

**Behavior:**
- Maintains aspect ratio
- Fits within available space
- Creates dead space if aspect ratios don't match
