def adjusted_img_size(img, ad):
    '''
    Recalculates the width and height of an image to fit within a given space.
    If either dimension exceeds the available space, the image will be shrunk to fit accordingly
    without affecting its aspect ratio. This will result in dead space if the aspect ratios of the
    two rectangles do not match.
    '''
    
    aratio = img.size[0] / img.size[1]  
    ew = aratio * ad[1]          # Estimated width if full available height is to be used
    eh = ad[0] / aratio          # Estimated height if full available width is to be used
    ew = int(min(ew, ad[0]))
    eh = int(min(eh, ad[1]))
    
    return ew, eh


def grid_centers(box, rows, cols):
    """Absolute ``(x, y)`` centre of every cell in a ``rows`` x ``cols`` grid.

    ``box`` is ``(x, y, width, height)``. Uses the same integer maths as
    ``Palette``'s automatic centre calculation, so an on-screen preview matches
    exactly where colours are sampled and clicked.
    """
    x, y, width, height = (int(v) for v in box)
    if rows <= 0 or cols <= 0:
        return []
    cell_w = width // cols
    cell_h = height // rows
    return [
        (x + col * cell_w + cell_w // 2, y + row * cell_h + cell_h // 2)
        for row in range(rows)
        for col in range(cols)
    ]


def format_duration(seconds):
    """Format seconds as ``30s``, ``1:30`` or ``1:00h``."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{int(seconds // 60)}:{int(seconds % 60):02d}"
    return f"{int(seconds // 3600)}:{int((seconds % 3600) // 60):02d}h"


def format_estimate(seconds):
    """Human-friendly estimate string, e.g. ``~1:30 minutes``."""
    if seconds < 10:
        return f"~{seconds:.1f} seconds"
    if seconds < 60:
        return f"~{seconds:.0f} seconds"
    if seconds < 3600:
        return f"~{int(seconds // 60)}:{seconds % 60:02.0f} minutes"
    return f"~{int(seconds // 3600)}:{int((seconds % 3600) // 60):02.0f} hours"


def estimate_drawing_seconds(cmap, delay, jump_delay, jump_threshold):
    """Estimate a drawing's duration in seconds from its stroke map."""
    try:
        estimated = 0.0
        for lines in cmap.values():
            last_end = None
            for start_pos, end_pos in lines:
                estimated += delay
                if last_end is not None:
                    jump = (
                        (start_pos[0] - last_end[0]) ** 2
                        + (start_pos[1] - last_end[1]) ** 2
                    ) ** 0.5
                    if jump > jump_threshold:
                        estimated += jump_delay
                last_end = end_pos
        estimated += len(cmap) * 0.5  # colour-switch overhead
        return estimated
    except Exception:
        return 0.0


def estimate_path_seconds(cmap, speed, frame_interval, travel_delay, jump_threshold):
    """Estimate duration for human-style continuous strokes.

    Each stroke is a single button-down/up, so there is no per-stroke delay
    term: time is dominated by ``path_length / speed`` plus a ``travel_delay``
    pause whenever the cursor jumps to a new stroke. ``frame_interval`` is
    accepted for symmetry with the executor and future per-point accounting.
    """
    try:
        estimated = 0.0
        speed = max(float(speed), 1.0)
        for strokes in cmap.values():
            last_end = None
            for stroke in strokes:
                points = [(float(x), float(y)) for x, y in stroke]
                if len(points) < 2:
                    continue
                length = 0.0
                for (x1, y1), (x2, y2) in zip(points, points[1:]):
                    length += ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
                estimated += length / speed
                if last_end is not None:
                    jump = (
                        (points[0][0] - last_end[0]) ** 2
                        + (points[0][1] - last_end[1]) ** 2
                    ) ** 0.5
                    if jump > jump_threshold:
                        estimated += travel_delay
                last_end = points[-1]
        estimated += len(cmap) * 0.5  # colour-switch overhead
        return estimated
    except Exception:
        return 0.0