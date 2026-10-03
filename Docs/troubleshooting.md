# Troubleshooting

## Drawing doesn't start

- The **Canvas** must be configured. Run **Auto-detect**, or teach it in
  **Setup**.
- The **Palette** must be configured. Auto-detect or teach the grid and its
  rows/columns.
- Load an image first (file, URL, or drag-and-drop).
- If a run is already in progress, wait for it or press `ESC`.

## Colours are wrong

- Re-run **Auto-detect** (or teach the palette) so the swatch centres are
  sampled correctly. The **Detection** tab draws a dot at each cell centre —
  check the dots sit inside the swatches.
- Reduce **Pixel Size** for more detail.
- Make sure a palette colour isn't being sampled from a border/gap.

## Colours are skipped entirely

Pyaint only draws colours that are present in the sampled palette. If the image
uses colours the palette doesn't contain, they map to the nearest swatch; a
colour with no close swatch may be skipped.

## Auto-detect found nothing

- Maximize the target app on the **primary** monitor at **100%** display
  scaling.
- The window may have been moved or resized since the recipe was tuned; use
  **Setup** to teach the palette and canvas manually.
- Detection failures are silent by design — it never draws in the wrong place.

## Drawing is slow

- Increase **Pixel Size** (fewer strokes) and/or reduce **Delay**.
- Use **Pre-compute** so repeat runs start instantly (it does not change
  drawing speed).
- A large **Jump Delay** or a low **Jump Threshold** adds pauses between
  strokes.

## The application is unresponsive

Press `ESC` to stop the current run, or `P` (the pause key) to pause/resume.
The UI is not blocking during a draw — the engine runs on a worker thread.

## Reset

- **Settings → Files → Reset config** deletes `config.json` (taught positions
  and preferences). Restart to use defaults.
- The `cache/` directory is removed on exit; delete it manually to force
  reprocessing.
