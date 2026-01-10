# Pyaint

An intelligent drawing automation tool that converts images into precise mouse movements for painting applications. Built with Python and designed for artists and designers who want to recreate digital images through automated brush strokes.

## Features

### Core Functionality
- **Multi-Application Support**: Compatible with MS Paint, Clip Studio Paint, skribbl, and most drawing software
- **Dual Input Methods**: Load images from local files or remote URLs
- **High-Precision Drawing**: Produces near-perfect color accuracy with customizable precision settings
- **Real-time Progress**: Live progress tracking with estimated completion time

### Advanced Controls
- **Configurable Timing**: Adjustable stroke delay for different system speeds
- **Detail Control**: Pixel size settings for balancing detail vs. drawing time
- **Color Optimization**: Precision settings for color accuracy vs. performance
- **Smart Movement**: Jump delay optimization for large cursor movements
- **Background Handling**: Option to ignore white pixels for cleaner results
- **Skip First Color**: Skip the first color when drawing - useful when you want to start from the second color or when the first color is already present on the canvas

### Drawing Modes
- **Test Draw**: Draw first 20 lines to calibrate brush size before full drawing
- **Simple Test Draw**: Quick 5-line brush calibration without color picking
- **Full Drawing**: Complete automated image recreation
- **Slotted Mode**: Simple color-to-lines mapping for faster processing
- **Layered Mode**: Advanced color layering with frequency sorting (default)
- **Region-Based Redrawing**: Select specific image areas to redraw
- **Pause/Resume**: Configurable hotkey for interruption and continuation
- **Mid-Stroke Recovery**: Resume drawing from exact interruption point

### Performance Features
- **Intelligent Caching**: Pre-compute image processing for instant subsequent runs
- **Cache Validation**: Validates cache matches current settings, canvas, and image
- **Cache Invalidation**: Auto-invalidates after 24 hours for freshness
- **Layered Processing**: Advanced color layering algorithms for optimal results
- **Background Processing**: Non-blocking computation with progress updates
- **Memory Efficient**: Optimized for large images and long drawing sessions
- **Time Estimation**: Pre-draw time estimation based on coordinate data

### Advanced Palette Features
- **Manual Color Center Picking**: Click to set exact center points for each palette color
- **Valid Positions Selection**: Toggle which palette colors are valid/invalid
- **Auto-Estimate Centers**: Automatically calculate center points using grid-based estimation
- **Precision Estimate**: Advanced center calculation using reference point selection for maximum accuracy
  - **Single Column Mode**: Pick first row (1st box), second row (1st box), and last row (1st box) to calculate vertical spacing
  - **1 Row Mode**: Pick first box, second box, and last box of the row to calculate horizontal spacing
  - **Multi-Row Mode**: Pick first row (1st, 2nd, last boxes), second row (1st box), and last row (1st, last boxes)
  - Automatically calculates spacing between boxes and rows for precise center estimation
- **Grid-Based Configuration**: Visual grid for easy palette cell selection
- **Preview Generation**: Visual preview of captured palette, canvas, and custom color regions

### Custom Colors Spectrum Scanning
- **Automatic Spectrum Mapping**: Scans the custom color spectrum to create a color-to-position map
- **Intelligent Color Selection**: Automatically finds and clicks the nearest matching color on the spectrum
- **High Precision**: Samples the spectrum at regular intervals for accurate color matching
- **Full Spectrum Support**: Works with continuous color spectrums for unlimited color options

### Color Button Features
- **Color Button Click**: Automatically clicks the color button to open the color picker
- **Color Button Okay**: Optional click to confirm color selection (can be enabled/disabled)
- **Modifier Keys**: Configure CTRL, ALT, SHIFT modifiers for color button clicks
- **Configurable Delay**: Set delay after color button click to allow the color picker to open
- **Application Compatibility**: Supports applications that require clicking a button to access the color picker

### Additional Features
- **New Layer Automation**: Automatic layer creation with keyboard modifier support (Ctrl, Alt, Shift)
- **Settings Persistence**: All preferences automatically saved and restored
- **Windows Compatible**: Optimized for Windows with Python 3.8+
- **Error Recovery**: Robust error handling and graceful failure recovery

## Installation

### Requirements
- Python 3.8 or higher (3.8 recommended)
- Windows operating system

### Setup
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

## Usage

### Initial Setup
1. Launch the application
2. Click **"Setup"** to configure your drawing environment
3. Initialize **Palette**, **Canvas**, and **Custom Colors** by clicking the corners as prompted
4. Configure palette dimensions (rows and columns) if needed
5. Optionally use advanced palette features:
   - Toggle valid/invalid palette cells
   - Pick exact center points for precise color selection
   - Auto-estimate centers for quick setup (uses simple grid calculation)
   - **Precision Estimate** for maximum accuracy (uses reference point selection):
     - Select 3-5 reference points based on your palette's row count
     - System calculates exact spacing between boxes and rows
     - Automatically estimates centers for all valid positions
6. Configure **Color Button** and **Color Button Okay** if your application requires clicking a button to access the color picker:
   - Click the location of the color button
   - Set optional modifier keys (CTRL, ALT, SHIFT) if needed
   - Configure delay after color button click (allows time for the color picker to open)
   - Enable/disable "Color Button Okay" to click the confirmation button after color selection
7. Configure your preferred settings using the control panel sliders

### Basic Drawing
1. Enter an image URL or select a local file
2. Click **"Pre-compute"** (optional, for caching and time estimation)
3. Click **"Simple Test Draw"** for quick brush calibration or **"Test Draw"** for detailed calibration
4. Adjust brush settings in your painting application
5. Click **"Start"** for complete automated drawing

### Region-Based Redrawing
1. Load your image
2. Click **"Pick Region"** to select a specific area on your canvas
3. Click on the upper-left and lower-right corners of the region you want to redraw
4. Click **"Draw Region"** to draw only the selected area
5. Useful for fixing mistakes or adding details without a full redraw
6. The selected region is automatically scaled to match the canvas size

### Controls
- **ESC**: Stop current drawing operation
- **Custom Pause Key**: Pause/resume drawing (default: 'p')
- **Setup**: Configure palette, canvas, and custom colors
- **Pre-compute**: Cache image processing for faster subsequent runs
- **Simple Test Draw**: Quick 5-line brush calibration
- **Test Draw**: Draw sample lines for brush calibration (first 20 lines)
- **Start**: Begin full image drawing
- **Redraw Region**: Draw selected image region only

## Configuration

### Drawing Settings
- **Delay**: Stroke timing (0.0-1.0 seconds)
- **Pixel Size**: Detail level (3-50 pixels)
- **Precision**: Color accuracy (0.0-1.0)
- **Jump Delay**: Cursor movement optimization (0.0-2.0 seconds)

### Drawing Mode
- **Slotted**: Fast processing, simple color-to-lines mapping
- **Layered**: Better visual results, color frequency sorting with line merging

### Options
- **Ignore White Pixels**: Skip drawing white areas
- **Use Custom Colors**: Enable advanced color mixing
- **New Layer**: Automatic layer creation with modifiers
- **Skip First Color**: Skip drawing the first color in the sequence - also skips new layer creation for the first color when enabled

### Hotkeys
- **Pause Key**: Configurable key for pause/resume (any keyboard key)
- **ESC**: Emergency stop for all operations

### Calibration Settings
- **Calibration Step**: Step size for color calibration (1-10 pixels) - lower values provide more accurate calibration but take longer to complete

### Palette Configuration
- **Rows/Columns**: Define palette grid dimensions
- **Valid Positions**: Select which palette cells to use
- **Manual Centers**: Pick exact center points for each color
- **Auto-Estimate**: Automatically calculate center positions

### Color Button Configuration
- **Color Button**: Location of the color picker button in your application
- **Color Button Okay**: Location of the confirmation button (optional)
- **Delay**: Time to wait after clicking color button before selecting color
- **Modifiers**: CTRL, ALT, SHIFT keys to hold when clicking

## Architecture

The application consists of three main components:

### Bot (`bot.py`)
Core drawing engine handling image processing, mouse automation, and drawing algorithms.

### Window (`ui/window.py`)
Graphical user interface with real-time controls and progress monitoring.

### Setup (`ui/setup.py`)
Configuration wizard for initializing palette, canvas, and custom color regions with advanced features like manual center picking and valid position selection.

## Dependencies

- **PyAutoGUI**: Cross-platform GUI automation
- **Pillow**: Image processing and manipulation
- **pynput**: Global keyboard input monitoring
- **NumPy**: Mathematical computations (via Pillow)

## Color Calibration System

The color calibration system provides precise color matching for custom colors by scanning the color spectrum grid and recording the RGB values displayed at each position.

### How It Works
1. **Calibration Process**: The bot systematically moves through the color spectrum grid, clicking at each position and capturing the RGB value shown in the preview spot
2. **Data Storage**: Calibration data is saved to `color_calibration.json` for reuse across sessions
3. **Exact Matching**: When drawing, the bot first tries to find an exact color match within a configurable tolerance (default: 20)
4. **Fallback**: If no exact match is found, it falls back to the nearest color using Euclidean distance calculation

### Usage
1. Run **Setup** and configure the **Custom Colors** grid area
2. Configure the **Color Preview Spot** where the selected color is displayed
3. Click **"Run Calibration"** to start the calibration process
4. Adjust the **Calibration Step** setting (1-10) to balance accuracy vs. calibration time:
   - Lower values (1-3): More accurate, slower calibration
   - Higher values (5-10): Faster calibration, less precise
5. Wait for calibration to complete - progress is displayed in real-time
6. Calibration data is automatically saved and loaded for future drawing sessions

### Benefits
- **Accurate Color Selection**: Solves issues where the bot picks wrong colors (e.g., white instead of yellow)
- **Persistent Data**: Calibration data persists between sessions
- **Configurable Precision**: Adjust step size for your specific needs
- **Tolerance Matching**: Finds exact matches within tolerance before falling back to nearest color

## Troubleshooting

### Common Issues
- **Drawing not starting**: Ensure palette and canvas are properly initialized
- **Colors incorrect**: Check custom colors setup and precision settings
- **Slow performance**: Reduce pixel size or increase delay settings
- **Application not responding**: Use ESC to stop and restart
- **Palette colors not selecting**: Verify valid positions are marked and centers are correctly picked
- **Custom colors not working**: Ensure custom colors box is correctly configured and spectrum scanning has completed

### Performance Tips
- Use **Pre-compute** for images you'll draw multiple times
- Adjust **Pixel Size** based on desired detail level
- Enable **Ignore White Pixels** for images with large white areas
- Fine-tune **Jump Delay** for optimal cursor movement
- Use **Layered mode** for better visual results, **Slotted mode** for faster processing

### Palette Tips
- Use **Auto-Estimate Centers** for quick initial setup on regular grids
- Use **Precision Estimate** for maximum accuracy on irregular or complex palettes
- Use **Pick Centers** for precise color selection on complex palettes requiring manual input
- Toggle invalid positions to exclude broken or unused colors
- Preview captured regions to verify correct configuration
- For Precision Estimate with multiple rows, ensure you have at least 2 valid rows for accurate row spacing calculation

### Color Button Tips
- Set appropriate delay for your application's color picker opening time
- Use modifier keys if your application requires them to access the color picker
- Enable "Color Button Okay" if your application requires clicking a confirmation button
- Test color button configuration with a simple test draw before starting a full drawing

## Development

### Project Structure
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

### Original Videos
You can watch the bot in action [here](https://youtu.be/qXfUc9KuVlg) and [here](https://youtu.be/kj0iqZkIG1k).


#### Usage with gimp
Demostrates the ability to use within gimp, with new layers and custom colors calibrated.

https://github.com/user-attachments/assets/965556a4-f72b-4e24-a9ea-160732c6be51


#### Usage with MS Paint
Demostrates the ability to use within MS Paint, with custom colors calibrated.

https://github.com/user-attachments/assets/50f2f344-8ca9-439b-8722-0175356ad59e

Calibration is recomended but not required. You only need to calibrate once, but if you use a different drawing app,
it's recomened to calibrate. If you can not calibrate then dont worry about it, it'll try it's best to match via Euclidean search.


### Contributing
Suggestions and contributions are welcome. Please ensure compatibility with the existing codebase and maintain the application's stability.

## License

This project is licensed under GNU General Public License v3.0 (GPL-3.0).
