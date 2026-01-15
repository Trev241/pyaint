# Pyaint Documentation

Welcome to Pyaint documentation. Pyaint is an intelligent drawing automation tool that converts images into precise mouse movements for painting applications.

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
- **File Management**: Remove calibration and reset config from UI

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

The Bot module contains the core drawing engine.

**Key Classes:**
- `Bot`: Main automation class

**Constants:**
- `SLOTTED` - Simple color-to-lines mapping mode
- `LAYERED` - Advanced color layering mode (default)

**Settings:**
- `delay` (float) - Stroke timing delay
- `pixel_size` (int) - Pixel step size
- `precision` (float) - Color accuracy
- `jump_delay` (float) - Delay for large cursor movements
- `jump_threshold` (int) - Pixel distance threshold for jump delay (default: 5)

**Key Methods:**
- `draw()` - Execute full drawing with pause/resume support
- `draw_test()` - Draw first N lines for calibration
- `simple_test_draw()` - Quick 5-line brush test
- `precompute_image()` - Pre-process and cache image
- `pick_palette_color()` - Select palette color
- `pick_custom_color()` - Select custom color
- `calibrate_custom_colors()` - Scan and save custom color calibration

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
- Jump Threshold (1-100px) - Distance threshold for jump delay (default: 5)
- Calibration Step Size (1-10) - Pixel step for color calibration scanning

**Drawing Modes:**
- Slotted - Fast processing, simple mapping
- Layered - Better visual results with color frequency sorting

**Options:**
- Ignore White Pixels - Skip white areas
- Use Custom Colors - Enable advanced color mixing
- Skip First Color - Skip first color when drawing
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

**File Management:**
- Remove Calibration - Delete color calibration file
- Reset Config - Delete main configuration file

**Pause Key:**
- Entry field for key configuration (default: 'p')

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
4. **Precision Estimate** - Advanced calculation using reference points

## Configuration

Configuration is stored in `config.json` with the following structure:

```json
{
  "drawing_settings": {
    "delay": 0.1,
    "pixel_size": 12,
    "precision": 0.9,
    "jump_delay": 0.5
  },
  "drawing_options": {
    "ignore_white_pixels": false,
    "use_custom_colors": false,
    "skip_first_color": false
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
      "shift": true
    }
  },
  "Color Button": {
    "status": true,
    "coords": [x, y],
    "enabled": false,
    "delay": 0.1,
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
    "delay": 0.1,
    "modifiers": {
      "ctrl": false,
      "alt": false,
      "shift": false
    }
  },
  "MSPaint Mode": {
    "enabled": false,
    "delay": 0.5
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

## API Reference

### Bot API

#### `Bot(config_file='config.json')`

Create a new Bot instance.

**Parameters:**
- `config_file` (str) - Path to config file (default: 'config.json')

**Key Attributes:**
- `terminate` (bool) - Stop drawing when True
- `paused` (bool) - Pause/resume state
- `pause_key` (str) - Key for pause/resume (default: 'p')
- `delay` (float) - Stroke timing delay
- `pixel_size` (int) - Pixel step size
- `precision` (float) - Color accuracy
- `jump_delay` (float) - Delay for large cursor movements
- `jump_threshold` (int) - Pixel distance threshold for jump delay
- `drawing` (bool) - Currently drawing flag

### Window API

#### `Window(title, bot, width, height, screen_x, screen_y)`

Create main application window.

**Parameters:**
- `title` (str) - Window title
- `bot` (Bot) - Bot instance
- `width` (int) - Window width
- `height` (int) - Window height
- `screen_x` (int) - Screen x offset
- `screen_y` (int) - Screen y offset

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
   - **MSPaint Mode**: (optional) Enable double-click on palette

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

### File Management

**Remove Calibration:**
- Deletes `color_calibration.json`
- Useful when calibration data is outdated or incorrect
- Forces recalibration on next use

**Reset Config:**
- Deletes `config.json`
- Resets all settings to defaults
- Requires reconfiguration of all tools
- Useful when configuration is corrupted or you want to start fresh

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

1. Add settings to `config.json` structure
2. Update UI in `ui/window.py` to add controls
3. Update `load_config()` to load new settings
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
3. If exact match found, clicks on exact calibrated position
4. If no exact match, falls back to nearest color with tolerance
5. If calibration not available, uses spectrum scanning or keyboard input

**Advantages:**
- Precise color selection (prevents wrong color selection)
- Tolerance-based matching (handles minor variations)
- Faster than keyboard input fallback
- Saved calibration can be reused across sessions

### Caching Strategy

Cache files are named using MD5 hash:

```
cache/{image_hash}_{settings_hash}.json
```

**Cache Validation:**
- Settings must match current configuration
- Canvas dimensions must match
- Cache age < 24 hours

### Error Handling

Custom exceptions in `exceptions.py`:

- `PyaintException` - Base exception
- `NotInitializedError` - Tool not initialized
- `ConfigurationError` - Configuration issues
- `DrawingError` - Drawing operation failures

### Thread Safety

Long-running operations use separate threads:
- Pre-computation
- Test draw
- Simple test draw
- Full drawing
- Color calibration

### Dependencies

- **PyAutoGUI** - Mouse and keyboard automation
- **Pillow** - Image processing
- **pynput** - Global input monitoring
- **tkinter** - GUI framework

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
