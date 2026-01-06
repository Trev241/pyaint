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
- **Auto-Estimate Centers**: Automatically calculate center points for all valid colors
- **Grid-Based Configuration**: Visual grid for easy palette cell selection
- **Preview Generation**: Visual preview of captured palette, canvas, and custom color regions

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
3. Initialize the **Palette**, **Canvas**, and **Custom Colors** by clicking the corners as prompted
4. Configure palette dimensions (rows and columns) if needed
5. Optionally use advanced palette features:
   - Toggle valid/invalid palette cells
   - Pick exact center points for precise color selection
   - Auto-estimate centers for quick setup
6. Configure your preferred settings using the control panel sliders

### Basic Drawing
1. Enter an image URL or select a local file
2. Click **"Pre-compute"** (optional, for caching and time estimation)
3. Click **"Simple Test Draw"** for quick brush calibration or **"Test Draw"** for detailed calibration
4. Adjust brush settings in your painting application
5. Click **"Start"** for complete automated drawing

### Region-Based Redrawing
1. Load your image
2. Click and drag on the image preview to select a region
3. Click **"Redraw Region"** to draw only the selected area
4. Useful for fixing mistakes or adding details without full redraw

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

### Hotkeys
- **Pause Key**: Configurable key for pause/resume (any keyboard key)
- **ESC**: Emergency stop for all operations

### Palette Configuration
- **Rows/Columns**: Define palette grid dimensions
- **Valid Positions**: Select which palette cells to use
- **Manual Centers**: Pick exact center points for each color
- **Auto-Estimate**: Automatically calculate center positions

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

## Troubleshooting

### Common Issues
- **Drawing not starting**: Ensure palette and canvas are properly initialized
- **Colors incorrect**: Check custom colors setup and precision settings
- **Slow performance**: Reduce pixel size or increase delay settings
- **Application not responding**: Use ESC to stop and restart
- **Palette colors not selecting**: Verify valid positions are marked and centers are correctly picked

### Performance Tips
- Use **Pre-compute** for images you'll draw multiple times
- Adjust **Pixel Size** based on desired detail level
- Enable **Ignore White Pixels** for images with large white areas
- Fine-tune **Jump Delay** for optimal cursor movement
- Use **Layered mode** for better visual results, **Slotted mode** for faster processing

### Palette Tips
- Use **Auto-Estimate Centers** for quick initial setup
- Use **Pick Centers** for precise color selection on complex palettes
- Toggle invalid positions to exclude broken or unused colors
- Preview captured regions to verify correct configuration

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

### Contributing
Suggestions and contributions are welcome. Please ensure compatibility with the existing codebase and maintain the application's stability.

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0).

## Credits

This project is a fork of the original [pyaint](https://github.com/Trev241/pyaint) by Trev241. The original implementation provided the foundation for this enhanced version with additional features and improvements.

---

*Pyaint - Bringing digital images to life through automated artistry*
