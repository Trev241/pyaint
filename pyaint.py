import pyautogui
import itertools
import urllib.request
import time

from PIL.Image import Resampling
from PIL import ImageTk, Image

from tkinter import Label, Tk, Button, Radiobutton, messagebox, Checkbutton, DoubleVar, IntVar, StringVar, Entry, END
from tkinter.ttk import LabelFrame, Frame, Scale

def adjusted_img_size(img, ad):
    '''
    Recalculates the width and height of an image to fit within a given space (represented by ad)
    If either dimension exceeds the available space, the image will be shrunk to fit accordingly
    without affecting its aspect ratio. This will result in dead space which is commonly seen in the
    form of black boxes on some applications.
    '''
    
    aratio = img.size[0] / img.size[1]  
    ew = aratio * ad[1]                # Estimated width if full available height is to be used
    eh = (1 / aratio) * ad[0]          # Estimated height if full available width is to be used
    ew = int(min(ew, ad[0]))
    eh = int(min(eh, ad[1]))
    
    return ew, eh

class Palette:
    def __init__(self, box, c_in_row, rows):
        self._c_size = int(box[2] // c_in_row)
        self.box = box
        self.c_in_row = c_in_row
        self.rows = rows
        
        pix = pyautogui.screenshot(region=box).load()
        x, y = self._c_size // 2, self._c_size // 2
        end = c_in_row * self._c_size

        # Obtain RGB values of palette colors along with their coordinates
        # COLOR LAYOUT    :    (index, (r, g, b), (x, y))
        self.colors = tuple(
            map(lambda t : (t[0], pix[t[1], t[2]], (box[0] + t[1], box[1] + t[2])), 
                [(j, i if i < end else i % end, y + (0 if i < end else self._c_size)) for i, j in itertools.zip_longest(range(x, end * 2, self._c_size), range(c_in_row * rows))])
        )
        
        # Alternatively, this also produces the same result
        # self.colors = list()
        # for i in range(c_in_row * 2):
        #     self.colors.append((pix[x, y], box[0] + x, box[1] + y))
        #     x = (x + c_size) % end
        #     y = y + (c_size if i == c_in_row - 1 else 0)
        # self.colors = tuple(self.colors)
        
        # Alternatively, an even more verbose list comprehension
        # self.colors = list(map(lambda i : (pix[(x + ((i * c_size)) % (c_in_row * c_size)) - palette[0], (y + (0 if i < c_in_row else c_size)) - palette[1]], (x + ((i * c_size)) % (c_in_row * c_size)), (y + (0 if i < c_in_row else c_size))), [i for i in range(c_in_row * 2)]))
    
    def nearest_color(self, query):
        return min(self.colors, key = lambda color: sum((s - q) ** 2 for s, q in zip(color[1], query)))
    
class Bot:
    CONF, DELAY, STEP = tuple(i for i in range(3))
    PALETTE_PRESETS = {'1' : (('assets/palette_mspaint.png', 10, 2), 'assets/canvas_mspaint.png'), 
        '2' : (('assets/palette_skribbl.png', 11, 2), 'assets/canvas_skribbl.png')}

    def __init__(self):
        self.terminate = False
        self.settings = [.75, .05, 5]
        self.ptype = '1'
        self.ignwhite = 0
        
        pyautogui.PAUSE = 0.0
    
    def init_tools(self, grace_time):
        time.sleep(grace_time)
        
        prst = Bot.PALETTE_PRESETS[self.ptype]
        pbox = pyautogui.locateOnScreen(prst[0][0], confidence=self.settings[Bot.CONF])
        self._canvas = pyautogui.locateOnScreen(prst[1], confidence=self.settings[Bot.CONF])
        if pbox is None or self._canvas is None:
            return False
        self._palette = Palette(pbox, prst[0][1], prst[0][2])
        
        return True
    
    def test(self):
        box = self._canvas
        locs = [c[2] for c in self._palette.colors] + [(box[0], box[1]), (box[0] + box[2], box[1] + box[3])]
        for l in locs:
            pyautogui.moveTo(l)
            time.sleep(.25)

    def draw(self, file):
        self.terminate = False
        step = int(self.settings[Bot.STEP])
        
        img = Image.open(file).convert('RGBA')
        x, y, cw, ch = self._canvas
        tw, th = tuple(int(d // step) for d in adjusted_img_size(img, (cw, ch)))
        xo = x = x + ((cw - tw * step) // 2)    # Center the drawing correctly
        y += ((ch - th * step) // 2)
    
        img_small = img.resize((tw, th), resample=Resampling.BILINEAR)
        pix = img_small.load()
        w, h = img_small.size
        start = xo, y

        cmap = tuple(list() for _ in range(len(self._palette.colors)))
        ncmap = dict()
        old_col = None
    
        for i in range(h):
            for j in range(w): 
                r, g, b = pix[j, i][:3]
                
                # Find nearest color. Avoid recomputing for colors encountered before.
                col = self._palette.nearest_color((r, g, b)) if (r, g, b) not in ncmap else ncmap[(r, g, b)]
                
                # End brush stroke when...
                # - a new color is encountered 
                # - the brush is at the end of the row
                if j == w - 1 or (old_col != None and old_col != col):
                    end = (x, y)
                    
                    if not (self.ignwhite and old_col[1] == (255, 255, 255)):
                        cmap[old_col[0]].append((start, end))
                    
                    start = (xo, y + step) if j == w - 1 else (x + step, y)
    
                old_col = col
                x += step
        
            x = xo
            y += step
            
        for i in range(len(cmap)):
            # Ignore colors that do no exist in the final render
            if len(cmap[i]) == 0:
                continue
            
            pyautogui.click(self._palette.colors[i][2], clicks=2, interval=.25)
            for line in cmap[i]:
                if self.terminate:
                    pyautogui.mouseUp()
                    return False
                
                time.sleep(self.settings[Bot.DELAY])
                pyautogui.moveTo(line[0])
                pyautogui.dragTo(line[1])
                
        return True       
  
class Window:
    # TODO    :    Refactor all options that share similar properties to some kind of class
    _TOOLTIPTEXT = ('The confidence factor affects the bot\'s accuracy to find its tools. Lower confidence allows more room for error but is just as likely to generate false positives. Avoid extremely low values.',
                    'Affects the delay (more accurately duration) for each stroke. Increase the delay if your machine is slow and does not respond well to extremely fast input',
                    'For more detailed results, reduce the pixel size. Remember that lower pixel sizes imply longer draw times. This setting does not affect the botted application\'s brush size. You must do that manually.')
    
    def __init__(self, title, bot, w, h, x, y):
        self._root = Tk()
        
        self._root.title(title)
        self._root.geometry(f"{w}x{h}+{x}+{y}")
        
        self._root.columnconfigure(0, weight=1)
        self._root.columnconfigure(1, weight=5)
        self._root.rowconfigure(0, weight=2)
        self._root.rowconfigure(1, weight=1)
        
        self.bot = bot
        self.tfnt = ('Trebuchet MS', 9, 'bold')
        self.font = ('Trebuchet MS', 9)
        self.title = title
        
        # CONTROL PANEL    :    [0, 0]
        self._cpanel = self._init_cpanel()
        self._cpanel.grid(column=0, row=0, sticky='nsew', padx=5, pady=5)
        
        # PREVIEW PANEL    :    [0, 1]
        self._ipanel = self._init_ipanel()
        self._ipanel.grid(column=1, row=0, sticky='nsew', padx=5, pady=5)
        
        # TOOLTIP PANEL    :    [1, 0]
        self._tpanel = self._init_tpanel()
        self._tpanel.grid(column=0, row=1, columnspan=2, sticky='nsew', padx=5, pady=5)
        self._tpanel.update()
        
        # Work to do after the window is visible (necessary for certain widgets to have their widths and heights established
        self._tlabel['wraplength'] = self._tpanel.winfo_width() - 5 * 2
        self._set_img('assets/sample.png')
        
        self._root.mainloop()
        
    def _init_cpanel(self):
        # CONTROL PANEL FRAME
        frame = LabelFrame(self._root, text='Control Panel')
        frame.columnconfigure(0, weight=1)
        for i in range(13):
            frame.rowconfigure(i, weight=2)
        frame['borderwidth'] = 3
        frame['relief'] = 'groove'

        curr_row = 0

        # Options
        self._bsetup = Button(frame, text='Setup', font=self.font, command=self.setup)
        self._bsetup.grid(column=0, row=0, padx=5, sticky='ew')
        self._btestp = Button(frame, text='Test', font=self.font, command=self.bot.test)
        self._btestp.grid(column=0, row=1, padx=5, sticky='ew')
        self._bstart = Button(frame, text='Start', font=self.font, command=self.start)
        self._bstart.grid(column=0, row=2, padx=5, sticky='ew')
        
        self._opt_ignorewhite = IntVar()
        self._cwhite = Checkbutton(frame, text='Ignore white pixels', variable=self._opt_ignorewhite, font=self.font, command=self._on_check)
        self._cwhite.grid(column=0, row=3, padx=5, sticky='ew')
        
        self._palbel = Label(frame, text='Palette Type', font=self.tfnt)
        self._palbel.grid(column=0, row=4, padx=5, sticky='w')
        self._pvarbl = StringVar(frame, '1')
        pvalues = (('MS Paint', '1'), ('skribble.io', '2'))

        curr_row = 5
        for i in range(len(pvalues)):
            Radiobutton(frame, text = pvalues[i][0], value = pvalues[i][1], variable=self._pvarbl, command=self._on_click_rbtn).grid(column=0, row=i + curr_row, sticky='w')
        curr_row += len(pvalues)

        # For every option in options, option layout is    :    (name, default, from, to)
        defaults = self.bot.settings
        self._options = (('Confidence', defaults[0], 0, 1), ('Delay', defaults[1], 0, 1), ('Pixel Size', defaults[2], 3, 50))
        size = len(self._options)
        self._optvars = [DoubleVar() for _ in range(size)]
        self._optlabl = [Label(frame, text=f"{o[0]}: {o[1]:.2f}", font=self.tfnt) for o in self._options]
        self._optslid = [Scale(frame, from_=self._options[i][2], to=self._options[i][3], variable=self._optvars[i]) for i in range(size)]
        
        for i in range(size):
            self._optslid[i].bind('<ButtonRelease-1>', self._on_slider_move)
            self._optslid[i].set(self._options[i][1])
            self._optslid[i].name = f"scale{i}"
            self._optslid[i].set(defaults[i])
            self._optlabl[i].grid(column=0, row=(i * 2) + curr_row, padx=5, sticky='w')
            self._optslid[i].grid(column=0, row=(i * 2) + curr_row + 1, padx=5, sticky='ew')
        curr_row += size * 2
        
        return frame
    
    def _init_ipanel(self):
        # IMAGE PREVIEW FRAME
        frame = LabelFrame(self._root, text='Preview')
        frame.columnconfigure(0, weight=5)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        # frame.bind('<Configure>', self._on_resize)
        frame['borderwidth'] = 3
        frame['relief'] = 'groove'

        self._imname = 'sample.png'
        self._ilabel = Label(frame)
        self._ilabel.grid(column=0, row=0, padx=5, pady=5)
        
        self._ientry = Entry(frame)
        Window._set_etext(self._ientry, 'Enter image URL')
        self._ientry.grid(column=0, row=1, sticky='ew', padx=5, pady=5)
        
        self._ibuttn = Button(frame, text='Search', command=self._on_search_img)
        self._ibuttn.grid(column=1, row=1, sticky='ew', padx=5, pady=5)
        
        return frame
    
    def _init_tpanel(self):
        # TOOLTIP FRAME
        frame = Frame(self._root)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        frame.grid(column=0, row=1, sticky='ew')
        frame['borderwidth'] = 3
        frame['relief'] = 'groove'
        
        self._tlabel = Label(frame, text='Hello! Begin by pressing "Setup"')
        self._tlabel.grid(column=0, row=0, sticky='ew', padx=5)
        
        return frame
        
    @staticmethod
    def _set_etext(e, txt):    
        e.delete(0, END)
        e.insert(0, txt)
        
    def _set_img(self, fname='assets/result.png'):
        self._imname = fname
        img = Image.open(self._imname)
        self._ipanel.update()
        size = adjusted_img_size(img, (self._ipanel.winfo_width(), self._ipanel.winfo_height()) )
        self._img = ImageTk.PhotoImage(img.resize(adjusted_img_size(img, size)))
        self._ilabel['image'] = self._img
        
    # def _on_resize(self, event):
    #     self._set_img()    
    
    def _on_search_img(self):
        try:
            urllib.request.urlretrieve(self._ientry.get(), 'assets/result.png')
            self._set_img('assets/result.png')
        except:
            self._tlabel['text'] = 'Invalid URL submitted'
    
    def setup(self):
        messagebox.showinfo(self.title, 'Once you click OK, pyaint will wait 5 seconds and then capture your screen.')
        self._root.iconify()
        
        if self.bot.init_tools(5):
            messagebox.showinfo(self.title, 'Found tools successfully!')
            self._tlabel['text'] = 'Found tools successfully!'
        else:
            messagebox.showerror(self.title, 'Failed to find tools.\n1. Do not obstruct the palette and the canvas\n2. Lower the confidence factor\n3. Ensure that the correct window is maximized\n4. Choose the correct application')
        
        self._root.deiconify()
    
    def _on_check(self):
        self.bot.ignwhite = self._opt_ignorewhite.get()
        self._tlabel['text'] = 'Ignores drawing the white pixels of an image. Useful for when the canvas is white.'

    def _on_slider_move(self, event):    
        i = int(event.widget.name[-1])
        self.bot.settings[i] = val = float('{:.2f}'.format(self._optvars[i].get()))
        self._optlabl[i]['text'] = f"{self._options[i][0]}: {val}"  
        self._tlabel['text'] = Window._TOOLTIPTEXT[i]
    
    def _on_click_rbtn(self):
        self.bot.ptype = self._pvarbl.get()
        self._tlabel['text'] = 'Informs the bot about the paint application to be botted. You MUST setup if you change this option.'
        
    def start(self):
        messagebox.showwarning(self.title, 'You can stop the bot at any time by pressing any key.')
        
        self._root.iconify()
        t = time.time() 
        result = self.bot.draw(self._imname)
        self._root.deiconify()
        self._tlabel['text'] = f"{'Success' if result else 'Failure'}. Time elapsed: {time.time() - t:.2f}s"