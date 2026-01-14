# Pyaint Architecture

Detailed system architecture and design decisions for Pyaint.

## Table of Contents

- [System Overview](#system-overview)
- [Component Architecture](#component-architecture)
- [Data Flow](#data-flow)
- [Drawing Algorithms](#drawing-algorithms)
- [State Management](#state-management)
- [Threading Model](#threading-model)
- [Configuration System](#configuration-system)
- [Error Handling](#error-handling)
- [Performance Considerations](#performance-considerations)

---

## System Overview

Pyaint is a desktop automation application that converts digital images into mouse movements for painting applications. The system uses a modular architecture with clear separation between the drawing engine, user interface, and configuration management.

### Core Technologies

- **Python 3.8+**: Primary language
- **PyAutoGUI**: Mouse and keyboard automation
- **Pillow (PIL)**: Image processing
- **pynput**: Global keyboard monitoring
- **tkinter**: GUI framework
- **JSON**: Configuration and data persistence

### Design Goals

1. **Modularity**: Clear separation between bot logic and UI
2. **Extensibility**: Easy to add new drawing features
3. **Reliability**: Robust error handling and recovery
4. **Performance**: Caching and optimized algorithms
5. **User Experience**: Real-time feedback and intuitive controls

---

## Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Main Application (main.py)              │
│  ┌──────────────────────────────────────────────┐       │
│  │    Global Keyboard Listener (pynput)     │       │
│  └──────────────────────────────────────────────┘       │
│  ┌──────────────────────────────────────────────┐       │
│  │         Bot Instance                     │       │
│  │  ┌────────────────────────────────┐         │       │
│  │  │  Drawing Engine              │         │       │
│  │  │  - process()               │         │       │
│  │  │  - draw()                  │         │       │
│  │  │  - calibrate_custom_colors() │         │       │
│  │  └────────────────────────────────┘         │       │
│  └──────────────────────────────────────────────┘       │
│  ┌──────────────────────────────────────────────┐       │
│  │         Window Instance (GUI)               │       │
│  │  ┌────────────────────────────┐             │       │
│  │  │  Control Panel          │             │       │
│  │  │  - Settings controls     │             │       │
│  │  │  - Action buttons        │             │       │
│  │  └────────────────────────────┘             │       │
│  │  ┌────────────────────────────┐             │       │
│  │  │  Preview Panel          │             │       │
│  │  │  - Image display        │             │       │
│  │  │  - URL/file input       │             │       │
│  │  └────────────────────────────┘             │       │
│  │  ┌────────────────────────────┐             │       │
│  │  │  Tooltip Panel          │             │       │
│  │  │  - Status messages       │             │       │
│  │  │  - Progress tracking     │             │       │
│  │  └────────────────────────────┘             │       │
│  └──────────────────────────────────────────────┘       │
│                                                          │
│  ┌──────────────────────────────────────────────┐       │
│  │         SetupWindow (Configuration Wizard)  │       │
│  │  ┌────────────────────────────┐             │       │
│  │  │  Tool Configuration      │             │       │
│  │  │  - Palette             │             │       │
│  │  │  - Canvas              │             │       │
│  │  │  - Custom Colors        │             │       │
│  │  │  - New Layer           │             │       │
│  │  │  - Color Button         │             │       │
│  │  │  - Color Button Okay    │             │       │
│  │  │  - Color Preview Spot   │             │       │
│  │  └────────────────────────────┘             │       │
│  │  ┌────────────────────────────┐             │       │
│  │  │  Palette Features       │             │       │
│  │  │  - Toggle valid/invalid │             │       │
│  │  │  - Pick centers         │             │       │
│  │  │  - Auto-estimate        │             │       │
│  │  │  - Precision estimate    │             │       │
│  │  │  - Select/Deselect all │             │       │
│  │  └────────────────────────────┘             │       │
│  └──────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌─────────────────────────┐
              │   config.json         │
              │   - Settings           │
              │   - Tool configs       │
              │   - Calibration data    │
              └─────────────────────────┘
                          │
                          ▼
              ┌─────────────────────────┐
              │   cache/              │
              │   - Precomputed cmap  │
              │   - Image hash keys    │
              └─────────────────────────┘
```

---

## Data Flow

### 1. Application Startup

```
main.py
  │
  ├─> Create Bot instance
  │     ├─> Initialize settings
  │     ├─> Initialize state (terminate, paused, drawing)
  │     └─> Initialize tools (palette, canvas, custom_colors)
  │
  ├─> Start pynput keyboard listener
  │     ├─> Monitor ESC key (set terminate flag)
  │     └─> Monitor pause key (toggle paused flag)
  │
  └─> Create Window instance
        ├─> Load configuration from config.json
        ├─> Initialize UI components
        └─> Enter mainloop
```

### 2. Tool Configuration Flow

```
User clicks "Setup"
  │
  ├─> SetupWindow opens
  │
  ├─> User selects tool and clicks "Initialize"
  │     ├─> Window minimizes
  │     ├─> pynput.mouse.Listener starts
  │     ├─> User clicks on screen (1-2 points)
  │     ├─> Screen capture via ImageGrab
  │     ├─> Save preview image to assets/
  │     ├─> Store coordinates in tools dict
  │     ├─> Mark tool.status = True
  │     └─> Window deiconifies
  │
  ├─> User can click "Preview" to view captured region
  │
  └─> User clicks "Done" -> SetupWindow closes
        └─> Window.merge_tools() -> saves to config.json
```

### 3. Color Calibration Flow

```
User configures Custom Colors and Color Preview Spot
  │
  ├─> User sets Calibration Step Size (1-10)
  │
  ├─> User clicks "Run Calibration"
  │     ├─> Background thread starts
  │     ├─> Get Custom Colors box and Color Preview Spot coords
  │     ├─> Press mouse down at spectrum start
  │     ├─> Drag through entire spectrum (step_size intervals)
  │     ├─> At each step: Capture 1x1 pixel from preview spot
  │     ├─> Store RGB → (x, y) in color_calibration_map
  │     ├─> Release mouse up
  │     ├─> Save to color_calibration.json
  │     └─> Report completion to UI
  │
  └─> During drawing:
        ├─> For each color: Check calibration map first
        ├─> If match within tolerance: Use calibrated position
        └─> If no match: Use spectrum scan or keyboard input
```

### 4. Image Processing Flow

```
User loads image (URL or file)
  │
  ├─> Display in preview panel
  │
  ├─> User clicks "Pre-compute" or "Start"
  │     ├─> Background thread starts
  │     ├─> Load image with PIL
  │     ├─> Calculate resize dimensions (fit canvas, maintain aspect)
  │     ├─> Resize image
  │     ├─> Scan pixels at step_size intervals
  │     ├─> For each pixel:
  │     │     ├─> Get RGB value
  │     │     ├─> If IGNORE_WHITE and white: Skip
  │     │     └─> Else: Map to palette color
  │     │           ├─> If USE_CUSTOM_COLORS: Round to interval
  │     │           └─> Else: nearest_color(palette)
  │     │
  │     ├─> Generate line segments (horizontal runs)
  │     └─> Return cmap: {color: [line_segments]}
  │
  └─> If pre-compute: Save to cache/{hash}.json
```

### 5. Drawing Flow

```
User clicks "Start"
  │
  ├─> Check for valid cache
  │     ├─> If exists: Load cached cmap
  │     └─> Else: Call process() (live)
  │
  ├─> Calculate estimated drawing time
  │     ├─> Sum all stroke delays
  │     ├─> Add jump delays (> 5px movements)
  │     └─> Add color switching overhead (~0.5s/color)
  │
  ├─> Show warning dialog (ESC, pause_key)
  │
  ├─> Window minimizes
  │
  ├─> Drawing thread starts
  │     ├─> Reset state (terminate=False, paused=False)
  │     ├─> For each color in cmap (sorted):
  │     │     ├─> Skip first color if enabled and color_idx == 0
  │     │     ├─> If New Layer enabled:
  │     │     │     ├─> Press modifiers (CTRL/ALT/SHIFT)
  │     │     │     ├─> Click new_layer coords
  │     │     │     ├─> Release modifiers
  │     │     │     └─> Wait 0.75s
  │     │     ├─> If Color Button enabled:
  │     │     │     ├─> Press modifiers
  │     │     │     ├─> Click color_button coords
  │     │     │     ├─> Release modifiers
  │     │     │     └─> Wait delay (0.1-5.0s)
  │     │     ├─> Select color:
  │     │     │     ├─> If in palette: Click palette coords
  │     │     │     ├─> Else if calibration: get_calibrated_color_position()
  │     │     │     ├─> Else if spectrum: Find nearest spectrum color
  │     │     │     └─> Else: Keyboard input (tab, RGB values, enter)
  │     │     ├─> If Color Button Okay enabled:
  │     │     │     ├─> Press modifiers
  │     │     │     ├─> Click okay_button coords
  │     │     │     ├─> Release modifiers
  │     │     │     └─> Wait delay (0.1-5.0s)
  │     │     └─> For each line segment:
  │     │           ├─> Check jump distance (> 5px?)
  │     │           │     ├─> If yes: Sleep(JUMP_DELAY)
  │     │           │     └─> If no: Continue
  │     │           ├─> Check if paused:
  │     │           │     ├─> If yes: Wait (hold any modifiers)
  │     │           │     └─> If no: Continue
  │     │           ├─> If was_paused: Replay stroke
  │     │           ├─> Move to start position
  │     │           ├─> Mouse down
  │     │           ├─> Segment line (2-10 segments based on length)
  │     │           ├─> Sleep(delay / segments) between each
  │     │           └─> Mouse up
  │     │           └─> Update progress (strokes/total_strokes)
  │     │
  │     └─> Report actual vs estimated time
  │
  └─> Window deiconifies (restore, show results)
```

### 6. Pause/Resume Flow

```
Drawing in progress
  │
  ├─> User presses pause_key (e.g., 'p')
  │     ├─> Global pynput listener detects key
  │     ├─> bot.paused = not bot.paused (toggle)
  │     └─> Print "Pause toggled: True/False"
  │
  ├─> Drawing loop checks bot.paused
  │     ├─> If paused:
  │     │     ├─> Release any stuck modifiers (SHIFT, ALT, CTRL)
  │     │     ├─> Wait (busy loop with 0.1s sleep)
  │     │     └─> Continue waiting until not paused
  │     │
  │     └─> When resumed:
  │           ├─> Set was_paused flag
  │           └─> Replay current stroke for clean result
  │
  └─> User presses pause_key again to resume
```

---

## Drawing Algorithms

### Slotted Mode

Simple, direct color-to-lines mapping without optimization.

**Algorithm:**

```python
for each pixel in image:
    if color != previous_color:
        end_current_line()
        start_new_line()
    accumulate_pixels()
```

**Characteristics:**
- **Lines**: Direct horizontal segments of same color
- **Color Order**: Unchanged from scan order
- **Complexity**: O(n) where n = pixel count
- **Memory**: Minimal (only store line segments)
- **Performance**: Fast, simple code path

**Use Case:** Best for simple images or when speed is prioritized

### Layered Mode

Advanced color layering with frequency-based optimization.

**Algorithm:**

```python
# Phase 1: Collect data
for each pixel in image:
    color = map_pixel_to_palette()
    lines_by_row[row].append((color, segment))
    color_freq[color] += segment_length

# Phase 2: Sort by frequency
sorted_colors = sort(colors, by=frequency, descending)

# Phase 3: Merge and optimize
for each color in sorted_colors:
    for each row:
        merge_adjacent_lines(color, lower_frequency_colors)
        if merged_lines_are_exposed:
            add_to_output(color, merged_lines)
```

**Characteristics:**
- **Lines**: Merged segments of lower-frequency colors
- **Color Order**: Frequency-based (most used first)
- **Complexity**: O(n log n) due to sorting
- **Memory**: Higher (stores per-row data)
- **Performance**: Slower processing, better visual results

**Optimizations:**
- Fewer color switches (painter stays on one color longer)
- Overpaint strategy (high-frequency colors paint over low-frequency)
- Reduced mouse movements (merged segments)

**Use Case:** Best for complex images or when quality is prioritized

### Stroke Segmentation

For smooth drawing, long lines are divided into segments.

**Algorithm:**

```python
line_length = calculate_distance(start, end)
segments = clamp(2, line_length / 10, 10)

segment_delay = DELAY / segments

for i in 1 to segments:
    t = i / segments
    next_pos = lerp(start, end, t)
    move_to(next_pos)
    sleep(segment_delay / segments)
```

**Rationale:**
- **Precision**: Multiple small movements = smoother curves
- **Responsiveness**: Shorter sleeps = more responsive control
- **Balance**: 2-10 segments based on line length

---

## State Management

### Bot State

The `Bot` class maintains multiple state flags for control:

| State | Type | Description | Scope |
|-------|--------|-------------|--------|
| `terminate` | bool | Stop all operations immediately | Global |
| `paused` | bool | Pause/resume current drawing | Global |
| `drawing` | bool | Actively executing draw() | Global |
| `draw_state` | dict | Resume state for pause/recovery | Instance |

### Draw State for Pause/Resume

```python
draw_state = {
    'color_idx': int,        # Resume color index
    'line_idx': int,         # Resume line index
    'segment_idx': int,       # Resume segment index
    'current_color': tuple,   # Saved active color
    'was_paused': bool       # Flag for stroke replay
}
```

**Usage:**
1. **Before draw**: Reset to `{0, 0, 0, None, False}`
2. **During draw**: Update after each completed segment
3. **On pause**: Save current state
4. **On resume**: Continue from saved state + replay stroke

### UI State

The `Window` class maintains UI state:

| State | Type | Description |
|-------|--------|-------------|
| `busy` | bool | Block concurrent operations |
| `tools` | dict | All tool configurations |
| `_initializing` | bool | Prevent saving during UI setup |

### Setup State

The `SetupWindow` class maintains configuration state:

| State | Type | Description |
|-------|--------|-------------|
| `_valid_positions` | set | Valid palette cell indices |
| `_manual_centers` | dict | Manually picked center points |
| `_pick_centers_mode` | bool | Mode toggle flag |
| `_precision_mode` | str | 'single_column', '1_row', 'multi_row' |
| `_precision_points` | list | Reference points for estimation |
| `_grid_buttons` | dict | Grid cell UI widgets |
| `_mod_vars` | dict | Modifier key checkboxes |
| `_enable_vars` | dict | Enable checkbox for Color Button Okay |

---

## Threading Model

### Thread Types

Pyaint uses multiple thread types for different operations:

1. **Main Thread**: GUI mainloop (tkinter)
2. **Keyboard Listener**: Global pynput thread (main.py)
3. **Worker Threads**: Background operations

### Worker Thread Operations

| Operation | Entry Point | Manager | Updates |
|-----------|--------------|---------|---------|
| Pre-compute | `precompute()` | `_manage_precompute_thread()` | Progress % |
| Test Draw | `test_draw()` | `_manage_test_draw_thread()` | Progress % |
| Simple Test Draw | `simple_test_draw()` | `_manage_simple_test_draw_thread()` | Status |
| Full Draw | `draw()` | `_manage_draw_thread()` | Progress % |
| Calibration | `calibrate_custom_colors()` | `_manage_calibration_thread()` | Progress % |
| Region Redraw | `redraw_region()` | `_manage_redraw_thread()` | Progress % |

### Thread Safety

**Shared State Access:**
- **Read-only**: Settings, configuration (thread-safe)
- **Write**: Flags (terminate, paused) - simple atomic operations
- **Guarded**: UI updates via `root.after()` callback

**Potential Issues:**
- Race conditions on `bot.terminate` / `bot.paused`
- Solution: These are boolean flags, atomic in Python
- UI updates from non-main thread via `root.after()`

### Thread Lifecycle

```
User action
  │
  ├─> Check busy flag
  │     └─> If busy: Show error, return
  │
  ├─> Set busy = True
  │
  ├─> Create Thread(target=operation)
  │
  ├─> thread.start()
  │
  ├─> Manager thread starts (every 500ms via root.after())
  │     ├─> Check thread.is_alive()
  │     ├─> Update UI progress
  │     └─> If done: Set busy = False
  │
  └─> Operation completes
        └─> Thread exits naturally or returns
```

---

## Configuration System

### Configuration File

**Location:** `config.json` (project root)

**Format:** JSON

**Persistence:**
- Saved on: Tool configuration completion, setting changes
- Loaded on: Application startup
- Encoding: UTF-8 for international support

### Configuration Sections

#### Drawing Settings

```json
"drawing_settings": {
    "delay": 0.15,        // Stroke timing (seconds)
    "pixel_size": 12,       // Detail level
    "precision": 0.9,        // Color accuracy
    "jump_delay": 0.5        // Cursor jump delay (seconds)
}
```

#### Tool Configurations

Each tool has:
- `status`: bool - Is initialized?
- `box` / `coords`: Screen coordinates
- `preview`: Path to captured screenshot
- `modifiers`: dict of CTRL/ALT/SHIFT flags

Special tools:
- Palette: rows, cols, color_coords, valid_positions, manual_centers
- New Layer, Color Button: enabled, delay
- Color Button Okay: enabled, delay

#### User Preferences

```json
"drawing_options": {
    "ignore_white_pixels": false,
    "use_custom_colors": false
},
"pause_key": "p",
"calibration_settings": {
    "step_size": 2
},
"last_image_url": "https://..."
```

### Configuration Loading Flow

```
Window.__init__()
  │
  ├─> Set _initializing = True (prevent saves)
  │
  ├─> Load config.json
  │     ├─> If file missing: Use defaults
  │     ├─> If file corrupt: Show error, use defaults
  │     └─> Parse JSON
  │
  ├─> Apply to bot:
  │     ├─> bot.pause_key
  │     ├─> bot.settings
  │     ├─> bot.new_layer
  │     ├─> bot.color_button
  │     ├─> bot.color_button_okay
  │     └─> bot.options
  │
  ├─> Apply to UI:
  │     ├─> Drawing settings (delay, pixel_size, precision, jump_delay)
  │     ├─> Drawing options (ignore_white, use_custom_colors)
  │     ├─> Pause key entry
  │     ├─> Calibration step entry
  │     └─> Checkboxes
  │
  ├─> Load tool configs:
  │     ├─> Palette (reconstruct from box/rows/cols)
  │     ├─> Canvas
  │     ├─> Custom Colors
  │     ├─> New Layer
  │     ├─> Color Button
  │     ├─> Color Button Okay
  │     └─> Color Preview Spot
  │
  └─> Set _initializing = False (enable saves)
```

### Configuration Saving Flow

```
Setting changes
  │
  ├─> Check _initializing flag
  │     └─> If True: Skip save (UI setup phase)
  │
  ├─> Update tools dict
  │
  ├─> Write to config.json
  │     ├─> Serialize to JSON
  │     ├─> Encode as UTF-8
  │     └─> Atomic write
  │
  └─> Update UI status text
```

---

## Error Handling

### Exception Hierarchy

```
Exception (Python built-in)
  │
  ├── NoToolError (custom base)
  │     ├── NoPaletteError
  │     ├── NoCanvasError
  │     └── NoCustomColorsError
  │
  └── CorruptConfigError (custom)
```

### Error Handling Strategy

#### 1. Bot Layer

**Where**: `bot.py`

**Strategy**: Raise exceptions with descriptive messages

```python
def init_palette(self, ...):
    try:
        palette = Palette(...)
    except ValueError as e:
        raise NoPaletteError(f'Palette initialization failed: {e}')
```

**Recovery**: Window catches and shows to user

#### 2. UI Layer

**Where**: `ui/window.py`, `ui/setup.py`

**Strategy**: Try-catch with user feedback

```python
try:
    result = bot.draw(cmap)
except NoPaletteError:
    messagebox.showerror('Palette not configured')
except Exception as e:
    messagebox.showerror(f'Drawing failed: {e}')
finally:
    self._set_busy(False)
```

#### 3. Global Level

**Where**: `main.py`

**Strategy**: Graceful shutdown on critical errors

```python
try:
    Window('pyaint', bot, ...)
finally:
    pynput_listener.stop()  # Cleanup
```

### User-Facing Errors

| Error | Message | Resolution |
|-------|---------|------------|
| NoPaletteError | "Palette not initialized" | Run Setup |
| NoCanvasError | "Canvas not initialized" | Run Setup |
| NoCustomColorsError | "Custom colors not initialized" | Configure in Setup |
| CorruptConfigError | "Config file missing or invalid" | Run Setup |

---

## Performance Considerations

### 1. Image Processing

**Complexity**: O(n) where n = pixel count

**Optimizations:**
- Nearest color memoization: Cache RGB → palette lookups
- Vector distance calculation: Pre-compute palette colors
- Interval-based scanning: Step size reduces pixel count

### 2. Drawing Time

**Components:**

| Factor | Impact | Optimization |
|--------|----------|--------------|
| Stroke count | Linear | Larger pixel size = fewer strokes |
| Color switches | ~0.5s each | Layered mode reduces switches |
| Jump delays | Variable | Tune jump_delay setting |
| Modifier keys | Negligible | Minimal overhead |
| Segment delays | Per segment | Controlled by delay setting |

**Approximation Formula:**

```
total_time = (strokes * delay)
           + (jumps * jump_delay)
           + (colors * 0.5)
           + (modifiers * 0.1)
```

**Behavior Details:**

- **Jump Delay Threshold**: Cursor movements greater than 5 pixels trigger jump delay
- **Stroke Segmentation**: Long lines are divided into 2-10 segments for smooth drawing
- **Time Comparison Display**: After drawing completes, actual time vs. estimated time is shown
- **Cache Cleanup**: Cache files are automatically cleaned up on application exit

### 3. Caching

**Cache Hit Performance:**
- Load time: ~0.01s (JSON parse)
- Avoid: Image processing (1-30s depending on size)

**Cache Miss Performance:**
- Process time: 1-30s
- Save time: ~0.1s (JSON write)

**Cache Validation:**
- Age check: < 24 hours
- Settings match: Exact equality
- Canvas check: Exact dimensions

### 4. Memory Usage

**Components:**

| Component | Approx. Size | Notes |
|-----------|-------------|-------|
| Palette object | ~1 KB | Small grids |
| Canvas box | 4 ints | Negligible |
| Color calibration map | ~50-500 KB | Depends on step size |
| Spectrum map | ~50-200 KB | Depends on spectrum size |
| Coordinate map (cmap) | 100 KB - 10 MB | Image dependent |
| Config JSON | ~1-5 KB | Tool configs |

**Optimizations:**
- Use generators where possible
- Release large data structures after use
- Cache invalidation strategy

### 5. Threading Overhead

**Thread creation**: ~1-5ms per thread

**Context switching**: Minimal (Python GIL)

**UI updates**: Every 500ms via `root.after()`

**Synchronization**: Atomic boolean flags (no locks needed)

---

## Design Decisions

### Why pynput for Keyboard?

**Chosen**: `pynput` (global monitoring)

**Alternatives Considered**:
- `pyautogui.press()`: Requires focus, can't detect ESC
- `tkinter` hotkeys: Limited to window focus

**Decision**: `pynput` provides:
- Global hotkey detection (even when minimized)
- Low overhead
- Multi-key support (modifiers)

### Why JSON for Configuration?

**Chosen**: JSON

**Alternatives Considered**:
- YAML: More readable, requires extra dependency
- INI: Limited structure, no nested dicts
- Pickle: Binary, not human-readable, security risk

**Decision**: JSON provides:
- Native Python support (no imports needed)
- Human-readable
- Standard format
- Type-safe (schema can validate)

### Why Separate Threading?

**Chosen**: Background threads for long operations

**Rationale**:
- GUI responsiveness: Main thread never blocks
- User feedback: Progress updates every 500ms
- User control: ESC/pause detected via separate pynput thread

**Alternative Rejected**:
- Synchronous: Blocks GUI, poor UX
- Multiprocessing: Overkill, complexity

### Why MD5 for Cache Keys?

**Chosen**: MD5 hash

**Characteristics**:
- Deterministic: Same file = same hash
- Fast: O(n) with good distribution
- Collision resistant: Very low probability

**Implementation**:
```python
image_hash = hashlib.md5(image_data).hexdigest()[:8]
settings_hash = hashlib.md5(settings_str).hexdigest()[:8]
```

### Why Two Drawing Modes?

**Slotted**: Simple, fast
- Direct mapping
- No optimization
- Good for: Simple images, speed priority

**Layered**: Advanced, slower
- Color layering
- Frequency optimization
- Good for: Complex images, quality priority

**User Choice**: Mode dropdown in UI

---

## Future Extensions

### Potential Improvements

1. **Multi-threaded Drawing**: Parallel stroke execution (complex)
2. **GPU Acceleration**: Use CUDA for image processing
3. **Neural Upscaling**: Integrate with ESRGAN/SwinIR
4. **Plugin System**: Custom drawing strategies
5. **Cloud Sync**: Sync cache/settings across devices
6. **Undo/Redo**: Bot-level undo system
7. **Real-time Preview**: Overlay on canvas while drawing

### Scalability Considerations

- **4K+ Images**: Memory optimization needed
- **Video Support**: Frame-by-frame processing
- **Batch Processing**: Queue system for multiple images
- **Network Bot**: Remote control via web interface
