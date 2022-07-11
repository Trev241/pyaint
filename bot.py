import math
import pyautogui
import time
import utils

from exceptions import PaintToolError
from PIL import Image

class Palette:
    def __init__(self, box, rows, columns):
        self.box = box
        self.rows = rows
        self.columns = columns

        self._csizex = int(box[2] // columns)
        self._csizey = int(box[3] // rows)

        pix = pyautogui.screenshot(region=box).load()
        x, y = self._csizex // 2, self._csizey // 2
        xend = columns * self._csizex

        # Obtain RGB values of palette colors along with their coordinates
        # COLOR LAYOUT    :    ((r, g, b) : (x, y))
        self.colors_pos = dict()
        self.colors = set()
        for i in range(columns * rows):
            col = (pix[x, y][:3])
            self.colors_pos[col] = (box[0] + x, box[1] + y)
            self.colors.add(col)

            x = (x + self._csizex) % xend
            y = y + (self._csizey if (i + 1) % columns == 0 else 0)

    def nearest_color(self, query):
        return min(self.colors, key=lambda color: Palette.euclid_dist(color, query))

    @staticmethod
    def euclid_dist(colx, coly):
        return math.sqrt(sum((s - q) ** 2 for s, q in zip(colx, coly)))
    
class Bot:
    CONF, DELAY, STEP, ACCURACY = tuple(i for i in range(4))
    RESOURCES = (
        'assets/palette.png',
        'assets/canvas.png',
        'assets/custom_cols_mspaint.png'
    )
    
    IGNORE_WHITE = 1 << 0
    USE_CUSTOM_COLORS = 1 << 1

    def __init__(self):
        self.terminate = False
        self.settings = [.75, .05, 5, .75]
        self.options = Bot.IGNORE_WHITE
        
        pyautogui.PAUSE = 0.0
    
    def init_tools(self, grace_time, prows, pcols):
        time.sleep(grace_time)
        
        pbox = pyautogui.locateOnScreen(Bot.RESOURCES[0], confidence=self.settings[Bot.CONF])
        self._palette = Palette(pbox, rows=prows, columns=pcols)

        self._canvas = pyautogui.locateOnScreen(Bot.RESOURCES[1], confidence=self.settings[Bot.CONF])
        if self._canvas is None:
            raise PaintToolError('Failed to locate canvas and received value None instead')

        self._custom_colors = pyautogui.locateOnScreen(Bot.RESOURCES[2], confidence=self.settings[Bot.CONF])

        return True
    
    def test(self):
        box = self._canvas
        locs = [p for p in self._palette.colors_pos.values()] + [(box[0], box[1]), (box[0] + box[2], box[1] + box[3])]
        for l in locs:
            pyautogui.moveTo(l)
            time.sleep(.25)

    def process(self, file, flags, logger=None):
        '''
        Processes the requested file as per the flags submitted and returns 
        a table mapping each color to a list of lines that are to be drawn on 
        the canvas. Each line contains both starting and terminating coordinates.
        '''
        
        self.terminate = False
        step = int(self.settings[Bot.STEP])
        
        img = Image.open(file).convert('RGBA')
        x, y, cw, ch = self._canvas
        tw, th = tuple(int(p // step) for p in utils.adjusted_img_size(img, (cw, ch)))
        xo = x = x + ((cw - tw * step) // 2)    # Center the drawing correctly
        y += ((ch - th * step) // 2)
    
        img_small = img.resize((tw, th), resample=Image.NEAREST)
        pix = img_small.load()
        w, h = img_small.size
        start = xo, y

        cmap = dict()
        nearest_colors = dict()
        old_col = None
    
        for i in range(h):
            for j in range(w): 
                r, g, b = pix[j, i][:3]
                col = near = (r, g, b)

                # Deciding what to do with new RGB triplet
                if (r, g, b) not in nearest_colors:
                    if flags & Bot.USE_CUSTOM_COLORS:
                        # Find the nearest custom color previously used, if any
                        if len(cmap.keys()) > 0:
                            near = min(cmap.keys(), key=lambda c : Palette.euclid_dist(c, col))
                        # Find the euclidean distance of the furthest color
                        max_dist = math.sqrt( sum( max( 255 - col[i], col[i] - 0) ** 2 for i in range(len(col)) ) )
                        col = near if (max_dist - Palette.euclid_dist(near, col)) / max_dist >= self.settings[Bot.ACCURACY] else col
                    else:
                        # Find the nearest color from the palette
                        col = self._palette.nearest_color((r, g, b))

                    # Save the nearest color for this RGB triplet to avoid recomputing it
                    nearest_colors[(r, g, b)] = col
                else:
                    col = nearest_colors[(r, g, b)]

                # End brush stroke when...
                # 1. a new color is encountered 
                # 2. the brush is at the end of the row
                if j == w - 1 or (old_col != None and old_col != col):
                    end = (x, y)
                    if not ((flags & Bot.IGNORE_WHITE) and old_col == (255, 255, 255)):
                        lines = cmap.get(old_col, [])
                        lines.append( (start, end) )
                        cmap[old_col] = lines
                    start = (xo, y + step) if j == w - 1 else (x + step, y)
                
                if logger is not None:
                    completed = ((i * w + (j + 1)) / w * h) * 100
                    logger['text'] = f"Processing image... {completed}%"

                old_col = col
                x += step

            x = xo
            y += step
        
        return cmap

    def draw(self, cmap):
        '''
        Draws the image as per the coordinates of the processed cmap table.
        Depending upon the selection of colors used, the bot will choose
        from either the standard palette or custom color option accordingly.
        '''
        
        for c, lines in cmap.items():
            if c in self._palette.colors:
                pyautogui.click(self._palette.colors_pos[c], clicks=3, interval=.15)
            else:
                cc_box = self._custom_colors
                pyautogui.PAUSE = .025
                pyautogui.click( (cc_box[0] + cc_box[2] // 2, cc_box[1] + cc_box[3] // 2 ), clicks=3, interval=.15)
                pyautogui.press('tab', presses=7, interval=.05)
                for val in c:
                    numbers = (d for d in str(val))
                    for n in numbers:
                        pyautogui.press(str(n))
                    pyautogui.press('tab')
                pyautogui.press('tab')
                pyautogui.press('enter')
                pyautogui.PAUSE = 0.0

            for line in lines:
                if self.terminate:
                    pyautogui.mouseUp()
                    return False
                
                time.sleep(self.settings[Bot.DELAY])
                pyautogui.moveTo(line[0])
                pyautogui.dragTo(line[1])
                
        return True       
