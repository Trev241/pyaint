# Pyaint Documentation

Welcome to the Pyaint documentation. Pyaint is an intelligent drawing automation tool that converts images into precise mouse movements for painting applications.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Core Modules](#core-modules)
  - [Bot Module](#bot-module)
  - [UI Module](#ui-module)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Usage Guide](./usage-guide.md)
- [Tutorial](./tutorial.md)
- [Development Guide](#development-guide)

## Overview

Pyaint is a Python-based automation tool designed to recreate digital images through automated brush strokes in painting applications like MS Paint, Clip Studio Paint, and skribbl.

### Key Features

- **Multi-Application Support**: Compatible with various drawing software
- **Dual Input Methods**: Load images from local files or remote URLs
- **High-Precision Drawing**: Near-perfect color accuracy with customizable settings
- **Real-time Progress**: Live tracking with estimated completion time
- **Intelligent Caching**: Pre-compute image processing for instant subsequent runs
- **Advanced Palette Features**: Manual center picking, valid position selection, precision estimation
- **Pause/Resume**: Configurable hotkey for interruption and continuation
- **Skip First Color**: Option to skip drawing the first color in the coordinate map
- **MSPaint Mode**: Double-click on palette colors instead of single click (optional)
- **Region-Based Redrawing**: Select specific image areas to redraw
- **Color Calibration System**: Scan and save custom color mappings for improved accuracy
- **Modifier Key Support**: Configure CTRL, ALT, SHIFT modifiers for tool clicks

## Architecture

The application consists of three main components:

```
pyaint/
├── main.py              # Application entry point
├── bot.py               # Core drawing engine
├── ui/
│   ├── window.py        # Main GUI interface
│   └── setup.py         # Setup configuration wizard
├── exceptions.py        # Custom error classes
├── utils.py             # Utility functions
├── config.json          # Persistent settings storage
├── cache/               # Cached computation results
└── requirements.txt     # Python dependencies
```

### Data Flow

1. **Initialization**: User configures tools (palette, canvas, custom colors) via Setup Window
2. **Color Calibration** (optional): User runs calibration to scan custom color spectrum
3. **Image Loading**: User provides image URL or local file path
4. **Processing**: Bot processes image into coordinate map (color → lines)
5. **Drawing**: Bot executes mouse movements to recreate image
6. **Caching**: Results can be cached for faster subsequent runs

## Core Modules

### Bot Module (`bot.py`)

The Bot module contains the core drawing engine with two main classes: [`Palette`](bot.py:16) and [`Bot`](bot.py:87).

#### Palette Class

Handles color palette detection and color matching.

**Methods:**
- [`__init__()`](bot.py:17) - Initialize palette from box dimensions or pre-defined color positions
- [`nearest_color()`](bot.py:75) - Find nearest palette color to a target RGB value
- [`dist()`](bot.py:78) - Calculate squared distance between two RGB colors

**Attributes:**
- `colors_pos` - Dictionary mapping RGB tuples to screen coordinates
- `colors` - Set of available colors
- `box` - Palette bounding box (left, top, width, height)
- `rows`, `columns` - Grid dimensions

#### Bot Class

Main drawing engine handling image processing and mouse automation.

**Constants:**
- `SLOTTED` - Simple color-to-lines mapping mode
- `LAYERED` - Advanced color layering mode (default)
- `IGNORE_WHITE` - Skip drawing white pixels
- `USE_CUSTOM_COLORS` - Enable custom color mixing

**Settings Indices:**
- `DELAY` (0) - Stroke timing delay
- `STEP` (1) - Pixel size step
- `ACCURACY` (2) - Color precision
- `JUMP_DELAY` (3) - Delay for large cursor movements

**Instance Attributes:**
- `terminate` (bool) - Stop drawing when True
- `paused` (bool) - Pause/resume state
- `pause_key` (str) - Key for pause/resume (default: 'p')
- `settings` (list) - [delay, step, accuracy, jump_delay]
- `progress` (float) - Processing progress (0-100)
- `options` (int) - Drawing flags
- `drawing` (bool) - Currently drawing flag
- `draw_state` (dict) - State for pause/resume recovery
- `skip_first_color` (bool) - Skip first color when drawing (default: False)
- `new_layer` (dict) - New layer configuration
- `color_button` (dict) - Color button configuration
- `color_button_okay` (dict) - Color button okay configuration
- `mspaint_mode` (dict) - MSPaint mode (double-click on palette)
- `total_strokes` (int) - Total number of strokes for progress tracking
- `completed_strokes` (int) - Number of completed strokes
- `start_time` (float) - Timestamp when drawing started
- `estimated_time_seconds` (float) - Estimated drawing time in seconds
- `_canvas` (tuple) - Canvas box (x, y, w, h)
- `_palette` (Palette) - Palette object
- `_custom_colors` (tuple) - Custom colors box
- `_spectrum_map` (dict) - Color spectrum mappings
- `color_calibration_map` (dict) - Color calibration data

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|--------|----------|-------------|
| `config_file` (str) - Path to config file (default: 'config.json') |

**Key Methods:**

##### Initialization
- [`init_palette()`](bot.py:165) - Initialize color palette from screen region
- [`init_canvas()`](bot.py:186) - Define canvas drawing area
- [`init_custom_colors()`](bot.py:193) - Configure custom color spectrum

##### Color Calibration
- [`calibrate_custom_colors()`](bot.py:213) - Scan custom colors grid and create calibration map
- [`save_color_calibration()`](bot.py:303) - Save calibration data to JSON file
- [`load_color_calibration()`](bot.py:324) - Load calibration data from JSON file
- [`get_calibrated_color_position()`](bot.py:347) - Find exact calibrated color with tolerance

##### Image Processing
- [`process()`](bot.py:266) - Convert image to coordinate map
- [`process_region()`](bot.py:1083) - Process specific image region

##### Drawing
- [`draw()`](bot.py:397) - Execute full drawing with pause/resume support
- [`test_draw()`](bot.py:810) - Draw first N lines for calibration
- [`simple_test_draw()`](bot.py:1237) - Quick 5-line brush test

##### Caching
- [`precompute()`](bot.py:1001) - Pre-process and cache image
- [`get_cache_filename()`](bot.py:907) - Generate cache file path
- [`load_cached()`](bot.py:1040) - Load and validate cached data
- [`get_cached_status()`](bot.py:1283) - Check cache availability

##### Estimation
- [`estimate_drawing_time()`](bot.py:979) - Calculate estimated drawing time
- [`_estimate_drawing_time_seconds()`](bot.py:929) - Internal time calculation
- [`_format_time()`](bot.py:966) - Format seconds to human-readable string

### UI Module

#### Window Class (`ui/window.py`)

Main GUI interface providing real-time controls and progress monitoring.

**Key Components:**
- Control Panel - Drawing settings and action buttons
- Image Preview Panel - Image loading and preview
- Tooltip Panel - Status messages and progress updates

**Drawing Settings:**
- Delay (0.01-10.0s) - Stroke timing
- Pixel Size (3-50) - Detail level
- Precision (0.0-1.0) - Color accuracy
- Jump Delay (0.0-2.0s) - Cursor movement optimization
- Calibration Step Size (1-10) - Pixel step for color calibration scanning

**Drawing Modes:**
- Slotted - Fast processing, simple mapping
- Layered - Better visual results with color frequency sorting

**Options:**
- Ignore White Pixels - Skip white areas
- Use Custom Colors - Enable advanced color mixing
- Enable New Layer - Automatic layer creation
- Enable Color Button - Click color picker button
- Enable Color Button Okay - Click color confirmation button

**Actions:**
- Setup - Configure palette, canvas, custom colors
- Run Calibration - Scan and save custom color calibration
- Pre-compute - Cache image processing
- Test Draw - Draw sample lines for calibration
- Simple Test Draw - Quick 5-line test
- Start - Begin full drawing
- Redraw Region - Draw selected area only

#### SetupWindow Class (`ui/setup.py`)

Configuration wizard for initializing tools with advanced features.

**Features:**
- Tool initialization via mouse click selection
- Preview captured regions
- Manual color selection with valid/invalid toggle
- Center point picking for precise color selection
- Auto-estimate centers for quick setup
- Precision estimate using reference points
- Modifier key configuration (CTRL, ALT, SHIFT)
- Select All / Deselect All buttons for batch color selection
- Show Custom Centers overlay for manual center verification

**Palette Configuration Modes:**
1. **Toggle Mode** - Click cells to mark valid/invalid
2. **Pick Centers Mode** - Click exact center points for each color
3. **Auto-Estimate** - Calculate centers using grid-based estimation
4. **Precision Estimate** - Advanced calculation using reference points:
   - Single Column Mode - For vertical palettes
   - 1 Row Mode - For horizontal palettes
   - Multi-Row Mode - For grid palettes

## Configuration

Configuration is stored in [`config.json`](../config.json) with the following structure:

```json
{
  "drawing_settings": {
    "delay": 0.1,
    "pixel_size": 12,
    "precision": 0.9,
    "jump_delay": 0.5
  },
  "Palette": {
    "status": true,
    "box": [1638, 112, 1893, 516],
    "rows": 37,
    "cols": 7,
    "color_coords": {
      "(r, g, b)": [x, y],
      ...
    },
    "valid_positions": [0, 1, 2, ...],
    "manual_centers": {
      "0": [x, y],
      ...
    },
    "preview": "assets/Palette_preview.png"
  },
  "Canvas": {
    "status": true,
    "box": [275, 306, 1522, 807],
    "preview": "assets/Canvas_preview.png"
  },
  "Custom Colors": {
    "status": true,
    "box": [1880, 107, 1893, 442],
    "preview": "assets/Custom Colors_preview.png"
  },
  "New Layer": {
    "status": true,
    "coords": [1633, 1027],
    "enabled": false,
    "modifiers": {
      "ctrl": false,
      "alt": false,
      "shift": true
    }
  },
  "Color Button": {
    "status": true,
    "coords": [88, 399],
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
    "coords": [1721, 828],
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
  "calibration_settings": {
    "step_size": 2
  },
  "pause_key": "p",
  "drawing_options": {
    "ignore_white_pixels": false,
    "use_custom_colors": false
  },
  "last_image_url": "https://..."
}
```

## API Reference

### Bot API

#### `Bot(settings=[0.1, 12, 0.9, 0.5])`

Create a new Bot instance with default settings.

**Parameters:**
- `config_file` (str) - Path to config file (default: 'config.json')

**Attributes:**
- `terminate` (bool) - Stop drawing when True
- `paused` (bool) - Pause/resume state
- `pause_key` (str) - Key for pause/resume (default: 'p')
- `settings` (list) - [delay, step, accuracy, jump_delay]
- `progress` (float) - Processing progress (0-100)
- `options` (int) - Drawing flags (IGNORE_WHITE | USE_CUSTOM_COLORS)
- `drawing` (bool) - Currently drawing flag
- `draw_state` (dict) - State for pause/resume recovery
- `color_calibration_map` (dict) - Color calibration mappings
- `new_layer` (dict) - New layer configuration
- `color_button` (dict) - Color button configuration
- `color_button_okay` (dict) - Color button okay configuration

#### `init_palette(pbox, prows, pcols, valid_positions=None, manual_centers=None)`

Initialize color palette from screen region.

**Parameters:**
- `pbox` (tuple) - Palette box (left, top, width, height)
- `prows` (int) - Number of rows
- `pcols` (int) - Number of columns
- `valid_positions` (set) - Indices of valid palette cells
- `manual_centers` (dict) - Manual center points {index: (x, y)}

**Returns:** [`Palette`](bot.py:16) object

**Raises:** [`NoPaletteError`](exceptions.py:7)

#### `init_canvas(cabox)`

Define canvas drawing area.

**Parameters:**
- `cabox` (tuple) - Canvas box (x1, y1, x2, y2)

**Raises:** [`NoCanvasError`](exceptions.py:10)

#### `init_custom_colors(ccbox)`

Configure custom color spectrum.

**Parameters:**
- `ccbox` (tuple) - Custom colors box (x1, y1, x2, y2)

**Side Effect:** Scans spectrum and creates `_spectrum_map` attribute

#### `calibrate_custom_colors(grid_box, preview_point, step=2)`

Scan custom colors grid and record RGB values shown in preview point.

**Parameters:**
- `grid_box` (tuple/list) - Color spectrum area [x1, y1, x2, y2] or dict
- `preview_point` (tuple/list) - Preview point coordinates [x, y] or dict
- `step` (int) - Pixel step size for scanning (default: 2)

**Returns:** `dict` - Mapping of RGB tuples to (x, y) coordinates

**Notes:**
- Requires Custom Colors and Color Preview Spot tools to be configured
- Scans entire spectrum by dragging slider through it
- Can be cancelled with ESC key

#### `save_color_calibration(filepath)`

Save color calibration map to JSON file.

**Parameters:**
- `filepath` (str) - Path to JSON file

**Returns:** `bool` - True on success, False on failure

#### `load_color_calibration(filepath)`

Load color calibration data from JSON file.

**Parameters:**
- `filepath` (str) - Path to JSON file

**Returns:** `bool` - True on success, False on failure

#### `get_calibrated_color_position(target_rgb, tolerance=20)`

Find exact calibrated color position with tolerance before falling back to nearest.

**Parameters:**
- `target_rgb` (tuple) - Target RGB (r, g, b)
- `tolerance` (int) - Maximum color difference for match (default: 20)

**Returns:** `tuple` or `None` - (x, y) coordinates or None

#### `process(file, flags=0, mode=LAYERED)`

Convert image to coordinate map.

**Parameters:**
- `file` (str) - Path to image file
- `flags` (int) - Drawing options (IGNORE_WHITE | USE_CUSTOM_COLORS)
- `mode` (str) - 'slotted' or 'layered'

**Returns:** dict mapping colors to list of line coordinates

**Processing Steps:**
1. Load image with PIL
2. Resize to fit canvas (maintaining aspect ratio)
3. Scan pixels at step size intervals
4. Map each pixel to nearest palette color (or calibrated color)
5. Generate line segments (horizontal runs of same color)
6. In LAYERED mode: sort colors by frequency and merge lines

#### `process_region(file, region, flags=0, mode=LAYERED, canvas_target=None)`

Process specific region of an image.

**Parameters:**
- `file` (str) - Path to image file
- `region` (tuple) - Image region (x1, y1, x2, y2)
- `flags` (int) - Drawing options
- `mode` (str) - Processing mode
- `canvas_target` (tuple, optional) - Target canvas area (x, y, w, h)

**Returns:** dict - Color map for region

#### `draw(cmap)`

Execute full drawing from coordinate map with pause/resume support.

**Parameters:**
- `cmap` (dict) - Color map from [`process()`](#processself-file-flags0-modelayered)

**Returns:** 'success', 'terminated', or 'paused'

**Features:**
- Progress tracking with time estimation
- Jump delay for cursor movements > 5px
- Stroke segmentation for smooth drawing
- Pause/resume with state recovery
- New layer support (if enabled)
- Color button support (if enabled)
- Color button okay support (if enabled)
- Calibrated color selection (if available)

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

#### `test_draw(cmap, max_lines=20)`

Draw first N lines for brush calibration.

**Parameters:**
- `cmap` (dict) - Color map
- `max_lines` (int) - Maximum lines to draw (default: 20)

#### `simple_test_draw()`

Draw 5 horizontal lines for quick brush calibration.

**Features:**
- No color picking
- Lines drawn starting from canvas upper-left area, spaced by pixel size
- Each line is 1/4 of canvas width

#### `precompute(image_path, flags=0, mode=LAYERED)`

Pre-process and cache image for faster subsequent runs.

**Parameters:**
- `image_path` (str) - Path to image file
- `flags` (int) - Drawing options
- `mode` (str) - Processing mode

**Returns:** str - Cache file path

**Cache File:** `cache/{img_hash}_{settings_hash}.json`

#### `estimate_drawing_time(cmap)`

Calculate estimated drawing time based on coordinate data.

**Parameters:**
- `cmap` (dict) - Color map

**Returns:** str - Human-readable time string

**Calculation:**
- Sum of stroke delays
- Jump delays for movements > 5px
- Color switching overhead (~0.5s per color)

### Window API

#### `Window(title, bot, w, h, x, y)`

Create main application window.

**Parameters:**
- `title` (str) - Window title
- `bot` (Bot) - Bot instance
- `w`, `h` (int) - Window dimensions
- `x`, `y` (int) - Window position

**Methods:**
- `setup()` - Open setup window
- `start_precompute_thread()` - Start pre-computation in background
- `start_test_draw_thread()` - Start test draw
- `start_simple_test_draw_thread()` - Start simple test
- `start_draw_thread()` - Start full drawing
- `start_calibration_thread()` - Start color calibration process
- `load_config()` - Load saved configuration
- `_on_search_img()` - Load image from URL or file path

### SetupWindow API

#### `SetupWindow(parent, bot, tools, on_complete, title='Child Window', w=700, h=800, x=5, y=5)`

Create setup configuration window.

**Parameters:**
- `parent` (Tk) - Parent window
- `bot` (Bot) - Bot instance
- `tools` (dict) - Tool configuration
- `on_complete` (callable) - Callback on completion
- `title` (str) - Window title
- `w`, `h` (int) - Window dimensions
- `x`, `y` (int) - Window position

**Color Selection Methods:**
- `_start_manual_color_selection(name, tool)` - Open manual color selection window
- `_open_color_selection_window()` - Create color selection grid interface
- `_toggle_grid_cell(index)` - Toggle a grid cell between valid and invalid
- `_set_pick_centers_mode()` - Set mode to pick exact center points
- `_pick_center(index)` - Pick a center point for a specific color cell
- `_auto_estimate_centers()` - Automatically calculate center points
- `_start_precision_estimate()` - Start precision estimate
- `_show_centers_overlay()` - Display overlay circles showing estimated center positions
- `_show_custom_centers_overlay()` - Display overlay circles showing manually picked center positions
- `_select_all_colors()` - Mark all grid cells as valid
- `_deselect_all_colors()` - Mark all grid cells as invalid

## Usage Guide

### Initial Setup

1. Launch application: `python main.py`
2. Click **"Setup"** button
3. Initialize tools by clicking corners as prompted:
   - **Palette**: Click upper-left and lower-right corners
   - **Canvas**: Click upper-left and lower-right corners
   - **Custom Colors**: Click upper-left and lower-right corners
   - **Color Preview Spot**: (optional) Click on the preview location
   - **New Layer**: (optional) Click on new layer button
   - **Color Button**: (optional) Click on color picker button
   - **Color Button Okay**: (optional) Click on color confirmation button

### Color Calibration (Optional)

For improved color accuracy with custom colors:

1. Configure **Custom Colors** tool (spectrum area)
2. Configure **Color Preview Spot** tool (preview location)
3. Set **Calibration Step Size** (1-10, default: 2)
4. Click **"Run Calibration"** button
5. System scans the entire spectrum and maps RGB values to positions
6. Calibration saved to `color_calibration.json`
7. During drawing, bot uses exact calibrated colors instead of approximations

### Drawing Workflow

1. Load image via URL or file browser
2. (Optional) Run calibration for better color accuracy
3. (Optional) Click **"Pre-compute"** to cache processing
4. Click **"Test Draw"** or **"Simple Test Draw"** to calibrate brush
5. Adjust brush settings in your painting application
6. Click **"Start"** to begin drawing
7. Use **ESC** to stop or pause key to pause/resume

### Region-Based Redrawing

1. Load your image
2. Click and drag on preview to select region
3. Click **"Redraw Region"** to draw only selected area

### Controls

- **ESC**: Stop current drawing operation
- **Pause Key** (default 'p'): Pause/resume drawing
- **Setup**: Configure palette, canvas, custom colors

## Development Guide

### Project Structure

```
pyaint/
├── main.py              # Entry point with keyboard listener
├── bot.py               # Core drawing engine
├── ui/
│   ├── __init__.py     # Package marker
│   ├── window.py        # Main GUI (Window class)
│   └── setup.py         # Setup wizard (SetupWindow class)
├── exceptions.py        # Custom exceptions
├── utils.py             # Utility functions
├── config.json          # Settings storage
├── cache/               # Computed results cache
└── requirements.txt     # Dependencies
```

### Adding New Features

1. Add settings to [`config.json`](../config.json) structure
2. Update [`Window._init_cpanel()`](ui/window.py:145) to add UI controls
3. Update [`load_config()`](ui/window.py:669) to load new settings
4. Add validation and save logic

### Drawing Algorithms

#### Slotted Mode

Simple color-to-lines mapping. Each color gets a list of horizontal line segments.

**Advantages:**
- Faster processing
- Simpler code path
- Less memory usage

#### Layered Mode

Advanced color layering with frequency sorting:

1. Count color frequency (total pixel coverage)
2. Sort colors by frequency (most used first)
3. Merge adjacent lines of lower-frequency colors
4. Higher-frequency colors paint over lower-frequency ones

**Advantages:**
- Better visual results
- Fewer color switches
- Optimized for complex images

### Color Calibration System

When custom colors are enabled and calibration is available:

1. System loads calibration data from `color_calibration.json`
2. For each image color, looks for exact match within tolerance
3. If exact match found, clicks the exact calibrated position
4. If no exact match, falls back to nearest color with tolerance
5. If calibration not available, uses spectrum scanning or keyboard input

**Advantages:**
- Precise color selection (prevents wrong color selection)
- Tolerance-based matching (handles minor variations)
- Faster than keyboard input fallback
- Saved calibration can be reused across sessions

**Calibration Process:**
1. User specifies Custom Colors spectrum box
2. User specifies Color Preview Spot (where selected color appears)
3. Set calibration step size (lower = more accurate but slower)
4. Run calibration - system drags slider through entire spectrum
5. For each position, captures RGB from preview spot
6. Saves mapping of RGB → (x, y) coordinates to JSON

### Custom Color Spectrum

When custom colors are enabled:

1. System scans the custom color spectrum box
2. Creates a color-to-position map by sampling pixels
3. For each image color, finds nearest spectrum color
4. If calibration exists, uses calibrated exact match
5. Clicks the nearest position on spectrum
6. Falls back to keyboard input if spectrum unavailable

### Caching Strategy

Cache files are named using MD5 hash:

```
cache/{image_hash}_{settings_hash}.json
```

**Cache Contents:**
- `cmap` - Color coordinate map
- `settings` - Drawing settings used
- `flags` - Drawing options
- `mode` - Processing mode
- `canvas` - Canvas dimensions
- `image_hash` - Source image hash
- `timestamp` - Cache creation time
- `palette_info` - Palette configuration

**Cache Validation:**
- Settings must match current configuration
- Canvas dimensions must match
- Cache age < 24 hours

### Error Handling

Custom exceptions in [`exceptions.py`](../exceptions.py):

- [`NoToolError`](exceptions.py:1) - Base exception for tool errors
- [`CorruptConfigError`](exceptions.py:4) - Invalid configuration
- [`NoPaletteError`](exceptions.py:7) - Palette not initialized
- [`NoCanvasError`](exceptions.py:10) - Canvas not initialized
- [`NoCustomColorsError`](exceptions.py:13) - Custom colors not initialized

### Thread Safety

Long-running operations use separate threads:
- Pre-computation
- Test draw
- Simple test draw
- Full drawing
- Color calibration

Thread management via [`_manage_*_thread()`](ui/window.py:1041) methods.

### Dependencies

- **PyAutoGUI** - Mouse and keyboard automation
- **Pillow** - Image processing
- **pynput** - Global input monitoring
- **tkinter** - GUI framework

### Testing

Run tests before full drawing:
1. **Simple Test Draw** - Quick 5-line calibration
2. **Test Draw** - First 20 lines with color switching
3. Adjust brush size based on test results

### Performance Optimization

- Use pre-computation for repeated drawings
- Run color calibration for better accuracy
- Increase pixel size for faster drawing (less detail)
- Adjust delay based on system responsiveness
- Use jump delay to prevent unintended strokes
- Enable "Ignore White Pixels" for images with large white areas

## See Also

- [Architecture Documentation](./architecture.md)
- [API Reference](./api.md)
- [Configuration Guide](./configuration.md)
- [Troubleshooting](./troubleshooting.md)
