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