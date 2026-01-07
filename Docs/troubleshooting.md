# Pyaint Troubleshooting

This document provides solutions to common issues and problems you may encounter while using Pyaint.

## Table of Contents

- [Common Issues](#common-issues)
- [Setup Problems](#setup-problems)
- [Drawing Issues](#drawing-issues)
- [Performance Issues](#performance-issues)
- [Configuration Issues](#configuration-issues)
- [Palette Issues](#palette-issues)
- [Color Button Issues](#color-button-issues)
- [Cache Issues](#cache-issues)

## Common Issues

### Drawing Not Starting

**Symptoms:**
- Clicking "Start" button has no effect
- "Drawing not starting" error message appears
- Setup window shows "NOT INITIALIZED" for palette or canvas

**Causes:**
- Palette not initialized
- Canvas not initialized
- Tools not configured

**Solutions:**
1. Click **"Setup"** button to open Setup Window
2. Click **"Initialize"** for each tool:
   - **Palette**: Click upper-left and lower-right corners of palette
   - **Canvas**: Click upper-left and lower-right corners of canvas
   - **Custom Colors**: Click upper-left and lower-right corners of custom colors box
3. Ensure status shows **"INITIALIZED"** (green) for all tools
4. Click **"Done"** to save setup

**Prevention:**
- Always run Setup after first launch
- Verify all three tools (Palette, Canvas, Custom Colors) are initialized before drawing

---

### Colors Incorrect

**Symptoms:**
- Drawn image has wrong colors
- Colors don't match the source image
- Some colors are completely different from expected

**Causes:**
- Palette not properly configured
- Wrong palette selected
- Custom colors enabled but not configured correctly
- Precision setting too low (reduces color variety)

**Solutions:**
1. **Verify Palette Configuration:**
   - Click "Setup" → "Preview" to see palette
   - Ensure correct palette is selected
   - Check rows/columns match your actual palette

2. **Check Custom Colors:**
   - If using custom colors, verify custom colors box is configured
   - Check console for "[Spectrum] Scanned" message
   - Test with simple test draw to verify color selection

3. **Adjust Precision Setting:**
   - Increase precision for more accurate colors
   - Try values between 0.85-0.95
   - Re-process image after changing precision

4. **Reinitialize Palette:**
   - Click "Setup" → "Initialize" to rescan palette
   - This may fix corrupted color mappings

---

### Slow Performance

**Symptoms:**
- Drawing takes much longer than expected
- Cursor movements are sluggish
- Application becomes unresponsive during drawing

**Causes:**
- Delay setting too high
- Pixel size too small (more detail = more strokes)
- Custom colors enabled (slower than palette)
- Other applications consuming CPU
- System resources limited

**Solutions:**
1. **Adjust Delay Setting:**
   - Decrease delay (try 0.05-0.1 seconds)
   - Lower values = faster drawing
   - Balance between speed and reliability

2. **Increase Pixel Size:**
   - Larger pixel size = fewer strokes
   - Try values between 10-20 for faster drawing
   - Accept lower detail for speed

3. **Disable Custom Colors:**
   - Custom colors are slower than palette
   - Disable if not needed for faster drawing

4. **Close Other Applications:**
   - Close browser, music players, etc.
   - Free up CPU resources

5. **Use Pre-compute:**
   - Pre-compute once for repeated drawings
   - Avoids reprocessing same image

6. **Check System Resources:**
   - Ensure adequate RAM available
   - Close unnecessary background processes
   - Check CPU usage in Task Manager

---

### Drawing Too Fast / Missed Strokes

**Symptoms:**
- Drawing completes much faster than expected
- Some strokes are missing
- Lines appear incomplete

**Causes:**
- Delay setting too low
- Jump delay too low
- System too fast for application to keep up
- Mouse acceleration causing issues

**Solutions:**
1. **Increase Delay Setting:**
   - Try values between 0.2-0.5 seconds
   - Gives application more time to register strokes

2. **Increase Jump Delay:**
   - Set to 0.1-0.2 seconds
   - Prevents rapid cursor movements

3. **Disable Mouse Acceleration:**
   - In Windows: Control Panel → Mouse → Pointer Options
   - Uncheck "Enhance pointer precision"
   - Reduce pointer speed

4. **Use Test Draw First:**
   - Run test draw to verify brush settings
   - Adjust based on test results

---

### Application Not Responding

**Symptoms:**
- Application freezes during drawing
- Cursor gets stuck
- Drawing stops mid-way

**Causes:**
- Application overwhelmed by rapid input
- Delay too low (too fast)
- System resources exhausted
- Application crash or hang

**Solutions:**
1. **Press ESC to Stop:**
   - Immediately stops all drawing
   - Allows application to recover

2. **Increase Delay:**
   - Slower input gives application more time
   - Try values between 0.3-1.0 seconds

3. **Restart Application:**
   - Close and reopen application
   - Clears any stuck states

4. **Check Application Status:**
   - Look for error messages in target application
   - Verify application is still running

---

## Setup Problems

### Palette Not Initializing

**Symptoms:**
- "Palette not initialized" error
- Setup shows "NOT INITIALIZED" (red status)
- Clicking "Initialize" has no effect

**Causes:**
- Incorrect box coordinates
- Rows/columns not set
- Box format incorrect

**Solutions:**
1. **Verify Box Coordinates:**
   - Ensure format is `(left, top, width, height)`
   - Check that upper-left is actually top-left
   - Width and height are positive values

2. **Set Rows and Columns:**
   - Count actual rows and columns in your palette
   - Enter correct values before clicking "Initialize"

3. **Check Preview:**
   - Click "Preview" to see captured region
   - Verify it matches your actual palette

4. **Re-capture Box:**
   - Click "Initialize" again
   - Select corners carefully
   - Upper-left first, then lower-right

---

### Canvas Not Initializing

**Symptoms:**
- "Canvas not initialized" error
- Setup shows "NOT INITIALIZED" (red status)

**Solutions:**
1. **Verify Box Coordinates:**
   - Ensure format is `(x1, y1, x2, y2)`
   - Check that x2 > x1 and y2 > y1

2. **Check Preview:**
   - Click "Preview" to see captured region
   - Verify it matches your actual canvas

3. **Re-capture Box:**
   - Click "Initialize" again
   - Select corners carefully

---

### Custom Colors Not Initializing

**Symptoms:**
- "Custom colors not initialized" error
- Setup shows "NOT INITIALIZED" (red status)

**Solutions:**
1. **Verify Box Coordinates:**
   - Ensure format is `(x1, y1, x2, y2)`
   - Check that box covers actual custom colors area

2. **Check Preview:**
   - Click "Preview" to see captured region
   - Verify it matches your actual custom colors box

3. **Re-capture Box:**
   - Click "Initialize" again
   - Select corners carefully

---

## Drawing Issues

### Drawing Stops Midway

**Symptoms:**
- Drawing stops unexpectedly
- No error message
- Progress stops updating

**Causes:**
- ESC key pressed accidentally
- Application lost focus
- System interrupt
- Canvas moved or resized

**Solutions:**
1. **Check Keyboard State:**
   - Ensure no keys are stuck
   - Check if modifier keys are active
   - Try pressing ESC again to stop cleanly

2. **Resume Drawing:**
   - Click "Start" again
   - Bot should resume from saved state
   - Check console for "Resuming with saved color" message

3. **Verify Application State:**
   - Ensure target application is still visible
   - Check if canvas is still in correct position

---

### Colors Switching Too Slowly

**Symptoms:**
- Drawing takes very long time
- Frequent color changes
- Each color switch has long delay

**Causes:**
- Color button delay too high
- Color button okay enabled with delay
- Application slow to open color picker
- Custom colors enabled (slower than palette)

**Solutions:**
1. **Reduce Color Button Delay:**
   - Set to 0.05-0.2 seconds
   - Faster color switching

2. **Disable Color Button Okay:**
   - If not needed, disable this feature
   - Reduces extra delay

3. **Use Palette Colors Only:**
   - Disable custom colors if not needed
   - Palette clicks are much faster

4. **Optimize Palette:**
   - Use valid positions to skip unused colors
   - Fewer colors = faster switching

---

## Performance Issues

### High CPU Usage

**Symptoms:**
- System becomes sluggish
- Other applications slow down
- Fan runs constantly

**Causes:**
- Pre-computation running in background
- Drawing with very low delay
- Multiple instances running
- Custom colors scanning

**Solutions:**
1. **Wait for Pre-compute:**
   - Let pre-computation finish before starting drawing
   - Check console for completion message

2. **Increase Delay:**
   - Higher delay = less frequent updates
   - Reduces CPU load

3. **Close Unnecessary Applications:**
   - Free up system resources

4. **Use Layered Mode:**
   - More efficient color switching than slotted mode

---

### Memory Issues

**Symptoms:**
- Application crashes
- "Out of memory" errors
- System becomes unresponsive

**Causes:**
- Very large images
- Low pixel size (too many coordinates)
- Cache accumulation
- Memory leaks in long-running sessions

**Solutions:**
1. **Increase Pixel Size:**
   - Larger values = fewer coordinates
   - Try 15-30 for large images

2. **Clear Cache:**
   - Delete `cache/` directory manually
   - Cache rebuilds automatically on next run

3. **Use Pre-compute:**
   - Pre-computes once, then uses cache
   - Avoids repeated processing

4. **Restart Application:**
   - Close and reopen between large drawings
   - Clears memory

---

## Configuration Issues

### Settings Not Saving

**Symptoms:**
- Settings revert to defaults on restart
- Changes lost after closing application
- `config.json` not updated

**Causes:**
- File permission issues
- Application closed before saving
- Disk full
- Corrupted config file

**Solutions:**
1. **Check File Permissions:**
   - Ensure write access to `config.json`
   - Run as administrator if needed

2. **Verify Config File:**
   - Open `config.json` in text editor
   - Check for valid JSON syntax
   - Verify settings are present

3. **Manual Backup:**
   - Copy `config.json` before making changes
   - Restore if corruption occurs

4. **Check Console Output:**
   - Look for "Saved config to" messages
   - Verify no error messages appear

---

### Invalid Config File

**Symptoms:**
- Application fails to start
- "Config file missing or invalid" error
- Default settings used instead

**Causes:**
- Corrupted JSON syntax
- Missing required keys
- Invalid data types
- File deleted or moved

**Solutions:**
1. **Restore from Backup:**
   - Copy backup `config.json` back
   - Replace corrupted file

2. **Manual Recreation:**
   - Delete corrupted file
   - Run Setup to recreate configuration
   - Application will create new config

3. **Check JSON Syntax:**
   - Use JSON validator (online or text editor)
   - Ensure all brackets and commas are correct
   - Verify all strings are quoted

---

## Palette Issues

### Palette Colors Not Selecting Correctly

**Symptoms:**
- Wrong colors are selected
- Clicks miss the intended color
- Offset from intended color

**Causes:**
- Manual centers not set correctly
- Valid positions not marked
- Palette box moved
- Different resolution than when configured

**Solutions:**
1. **Use Manual Center Picking:**
   - Click "Edit Colors" → "Pick Centers"
   - Click exact center for each color cell
   - Most accurate method

2. **Use Precision Estimate:**
   - Click "Edit Colors" → "Precision Estimate"
   - Follow on-screen instructions
   - System calculates optimal spacing

3. **Verify Valid Positions:**
   - Ensure only used colors are marked as valid (green)
   - Toggle invalid colors (red) to exclude them

4. **Reinitialize Palette:**
   - Click "Initialize" to rescan with new settings
   - This may fix offset issues

---

### Manual Centers Not Working

**Symptoms:**
- Centers not being used
- Clicks go to wrong positions
- "Manual centers" setting ignored

**Causes:**
- Manual centers not saved in config
- `manual_centers` dictionary empty or corrupted
- Pick centers mode not activated
- Valid positions not set

**Solutions:**
1. **Verify Setup Completed:**
   - Click "Done" after picking centers
   - Check for "Palette updated" success message

2. **Check Config File:**
   - Open `config.json`
   - Verify `manual_centers` object exists
   - Check it contains center coordinates

3. **Re-enter Pick Centers Mode:**
   - Click "Edit Colors" → "Pick Centers" again
   - System will use saved centers

4. **Check Console:**
   - Look for "Picked center for color X" messages
   - Verify centers are being applied

---

## Color Button Issues

### Color Button Not Clicking

**Symptoms:**
- Color picker doesn't open
- Palette colors used instead
- Wrong color selected

**Causes:**
- Color button not enabled
- Coords not configured
- Application doesn't require color button click
- Modifier keys not set correctly

**Solutions:**
1. **Enable Color Button:**
   - Check "Enable Color Button" checkbox in main window
   - Verify checkbox is checked

2. **Configure Coords:**
   - Click "Setup" → Initialize Color Button
   - Click the color picker button location

3. **Set Delay Appropriately:**
   - Adjust delay for your application
   - Test with simple test draw first

4. **Check Modifiers:**
   - Set CTRL/ALT/SHIFT if required
   - Verify application responds to modifier keys

---

### Color Button Okay Not Clicking

**Symptoms:**
- Color selection not confirmed
- Drawing continues with wrong color
- Color picker stays open

**Causes:**
- Color button okay not enabled
- Coords not configured
- Delay too short (picker doesn't have time to open)

**Solutions:**
1. **Enable Color Button Okay:**
   - Check "Enable" checkbox in Setup Window
   - Verify checkbox is checked

2. **Configure Coords:**
   - Click "Setup" → Initialize Color Button Okay
   - Click the confirmation button location

3. **Increase Delay:**
   - Give picker time to fully open
   - Try values between 0.2-0.5 seconds

---

## Cache Issues

### Cache Not Loading

**Symptoms:**
- "No cached computation" message
- Image reprocessed every time
- Slow startup for repeated drawings

**Causes:**
- Cache file corrupted
- Settings changed since cache was created
- Canvas dimensions changed
- Cache expired (>24 hours old)

**Solutions:**
1. **Delete Cache Directory:**
   - Delete `cache/` folder
   - Next run will rebuild cache

2. **Force Re-process:**
   - Delete specific cache file
   - Application will reprocess image

3. **Check Cache Validity:**
   - Look for "Cache file invalid" message
   - Verify settings match current configuration

4. **Verify Image Hash:**
   - Check console for image hash messages
   - Ensure same image is being processed

---

### Cache Not Saving

**Symptoms:**
- Pre-compute completes but no cache file created
- "Failed to save config" error
- Cache not found on next run

**Causes:**
- No write permissions
- Disk full
- Cache directory doesn't exist
- File path issues

**Solutions:**
1. **Check Directory Permissions:**
   - Ensure `cache/` directory is writable
   - Check parent directory permissions

2. **Verify Disk Space:**
   - Ensure adequate free space
   - Clear unnecessary files if needed

3. **Check Console:**
   - Look for "Cache saved to" message
   - Verify no error messages

4. **Manual Cache Directory Creation:**
   - Create `cache/` directory manually
   - Ensure it's in project root

---

## Debugging Tips

### Enable Console Logging

The console provides detailed information about what's happening:

**Key Messages to Watch:**
- `"Switching to color (r, g, b) - N lines"` - Color changes
- `"Drawing stroke X/Y for color (r, g, b)" - Drawing progress
- `"Large jump detected (X pixels) - adding delay"` - Jump delays
- `"[Spectrum] Scanned X unique colors"` - Custom colors setup
- `"Using cached computation"` - Cache usage
- `"Cache file invalid, processing live..."` - Cache miss

### Test Drawing

Always test before full drawing:

1. **Simple Test Draw:**
   - Quick 5-line test
   - Verifies brush size
   - No color picking

2. **Test Draw:**
   - First 20 lines with color switching
   - Verifies palette selection
   - Tests actual drawing behavior

3. **Check Results:**
   - Compare test output to expected
   - Adjust settings based on test

### Progress Monitoring

Watch the progress messages:

```
Processing image: 25.50%
Drawing stroke 10/100 for color (255, 0, 0)
Total progress: 150/500 strokes - 2:30 remaining
```

**What to Check:**
- Progress percentage increasing
- Time remaining estimate decreasing
- No long pauses without pause message

### Getting Help

If issues persist:

1. Check [README.md](../README.md) for basic usage
2. Review [Configuration Guide](./configuration.md) for settings
3. Review [API Reference](./api.md) for technical details
4. Review [Architecture](./architecture.md) for system design

## See Also

- [README.md](../README.md)
- [API Reference](./api.md)
- [Configuration Guide](./configuration.md)
- [Architecture](./architecture.md)
