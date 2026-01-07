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
- [Usage Guide](#usage-guide)
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
- **Region-Based Redrawing**: Select specific image areas to redraw

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
2. **Image Loading**: User provides image URL or local file path
3. **Processing**: Bot processes image into coordinate map (color → lines)
4. **Drawing**: Bot executes mouse movements to recreate image
5. **Caching**: Results can be cached for faster subsequent runs

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

**Key Methods:**

##### Initialization
- [`init_palette()`](bot.py:165) - Initialize color palette from screen region
- [`init_canvas()`](bot.py:186) - Define canvas drawing area
- [`init_custom_colors()`](bot.py:193) - Configure custom color spectrum

##### Image Processing
- [`process()`](bot.py:266) - Convert image to coordinate map
- [`process_region()`](bot.py:1083) - Process specific image region
- [`_scan_spectrum()`](bot.py:202) - Scan custom color spectrum for color mapping

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

**Drawing Modes:**
- Slotted - Fast processing, simple mapping
- Layered - Better visual results with color frequency sorting

**Options:**
- Ignore White Pixels - Skip white areas
- Use Custom Colors - Enable advanced color mixing
- New Layer - Automatic layer creation
- Color Button - Click color picker button
- Color Button Okay - Confirm color selection

**Actions:**
- Setup - Configure palette, canvas, custom colors
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
    "delay": 0.15,
    "pixel_size": 3,
    "precision": 0.896,
    "jump_delay": 0.059
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

**Raises:** [`NoCustomColorsError`](exceptions.py:13)

#### `process(file, flags=0, mode=LAYERED)`

Convert image to coordinate map.

**Parameters:**
- `file` (str) - Path to image file
- `flags` (int) - Drawing options (IGNORE_WHITE | USE_CUSTOM_COLORS)
- `mode` (str) - 'slotted' or 'layered'

**Returns:** dict mapping colors to list of line coordinates

#### `draw(cmap)`

Execute drawing from coordinate map.

**Parameters:**
- `cmap` (dict) - Color map from [`process()`](bot.py:266)

**Returns:** 'success', 'terminated', or 'paused'

**Features:**
- Pause/resume support
- Progress tracking
- Time estimation
- Jump delay optimization
- Stroke replay on resume

#### `test_draw(cmap, max_lines=20)`

Draw first N lines for calibration.

**Parameters:**
- `cmap` (dict) - Color map
- `max_lines` (int) - Maximum lines to draw

#### `simple_test_draw()`

Draw 5 horizontal lines for quick brush calibration.

#### `precompute(image_path, flags=0, mode=LAYERED)`

Pre-process and cache image.

**Returns:** Cache file path

#### `estimate_drawing_time(cmap)`

Calculate estimated drawing time.

**Returns:** Human-readable time string

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

## Usage Guide

### Initial Setup

1. Launch application: `python main.py`
2. Click **"Setup"** button
3. Initialize tools by clicking corners as prompted:
   - **Palette**: Click upper-left and lower-right corners
   - **Canvas**: Click upper-left and lower-right corners
   - **Custom Colors**: Click upper-left and lower-right corners

### Palette Configuration

After capturing the palette box:

1. Set **Rows** and **Columns** for your palette grid
2. Click **"Initialize"** to scan colors
3. Optional advanced features:
   - **Edit Colors**: Open manual color selection window
   - Toggle valid/invalid cells
   - Pick exact center points for precision
   - Auto-estimate centers for quick setup
   - Use Precision Estimate for maximum accuracy

### Drawing Workflow

1. Load image via URL or file browser
2. (Optional) Click **"Pre-compute"** to cache processing
3. Click **"Test Draw"** or **"Simple Test Draw"** to calibrate brush
4. Adjust brush settings in your painting application
5. Click **"Start"** to begin drawing
6. Use **ESC** to stop or pause key to pause/resume

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

### Custom Color Spectrum

When custom colors are enabled:

1. System scans the custom color spectrum box
2. Creates a color-to-position map by sampling pixels
3. For each image color, finds nearest spectrum color
4. Clicks the nearest position on spectrum
5. Falls back to keyboard input if spectrum unavailable

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

Thread management via [`_manage_*_thread()`](ui/window.py:1041) methods.

### Dependencies

- **PyAutoGUI** - Mouse and keyboard automation
- **Pillow** - Image processing
- **pynput** - Global input monitoring
- **keyboard** - Keyboard state checking
- **tkinter** - GUI framework

### Testing

Run tests before full drawing:
1. **Simple Test Draw** - Quick 5-line calibration
2. **Test Draw** - First 20 lines with color switching
3. Adjust brush size based on test results

### Performance Optimization

- Use pre-computation for repeated drawings
- Increase pixel size for faster drawing (less detail)
- Adjust delay based on system responsiveness
- Use jump delay to prevent unintended strokes
- Enable "Ignore White Pixels" for images with large white areas

## See Also

- [Architecture Documentation](./architecture.md)
- [API Reference](./api.md)
- [Configuration Guide](./configuration.md)
- [Troubleshooting](./troubleshooting.md)
