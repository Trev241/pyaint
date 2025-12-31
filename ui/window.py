import json
import os
import time
import tkinter
import traceback
import urllib.request
import urllib.error as urllib_error
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
        'Recommended setting: 0.9',

        'Adds delay when cursor jumps more than 5 pixels between strokes. ' +
        'Helps prevent unintended strokes from rapid cursor movement. ' +
        'Recommended: 0.5 seconds'
    )
    
    _MISC_TOOLTIPS = (
        'Ignores and does not draw the white pixels of an image. Useful for when the canvas is white.',
        'Use custom colors. This option considerably lengthens the draw duration.'
    )

    def __init__(self, title, bot, w, h, x, y):
        self._root = Tk()
        # Prevent saving during initial UI setup (slider.set etc.)
        self._initializing = True
        # Config path should be available immediately because some widget
        # callbacks trigger during initialization and may attempt to save.
        self._config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')

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

        # Initialize tools dict early so _init_ipanel can access it
        self.tools = {}
        
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
        # Determine config file path relative to project root (one level up from ui/)
        self._config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
        self.load_config()  # Load saved config
        # UI initialization finished — allow saving
        self._initializing = False

        self._root.mainloop()

    def __del__(self):
        """Clean up cache directory on application exit"""
        try:
            import shutil
            cache_dir = 'cache'
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir)
                print(f"Cleaned up cache directory: {cache_dir}")
        except Exception as e:
            print(f"Warning: Could not clean up cache directory: {e}")
        
    def _init_cpanel(self):
        # CONTROL PANEL FRAME
        oframe = LabelFrame(self._root, text='Control Panel')          # Outer frame that will hold the canvas

        self._canvas = Canvas(oframe, borderwidth=0, highlightthickness=0)
        # Create inner self._cframe that will be held by the canvas
        self._cframe = tkinter.Frame(self._canvas, borderwidth=0, highlightthickness=0)
        self._cframe.pack(fill='both', expand=True)
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
        btn_names = [
            'Setup',
            # 'Inspect',
            'Pre-compute',
            'Test Draw',
            'Start'
        ]

        buttons = []
        for i in range(len(btn_names)):
            b = Button(self._cframe, text=btn_names[i])
            b.grid(column=0, row=i, columnspan=2, padx=5, pady=5, sticky='ew')
            buttons.append(b)
        buttons[0]['command'] = self.setup
        # buttons[1]['command'] = self.test
        buttons[1]['command'] = self._precompute_thread
        buttons[2]['command'] = self._test_draw_thread
        buttons[3]['command'] = self._start_draw_thread

        self._teclbl = Label(self._cframe, text='Draw Mode', font=Window.TITLE_FONT)
        self._teclbl.grid(column=0, row=4, columnspan=2, sticky='w', padx=5, pady=5)
        modes = [Bot.SLOTTED, Bot.LAYERED]
        self._tecvar = StringVar()
        self._tecvar.set(modes[1])
        self._mode = modes[1]
        self._teclst = OptionMenu(self._cframe, self._tecvar, self._mode, *modes, command=self._update_mode)
        self._teclst.grid(column=0, row=5, columnspan=2, sticky='ew', padx=5, pady=5)

        curr_row = 6

        # For every slider option in options, option layout is    :    (name, default, from, to)
        defaults = self.bot.settings
        self._options = (
            # ('Confidence', defaults[0], 0, 1),
            ('Delay', defaults[0], 0, 1),
            ('Pixel Size', defaults[1], 3, 50),
            ('Precision', defaults[2], 0, 1),
            ('Jump Delay', defaults[3] if len(defaults) > 3 else 0.5, 0, 2),
        )
        size = len(self._options)
        # Use IntVar for Pixel Size (index 1), DoubleVar for others
        self._optvars = []
        for i in range(size):
            if i == 1:  # Pixel Size
                self._optvars.append(IntVar())
            else:
                self._optvars.append(DoubleVar())

        self._optlabl = []
        for i, o in enumerate(self._options):
            if i == 1:  # Pixel Size - show as integer
                self._optlabl.append(Label(self._cframe, text=f"{o[0]}: {int(o[1])}", font=Window.TITLE_FONT))
            else:
                self._optlabl.append(Label(self._cframe, text=f"{o[0]}: {o[1]:.2f}", font=Window.TITLE_FONT))
        self._optslid = [
            Scale(
                self._cframe,
                from_=self._options[i][2],
                to=self._options[i][3],
                variable=self._optvars[i],
                command=lambda val, index=i : self._on_slider_move(index, val)
            ) for i in range(size)
        ]
        
        for i in range(size):
            # self._optslid[i].bind('<ButtonRelease-1>', self._on_slider_move)
            self._optslid[i].set(self._options[i][1])
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

        # New Layer option
        Label(self._cframe, text='New Layer', font=Window.TITLE_FONT).grid(column=0, row=curr_row, padx=5, pady=5, sticky='w')
        self._newlayer_var = IntVar()
        self._newlayer_cb = Checkbutton(self._cframe, text='Enable New Layer', variable=self._newlayer_var,
            command=self._on_newlayer_toggle)
        self._newlayer_cb.grid(column=1, row=curr_row, padx=5, pady=5, sticky='w')
        curr_row += 1

        # Pause Key Setting
        Label(self._cframe, text='Pause Key', font=Window.TITLE_FONT).grid(column=0, row=curr_row, padx=5, pady=5, sticky='w')
        self._pause_key_entry = Entry(self._cframe)
        self._pause_key_entry.grid(column=1, row=curr_row, padx=5, pady=5, sticky='ew')
        self._pause_key_entry.bind('<Key>', self._on_pause_key_entry_press)
        curr_row += 1

        # Redraw Region section
        Label(self._cframe, text='Redraw Region', font=Window.TITLE_FONT).grid(column=0, row=curr_row, columnspan=2, padx=5, pady=5, sticky='w')
        curr_row += 1

        # Redraw buttons
        self._redraw_pick_btn = Button(self._cframe, text='Pick Region', command=self._on_redraw_pick)
        self._redraw_pick_btn.grid(column=0, row=curr_row, padx=5, pady=5, sticky='ew')
        self._redraw_draw_btn = Button(self._cframe, text='Draw Region', command=self._redraw_draw_thread)
        self._redraw_draw_btn.grid(column=1, row=curr_row, padx=5, pady=5, sticky='ew')
        curr_row += 1

        # Redraw region display
        self._redraw_region_label = Label(self._cframe, text='No region selected', font=('TkDefaultFont', 8))
        self._redraw_region_label.grid(column=0, row=curr_row, columnspan=2, padx=5, pady=5, sticky='w')
        curr_row += 1

        # Initialize redraw state
        self._redraw_region = None  # Will store (x1, y1, x2, y2) canvas coordinates
        self._redraw_picking = False  # Flag for when we're in region selection mode

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
        self._last_url = None  # Store the last entered URL
        self._ilabel = Label(frame)
        self._ilabel.bind(
            '<Configure>',
            lambda e : self._set_img(path=self._imname)
        )
        self._ilabel.grid(column=0, row=0, columnspan=3, sticky='ns', padx=5, pady=5)

        self._ientry = Entry(frame)
        # Initialize with placeholder - will be updated after config loads
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

        # Check cache status and update status (only if canvas is initialized)
        if hasattr(self.bot, '_canvas') and self.bot._canvas is not None:
            has_cache, _ = self.bot.get_cached_status(self._imname, flags=self.draw_options, mode=self._mode)
            if has_cache:
                self.tlabel['text'] = 'Cached computation available ✓'
            else:
                self.tlabel['text'] = 'No cached computation - will process live'
        else:
            self.tlabel['text'] = 'Loading configuration...'

    def _fetch_remote_image(self, url, timeout=10, retries=3):
        """Fetch remote image with proper headers and error handling"""
        import tempfile
        import os

        # Create a proper request with headers
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )

        for attempt in range(retries):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    # Check if response is actually an image
                    content_type = response.headers.get('content-type', '').lower()
                    if not content_type.startswith('image/'):
                        raise ValueError(f"URL does not point to an image (content-type: {content_type})")

                    # Create temporary file
                    fd, temp_path = tempfile.mkstemp(suffix='.png')
                    try:
                        with os.fdopen(fd, 'wb') as tmp_file:
                            tmp_file.write(response.read())
                        return temp_path
                    except Exception:
                        os.close(fd)
                        if os.path.exists(temp_path):
                            os.unlink(temp_path)
                        raise

            except urllib_error.HTTPError as e:
                if e.code == 429:  # Rate limited
                    wait_time = min(2 ** attempt, 10)  # Exponential backoff, max 10s
                    print(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}/{retries}")
                    time.sleep(wait_time)
                    continue
                elif e.code >= 400:
                    raise ValueError(f"HTTP {e.code}: {e.reason}")
                else:
                    raise
            except urllib_error.URLError as e:
                if attempt == retries - 1:
                    raise ValueError(f"Network error: {e.reason}")
                continue

        raise ValueError("Failed to fetch image after all retries")

    def _on_search_img(self):
        try:
            input_text = self._ientry.get().strip()
            if not input_text:
                self.tlabel['text'] = 'Please enter a URL or file path'
                return

            # Check if it's a local file first
            if isfile(input_text):
                path = input_text
                # Don't save file paths as URLs
                self._last_url = None
            else:
                # Try to fetch as remote image
                self.tlabel['text'] = 'Fetching remote image...'
                path = self._fetch_remote_image(input_text)
                # Save the URL for persistence
                self._last_url = input_text
                self.tools['last_image_url'] = input_text
                try:
                    if not getattr(self, '_initializing', False):
                        with open(self._config_path, 'w', encoding='utf-8') as f:
                            json.dump(self.tools, f, ensure_ascii=False, indent=4)
                        print(f"Saved config to {self._config_path}; keys={list(self.tools.keys())}")
                except Exception as e:
                    print(f"Failed to save config: {e}")

            self._set_img(path=path)
            self.tlabel['text'] = f'Image loaded successfully'

        except ValueError as e:
            self.tlabel['text'] = f'Error: {str(e)}'
        except Exception as e:
            traceback.print_exc()
            self.tlabel['text'] = f'Unexpected error: {str(e)}'

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

        # Save drawing options to config
        if 'drawing_options' not in self.tools:
            self.tools['drawing_options'] = {}
        self.tools['drawing_options']['ignore_white_pixels'] = bool(self.draw_options & Bot.IGNORE_WHITE)
        self.tools['drawing_options']['use_custom_colors'] = bool(self.draw_options & Bot.USE_CUSTOM_COLORS)
        try:
            if not getattr(self, '_initializing', False):
                with open(self._config_path, 'w', encoding='utf-8') as f:
                    json.dump(self.tools, f, ensure_ascii=False, indent=4)
                print(f"Saved config to {self._config_path}; keys={list(self.tools.keys())}")
        except Exception as e:
            print(f"Failed to save config: {e}")

    def _on_newlayer_toggle(self):
        enabled = bool(self._newlayer_var.get())
        # Update bot state and tools dict
        self.bot.new_layer['enabled'] = enabled
        if 'New Layer' not in self.tools:
            self.tools['New Layer'] = {'status': False, 'coords': None, 'modifiers': {'ctrl': False, 'alt': False, 'shift': False}}
        self.tools['New Layer']['enabled'] = enabled
        try:
            if not getattr(self, '_initializing', False):
                with open(self._config_path, 'w', encoding='utf-8') as f:
                    json.dump(self.tools, f, ensure_ascii=False, indent=4)
                print(f"Saved config to {self._config_path}; keys={list(self.tools.keys())}")
        except Exception as e:
            print(f"Failed to save config: {e}")

    def _on_slider_move(self, index, val):
        val = float(val)
        if index == 1:  # Pixel Size - force to integer
            val = int(round(val))
            self.bot.settings[index] = val
            self._optlabl[index]['text'] = f"{self._options[index][0]}: {val}"
        else:
            self.bot.settings[index] = round(val, 3)
            self._optlabl[index]['text'] = f"{self._options[index][0]}: {val:.2f}"

        # Save drawing settings to config
        if 'drawing_settings' not in self.tools:
            self.tools['drawing_settings'] = {}
        self.tools['drawing_settings']['delay'] = self.bot.settings[0]
        self.tools['drawing_settings']['pixel_size'] = self.bot.settings[1]
        self.tools['drawing_settings']['precision'] = self.bot.settings[2]
        self.tools['drawing_settings']['jump_delay'] = self.bot.settings[3]

        try:
            try:
                if not getattr(self, '_initializing', False):
                    with open(self._config_path, 'w', encoding='utf-8') as f:
                        json.dump(self.tools, f, ensure_ascii=False, indent=4)
                else:
                    # Skip saving during initialization
                    pass
            except Exception as e:
                print(f"Failed to save config: {e}")
            else:
                if not getattr(self, '_initializing', False):
                    print(f"Saved config to {self._config_path}; keys={list(self.tools.keys())}")
        except Exception as e:
            print(f"Failed to save config: {e}")

        self.tlabel['text'] = Window._SLIDER_TOOLTIPS[index]

    def _on_pause_key_entry_press(self, event):
        # Only allow setting the pause key when not drawing
        if not self.busy:
            # When not drawing, allow setting the pause key by typing in the entry field
            key_name = event.keysym.lower()
            # Handle special cases
            if key_name.startswith('f') and key_name[1:].isdigit():
                key_name = key_name  # f1, f2, etc.
            elif len(key_name) > 1:
                # For special keys, keep as-is
                pass
            else:
                # For regular keys, use the char
                key_name = event.char.lower() if event.char else key_name

            # Update the entry field and bot's pause key
            self._pause_key_entry.delete(0, END)
            self._pause_key_entry.insert(0, key_name)
            self.bot.pause_key = key_name

            # Save the pause key to config file
            self.tools['pause_key'] = key_name
            try:
                if not getattr(self, '_initializing', False):
                    with open(self._config_path, 'w', encoding='utf-8') as f:
                        json.dump(self.tools, f, ensure_ascii=False, indent=4)
            except Exception as e:
                print(f"Failed to save config: {e}")

            return "break"

        # This should never be reached when not busy, but just in case
        print(f"Unexpected pause key press while busy={self.busy}")
        return "break"

    def load_config(self):
        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                self.tools = json.load(f)
            print(f"Loaded config from {self._config_path}; keys={list(self.tools.keys())}")

            # Load pause key first
            self.bot.pause_key = self.tools.get('pause_key', 'p')
            self._pause_key_entry.delete(0, END)
            self._pause_key_entry.insert(0, self.bot.pause_key)

            # Load saved drawing settings
            if 'drawing_settings' in self.tools:
                settings = self.tools['drawing_settings']
                # Update bot settings
                self.bot.settings = [
                    settings.get('delay', 0.1),
                    settings.get('pixel_size', 12),
                    settings.get('precision', 0.9),
                    settings.get('jump_delay', 0.5)
                ]
                # Update UI sliders
                for i, val in enumerate(self.bot.settings):
                    if i == 1:  # Pixel Size - force to integer
                        val = int(val)
                    self._optvars[i].set(val)
                    if i == 1:  # Pixel Size - show as integer
                        self._optlabl[i]['text'] = f"{self._options[i][0]}: {val}"
                    else:
                        self._optlabl[i]['text'] = f"{self._options[i][0]}: {val:.2f}"

            # Load saved drawing options
            if 'drawing_options' in self.tools:
                options = self.tools['drawing_options']
                # Update ignore white pixels checkbox
                ignore_white = options.get('ignore_white_pixels', True)
                self._checkbutton_vars[0].set(1 if ignore_white else 0)
                if ignore_white:
                    self.draw_options |= Bot.IGNORE_WHITE
                else:
                    self.draw_options &= ~Bot.IGNORE_WHITE

                # Update use custom colors checkbox
                use_custom = options.get('use_custom_colors', False)
                self._checkbutton_vars[1].set(1 if use_custom else 0)
                if use_custom:
                    self.draw_options |= Bot.USE_CUSTOM_COLORS
                else:
                    self.draw_options &= ~Bot.USE_CUSTOM_COLORS

            # Update URL entry field with last saved URL if available
            last_url = self.tools.get('last_image_url', '')
            if last_url:
                self._ientry.delete(0, END)
                self._ientry.insert(0, last_url)
                self._last_url = last_url

            # Try to load old setup data (Palette, Canvas, Custom Colors) if available
            try:
                if 'Palette' in self.tools and self.tools['Palette'].get('color_coords'):
                    self.bot.init_palette(
                        # Converting string key into tuple
                        colors_pos={
                            tuple(map(int, k[1:-1].split(', '))): tuple(v)
                            for k, v in self.tools['Palette']['color_coords'].items()
                        }
                    )
                if 'Canvas' in self.tools and self.tools['Canvas'].get('box'):
                    self.bot.init_canvas(self.tools['Canvas']['box'])
                if 'Custom Colors' in self.tools and self.tools['Custom Colors'].get('box'):
                    self.bot.init_custom_colors(self.tools['Custom Colors']['box'])

                self.tlabel['text'] = 'Successfully loaded setup from config file.'
            except Exception:
                # Old setup data might be missing or invalid, but new settings loaded
                self.tlabel['text'] = 'Loaded settings from config. Setup may need to be redone for full functionality.'

        except Exception as e:
            # Config file missing or invalid, use defaults without overwriting
            self.tools = {
                'pause_key': 'p',
            }
            self.bot.pause_key = 'p'
            self._pause_key_entry.delete(0, END)
            self._pause_key_entry.insert(0, 'p')
            self.tlabel['text'] = f'Config file missing or invalid ({str(e)}). Using default settings.'

        # Apply New Layer settings to bot if present
        try:
            nl = self.tools.get('New Layer')
            if nl:
                # coords may be stored as list
                coords = nl.get('coords')
                if isinstance(coords, list) and len(coords) >= 2:
                    self.bot.new_layer['coords'] = (int(coords[0]), int(coords[1]))
                elif isinstance(coords, tuple):
                    self.bot.new_layer['coords'] = coords
                self.bot.new_layer['enabled'] = bool(nl.get('enabled', nl.get('status', False)))
                mods = nl.get('modifiers', {})
                self.bot.new_layer['modifiers']['ctrl'] = bool(mods.get('ctrl', False))
                self.bot.new_layer['modifiers']['alt'] = bool(mods.get('alt', False))
                self.bot.new_layer['modifiers']['shift'] = bool(mods.get('shift', False))
                # Update UI checkbox
                self._newlayer_var.set(1 if self.bot.new_layer['enabled'] else 0)
        except Exception:
            pass

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
        # Ensure setup tools exist with default structure if missing
        default_tools = {
            'Palette': {
                'status': False,
                'box': None,
                'rows': 6,
                'cols': 8,
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
            'New Layer': {
                'status': False,
                'coords': None,
                'enabled': False,
                'modifiers': {
                    'ctrl': False,
                    'alt': False,
                    'shift': False
                }
            }
        }

        # Build a dedicated setup_tools mapping (only the tools) so the
        # SetupWindow doesn't iterate non-tool keys (like drawing_settings).
        setup_tools = {}
        for tool_name in ['Palette', 'Canvas', 'Custom Colors', 'New Layer']:
            existing = self.tools.get(tool_name, {})
            merged = default_tools[tool_name].copy()
            merged.update(existing if isinstance(existing, dict) else {})
            setup_tools[tool_name] = merged

        # Keep a reference so we can merge results back into self.tools
        self._setup_tools = setup_tools
        self._iwindow = SetupWindow(parent=self._root, bot=self.bot, tools=self._setup_tools, on_complete=self._on_complete_setup, title='Setup')

    def _on_complete_setup(self):
        # If SetupWindow returned modified setup data, merge it back into self.tools
        if hasattr(self, '_setup_tools'):
            for k, v in self._setup_tools.items():
                self.tools[k] = v

        # If New Layer was configured during setup, apply it to bot state
        try:
            nl = self.tools.get('New Layer')
            if nl:
                coords = nl.get('coords')
                if isinstance(coords, list) and len(coords) >= 2:
                    self.bot.new_layer['coords'] = (int(coords[0]), int(coords[1]))
                elif isinstance(coords, tuple):
                    self.bot.new_layer['coords'] = coords
                self.bot.new_layer['enabled'] = bool(nl.get('enabled', nl.get('status', False)))
                mods = nl.get('modifiers', {})
                self.bot.new_layer['modifiers']['ctrl'] = bool(mods.get('ctrl', False))
                self.bot.new_layer['modifiers']['alt'] = bool(mods.get('alt', False))
                self.bot.new_layer['modifiers']['shift'] = bool(mods.get('shift', False))
                # Update main UI checkbox to reflect new state
                try:
                    self._newlayer_var.set(1 if self.bot.new_layer['enabled'] else 0)
                except Exception:
                    pass
        except Exception:
            pass

        # The SetupWindow has already modified self._setup_tools, so save everything
        self.tools['pause_key'] = self._pause_key_entry.get().strip() or 'p'
        self.bot.pause_key = self.tools['pause_key']

        # Convert tuples to lists for JSON serialization
        for tool_name in ['Canvas', 'Custom Colors']:
            if tool_name in self.tools and 'box' in self.tools[tool_name]:
                box = self.tools[tool_name]['box']
                if isinstance(box, tuple):
                    self.tools[tool_name]['box'] = list(box)

        # Save current drawing settings
        if 'drawing_settings' not in self.tools:
            self.tools['drawing_settings'] = {}
        self.tools['drawing_settings']['delay'] = self.bot.settings[0]
        self.tools['drawing_settings']['pixel_size'] = self.bot.settings[1]
        self.tools['drawing_settings']['precision'] = self.bot.settings[2]
        self.tools['drawing_settings']['jump_delay'] = self.bot.settings[3]

        # Save current drawing options
        if 'drawing_options' not in self.tools:
            self.tools['drawing_options'] = {}
        self.tools['drawing_options']['ignore_white_pixels'] = bool(self.draw_options & Bot.IGNORE_WHITE)
        self.tools['drawing_options']['use_custom_colors'] = bool(self.draw_options & Bot.USE_CUSTOM_COLORS)

        # Save current URL if any
        if hasattr(self, '_last_url') and self._last_url:
            self.tools['last_image_url'] = self._last_url

        try:
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(self.tools, f, ensure_ascii=False, indent=4)
            self.tlabel['text'] = 'Setup saved.'
        except Exception as e:
            self.tlabel['text'] = f'Failed to save config: {str(e)}'

        self._set_busy(False)

    @is_free
    def _precompute_thread(self):
        self._precompute_thread = Thread(target=self.precompute)
        self._precompute_thread.start()
        self._manage_precompute_thread()

    def _manage_precompute_thread(self):
        if self._precompute_thread.is_alive() and self.busy:
            self._root.after(500, self._manage_precompute_thread)
            self.tlabel['text'] = f"Pre-computing: {self.bot.progress:.2f}%"
        elif self.busy:
            # Pre-compute finished
            self.tlabel['text'] = 'Pre-compute completed! Cache saved.'
            self._set_busy(False)

    def precompute(self):
        try:
            cache_file = self.bot.precompute(self._imname, flags=self.draw_options, mode=self._mode)

            # Load the cached data to estimate drawing time
            cache_data = self.bot.load_cached(cache_file)
            if cache_data:
                drawing_eta = self.bot.estimate_drawing_time(cache_data['cmap'])
                self.tlabel['text'] = f'Pre-compute completed! Estimated drawing time: {drawing_eta}'
            else:
                self.tlabel['text'] = f'Pre-compute completed! Cache saved.'

        except Exception as e:
            traceback.print_exc()
            messagebox.showerror(self.title, f'Pre-compute failed: {str(e)}')
        finally:
            self._set_busy(False)

    @is_free
    def _test_draw_thread(self):
        self._test_draw_thread = Thread(target=self.test_draw)
        self._test_draw_thread.start()
        self._manage_test_draw_thread()

    def _manage_test_draw_thread(self):
        # Display progress updates every half a second
        if self._test_draw_thread.is_alive() and self.busy:
            self._root.after(500, self._manage_test_draw_thread)
            self.tlabel['text'] = f"Test drawing: {self.bot.progress:.2f}%"
        elif self.busy:
            # Test draw finished
            self.tlabel['text'] = 'Test draw completed!'
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

    def test_draw(self):
        try:
            t = time.time()

            # Check for cached computation first
            has_cache, cache_file = self.bot.get_cached_status(self._imname, flags=self.draw_options, mode=self._mode)
            if has_cache:
                # Load from cache
                print(f"Loading from cache: {cache_file}")
                cache_data = self.bot.load_cached(cache_file)
                if cache_data:
                    cmap = cache_data['cmap']
                    # Log cache details
                    num_colors = len(cmap)
                    total_points = sum(len(lines) for lines in cmap.values())
                    cache_time = time.ctime(cache_data['timestamp'])
                    print(f"Cache loaded - {num_colors} colors, {total_points} coordinate points")
                    print(f"Cached on: {cache_time}")
                    print(f"Settings: Delay={cache_data['settings'][0]}, PixelSize={cache_data['settings'][1]}")
                    self.tlabel['text'] = f"Using cached computation for test draw"
                else:
                    # Cache invalid, fall back to processing
                    print("Cache file invalid, processing live...")
                    cmap = self.bot.process(self._imname, flags=self.draw_options, mode=self._mode)
            else:
                # No cache, process normally
                print("No cache available, processing live...")
                cmap = self.bot.process(self._imname, flags=self.draw_options, mode=self._mode)

            # Count total lines and limit to first 20 (or fewer if less available)
            total_lines = sum(len(lines) for lines in cmap.values())
            test_lines = min(20, total_lines)
            print(f"Test drawing first {test_lines} lines out of {total_lines} total")

            messagebox.showinfo(self.title, f'Test drawing the first {test_lines} lines. Adjust your brush size in the painting app, then use the full "Start" button.')
            self._root.iconify()
            # Clear any previous termination/paused state so test can be retried
            self.bot.terminate = False
            self.bot.paused = False
            self.bot.drawing = False
            self.bot.draw_state = {
                'color_idx': 0,
                'line_idx': 0,
                'segment_idx': 0,
                'current_color': None,
                'was_paused': False
            }

            result = self.bot.test_draw(cmap, max_lines=test_lines)
            self._root.deiconify()  # type: ignore
            self._root.wm_state('normal')  # type: ignore
            if result == 'success':
                self.tlabel['text'] = f"Test draw completed. Time elapsed: {time.time() - t:.2f}s"
            elif result == 'terminated':
                self.tlabel['text'] = f"Test draw terminated by user. Time elapsed: {time.time() - t:.2f}s"
                # Clear termination so future tests can run
                self.bot.terminate = False
            else:
                self.tlabel['text'] = f"Test draw result: {result}"
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror(self.title, str(e))

        # Let the thread manager know that the task has ended
        self._set_busy(False)

    def _on_redraw_pick(self):
        """Start region selection mode for redraw functionality (like canvas setup)"""
        if not hasattr(self.bot, '_canvas') or self.bot._canvas is None:
            messagebox.showerror(self.title, "Canvas not configured. Please run Setup first.")
            return

        self._redraw_picking = True
        self._coords = []
        self._clicks = 0
        self._required_clicks = 2

        # Prompt user like the setup process
        if messagebox.askokcancel(self.title, "Click on the UPPER LEFT and LOWER RIGHT corners of the region you want to redraw.") == True:
            from pynput.mouse import Listener
            self._listener = Listener(on_click=self._on_redraw_click)
            self._listener.start()
            self._root.iconify()

    def _on_redraw_click(self, x, y, button, pressed):
        """Handle mouse clicks for redraw region selection (like setup canvas selection)"""
        if pressed:
            self._root.bell()
            print(x, y)
            self._clicks += 1
            self._coords += x, y

            if self._clicks == self._required_clicks:
                # Determining corner coordinates based on received input. ImageGrab.grab() always expects
                # the first pair of coordinates to be above and on the left of the second pair
                top_left = min(self._coords[0], self._coords[2]), min(self._coords[1], self._coords[3])
                bot_right = max(self._coords[0], self._coords[2]), max(self._coords[1], self._coords[3])
                box = top_left + bot_right
                print(f'Capturing box: {box}')

                # Store the selected region coordinates
                self._redraw_region = box
                self._redraw_region_label['text'] = f"Region: ({box[0]}, {box[1]}) to ({box[2]}, {box[3]})"
                self.tlabel['text'] = "Redraw region selected. Click 'Draw Region' to start drawing."
                self._redraw_picking = False

                self._listener.stop()
                self._root.deiconify()

                messagebox.showinfo(self.title, f"Region selected!\n\nTop-left: ({box[0]}, {box[1]})\nBottom-right: ({box[2]}, {box[3]})\n\nYou can now click 'Draw Region' to redraw this area.")

    def _get_redraw_region_manual(self):
        """Get redraw region coordinates manually from user input"""
        # Create a simple dialog to get coordinates
        import tkinter.simpledialog as sd

        try:
            x1 = sd.askinteger(self.title, "Enter X coordinate of first point (top-left):")
            if x1 is None:
                self._cancel_redraw_pick()
                return

            y1 = sd.askinteger(self.title, "Enter Y coordinate of first point (top-left):")
            if y1 is None:
                self._cancel_redraw_pick()
                return

            x2 = sd.askinteger(self.title, "Enter X coordinate of second point (bottom-right):")
            if x2 is None:
                self._cancel_redraw_pick()
                return

            y2 = sd.askinteger(self.title, "Enter Y coordinate of second point (bottom-right):")
            if y2 is None:
                self._cancel_redraw_pick()
                return

            # Validate coordinates
            if x1 >= x2 or y1 >= y2:
                messagebox.showerror(self.title, "Invalid region: first point must be above and left of second point.")
                self._cancel_redraw_pick()
                return

            self._redraw_region = (x1, y1, x2, y2)
            self._redraw_region_label['text'] = f"Region: ({x1}, {y1}) to ({x2}, {y2})"
            self.tlabel['text'] = "Redraw region selected. Click 'Draw Region' to start drawing."
            self._redraw_picking = False

        except Exception as e:
            messagebox.showerror(self.title, f"Error getting coordinates: {str(e)}")
            self._cancel_redraw_pick()

    def _cancel_redraw_pick(self):
        """Cancel the redraw region selection"""
        self._redraw_picking = False
        self.tlabel['text'] = "Redraw region selection cancelled."

    @is_free
    def _redraw_draw_thread(self):
        """Start the redraw region drawing process"""
        if self._redraw_region is None:
            messagebox.showerror(self.title, "No redraw region selected. Please click 'Pick Region' first.")
            return

        if not hasattr(self.bot, '_canvas') or self.bot._canvas is None:
            messagebox.showerror(self.title, "Canvas not configured. Please run Setup first.")
            return

        self._redraw_thread = Thread(target=self.redraw_region)
        self._redraw_thread.start()
        self._manage_redraw_thread()

    def _manage_redraw_thread(self):
        """Manage the redraw thread progress"""
        if self._redraw_thread.is_alive() and self.busy:
            self._root.after(500, self._manage_redraw_thread)
            self.tlabel['text'] = f"Processing redraw region: {self.bot.progress:.2f}%"
        elif self.busy:
            # Redraw finished
            self.tlabel['text'] = 'Redraw region completed!'
            self._set_busy(False)

    def redraw_region(self):
        """Process and draw only the selected region"""
        try:
            t = time.time()

            # Convert canvas region to reference image region
            canvas_region = self._redraw_region  # (x1, y1, x2, y2) in canvas coordinates
            image_region = self._canvas_to_image_region(canvas_region)

            print(f"Canvas region: {canvas_region}")
            print(f"Image region: {image_region}")

            # Process only the selected region of the image and draw it at the selected canvas location
            canvas_target = (canvas_region[0], canvas_region[1], canvas_region[2] - canvas_region[0], canvas_region[3] - canvas_region[1])
            cmap = self.bot.process_region(self._imname, image_region, flags=self.draw_options, mode=self._mode, canvas_target=canvas_target)

            if not cmap or len(cmap) == 0:
                self.tlabel['text'] = "No drawable content found in selected region."
                return

            # Show drawing time estimate
            drawing_eta = self.bot.estimate_drawing_time(cmap)
            print(f"Estimated redraw time: {drawing_eta}")
            self.tlabel['text'] = f"Starting redraw - ETA: {drawing_eta}"

            messagebox.showwarning(self.title, f'Redrawing selected region.\nPress ESC to stop the bot. Press {self.bot.pause_key} to pause/resume.')
            self._root.iconify()

            # Clear any previous termination/paused state
            self.bot.terminate = False
            self.bot.paused = False
            self.bot.drawing = False
            self.bot.draw_state = {
                'color_idx': 0,
                'line_idx': 0,
                'segment_idx': 0,
                'current_color': None,
                'was_paused': False
            }

            result = self.bot.draw(cmap)
            self._root.deiconify()
            self._root.wm_state('normal')

            if result == 'success':
                self.tlabel['text'] = f"Redraw completed. Time elapsed: {time.time() - t:.2f}s"
            elif result == 'terminated':
                self.tlabel['text'] = f"Redraw terminated by user. Time elapsed: {time.time() - t:.2f}s"
                self.bot.terminate = False
            elif result == 'paused':
                self.tlabel['text'] = f"Redraw paused. Press {self.bot.pause_key} again to resume."
            else:
                self.tlabel['text'] = f"Unknown redraw result: {result}"

        except Exception as e:
            traceback.print_exc()
            messagebox.showerror(self.title, f'Redraw failed: {str(e)}')
        finally:
            self._set_busy(False)

    def _canvas_to_image_region(self, canvas_region):
        """Convert canvas coordinates to reference image coordinates"""
        x1, y1, x2, y2 = canvas_region

        # Get canvas dimensions
        canvas_x, canvas_y, canvas_w, canvas_h = self.bot._canvas

        # Load the reference image to get its dimensions
        img = Image.open(self._imname)
        img_w, img_h = img.size

        # Calculate scaling factors
        scale_x = img_w / canvas_w
        scale_y = img_h / canvas_h

        # Convert canvas coordinates to image coordinates
        img_x1 = int((x1 - canvas_x) * scale_x)
        img_y1 = int((y1 - canvas_y) * scale_y)
        img_x2 = int((x2 - canvas_x) * scale_x)
        img_y2 = int((y2 - canvas_y) * scale_y)

        # Ensure coordinates are within image bounds
        img_x1 = max(0, min(img_x1, img_w))
        img_y1 = max(0, min(img_y1, img_h))
        img_x2 = max(0, min(img_x2, img_w))
        img_y2 = max(0, min(img_y2, img_h))

        return (img_x1, img_y1, img_x2, img_y2)

    def _capture_redraw_points(self):
        """Capture two mouse clicks to define the redraw region"""
        import pyautogui
        import keyboard

        points = []
        click_count = 0
        last_mouse_state = False

        print("Mouse capture started. Press 'ESC' to cancel.")
        print("Move mouse to first point and click...")

        try:
            while click_count < 2 and not keyboard.is_pressed('esc'):
                # Check for mouse click (detect press, not hold)
                current_mouse_state = pyautogui.mouseDown()
                if current_mouse_state and not last_mouse_state:
                    # Mouse was just pressed
                    x, y = pyautogui.position()
                    points.append((x, y))
                    click_count += 1

                    if click_count == 1:
                        print(f"First point captured: ({x}, {y})")
                        print("Now move to bottom-right point and click...")
                    elif click_count == 2:
                        print(f"Second point captured: ({x}, {y})")

                    # Small delay to debounce
                    time.sleep(0.3)

                last_mouse_state = current_mouse_state
                time.sleep(0.01)  # Small polling delay

            if keyboard.is_pressed('esc'):
                raise KeyboardInterrupt("User cancelled with ESC")

            # Validate the points
            if len(points) == 2:
                x1, y1 = points[0]
                x2, y2 = points[1]

                # Ensure first point is top-left, second is bottom-right
                min_x, max_x = min(x1, x2), max(x1, x2)
                min_y, max_y = min(y1, y2), max(y1, y2)

                self._redraw_region = (min_x, min_y, max_x, max_y)
                self._redraw_region_label['text'] = f"Region: ({min_x}, {min_y}) to ({max_x}, {max_y})"
                self.tlabel['text'] = "Redraw region selected. Click 'Draw Region' to start drawing."
                self._redraw_picking = False

                # Restore the UI
                self._root.deiconify()
                self._root.wm_state('normal')

                print(f"Region selected: ({min_x}, {min_y}) to ({max_x}, {max_y})")
                messagebox.showinfo(self.title, f"Region selected!\n\nTop-left: ({min_x}, {min_y})\nBottom-right: ({max_x}, {max_y})\n\nYou can now click 'Draw Region' to redraw this area.")

        except KeyboardInterrupt:
            print("Mouse capture cancelled by user")
            self._cancel_redraw_pick()
            # Restore the UI
            self._root.deiconify()
            self._root.wm_state('normal')
        except Exception as e:
            print(f"Error during mouse capture: {e}")
            self._cancel_redraw_pick()
            # Restore the UI
            self._root.deiconify()
            self._root.wm_state('normal')

    def start(self):
        try:
            t = time.time()

            # Check for cached computation first
            has_cache, cache_file = self.bot.get_cached_status(self._imname, flags=self.draw_options, mode=self._mode)
            if has_cache:
                # Load from cache
                print(f"Loading from cache: {cache_file}")
                cache_data = self.bot.load_cached(cache_file)
                if cache_data:
                    cmap = cache_data['cmap']
                    # Log cache details
                    num_colors = len(cmap)
                    total_points = sum(len(lines) for lines in cmap.values())
                    cache_time = time.ctime(cache_data['timestamp'])
                    print(f"Cache loaded - {num_colors} colors, {total_points} coordinate points")
                    print(f"Cached on: {cache_time}")
                    print(f"Settings: Delay={cache_data['settings'][0]}, PixelSize={cache_data['settings'][1]}")
                    self.tlabel['text'] = f"Using cached computation"
                else:
                    # Cache invalid, fall back to processing
                    print("Cache file invalid, processing live...")
                    cmap = self.bot.process(self._imname, flags=self.draw_options, mode=self._mode)
            else:
                # No cache, process normally
                print("No cache available, processing live...")
                cmap = self.bot.process(self._imname, flags=self.draw_options, mode=self._mode)

            # Show drawing time estimate
            drawing_eta = self.bot.estimate_drawing_time(cmap)
            print(f"Estimated drawing time: {drawing_eta}")
            self.tlabel['text'] = f"Starting draw - ETA: {drawing_eta}"

            messagebox.showwarning(self.title, f'Press ESC to stop the bot. Press {self.bot.pause_key} to pause/resume.')
            self._root.iconify()
            # Clear any previous termination/paused state before starting
            self.bot.terminate = False
            self.bot.paused = False
            self.bot.drawing = False
            self.bot.draw_state = {
                'color_idx': 0,
                'line_idx': 0,
                'segment_idx': 0,
                'current_color': None,
                'was_paused': False
            }

            result = self.bot.draw(cmap)
            self._root.deiconify()  # type: ignore
            self._root.wm_state('normal')  # type: ignore
            if result == 'success':
                self.tlabel['text'] = f"Success. Time elapsed: {time.time() - t:.2f}s"
            elif result == 'terminated':
                self.tlabel['text'] = f"Terminated by user. Time elapsed: {time.time() - t:.2f}s"
                # Reset bot state for fresh start after termination
                self.bot.draw_state = {
                    'color_idx': 0,
                    'line_idx': 0,
                    'segment_idx': 0,
                    'current_color': None,
                    'was_paused': False
                }
                # Clear termination flag so user can start again
                self.bot.terminate = False
            elif result == 'paused':
                self.tlabel['text'] = f"Paused. Press {self.bot.pause_key} again to resume. Time elapsed: {time.time() - t:.2f}s"
            else:
                self.tlabel['text'] = f"Unknown result: {result}"
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror(self.title, str(e))

        # Let the thread manager know that the task has ended
        self._set_busy(False)
