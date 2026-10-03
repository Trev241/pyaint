import json
import os
import time
import tkinter
import traceback
import urllib.request
import urllib.error as urllib_error
import utils

from pyaint_profile import Profile, ENV_CONFIG_KEYS
from pyaint_targets import (
    apply_profile_defaults,
    get_recipe,
    list_recipes,
    load_user_recipes,
    merge_drawing_options,
    merge_drawing_settings,
)
from pyaint_locators import detect_target
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
    Entry,
    Progressbar
)


def is_free(func):
    """
    Decorator that only executes a function when the bot is not busy by checking that
    `self.busy` flag. Keeps decorator at module scope to avoid descriptor/type issues.
    """

    def decorator(self):
        if self.busy:
            self.tlabel['text'] = "Cannot perform action. Currently busy..."
        else:
            self.busy = True
            func(self)

    return decorator

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
        # Center the window on screen
        screen_width = self._root.winfo_screenwidth()
        screen_height = self._root.winfo_screenheight()
        x = (screen_width - w) // 2
        y = (screen_height - h) // 2
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

        # The taught environment. This is the single source of truth and is
        # shared with the bot (see pyaint_profile.py).
        self.profile = Profile()
        self.bot.profile = self.profile

        # Non-environment preferences (drawing knobs, options, pause key).
        # Initialize early so _init_ipanel can access it.
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
        # UI initialization finished - allow saving
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
        for i in range(20):
            self._cframe.rowconfigure(i, weight=1)

        curr_row = 0

        # Target application (recipe). Selecting one applies its defaults and
        # limits which tools Setup asks for.
        Label(self._cframe, text='Target App', font=Window.TITLE_FONT).grid(
            column=0, row=curr_row, columnspan=2, sticky='w', padx=5, pady=5)
        # Load any user/community recipes from targets/ and ~/.pyaint/targets
        # before building the list (they may override built-ins).
        load_user_recipes()
        self._recipes = list_recipes()
        self._recipes_by_name = {r.name: r for r in self._recipes}
        self._target_var = StringVar()
        initial_recipe = get_recipe(self.profile.target)
        self._target_var.set(initial_recipe.name)
        self._target_menu = OptionMenu(
            self._cframe, self._target_var, initial_recipe.name,
            *[r.name for r in self._recipes], command=self._on_target_change)
        self._target_menu.grid(column=0, row=curr_row + 1, columnspan=2, sticky='ew', padx=5, pady=5)
        curr_row += 2

        # Options
        btn_names = [
            'Setup',
            'Auto-detect',
            # 'Inspect',
            'Pre-compute',
            'Test Draw',
            'Simple Test Draw',
            'Run Calibration',
            'Start'
        ]

        buttons = []
        for i in range(len(btn_names)):
            b = Button(self._cframe, text=btn_names[i])
            b.grid(column=0, row=curr_row + i, columnspan=2, padx=5, pady=5, sticky='ew')
            buttons.append(b)
        buttons[0]['command'] = self.setup
        buttons[1]['command'] = self.auto_detect
        # buttons[2]['command'] = self.test
        buttons[2]['command'] = self.start_precompute_thread
        buttons[3]['command'] = self.start_test_draw_thread
        buttons[4]['command'] = self.start_simple_test_draw_thread
        buttons[5]['command'] = self.start_calibration_thread
        buttons[6]['command'] = self.start_draw_thread
        curr_row += len(btn_names)

        self._teclbl = Label(self._cframe, text='Draw Mode', font=Window.TITLE_FONT)
        self._teclbl.grid(column=0, row=curr_row, columnspan=2, sticky='w', padx=5, pady=5)
        curr_row += 1
        modes = [Bot.SLOTTED, Bot.LAYERED]
        self._tecvar = StringVar()
        self._tecvar.set(modes[1])
        self._mode = modes[1]
        self._teclst = OptionMenu(self._cframe, self._tecvar, self._mode, *modes, command=self._update_mode)
        self._teclst.grid(column=0, row=curr_row, columnspan=2, sticky='ew', padx=5, pady=5)
        curr_row += 1

        # For every slider option in options, option layout is    :    (name, default, from, to)
        defaults = self.bot.settings
        self._options = (
            # ('Confidence', defaults[0], 0, 1),
            ('Delay', defaults[0], 0, 1),
            ('Pixel Size', defaults[1], 1, 50),
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
        
        # Create sliders for all options except Delay (index 0)
        self._optslid = []
        for i in range(size):
            if i == 0:  # Skip Delay - will use Entry field instead
                self._optslid.append(None)
            else:
                self._optslid.append(Scale(
                    self._cframe,
                    from_=self._options[i][2],
                    to=self._options[i][3],
                    variable=self._optvars[i],
                    command=lambda val, index=i : self._on_slider_move(index, val)
                ))
        
        # Delay Entry field (replaces slider for index 0)
        self._delay_var = StringVar()
        self._delay_entry = Entry(self._cframe, textvariable=self._delay_var, width=10)
        self._delay_entry.bind('<Return>', self._on_delay_entry_change)
        self._delay_entry.bind('<FocusOut>', self._on_delay_entry_change)
        
        # Grid all widgets
        for i in range(size):
            self._optlabl[i].grid(column=0, row=(i * 2) + curr_row, columnspan=2, padx=5, pady=5, sticky='w')
            if i == 0:  # Delay - use Entry field
                self._delay_entry.grid(column=0, row=(i * 2) + curr_row + 1, columnspan=2, padx=5, pady=5, sticky='ew')
            else:  # Other options - use sliders
                self._optslid[i].set(self._options[i][1])
                self._optslid[i].set(defaults[i])
                self._optslid[i].grid(column=0, row=(i * 2) + curr_row + 1, columnspan=2, padx=5, sticky='ew')
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

        # Color Button option
        Label(self._cframe, text='Color Button', font=Window.TITLE_FONT).grid(column=0, row=curr_row, padx=5, pady=5, sticky='w')
        self._colorbutton_var = IntVar()
        self._colorbutton_cb = Checkbutton(self._cframe, text='Enable Color Button', variable=self._colorbutton_var,
            command=self._on_colorbutton_toggle)
        self._colorbutton_cb.grid(column=1, row=curr_row, padx=5, pady=5, sticky='w')
        curr_row += 1

        # Skip first color option
        Label(self._cframe, text='Skip First Color', font=Window.TITLE_FONT).grid(column=0, row=curr_row, padx=5, pady=5, sticky='w')
        self._skip_first_color_var = IntVar()
        self._skip_first_color_cb = Checkbutton(self._cframe, text='Skip first color', variable=self._skip_first_color_var,
            command=self._on_skip_first_color_toggle)
        self._skip_first_color_cb.grid(column=1, row=curr_row, padx=5, pady=5, sticky='w')
        curr_row += 1

        # MSPaint Mode option
        Label(self._cframe, text='MSPaint Mode', font=Window.TITLE_FONT).grid(column=0, row=curr_row, padx=5, pady=5, sticky='w')
        self._mspaint_mode_var = IntVar()
        self._mspaint_mode_cb = Checkbutton(self._cframe, text='Enable double-click', variable=self._mspaint_mode_var,
            command=self._on_mspaint_mode_toggle)
        self._mspaint_mode_cb.grid(column=1, row=curr_row, padx=5, pady=5, sticky='w')
        curr_row += 1

        # MSPaint Mode delay setting
        Label(self._cframe, text='MSPaint Delay (s)', font=Window.TITLE_FONT).grid(column=0, row=curr_row, padx=5, pady=5, sticky='w')
        self._mspaint_delay_var = StringVar()
        self._mspaint_delay_entry = Entry(self._cframe, textvariable=self._mspaint_delay_var, width=5)
        self._mspaint_delay_entry.bind('<FocusOut>', self._on_mspaint_delay_change)
        self._mspaint_delay_entry.bind('<Return>', self._on_mspaint_delay_change)
        self._mspaint_delay_entry.grid(column=1, row=curr_row, padx=5, pady=5, sticky='ew')
        curr_row += 1

        # Pause Key Setting
        Label(self._cframe, text='Pause Key', font=Window.TITLE_FONT).grid(column=0, row=curr_row, padx=5, pady=5, sticky='w')
        self._pause_key_entry = Entry(self._cframe)
        self._pause_key_entry.grid(column=1, row=curr_row, padx=5, pady=5, sticky='ew')
        self._pause_key_entry.bind('<Key>', self._on_pause_key_entry_press)
        curr_row += 1

        # Calibration Step Size Setting
        Label(self._cframe, text='Calib. Step', font=Window.TITLE_FONT).grid(column=0, row=curr_row, padx=5, pady=5, sticky='w')
        self._calib_step_var = StringVar()
        self._calib_step_var.set('2')
        self._calib_step_entry = Entry(self._cframe, textvariable=self._calib_step_var, width=5)
        self._calib_step_entry.grid(column=1, row=curr_row, padx=5, pady=5, sticky='ew')
        self._calib_step_entry.bind('<FocusOut>', self._on_calib_step_change)
        self._calib_step_entry.bind('<Return>', self._on_calib_step_change)
        curr_row += 1

        # Jump Threshold Setting
        Label(self._cframe, text='Jump Thresh (px)', font=Window.TITLE_FONT).grid(column=0, row=curr_row, padx=5, pady=5, sticky='w')
        self._jump_threshold_var = StringVar()
        self._jump_threshold_var.set('5')
        self._jump_threshold_entry = Entry(self._cframe, textvariable=self._jump_threshold_var, width=5)
        self._jump_threshold_entry.grid(column=1, row=curr_row, padx=5, pady=5, sticky='ew')
        self._jump_threshold_entry.bind('<FocusOut>', self._on_jump_threshold_change)
        self._jump_threshold_entry.bind('<Return>', self._on_jump_threshold_change)
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

        # Delete Files section
        Label(self._cframe, text='File Management', font=Window.TITLE_FONT).grid(column=0, row=curr_row, columnspan=2, padx=5, pady=5, sticky='w')
        curr_row += 1

        self._delete_calib_btn = Button(self._cframe, text='Remove Calibration', command=self._on_delete_calibration)
        self._delete_calib_btn.grid(column=0, row=curr_row, padx=5, pady=5, sticky='ew')
        self._reset_config_btn = Button(self._cframe, text='Reset Config', command=self._on_reset_config)
        self._reset_config_btn.grid(column=1, row=curr_row, padx=5, pady=5, sticky='ew')
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

    def _on_target_change(self, value):
        """Handle the user picking a target from the dropdown."""
        recipe = self._recipes_by_name.get(value)
        if recipe is None:
            return
        self._select_target(recipe)

    def _select_target(self, recipe):
        """Apply a target recipe and persist the choice."""
        self.profile.target = recipe.id
        self._apply_recipe(recipe)
        self._store_drawing_settings()
        self._store_drawing_options()
        self.tlabel['text'] = f"Target set to {recipe.name}. Use Setup to teach its tools."
        self._save_config()

    def _apply_recipe(self, recipe):
        """Apply a recipe's defaults to the live profile/bot and refresh widgets."""
        apply_profile_defaults(self.profile, recipe)

        settings = recipe.drawing_settings or {}
        self.bot.settings[:] = merge_drawing_settings(self.bot.settings, settings)
        if 'jump_threshold' in settings:
            self.bot.jump_threshold = settings['jump_threshold']

        self.draw_options = merge_drawing_options(
            self.draw_options,
            recipe.drawing_options or {},
            Bot.IGNORE_WHITE,
            Bot.USE_CUSTOM_COLORS,
        )
        self.bot.skip_first_color = bool(recipe.skip_first_color)

        self._refresh_drawing_widgets()
        self._refresh_option_widgets()
        self._sync_env_ui()

    def _refresh_drawing_widgets(self):
        """Mirror ``self.bot.settings`` into the delay entry and sliders."""
        for i, val in enumerate(self.bot.settings):
            if i == 0:  # Delay - entry field
                self._delay_var.set(str(val))
                self._optlabl[0]['text'] = f"{self._options[0][0]}: {val:.2f}"
            elif i == 1:  # Pixel Size - integer slider
                val = int(val)
                self._optvars[i].set(val)
                self._optlabl[i]['text'] = f"{self._options[i][0]}: {val}"
            else:  # Other sliders
                self._optvars[i].set(val)
                self._optlabl[i]['text'] = f"{self._options[i][0]}: {val:.2f}"

    def _refresh_option_widgets(self):
        """Mirror the ``draw_options`` bit flags into the checkbuttons."""
        self._checkbutton_vars[0].set(1 if self.draw_options & Bot.IGNORE_WHITE else 0)
        self._checkbutton_vars[1].set(1 if self.draw_options & Bot.USE_CUSTOM_COLORS else 0)

    @is_free
    def auto_detect(self):
        """Capture the screen after a short countdown and locate the target."""
        recipe = get_recipe(self.profile.target)
        if not recipe.detection:
            messagebox.showinfo(
                self.title,
                f'No auto-detection is configured for "{recipe.name}". '
                'Please use Setup to teach its tools manually.')
            self._set_busy(False)
            return

        # Get pyaint out of the way and give the user a moment to bring the
        # target application to the front before capturing.
        messagebox.showinfo(
            self.title,
            'Auto-detect will capture the screen in 3 seconds.\n\n'
            'Bring the target application to the front now.')
        self._pending_recipe = recipe
        self._root.iconify()
        self._root.after(3000, self._finish_auto_detect)

    def _finish_auto_detect(self):
        try:
            recipe = self._pending_recipe
            image = self.bot.capture_screen()
            detection = detect_target(recipe, image)
            print(f"[AutoDetect] {recipe.id}: screen={image.size} canvas={detection.canvas} "
                  f"palette={detection.palette} rows={detection.palette_rows} cols={detection.palette_cols}")
            self._root.deiconify()
            self._root.wm_state('normal')
            if not detection:
                messagebox.showwarning(
                    self.title,
                    f'Could not auto-detect "{recipe.name}". '
                    'Please use Setup to teach its tools manually.')
                self.tlabel['text'] = 'Auto-detect found nothing - use Setup.'
                return

            self._show_detection_preview(image, detection)
            if messagebox.askyesno(
                self.title,
                f'Detected: {detection.summary()}\n\nApply these regions?'):
                applied = self.bot.apply_detection(detection)
                self._sync_env_ui()
                self._store_drawing_settings()
                self._store_drawing_options()
                self._save_config()
                self.tlabel['text'] = f'Auto-detect applied ({", ".join(applied)}).'
            else:
                self.tlabel['text'] = 'Auto-detect cancelled - use Setup to teach tools manually.'
        except Exception as e:
            traceback.print_exc()
            try:
                self._root.deiconify()
                self._root.wm_state('normal')
            except Exception:
                pass
            messagebox.showerror(self.title, f'Auto-detect failed: {e}')
        finally:
            self._set_busy(False)

    def _show_detection_preview(self, image, detection):
        """Draw detected regions onto a copy of the screenshot and preview it."""
        try:
            from PIL import ImageDraw
            annotated = image.convert('RGB').copy()
            draw = ImageDraw.Draw(annotated)
            if detection.canvas:
                x, y, w, h = detection.canvas
                draw.rectangle([x, y, x + w, y + h], outline='red', width=3)
            if detection.palette:
                x, y, w, h = detection.palette
                draw.rectangle([x, y, x + w, y + h], outline='lime', width=3)
            self._set_img(image=annotated)
        except Exception as e:
            print(f'[AutoDetect] Could not render preview: {e}')

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
                self._save_config()

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

        self._store_drawing_options()
        self._save_config()

    def _on_newlayer_toggle(self):
        # bot.new_layer is the same dict as profile['New Layer']
        self.profile['New Layer']['enabled'] = bool(self._newlayer_var.get())
        self._save_config()

    def _on_colorbutton_toggle(self):
        self.profile['Color Button']['enabled'] = bool(self._colorbutton_var.get())
        self._save_config()

    def _on_skip_first_color_toggle(self):
        enabled = bool(self._skip_first_color_var.get())
        # Update bot state and tools dict
        self.bot.skip_first_color = enabled
        self.tools['skip_first_color'] = enabled
        self._save_config()

    def _on_mspaint_mode_toggle(self):
        self.profile.mspaint_mode['enabled'] = bool(self._mspaint_mode_var.get())
        self._save_config()

    def _on_mspaint_delay_change(self, event=None):
        """Handle changes to MSPaint Mode delay entry field with validation"""
        try:
            val_str = self._mspaint_delay_var.get().strip()
            if not val_str:
                return  # Empty input, don't update
            
            val = float(val_str)
            
            # Validate range: 0.01 to 5.0
            if val < 0.01:
                val = 0.01
                self._mspaint_delay_var.set(str(val))
            elif val > 5.0:
                val = 5.0
                self._mspaint_delay_var.set(str(val))
            
            # Update bot state (shared with the profile)
            self.profile.mspaint_mode['delay'] = round(val, 3)
            self._save_config()
            
            self.tlabel['text'] = 'MSPaint Mode delay updated. This is the wait time between double-clicks on the palette.'
            
        except ValueError:
            # Invalid input, revert to current bot setting
            self._mspaint_delay_var.set(str(self.bot.mspaint_mode.get('delay', 0.5)))
            self.tlabel['text'] = 'Invalid delay value. Please enter a number between 0.01 and 5.0'

    def _on_delay_entry_change(self, event=None):
        """Handle changes to the delay entry field with validation"""
        try:
            val_str = self._delay_var.get().strip()
            if not val_str:
                return  # Empty input, don't update
            
            val = float(val_str)
            
            # Validate range: 0.01 to 10.0
            if val < 0.01:
                val = 0.01
                self._delay_var.set(str(val))
            elif val > 10.0:
                val = 10.0
                self._delay_var.set(str(val))
            
            # Update bot settings
            self.bot.settings[0] = round(val, 3)
            self._optlabl[0]['text'] = f"{self._options[0][0]}: {val:.2f}"
            
            self._store_drawing_settings()
            self._save_config()

            self.tlabel['text'] = Window._SLIDER_TOOLTIPS[0]
            
        except ValueError:
            # Invalid input, revert to current bot setting
            self._delay_var.set(str(self.bot.settings[0]))
            self.tlabel['text'] = 'Invalid delay value. Please enter a number between 0.01 and 10.0'

    def _on_slider_move(self, index, val):
        # Skip delay (index 0) since it uses an entry field now
        if index == 0:
            return
            
        val = float(val)
        if index == 1:  # Pixel Size - force to integer
            val = int(round(val))
            self.bot.settings[index] = val
            self._optlabl[index]['text'] = f"{self._options[index][0]}: {val}"
        else:
            self.bot.settings[index] = round(val, 3)
            self._optlabl[index]['text'] = f"{self._options[index][0]}: {val:.2f}"

        self._store_drawing_settings()
        self._save_config()

        self.tlabel['text'] = Window._SLIDER_TOOLTIPS[index]

    def _on_jump_threshold_change(self, event=None):
        """Handle jump threshold change"""
        try:
            val_str = self._jump_threshold_var.get().strip()
            if not val_str:
                return  # Empty input, don't update
            
            val = int(val_str)
            
            # Validate range: 1 to 100 pixels
            if val < 1:
                val = 1
                self._jump_threshold_var.set(str(val))
            elif val > 100:
                val = 100
                self._jump_threshold_var.set(str(val))
            
            # Update bot state
            self.bot.jump_threshold = val
            
            self.tools.setdefault('drawing_settings', {})['jump_threshold'] = val
            self._save_config()

            self.tlabel['text'] = f'Jump threshold updated to {val} pixels. Cursor jumps larger than this will trigger delay.'
            
        except ValueError:
            # Invalid input, revert to current bot setting
            self._jump_threshold_var.set(str(self.bot.jump_threshold))
            self.tlabel['text'] = 'Invalid jump threshold. Please enter a number between 1 and 100.'

    def _on_calib_step_change(self, event=None):
        """Handle calibration step size change"""
        try:
            val_str = self._calib_step_var.get().strip()
            if not val_str:
                return  # Empty input, don't update
            
            val = int(val_str)
            
            # Validate range: 1 to 10
            if val < 1:
                val = 1
                self._calib_step_var.set(str(val))
            elif val > 10:
                val = 10
                self._calib_step_var.set(str(val))
            
            self.tools.setdefault('calibration_settings', {})['step_size'] = val
            self._save_config()

            self.tlabel['text'] = 'Calibration step size updated. Lower values = more accurate but slower.'
            
        except ValueError:
            # Invalid input, revert to default
            self._calib_step_var.set('2')
            self.tlabel['text'] = 'Invalid step size. Please enter a number between 1 and 10.'

    def _on_pause_key_entry_press(self, event):
        # Only allow setting pause key when not drawing
        if not self.busy:
            # When not drawing, allow setting pause key by typing in the entry field
            key_name = event.keysym.lower()
            # Handle special cases
            if key_name.startswith('f') and key_name[1:].isdigit():
                key_name = key_name  # f1, f2, etc.
            elif len(key_name) > 1:
                # For special keys, keep as-is
                pass
            else:
                # For regular keys, use char
                key_name = event.char.lower() if event.char else key_name

            # Update the entry field and bot's pause key
            self._pause_key_entry.delete(0, END)
            self._pause_key_entry.insert(0, key_name)
            self.bot.pause_key = key_name

            # Save pause key to config file
            self.tools['pause_key'] = key_name
            self._save_config()

            return "break"

        # This should never be reached when not busy, but just in case
        print(f"Unexpected pause key press while busy={self.busy}")
        return "break"

    def _save_config(self):
        """Persist preferences and the environment profile to config.json."""
        if getattr(self, '_initializing', False):
            return
        payload = dict(self.tools)
        payload.update(self.profile.to_config())
        try:
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=4)
            print(f"Saved config to {self._config_path}; keys={list(payload.keys())}")
        except Exception as e:
            print(f"Failed to save config: {e}")

    def _store_drawing_settings(self):
        """Copy the live drawing settings into the preferences dict."""
        settings = self.tools.setdefault('drawing_settings', {})
        settings['delay'] = self.bot.settings[0]
        settings['pixel_size'] = self.bot.settings[1]
        settings['precision'] = self.bot.settings[2]
        settings['jump_delay'] = self.bot.settings[3]

    def _store_drawing_options(self):
        """Copy the live drawing option flags into the preferences dict."""
        options = self.tools.setdefault('drawing_options', {})
        options['ignore_white_pixels'] = bool(self.draw_options & Bot.IGNORE_WHITE)
        options['use_custom_colors'] = bool(self.draw_options & Bot.USE_CUSTOM_COLORS)

    def _sync_env_ui(self):
        """Reflect the environment profile into the main window's widgets."""
        self._newlayer_var.set(1 if self.profile['New Layer'].get('enabled') else 0)
        cb = self.profile['Color Button']
        self._colorbutton_var.set(1 if cb.get('enabled') else 0)
        self._colorbutton_cb.config(state='normal' if cb.get('status') else 'disabled')
        self._skip_first_color_var.set(1 if self.bot.skip_first_color else 0)
        self._mspaint_mode_var.set(1 if self.profile.mspaint_mode.get('enabled') else 0)
        self._mspaint_delay_var.set(str(self.profile.mspaint_mode.get('delay', 0.5)))

    def load_config(self):
        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"Loaded config from {self._config_path}; keys={list(config.keys())}")
        except Exception as e:
            config = {}
            print(f"Config file missing or invalid ({e}); using defaults")

        # Split persisted state into the taught environment (Profile) and user
        # preferences (self.tools). The bot shares this exact Profile instance.
        self.profile = Profile.from_config(config)
        self.bot.profile = self.profile
        self.tools = {k: v for k, v in config.items() if k not in ENV_CONFIG_KEYS}
        self.tools.setdefault('pause_key', 'p')

        # Restore the selected target without re-applying its defaults; the
        # user's saved settings take precedence on load.
        try:
            recipe = get_recipe(self.profile.target)
            self.profile.target = recipe.id
            self._target_var.set(recipe.name)
        except Exception:
            pass

        try:
            # Load pause key first
            self.bot.pause_key = self.tools.get('pause_key', 'p')
            self._pause_key_entry.delete(0, END)
            self._pause_key_entry.insert(0, self.bot.pause_key)

            # Load calibration step size setting
            if 'calibration_settings' in self.tools:
                calib_step = self.tools['calibration_settings'].get('step_size', 2)
                self._calib_step_var.set(str(calib_step))
            else:
                self._calib_step_var.set('2')

            # Load jump threshold setting
            if 'drawing_settings' in self.tools:
                jump_threshold = self.tools['drawing_settings'].get('jump_threshold', 5)
                self.bot.jump_threshold = jump_threshold
                self._jump_threshold_var.set(str(jump_threshold))
            else:
                self.bot.jump_threshold = 5
                self._jump_threshold_var.set('5')

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
                # Update UI - delay uses entry field, others use sliders
                for i, val in enumerate(self.bot.settings):
                    if i == 0:  # Delay - use entry field
                        self._delay_var.set(str(val))
                        self._optlabl[0]['text'] = f"{self._options[0][0]}: {val:.2f}"
                    elif i == 1:  # Pixel Size - force to integer
                        val = int(val)
                        self._optvars[i].set(val)
                        self._optlabl[i]['text'] = f"{self._options[i][0]}: {val}"
                    else:  # Other options - use sliders
                        self._optvars[i].set(val)
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
                if self.profile.get('Palette'):
                    palette_config = self.profile['Palette']
                    
                    # If we have valid_positions, use them to reconstruct palette
                    # This handles case where user has manually edited color positions
                    if (palette_config.get('box') and 
                        palette_config.get('rows') and 
                        palette_config.get('cols') and 
                        palette_config.get('valid_positions')):
                        
                        pbox = palette_config['box']
                        prows = palette_config['rows']
                        pcols = palette_config['cols']
                        valid_positions = palette_config['valid_positions']
                        
                        # Load manual centers if available
                        manual_centers = None
                        if palette_config.get('manual_centers'):
                            manual_centers = {int(k): tuple(v) for k, v in palette_config['manual_centers'].items()}
                        
                        # Reconstruct palette from box with valid positions and manual centers
                        pbox_adj = (pbox[0], pbox[1], pbox[2] - pbox[0], pbox[3] - pbox[1])
                        self.bot.init_palette(
                            pbox=pbox_adj,
                            prows=prows,
                            pcols=pcols,
                            valid_positions=set(valid_positions),
                            manual_centers=manual_centers
                        )
                    # Otherwise use saved color_coords if available
                    elif palette_config.get('color_coords'):
                        self.bot.init_palette(
                            # Converting string key into tuple
                            colors_pos={
                                tuple(map(int, k[1:-1].split(', '))): tuple(v)
                                for k, v in palette_config['color_coords'].items()
                            }
                        )
                
                if self.profile['Canvas'].get('box'):
                    self.bot.init_canvas(self.profile['Canvas']['box'])
                if self.profile['Custom Colors'].get('box'):
                    self.bot.init_custom_colors(self.profile['Custom Colors']['box'])

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
            nl = self.profile.get('New Layer')
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

        # Apply Color Button settings to bot if present
        try:
            cb = self.profile.get('Color Button')
            if cb:
                # coords may be stored as list
                coords = cb.get('coords')
                if isinstance(coords, list) and len(coords) >= 2:
                    self.bot.color_button['coords'] = (int(coords[0]), int(coords[1]))
                elif isinstance(coords, tuple):
                    self.bot.color_button['coords'] = coords
                self.bot.color_button['enabled'] = bool(cb.get('enabled', False))
                self.bot.color_button['delay'] = float(cb.get('delay', 0.1))
                mods = cb.get('modifiers', {})
                self.bot.color_button['modifiers']['ctrl'] = bool(mods.get('ctrl', False))
                self.bot.color_button['modifiers']['alt'] = bool(mods.get('alt', False))
                self.bot.color_button['modifiers']['shift'] = bool(mods.get('shift', False))
                # Update main UI checkbox to reflect new state
                try:
                    self._colorbutton_var.set(1 if self.bot.color_button['enabled'] else 0)
                    # Enable checkbox only if Color Button is configured (status: true)
                    self._colorbutton_cb.config(state='normal' if cb.get('status', False) else 'disabled')
                except Exception:
                    pass
        except Exception:
            pass

        # Apply Skip First Color setting to bot if present
        try:
            self.bot.skip_first_color = bool(self.tools.get('skip_first_color', 0))
            self._skip_first_color_var.set(1 if self.bot.skip_first_color else 0)
        except Exception:
            pass

        # Apply MSPaint Mode settings to bot if present
        try:
            mm = self.profile.mspaint_mode
            if mm:
                self.bot.mspaint_mode['enabled'] = bool(mm.get('enabled', False))
                self.bot.mspaint_mode['delay'] = float(mm.get('delay', 0.5))
                self._mspaint_mode_var.set(1 if self.bot.mspaint_mode['enabled'] else 0)
                self._mspaint_delay_var.set(str(self.bot.mspaint_mode['delay']))
        except Exception:
            pass

        # Apply Color Button Okay settings to bot if present
        try:
            cbo = self.profile.get('Color Button Okay')
            if cbo:
                # coords may be stored as list
                coords = cbo.get('coords')
                if isinstance(coords, list) and len(coords) >= 2:
                    self.bot.color_button_okay['coords'] = (int(coords[0]), int(coords[1]))
                elif isinstance(coords, tuple):
                    self.bot.color_button_okay['coords'] = coords
                self.bot.color_button_okay['enabled'] = bool(cbo.get('enabled', False))
                mods = cbo.get('modifiers', {})
                self.bot.color_button_okay['modifiers']['ctrl'] = bool(mods.get('ctrl', False))
                self.bot.color_button_okay['modifiers']['alt'] = bool(mods.get('alt', False))
                self.bot.color_button_okay['modifiers']['shift'] = bool(mods.get('shift', False))
        except Exception:
            pass

    def _set_busy(self, val):
        self.busy = val

    @is_free
    def setup(self):
        self.load_config()
        # The Profile is the single source of truth; SetupWindow mutates it in
        # place, so there is nothing to merge back afterwards. Only show the
        # tools the selected target actually needs.
        recipe = get_recipe(self.profile.target)
        self._iwindow = SetupWindow(parent=self._root, bot=self.bot, tools=self.profile, on_complete=self._on_complete_setup, title='Setup', required_tools=recipe.tools)

    def _on_complete_setup(self):
        # SetupWindow mutated the shared Profile in place, so the bot already
        # sees the new environment. Refresh the widgets and persist.
        self.bot.profile = self.profile
        self._sync_env_ui()

        self.tools['pause_key'] = self._pause_key_entry.get().strip() or 'p'
        self.bot.pause_key = self.tools['pause_key']

        # Normalise tuple boxes for JSON serialization.
        for tool_name in ('Canvas', 'Custom Colors'):
            box = self.profile[tool_name].get('box')
            if isinstance(box, tuple):
                self.profile[tool_name]['box'] = list(box)

        self._store_drawing_settings()
        self._store_drawing_options()
        if getattr(self, '_last_url', None):
            self.tools['last_image_url'] = self._last_url

        self._save_config()
        self.tlabel['text'] = 'Setup saved.'
        self._set_busy(False)

    @is_free
    def start_precompute_thread(self):
        # Use a distinct attribute name for the Thread object to avoid
        # colliding with the method name (static type checkers complain).
        self._precompute_thread_obj = Thread(target=self.precompute)
        self._precompute_thread_obj.start()
        self._manage_precompute_thread()

    def _manage_precompute_thread(self):
        if getattr(self, '_precompute_thread_obj', None) is not None and self._precompute_thread_obj.is_alive() and self.busy:
            self._root.after(500, self._manage_precompute_thread)
            self.tlabel['text'] = f"Pre-computing: {self.bot.progress:.2f}%"
        elif self.busy:
            # Pre-compute finished
            self.tlabel['text'] = 'Pre-compute completed! Cache saved.'
            self._set_busy(False)

    def precompute(self):
        try:
            cache_file = self.bot.precompute(self._imname, flags=self.draw_options, mode=self._mode)

            # Load cached data to estimate drawing time
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
    def start_test_draw_thread(self):
        self._test_draw_thread_obj = Thread(target=self.test_draw)
        self._test_draw_thread_obj.start()
        self._manage_test_draw_thread()

    def _manage_test_draw_thread(self):
        # Display progress updates every half a second
        if getattr(self, '_test_draw_thread_obj', None) is not None and self._test_draw_thread_obj.is_alive() and self.busy:
            self._root.after(500, self._manage_test_draw_thread)
            self.tlabel['text'] = f"Test drawing: {self.bot.progress:.2f}%"
        elif self.busy:
            # Test draw finished
            self.tlabel['text'] = 'Test draw completed!'
            self._set_busy(False)

    @is_free
    def start_simple_test_draw_thread(self):
        """Start simple test draw in a separate thread"""
        if not hasattr(self.bot, '_canvas') or self.bot._canvas is None:
            messagebox.showerror(self.title, "Canvas not configured. Please run Setup first.")
            self._set_busy(False)
            return

        self._simple_test_thread_obj = Thread(target=self.simple_test_draw)
        self._simple_test_thread_obj.start()
        self._manage_simple_test_draw_thread()

    def _manage_simple_test_draw_thread(self):
        """Manage simple test draw thread"""
        if getattr(self, '_simple_test_thread_obj', None) is not None and self._simple_test_thread_obj.is_alive() and self.busy:
            self._root.after(500, self._manage_simple_test_draw_thread)
            self.tlabel['text'] = "Simple test drawing in progress..."
        elif self.busy:
            # Simple test draw finished
            self.tlabel['text'] = 'Simple test draw completed!'
            self._set_busy(False)

    @is_free
    def start_calibration_thread(self):
        """Start color calibration process in a separate thread"""
        # Check if required tools are configured
        custom_colors_data = self.profile['Custom Colors'].get('box')
        if not custom_colors_data or (isinstance(custom_colors_data, list) and len(custom_colors_data) == 0):
            messagebox.showerror(self.title, "Custom Colors tool not configured. Please run Setup first.")
            self._set_busy(False)
            return
        
        preview_spot_coords = self.profile['color_preview_spot'].get('coords')
        if not preview_spot_coords:
            messagebox.showerror(self.title, "Color Preview Spot tool not configured. Please run Setup first.")
            self._set_busy(False)
            return
        
        # Get step size from entry field
        try:
            step = int(self._calib_step_var.get())
        except ValueError:
            step = 2  # Default to 2 if invalid
        
        # Store step size in tools config
        if 'calibration_settings' not in self.tools:
            self.tools['calibration_settings'] = {}
        self.tools['calibration_settings']['step_size'] = step
        
        # Create calibration progress overlay window
        self._create_calibration_overlay()
        
        # Minimize window then start calibration
        messagebox.showinfo(self.title, f'Press ESC to stop calibration.')
        self._root.iconify()
        time.sleep(1)  # Small delay before starting to allow window to minimize
        
        # Track calibration start time for ETA calculation
        self._calibration_start_time = time.time()
        
        # Create and start calibration thread
        self._calibration_thread_obj = Thread(target=self._calibration_thread)
        self._calibration_thread_obj.start()
        self._manage_calibration_thread()

    def _create_calibration_overlay(self):
        """
        Create and show an always-on-top progress overlay window for color calibration.
        The window displays current calibration progress and appears above the custom color box location.
        """
        try:
            # Get custom color box location for positioning
            custom_colors_box = self.profile['Custom Colors'].get('box')
            if not custom_colors_box:
                # Fallback to top center of screen if box location not available
                screen_width = self._root.winfo_screenwidth()
                x_position = (screen_width - 240) // 2
                y_position = 10
            else:
                # Position above the custom color box
                if isinstance(custom_colors_box, list):
                    box_x = custom_colors_box[0]
                    box_y = custom_colors_box[1]
                else:
                    box_x = custom_colors_box.get('x', 0)
                    box_y = custom_colors_box.get('y', 0)
                
            # Position overlay above the box (with some offset)
            window_width = 400
            window_height = 20
            # Align right edge of overlay with right edge of custom colors box
            box_right = custom_colors_box[2] if isinstance(custom_colors_box, list) else box_x + (custom_colors_box.get('width', 0) if isinstance(custom_colors_box, dict) else 0)
            x_position = box_right - window_width
            y_position = box_y - 30  # 30 pixels above the box
            
            # Create the overlay window
            self._calib_overlay_window = tkinter.Toplevel(self._root)
            self._calib_overlay_window.title("Calibration Progress")

            # Set window to always on top and remove decorations
            self._calib_overlay_window.attributes("-topmost", True)
            self._calib_overlay_window.overrideredirect(True)

            # Set window size and position
            window_width = 400
            window_height = 20
            self._calib_overlay_window.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")

            # Create a dark background frame with border
            border_frame = tkinter.Frame(
                self._calib_overlay_window,
                bg="#4a4a4a",
                width=window_width,
                height=window_height
            )
            border_frame.pack(fill=tkinter.BOTH, expand=True)

            # Inner frame for content
            overlay_frame = tkinter.Frame(
                border_frame,
                bg="#2c2c2c",
                width=window_width - 2,
                height=window_height - 2
            )
            overlay_frame.place(x=1, y=1, width=window_width - 2, height=window_height - 2)

            # Create centered label for progress text
            self._calib_overlay_label = tkinter.Label(
                overlay_frame,
                text="Initializing...",
                bg="#2c2c2c",
                fg="#00ff00",  # Green text for progress
                font=("Arial", 9, "bold"),
                relief=tkinter.FLAT
            )
            self._calib_overlay_label.place(relx=0.5, rely=0.5, anchor=tkinter.CENTER)

            # Keep window responsive
            self._calib_overlay_window.update()

            print("[CalibrationOverlay] Overlay window created")
            return self._calib_overlay_window

        except Exception as e:
            print(f"[CalibrationOverlay] Error creating overlay: {e}")
            return None

    def _close_calibration_overlay(self):
        """Close the calibration progress overlay window"""
        try:
            if hasattr(self, '_calib_overlay_window') and self._calib_overlay_window is not None:
                self._calib_overlay_window.destroy()
                self._calib_overlay_window = None
                self._calib_overlay_label = None
                print("[CalibrationOverlay] Overlay window closed")
        except Exception as e:
            print(f"[CalibrationOverlay] Error closing overlay: {e}")

    def _manage_calibration_thread(self):
        """Manage calibration thread and update progress"""
        if getattr(self, '_calibration_thread_obj', None) is not None and self._calibration_thread_obj.is_alive() and self.busy:
            # Check if calibration was cancelled
            if self.bot.terminate:
                self.tlabel['text'] = 'Calibration cancelled by user (ESC pressed)'
                self._close_calibration_overlay()
                self._set_busy(False)
                return
            
            self._root.after(500, self._manage_calibration_thread)
            # Update progress based on calibration state
            if hasattr(self.bot, '_calibration_progress'):
                total = self.bot._calibration_progress.get('total', 0)
                current = self.bot._calibration_progress.get('current', 0)
                if total > 0:
                    percent = (current / total) * 100
                    # Calculate ETA based on elapsed time
                    elapsed_time = time.time() - self._calibration_start_time
                    if current > 0 and percent < 100:
                        avg_time_per_color = elapsed_time / current
                        colors_remaining = total - current
                        eta_seconds = colors_remaining * avg_time_per_color
                        eta_str = self.bot._format_time(eta_seconds)
                    else:
                        eta_str = "calculating..."
                    # Update overlay label
                    if hasattr(self, '_calib_overlay_label') and self._calib_overlay_label is not None:
                        self._calib_overlay_label['text'] = f"Calibrating: {current}/{total} ({percent:.1f}%) - ETA: {eta_str}"
                        if hasattr(self, '_calib_overlay_window') and self._calib_overlay_window is not None:
                            try:
                                self._calib_overlay_window.update()  # Force UI update
                            except Exception as e:
                                print(f"[CalibrationOverlay] Error updating window: {e}")
                    self.tlabel['text'] = f"Calibrating: {current}/{total} colors ({percent:.1f}%) - ETA: {eta_str}"
                else:
                    elapsed_time = time.time() - self._calibration_start_time
                    if hasattr(self, '_calib_overlay_label') and self._calib_overlay_label is not None:
                        self._calib_overlay_label['text'] = f"Calibrating: {current} colors... ({elapsed_time:.0f}s)"
                        if hasattr(self, '_calib_overlay_window') and self._calib_overlay_window is not None:
                            try:
                                self._calib_overlay_window.update()  # Force UI update
                            except Exception as e:
                                print(f"[CalibrationOverlay] Error updating window: {e}")
                    self.tlabel['text'] = f"Calibrating: {current} colors... (Time: {elapsed_time:.0f}s)"
        elif self.busy:
            # Calibration finished or cancelled
            total_time = time.time() - self._calibration_start_time
            self._close_calibration_overlay()
            if self.bot.terminate:
                self.tlabel['text'] = f'Calibration cancelled by user (ESC pressed) - Time: {total_time:.0f}s'
                # Reset terminate flag for next calibration
                self.bot.terminate = False
            else:
                num_colors = len(self.bot.color_calibration_map) if hasattr(self.bot, 'color_calibration_map') else 0
                self.tlabel['text'] = f'Calibration completed! {num_colors} colors mapped - Time: {total_time:.0f}s'
            self._set_busy(False)

    def _calibration_thread(self):
        """Execute color calibration process"""
        try:
            # Get grid_box and preview_point from tools
            grid_box = self.profile['Custom Colors'].get('box')
            preview_point = self.profile['color_preview_spot'].get('coords')
            
            if not grid_box or not preview_point:
                self.tlabel['text'] = 'Error: Missing calibration configuration data'
                self._set_busy(False)
                return
            
            # Get step size
            step = self.tools.get('calibration_settings', {}).get('step_size', 2)
            
            # Initialize progress tracking
            self.bot._calibration_progress = {'total': 0, 'current': 0}
            
            # Calculate total positions to calibrate
            if isinstance(grid_box, (list, tuple)):
                grid_width = grid_box[2] - grid_box[0]
                grid_height = grid_box[3] - grid_box[1]
            else:
                grid_width = grid_box.get('width', 0)
                grid_height = grid_box.get('height', 0)
            total_positions = ((grid_width // step) + 1) * ((grid_height // step) + 1)
            self.bot._calibration_progress['total'] = total_positions
            
            # Run calibration
            self.bot.calibrate_custom_colors(grid_box, preview_point, step=step)
            
            # Save calibration data to file
            calib_file = 'color_calibration.json'
            if self.bot.save_color_calibration(calib_file):
                self.tlabel['text'] = f'Calibration saved to {calib_file} with {len(self.bot.color_calibration_map)} colors'
            else:
                self.tlabel['text'] = 'Failed to save calibration data'
            
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror(self.title, f'Calibration failed: {str(e)}')
        finally:
            # Close calibration overlay window
            self._close_calibration_overlay()
            # Restore window after calibration completes (even if cancelled or failed)
            self._root.deiconify()
            self._root.wm_state('normal')
            self._set_busy(False)

    def simple_test_draw(self):
        """Execute simple test draw"""
        try:
            t = time.time()

            messagebox.showinfo(self.title, 'Simple test draw: Will draw 5 lines (1/4 canvas width each) starting from upper-left corner.\n\nPlease select your desired color in painting app first. No color picking will occur.')
            self._root.iconify()

            # Clear any previous termination/paused state
            self.bot.terminate = False
            self.bot.paused = False
            self.bot.drawing = False

            result = self.bot.simple_test_draw()
            self._root.deiconify()
            self._root.wm_state('normal')

            if result == 'success':
                actual_time = time.time() - t
                self.tlabel['text'] = f"Simple test draw completed. Time elapsed: {actual_time:.2f}s"
            elif result == 'terminated':
                actual_time = time.time() - t
                self.tlabel['text'] = f"Simple test draw terminated. Time elapsed: {actual_time:.2f}s"
                self.bot.terminate = False
            else:
                self.tlabel['text'] = f"Simple test draw result: {result}"
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror(self.title, f'Simple test draw failed: {str(e)}')
        finally:
            self._set_busy(False)

    @is_free
    def start_draw_thread(self):
        # `_draw_thread` is actual Thread object used elsewhere; keep that name.
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

            messagebox.showinfo(self.title, f'Test drawing first {test_lines} lines. Adjust your brush size in the painting app, then use the full "Start" button.')
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
                actual_time = time.time() - t
                # Show time comparison if available
                if hasattr(self.bot, 'estimated_time_seconds'):
                    estimated_str = self.bot._format_time(self.bot.estimated_time_seconds)
                    actual_str = self.bot._format_time(actual_time)
                    diff_seconds = self.bot.estimated_time_seconds - actual_time
                    if diff_seconds >= 0:
                        diff_str = f"Saved: {self.bot._format_time(diff_seconds)}"
                    else:
                        diff_str = f"Extra: {self.bot._format_time(abs(diff_seconds))}"
                    self.tlabel['text'] = f"Test draw completed! Est: {estimated_str}, Act: {actual_str}, {diff_str}"
                else:
                    self.tlabel['text'] = f"Test draw completed. Time elapsed: {actual_time:.2f}s"
            elif result == 'terminated':
                actual_time = time.time() - t
                if hasattr(self.bot, 'estimated_time_seconds'):
                    estimated_str = self.bot._format_time(self.bot.estimated_time_seconds)
                    actual_str = self.bot._format_time(actual_time)
                    self.tlabel['text'] = f"Test draw terminated. Est: {estimated_str}, Act: {actual_str}"
                else:
                    self.tlabel['text'] = f"Test draw terminated by user. Time elapsed: {actual_time:.2f}s"
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
                # Determining corner coordinates based on the received input. ImageGrab.grab() always expects
                # the first pair of coordinates to be above and on the left of the second pair
                top_left = min(self._coords[0], self._coords[2]), min(self._coords[1], self._coords[3])
                bot_right = max(self._coords[0], self._coords[2]), max(self._coords[1], self._coords[3])
                box = top_left + bot_right
                print(f'Capturing box: {box}')

                # Store selected region coordinates
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
        """Cancel redraw region selection"""
        self._redraw_picking = False
        self.tlabel['text'] = "Redraw region selection cancelled."

    def _on_delete_calibration(self):
        """Remove the color calibration file"""
        from tkinter import messagebox
        if messagebox.askyesno(self.title, "Are you sure you want to remove the color calibration file?\n\nThis will delete: color_calibration.json"):
            try:
                import os
                calib_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'color_calibration.json')
                if os.path.exists(calib_path):
                    os.remove(calib_path)
                    self.tlabel['text'] = "Color calibration file removed successfully."
                    # Clear calibration data from bot
                    self.bot.color_calibration_map = None
                    print(f"[File Management] Removed calibration file: {calib_path}")
                else:
                    self.tlabel['text'] = "No calibration file found to remove."
            except Exception as e:
                self.tlabel['text'] = f"Error removing calibration file: {str(e)}"
                print(f"[File Management] Error: {e}")

    def _on_reset_config(self):
        """Delete config.json file to reset to defaults"""
        from tkinter import messagebox
        if messagebox.askyesno(self.title, "Are you sure you want to reset to default settings?\n\nThis will delete: config.json\n\nAll your tool positions, settings, and preferences will be lost."):
            try:
                import os
                config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
                if os.path.exists(config_path):
                    os.remove(config_path)
                    self.tlabel['text'] = "Config file removed successfully. Please restart the application to use defaults."
                    print(f"[File Management] Removed config file: {config_path}")
                else:
                    self.tlabel['text'] = "No config file found to remove."
            except Exception as e:
                self.tlabel['text'] = f"Error removing config file: {str(e)}"
                print(f"[File Management] Error: {e}")

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
                self.tlabel['text'] = "No drawable content found in the selected region."
                return

            # Show drawing time estimate
            drawing_eta = self.bot.estimate_drawing_time(cmap)
            print(f"Estimated redraw time: {drawing_eta}")
            self.tlabel['text'] = f"Starting redraw - ETA: {drawing_eta}"

            messagebox.showwarning(self.title, f'Redrawing the selected region.\nPress ESC to stop the bot. Press {self.bot.pause_key} to pause/resume.')
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
                actual_time = time.time() - t
                # Show time comparison if available
                if hasattr(self.bot, 'estimated_time_seconds'):
                    estimated_str = self.bot._format_time(self.bot.estimated_time_seconds)
                    actual_str = self.bot._format_time(actual_time)
                    diff_seconds = self.bot.estimated_time_seconds - actual_time
                    if diff_seconds >= 0:
                        diff_str = f"Saved: {self.bot._format_time(diff_seconds)}"
                    else:
                        diff_str = f"Extra: {self.bot._format_time(abs(diff_seconds))}"
                    self.tlabel['text'] = f"Redraw completed! Est: {estimated_str}, Act: {actual_str}, {diff_str}"
                else:
                    self.tlabel['text'] = f"Redraw completed. Time elapsed: {actual_time:.2f}s"
            elif result == 'terminated':
                actual_time = time.time() - t
                if hasattr(self.bot, 'estimated_time_seconds'):
                    estimated_str = self.bot._format_time(self.bot.estimated_time_seconds)
                    actual_str = self.bot._format_time(actual_time)
                    self.tlabel['text'] = f"Redraw terminated. Est: {estimated_str}, Act: {actual_str}"
                else:
                    self.tlabel['text'] = f"Redraw terminated by user. Time elapsed: {actual_time:.2f}s"
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

            # Validate points
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

                # Restore UI
                self._root.deiconify()
                self._root.wm_state('normal')

                print(f"Region selected: ({min_x}, {min_y}) to ({max_x}, {max_y})")
                messagebox.showinfo(self.title, f"Region selected!\n\nTop-left: ({min_x}, {min_y})\nBottom-right: ({max_x}, {max_y})\n\nYou can now click 'Draw Region' to redraw this area.")

        except KeyboardInterrupt:
            print("Mouse capture cancelled by user")
            self._cancel_redraw_pick()
            # Restore UI
            self._root.deiconify()
            self._root.wm_state('normal')
        except Exception as e:
            print(f"Error during mouse capture: {e}")
            self._cancel_redraw_pick()
            # Restore UI
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
            # Allow time for user to click inside the app to draw in
            time.sleep(5)
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
                actual_time = time.time() - t
                # Show time comparison if available
                if hasattr(self.bot, 'estimated_time_seconds'):
                    estimated_str = self.bot._format_time(self.bot.estimated_time_seconds)
                    actual_str = self.bot._format_time(actual_time)
                    diff_seconds = self.bot.estimated_time_seconds - actual_time
                    if diff_seconds >= 0:
                        diff_str = f"Saved: {self.bot._format_time(diff_seconds)}"
                    else:
                        diff_str = f"Extra: {self.bot._format_time(abs(diff_seconds))}"
                    self.tlabel['text'] = f"Success! Est: {estimated_str}, Act: {actual_str}, {diff_str}"
                else:
                    self.tlabel['text'] = f"Success. Time elapsed: {actual_time:.2f}s"
            elif result == 'terminated':
                actual_time = time.time() - t
                if hasattr(self.bot, 'estimated_time_seconds'):
                    estimated_str = self.bot._format_time(self.bot.estimated_time_seconds)
                    actual_str = self.bot._format_time(actual_time)
                    self.tlabel['text'] = f"Terminated. Est: {estimated_str}, Act: {actual_str}"
                else:
                    self.tlabel['text'] = f"Terminated by user. Time elapsed: {actual_time:.2f}s"
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
                actual_time = time.time() - t
                if hasattr(self.bot, 'estimated_time_seconds'):
                    estimated_str = self.bot._format_time(self.bot.estimated_time_seconds)
                    actual_str = self.bot._format_time(actual_time)
                    self.tlabel['text'] = f"Paused. Press {self.bot.pause_key} again to resume. Est: {estimated_str}, Act: {actual_str}"
                else:
                    self.tlabel['text'] = f"Paused. Press {self.bot.pause_key} again to resume. Time elapsed: {actual_time:.2f}s"
            else:
                self.tlabel['text'] = f"Unknown result: {result}"
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror(self.title, str(e))

        # Let the thread manager know that the task has ended
        self._set_busy(False)
