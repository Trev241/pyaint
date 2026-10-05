# Configuration

Pyaint stores its state in `config.json`, next to the executable (the repo root
for a source checkout). The file is written whenever you change something in the
UI.

## Structure

```json
{
  "drawing_settings": {
    "delay": 0.1,
    "pixel_size": 12,
    "jump_delay": 0.5,
    "jump_threshold": 5
  },
  "drawing_options": { "ignore_white_pixels": true, "ignore_transparent_pixels": true },
  "pause_key": "p",
  "theme": "auto",
  "draw_mode": "layered",
  "color_metric": "ciede2000",
  "skip_first_color": false,
  "last_image_url": "",
  "image_search_provider": "openverse",
  "drawing_by_target": {},
  "environments": {},
  "target": "generic",

  "Palette": { "status": true, "box": [x1, y1, x2, y2], "rows": 6, "cols": 8,
               "color_coords": { "(r, g, b)": [x, y] } },
  "Canvas": { "status": true, "box": [x1, y1, x2, y2] },
  "New Layer": { "status": false, "coords": [x, y], "enabled": false,
                 "modifiers": { "ctrl": false, "alt": false, "shift": false } },
  "Color Button": { "status": false, "coords": [x, y], "enabled": false, "delay": 0.1,
                    "modifiers": { "ctrl": false, "alt": false, "shift": false } },
  "Color Button Okay": { "status": false, "coords": [x, y], "enabled": false, "delay": 0.1,
                         "modifiers": { "ctrl": false, "alt": false, "shift": false } },
  "MSPaint Mode": { "enabled": false, "delay": 0.5 }
}
```

Two groups:

- **Environment** (`Palette`, `Canvas`, `New Layer`, `Color Button`,
  `Color Button Okay`, `MSPaint Mode`, `target`) — owned by the shared
  `Profile`.
- **Preferences** (`drawing_settings`, `drawing_options`, `drawing_by_target`,
  `environments`, `pause_key`, `theme`, `draw_mode`, `color_metric`,
  `skip_first_color`, `last_image_url`, `image_search_provider`) — owned by the
  window.

Legacy keys from older versions (`Custom Colors`, `color_preview_spot`,
`color_selection`) are ignored and dropped on the next save.

## Drawing settings

| Setting | Range | Default | Meaning |
|---------|-------|---------|---------|
| `delay` | 0.0–1.0 s | 0.1 | How long each stroke takes |
| `pixel_size` | 1–50 px | 12 | Detail level (lower = more detail, slower) |
| `jump_delay` | 0.0–2.0 s | 0.5 | Pause after a large cursor jump |
| `jump_threshold` | 1–200 px | 5 | Jump distance that triggers `jump_delay` |

## Drawing options

| Option | Default | Meaning |
|--------|---------|---------|
| `ignore_white_pixels` | true | Skip pure-white runs |
| `ignore_transparent_pixels` | true | Skip pixels with alpha below the cutoff (128), so transparent PNG areas aren't painted black |
| `skip_first_color` | false | Don't draw the first colour in the map |
| `draw_mode` | `layered` | `layered` (fewer strokes) or `slotted` (exact runs) |
| `color_metric` | `ciede2000` | `ciede2000` (perceptual) or `rgb` (legacy squared Euclidean) |

### Per-target drawing settings

`drawing_settings`, `drawing_options`, `draw_mode`, and `skip_first_color` are
remembered **per target** under `drawing_by_target`, keyed by target id. On
switching targets the current values are saved and the new target's are
restored; a target with no saved values uses its recipe's defaults. The
top-level keys above remain as the fallback and always record the active
target's values (for older configs and recipes).

## Environment tools

| Tool | What to teach |
|------|---------------|
| `Palette` | Top-left and bottom-right corners of the swatch grid, plus rows/columns |
| `Canvas` | Top-left and bottom-right corners of the drawing surface |
| `New Layer` | The button that creates a layer (optional; supports modifiers) |
| `Color Button` | A button to click before selecting a swatch (optional) |
| `Color Button Okay` | A button to click after selecting a swatch (optional) |
| `MSPaint Mode` | Double-click swatches instead of a single click |

The `Palette` entry stores cells in `color_coords` (sampled RGB → screen
position).

## Appearance

`theme` is `auto` (follow the OS), `dark`, or `light`.

## Defaults

A fresh profile has an unconfigured `Palette`/`Canvas`, `delay` 0.1,
`pixel_size` 12, `jump_delay` 0.5, `jump_threshold` 5,
`ignore_white_pixels` true, `ignore_transparent_pixels` true, `theme` `auto`,
and `target` `generic`.

## Resetting

Use **Advanced → Files → Reset config**, or delete `config.json` and restart.
