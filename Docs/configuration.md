# Pyaint Configuration Guide

Complete guide to configuring Pyaint's settings and tools.

## Table of Contents

- [Configuration File](#configuration-file)
- [Drawing Settings](#drawing-settings)
- [Tool Configuration](#tool-configuration)
- [Advanced Features](#advanced-features)
- [Default Values](#default-values)

---

## Configuration File

### File Location

**Path:** `config.json` (in project root, same level as `main.py`)

**Format:** JSON (UTF-8 encoded)

**Loading:**
- Automatic on application startup
- Graceful fallback to defaults if missing/corrupt

**Saving:**
- Automatic on tool configuration completion
- Automatic on drawing setting changes
- Automatic on checkbox toggles

### Configuration Structure

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

---

## Drawing Settings

### Delay

**Range:** 0.01 - 10.0 seconds

**Default:** 0.1

**Description:** Controls the duration of each brush stroke.

**UI Control:** Text entry field (not a slider)

**When to Adjust:**
- **Increase** if your machine is slow and doesn't respond well to fast input
- **Decrease** for faster drawing (if your system can handle it)

**Impact:**
- Higher delay = slower drawing but more reliable
- Lower delay = faster drawing but may miss strokes on slow systems

### Pixel Size

**Range:** 3 - 50 (integer)

**Default:** 12

**Description:** Controls the detail level of the drawing. This does NOT affect your brush size in the painting application.

**UI Control:** Slider with integer display

**When to Adjust:**
- **Increase** for more detail (longer draw time)
- **Decrease** for faster drawing (less detail)

**Impact:**
- Larger values = fewer pixels to process = faster
- Smaller values = more detail = significantly longer draw time

### Precision

**Range:** 0.0 - 1.0

**Default:** 0.9

**Description:** Controls color accuracy for custom colors. Higher values use more distinct colors.

**UI Control:** Slider

**When to Adjust:**
- **Increase** for better color matching (slower processing)
- **Decrease** for faster processing with fewer color variations

**Impact:**
- Higher precision = more accurate colors but slower
- Lower precision = fewer colors but faster processing
- Only applies when "Use Custom Colors" is enabled

### Jump Delay

**Range:** 0.0 - 2.0 seconds

**Default:** 0.5

**Description:** Adds delay when cursor jumps more than 5 pixels between strokes.

**UI Control:** Slider

**When to Adjust:**
- **Increase** to prevent unintended strokes from rapid cursor movement
- **Decrease** for faster drawing on responsive systems

**Impact:**
- Higher jump delay = fewer accidental strokes but slower
- Lower jump delay = faster but risk of unintended strokes

---

## Tool Configuration

### Palette

**Status:** Essential (required for drawing)

**Fields:**

| Field | Type | Description |
|--------|--------|-------------|
| `status` | bool | True if initialized |
| `box` | array | [x1, y1, x2, y2] screen coordinates |
| `rows` | int | Number of rows in palette grid |
| `cols` | int | Number of columns in palette grid |
| `color_coords` | object | RGB → (x, y) mappings |
| `valid_positions` | array | Indices of valid palette cells |
| `manual_centers` | object | Manual center point overrides |
| `preview` | string | Path to preview screenshot |

**Advanced Features:**
- **Valid Positions**: Toggle which palette cells are available
- **Manual Centers**: Set exact center points for each color
- **Auto-Estimate**: Calculate grid-based center points
- **Precision Estimate**: Advanced calculation using reference points

### Canvas

**Status:** Essential (required for drawing)

**Fields:**

| Field | Type | Description |
|--------|--------|-------------|
| `status` | bool | True if initialized |
| `box` | array | [x1, y1, x2, y2] screen coordinates |
| `preview` | string | Path to preview screenshot |

### Custom Colors

**Status:** Optional (required if "Use Custom Colors" enabled)

**Fields:**

| Field | Type | Description |
|--------|--------|-------------|
| `status` | bool | True if initialized |
| `box` | array | [x1, y1, x2, y2] spectrum coordinates |
| `preview` | string | Path to preview screenshot |

**Behavior:**
- Scans spectrum to create color map
- Used when "Use Custom Colors" is enabled
- Falls back to keyboard input if not configured

### MSPaint Mode

**Status:** Optional

**Fields:**

| Field | Type | Default | Description |
|--------|--------|----------|-------------|
| `enabled` | bool | false | Whether to double-click on palette instead of single click |
| `delay` | float | 0.5 | Delay between double-clicks in seconds |

**Behavior:**
- If enabled: Double-clicks on palette colors instead of single click
- Waits configured delay between clicks
- Useful for MS Paint and similar applications requiring double-click

### Color Preview Spot

**Status:** Optional (required for color calibration)

**Fields:**

| Field | Type | Description |
|--------|--------|-------------|
| `name` | string | "Color Preview Spot" |
| `status` | bool | True if initialized |
| `coords` | array | [x, y] screen coordinates |
| `enabled` | bool | Whether feature is active |
| `modifiers` | object | CTRL/ALT/SHIFT key flags |

**Purpose:** Specifies where to capture RGB values during color calibration

### New Layer

**Status:** Optional

**Fields:**

| Field | Type | Description |
|--------|--------|-------------|
| `status` | bool | True if initialized |
| `coords` | array | [x, y] button coordinates |
| `enabled` | bool | Whether to automatically create layers |
| `modifiers` | object | CTRL/ALT/SHIFT key flags |

**Behavior:**
- If enabled: clicks new layer button before each color change
- Waits 0.75 seconds after click for layer to be created
- Supports modifier keys (useful if app requires keyboard shortcut)

### Color Button

**Status:** Optional

**Fields:**

| Field | Type | Description |
|--------|--------|-------------|
| `status` | bool | True if initialized |
| `coords` | array | [x, y] button coordinates |
| `enabled` | bool | Whether to click color picker button |
| `delay` | float | Time to wait after click (0.01-5.0s) |
| `modifiers` | object | CTRL/ALT/SHIFT key flags |

**Behavior:**
- If enabled: clicks color button before each color change
- Waits configured delay for color picker to open
- Supports modifier keys (useful if app requires keyboard shortcut)

### Color Button Okay

**Status:** Optional

**Fields:**

| Field | Type | Description |
|--------|--------|-------------|
| `status` | bool | True if initialized |
| `coords` | array | [x, y] button coordinates |
| `enabled` | bool | Whether to click confirmation button |
| `delay` | float | Time to wait after click (0.01-5.0s) |
| `modifiers` | object | CTRL/ALT/SHIFT key flags |

**Behavior:**
- If enabled: clicks confirmation button after color selection
- Waits configured delay after click
- Supports modifier keys

---

## Advanced Features

### Calibration Settings

**Purpose:** Configure color calibration scanning behavior

**Fields:**

| Field | Type | Range | Description |
|--------|--------|--------|-------------|
| `step_size` | int | 1-10 | Pixel step size for scanning |

**Default:** 2

**Behavior:**
- Lower step = more accurate calibration but slower
- Higher step = faster calibration but less accurate

### Drawing Options

**Purpose:** Enable/disable drawing features

**Fields:**

| Field | Type | Default | Description |
|--------|--------|----------|-------------|
| `ignore_white_pixels` | bool | false | Skip drawing white pixels |
| `use_custom_colors` | bool | false | Use custom color spectrum |
| `skip_first_color` | bool | false | Skip first color when drawing |

### Pause Key

**Purpose:** Configure keyboard key for pause/resume

**Field:**

| Field | Type | Default | Description |
|--------|--------|----------|-------------|
| `pause_key` | string | 'p' | Key name for pause/resume |

**Supported Keys:**
- Any letter key (a-z)
- Any number (0-9)
- Function keys (F1-F12)
- Special keys (arrows, etc.)

---

## Default Values

### Drawing Settings

| Setting | Default | Min | Max |
|---------|---------|-----|-----|
| Delay | 0.1s | 0.01s | 10.0s |
| Pixel Size | 12 | 3 | 50 |
| Precision | 0.9 | 0.0 | 1.0 |
| Jump Delay | 0.5s | 0.0s | 2.0s |

### Tool Configuration

All tools default to not initialized (`status: false`).

### User Preferences

| Setting | Default | Description |
|---------|---------|-------------|
| pause_key | 'p' | Pause/resume key |
| skip_first_color | false | Skip first color when drawing |
| calibration_settings.step_size | 2 | Calibration scan step |
| drawing_options.ignore_white_pixels | false | Skip white pixels |
| drawing_options.use_custom_colors | false | Use custom colors |
| mspaint_mode.enabled | false | Enable double-click on palette |
| mspaint_mode.delay | 0.5 | Delay between double-clicks in seconds |

---

## Modifying Configuration

### Via UI

Most settings can be changed through the main window:

1. **Drawing Settings**: Adjust sliders/entry in Control Panel
2. **Drawing Options**: Toggle checkboxes in Control Panel
3. **Pause Key**: Click entry field and press key
4. **Tools**: Click "Setup" button to configure tools

### Via Text Editor

Edit `config.json` directly in a text editor.

**Warning:** Invalid JSON will cause the application to use defaults.

### Resetting Configuration

To reset all settings:
1. **Via UI**: Click "Reset Config" button in File Management section
2. **Via Manual**: Delete `config.json` file and restart Pyaint
3. Configure tools via Setup button

---

## File Management

### Overview

The File Management section in the Control Panel provides two buttons for managing configuration files:

- **Remove Calibration**: Deletes the color calibration file
- **Reset Config**: Deletes the main configuration file

### Remove Calibration

**Purpose:** Clear color calibration data to force recalibration or remove outdated data.

**What it Deletes:** `color_calibration.json`

**When to Use:**
- Color calibration data is outdated or incorrect
- You want to recalibrate from scratch
- Calibration was done on different display settings

**Actions:**
1. Click "Remove Calibration" button
2. Confirm the deletion in the dialog
3. Color calibration map is cleared from memory
4. Next drawing will require new calibration or revert to keyboard input

**Restoration:** The calibration data will be rebuilt automatically when:
- You run "Run Calibration" again, OR
- No calibration file exists and drawing uses custom colors (falls back to keyboard input)

### Reset Config

**Purpose:** Reset all settings, tools, and preferences to default values.

**What it Deletes:** `config.json`

**What is Lost:**
- All tool configurations (Palette, Canvas, Custom Colors, etc.)
- All drawing settings (Delay, Pixel Size, Precision, Jump Delay)
- All feature toggles (New Layer, Color Button, MSPaint Mode, etc.)
- Pause key configuration
- Last used image URL

**When to Use:**
- Configuration is corrupted or causing issues
- You want to start completely fresh
- Settings are lost and need to reconfigure everything

**Actions:**
1. Click "Reset Config" button
2. Confirm the reset in the warning dialog
3. Configuration file is deleted
4. Restart the application to load default settings

**Restoration:** You will need to:
1. Restart Pyaint (application will use built-in defaults)
2. Run "Setup" to reconfigure tools
3. Adjust drawing settings as needed
4. Run "Run Calibration" if using custom colors

### Confirmation Safety

Both deletion operations include confirmation dialogs to prevent accidental data loss:
- **Remove Calibration**: Confirm dialog showing which file will be deleted
- **Reset Config**: Warning dialog listing all data that will be lost

### Error Handling

Both operations provide feedback:
- Success message when file is deleted
- Informational message if file doesn't exist
- Error message with details if deletion fails

Check the tooltip/status label at the bottom of the window for detailed feedback.

---

## Configuration Validation

### Palette

- Must have at least one valid position
- Rows and columns must be positive integers
- Box coordinates must be valid (x1 < x2, y1 < y2)

### Canvas

- Box coordinates must be valid (x1 < x2, y1 < y2)
- Must be larger than 0 pixels in both dimensions

### Custom Colors

- Box coordinates must be valid (x1 < x2, y1 < y2)

### Drawing Settings

- Delay must be between 0.01 and 10.0
- Pixel size must be between 3 and 50
- Precision must be between 0.0 and 1.0
- Jump delay must be between 0.0 and 2.0

---

## See Also

- [API Reference](./api.md) - Detailed API documentation
- [Architecture](./architecture.md) - System architecture details
- [Troubleshooting](./troubleshooting.md) - Common issues and solutions
- [Usage Guide](./usage-guide.md) - Step-by-step usage instructions
