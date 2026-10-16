# Troubleshooting

## Drawing doesn't start

- The **Canvas** must be configured. Click **Find the canvas**, or pick it in
  **Pick the regions**.
- The **Palette** must be configured. Find the canvas, or pick the grid and its
  rows/columns.
- Load an image first (file, URL, search words, or drag-and-drop).
- If a run is already in progress, wait for it or press `ESC`.

## Colours are wrong

- Re-run **Find the canvas** (or pick the palette) so the swatch centres are
  sampled correctly. The on-screen detection overlay draws a dot at each cell
  centre — check the dots sit inside the swatches.
- Reduce **Detail** for more detail.
- Make sure a palette colour isn't being sampled from a border/gap.

## Colours are skipped entirely

Pyaint only draws colours that are present in the sampled palette. If the image
uses colours the palette doesn't contain, they map to the nearest swatch; a
colour with no close swatch may be skipped.

## Find the canvas found nothing

- **The canvas must be blank.** Detection assumes a uniform canvas (white for
  skribbl, a solid colour for MS Paint); existing artwork defeats it. Clear the
  canvas and retry.
- Maximize the target app on the **primary** monitor at **100%** display
  scaling.
- The window may have been moved or resized since the recipe was tuned; use
  **Pick the regions** to point at the palette and canvas.
- If it finds nothing, it falls back to picking by hand rather than guessing.

## Drawing is slow

- Increase **Detail** (fewer strokes) and/or reduce **Time per stroke**.
- Use **Save the plan for next time** so repeat runs skip processing (drawing
  time is unchanged).
- A large **Jump Delay** or a low **Jump Threshold** adds pauses between
  strokes.

## The application is unresponsive

Press `ESC` to stop the current run, or `P` (the pause key) to pause/resume.
The UI is not blocking during a draw — the engine runs on a worker thread.

## Reset

- **Advanced → Files → Reset config** deletes `config.json` (taught positions
  and preferences). Restart to use defaults.
- The `cache/` directory is removed on exit; delete it manually to force
  reprocessing.
