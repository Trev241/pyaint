# Pyaint Architecture

This document describes the system architecture, design patterns, and component relationships in Pyaint.

## System Overview

Pyaint is a Python-based GUI application that automates drawing by converting images into mouse movements. The system follows a modular architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Window (GUI)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Control Panel │  │ Image Panel  │  │ Tooltip Panel │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                           │
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Bot (Drawing Engine)                   │
│  ┌──────────────┐  ┌──────────────┐                     │
│  │   Palette    │  │   Canvas     │                     │
│  └──────────────┘  └──────────────┘                     │
│  ┌──────────────┐                                        │
│  │Custom Colors │                                        │
│  └──────────────┘                                        │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   Config     │
                    │  (JSON)     │
                    └──────────────┘
```

## Component Architecture

### Entry Point (`main.py`)

The application entry point initializes the global keyboard listener and launches the main GUI window.

**Responsibilities:**
- Initialize [`Bot`](../bot.py:87) instance
- Start [`Window`](../ui/window.py:58) GUI
- Configure global keyboard listener for ESC (terminate) and pause key
- Manage pynput keyboard listener lifecycle

**Key Functions:**
```python
def on_pynput_key(key):
    """Handle global keyboard events for pause/terminate"""
    # ESC key: Set bot.terminate = True
    # Pause key: Toggle bot.paused during drawing
```

### Bot Module (`bot.py`)

The core drawing engine containing two main classes: [`Palette`](../bot.py:16) and [`Bot`](bot.py:87).

#### Palette Class

Handles color detection and matching from a screen region.

**Design Pattern:** Builder Pattern

The [`Palette`](../bot.py:16) class can be initialized in two ways:

1. **Automatic Detection**: Scan a grid-based palette box
2. **Manual Definition**: Use pre-defined color positions

**Initialization Flow:**
```
┌─────────────────────────────────────────────────────────┐
│  init_palette()                                   │
│     │                                            │
│     ├─ colors_pos provided? ────Yes──► Use positions  │
│     │                                            │
│     └─ No ──► Scan grid box                      │
│           │                                       │
│           ├─ valid_positions? ──► Skip invalid cells │
│           │                                       │
│           └─ manual_centers? ──► Use custom centers │
│                                                   │
└─────────────────────────────────────────────────────────┘
```

**Key Attributes:**
- `colors_pos` - Dictionary: `{(r, g, b): (x, y)}`
- `colors` - Set of available RGB tuples
- `box` - Palette bounding box (left, top, width, height)
- `rows`, `columns` - Grid dimensions

**Color Matching Algorithm:**
```python
def nearest_color(self, query):
    """Find nearest palette color using squared Euclidean distance"""
    return min(self.colors, key=lambda color: Palette.dist(color, query))

@staticmethod
def dist(colx, coly):
    """Squared RGB distance (no sqrt for performance)"""
    return sum((s - q) ** 2 for s, q in zip(colx, coly))
```

#### Bot Class

Main drawing engine orchestrating image processing and mouse automation.

**Design Pattern:** State Machine

The [`Bot`](bot.py:87) class maintains multiple state flags:

```python
self.terminate = False    # Stop all operations
self.paused = False       # Pause/resume state
self.drawing = False      # Currently drawing flag
```

**Drawing State for Pause/Resume:**
```python
self.draw_state = {
    'color_idx': 0,        # Current color index
    'line_idx': 0,         # Current line index
    'segment_idx': 0,       # Current stroke segment
    'current_color': None,   # Saved color for resume
    'cmap': None             # Saved coordinate map
}
```

**Settings Array:**
```python
self.settings = [
    DELAY,      # [0] Stroke timing (0.01-10.0s)
    STEP,        # [1] Pixel size (3-50)
    ACCURACY,    # [2] Color precision (0.0-1.0)
    JUMP_DELAY   # [3] Cursor jump delay (0.0-2.0s)
]
```

**Processing Pipeline:**
```
┌─────────────────────────────────────────────────────────┐
│  Image Input                                      │
│     │                                            │
│     ▼                                            │
│  process() / process_region()                    │
│     │                                            │
│     ├─ Load image (PIL)                          │
│     ├─ Resize to canvas fit                         │
│     ├─ Scan pixels (step size)                     │
│     ├─ Map to palette colors                         │
│     ├─ Generate line segments                        │
│     └─ Return color map (cmap)                    │
│                                                   │
│     ▼                                            │
│  draw()                                          │
│     │                                            │
│     ├─ For each color in cmap:                     │
│     │   ├─ Select color (palette or custom)       │
│     │   ├─ For each line segment:                │
│     │   │   ├─ Move to start                    │
│     │   │   ├─ Mouse down                          │
│     │   │   ├─ Drag to end (with segments)        │
│     │   │   └─ Mouse up                          │
│     │   └─ Check pause/terminate                   │
│     └─ Return status                              │
└─────────────────────────────────────────────────────────┘
```

### UI Module

The UI module provides the graphical interface using Tkinter.

#### Window Class (`ui/window.py`)

Main application window with three panels.

**Panel Layout:**
```
┌──────────────────────────────────────────────────────────────────┐
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │  Control Panel  │  │  Image Panel    │               │
│  │                 │  │                 │               │
│  │  Setup          │  │  URL Entry      │               │
│  │  Pre-compute   │  │  File Browser   │               │
│  │  Test Draw      │  │  Preview Image   │               │
│  │  Start          │  │                 │               │
│  │  Settings       │  │                 │               │
│  │  - Delay       │  │                 │               │
│  │  - Pixel Size  │  │                 │               │
│  │  - Precision    │  │                 │               │
│  │  - Jump Delay   │  │                 │               │
│  │  Options       │  │                 │               │
│  │  Redraw Region │  │                 │               │
│  └──────────────────┘  └──────────────────┘               │
│  ┌────────────────────────────────────────────────────┐     │
│  │           Tooltip Panel                    │     │
│  │           Status messages                 │     │
│  └────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────┘
```

**Thread Management:**
Long-running operations use separate threads to keep UI responsive:

```python
@is_free
def start_draw_thread(self):
    """Start drawing in background thread"""
    self._draw_thread = Thread(target=self.start)
    self._draw_thread.start()
    self._manage_draw_thread()

def _manage_draw_thread(self):
    """Update progress while thread is alive"""
    if self._draw_thread.is_alive() and self.busy:
        self._root.after(500, self._manage_draw_thread)
```

**Busy State Management:**
```python
@is_free
def setup(self):
    """Decorator to prevent concurrent operations"""
    if self.busy:
        self.tlabel['text'] = "Cannot perform action. Currently busy..."
    else:
        self.busy = True
        func(self)
```

#### SetupWindow Class (`ui/setup.py`)

Configuration wizard for tool initialization with advanced palette features.

**Features:**
- Mouse-based region selection
- Preview captured regions
- Manual color selection with visual grid
- Center point picking for precision
- Auto-estimate centers using grid calculation
- Precision estimate using reference points
- Modifier key configuration (CTRL, ALT, SHIFT)

**Color Selection Modes:**

1. **Toggle Mode** - Click cells to mark valid/invalid
2. **Pick Centers Mode** - Click exact center points
3. **Auto-Estimate** - Grid-based center calculation
4. **Precision Estimate** - Reference point calculation:
   - Single Column Mode - Vertical palettes
   - 1 Row Mode - Horizontal palettes
   - Multi-Row Mode - Grid palettes

## Data Flow

### Configuration Flow

```
┌─────────────────────────────────────────────────────────┐
│  config.json                                     │
│     │                                            │
│     ├─ Load on startup                           │
│     ├─ Update on setting change                    │
│     └─ Save on setup completion                   │
└─────────────────────────────────────────────────────────┘
```

### Image Processing Flow

```
┌─────────────────────────────────────────────────────────┐
│  Image File                                      │
│     │                                            │
│     ▼                                            │
│  Load (PIL)                                     │
│     │                                            │
│     ▼                                            │
│  Resize to Canvas Fit                              │
│     │                                            │
│     ▼                                            │
│  Scan Pixels (step size)                          │
│     │                                            │
│     ▼                                            │
│  For Each Pixel:                                  │
│     │                                            │
│     ├─ Get RGB value                               │
│     ├─ Find nearest palette color                    │
│     ├─ Check color change                            │
│     └─ Create line segment                          │
│                                                   │
│     ▼                                            │
│  Color Map (cmap)                                 │
│     {color: [(start, end), ...]}                   │
└─────────────────────────────────────────────────────────┘
```

### Drawing Flow

```
┌─────────────────────────────────────────────────────────┐
│  Color Map (cmap)                                │
│     │                                            │
│     ▼                                            │
│  For Each Color:                                   │
│     │                                            │
│     ├─ Check pause/terminate                        │
│     ├─ Select color (palette click or spectrum)        │
│     ├─ For Each Line:                              │
│     │   ├─ Check jump distance > 5px               │
│     │   │   └─ Add jump delay if needed           │
│     │   ├─ Move to start position                  │
│     │   ├─ Break into segments (2-10)              │
│     │   ├─ Drag with delay distribution              │
│     │   └─ Update progress                         │
│     └─ Return status                               │
└─────────────────────────────────────────────────────────┘
```

### Caching Flow

```
┌─────────────────────────────────────────────────────────┐
│  Image + Settings                                 │
│     │                                            │
│     ▼                                            │
│  Generate Cache Filename (MD5 hash)                 │
│     cache/{img_hash}_{settings_hash}.json            │
│     │                                            │
│     ▼                                            │
│  Check Cache Validity                             │
│     │                                            │
│     ├─ File exists?                                │
│     ├─ Age < 24 hours?                             │
│     ├─ Settings match?                              │
│     └─ Canvas match?                               │
│     │                                            │
│     ├─ Yes ──► Load cached cmap                    │
│     └─ No ──► Process image normally              │
└─────────────────────────────────────────────────────────┘
```

## Design Patterns

### Builder Pattern

Used in [`Palette`](../bot.py:16) class for flexible initialization.

**Benefits:**
- Multiple initialization methods from single constructor
- Clear separation of automatic and manual setup
- Easy to extend with new configuration options

### State Machine Pattern

[`Bot`](bot.py:87) class uses state flags to control drawing flow.

**States:**
- `idle` - Not drawing
- `drawing` - Actively drawing
- `paused` - Drawing suspended
- `terminated` - Drawing stopped

**Transitions:**
```
idle ──► drawing ──► paused ──► drawing
  │            │          │
  └────────────┴──────────┘
                │
                ▼
           terminated
```

### Decorator Pattern

[`@is_free`](../ui/window.py:43) decorator prevents concurrent operations.

**Usage:**
```python
@is_free
def start_draw_thread(self):
    # Only executes if not busy
    self._draw_thread = Thread(target=self.start)
    self._draw_thread.start()
```

### Observer Pattern

Progress updates via periodic polling:

```python
def _manage_draw_thread(self):
    """Update progress every 500ms"""
    if self._draw_thread.is_alive() and self.busy:
        self._root.after(500, self._manage_draw_thread)
```

## Key Algorithms

### Color Matching

**Squared Euclidean Distance:**
```python
dist(colx, coly) = Σ(colx[i] - coly[i])²
```

Avoids square root for performance (order preservation).

### Line Generation

**Slotted Mode:**
- Simple color-to-lines mapping
- Each horizontal run of same color = one line segment

**Layered Mode:**
1. Count color frequency (total pixel coverage)
2. Sort colors by frequency (descending)
3. Merge adjacent lines of lower-frequency colors
4. Higher-frequency colors paint over lower-frequency ones

**Benefits:**
- Fewer color switches
- Better visual results
- Optimized for complex images

### Custom Color Spectrum Scanning

**Sampling Algorithm:**
```python
sample_step = 4  # Sample every 4th pixel
for y in range(0, height, sample_step):
    for x in range(0, width, sample_step):
        r, g, b = pix[x, y][:3]
        spectrum_map[(r, g, b)] = (screen_x, screen_y)
```

**Color Selection:**
- Find nearest spectrum color using [`Palette.dist()`](../bot.py:78)
- Click nearest position
- Fallback to keyboard input if spectrum unavailable

## Performance Considerations

### Memory Efficiency

- **Lazy Loading**: Palette colors loaded only when needed
- **Caching**: Pre-computed results stored for reuse
- **Streaming**: Image processed line-by-line, not pixel-by-pixel

### Threading

- **UI Thread**: Main GUI thread (Tkinter)
- **Worker Threads**: Background processing (draw, pre-compute)
- **Thread Safety**: State flags prevent race conditions

### Optimization Strategies

1. **Pre-computation**: Cache image processing for repeated drawings
2. **Jump Delay**: Prevent rapid cursor movements from causing issues
3. **Segmented Drawing**: Break long lines into smooth segments
4. **Color Batching**: Process all lines of one color before switching

## Error Handling

### Exception Hierarchy

```
NoToolError (base)
    ├── NoPaletteError
    ├── NoCanvasError
    └── NoCustomColorsError
CorruptConfigError
```

### Recovery Strategies

1. **Graceful Degradation**: Fall back to simpler methods on failure
2. **State Cleanup**: Reset flags on errors
3. **User Feedback**: Clear error messages via GUI
4. **Retry Logic**: Allow re-attempt after configuration fix

## Extension Points

### Adding New Drawing Modes

1. Define mode constant in [`Bot`](../bot.py:87) class
2. Add processing logic in [`process()`](bot.py:266) method
3. Update [`load_config()`](ui/window.py:669) to load mode setting

### Adding New Tools

1. Add tool to [`tools`](../ui/window.py:110) dictionary
2. Create UI controls in [`_init_cpanel()`](ui/window.py:145)
3. Add initialization logic in [`_on_click()`](ui/setup.py:1182)

### Adding Custom Color Features

1. Extend [`_scan_spectrum()`](bot.py:202) for new scanning methods
2. Add fallback strategies for color selection
3. Update [`draw()`](bot.py:397) to use new features

## See Also

- [API Reference](./api.md)
- [Configuration Guide](./configuration.md)
- [Usage Guide](./usage-guide.md)
