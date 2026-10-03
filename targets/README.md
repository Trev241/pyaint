# Target recipes

Drop a `*.json` recipe in this folder (or in `~/.pyaint/targets/`) and it will
appear in the **Target App** dropdown the next time Pyaint starts. Recipes here
are loaded after the built-ins and may override a built-in with the same `id`.

A recipe tells Pyaint which tools a drawing app needs, what colour strategy to
use, and how to auto-detect the canvas/palette.

## Fields

| Field | Meaning |
|-------|---------|
| `id` | Unique identifier (required) |
| `name` | Display name in the dropdown |
| `description` | Short description |
| `extends` | Optional parent `id`; parent fields are deep-merged then overridden by this recipe |
| `hidden` | If true the recipe is infrastructure (a base) and is not shown in the dropdown |
| `schema_version` | Recipe schema version (current: 1) |
| `tools` | Which taught tools Setup should show, from: `Palette`, `Canvas`, `Custom Colors`, `New Layer`, `Color Button`, `Color Button Okay`, `color_preview_spot` |
| `color_selection` | `auto`, `palette`, or `custom` |
| `supports_custom_colors` / `supports_layers` / `supports_mspaint_mode` | Capability flags |
| `drawing_settings` | Defaults applied on selection: `delay`, `pixel_size`, `precision`, `jump_delay`, `jump_threshold` |
| `drawing_options` | `ignore_white_pixels`, `use_custom_colors` |
| `skip_first_color` | bool |
| `palette` | Optional fixed `[[r,g,b], ...]` list (used to *locate* a palette via `color_signature`) |
| `detection` | Auto-detection specs (see below) |
| `notes` | Help text |

Recipes are checked by a static self-test on load; problems (unknown locator
type/params, bad colour, new schema) are printed to the console.

## Locator types (`detection.canvas` / `detection.palette`)

Each element takes one locator object, **or an ordered list of them** (a chain,
tried until one succeeds).

| Type | What it finds | Useful params |
|------|---------------|---------------|
| `white_rect` | largest near-white rectangle | `aspect`, `aspect_tolerance`, `threshold` |
| `color_rect` | largest solid rectangle of a given colour | `color`, `tolerance`, `aspect` |
| `color_grid` | a grid of saturated swatches | `min_saturation`, `gap` |
| `color_signature` | the block covering the most distinct listed colours | `colors`, `tolerance`, `gap`, `min_colors`, `min_fill` |
| `window_relative` | a sub-rectangle of an OS window | `window` (title substring), `rect` `[x,y,w,h]` (0..1) |

`color_signature` and `window_relative` return `rows`/`cols` from the spec, so
include them when detecting a palette.

## Inheritance

A recipe can extend another (including the built-in hidden bases
`desktop-base` and `browser-base`). For example:

```json
{
  "id": "my-paint",
  "name": "My Paint",
  "extends": "desktop-base",
  "drawing_settings": { "pixel_size": 6 }
}
```

Dict fields (`drawing_settings`, `drawing_options`, `detection`) are deep-merged,
so the child only specifies what it changes.

## Example

```json
{
  "id": "myapp",
  "name": "My App",
  "tools": ["Palette", "Canvas"],
  "color_selection": "palette",
  "drawing_options": { "ignore_white_pixels": true },
  "detection": {
    "canvas": { "type": "white_rect", "aspect": 1.3333, "aspect_tolerance": 0.2 },
    "palette": {
      "type": "color_signature",
      "colors": [[255, 0, 0], [0, 255, 0], [0, 0, 255]],
      "tolerance": 25,
      "min_colors": 3,
      "rows": 1,
      "cols": 3
    }
  }
}
```

To build a `color_signature` palette, capture a screenshot of the app with the
palette visible and sample the centre pixel of each swatch. The dev helper
`AGENTS/tools/detect_screenshot.py` can test detection against a saved
screenshot without running the GUI.
