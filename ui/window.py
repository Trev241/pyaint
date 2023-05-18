import json
import time
import tkinter
import traceback
import urllib.request
import utils

from ui.setup import SetupWindow
from tkinter import filedialog
from bot import Bot
from genericpath import isfile
from PIL import (
    Image, 
    ImageTk,
)
from threading import Thread
from tkinter import (
    Canvas, 
    StringVar, 
    Tk, 
    Button, 
    messagebox, 
    DoubleVar, 
    IntVar,
    font, 
    END
)
from tkinter.ttk import (
    LabelFrame, 
    Frame, 
    Scale, 
    Label, 
    OptionMenu, 
    Scrollbar, 
    Button, 
    Checkbutton, 
    Entry
)

class Window:
    _SLIDER_TOOLTIPS = (
        # 'The confidence factor affects the bot\'s accuracy to find its tools. ' + 
        # 'Lower confidence allows more room for error but is just as likely to generate false positives. ' + 
        # 'Avoid extremely low values.',

        'Affects the delay (more accurately duration) for each stroke. ' + 
        'Increase the delay if your machine is slow and does not respond well to extremely fast input',

        'For more detailed results, reduce the pixel size. Remember that lower pixel sizes imply longer draw times.' +
        'This setting does not affect the botted application\'s brush size. You must do that manually.',

        'Affects custom color accuracy for each pixel. ' +
        'At lower values, the color variety of the result will be greatly reduced. ' + 
        'At 1.0 accuracy, every pixel will have perfect colors ' + 
        'Recommended setting: 0.9'    
    )
    
    _MISC_TOOLTIPS = (
        'Ignores and does not draw the white pixels of an image. Useful for when the canvas is white.',
        'Use custom colors. This option considerably lengthens the draw duration.'
    )

    def __init__(self, title, bot, w, h, x, y):
        self._root = Tk()
        
        self._root.title(title)
        self._root.geometry(f"{w}x{h}+{x}+{y}")
        
        self._root.columnconfigure(0, weight=1, uniform='column')
        self._root.columnconfigure(1, weight=2, uniform='column')
        self._root.rowconfigure(0, weight=7, uniform='row')
        self._root.rowconfigure(1, weight=2, uniform='row')

        Window.STD_FONT = font.nametofont('TkDefaultFont').actual()
        Window.TITLE_FONT = (Window.STD_FONT['family'], Window.STD_FONT['size'], 'bold')

        self.bot = bot
        self.draw_options = 0
        self.title = title
        self.busy = False
        
        # TOOLTIP PANEL    :    [1, 0]
        self._tpanel = self._init_tpanel()
        self._tpanel.grid(column=0, row=1, columnspan=2, sticky='nsew', padx=5, pady=5)
        
        # CONTROL PANEL    :    [0, 0]
        self._cpanel = self._init_cpanel()
        self._cpanel.grid(column=0, row=0, sticky='nsew', padx=10, pady=5)
        
        # PREVIEW PANEL    :    [0, 1]
        self._ipanel = self._init_ipanel()
        self._ipanel.grid(column=1, row=0, sticky='nsew', padx=5, pady=5)
        
        
        self._set_img(path='assets/sample.png')
        self.load_config()  # Load saved config 
        
        self._root.mainloop()
        
    def _init_cpanel(self):
        # CONTROL PANEL FRAME
        oframe = LabelFrame(self._root, text='Control Panel')          # Outer frame that will hold the canvas

        self._canvas = Canvas(oframe, borderwidth=0, highlightthickness=0)
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

        self._cframe.columnconfigure(0, weight=2)
        self._cframe.columnconfigure(1, weight=1)
        for i in range(19):
            self._cframe.rowconfigure(i, weight=1)

        curr_row = 0

        # Options
        btn_names = (
            'Setup', 
            # 'Inspect', 
            'Start'
        )
        buttons = []
        for i in range(len(btn_names)):
            b = Button(self._cframe, text=btn_names[i])
            b.grid(column=0, row=i, columnspan=2, padx=5, pady=5, sticky='ew')
            buttons.append(b)
        buttons[0]['command'] = self.setup
        # buttons[1]['command'] = self.test
        buttons[1]['command'] = self._start_draw_thread

        self._teclbl = Label(self._cframe, text='Draw Mode', font=Window.TITLE_FONT)
        self._teclbl.grid(column=0, row=2, columnspan=2, sticky='w', padx=5, pady=5)
        modes = [Bot.SLOTTED, Bot.LAYERED]
        self._tecvar = StringVar()
        self._tecvar.set(modes[1])
        self._mode = modes[1]
        self._teclst = OptionMenu(self._cframe, self._tecvar, self._mode, *modes, command=self._update_mode)
        self._teclst.grid(column=0, row=3, columnspan=2, sticky='ew', padx=5, pady=5)

        curr_row = 4

        # For every slider option in options, option layout is    :    (name, default, from, to)
        defaults = self.bot.settings
        self._options = (
            # ('Confidence', defaults[0], 0, 1), 
            ('Delay', defaults[0], 0, 1), 
            ('Pixel Size', defaults[1], 3, 50),
            ('Precision', defaults[2], 0, 1),
        )
        size = len(self._options)
        self._optvars = [DoubleVar() for _ in range(size)]
        self._optlabl = [Label(self._cframe, text=f"{o[0]}: {o[1]:.2f}", font=Window.TITLE_FONT) for o in self._options]
        self._optslid = [
            Scale(
                self._cframe, 
                from_=self._options[i][2], 
                to=self._options[i][3], 
                variable=self._optvars[i], 
                # Lambda must accept an additional first argument that receives the value of the slider
                command=lambda val, index=i : self._on_slider_move(index, val)
            ) for i in range(size)
        ]
        
        for i in range(size):
            # self._optslid[i].bind('<ButtonRelease-1>', self._on_slider_move)
            self._optslid[i].set(self._options[i][1])
            self._optslid[i].name = f"scale{i}"
            self._optslid[i].set(defaults[i])
            self._optlabl[i].grid(column=0, row=(i * 2) + curr_row, columnspan=2, padx=5, pady=5, sticky='w')
            self._optslid[i].grid(column=0, row=(i * 2) + curr_row + 1, columnspan=2,  padx=5, sticky='ew')
        curr_row += size * 2
        
        self._misclbl = Label(self._cframe, text='Misc Settings', font=Window.TITLE_FONT)
        self._misclbl.grid(column=0, row=curr_row, columnspan=2, padx=5, pady=5, sticky='w')
        curr_row += 1

        misc_opt_names = ('Ignore white pixels', 'Use custom colors')
        self._checkbutton_vars = [IntVar() for _ in range(len(misc_opt_names))]
        options = [Bot.IGNORE_WHITE, Bot.USE_CUSTOM_COLORS]
        for i in range(len(misc_opt_names)):
            # The checkbutton submits the index of the option to the callback
            cb = Checkbutton(self._cframe, text=misc_opt_names[i], variable=self._checkbutton_vars[i], 
                command=lambda val=options[i], index=i: self._on_check(index, val))
            cb.grid(column=0, row=i + curr_row, columnspan=2, padx=5, sticky='w')
        curr_row += len(misc_opt_names)

        return oframe

    def _cpanel_cvs_config(self, event):
        # Callback function for when the canvas is resized. Use this event to resize the frame to fit the entire canvas
        self._canvas.itemconfig(self._cvsframe, width=event.width)

    def _cpanel_frm_config(self, event):
        # Makes the canvas scrollable
        self._canvas.configure(scrollregion=self._canvas.bbox('all'), width=200)

    def _update_mode(self, selection):
        self._mode = selection

    def _init_ipanel(self):
        # IMAGE PREVIEW FRAME
        frame = LabelFrame(self._root, text='Preview', borderwidth=3, relief='groove')
        frame.columnconfigure(0, weight=3, uniform='column')
        frame.columnconfigure(1, weight=1, uniform='column')
        frame.columnconfigure(2, weight=1, uniform='column')
        frame.rowconfigure(0, weight=4, uniform='row')
        frame.rowconfigure(1, weight=1, uniform='row')

        self._imname = 'sample.png'
        self._ilabel = Label(frame)
        self._ilabel.bind(
            '<Configure>', 
            lambda e : self._set_img(path=self._imname)
        )
        self._ilabel.grid(column=0, row=0, columnspan=3, sticky='ns', padx=5, pady=5)
        
        self._ientry = Entry(frame)
        Window._set_etext(self._ientry, 'Enter URL or File System Path')
        self._ientry.grid(column=0, row=1, sticky='ew', padx=5, pady=5)
        
        self._ibuttn = Button(frame, text='Search', command=self._on_search_img)
        self._ibuttn.grid(column=1, row=1, sticky='ew', padx=5, pady=5)
        self._fbuttn = Button(frame, text='Open File', command=self._open_file)
        self._fbuttn.grid(column=2, row=1, sticky='ew', padx=5, pady=5)

        return frame
    
    def _init_tpanel(self):
        # TOOLTIP FRAME
        frame = Frame(self._root, borderwidth=3, relief='groove')
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        
        self.tlabel = Label(frame, text='Hello! Begin by pressing "Setup"')
        self.tlabel.bind('<Configure>', lambda e : self.tlabel.config(wraplength=e.width))
        self.tlabel.grid(column=0, row=0, sticky='nsew', padx=5)
        
        return frame
        
    @staticmethod
    def _set_etext(e, txt):    
        e.delete(0, END)
        e.insert(0, txt)
        
    def _set_img(self, image=None, path=None):
        if image is not None:
            img = image
        else:
            self._imname = path if path is not None else 'assets/sample.png'
            img = Image.open(self._imname)

        # Resize image
        self._ipanel.update()
        size = utils.adjusted_img_size(img, (self._ipanel.winfo_width() - 10, self._ipanel.winfo_height() * .8 - 10) )
        self._img = ImageTk.PhotoImage(img.resize(size))
        
        self._ilabel['image'] = self._img

    def _on_search_img(self):
        try:
            path = self._ientry.get() if isfile(self._ientry.get()) else urllib.request.urlretrieve(self._ientry.get())[0]
            self._set_img(path=path)
        except Exception as e:
            traceback.print_exc()
            self.tlabel['text'] = e

    def _open_file(self):
        try:
            path = filedialog.askopenfile(parent=self._root)
            if path is not None:
                self._set_img(path=path.name)
        except Exception as e:
            self.tlabel['text'] = e
    
    def _on_check(self, index, option):
        self.tlabel['text'] = Window._MISC_TOOLTIPS[index]
        # Bot options are updated with the newly toggled option
        if self._checkbutton_vars[index].get() == 1:    # 1 indicates that the button has been checked
            self.draw_options |= option
        else:
            self.draw_options &= ~option

    def _on_slider_move(self, index, val): 
        self.bot.settings[index] = val = round(float(val), 3)
        self._optlabl[index]['text'] = f"{self._options[index][0]}: {val}"  
        self.tlabel['text'] = Window._SLIDER_TOOLTIPS[index]

    def load_config(self):
        try:
            with open('config.json', 'r') as f:
                self.tools = json.load(f)
            try:
                self.bot.init_palette(
                    # Converting string key into tuple
                    colors_pos={
                        tuple(map(int, k[1:-1].split(', '))): tuple(v) 
                        for k, v in self.tools['Palette']['color_coords'].items()
                    }
                )
                self.bot.init_canvas(self.tools['Canvas']['box'])
                self.bot.init_custom_colors(self.tools['Custom Colors']['box'])
                self.tlabel['text'] = 'Successfully loaded old setup from config file.'
            except Exception as e:
                traceback.print_exc()
                self.tlabel['text'] = 'Some tools have not been initialized. This may prevent the bot from working correctly.'
        except Exception as e:
            self.tools = {
                'Palette': { 
                    'status': False, 
                    'box': None, 
                    'rows': 1,
                    'cols': 1,
                    'color_coords': None,
                    'preview': None,
                },
                'Canvas': { 
                    'status': False, 
                    'box': None, 
                    'preview': None,
                }, 
                'Custom Colors': { 
                    'status': False,
                    'box': None,
                    'preview': None,
                },
            }
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(self.tools, f, ensure_ascii=False, indent=4)
            self.tlabel['text'] = f'Config file was either missing or incorrectly modified and has been reset. Please perform setup again. Traceback: {e}'
          
    def is_free(func):
        '''
        Decorator that only executes a function when the bot is not busy by checking the self.busy flag.
        Useful for when you do not want some functions to interefere with each other.
        Tasks that use this decorator SHOULD set self.busy to False when they finish! Failure to do so
        will prevent other processes marked with this decorator from starting.
        '''

        def decorator(self):
            if self.busy:
                self.tlabel['text'] = "Cannot perform action. Currently busy..."
            else:
                self.busy = True
                func(self)
        
        return decorator

    def _set_busy(self, val):
        self.busy = val

    @is_free
    def setup(self):
        self.load_config()
        self._iwindow = SetupWindow(parent=self._root, bot=self.bot, tools=self.tools, on_complete=self._on_complete_setup, title='Setup')

    def _on_complete_setup(self):
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(self.tools, f, ensure_ascii=False, indent=4)        
        self.tlabel['text'] = 'Setup saved.'
        self._set_busy(False)

    @is_free
    def _start_draw_thread(self):
        self._draw_thread = Thread(target=self.start)
        self._draw_thread.start()
        self._manage_draw_thread()

    def _manage_draw_thread(self):
        # Display progress updates every half a second
        if self._draw_thread.is_alive() and self.busy:
            self._root.after(500, self._manage_draw_thread)
            self.tlabel['text'] = f"Processing image: {self.bot.progress:.2f}%"

    def start(self):
        try:
            t = time.time() 
            cmap = self.bot.process(self._imname, flags=self.draw_options, mode=self._mode)
            messagebox.showwarning(self.title, 'Press ESC to stop the bot.')
            self._root.iconify()
            result = self.bot.draw(cmap)
            self._root.deiconify
            self._root.wm_state('normal')
            self.tlabel['text'] = f"{'Success' if result else 'Failure'}. Time elapsed: {time.time() - t:.2f}s"
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror(self.title,  e)
        
        # Let the thread manager know that the task has ended
        self._set_busy(False)