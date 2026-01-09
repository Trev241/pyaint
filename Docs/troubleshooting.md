# Pyaint Troubleshooting Guide

Common issues and solutions.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Configuration Issues](#configuration-issues)
- [Tool Configuration](#tool-configuration)
- [Drawing Issues](#drawing-issues)
- [Performance Issues](#performance-issues)
- [UI Issues](#ui-issues)
- [Error Messages](#error-messages)
- [FAQ](#faq)

---

## Installation Issues

### Module Not Found Errors

**Error:** `ModuleNotFoundError: No module named 'pyautogui'`

**Solution:**
```bash
pip install -r requirements.txt
```

### Permission Denied (Windows)

Run Command Prompt as Administrator, then:
```bash
pip install -r requirements.txt
```

### pynput Installation Fails

**Solution:**
```bash
pip install pypiwin32
pip install pynput
```

---

## Configuration Issues

### Config File Missing or Corrupt

**Solution:**
1. Delete `config.json`
2. Restart Pyaint
3. Reconfigure tools via "Setup"

### Invalid JSON Error

**Cause:** Manually edited `config.json` with syntax errors

**Solution:**
1. Validate JSON at jsonlint.com
2. Fix errors (commas, quotes, braces)
3. Or delete file and reconfigure

### Settings Not Saving

**Causes:**
- Read-only file system
- Insufficient permissions
- Application crash

**Solution:**
1. Check file permissions on `config.json`
2. Ensure directory is writable

---

## Tool Configuration

### "Palette not initialized" Error

**Solution:**
1. Click "Setup" → "Palette"
2. Click "Initialize"
3. Follow prompts to click corners
4. Click "Done"

### "Canvas not initialized" Error

**Solution:**
1. Click "Setup" → "Canvas"
2. Click "Initialize"
3. Follow prompts
4. Click "Done"

### Palette Colors Not Matching

**Causes:**
- Misaligned palette box
- Incorrect rows/columns
- Invalid positions not set

**Solutions:**

**Check Alignment:**
1. Click "Setup" → "Palette" → "Preview"
2. Verify grid matches actual palette
3. Reinitialize if misaligned

**Adjust Valid Positions:**
1. Click "Setup" → "Palette" → "Manual Color Selection"
2. Toggle cells as valid/invalid
3. Click "Done"

**Use Manual Centers:**
1. Click "Set Pick Centers Mode"
2. Click exact center of each color
3. Click "Done"

**Try Auto-Estimate:**
1. Click "Auto-Estimate"
2. Click "Show Centers Overlay" to verify

### Canvas Position Offset

**Symptom:** Drawing appears shifted on canvas

**Solution:**
1. Reinitialize canvas with correct corners
2. Ensure upper-left is actual drawing area start
3. Verify preview shows correct area

### Custom Colors Not Working

**Symptom:** "Use Custom Colors" enabled but not using spectrum

**Solutions:**
1. Configure Custom Colors tool in Setup
2. Verify spectrum box is correct
3. Check if using calibrated colors

---

## Drawing Issues

### Drawing Won't Start

**Causes:**
- Missing tools (palette, canvas)
- Invalid cache
- Image not loaded

**Solutions:**
1. Ensure palette and canvas are initialized
2. Clear cache: delete files in `cache/` directory
3. Load image first via URL or file path

### Colors Are Wrong

**Causes:**
- Palette misconfigured
- Precision too low
- Using wrong color source

**Solutions:**
1. Reconfigure palette with Preview check
2. Increase Precision setting
3. Disable "Use Custom Colors" to use palette only
4. Run calibration for custom colors

### Drawing Too Slow

**Causes:**
- Low delay setting
- Small pixel size
- Many color switches
- High jump delay

**Solutions:**
1. **Increase Delay** for faster response
2. **Increase Pixel Size** for less detail (major speedup)
3. Use **Slotted** mode (faster but less accurate)
4. Enable **Ignore White Pixels** for images with white backgrounds
5. **Decrease Jump Delay** (if no accidental strokes)

### Drawing Too Fast / Missed Strokes

**Causes:**
- Delay too low for your system
- System not responding fast enough

**Solutions:**
1. **Increase Delay** setting
2. Close other applications to free resources
3. **Increase Jump Delay** to prevent accidental strokes

### Strokes Connecting Unintentionally

**Symptom:** Lines appearing between separate strokes

**Solution:**
1. **Increase Jump Delay** (prevents rapid cursor movement)
2. Check if painting app has "connect lines" feature enabled
3. **Decrease Delay** slightly (faster stroke may help)

### Drawing Wrong Size

**Symptom:** Drawing appears too small/large on canvas

**Solution:**
1. Adjust **Pixel Size** setting
2. **Decrease** for smaller pixels = larger image
3. **Increase** for larger pixels = smaller image

### Drawing Not Centered

**Symptom:** Drawing appears in wrong canvas location

**Solution:**
1. Reinitialize canvas with correct bounds
2. Ensure upper-left corner is correct
3. Preview canvas area in Setup to verify

### Drawing Gaps/Incomplete

**Symptom:** Some areas missing or broken

**Causes:**
- Too low precision
- Too high pixel size
- White pixels ignored but shouldn't be

**Solutions:**
1. **Increase Precision** setting
2. **Decrease Pixel Size** for more detail
3. Disable "Ignore White Pixels" if needed

### ESC Key Not Stopping Drawing

**Symptom:** Pressing ESC doesn't stop drawing

**Causes:**
- Keyboard listener not running
- ESC key mapping issue

**Solutions:**
1. Restart application
2. Check console for errors
3. Try pause key instead, then quit

---

## Performance Issues

### High Memory Usage

**Symptom:** Application using lots of RAM

**Causes:**
- Large images
- Small pixel size
- High precision

**Solutions:**
1. Use smaller images
2. **Increase Pixel Size**
3. **Decrease Precision**
4. Delete old cache files

### Processing Takes Too Long

**Symptom:** Image processing takes minutes

**Causes:**
- Large image
- Small pixel size
- High precision
- Slotted mode (slower than layered)

**Solutions:**
1. **Increase Pixel Size** (major impact)
2. **Decrease Precision**
3. Use **Layered** mode
4. Pre-compute and cache image
5. Use smaller/resized images

### Caching Not Working

**Symptom:** Pre-compute doesn't speed up subsequent runs

**Causes:**
- Settings changed
- Canvas changed
- Cache invalid (older than 24 hours)

**Solutions:**
1. Keep settings consistent
2. Use same canvas configuration
3. Clear old cache manually: delete `cache/*.json`
4. Check cache directory exists

---

## UI Issues

### Window Minimizes Unexpectedly

**Symptom:** Main window minimizes at wrong times

**Solution:**
1. This is normal during drawing
2. Click taskbar icon to restore when drawing complete
3. Use pause key to pause and restore window

### Progress Not Updating

**Symptom:** Progress bar stuck or not moving

**Causes:**
- Thread crash
- Very slow operation

**Solutions:**
1. Wait longer (may be slow)
2. Check console for errors
3. Use ESC to stop if stuck

### Preview Image Not Showing

**Symptom:** Image URL/file loaded but not displayed

**Causes:**
- Invalid URL
- Unsupported image format
- Network error

**Solutions:**
1. Try local file instead of URL
2. Use PNG/JPG format
3. Check internet connection
4. Verify URL is accessible in browser

### Setup Window Issues

**Symptom:** Setup window won't close/minimize properly

**Solution:**
1. Click "Done" button (don't close with X)
2. If stuck, close application and restart

### Mouse Clicks Not Registered

**Symptom:** Clicking during Setup has no effect

**Causes:**
- Window not properly minimized
- Mouse listener not active

**Solutions:**
1. Ensure Setup window is minimized (check taskbar)
2. Restart application
3. Check console for mouse listener errors

---

## Error Messages

### NoPaletteError

**Message:** "Palette not initialized"

**Solution:** Configure palette in Setup

### NoCanvasError

**Message:** "Canvas not initialized"

**Solution:** Configure canvas in Setup

### NoCustomColorsError

**Message:** "Custom colors not initialized"

**Solution:** 
- Either disable "Use Custom Colors"
- Or configure Custom Colors tool in Setup

### CorruptConfigError

**Message:** "Config file missing or invalid"

**Solution:** Delete `config.json` and reconfigure

### Generic Errors

**If you encounter other errors:**

1. Check console output for full error traceback
2. Ensure all dependencies installed: `pip install -r requirements.txt`
3. Check Python version (requires 3.8+)
4. Try restarting application
5. Report issue on GitHub with full error message

---

## FAQ

### Q: What is the optimal delay setting?

**A:** Start with 0.15 seconds. If strokes are being missed, increase it. If drawing is too slow, decrease it gradually.

### Q: How do I know what pixel size to use?

**A:** 
- Start with 12-15 for balanced detail/speed
- Increase (20-30) for faster, less detailed drawings
- Decrease (5-8) for more detail but slower

### Q: Should I use Slotted or Layered mode?

**A:**
- **Slotted**: Simple images, speed priority
- **Layered**: Complex images, quality priority (default)

### Q: What is the difference between Delay and Jump Delay?

**A:**
- **Delay**: Duration of each brush stroke (always applied)
- **Jump Delay**: Extra time when cursor jumps > 5px between strokes

### Q: Why does drawing take so long?

**A:** Time depends on:
- Image size and complexity
- Pixel size (smaller = longer)
- Number of colors
- Delay setting

**To speed up:**
- Increase pixel size
- Decrease delay
- Use pre-computation for repeated drawings

### Q: Can I pause and resume drawing?

**A:** Yes! Press your configured pause key (default: 'p') to pause. Press again to resume.

### Q: What does pre-compute do?

**A:** Pre-processes image and saves results to cache. Subsequent runs load from cache instead of reprocessing.

### Q: How do I use color calibration?

**A:**
1. Configure Custom Colors tool
2. Configure Color Preview Spot tool
3. Set Calibration Step Size
4. Click "Run Calibration"
5. Results saved to `color_calibration.json`

### Q: Why are some colors wrong even after calibration?

**A:**
- Increase calibration accuracy by decreasing step size
- Check that Color Preview Spot is correctly positioned
- Verify Custom Colors spectrum box is accurate
- Try higher tolerance in calibration lookup

### Q: Can I draw only part of an image?

**A:** Yes! Use the "Redraw Region" feature:
1. Load image
2. Click and drag on preview to select area
3. Click "Redraw Region"

### Q: What are modifier keys used for?

**A:** For tools that require keyboard shortcuts:
- CTRL, ALT, SHIFT modifiers
- Useful for applications where tools need key combinations
- Configure in Setup tool configuration

### Q: How do I reset all settings?

**A:**
1. Close Pyaint
2. Delete `config.json`
3. Restart
4. Reconfigure tools via Setup

### Q: Can I use Pyaint with any drawing application?

**A:** Most should work:
- MS Paint
- Clip Studio Paint
- Photoshop
- Krita
- GIMP
- And many others

**Requirements:**
- Visible palette and canvas
- Mouse-based color selection
- (Optional) Custom color spectrum

### Q: Why does the application need to minimize during drawing?

**A:** To prevent interference with the drawing process and ensure accurate mouse positioning.

### Q: Can I run Pyaint while using other applications?

**A:** Yes, but:
- Window will minimize during drawing
- Don't move the drawing application
- Don't interfere with mouse movements

### Q: How do I improve color accuracy?

**A:**
1. Use **Manual Centers** for palette
2. Run **Color Calibration** for custom colors
3. **Increase Precision** setting
4. Ensure palette/preview boxes are accurate

---

## Getting Help

### Documentation

- [API Reference](./api.md) - Detailed API docs
- [Architecture](./architecture.md) - System architecture
- [Configuration](./configuration.md) - Settings guide
- [Usage Guide](./usage-guide.md) - Step-by-step instructions

### Reporting Issues

When reporting issues, include:
1. Full error message and traceback
2. Your Python version
3. Your operating system
4. Steps to reproduce the issue
5. Your `config.json` (with sensitive coords removed)

### Known Limitations

- Single-threaded drawing (no parallel processing)
- Limited by system responsiveness
- Keyboard input fallback for colors can be slow
- Requires visible UI elements for automation
