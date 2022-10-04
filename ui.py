import re
import time
import tkinter
import traceback
import urllib.request
import utils

from bot import Bot
from components import InstructionWindow
from genericpath import isfile
from PIL import (
    Image, 
    ImageTk,
    ImageGrab
)
from pynput.mouse import Listener
from threading import Thread
from tkinter import (
    Canvas, 
    Label, 
    OptionMenu, 
    Scrollbar, 
    StringVar, 
    Tk, 
    Button, 
    messagebox, 
    Checkbutton, 
    DoubleVar, 
    IntVar, 
    Entry, 
    END
)
from tkinter.ttk import LabelFrame, Frame, Scale

class Window:
    _SLIDER_TOOLTIPS = ('The confidence factor affects the bot\'s accuracy to find its tools. ' + 
                        'Lower confidence allows more room for error but is just as likely to generate false positives. ' + 
                        'Avoid extremely low values.',

                        'Affects the delay (more accurately duration) for each stroke. ' + 
                        'Increase the delay if your machine is slow and does not respond well to extremely fast input',

                        'For more detailed results, reduce the pixel size. Remember that lower pixel sizes imply longer draw times.' +
                        'This setting does not affect the botted application\'s brush size. You must do that manually.',

                        '[ONLY APPLICABLE FOR WHEN CUSTOM COLORS ARE ENABLED] Affects the color accuracy of each pixel. ' +
                        'At lower values, the color variety of the result will be greatly reduced. ' + 
                        'At 1.0 accuracy, every pixel will have perfect colors ' + 
                        '(this will also have the effect of considerably slowing down the drawing process.) ' +
                        'Recommended setting: 0.9')
    
    _MISC_TOOLTIPS = ('Ignores and does not draw the white pixels of an image. Useful for when the canvas is white.',
                      'Use custom colors. This option considerably lengthens the draw duration.')

    TITLE_FONT = ('Trebuchet MS', 10, 'bold')
    STD_FONT = ('Trebuchet MS', 9)

    def __init__(self, title, bot, w, h, x, y):
        self._root = Tk()
        
        self._root.title(title)
        self._root.geometry(f"{w}x{h}+{x}+{y}")
        
        self._root.columnconfigure(0, weight=1, uniform='column')
        self._root.columnconfigure(1, weight=2, uniform='column')
        self._root.rowconfigure(0, weight=4, uniform='row')
        self._root.rowconfigure(1, weight=1, uniform='row')
        
        self.bot = bot
        self.draw_options = 0
        self.title = title
        self.busy = False
        
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
        self.tlabel['wraplength'] = self._tpanel.winfo_width() - 5 * 2
        self._set_img(path='assets/sample.png')
        
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

        self._cframe.columnconfigure(0, weight=2)
        self._cframe.columnconfigure(1, weight=1)
        for i in range(19):
            self._cframe.rowconfigure(i, weight=1)

        curr_row = 0

        # Options
        btn_names = (
            'Setup', 
            'Inspect', 
            'Start'
        )
        buttons = []
        for i in range(len(btn_names)):
            b = Button(self._cframe, text=btn_names[i], font=Window.STD_FONT)
            b.grid(column=0, row=i, columnspan=2, padx=5, pady=5, sticky='ew')
            buttons.append(b)
        buttons[0]['command'] = self.setup
        buttons[1]['command'] = self.test
        buttons[2]['command'] = self._start_draw_thread
        
        self._palbel = Label(self._cframe, text='Palette Dimensions', font=Window.TITLE_FONT)
        self._palbel.grid(column=0, row=3, columnspan=2, padx=5, pady=5, sticky='w')
        self._palblr = Label(self._cframe, text='Rows: ', font=Window.STD_FONT)
        self._parows = Entry(self._cframe, width=5)
        self._palblc = Label(self._cframe, text='Columns: ', font=Window.STD_FONT)
        self._pacols = Entry(self._cframe, width=5)

        self._parows.insert(0, '2')
        self._pacols.insert(0, '10')
        vcmd = (self._root.register(self._validate_dimensions), '%P')
        ivcmd = (self._root.register(self._on_invalid_dimensions),)
        self._parows.config(
            validate='all', 
            validatecommand=vcmd, 
            invalidcommand=ivcmd
        )
        self._parows.bind('<FocusOut>', self._on_update_dimensions)
        self._parows.bind('<Return>', self._on_update_dimensions)
        self._pacols.config(
            validate='all',
            validatecommand=vcmd,
            invalidcommand=ivcmd
        )
        self._pacols.bind('<FocusOut>', self._on_update_dimensions)
        self._pacols.bind('<Return>', self._on_update_dimensions)
        self._palblr.grid(column=0, row=4, sticky='w', padx=5, pady=5)
        self._parows.grid(column=1, row=4, sticky='ew', padx=5, pady=5)
        self._palblc.grid(column=0, row=5, sticky='w', padx=5, pady=5)
        self._pacols.grid(column=1, row=5, sticky='ew', padx=5, pady=5)

        self._teclbl = Label(self._cframe, text='Draw Mode', font=Window.TITLE_FONT)
        self._teclbl.grid(column=0, row=6, columnspan=2, sticky='w', padx=5, pady=5)
        modes = [Bot.SLOTTED, Bot.LAYERED]
        self._tecvar = StringVar()
        self._tecvar.set(modes[1])
        self._mode = modes[1]
        self._teclst = OptionMenu(self._cframe, self._tecvar, *modes, command=self._update_mode)
        self._teclst.grid(column=0, row=7, columnspan=2, sticky='ew', padx=5, pady=5)

        curr_row = 8

        # For every slider option in options, option layout is    :    (name, default, from, to)
        defaults = self.bot.settings
        self._options = (
            # ('Confidence', defaults[0], 0, 1), 
            ('Delay', defaults[0], 0, 1), 
            ('Pixel Size', defaults[1], 3, 50),
            ('Custom Color Precision', defaults[2], 0, 1)
        )
        size = len(self._options)
        self._optvars = [DoubleVar() for _ in range(size)]
        self._optlabl = [Label(self._cframe, text=f"{o[0]}: {o[1]:.2f}", font=Window.TITLE_FONT) for o in self._options]
        self._optslid = [Scale(self._cframe, from_=self._options[i][2], to=self._options[i][3], variable=self._optvars[i]) for i in range(size)]
        
        for i in range(size):
            self._optslid[i].bind('<ButtonRelease-1>', self._on_slider_move)
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
                font=Window.STD_FONT, command=lambda val=options[i], index=i: self._on_check(index, val))
            cb.grid(column=0, row=i + curr_row, columnspan=2, padx=5, sticky='w')
        curr_row += len(misc_opt_names)

        return oframe

    def _cpanel_cvs_config(self, event):
        # Callback function for when the canvas is resized. Use this event to resize the frame to fit the entire canvas
        self._canvas.itemconfig(self._cvsframe, width=event.width)

    def _cpanel_frm_config(self, event):
        # Makes the canvas scrollable
        self._canvas.configure(scrollregion=self._canvas.bbox('all'), width=200)
    
    def _validate_dimensions(self, value):
        return re.fullmatch('\d*', value) is not None

    def _on_invalid_dimensions(self):
        self._root.bell()
        self.tlabel['text'] = 'Invalid palette dimensions encountered!'

    def _on_update_dimensions(self, event):
        if event.widget.get() == '':
            Window._set_etext(event.widget, '1')

    def _update_mode(self, selection):
        self._mode = selection

    def _init_ipanel(self):
        # IMAGE PREVIEW FRAME
        frame = LabelFrame(self._root, text='Preview', borderwidth=3, relief='groove')
        frame.columnconfigure(0, weight=4, uniform='column')
        frame.columnconfigure(1, weight=1, uniform='column')
        frame.rowconfigure(0, weight=4, uniform='row')
        frame.rowconfigure(1, weight=1, uniform='row')

        self._imname = 'sample.png'
        self._ilabel = Label(frame)
        self._ilabel.grid(column=0, row=0, columnspan=2, padx=5, pady=5)
        
        self._ientry = Entry(frame)
        Window._set_etext(self._ientry, 'Enter URL or File System Path')
        self._ientry.grid(column=0, row=1, sticky='ew', padx=5, pady=5)
        
        self._ibuttn = Button(frame, text='Search', command=self._on_search_img)
        self._ibuttn.grid(column=1, row=1, sticky='ew', padx=5, pady=5)
        
        return frame
    
    def _init_tpanel(self):
        # TOOLTIP FRAME
        frame = Frame(self._root, borderwidth=3, relief='groove')
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        
        self.tlabel = Label(frame, text='Hello! Begin by pressing "Setup"')
        self.tlabel.grid(column=0, row=0, sticky='ew', padx=5)
        
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
        size = utils.adjusted_img_size(img, (self._ipanel.winfo_width(), self._ipanel.winfo_height() * .8) )
        self._img = ImageTk.PhotoImage(img.resize(utils.adjusted_img_size(img, size)))
        
        self._ilabel['image'] = self._img

    def _on_search_img(self):
        try:
            path = self._ientry.get() if isfile(self._ientry.get()) else urllib.request.urlretrieve(self._ientry.get())[0]
            self._set_img(path=path)
        except Exception as e:
            traceback.print_exc()
            self.tlabel['text'] = e
    
    def _on_check(self, index, option):
        self.tlabel['text'] = Window._MISC_TOOLTIPS[index]
        # Bot options are updated with the newly toggled option
        if self._checkbutton_vars[index].get() == 1:    # 1 indicates that the button has been checked
            self.draw_options |= option
        else:
            self.draw_options &= ~option

    def _on_slider_move(self, event):    
        i = int(event.widget.name[-1])
        self.bot.settings[i] = val = float('{:.2f}'.format(self._optvars[i].get()))
        self._optlabl[i]['text'] = f"{self._options[i][0]}: {val}"  
        self.tlabel['text'] = Window._SLIDER_TOOLTIPS[i]
          
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
        path = 'assets/tutorial'
        pages = (
            (
                f'{path}/intro.png', 
                'This short tutorial will briefly guide you on how to setup the bot.'
            ),
            (
                f'{path}/dimensions.png',
                'Before you continue, switch to the main window and specify the number of distinct colors in your palette for each dimension'
            ),
            (
                f'{path}/regions.png',
                'You will be designating a region on your screen for each tool to help the bot know approximately where to click in order to use its tools.'
            ),
            (
                None,
                'To designate a tool\'s region, you must click on its UPPER LEFT and LOWER RIGHT corners.'
            ),
            (
                f'{path}/help_palette_mspaint.png', 
                'To mark the palette\'s region, you will have to click on the UPPER LEFT and LOWER RIGHT corners as marked in the image.'
            ),
            (
                f'{path}/help_canvas_mspaint.png', 
                'Repeat the same process as explained before for demarcating the canvas as well.'
            ),
            (
                f'{path}/help_custom_cols_mspaint.png', 
                'Once again, repeat the same process for the custom colors option.'
            ),
            (
                None,
                'If you are using a different version of MS Paint or a different application altogether which does not have this tool, ' +
                'then you may mark any two random points on your screen for this step.'
            ),
            (
                f'{path}/sixpoints.png',
                'All in all, the bot will expect you to click in total SIX times - two clicks for each tool. ' +
                'You will hear a ping every time the bot registers a click.'
            ),
            (
                f'{path}/allpoints.png',
                'For MS Paint, the image above demonstrates an example of the order in which you would have to click (beginning from 1 followed to 6). '
            ),
            (
                f'{path}/cspexample.png',
                'Here is an example of a different application. The order of clicks here would be as indicated in the image.'
            ),
            (
                f'{path}/incorrect.png',
                'Remember! Designate ONE tool at a time. For instance, DO NOT click on the upper left corner of the palette and then proceed to click ' +
                'on the custom color option next.'
            ),
            (
                None,
                'You must also mark the tools in this order strictly: PALETTE -> CANVAS -> CUSTOM COLOR.'
            ),
            (
                f'{path}/inspect.png',
                'After the setup is complete, you can inspect the accuracy of the regions marked by clicking on "Inspect"'
            ),
            (
                None,
                'That\'s it! Remember that once you exit this tutorial, you must do as instructed for the setup to succeed. ' +
                '(Tip - Use ALT-TAB to switch between windows)'
            )
        )
        self._iwindow = InstructionWindow(
            parent=self._root, 
            pages=pages, 
            title='Setup Tutorial', 
            on_complete=self._start_listening,
            on_terminate=lambda : self._set_busy(False)
        )

    @is_free
    def test(self):
        try:
            pages = (
                (
                    self._images[0],
                    f'Palette ({self._parows.get()} x {self._pacols.get()} colors)'
                ),
                (
                    self._images[1],
                    'Canvas',
                ),
                (
                    self._images[2],
                    'Custom Colors'
                )
            )
            # Set busy flag to False when inspection is done
            self._iwindow = InstructionWindow(
                parent=self._root, 
                pages=pages, 
                title='Inspect', 
                on_terminate=lambda : self._set_busy(False)
            )
            self.tlabel['text'] = 'Perform the setup again if the tools were not correctly configured.'
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror(title='Error', message=f'{e} - Perform setup first!')
            self._set_busy(False)
            print(e)
        
    def _start_listening(self):
        self._coords = []
        self._images = []
        self._boxes = []
        
        self._clicks = 0
        self._number_of_tools = 3
        
        messagebox.showinfo(self.title, 'Click on the UPPER LEFT and LOWER RIGHT corners of each tool.')
        self._listener = Listener(on_click=self._on_click)
        self._listener.start()

    def _on_click(self, x, y, _, pressed):
        if pressed:
            self._root.bell()
            print(x, y)
            self._clicks += 1
            self._coords += x, y

            # Create a box every 2 clicks
            if self._clicks > 0 and self._clicks % 2 == 0:
                # Determining corner coordinates based on received input. ImageGrab.grab() always expects
                # the first pair of coordinates to be above and on the left of the second pair
                top_left = min(self._coords[0], self._coords[2]), min(self._coords[1], self._coords[3])
                bot_right = max(self._coords[0], self._coords[2]), max(self._coords[1], self._coords[3])
                box = top_left + bot_right
                
                print(f'Capturing box: {box}')
                self._boxes.append(box)
                self._images.append(ImageGrab.grab(box))
                self._coords = []

            if self._clicks >= 2 * self._number_of_tools:
                self._listener.stop()
                
                prows = int(self._parows.get())
                pcols = int(self._pacols.get())

                self.bot.init_tools(prows=prows, pcols=pcols, pbox=self._boxes[0], cabox=self._boxes[1], ccbox=self._boxes[2])
                self._set_busy(False)
                self.tlabel['text'] = 'Setup complete!'

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
            messagebox.showerror('Error', e)
        
        # Let the thread manager know that the task has ended
        self._set_busy(False)
