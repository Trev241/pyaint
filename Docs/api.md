# Pyaint API Reference

Complete API documentation for Pyaint's core components.

## Table of Contents

- [Bot Class](#bot-class)
- [Utility Functions](#utility-functions)
- [Exception Classes](#exception-classes)
- [UI Components](#ui-components)
- [Configuration](#configuration)

---

## Bot Class

The main `Bot` class handles all drawing automation operations.

### Constructor

```python
Bot()
```

Creates a new Bot instance with default settings.

### Attributes

#### Public Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `delay` | float | Duration of each brush stroke (seconds) |
| `pixel_size` | int | Detail level - pixels between sample points |
| `precision` | float | Color accuracy threshold (0.0 - 1.0) |
| `jump_delay` | float | Delay on cursor jumps > jump_threshold |
| `jump_threshold` | int | Pixel distance threshold for jump delay |
| `drawing_options` | dict | Drawing feature toggles |
| `terminate` | bool | Flag to stop all operations |
| `paused` | bool | Flag to pause/resume drawing |
| `drawing` | bool | Flag indicating if currently drawing |

#### Drawing Options

The `drawing_options` dictionary contains:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `ignore_white_pixels` | bool | false | Skip drawing white pixels |
| `use_custom_colors` | bool | false | Use custom color spectrum |
| `skip_first_color` | bool | false | Skip first color when drawing |

### Methods

#### Drawing Methods

##### `draw(image, region=None)`

Draws an image on the canvas.

**Parameters:**
- `image` (PIL.Image): Image to draw
- `region` (tuple, optional): Region to draw as (x1, y1, x2, y2)

**Returns:** None

**Behavior:**
- Processes image into draw commands
- Executes drawing with current settings
- Can be interrupted with ESC
- Can be paused/resumed with pause_key

##### `draw_test(image, lines=20)`

Draws a test sample of the image.

**Parameters:**
- `image` (PIL.Image): Image to test draw
- `lines` (int, optional): Number of lines to draw (default: 20)

**Returns:** None

**Behavior:**
- Draws only first N lines of the image
- Includes color switching
- Useful for testing brush size and settings

##### `simple_test_draw(width=4)`

Draws simple horizontal lines without color picking.

**Parameters:**
- `width` (int, optional): Width of lines as fraction of canvas (default: 4)

**Returns:** None

**Behavior:**
- Draws 5 horizontal lines
- Uses currently selected color only
- Useful for testing brush size only

##### `draw_region(region, image)`

Draws a specific region of an image.

**Parameters:**
- `region` (tuple): Region bounds as (x1, y1, x2, y2)
- `image` (PIL.Image): Source image

**Returns:** None

**Behavior:**
- Draws only the specified region
- Useful for fixing mistakes or adding details

#### Color Methods

##### `pick_palette_color(color)`

Selects a color from the palette.

**Parameters:**
- `color` (tuple): RGB color tuple (r, g, b)

**Returns:** None

**Behavior:**
- Finds nearest palette color
- Clicks on palette to select color
- Supports MSPaint Mode (double-click)

##### `pick_custom_color(color)`

Selects a color from the custom color spectrum.

**Parameters:**
- `color` (tuple): RGB color tuple (r, g, b)

**Returns:** None

**Behavior:**
- Finds nearest position in color spectrum
- Clicks on spectrum to select color
- Uses keyboard input if spectrum not available
- Supports color button and confirmation clicks

#### Processing Methods

##### `precompute_image(image)`

Pre-processes image for faster subsequent draws.

**Parameters:**
- `image` (PIL.Image): Image to pre-process

**Returns:** Processed data structure

**Behavior:**
- Processes image based on current mode (slotted/layered)
- Caches results for instant reuse
- Returns data structure for drawing

##### `estimate_time(processed_data)`

Estimates drawing time from pre-processed data.

**Parameters:**
- `processed_data`: Data from `precompute_image()`

**Returns:** Estimated time in seconds (float)

---

## Utility Functions

### `adjusted_img_size(img, ad)`

Recalculates image dimensions to fit within available space.

**Parameters:**
- `img` (PIL.Image): Source image
- `ad` (tuple): Available dimensions as (width, height)

**Returns:** Tuple of (adjusted_width, adjusted_height)

**Behavior:**
- Maintains aspect ratio
- Returns dimensions that fit within available space
- May result in dead space if aspect ratios don't match

---

## Exception Classes

### `PyaintException`

Base exception class for all Pyaint errors.

### `NotInitializedError`

Raised when a required tool is not initialized.

**Example:**
```python
raise NotInitializedError("Palette not initialized")
```

### `ConfigurationError`

Raised when configuration is invalid or missing.

**Example:**
```python
raise ConfigurationError("Config file missing or invalid")
```

### `DrawingError`

Raised when a drawing operation fails.

**Example:**
```python
raise DrawingError("Failed to draw: Canvas not initialized")
```

---

## UI Components

### Window Class

Main application window (`ui/window.py`).

#### Constructor

```python
Window(title, bot, width, height, screen_x, screen_y)
```

**Parameters:**
- `title` (str): Window title
- `bot` (Bot): Bot instance
- `width` (int): Window width
- `height` (int): Window height
- `screen_x` (int): Screen x offset
- `screen_y` (int): Screen y offset

#### Key Methods

##### `run()`

Starts the main application loop.

**Returns:** None

##### `update_tooltip(message)`

Updates the status tooltip at bottom of window.

**Parameters:**
- `message` (str): Status message to display

**Returns:** None

### SetupWindow Class

Setup window for configuring tools (`ui/setup.py`).

#### Key Methods

##### `run()`

Opens and runs the setup configuration dialog.

**Returns:** None

---

## Configuration

### Configuration File Structure

Pyaint uses `config.json` for persistent configuration.

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

### Configuration Loading

Configuration is loaded automatically from `config.json` on startup.

If the file is missing or invalid, default values are used.

### Configuration Saving

Configuration is saved automatically:
- After tool configuration completion
- After drawing setting changes
- After checkbox toggles

### Color Calibration File

Color calibration data is stored in `color_calibration.json`.

Structure:
```json
{
  "calibration_map": {
    "r,g,b": [x, y]
  },
  "timestamp": "YYYY-MM-DD HH:MM:SS"
}
```

---

## Main Entry Point

### `main.py`

The main entry point for the application.

**Behavior:**
1. Creates Bot instance
2. Sets up pynput keyboard listener for ESC and pause key
3. Launches main Window
4. Cleans up listener on exit

**Controls:**
- ESC: Terminates all operations
- pause_key: Toggles pause/resume during drawing

---

## Module Overview

### `bot.py`

Contains the `Bot` class - the core drawing automation engine.

### `utils.py`

Utility functions for image processing.

### `exceptions.py`

Custom exception classes for error handling.

### `main.py`

Application entry point with keyboard control setup.

### `ui/window.py`

Main application window and UI.

### `ui/setup.py`

Setup window for tool configuration.

---

## See Also

- [Architecture Documentation](./architecture.md) - System architecture details
- [Configuration Guide](./configuration.md) - Configuration options
- [Tutorial](./tutorial.md) - Step-by-step usage guide
- [Troubleshooting](./troubleshooting.md) - Common issues and solutions
