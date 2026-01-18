# Pyaint Architecture

System architecture and design documentation for Pyaint.

## Table of Contents

- [Overview](#overview)
- [System Components](#system-components)
- [Data Flow](#data-flow)
- [Drawing Pipeline](#drawing-pipeline)
- [Color System](#color-system)
- [Configuration Management](#configuration-management)
- [UI Architecture](#ui-architecture)
- [Control Flow](#control-flow)

---

## Overview

Pyaint is a drawing automation tool that converts images into precise mouse movements for painting applications. The system is built with a modular architecture that separates concerns between drawing logic, user interface, and configuration management.

### Core Principles

1. **Separation of Concerns**: Drawing logic, UI, and configuration are independent
2. **Automation-First**: Automated mouse/keyboard control through pynput
3. **Configurability**: All behaviors configurable via JSON
4. **Extensibility**: Modular design allows easy feature additions

### Technology Stack

- **Python**: Primary language (3.8+)
- **Pillow (PIL)**: Image processing
- **PyAutoGUI**: Mouse and keyboard automation
- **Pynput**: Global keyboard event handling
- **Tkinter**: GUI framework

---

## System Components

### Module Structure

```
pyaint/
├── main.py              # Application entry point
├── bot.py               # Core drawing automation engine
├── utils.py              # Utility functions
├── exceptions.py         # Custom exception classes
├── ui/
│   ├── __init__.py
│   ├── window.py          # Main application window
│   └── setup.py           # Setup/configuration window
├── assets/               # Preview images and assets
├── Docs/                 # Documentation
└── config.json           # Persistent configuration
```

### Component Responsibilities

#### `main.py`

**Purpose**: Application entry point and keyboard control setup

**Responsibilities**:
- Initialize Bot instance
- Set up pynput keyboard listener for global hotkeys
- Handle ESC key for termination
- Handle pause_key for pause/resume
- Launch main Window
- Clean up on exit

**Key Features**:
- Non-blocking keyboard listener
- ESC terminates all operations
- Configurable pause/resume key (default: 'p')

#### `bot.py`

**Purpose**: Core drawing automation engine

**Responsibilities**:
- Image processing and analysis
- Color matching and selection
- Mouse movement and click automation
- Drawing execution (full, test, region)
- Pause/resume handling
- Color calibration

**Key Classes**:
- `Bot`: Main automation class

**Key Methods**:
- `draw()`: Full image drawing
- `draw_test()`: Test sample drawing
- `simple_test_draw()`: Simple line test
- `draw_region()`: Region-based redrawing
- `precompute_image()`: Image preprocessing
- `pick_palette_color()`: Palette color selection
- `pick_custom_color()`: Custom color selection

#### `utils.py`

**Purpose**: Utility functions for image processing

**Responsibilities**:
- Image dimension calculations
- Aspect ratio handling

**Key Functions**:
- `adjusted_img_size()`: Calculate dimensions to fit space

#### `exceptions.py`

**Purpose**: Custom exception classes

**Responsibilities**:
- Define error hierarchy
- Provide specific error types

**Exception Classes**:
- `PyaintException`: Base exception
- `NotInitializedError`: Tool not initialized
- `ConfigurationError`: Configuration issues
- `DrawingError`: Drawing operation failures

#### `ui/window.py`

**Purpose**: Main application UI

**Responsibilities**:
- Display main interface
- Handle user input
- Coordinate with Bot instance
- Display status and progress

**Key Classes**:
- `Window`: Main application window

**Key Features**:
- Control panel for settings
- Preview panel for images
- Tooltip panel for status
- Real-time progress tracking

#### `ui/setup.py`

**Purpose**: Tool configuration interface

**Responsibilities**:
- Configure palette, canvas, custom colors
- Configure optional tools (New Layer, Color Button, etc.)
- Capture screen regions
- Manage tool state

**Key Classes**:
- `SetupWindow`: Setup configuration window

---

## Data Flow

### Application Startup Flow

```
main.py
  │
  ├─> Create Bot instance
  │
  ├─> Setup pynput keyboard listener
  │     ├─> ESC key → set bot.terminate = True
  │     └─> pause_key → toggle bot.paused
  │
  └─> Launch Window (main UI)
        │
        └─> Load config.json
```

### Drawing Flow

```
User Action (Click "Start")
  │
  ├─> Validate prerequisites
  │     ├─> Check palette initialized
  │     ├─> Check canvas initialized
  │     └─> Check image loaded
  │
  ├─> Process image
  │     ├─> Load PIL Image
  │     ├─> Apply drawing mode (slotted/layered)
  │     └─> Generate draw commands
  │
  ├─> Execute drawing
  │     ├─> For each command:
  │     │     ├─> Check terminate flag
  │     │     ├─> Check paused flag
  │     │     ├─> Select color if needed
  │     │     ├─> Move mouse
  │     │     └─> Click/drag
  │     └─> Update progress
  │
  └─> Complete
        └─> Show results
```

### Configuration Loading Flow

```
Application Startup
  │
  ├─> Check for config.json
  │
  ├─> File exists?
  │     ├─> Yes: Parse JSON
  │     │     ├─> Load drawing_settings
  │     │     ├─> Load drawing_options
  │     │     ├─> Load pause_key
  │     │     ├─> Load tool configurations
  │     │     └─> Apply to Bot instance
  │     │
  │     └─> No: Use defaults
  │
  └─> Initialize UI with loaded config
```

---

## Drawing Pipeline

### Processing Modes

#### Slotted Mode

**Purpose**: Simple color-to-lines mapping

**Process**:
1. Group pixels by color
2. Create line segments for each color
3. Draw all segments of color A, then color B, etc.

**Advantages**:
- Faster processing
- Less memory usage
- Simpler implementation

**Best For**: Simple images with few colors

#### Layered Mode (Default)

**Purpose**: Advanced color layering with frequency sorting

**Process**:
1. Group pixels by color
2. Sort colors by frequency (most common first)
3. Create line segments
4. Draw in frequency order

**Advantages**:
- Better visual results
- Fewer color switches
- Optimized for complex images

**Best For**: Complex images with many colors

### Drawing Execution

```
For each color in sorted order:
  ├─> Pick color (palette or custom)
  │     ├─> If MSPaint Mode: Double-click
  │     └─> Else: Single-click
  │
  ├─> For each line segment of this color:
  │     ├─> Calculate movement
  │     ├─> Check jump distance
  │     │     ├─> If > jump_threshold: Apply jump_delay
  │     │     └─> Else: No delay
  │     ├─> Move mouse to position
  │     ├─> Click and drag (delay seconds)
  │     └─> Release mouse
  │
  └─> Move to next color
```

### Pause/Resume Mechanism

**Pause State**:
- `bot.paused` flag set to True
- Drawing loop checks flag at each iteration
- State preserved (current position, color)
- Can resume mid-stroke

**Resume State**:
- `bot.paused` flag set to False
- Continues from exact interruption point
- No re-initialization needed

---

## Color System

### Color Sources

#### Palette Colors

**Source**: Predefined color palette in drawing application

**Configuration**:
- Grid-based layout (rows x columns)
- Clickable color cells
- Valid/invalid positions
- Manual center points

**Selection Process**:
1. Find nearest palette color to target RGB
2. Get center coordinates
3. Click on palette cell
4. Use selected color

#### Custom Colors

**Source**: Custom color spectrum in drawing application

**Configuration**:
- Continuous spectrum area
- Color-to-position mapping

**Selection Process**:
1. Find nearest spectrum position to target RGB
2. Click on spectrum
3. Use selected color
4. Fallback to keyboard input if spectrum unavailable

### Color Matching Algorithm

#### Palette Matching

```python
def find_nearest_palette_color(target_rgb, palette_colors):
    min_distance = infinity
    nearest_color = None
    
    for color in palette_colors:
        if color not in valid_positions:
            continue
        
        # Calculate Euclidean distance in RGB space
        distance = sqrt(
            (r1-r2)^2 + (g1-g2)^2 + (b1-b2)^2
        )
        
        if distance < min_distance:
            min_distance = distance
            nearest_color = color
    
    return nearest_color
```

#### Custom Color Matching

```python
def find_custom_color_position(target_rgb, spectrum_map):
    # Try calibration map first
    if calibration_map exists:
        if target_rgb in calibration_map:
            return calibration_map[target_rgb]
    
    # Fallback to nearest spectrum color
    best_position = None
    min_distance = infinity
    
    for position, rgb in spectrum_map.items():
        distance = color_distance(target_rgb, rgb)
        if distance < min_distance:
            min_distance = distance
            best_position = position
    
    return best_position
```

### Color Calibration

**Purpose**: Create precise RGB → (x, y) mapping

**Process**:
1. Configure Custom Colors (spectrum area)
2. Configure Color Preview Spot
3. Set calibration step size
4. Run calibration:
   - Press mouse at spectrum start
   - Drag through entire spectrum
   - At each step, capture RGB from Preview Spot
   - Build calibration map: RGB → (x, y)
   - Release mouse
5. Save to `color_calibration.json`

**Usage During Drawing**:
1. Check calibration map for exact match
2. If found: Use calibrated position
3. If not found: Fall back to nearest spectrum color

---

## Configuration Management

### Configuration File Structure

**File**: `config.json`

**Sections**:
1. `drawing_settings`: Core drawing parameters
2. `drawing_options`: Feature toggles
3. `pause_key`: Pause/resume hotkey
4. `calibration_settings`: Calibration parameters
5. Tool configurations (Palette, Canvas, Custom Colors, etc.)
6. Tool options (New Layer, Color Button, MSPaint Mode, etc.)
7. `last_image_url`: Recently used image URL

### Configuration Lifecycle

```
Application Start
  │
  ├─> Load config.json
  │     ├─> Exists: Parse and apply
  │     └─> Missing: Use defaults
  │
  ├─> User makes changes
  │     ├─> Drawing settings changed
  │     ├─> Checkboxes toggled
  │     └─> Tools configured
  │
  └─> Save to config.json
        (Automatic on each change)
```

### Tool Configuration

Each tool has a configuration structure:

```python
{
    "status": bool,           # Is tool initialized
    "box": [x1, y1, x2, y2], # Screen coordinates
    "coords": [x, y],         # Click coordinates
    "enabled": bool,           # Is feature active
    "modifiers": {             # Key modifiers
        "ctrl": bool,
        "alt": bool,
        "shift": bool
    },
    "delay": float,            # Delay after click
    "preview": string          # Preview image path
}
```

---

## UI Architecture

### Main Window Structure

```
┌─────────────────────────────────────────────┐
│              Pyaint Main Window            │
├──────────────┬──────────────────────────────┤
│              │                              │
│   Control    │      Preview Panel           │
│    Panel     │                              │
│              │                              │
│              │                              │
│  - Settings  │                              │
│  - Actions   │                              │
│  - Options   │                              │
│              │                              │
│              │                              │
├──────────────┴──────────────────────────────┤
│         Tooltip / Status Panel              │
└─────────────────────────────────────────────┘
```

### Control Panel Components

**Drawing Settings**:
- Delay (text entry)
- Pixel Size (slider)
- Precision (slider)
- Jump Delay (slider)
- Calibration Step (entry)
- Jump Threshold (entry)

**Drawing Options** (checkboxes):
- Ignore White Pixels
- Use Custom Colors
- Skip First Color
- Enable New Layer
- Enable Color Button
- Enable Color Button Okay

**Drawing Mode**:
- Slotted Mode (radio)
- Layered Mode (radio)

**Actions**:
- Open File
- Search (URL)
- Pre-compute
- Simple Test Draw
- Test Draw
- Start
- Setup

**Redraw Region**:
- Redraw Pick
- Draw Region

**File Management**:
- Remove Calibration
- Reset Config

**Pause Key**:
- Entry field for key configuration

### Setup Window Structure

Multi-tab configuration interface for tools:
- Palette configuration
- Canvas configuration
- Custom Colors configuration
- Color Preview Spot configuration
- New Layer configuration
- Color Button configuration
- Color Button Okay configuration
- MSPaint Mode configuration

---

## Control Flow

### Keyboard Control

**Global Listener** (pynput):
```python
def on_key_press(key):
    # Handle ESC
    if key == Key.esc:
        bot.terminate = True
    
    # Handle pause key during drawing
    if bot.drawing:
        key_name = extract_key_name(key)
        if key_name == pause_key.lower():
            bot.paused = not bot.paused
```

### Drawing Control Loop

```python
def draw_loop():
    for command in drawing_commands:
        # Check termination
        if terminate:
            break
        
        # Check pause
        while paused:
            time.sleep(0.1)
            if terminate:
                break
        
        # Execute command
        execute_command(command)
        
        # Update progress
        update_progress()
```

### Error Handling

```python
try:
    operation()
except NotInitializedError as e:
    show_error("Tool not initialized")
except ConfigurationError as e:
    show_error("Configuration error")
except DrawingError as e:
    show_error("Drawing failed")
except Exception as e:
    show_error(f"Unexpected error: {e}")
```

---

## Design Patterns

### Observer Pattern

**Usage**: Progress updates and status changes

**Implementation**:
- Window observes Bot state
- Tooltip updates based on state changes
- Progress bar reflects drawing progress

### Strategy Pattern

**Usage**: Drawing modes (Slotted vs Layered)

**Implementation**:
- Different image processing strategies
- User selects mode at runtime
- Bot delegates to appropriate strategy

### Factory Pattern

**Usage**: Tool configuration creation

**Implementation**:
- Setup window creates tool configurations
- Standardized configuration structures
- Extensible to new tools

### Singleton Pattern

**Usage**: Bot instance

**Implementation**:
- Single Bot instance created in main.py
- Shared across UI components
- Centralized drawing control

---

## Performance Considerations

### Caching Strategy

**Pre-computed Images**:
- Process once, draw multiple times
- Stored in memory during session
- Significant speedup for repeated drawings

**Color Maps**:
- Palette color coordinates cached
- Custom color spectrum cached
- Calibration map loaded from file

### Optimization Techniques

1. **Color Grouping**: Group pixels by color to minimize color switches
2. **Frequency Sorting**: Draw most common colors first (Layered mode)
3. **Region Processing**: Draw only needed areas (Region redraw)
4. **Pixel Size Tuning**: Balance detail vs. speed

---

## Extensibility

### Adding New Tools

To add a new tool:

1. Define configuration structure in `config.json`
2. Add UI elements in `ui/setup.py`
3. Add activation logic in `bot.py`
4. Update documentation

### Adding New Drawing Modes

To add a new drawing mode:

1. Define processing algorithm
2. Add to drawing mode selection UI
3. Implement in Bot class
4. Update documentation

---

## See Also

- [API Reference](./api.md) - Complete API documentation
- [Configuration Guide](./configuration.md) - Configuration options
- [Tutorial](./tutorial.md) - Step-by-step usage guide
- [Troubleshooting](./troubleshooting.md) - Common issues and solutions
