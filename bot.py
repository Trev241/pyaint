import math
import pyautogui
import time
import utils

from PIL import Image

class Palette:
    def __init__(self, box, c_in_row, rows):
        self.box = box
        self.c_in_row = c_in_row
        self.rows = rows
        self._c_size = int(box[2] // c_in_row)
        
        pix = pyautogui.screenshot(region=box).load()
        x, y = self._c_size // 2, self._c_size // 2
        end = c_in_row * self._c_size

        # Obtain RGB values of palette colors along with their coordinates
        # COLOR LAYOUT    :    ((r, g, b) : (x, y))
        self.colors_pos = dict()
        self.colors = set()
        for i in range(c_in_row * 2):
            col = (pix[x, y][:3])
            self.colors_pos[col] = (box[0] + x, box[1] + y)
            self.colors.add(col)

            x = (x + self._c_size) % end
            y = y + (self._c_size if i == c_in_row - 1 else 0)

    def nearest_color(self, query):
        return min(self.colors, key=lambda color: Palette.euclid_dist(color, query))

    @staticmethod
    def euclid_dist(colx, coly):
        return math.sqrt(sum((s - q) ** 2 for s, q in zip(colx, coly)))
    
class Bot:
    CONF, DELAY, STEP, ACCURACY = tuple(i for i in range(4))
    PALETTE_PRESETS = {
        '1' : (('assets/palette_mspaint.png', 10, 2), 'assets/canvas_mspaint.png', 'assets/custom_cols_mspaint.png'), 
        '2' : (('assets/palette_skribbl.png', 11, 2), 'assets/canvas_skribbl.png')
    }
    
    IGNORE_WHITE = 1
    USE_CUSTOM_COLORS = 2

    def __init__(self):
        self.terminate = False
        self.settings = [.75, .05, 5, .75]
        self.ptype = '1'
        self.options = Bot.IGNORE_WHITE
        
        pyautogui.PAUSE = 0.0
    
    def init_tools(self, grace_time):
        time.sleep(grace_time)
        
        preset = Bot.PALETTE_PRESETS[self.ptype]
        pbox = pyautogui.locateOnScreen(preset[0][0], confidence=self.settings[Bot.CONF])
        self._palette = Palette(pbox, preset[0][1], preset[0][2])
        self._canvas = pyautogui.locateOnScreen(preset[1], confidence=self.settings[Bot.CONF])
        if self.ptype == '1':
            self._custom_colors = pyautogui.locateOnScreen(preset[2], confidence=self.settings[Bot.CONF])

        return not (pbox is None or self._canvas is None or (self._custom_colors is None and self.ptype == '1'))
    
    def test(self):
        box = self._canvas
        locs = [p for _, p in self._palette.colors_pos.items()] + [(box[0], box[1]), (box[0] + box[2], box[1] + box[3])]
        for l in locs:
            pyautogui.moveTo(l)
            time.sleep(.25)

    def draw(self, file, flags):
        '''
        Draws the image while taking all settings into consideration.
        The bot's drawing behaviour can be adjusted by modifying the values of
        settings and the flags submitted during this function's call
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
                
                if flags & Bot.USE_CUSTOM_COLORS:
                    col = near = (r, g, b)
                    if len(cmap.keys()) > 0:
                        near = min(cmap.keys(), key=lambda c : Palette.euclid_dist(c, col))
                    # Find the euclidean distance of the furthest color
                    max_dist = math.sqrt( sum( max( 255 - col[i], col[i] - 0) ** 2 for i in range(len(col)) ) )
                    col = near if (max_dist - Palette.euclid_dist(near, col)) / max_dist >= self.settings[Bot.ACCURACY] else col
                else:
                    # Find nearest color. Avoid recomputing for colors encountered before.
                    col = self._palette.nearest_color((r, g, b)) if (r, g, b) not in nearest_colors else nearest_colors[(r, g, b)]
                    nearest_colors[(r, g, b)] = col

                # End brush stroke when...
                # - a new color is encountered 
                # - the brush is at the end of the row
                if j == w - 1 or (old_col != None and old_col != col):
                    end = (x, y)
                    if not ((flags & Bot.IGNORE_WHITE) and old_col == (255, 255, 255)):
                        lines = cmap.get(old_col, [])
                        lines.append( (start, end) )
                        cmap[old_col] = lines 
                    start = (xo, y + step) if j == w - 1 else (x + step, y)
    
                old_col = col
                x += step
            x = xo
            y += step
            
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
