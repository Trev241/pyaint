from math import sqrt
import pyautogui
import tkinter
import urllib.request
import time

from PIL import ImageTk, Image

from tkinter import Canvas, Label, Scrollbar, Tk, Button, Radiobutton, messagebox, Checkbutton, DoubleVar, IntVar, StringVar, Entry, END
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
        return sqrt(sum((s - q) ** 2 for s, q in zip(colx, coly)))
    
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
        
        prst = Bot.PALETTE_PRESETS[self.ptype]
        pbox = pyautogui.locateOnScreen(prst[0][0], confidence=self.settings[Bot.CONF])
        self._canvas = pyautogui.locateOnScreen(prst[1], confidence=self.settings[Bot.CONF])
        if self.ptype == '1':
            self._custom_colors = pyautogui.locateOnScreen(prst[2], confidence=self.settings[Bot.CONF])

        if pbox is None or self._canvas is None or (self._custom_colors is None and self.ptype == 1):
            return False
        self._palette = Palette(pbox, prst[0][1], prst[0][2])
        
        return True
    
    def test(self):
        box = self._canvas
        locs = [c[2] for c in self._palette.colors] + [(box[0], box[1]), (box[0] + box[2], box[1] + box[3])]
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
        tw, th = tuple(int(d // step) for d in adjusted_img_size(img, (cw, ch)))
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
                    max_dist = sqrt( sum( max( 255 - col[i], col[i] - 0) ** 2 for i in range(len(col)) ) )
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
                pyautogui.click(self._palette.colors_pos[c], clicks=2, interval=.25)
            else:
                cc_box = self._custom_colors
                pyautogui.PAUSE = .025
                pyautogui.click( (cc_box[0] + cc_box[2] // 2, cc_box[1] + cc_box[3] // 2 ), clicks=2, interval=.25)
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
  
class Window:
    _SLIDER_TOOLTIPS = ('The confidence factor affects the bot\'s accuracy to find its tools. ' + 
                        'Lower confidence allows more room for error but is just as likely to generate false positives. ' + 
                        'Avoid extremely low values.',

                        'Affects the delay (more accurately duration) for each stroke. ' + 
                        'Increase the delay if your machine is slow and does not respond well to extremely fast input',

                        'For more detailed results, reduce the pixel size. Remember that lower pixel sizes imply longer draw times.' +
                        'This setting does not affect the botted application\'s brush size. You must do that manually.',

                        '[ONLY APPLICABLE FOR WHEN CUSTOM COLORS ARE ENABLED] Affects the color accuracy of each pixel. ' +
                        'At lower values, colors will be rounded off to match any previously found color that is similar. ' + 
                        'At 1.0 accuracy, every pixel will have perfect colors ' + 
                        '(this will also have the effect of considerably slowing down the drawing process.)')
    
    _MISC_TOOLTIPS = ('Ignores and does not draw the white pixels of an image. Useful for when the canvas is white.',
                      'Use custom colors. This option considerably lengthens the draw duration.')

    def __init__(self, title, bot, w, h, x, y):
        self._root = Tk()
        
        self._root.title(title)
        self._root.geometry(f"{w}x{h}+{x}+{y}")
        
        self._root.columnconfigure(0, weight=1)
        self._root.columnconfigure(1, weight=5)
        self._root.rowconfigure(0, weight=2)
        self._root.rowconfigure(1, weight=1)
        
        self.bot = bot
        self.draw_options = 0
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
        oframe = LabelFrame(self._root, text='Control Panel')          # Outer frame that will hold the canvas

        self._canvas = Canvas(oframe)
        # Create inner self._cframe that will be held by the canvas
        self._cframe = tkinter.Frame(self._canvas, borderwidth=0, highlightthickness=0)
        self._cframe.pack(fill='both', expand='true')
        scroll = Scrollbar(oframe, orient='vertical', command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=scroll.set)

        self._canvas.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='both')
        self._cvsframe = self._canvas.create_window((0, 0), anchor='nw', window=self._cframe)
        self._canvas.bind('<Configure>', self._cpanel_cvs_config)
        self._cframe.bind('<Configure>', self._cpanel_frm_config)

        self._cframe.columnconfigure(0, weight=1)
        for i in range(14):
            self._cframe.rowconfigure(i, weight=1)

        curr_row = 0

        # Options
        btn_names = ('Setup', 'Test', 'Start')
        buttons = []
        for i in range(len(btn_names)):
            b = Button(self._cframe, text=btn_names[i], font=self.font)
            b.grid(column=0, row=i, padx=5, pady=5, sticky='ew')
            buttons.append(b)
        buttons[0]['command'] = self.setup
        buttons[1]['command'] = self.bot.test
        buttons[2]['command'] = self.start
        
        self._palbel = Label(self._cframe, text='Palette Type', font=self.tfnt)
        self._palbel.grid(column=0, row=3, padx=5, pady=5, sticky='w')
        self._pvarbl = StringVar(self._cframe, '1')
        pvalues = (('MS Paint', '1'), ('skribble.io', '2'))

        curr_row = 4
        for i in range(len(pvalues)):
            Radiobutton(self._cframe, text=pvalues[i][0], 
                value=pvalues[i][1], variable=self._pvarbl, 
                command=self._on_click_rbtn).grid(column=0, row=i + curr_row, sticky='w')
        curr_row += len(pvalues)

        # For every slider option in options, option layout is    :    (name, default, from, to)
        defaults = self.bot.settings
        self._options = (
            ('Confidence', defaults[0], 0, 1), 
            ('Delay', defaults[1], 0, 1), 
            ('Pixel Size', defaults[2], 3, 50),
            ('C. Color Accuracy', defaults[3], 0, 1)
        )
        size = len(self._options)
        self._optvars = [DoubleVar() for _ in range(size)]
        self._optlabl = [Label(self._cframe, text=f"{o[0]}: {o[1]:.2f}", font=self.tfnt) for o in self._options]
        self._optslid = [Scale(self._cframe, from_=self._options[i][2], to=self._options[i][3], variable=self._optvars[i]) for i in range(size)]
        
        for i in range(size):
            self._optslid[i].bind('<ButtonRelease-1>', self._on_slider_move)
            self._optslid[i].set(self._options[i][1])
            self._optslid[i].name = f"scale{i}"
            self._optslid[i].set(defaults[i])
            self._optlabl[i].grid(column=0, row=(i * 2) + curr_row, padx=5, sticky='w')
            self._optslid[i].grid(column=0, row=(i * 2) + curr_row + 1, padx=5, sticky='ew')
        curr_row += size * 2
        
        self._misclbl = Label(self._cframe, text='Misc Settings', font=self.tfnt)
        self._misclbl.grid(column=0, row=curr_row, padx=5, pady=5, sticky='w')
        curr_row += 1

        misc_opt_names = ('Ignore white pixels', 'Use custom colors')
        self._checkbutton_vars = [IntVar() for _ in range(len(misc_opt_names))]
        options = [Bot.IGNORE_WHITE, Bot.USE_CUSTOM_COLORS]
        for i in range(len(misc_opt_names)):
            # The checkbutton submits the index of the option to the callback
            cb = Checkbutton(self._cframe, text=misc_opt_names[i], variable=self._checkbutton_vars[i], 
                font=self.font, command=lambda val=options[i], index=i: self._on_check(index, val))
            cb.grid(column=0, row=i + curr_row, padx=5, sticky='w')
        curr_row += len(misc_opt_names)

        return oframe

    def _cpanel_cvs_config(self, event):
        # Callback function for when the canvas is resized. Use this event to resize the frame to fit the entire canvas
        self._canvas.itemconfig(self._cvsframe, width=event.width)

    def _cpanel_frm_config(self, event):
        # Makes the canvas scrollable
        self._canvas.configure(scrollregion=self._canvas.bbox('all'), width=200)
    
    def _init_ipanel(self):
        # IMAGE PREVIEW FRAME
        frame = LabelFrame(self._root, text='Preview', borderwidth=3, relief='groove')
        frame.columnconfigure(0, weight=5)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        # frame.bind('<Configure>', self._on_resize)

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
        frame = Frame(self._root, borderwidth=3, relief='groove')
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        
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
            self._tlabel['text'] = 'Invalid URL'
    
    def setup(self):
        messagebox.showinfo(self.title, 'Once you click OK, pyaint will wait 5 seconds and then capture your screen.')
        self._root.iconify()
        
        if self.bot.init_tools(5):
            messagebox.showinfo(self.title, 'Found tools successfully!')
            self._tlabel['text'] = 'Found tools successfully!'
        else:
            messagebox.showerror(self.title, 'Failed to find tools.\n1. Do not obstruct the palette and the canvas\n2. ' + 
                'Lower the confidence factor\n3. Ensure that the correct window is maximized\n4. Choose the correct application')
        
        self._root.deiconify()
    
    def _on_check(self, index, option):
        self._tlabel['text'] = Window._MISC_TOOLTIPS[index]
        # Bot options are updated with the newly toggled option
        if self._checkbutton_vars[index].get() == 1:    # 1 indicates that the button has been checked
            self.draw_options |= option
        else:
            self.draw_options &= ~option
        

    def _on_slider_move(self, event):    
        i = int(event.widget.name[-1])
        self.bot.settings[i] = val = float('{:.2f}'.format(self._optvars[i].get()))
        self._optlabl[i]['text'] = f"{self._options[i][0]}: {val}"  
        self._tlabel['text'] = Window._SLIDER_TOOLTIPS[i]
    
    def _on_click_rbtn(self):
        self.bot.ptype = self._pvarbl.get()
        self._tlabel['text'] = 'Informs the bot about the paint application to be botted. You MUST setup if you change this option.'
        
    def start(self):
        messagebox.showwarning(self.title, 'Press ESC to stop the bot.')
        
        self._root.iconify()
        t = time.time() 
        result = self.bot.draw(self._imname, self.draw_options)
        self._root.deiconify
        self._root.wm_state('normal')
        self._tlabel['text'] = f"{'Success' if result else 'Failure'}. Time elapsed: {time.time() - t:.2f}s"