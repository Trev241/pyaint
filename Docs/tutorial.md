# Pyaint Tutorial

A comprehensive guide to using Pyaint - an intelligent drawing automation tool that converts images into precise mouse movements for painting applications.

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Getting Started](#getting-started)
4. [Initial Setup](#initial-setup)
5. [Advanced Palette Configuration](#advanced-palette-configuration)
6. [Drawing Settings](#drawing-settings)
7. [Drawing Workflow](#drawing-workflow)
8. [Region-Based Redrawing](#region-based-redrawing)
9. [Controls](#controls)
10. [Tips & Best Practices](#tips--best-practices)
11. [Troubleshooting](#troubleshooting)

---

## Introduction

Pyaint is a Python-based automation tool designed to recreate digital images through automated brush strokes in painting applications. It's compatible with MS Paint, Clip Studio Paint, skribbl, and most drawing software.

### Key Features

- **Multi-Application Support**: Works with various drawing applications
- **Dual Input Methods**: Load images from local files or remote URLs
- **High-Precision Drawing**: Near-perfect color accuracy with customizable settings
- **Real-time Progress**: Live tracking with estimated completion time
- **Intelligent Caching**: Pre-compute image processing for instant subsequent runs
- **Pause/Resume**: Configurable hotkey for interruption and continuation
- **Region-Based Redrawing**: Select specific image areas to redraw

---

## Installation

### Requirements

- Python 3.8 or higher (3.8 recommended)
- Windows operating system

### Setup Steps

1. Clone or download the repository

2. **Optional: Create a conda environment** (recommended for isolation):
   ```bash
   conda create -n pyaint python=3.8
   conda activate pyaint
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   python main.py
   ```

<!-- IMAGE: Screenshot of terminal showing successful installation and running the application -->

---

## Getting Started

When you first launch Pyaint, you'll see the main window with three panels:

1. **Control Panel** (left): Drawing settings and action buttons
2. **Preview Panel** (right): Image loading and preview
3. **Tooltip Panel** (bottom): Status messages and progress updates

<!-- IMAGE: Screenshot of the main Pyaint window with all panels visible -->

The application will prompt you to begin by pressing **"Setup"** to configure your drawing environment.

---

## Initial Setup

The Setup process configures the tools Pyaint needs to interact with your drawing application. Click the **"Setup"** button to open the Setup window.

### Tools to Configure

You need to configure the following tools:

1. **Palette** - Your color palette in the drawing application
2. **Canvas** - The drawing area where images will be painted
3. **Custom Colors** - The custom color spectrum (optional)
4. **New Layer** - Button to create new layers (optional)
5. **Color Button** - Button to open color picker (optional)
6. **Color Button Okay** - Button to confirm color selection (optional)

<!-- IMAGE: Screenshot of the Setup window showing all tools -->

### Configuring the Palette

The Palette is essential - it tells Pyaint where your colors are located.

1. Set the **Rows** and **Columns** for your palette grid
2. Click **"Initialize"**
3. You'll be prompted to click on the **UPPER LEFT** and **LOWER RIGHT** corners of your palette
4. The system will capture and scan the colors

<!-- IMAGE: Screenshot showing the palette selection process with corners being clicked -->

After initialization, you can click **"Preview"** to see the captured palette.

### Configuring the Canvas

The Canvas defines where Pyaint will draw the image.

1. Click **"Initialize"** next to Canvas
2. Click on the **UPPER LEFT** and **LOWER RIGHT** corners of your drawing area
3. The canvas will be captured and saved

<!-- IMAGE: Screenshot showing canvas selection -->

### Configuring Custom Colors (Optional)

Custom Colors allow for unlimited color options through a spectrum.

1. Click **"Initialize"** next to Custom Colors
2. Click on the **UPPER LEFT** and **LOWER RIGHT** corners of your custom color spectrum
3. The system will scan the spectrum and create a color-to-position map

<!-- IMAGE: Screenshot showing custom colors spectrum selection -->

### Configuring New Layer (Optional)

If your drawing application supports layers, you can configure Pyaint to automatically create new layers.

1. Click **"Initialize"** next to New Layer
2. Click on the **New Layer button** location in your application
3. Optionally, select modifier keys (CTRL, ALT, SHIFT) if needed

<!-- IMAGE: Screenshot showing New Layer button configuration -->

### Configuring Color Button (Optional)

Some applications require clicking a button to access the color picker.

1. Click **"Initialize"** next to Color Button
2. Click on the **Color Button** location
3. Set the **Delay** (time to wait for the color picker to open)
4. Optionally, select modifier keys (CTRL, ALT, SHIFT) if needed

<!-- IMAGE: Screenshot showing Color Button configuration -->

### Configuring Color Button Okay (Optional)

If your application requires confirming color selection:

1. Click **"Initialize"** next to Color Button Okay
2. Click on the **Okay/Confirm button** location
3. Enable the checkbox to use this feature

<!-- IMAGE: Screenshot showing Color Button Okay configuration -->

---

## Advanced Palette Configuration

After initializing the palette, you can access advanced features by clicking **"Edit Colors"**.

### Toggle Valid/Invalid Colors

Some palette colors may be broken or unused. You can mark them as invalid:

1. Click **"Edit Colors"** to open the color selection window
2. Click on grid cells to toggle between **Valid (green)** and **Invalid (red)**
3. Click **"Done"** when finished

<!-- IMAGE: Screenshot showing the color selection window with some cells marked as invalid -->

### Pick Exact Center Points

For maximum precision, you can manually pick the exact center point for each color:

1. In the color selection window, click **"Pick Centers"**
2. Click on a color cell in the grid
3. Click on the exact center point of that color on your palette
4. The system automatically moves to the next color
5. Press **ESC** to stop at any time

<!-- IMAGE: Screenshot showing Pick Centers mode with center points being picked -->

### Auto-Estimate Centers

For quick setup on regular palettes:

1. Click **"Auto-Estimate Centers"**
2. The system calculates center points using grid-based estimation
3. An overlay shows the estimated positions for 5 seconds
4. Yellow cells indicate colors with estimated centers

<!-- IMAGE: Screenshot showing auto-estimated centers overlay on the palette -->

### Precision Estimate

For maximum accuracy on irregular or complex palettes:

1. Click **"Precision Estimate"**
2. The system detects your palette layout and provides instructions
3. **Single Column Mode** (vertical palettes): Click first row (1st), second row (1st), last row (1st)
4. **1 Row Mode** (horizontal palettes): Click first box, second box, last box
5. **Multi-Row Mode** (grid palettes): Click first row (1st, 2nd, last), second row (1st), last row (1st, last)
6. The system calculates exact spacing and estimates all centers

<!-- IMAGE: Screenshot showing precision estimate instructions -->

After precision estimation:
- Yellow cells show estimated centers
- Click **"Done"** to accept
- Click **"Pick Centers"** to manually adjust

<!-- IMAGE: Screenshot showing completed precision estimate with yellow cells -->

---

## Drawing Settings

### Main Settings

Located in the Control Panel, these settings control drawing behavior:

#### Delay

- **Range**: 0.01 - 10.0 seconds
- **Purpose**: Controls the duration of each stroke
- **Recommendation**: Increase if your machine is slow and doesn't respond well to fast input
- **Tip**: Lower values = faster drawing but may cause missed strokes on slow systems

<!-- IMAGE: Screenshot showing Delay setting -->

#### Pixel Size

- **Range**: 3 - 50 pixels
- **Purpose**: Controls detail level
- **Lower values**: More detail, longer draw time
- **Higher values**: Less detail, faster drawing
- **Note**: This does NOT affect your brush size - you must adjust that manually in your drawing app

<!-- IMAGE: Screenshot showing Pixel Size slider -->

#### Precision

- **Range**: 0.0 - 1.0
- **Purpose**: Controls custom color accuracy for each pixel
- **Lower values**: Reduced color variety, faster processing
- **Higher values**: Better color matching, slower processing
- **Recommendation**: 0.9 for good balance

<!-- IMAGE: Screenshot showing Precision slider -->

#### Jump Delay

- **Range**: 0.0 - 2.0 seconds
- **Purpose**: Adds delay when cursor jumps more than 5 pixels between strokes
- **Recommendation**: 0.5 seconds
- **Tip**: Helps prevent unintended strokes from rapid cursor movement

<!-- IMAGE: Screenshot showing Jump Delay slider -->

### Drawing Mode

Choose between two processing modes:

#### Slotted Mode

- Simple color-to-lines mapping
- Faster processing
- Less memory usage
- Better for simple images

#### Layered Mode (Default)

- Advanced color layering with frequency sorting
- Better visual results
- Fewer color switches
- Optimized for complex images

<!-- IMAGE: Screenshot showing Draw Mode dropdown -->

### Miscellaneous Settings

#### Ignore White Pixels

- Skips drawing white areas
- Useful when the canvas is white
- Reduces drawing time significantly for images with large white areas

<!-- IMAGE: Screenshot showing Ignore White Pixels checkbox -->

#### Use Custom Colors

- Enables advanced color mixing using the custom color spectrum
- Considerably lengthens draw duration
- Provides unlimited color options

<!-- IMAGE: Screenshot showing Use Custom Colors checkbox -->

#### Enable New Layer

- Automatically creates a new layer before drawing
- Requires New Layer to be configured in Setup
- Supports modifier keys (CTRL, ALT, SHIFT)

<!-- IMAGE: Screenshot showing Enable New Layer checkbox -->

#### Enable Color Button

- Automatically clicks the color button before selecting colors
- Requires Color Button to be configured in Setup
- Set delay to allow time for color picker to open

<!-- IMAGE: Screenshot showing Enable Color Button checkbox -->

### Pause Key

- Configure any keyboard key to pause/resume drawing
- Default: 'p'
- Click in the Pause Key field and press your desired key

<!-- IMAGE: Screenshot showing Pause Key field -->

---

## Drawing Workflow

### Step 1: Load an Image

You can load images in two ways:

#### From URL

1. Enter the image URL in the text field
2. Click **"Search"**
3. The image will be downloaded and displayed in the preview

<!-- IMAGE: Screenshot showing URL loading -->

#### From File

1. Click **"Open File"**
2. Select an image from your computer
3. The image will be displayed in the preview

<!-- IMAGE: Screenshot showing file browser dialog -->

### Step 2: Pre-Compute (Optional)

For images you'll draw multiple times, pre-computing saves time:

1. Click **"Pre-compute"**
2. The image is processed and cached
3. Estimated drawing time is displayed
4. Future draws will use the cached data

<!-- IMAGE: Screenshot showing pre-compute progress and completion message -->

### Step 3: Test Draw

Before the full drawing, test to calibrate your brush size:

#### Simple Test Draw

1. Click **"Simple Test Draw"**
2. 5 horizontal lines (1/4 canvas width each) will be drawn
3. No color picking occurs - use your currently selected color
4. Adjust brush size in your drawing app based on the result

<!-- IMAGE: Screenshot showing simple test draw result -->

#### Test Draw

1. Click **"Test Draw"**
2. First 20 lines of the image will be drawn
3. Includes color switching
4. Adjust brush size based on the test result

<!-- IMAGE: Screenshot showing test draw result -->

### Step 4: Full Drawing

1. Click **"Start"**
2. A warning shows the controls (ESC to stop, pause key to pause/resume)
3. The window minimizes
4. Drawing begins with real-time progress tracking

<!-- IMAGE: Screenshot showing drawing in progress with progress indicator -->

### Drawing Completion

When drawing completes:
- The window restores
- Actual time vs estimated time is displayed
- Success message is shown

<!-- IMAGE: Screenshot showing completed drawing with time comparison -->

---

## Region-Based Redrawing

Region-based redrawing allows you to fix mistakes or add details without a full redraw.

### Select a Region

1. Load your image
2. Click **"Pick Region"** in the Redraw Region section
3. Click on the **UPPER LEFT** corner of the area you want to redraw
4. Click on the **LOWER RIGHT** corner of the area
5. The selected region is displayed

<!-- IMAGE: Screenshot showing region selection on the preview -->

### Draw the Region

1. After selecting a region, click **"Draw Region"**
2. Only the selected area will be drawn
3. Useful for fixing mistakes or adding details

<!-- IMAGE: Screenshot showing region redraw in progress -->

---

## Controls

### ESC Key

- **Function**: Emergency stop for all operations
- **When to use**: To immediately stop any drawing operation
- **Behavior**: Stops the bot and clears the termination flag

<!-- IMAGE: Diagram showing ESC key usage -->

### Pause Key

- **Function**: Pause and resume drawing
- **Default**: 'p' (configurable)
- **When to use**: To temporarily pause drawing and resume later
- **Behavior**: 
  - First press: Pauses drawing (saves current state)
  - Second press: Resumes from exact interruption point
- **Mid-Stroke Recovery**: Can resume even in the middle of a stroke

<!-- IMAGE: Diagram showing pause/resume workflow -->

---

## Tips & Best Practices

### Performance Optimization

1. **Use Pre-Compute** for images you'll draw multiple times
2. **Adjust Pixel Size** based on desired detail level
3. **Enable "Ignore White Pixels"** for images with large white areas
4. **Fine-tune Jump Delay** for optimal cursor movement
5. **Use Layered mode** for better visual results
6. **Use Slotted mode** for faster processing

### Palette Tips

1. **Use Auto-Estimate Centers** for quick initial setup on regular grids
2. **Use Precision Estimate** for maximum accuracy on irregular palettes
3. **Use Pick Centers** for precise color selection on complex palettes
4. **Toggle invalid positions** to exclude broken or unused colors
5. **Preview captured regions** to verify correct configuration

### Color Button Tips

1. **Set appropriate delay** for your application's color picker opening time
2. **Use modifier keys** if your application requires them
3. **Enable "Color Button Okay"** if your application requires confirmation
4. **Test color button configuration** with a simple test draw before starting

### Drawing Tips

1. **Always test draw first** to calibrate brush size
2. **Start with higher pixel size** for faster results, reduce if needed
3. **Use pause/resume** to take breaks during long drawings
4. **Use region redraw** to fix mistakes without full redraw
5. **Monitor progress** to ensure drawing is proceeding correctly

---

## Troubleshooting

### Common Issues

#### Drawing not starting

**Symptoms**: Clicking Start doesn't begin drawing

**Solutions**:
- Ensure palette and canvas are properly initialized (status should be green)
- Check that an image is loaded in the preview
- Verify the image file is valid

<!-- IMAGE: Screenshot showing properly initialized tools -->

#### Colors incorrect

**Symptoms**: Drawn colors don't match the source image

**Solutions**:
- Check custom colors setup and precision settings
- Verify palette colors are correctly scanned
- Increase Precision setting for better color matching
- Ensure valid positions include all needed colors

<!-- IMAGE: Screenshot comparing incorrect vs correct colors -->

#### Slow performance

**Symptoms**: Drawing takes much longer than expected

**Solutions**:
- Reduce Pixel Size setting (less detail = faster)
- Increase Delay setting if strokes are being missed
- Enable "Ignore White Pixels" for images with large white areas
- Check if your system is under heavy load

<!-- IMAGE: Screenshot showing performance settings -->

#### Application not responding

**Symptoms**: Drawing app freezes or doesn't respond to bot input

**Solutions**:
- Use ESC to stop and restart
- Increase Delay setting to give app more time
- Check if Jump Delay is too low
- Verify your drawing app is compatible

<!-- IMAGE: Screenshot showing app not responding -->

#### Palette colors not selecting

**Symptoms**: Bot doesn't click on the correct colors

**Solutions**:
- Verify valid positions are marked correctly
- Check that centers are correctly picked
- Use Precision Estimate for better accuracy
- Preview the palette to verify it was captured correctly

<!-- IMAGE: Screenshot showing palette preview -->

#### Custom colors not working

**Symptoms**: Custom color spectrum isn't being used

**Solutions**:
- Ensure custom colors box is correctly configured
- Verify "Use Custom Colors" checkbox is enabled
- Check that spectrum scanning has completed
- Preview the custom colors region

<!-- IMAGE: Screenshot showing custom colors preview -->

### Error Messages

#### "Palette not initialized"

**Cause**: Palette tool hasn't been configured

**Solution**: Run Setup and initialize the Palette

#### "Canvas not initialized"

**Cause**: Canvas tool hasn't been configured

**Solution**: Run Setup and initialize the Canvas

#### "No valid colors selected"

**Cause**: All palette colors are marked as invalid

**Solution**: In Edit Colors, mark at least one color as valid (green)

#### "Config file missing or invalid"

**Cause**: Configuration file is corrupted or missing

**Solution**: The app will use default settings - re-run Setup to configure tools

---

## Summary

Pyaint provides a powerful way to automate drawing in your favorite painting applications. By following this tutorial, you should be able to:

1. Set up your drawing environment
2. Configure advanced palette features for maximum accuracy
3. Load and process images
4. Draw with customizable settings
5. Use pause/resume for long drawings
6. Fix mistakes with region-based redrawing

For more detailed information, refer to the API documentation and other guides in the Docs folder.

---

## Additional Resources

- [API Reference](./api.md) - Complete API documentation
- [Architecture Documentation](./architecture.md) - System architecture details
- [Configuration Guide](./configuration.md) - Configuration options
- [Troubleshooting Guide](./troubleshooting.md) - Detailed troubleshooting

<!-- IMAGE: Screenshot of the Docs folder contents -->
