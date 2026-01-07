# Pyaint Configuration Guide

This document explains the configuration options available in Pyaint and how to customize them.

## Table of Contents

- [Configuration File](#configuration-file)
- [Drawing Settings](#drawing-settings)
- [Drawing Modes](#drawing-modes)
- [Drawing Options](#drawing-options)
- [Palette Configuration](#palette-configuration)
- [Canvas Configuration](#canvas-configuration)
- [Custom Colors Configuration](#custom-colors-configuration)
- [New Layer Configuration](#new-layer-configuration)
- [Color Button Configuration](#color-button-configuration)
- [Color Button Okay Configuration](#color-button-okay-configuration)
- [Hotkeys](#hotkeys)

## Configuration File

Configuration is stored in [`config.json`](../config.json) in the project root directory.

**File Location:** `pyaint/config.json`

**Auto-save:** Settings are automatically saved when:
- Drawing settings are changed
- Drawing options are toggled
- Setup is completed
- Pause key is set

**Manual Editing:** You can edit [`config.json`](../config.json) directly with any text editor.

## Drawing Settings

### Delay

**Range:** 0.01 - 10.0 seconds  
**Default:** 0.15 seconds  
**Description:** Controls the timing delay for each stroke. Increase if your machine is slow and does not respond well to extremely fast input.

**Impact:**
- Higher values = Slower drawing, more reliable
- Lower values = Faster drawing, may cause missed strokes

### Pixel Size

**Range:** 3 - 50 pixels  
**Default:** 12 pixels  
**Description:** Controls the detail level of the drawing. Lower values create more detailed results but require longer drawing time.

**Impact:**
- Higher values = More detail, longer drawing time
- Lower values = Less detail, faster drawing

### Precision

**Range:** 0.0 - 1.0  
**Default:** 0.896  
**Description:** Affects custom color accuracy for each pixel. At lower values, color variety is greatly reduced. At 1.0 accuracy, every pixel will have perfect colors.

**Impact:**
- Higher values = More accurate colors, slower processing
- Lower values = Fewer colors, faster processing

**Recommendation:** 0.9 for most use cases

### Jump Delay

**Range:** 0.0 - 2.0 seconds  
**Default:** 0.059 seconds  
**Description:** Adds delay when cursor jumps more than 5 pixels between strokes. Helps prevent unintended strokes from rapid cursor movement.

**When Used:**
- Large jumps between non-adjacent line segments
- Cursor movements across canvas regions

## Drawing Modes

### Slotted Mode

**Description:** Simple color-to-lines mapping mode.

**Behavior:**
- Each horizontal run of the same color = one line segment
- Colors are processed in order encountered
- No color frequency sorting
- Faster processing

**Best For:**
- Simple images
- Faster processing requirements
- Limited color palettes

### Layered Mode

**Description:** Advanced color layering with frequency sorting.

**Behavior:**
1. Count color frequency (total pixel coverage)
2. Sort colors by frequency (most used first)
3. Merge adjacent lines of lower-frequency colors
4. Higher-frequency colors paint over lower-frequency ones

**Best For:**
- Complex images with many colors
- Better visual results
- Images with overlapping color regions

## Drawing Options

### Ignore White Pixels

**Type:** Checkbox option  
**Default:** `false`  
**Description:** Skip drawing white pixels of an image. Useful when the canvas is white.

**Use Case:**
- Images with white backgrounds
- To create transparent drawings
- To reduce drawing time

### Use Custom Colors

**Type:** Checkbox option  
**Default:** `false`  
**Description:** Enable advanced color mixing using the custom colors spectrum.

**Impact:**
- When enabled: Scans custom color spectrum for color matching
- When disabled: Uses only palette colors
- **Significantly** increases draw duration

## Palette Configuration

### Status

**Type:** Boolean  
**Values:** `true` or `false`  
**Description:** Indicates whether the palette has been initialized.

### Box

**Type:** Array `[x1, y1, x2, y2]`  
**Description:** Screen coordinates of the palette region.

**Format:** Upper-left and lower-right corners.

### Rows / Columns

**Type:** Integer  
**Description:** Define the palette grid dimensions.

**Example:** 7 columns × 37 rows = 259 colors

### Color Coords

**Type:** Object  
**Format:** `{"(r, g, b)": [x, y], ...}`  
**Description:** Maps each RGB color to its screen coordinates.

**Note:** Keys are strings because JSON doesn't support tuple keys.

### Valid Positions

**Type:** Array `[0, 1, 2, ...]`  
**Description:** Indices of valid palette cells.

**Use Case:**
- Exclude broken or unused colors
- Mark only the cells you want to use

### Manual Centers

**Type:** Object  
**Format:** `{"0": [x, y], "1": [x, y], ...}`  
**Description:** Exact center points for each palette cell.

**Use Case:**
- Precise color selection on irregular palettes
- Override automatic center calculation

### Preview

**Type:** String (path)  
**Description:** Path to captured palette preview image.

## Canvas Configuration

### Status

**Type:** Boolean  
**Values:** `true` or `false`  
**Description:** Indicates whether the canvas has been initialized.

### Box

**Type:** Array `[x1, y1, x2, y2]`  
**Description:** Screen coordinates of the canvas drawing area.

**Format:** Upper-left and lower-right corners.

### Preview

**Type:** String (path)  
**Description:** Path to captured canvas preview image.

## Custom Colors Configuration

### Status

**Type:** Boolean  
**Values:** `true` or `false`  
**Description:** Indicates whether custom colors have been initialized.

### Box

**Type:** Array `[x1, y1, x2, y2]`  
**Description:** Screen coordinates of the custom color spectrum region.

### Preview

**Type:** String (path)  
**Description:** Path to captured custom colors preview image.

## New Layer Configuration

### Status

**Type:** Boolean  
**Values:** `true` or `false`  
**Description:** Indicates whether the new layer feature is configured.

### Coords

**Type:** Array `[x, y]`  
**Description:** Screen coordinates of the new layer button.

### Enabled

**Type:** Boolean  
**Values:** `true` or `false`  
**Description:** Whether automatic layer creation is active during drawing.

### Modifiers

**Type:** Object  
**Format:** `{"ctrl": bool, "alt": bool, "shift": bool}`  
**Description:** Modifier keys to hold when clicking the new layer button.

**Use Case:**
- Applications that require keyboard shortcuts for layer creation
- Example: Shift+Click to create new layer

## Color Button Configuration

### Status

**Type:** Boolean  
**Values:** `true` or `false`  
**Description:** Indicates whether the color button feature is configured.

### Coords

**Type:** Array `[x, y]`  
**Description:** Screen coordinates of the color picker button.

### Enabled

**Type:** Boolean  
**Values:** `true` or `false`  
**Description:** Whether automatic color button clicking is active during drawing.

### Delay

**Type:** Float  
**Range:** 0.01 - 5.0 seconds  
**Default:** 0.1 seconds  
**Description:** Time to wait after clicking the color button before selecting color.

**Use Case:**
- Applications that take time to open color picker
- Adjust based on your application's response time

### Modifiers

**Type:** Object  
**Format:** `{"ctrl": bool, "alt": bool, "shift": bool}`  
**Description:** Modifier keys to hold when clicking the color button.

## Color Button Okay Configuration

### Status

**Type:** Boolean  
**Values:** `true` or `false`  
**Description:** Indicates whether the color button okay feature is configured.

### Coords

**Type:** Array `[x, y]`  
**Description:** Screen coordinates of the color confirmation button.

### Enabled

**Type:** Boolean  
**Values:** `true` or `false`  
**Description:** Whether automatic color button okay clicking is active during drawing.

### Modifiers

**Type:** Object  
**Format:** `{"ctrl": bool, "alt": bool, "shift": bool}`  
**Description:** Modifier keys to hold when clicking the color button okay button.

## Hotkeys

### Pause Key

**Type:** String  
**Default:** `"p"`  
**Description:** Key used to pause/resume drawing.

**Valid Values:**
- Any single character key (e.g., 'p', 's', ' ')
- Function keys (e.g., 'f1', 'f2')
- Special keys (e.g., 'space', 'tab')

**Behavior:**
- Press during drawing: Toggle pause/resume
- Press when not drawing: Set the pause key

### ESC Key

**Type:** Global hotkey  
**Description:** Emergency stop for all drawing operations.

**Behavior:**
- Pressing ESC immediately stops drawing
- Works during full drawing, test draw, and simple test draw

## Palette Advanced Features

### Manual Color Selection Modes

#### Toggle Mode

**Description:** Click grid cells to mark them as valid (green) or invalid (red).

**Usage:**
1. Click "Edit Colors" in Setup Window
2. Click cells to toggle their state
3. Click "Done" to save

#### Pick Centers Mode

**Description:** Click exact center points for each palette cell.

**Usage:**
1. Click "Edit Colors" in Setup Window
2. Click "Pick Centers" button
3. Click a cell, then click the center point on your palette
4. System automatically moves to next color cell
5. Press ESC to stop

#### Auto-Estimate

**Description:** Automatically calculate center points using grid-based estimation.

**Algorithm:**
```python
cell_width = palette_width / columns
cell_height = palette_height / rows
center_x = col * cell_width + cell_width / 2
center_y = row * cell_height + cell_height / 2
```

**Usage:**
1. Click "Edit Colors" in Setup Window
2. Click "Auto-Estimate Centers"
3. Review overlay showing estimated positions
4. Click "Done" to save

#### Precision Estimate

**Description:** Advanced center calculation using reference point selection for maximum accuracy.

**Modes:**

##### Single Column Mode

**When to use:** Vertical palettes (1 column, multiple rows)

**Reference Points:**
1. Center of first color box in first row
2. Center of first color box in second row
3. Center of first color box in last row

**Calculation:**
```python
row_spacing = (last_row_center - first_row_center) / (last_row_index - first_row_index)
```

##### 1 Row Mode

**When to use:** Horizontal palettes (1 row, multiple columns)

**Reference Points:**
1. Center of first color box (leftmost)
2. Center of second color box
3. Center of last color box (rightmost)

**Calculation:**
```python
col_spacing = (last_col_center - first_col_center) / (last_col_index - first_col_index)
```

##### Multi-Row Mode

**When to use:** Grid palettes (multiple rows and columns)

**Reference Points:**
1. First row: first box, second box, last box
2. Second row: first box (if > 2 rows)
3. Last row: first box, last box

**Calculation:**
```python
col_spacing = (first_row_last - first_row_first) / (last_col_index - first_col_index)
row_spacing = (last_row_first - first_row_first) / (last_row_index - first_row_index)
```

**Usage:**
1. Click "Edit Colors" in Setup Window
2. Click "Precision Estimate"
3. Follow on-screen instructions to click reference points
4. System calculates all centers
5. Review overlay showing estimated positions
6. Click "Done" to save

## Cache Configuration

Cache files are automatically created in the `cache/` directory.

### Cache File Naming

**Format:** `cache/{image_hash}_{settings_hash}.json`

**Components:**
- `image_hash` - MD5 hash of source image (first 8 characters)
- `settings_hash` - MD5 hash of drawing settings

### Cache Contents

```json
{
  "cmap": {
    "(r, g, b)": [(start, end), ...]
  },
  "settings": [delay, step, accuracy, jump_delay],
  "flags": 0,
  "mode": "layered",
  "canvas": [x, y, w, h],
  "image_hash": "abc12345",
  "timestamp": 1234567890.0,
  "palette_info": {
    "colors_pos": {...},
    "colors": [...]
  }
}
```

### Cache Validation

Cache is considered valid when:
- File exists
- Age < 24 hours
- Settings match current configuration
- Canvas dimensions match

### Cache Invalidation

Cache is automatically invalidated when:
- Drawing settings change
- Canvas dimensions change
- Palette configuration change
- 24 hours have passed

## Configuration Tips

### Performance Optimization

1. **Use Pre-compute** for images you'll draw multiple times
2. **Adjust Pixel Size** based on desired detail vs. speed tradeoff
3. **Enable "Ignore White Pixels"** for images with large white areas
4. **Use Layered Mode** for better visual results on complex images
5. **Fine-tune Jump Delay** for optimal cursor movement

### Palette Setup Tips

1. **Use Auto-Estimate** for quick initial setup on regular grids
2. **Use Precision Estimate** for maximum accuracy on irregular palettes
3. **Toggle Invalid Positions** to exclude broken or unused colors
4. **Preview captured regions** to verify correct configuration
5. **For Precision Estimate with multiple rows**, ensure you have at least 2 valid rows

### Color Button Tips

1. **Set appropriate delay** for your application's color picker opening time
2. **Use modifier keys** if your application requires them to access color picker
3. **Enable "Color Button Okay"** if your application requires clicking a confirmation button
4. **Test color button configuration** with a simple test draw before starting a full drawing

## Troubleshooting Configuration Issues

### Palette Not Initializing

**Symptoms:**
- "Palette not initialized" error when trying to draw
- Setup window shows "NOT INITIALIZED" status

**Solutions:**
1. Click "Initialize" in Setup Window
2. Ensure rows and columns are set correctly
3. Verify palette box coordinates are correct

### Canvas Not Initializing

**Symptoms:**
- "Canvas not initialized" error when trying to draw
- Setup window shows "NOT INITIALIZED" status

**Solutions:**
1. Click "Initialize" in Setup Window
2. Verify canvas box coordinates are correct

### Custom Colors Not Working

**Symptoms:**
- Colors appear incorrect when using custom colors
- Drawing uses palette colors instead

**Solutions:**
1. Ensure custom colors box is correctly configured
2. Verify spectrum scanning has completed (check console for "[Spectrum] Scanned" message)
3. Test with a simple test draw to verify color selection

### Drawing Too Slow

**Symptoms:**
- Drawing takes much longer than expected
- Cursor movements are sluggish

**Solutions:**
1. Increase Delay setting
2. Increase Pixel Size (less detail = faster)
3. Check for background applications consuming CPU
4. Close unnecessary applications

### Drawing Too Fast / Missed Strokes

**Symptoms:**
- Drawing completes too quickly
- Colors are wrong or strokes are missed

**Solutions:**
1. Decrease Delay setting
2. Increase Pixel Size (more detail = more reliable)
3. Check Jump Delay setting

### Colors Not Selecting Correctly

**Symptoms:**
- Wrong colors are being selected
- Palette clicks miss the intended color

**Solutions:**
1. Use manual center picking for precise selection
2. Use Precision Estimate for maximum accuracy
3. Check valid positions are marked correctly
4. Review palette preview to verify configuration

## See Also

- [API Reference](./api.md)
- [Architecture](./architecture.md)
- [Usage Guide](./usage-guide.md)
