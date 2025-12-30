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
- **Full Drawing**: Complete automated image recreation
- **Pause/Resume**: Configurable hotkey for interruption and continuation
- **Mid-Stroke Recovery**: Resume drawing from exact interruption point

### Performance Features
- **Intelligent Caching**: Pre-compute image processing for instant subsequent runs
- **Layered Processing**: Advanced color layering algorithms for optimal results
- **Background Processing**: Non-blocking computation with progress updates
- **Memory Efficient**: Optimized for large images and long drawing sessions

### Additional Features
- **New Layer Automation**: Automatic layer creation with keyboard modifier support
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
4. Configure your preferred settings using the control panel sliders

### Basic Drawing
1. Enter an image URL or select a local file
2. Click **"Pre-compute"** (optional, for caching)
3. Click **"Test Draw"** to calibrate brush size with the first 20 lines
4. Adjust brush settings in your painting application
5. Click **"Start"** for complete automated drawing

### Controls
- **ESC**: Stop current drawing operation
- **Custom Pause Key**: Pause/resume drawing (default: 'p')
- **Setup**: Configure palette, canvas, and custom colors
- **Pre-compute**: Cache image processing for faster subsequent runs
- **Test Draw**: Draw sample lines for brush calibration
- **Start**: Begin full image drawing

## Configuration

### Drawing Settings
- **Delay**: Stroke timing (0.0-1.0 seconds)
- **Pixel Size**: Detail level (3-50 pixels)
- **Precision**: Color accuracy (0.0-1.0)
- **Jump Delay**: Cursor movement optimization (0.0-2.0 seconds)

### Options
- **Ignore White Pixels**: Skip drawing white areas
- **Use Custom Colors**: Enable advanced color mixing
- **New Layer**: Automatic layer creation with modifiers

### Hotkeys
- **Pause Key**: Configurable key for pause/resume (any keyboard key)
- **ESC**: Emergency stop for all operations

## Architecture

The application consists of three main components:

### Bot (`bot.py`)
Core drawing engine handling image processing, mouse automation, and drawing algorithms.

### Window (`ui/window.py`)
Graphical user interface with real-time controls and progress monitoring.

### Setup (`ui/setup.py`)
Configuration wizard for initializing palette, canvas, and custom color regions.

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

### Performance Tips
- Use **Pre-compute** for images you'll draw multiple times
- Adjust **Pixel Size** based on desired detail level
- Enable **Ignore White Pixels** for images with large white areas
- Fine-tune **Jump Delay** for optimal cursor movement

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
