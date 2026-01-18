# Pyaint Troubleshooting Guide

Complete troubleshooting guide for Pyaint - solving common issues and errors.

## Table of Contents

- [Common Issues](#common-issues)
- [Error Messages](#error-messages)
- [Configuration Issues](#configuration-issues)
- [Performance Issues](#performance-issues)
- [Tool Issues](#tool-issues)
- [Drawing Issues](#drawing-issues)
- [Color Issues](#color-issues)
- [File Management Issues](#file-management-issues)

---

## Common Issues

### Drawing not starting

**Symptoms**: Clicking Start doesn't begin drawing

**Possible Causes**:
- Palette or canvas not initialized
- No image loaded in preview
- Invalid image file

**Solutions**:
1. Ensure palette and canvas are properly initialized (status should be green)
2. Check that an image is loaded in the preview panel
3. Verify the image file is valid and readable
4. Try reloading the image

### Application not responding to bot

**Symptoms**: Drawing app freezes or doesn't respond to mouse movements

**Possible Causes**:
- Delay setting too low
- Jump delay too low
- System under heavy load
- Application compatibility issues

**Solutions**:
1. Use ESC to stop the current drawing
2. Increase the **Delay** setting to give the app more time
3. Increase the **Jump Delay** setting
4. Check if your drawing app is compatible
5. Close other applications to reduce system load

### Colors incorrect or mismatched

**Symptoms**: Drawn colors don't match the source image

**Possible Causes**:
- Invalid palette configuration
- Precision setting too low
- Valid positions not correctly set
- Custom colors not configured properly

**Solutions**:
1. Verify palette colors are correctly scanned
2. Check custom colors setup if enabled
3. Increase **Precision** setting for better color matching
4. Ensure valid positions include all needed colors
5. Run color calibration for improved accuracy
6. Preview the palette to verify correct configuration

### Slow drawing performance

**Symptoms**: Drawing takes much longer than expected

**Possible Causes**:
- Pixel size too small (too much detail)
- System under heavy load
- Delay setting too high
- Custom colors enabled (slower processing)

**Solutions**:
1. Increase **Pixel Size** setting (less detail = faster)
2. Increase **Delay** if strokes are being missed
3. Enable **"Ignore White Pixels"** for images with large white areas
4. Check if your system is under heavy load
5. Use **Slotted mode** instead of Layered mode for faster processing
6. Consider disabling custom colors if not necessary

### Palette colors not selecting correctly

**Symptoms**: Bot doesn't click on the correct colors

**Possible Causes**:
- Invalid center points
- Invalid positions marked incorrectly
- Palette layout changed

**Solutions**:
1. Verify valid positions are marked correctly
2. Check that centers are correctly picked
3. Use **Precision Estimate** for better accuracy
4. Preview the palette to verify it was captured correctly
5. Try manual center picking
6. Re-initialize the palette if layout changed

### Custom colors not working

**Symptoms**: Custom color spectrum isn't being used

**Possible Causes**:
- Custom colors box not configured
- Checkbox not enabled
- Spectrum scanning incomplete

**Solutions**:
1. Ensure custom colors box is correctly configured
2. Verify **"Use Custom Colors"** checkbox is enabled
3. Check that spectrum scanning has completed
4. Preview the custom colors region
5. Ensure Color Preview Spot is configured if using calibration

### Drawing stops prematurely

**Symptoms**: Drawing stops before completion

**Possible Causes**:
- ESC key accidentally pressed
- System interruption
- Error during execution

**Solutions**:
1. Check if ESC was pressed
2. Review error messages in tooltip panel
3. Check system logs for errors
4. Restart the application
5. Try drawing with different settings

---

## Error Messages

### "Palette not initialized"

**Cause**: Palette tool hasn't been configured

**Solutions**:
1. Click **"Setup"** button
2. Initialize the Palette by clicking **"Initialize"**
3. Follow prompts to select palette corners
4. Verify status shows green after initialization

### "Canvas not initialized"

**Cause**: Canvas tool hasn't been configured

**Solutions**:
1. Click **"Setup"** button
2. Initialize the Canvas by clicking **"Initialize"**
3. Follow prompts to select canvas corners
4. Verify status shows green after initialization

### "Custom colors not initialized"

**Cause**: Custom Colors tool hasn't been configured but **"Use Custom Colors"** is enabled

**Solutions**:
1. Either disable **"Use Custom Colors"** checkbox, OR
2. Click **"Setup"** button
3. Initialize Custom Colors tool
4. Follow prompts to select spectrum corners

### "No valid colors selected"

**Cause**: All palette colors are marked as invalid

**Solutions**:
1. Click **"Manual Color Selection"**
2. Click on at least one grid cell to make it valid (green)
3. Click **"Done"** when finished
4. Verify at least one color is marked as valid

### "Config file missing or invalid"

**Cause**: Configuration file is corrupted or missing

**Solutions**:
1. The app will use default settings
2. Click **"Reset Config"** in File Management section
3. Restart the application
4. Run **"Setup"** to reconfigure tools

### "Color calibration not found"

**Cause**: Color calibration file doesn't exist

**Solutions**:
1. Run **"Run Calibration"** to create new calibration
2. Ensure Custom Colors and Color Preview Spot are configured
3. Set appropriate Calibration Step Size
4. Wait for calibration to complete

### "Invalid image URL"

**Cause**: The URL provided doesn't point to a valid image

**Solutions**:
1. Verify the URL is correct
2. Ensure the URL points directly to an image file (not a webpage)
3. Try opening the URL in a browser to verify
4. Use **"Open File"** to load from local disk instead

### "Region not selected"

**Cause**: Attempting to draw a region without selecting one first

**Solutions**:
1. Click **"Redraw Pick"** first
2. Click on the upper left corner of the region
3. Click on the lower right corner of the region
4. Then click **"Draw Region"**

### "Drawing already in progress"

**Cause**: Attempting to start a new drawing while one is already running

**Solutions**:
1. Press ESC to stop the current drawing
2. Wait for the drawing to complete
3. Check if drawing is paused and resume or stop

---

## Configuration Issues

### Settings not saving

**Symptoms**: Changes to settings are not persisted

**Possible Causes**:
- File permission issues
- Disk full
- Invalid JSON in config file

**Solutions**:
1. Check file permissions for `config.json`
2. Ensure sufficient disk space
3. Verify JSON syntax if editing manually
4. Try **"Reset Config"** and reconfigure

### Invalid settings loaded

**Symptoms**: Settings show incorrect values on startup

**Possible Causes**:
- Corrupted configuration file
- Manual editing errors
- Version incompatibility

**Solutions**:
1. Click **"Reset Config"** in File Management section
2. Restart the application
3. Reconfigure all tools and settings
4. Avoid manual editing of config files

### Tool status not updating

**Symptoms**: Tool initialization status doesn't change

**Possible Causes**:
- Preview not saved
- Image capture failed
- UI update delay

**Solutions**:
1. Verify the preview images were saved in `assets/` folder
2. Try initializing the tool again
3. Check for error messages in tooltip
4. Restart the application

---

## Performance Issues

### High CPU usage

**Symptoms**: Application uses excessive CPU during drawing

**Possible Causes**:
- Pixel size too small
- Custom colors enabled
- Complex image

**Solutions**:
1. Increase **Pixel Size** to reduce processing
2. Disable custom colors if not needed
3. Use **Slotted mode** for faster processing
4. Reduce image complexity if possible

### Long processing time for Pre-compute

**Symptoms**: Pre-computing takes very long time

**Possible Causes**:
- Large image size
- Very small pixel size
- Custom colors enabled

**Solutions**:
1. Use smaller images or resize before loading
2. Increase **Pixel Size**
3. Disable custom colors during pre-compute
4. Consider skipping pre-compute for one-time drawings

### Memory usage high

**Symptoms**: Application uses a lot of memory

**Possible Causes**:
- Large cached images
- Multiple pre-computed images
- Layered mode

**Solutions**:
1. Use **Slotted mode** instead of Layered mode
2. Clear cached data by restarting
3. Reduce image size before loading
4. Increase **Pixel Size** to reduce data

---

## Tool Issues

### Palette initialization fails

**Symptoms**: Unable to initialize palette

**Possible Causes**:
- Invalid corner selection
- Palette area too small
- System permissions

**Solutions**:
1. Ensure you click on actual corners, not near them
2. Make sure palette area is large enough
3. Check screen permissions
4. Try restarting the application

### Canvas initialization fails

**Symptoms**: Unable to initialize canvas

**Possible Causes**:
- Invalid corner selection
- Canvas area too small
- Multiple monitors

**Solutions**:
1. Ensure you click on actual corners
2. Make sure canvas is visible on screen
3. Move canvas to primary monitor if using multiple displays
4. Check screen permissions

### Custom colors initialization fails

**Symptoms**: Unable to initialize custom colors

**Possible Causes**:
- Spectrum not accessible
- Invalid corner selection
- Application blocking screenshot

**Solutions**:
1. Ensure custom color spectrum is visible
2. Click on exact corners of spectrum
3. Close other applications that might block screenshots
4. Restart the application

### Color calibration fails

**Symptoms**: Calibration doesn't complete or produces errors

**Possible Causes**:
- Preview spot not configured
- Spectrum not accessible
- Calibration step too small/large
- Application blocking mouse

**Solutions**:
1. Verify Color Preview Spot is configured
2. Ensure custom color spectrum is accessible
3. Adjust Calibration Step Size (try 2-5)
4. Make sure drawing app doesn't block mouse input
5. Close other applications that might interfere

---

## Drawing Issues

### Drawing starts in wrong location

**Symptoms**: Drawing begins offset from expected location

**Possible Causes**:
- Canvas box incorrect
- Window moved after initialization
- Display scaling changed

**Solutions**:
1. Re-initialize the Canvas tool
2. Ensure drawing app window hasn't moved
3. Check display scaling settings
4. Restart the application if display changed

### Drawing has gaps

**Symptoms**: Some areas of the image are not drawn

**Possible Causes**:
- Pixel size too large
- Ignore White Pixels enabled
- Color not in palette

**Solutions**:
1. Decrease **Pixel Size** for more detail
2. Disable **"Ignore White Pixels"** if needed
3. Verify all needed colors are in palette
4. Check that valid positions include needed colors

### Drawing has artifacts

**Symptoms**: Extra dots or marks appear in drawing

**Possible Causes**:
- Jump delay too low
- Mouse sensitivity too high
- Unexpected cursor movement

**Solutions**:
1. Increase **Jump Delay**
2. Decrease mouse sensitivity in drawing app
3. Increase **Delay** setting
4. Check for interference from other software

### Strokes not appearing

**Symptoms**: Bot moves but no strokes appear

**Possible Causes**:
- Delay too short
- Brush not selected
- Drawing app not active window

**Solutions**:
1. Increase **Delay** setting
2. Ensure brush tool is selected in drawing app
3. Make sure drawing app is the active window
4. Check that drawing app is responding to mouse

---

## Color Issues

### Colors washed out

**Symptoms**: Colors appear lighter/less saturated than source

**Possible Causes**:
- Precision setting too low
- Custom colors not configured
- Palette colors limited

**Solutions**:
1. Increase **Precision** setting
2. Enable and configure custom colors
3. Run color calibration
4. Verify palette has good color variety

### Colors too dark

**Symptoms**: Colors appear darker than source

**Possible Causes**:
- Palette colors too dark
- Custom colors scanning error
- Preview spot not accurate

**Solutions**:
1. Verify palette colors are accurate
2. Re-initialize custom colors
3. Check Color Preview Spot location
4. Run calibration again

### Wrong color selected

**Symptoms**: Bot selects different color than intended

**Possible Causes**:
- Invalid color mapping
- Center points incorrect
- Calibration mismatch

**Solutions**:
1. Re-pick center points in **Manual Color Selection**
2. Use **Precision Estimate** for better accuracy
3. Re-run color calibration
4. Verify valid positions

### Color changes too frequently

**Symptoms**: Bot switches colors excessively

**Possible Causes**:
- Pixel size too small
- Image has many color variations
- Precision too high

**Solutions**:
1. Increase **Pixel Size**
2. Decrease **Precision** setting
3. Use **Slotted mode** for fewer color switches
4. Enable **"Skip First Color"** if applicable

---

## File Management Issues

### Cannot remove calibration

**Symptoms**: Clicking "Remove Calibration" doesn't work

**Possible Causes**:
- File in use by another process
- File permissions issue
- Calibration file doesn't exist

**Solutions**:
1. Stop any running drawing operations
2. Close other applications that might use the file
3. Check file permissions for `color_calibration.json`
4. Check tooltip for specific error message

### Cannot reset config

**Symptoms**: Clicking "Reset Config" doesn't work

**Possible Causes**:
- File in use by application
- File permissions issue
- Config file doesn't exist

**Solutions**:
1. Restart the application
2. Close other instances of Pyaint
3. Check file permissions for `config.json`
4. Manually delete the file if needed

### Confirmation dialog not appearing

**Symptoms**: No confirmation dialog when clicking delete buttons

**Possible Causes**:
- UI unresponsive
- Dialog appearing off-screen
- Application frozen

**Solutions**:
1. Check if application is responding
2. Restart the application
3. Check application logs for errors
4. Try the operation again after restart

### File deletion fails

**Symptoms**: Error message appears when trying to delete files

**Possible Causes**:
- File doesn't exist
- File in use
- Permissions issue
- Disk full

**Solutions**:
1. Check tooltip for specific error message
2. Verify file exists in project directory
3. Close other applications using the file
4. Check disk space
5. Manually delete the file as last resort

### Data lost after reset

**Symptoms**: All settings gone after reset

**Cause**: This is expected behavior of Reset Config

**Prevention**:
1. Always back up `config.json` before resetting
2. Export important settings manually
3. Take screenshots of your setup

**Recovery**:
1. Run **"Setup"** to reconfigure all tools
2. Adjust drawing settings to preferred values
3. Run calibration if using custom colors
4. Consider keeping a backup config file for future reference

### Calibration data outdated

**Symptoms**: Colors don't match after display or application changes

**Cause**: Calibration data from old configuration

**Solutions**:
1. Click **"Remove Calibration"** in File Management section
2. Confirm deletion
3. Reconfigure Custom Colors if needed
4. Run **"Run Calibration"** again
5. Test with a test draw before full drawing

---

## Getting Additional Help

If you're still experiencing issues after trying these solutions:

1. **Check the logs**: Look for error messages in the tooltip panel
2. **Review configuration**: Verify all tools are correctly configured
3. **Test simple cases**: Try with a simple image first
4. **Restart**: Often a simple application restart resolves issues
5. **Consult documentation**: Review the [Tutorial](./tutorial.md) and [Configuration Guide](./configuration.md)

---

## Prevention Tips

To avoid common issues:

1. **Save backups**: Keep a backup of your `config.json`
2. **Test before full drawing**: Always run a test draw first
3. **Keep settings moderate**: Avoid extreme delay or pixel size values
4. **Regular calibration**: Run calibration periodically for best results
5. **Update regularly**: Keep Pyaint updated to latest version
6. **Monitor system**: Ensure system has sufficient resources
7. **Clean setup**: Start fresh if experiencing persistent issues with Reset Config
