<div align="center">

# Pyaint

**Transform images into automated brush strokes**

An intelligent drawing automation tool that converts images into precise mouse movements for painting applications.

[Quick Start](#installation) • [Usage](#usage) • [Demo](#videos)

</div>

---

## Features

- **Multi-Application Support** - Works with MS Paint, Clip Studio Paint, GIMP, skribbl, and more
- **Dual Input** - Load images from local files or URLs
- **High Precision** - Near-perfect color accuracy with customizable settings
- **Smart Caching** - Pre-compute for instant subsequent runs
- **Pause & Resume** - Mid-stroke recovery from exact interruption point
- **Advanced Palette Config** - Manual or automatic color center positioning
- **Color Calibration** - Spectrum scanning for accurate custom colors
- **File Management** - Remove calibration data and reset configuration with UI buttons

## Installation

**Requirements:** Python 3.8+ • Windows

```bash
# Clone the repo
git clone https://github.com/Trev241/pyaint.git
cd pyaint

# (Optional) Create virtual environment
conda create -n pyaint python=3.8
conda activate pyaint

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

## Usage

### Quick Start

1. **Setup** - Click "Setup" to define your palette, canvas, and custom colors
2. **Load Image** - Enter a URL or select a local file
3. **Calibrate** - Use "Simple Test Draw" for quick brush adjustment
4. **Draw** - Click "Start" to begin automated painting

### Key Controls

| Key | Action |
|-----|--------|
| `ESC` | Stop drawing |
| `P` (default) | Pause/Resume |
| `Setup` | Configure colors & canvas |
| `Pre-compute` | Cache for faster redraws |
| `Pick Region` | Select area to redraw only |

## Configuration

### Drawing Settings

| Setting | Range | Description |
|---------|-------|-------------|
| **Delay** | 0.0-1.0s | Time between strokes |
| **Pixel Size** | 3-50px | Detail level (lower = more detail) |
| **Precision** | 0.0-1.0 | Color accuracy |
| **Jump Delay** | 0.0-2.0s | Cursor movement optimization |

### Drawing Mode

- **Slotted** - Fast processing, simple mapping
- **Layered** - Better results, color frequency sorting

### Options

✓ Ignore White Pixels → Skip white areas for cleaner results  
✓ Use Custom Colors → Enable spectrum color matching  
✓ New Layer → Auto-create layers with Ctrl/Alt/Shift modifiers  
✓ Skip First Color → Skip initial color in sequence  

### Palette Setup

- **Manual Centers** - Pick exact color positions
- **Auto-Estimate** - Quick grid calculation
- **Precision Estimate** - Reference-point based accuracy  
✓ Toggle valid/invalid palette cells

## Architecture

```
pyaint/
├── main.py          # Entry point
├── bot.py           # Drawing engine & image processing
├── ui/
│   ├── window.py    # GUI interface
│   └── setup.py     # Configuration wizard
├── utils.py         # Utilities
└── config.json      # Settings storage
```

## Color Calibration

Precise color matching for custom colors using spectrum scanning.

**How it works:**
1. Scans color spectrum grid, capturing RGB values at each position
2. Saves data to `color_calibration.json` for reuse
3. Uses exact match (tolerance-based) → falls back to nearest Euclidean match
**Calibration Step:** 1-10 pixels  
- **1-3**: High accuracy, slower  
- **5-10**: Faster calibration

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Drawing not starting | Verify palette & canvas are initialized |
| Colors incorrect | Check custom colors setup & precision |
| Slow performance | Reduce pixel size or increase delay |
| Application unresponsive | Press `ESC` to stop & restart |

**Tips:**
- Use **Pre-compute** for repeated drawings
- Enable **Ignore White Pixels** for images with large blank areas
- **Layered mode** = better results, **Slotted mode** = faster processing

## Documentation

- [API Reference](Docs/api.md)
- [Architecture](Docs/architecture.md)
- [Configuration Guide](Docs/configuration.md)
- [Troubleshooting](Docs/troubleshooting.md)

## Dependencies

- **PyAutoGUI** - GUI automation
- **Pillow** - Image processing
- **pynput** - Keyboard monitoring
- **NumPy** - Math computations

## Videos

### Usage with GIMP
Demonstrates new layers and custom color calibration

https://github.com/user-attachments/assets/965556a4-f72b-4e24-a9ea-160732c6be51

### Usage with MS Paint
Demonstrates custom color calibration

https://github.com/user-attachments/assets/50f2f344-8ca9-439b-8722-0175356ad59e

> **Note:** Calibration is recommended but not required. Calibrate once per app, or let Pyaint match via Euclidean search.

## License

GNU General Public License v3.0
