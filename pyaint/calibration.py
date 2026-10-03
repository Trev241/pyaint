"""Custom-colour calibration: scan a spectrum/grid and map RGB -> screen (x, y).

Extracted from ``bot.py`` into a mixin so the engine module stays cohesive.
``Bot`` inherits :class:`CalibrationMixin`; the methods keep using ``self`` and
resolve ``color_calibration_map`` through ``Bot``'s property.
"""
from pyaint.log import log

import json
import math
import time
from typing import Any, Dict, Optional, Tuple

import pyautogui
from PIL import ImageGrab

class CalibrationMixin:
    def _scan_spectrum(self, ccbox):
        """
        Scan the custom colors spectrum to create a color-to-position map.
        The spectrum typically shows a gradient of colors, so we sample it
        to find the closest match for any requested color.
        """
        # Get the box coordinates in (left, top, width, height) format
        left, top, width, height = ccbox[0], ccbox[1], ccbox[2] - ccbox[0], ccbox[3] - ccbox[1]
        
        # Capture the spectrum region
        spectrum_img = pyautogui.screenshot(region=(left, top, width, height))
        pix = spectrum_img.load()
        
        # Sample the spectrum at regular intervals to build a color map
        # Higher sampling = more accurate but slower
        sample_step = 4  # Sample every 4th pixel
        spectrum_map = {}
        
        log.info(f"[Spectrum] Scanning spectrum box: ({left}, {top}, {width}, {height})")
        
        for y in range(0, height, sample_step):
            for x in range(0, width, sample_step):
                try:
                    # Get RGB color at this position
                    r, g, b = pix[x, y][:3]
                    color = (r, g, b)
                    
                    # Store the screen coordinates for this color
                    screen_x = left + x
                    screen_y = top + y
                    spectrum_map[color] = (screen_x, screen_y)
                except (IndexError, TypeError):
                    # Skip invalid pixels
                    continue
        
        log.info(f"[Spectrum] Created spectrum map with {len(spectrum_map)} color positions")
        return spectrum_map

    def calibrate_custom_colors(self, grid_box: Any, preview_point: Any, step: int = 2) -> Dict[Tuple[int, int, int], Tuple[int, int]]:
        """
        Calibrate custom colors by scanning the color spectrum grid and recording
        the RGB values shown in the preview point at each grid position.
        
        Parameters:
            grid_box: list/tuple [x1, y1, x2, y2] defining the color spectrum area
            preview_point: list/tuple [x, y] defining where the selected color is shown
            step: pixel step size for scanning (default 2)
        
        Returns:
            Dictionary mapping RGB tuples to (x, y) coordinates on the grid
        """
        # Reset terminate flag to allow new calibration runs
        self.terminate = False
        self.color_calibration_map = {}
        
        # Store grid parameters for re-scanning if needed
        self._calibration_grid_box = grid_box
        self._calibration_preview_point = preview_point
        
        # Extract grid coordinates
        if isinstance(grid_box, (list, tuple)):
            grid_x = grid_box[0]
            grid_y = grid_box[1]
            # Calculate width/height assuming [x1, y1, x2, y2] format from setup
            grid_width = grid_box[2] - grid_box[0]
            grid_height = grid_box[3] - grid_box[1]
        else:
            # Fallback for dict if passed programmatically with named keys
            grid_x = grid_box['x']
            grid_y = grid_box['y']
            grid_width = grid_box['width']
            grid_height = grid_box['height']
        
        # Extract preview point coordinates
        if isinstance(preview_point, (list, tuple)):
            preview_x = preview_point[0]
            preview_y = preview_point[1]
        else:
            preview_x = preview_point['x']
            preview_y = preview_point['y']
        
        # Define the bbox for 1x1 pixel capture at preview point
        preview_bbox = (preview_x, preview_y, preview_x + 1, preview_y + 1)
        
        log.info(f"[Calibration] Starting calibration of custom colors grid...")
        log.info(f"[Calibration] Grid area: ({grid_x}, {grid_y}, {grid_width}, {grid_height})")
        log.info(f"[Calibration] Preview point: ({preview_x}, {preview_y})")
        log.info(f"[Calibration] Step size: {step}")
        
        # Press mouse down at the start of grid (to grab the slider)
        start_x = grid_x
        start_y = grid_y
        pyautogui.mouseDown(start_x, start_y, button='left')
        time.sleep(0.1)  # Small delay to ensure mouse is pressed
        
        # Track progress for console output
        total_steps = ((grid_width // step) + 1) * ((grid_height // step) + 1)
        current_step = 0
        last_progress = 0
        start_time = time.time()  # Track start time for ETA calculation
        
        # Loop through grid coordinates with step size
        for y in range(grid_y, grid_y + grid_height, step):
            for x in range(grid_x, grid_x + grid_width, step):
                # Increment step counter
                current_step += 1

                # Update progress continuously for UI updates
                self._calibration_progress['current'] = current_step

                # Print progress every 10% or every 100 steps, whichever is more frequent
                progress_percent = (current_step / total_steps) * 100
                if (progress_percent - last_progress >= 10) or (current_step % 100 == 0):
                    # Calculate ETA
                    elapsed_time = time.time() - start_time
                    if current_step > 0:
                        avg_time_per_step = elapsed_time / current_step
                        remaining_steps = total_steps - current_step
                        estimated_remaining = remaining_steps * avg_time_per_step

                        # Format time remaining
                        if estimated_remaining < 60:
                            eta_str = f"{estimated_remaining:.1f}s"
                        elif estimated_remaining < 3600:
                            minutes = int(estimated_remaining // 60)
                            seconds = estimated_remaining % 60
                            eta_str = f"{minutes}:{seconds:02.0f}"
                        else:
                            hours = int(estimated_remaining // 3600)
                            minutes = int((estimated_remaining % 3600) // 60)
                            eta_str = f"{hours}:{minutes:02.0f}h"
                    else:
                        eta_str = "calculating..."

                    log.info(f"[Calibration] Progress: {current_step}/{total_steps} ({progress_percent:.1f}%) - {len(self.color_calibration_map)} colors mapped - ETA: {eta_str}")
                    last_progress = progress_percent
                # Check for termination (ESC key pressed)
                if self.terminate:
                    log.info("[Calibration] Calibration cancelled by user")
                    # Release mouse before exiting
                    try:
                        pyautogui.mouseUp(button='left')
                    except Exception:
                        pass
                    return self.color_calibration_map

                # Move mouse to the current grid position
                pyautogui.moveTo(x, y)
                time.sleep(0.01)  # Small delay to allow UI to update

                # Capture 1x1 pixel at preview point
                try:
                    pixel_img = ImageGrab.grab(bbox=preview_bbox)
                    r, g, b = pixel_img.getpixel((0, 0))
                    color = (r, g, b)

                    # Store the calibration data
                    self.color_calibration_map[color] = (x, y)
                except Exception as e:
                    log.info(f"[Calibration] Error capturing pixel at ({x}, {y}): {e}")
                    continue
        
        # Release mouse up at the end
        pyautogui.mouseUp(button='left')
        
        # Calculate actual time and show completion message
        actual_time = time.time() - start_time
        if actual_time < 60:
            actual_str = f"{actual_time:.1f}s"
        elif actual_time < 3600:
            minutes = int(actual_time // 60)
            seconds = actual_time % 60
            actual_str = f"{minutes}:{seconds:02.0f}"
        else:
            hours = int(actual_time // 3600)
            minutes = int((actual_time % 3600) // 60)
            actual_str = f"{hours}:{minutes:02.0f}h"
        
        log.info(f"[Calibration] Calibration complete. Mapped {len(self.color_calibration_map)} colors.")
        log.info(f"[Calibration] Total time: {actual_str}")
        
        return self.color_calibration_map

    def save_color_calibration(self, filepath: str) -> bool:
        """
        Save the color calibration map to a JSON file.
        
        Parameters:
            filepath: Path to the JSON file to save
        
        Returns:
            True on success, False on failure
        """
        if self.color_calibration_map is None:
            log.info("[Calibration] No calibration data to save.")
            return False
        
        try:
            # Convert tuple keys to string format for JSON compatibility
            calibration_json = {}
            for (r, g, b), (x, y) in self.color_calibration_map.items():
                key = f"{r},{g},{b}"
                calibration_json[key] = [x, y]
            
            # Save to file
            with open(filepath, 'w') as f:
                json.dump(calibration_json, f, indent=2)
            
            log.info(f"[Calibration] Calibration data saved to: {filepath}")
            return True
        except Exception as e:
            log.info(f"[Calibration] Error saving calibration data: {e}")
            return False

    def load_color_calibration(self, filepath: str) -> bool:
        """
        Load color calibration data from a JSON file.
        
        Parameters:
            filepath: Path to the JSON file to load
        
        Returns:
            True on success, False on failure
        """
        try:
            with open(filepath, 'r') as f:
                calibration_json = json.load(f)
            
            # Convert string keys back to tuples
            self.color_calibration_map = {}
            for key, value in calibration_json.items():
                # Parse the key "r,g,b" back to tuple
                r, g, b = map(int, key.split(','))
                self.color_calibration_map[(r, g, b)] = tuple(value)
            
            log.info(f"[Calibration] Calibration data loaded from: {filepath}")
            log.info(f"[Calibration] Loaded {len(self.color_calibration_map)} color mappings.")
            return True
        except FileNotFoundError:
            log.info(f"[Calibration] Calibration file not found: {filepath}")
            return False
        except Exception as e:
            log.info(f"[Calibration] Error loading calibration data: {e}")
            return False

    def get_calibrated_color_position(self, target_rgb: Tuple[int, int, int], tolerance: int = 20, k_neighbors: int = 4) -> Optional[Tuple[int, int]]:
        """
        Find the exact calibrated color position for a target RGB value.
        Uses exact match with tolerance before falling back to spatial interpolation.
        This solves the issue where distinct colors pick the same spot in the custom color spectrum.
        
        Parameters:
            target_rgb: Tuple (r, g, b) representing the target color
            tolerance: Maximum color difference to consider a match (default 20)
            k_neighbors: Number of nearest colors to use for interpolation (default 4)
        
        Returns:
            (x, y) coordinates of the best match, or None if no calibration data exists
        """
        if self.color_calibration_map is None or not self.color_calibration_map:
            log.info(f"[Calibration] ERROR: Calibration map is empty or None!")
            return None
        
        log.info(f"[Calibration] Looking up target color {target_rgb}")
        log.info(f"[Calibration] Calibration map has {len(self.color_calibration_map)} entries")
        
        # First, try to find exact match within tolerance using Manhattan distance
        for color, pos in self.color_calibration_map.items():
            diff = abs(color[0] - target_rgb[0]) + abs(color[1] - target_rgb[1]) + abs(color[2] - target_rgb[2])
            if diff <= tolerance:
                # Found exact match within tolerance
                log.info(f"[Calibration] Exact match found: {target_rgb} ~ {color} (diff={diff}) at {pos}")
                return pos
        
        # If no exact match, use k-nearest neighbors with weighted spatial interpolation
        # This prevents distinct colors from all mapping to the same spot
        color_distances = []
        for color, pos in self.color_calibration_map.items():
            # Calculate Euclidean distance in RGB space
            distance = math.sqrt(
                (color[0] - target_rgb[0]) ** 2 +
                (color[1] - target_rgb[1]) ** 2 +
                (color[2] - target_rgb[2]) ** 2
            )
            color_distances.append((distance, color, pos))
        
        # Sort by distance and get k nearest neighbors
        color_distances.sort(key=lambda x: x[0])
        neighbors = color_distances[:k_neighbors]
        
        # Calculate inverse distance weights (closer colors have more influence)
        # Add a small epsilon to prevent division by zero
        epsilon = 0.0001
        weights = [1.0 / (dist + epsilon) for dist, _, _ in neighbors]
        total_weight = sum(weights)
        
        # Normalize weights
        normalized_weights = [w / total_weight for w in weights]
        
        # Calculate weighted position
        weighted_x = sum(w * pos[0] for w, (_, _, pos) in zip(normalized_weights, neighbors))
        weighted_y = sum(w * pos[1] for w, (_, _, pos) in zip(normalized_weights, neighbors))
        
        # Log the interpolation details
        nearest_color = neighbors[0][1]
        nearest_dist = neighbors[0][0]
        log.info(f"[Calibration] Target: {target_rgb}, Nearest: {nearest_color} (dist={nearest_dist:.2f})")
        log.info(f"[Calibration] Using {k_neighbors}-nearest interpolation to ({weighted_x:.1f}, {weighted_y:.1f})")
        
        return (int(weighted_x), int(weighted_y))
