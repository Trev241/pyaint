import re
import time
import tkinter
import traceback
import urllib.request
import utils

from bot import Bot
from PIL import Image, ImageTk
from threading import Thread
from tkinter import Canvas, Label, OptionMenu, Scrollbar, StringVar, Tk, Button, messagebox, Checkbutton, DoubleVar, IntVar, Entry, END
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
                        'At lower values, colors will be rounded off to match any previously found color that is similar. ' + 
                        'At 1.0 accuracy, every pixel will have perfect colors ' + 
                        '(this will also have the effect of considerably slowing down the drawing process.)')
    
    _MISC_TOOLTIPS = ('Ignores and does not draw the white pixels of an image. Useful for when the canvas is white.',
                      'Use custom colors. This option considerably lengthens the draw duration.')

    TITLE_FONT = ('Trebuchet MS', 10, 'bold')
    STD_FONT = ('Trebuchet MS', 9)

    def __init__(self, title, bot, w, h, x, y):
        self._root = Tk()
        
        self._root.title(title)
        self._root.geometry(f"{w}x{h}+{x}+{y}")
        
        self._root.columnconfigure(0, weight=1)
        self._root.columnconfigure(1, weight=1)
        self._root.rowconfigure(0, weight=2)
        self._root.rowconfigure(1, weight=1)
        
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

        self._cframe.columnconfigure(0, weight=2)
        self._cframe.columnconfigure(1, weight=1)
        for i in range(19):
            self._cframe.rowconfigure(i, weight=1)

        curr_row = 0

        # Options
        btn_names = (
            'Setup', 
            'Test', 
            'Start'
        )
        buttons = []
        for i in range(len(btn_names)):
            b = Button(self._cframe, text=btn_names[i], font=Window.STD_FONT)
            b.grid(column=0, row=i, columnspan=2, padx=5, pady=5, sticky='ew')
            buttons.append(b)
        buttons[0]['command'] = self.setup
        buttons[1]['command'] = self.bot.test
        buttons[2]['command'] = self.start_draw_thread
        
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
            ('Confidence', defaults[0], 0, 1), 
            ('Delay', defaults[1], 0, 1), 
            ('Pixel Size', defaults[2], 3, 50),
            ('C. Color Accuracy', defaults[3], 0, 1)
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
        frame.columnconfigure(0, weight=5)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

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
        
        self.tlabel = Label(frame, text='Hello! Begin by pressing "Setup"')
        self.tlabel.grid(column=0, row=0, sticky='ew', padx=5)
        
        return frame
        
    @staticmethod
    def _set_etext(e, txt):    
        e.delete(0, END)
        e.insert(0, txt)
        
    def _set_img(self, fname='assets/result.png'):
        self._imname = fname
        img = Image.open(self._imname)

        # Resize image
        self._ipanel.update()
        size = utils.adjusted_img_size(img, (self._ipanel.winfo_width(), self._ipanel.winfo_height()) )
        self._img = ImageTk.PhotoImage(img.resize(utils.adjusted_img_size(img, size)))
        
        self._ilabel['image'] = self._img

    def _on_search_img(self):
        try:
            urllib.request.urlretrieve(self._ientry.get(), 'assets/result.png')
            self._set_img('assets/result.png')
        except:
            self.tlabel['text'] = 'Invalid URL'
    
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
          
    def setup(self):
        prows = int(self._parows.get())
        pcols = int(self._pacols.get())
        
        messagebox.showinfo(self.title, 'Once you click OK, pyaint will wait 5 seconds and then capture your screen.')
        self._root.iconify()
        
        try:
            self.bot.init_tools(grace_time=0, prows=prows, pcols=pcols)
            messagebox.showinfo(self.title, 'Found tools successfully!')
            self.tlabel['text'] = 'Found tools successfully!'
        except IndexError as e:
            messagebox.showerror(self.title, e + '\nPossibly due to inconsistent palette dimensions')
        except Exception as e:
            messagebox.showerror(self.title, e)
            self.tlabel['text'] = e
        
        self._root.deiconify()

    def start_draw_thread(self):
        if not self.busy:
            self.busy = True
            
            self._draw_thread = Thread(target=self.start)
            self._draw_thread.start()
            self.manage_draw_thread()
        else:
            self.tlabel['text'] = 'Already started!'

    def manage_draw_thread(self):
        # Display progress updates every half a second
        if self._draw_thread.is_alive() and self.busy:
            self._root.after(500, self.manage_draw_thread)
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
            messagebox.showerror(self.title, e)
            traceback.print_exc()
        
        # Let the thread manager know that the task has ended
        self.busy = False
