import re
import utils

from PIL import (
    Image, 
    ImageTk,
    ImageGrab
)
from pynput.mouse import Listener
from tkinter import (
    Button, 
    Toplevel, 
    messagebox, 
    font, 
    END
)
from tkinter.ttk import (
    LabelFrame, 
    Frame, 
    Label, 
    Button, 
    Entry
)

class SetupWindow:
    def __init__(self, parent, bot, tools, on_complete, title='Child Window', w=700, h=600, x=5, y=5):
        self._root = Toplevel(parent)

        self.title = title
        self.bot = bot
        self.on_complete = on_complete
        self.tools = tools
        self.parent = parent

        self._root.title(self.title)
        self._root.geometry(f'{w}x{h}+{x}+{y}')
        self._root.protocol('WM_DELETE_WINDOW', self.close)

        default_font = font.nametofont('TkDefaultFont').actual()
        SetupWindow.TITLE_FONT = (default_font['family'], default_font['size'], 'bold')

        # LAYOUT
        self._root.columnconfigure(0, weight=1, uniform='column')
        self._root.rowconfigure(0, weight=1, uniform='row')
        self._root.rowconfigure(1, weight=1, uniform='row')
        
        self._tools_panel = self._init_tools_panel()
        self._tools_panel.grid(column=0, row=0, padx=5, pady=5, sticky='nsew')

        self._preview_panel = self._init_preview_panel()
        self._preview_panel.grid(column=0, row=1, sticky='nsew', padx=5, pady=5)

    def _init_tools_panel(self):
        frame = LabelFrame(self._root, text='Tools')

        for i in range(2):
            frame.columnconfigure(i, weight=1, uniform='column')
        frame.columnconfigure(2, weight=2, uniform='column')
        for i in range(3):
            frame.rowconfigure(i, weight=1, uniform='row')

        self._statuses = {}

        for idt, (k, v) in enumerate(self.tools.items()):
            Label(frame, text=k, font=SetupWindow.TITLE_FONT).grid(column=0, row=idt, sticky='w', padx=5, pady=5)
            status = Label(
                frame, 
                text='INITIALIZED' if v['status'] else 'NOT INITIALIZED', 
                foreground='white', 
                background='green' if v['status'] else 'red',
                justify='center',
                anchor='center'
            )
            status.grid(column=1, row=idt, sticky='ew', padx=10)
            self._statuses[k] = status

            settings_frame = Frame(frame)
            for i in range(4):
                settings_frame.columnconfigure(i, weight=1, uniform='column')
            settings_frame.rowconfigure(0, weight=1, uniform='row')

            # Do not write the callback as "lambda : self._start_listening(tool)" as this will cause only the last tool to be registered in every callback
            # Instead, do "lambda t=tool : self._start_listening(t)" which will pass the tool of the current iteration for every new callback.
            # (Note that t here stores the current tool as a default argument)
            Button(settings_frame, text='Initialize', command=lambda n=k, t=v : self._start_listening(n, t)).grid(column=0, columnspan=2, row=0, sticky='ew', padx=5, pady=5)
            Button(settings_frame, text='Preview', command=lambda n=k : self._set_preview(n)).grid(column=2, columnspan=2, row=0, sticky='ew', padx=5, pady=5)

            if k == 'Palette':
                settings_frame.rowconfigure(1, weight=1, uniform='row')

                Label(settings_frame, text='Rows').grid(column=0, row=1, padx=5, pady=5)
                self._erows = Entry(settings_frame, width=5)
                self._erows.grid(column=1, row=1, padx=5, pady=5)
                Label(settings_frame, text='Columns').grid(column=2, row=1, padx=5, pady=5)
                self._ecols = Entry(settings_frame, width=5)
                self._ecols.grid(column=3, row=1, padx=5, pady=5)

                self._erows.insert(0, v['rows'])
                self._ecols.insert(0, v['cols'])
                vcmd = (self._root.register(self._validate_dimensions), '%P')
                ivcmd = (self._root.register(self._on_invalid_dimensions),)
                self._erows.config(
                    validate='all', 
                    validatecommand=vcmd, 
                    invalidcommand=ivcmd
                )
                self._erows.bind('<FocusOut>', self._on_update_dimensions)
                self._erows.bind('<Return>', self._on_update_dimensions)
                self._ecols.config(
                    validate='all',
                    validatecommand=vcmd,
                    invalidcommand=ivcmd
                )
                self._ecols.bind('<FocusOut>', self._on_update_dimensions)
                self._ecols.bind('<Return>', self._on_update_dimensions)

            settings_frame.grid(column=2, row=idt, sticky='nsew')
        return frame

    def _init_preview_panel(self):
        frame = LabelFrame(self._root, text='Preview')
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        self._img_label = Label(frame, text='No image to preview')
        self._img_label.grid(column=0, row=0, sticky='ns', padx=5, pady=5)

        return frame

    def _set_preview(self, name):
        self._current_tool = self.tools[name]
        try:
            self._img = Image.open(self.tools[name]['preview'])
            self._img = ImageTk.PhotoImage(self._img.resize(
                utils.adjusted_img_size(self._img, (self._preview_panel.winfo_width() - 10, self._preview_panel.winfo_height() - 10))
            ))
            self._img_label['image'] = self._img
        except:
            self._img_label['image'] = ''
            self._img_label['text'] = 'No image to preview'

    def _start_listening(self, name, tool):
        self._current_tool = tool
        self._tool_name = name

        if self._tool_name == 'Palette':
            try:
                self.rows = int(self._erows.get())
                self.cols = int(self._ecols.get())
            except:
                messagebox.showerror(self.title, 'Please enter valid values for rows and columns before initializing your palette!')
                return

        self._coords = []
        self._clicks = 0
        
        if messagebox.askokcancel(self.title, 'Click on the UPPER LEFT and LOWER RIGHT corners of the tool.') == True:
            self._listener = Listener(on_click=self._on_click)
            self._listener.start()
            self._root.iconify()
            self.parent.iconify()
            

    def _on_click(self, x, y, _, pressed):
        if pressed:
            self._root.bell()
            print(x, y)
            self._clicks += 1
            self._coords += x, y

            if self._clicks == 2:
                # Determining corner coordinates based on received input. ImageGrab.grab() always expects
                # the first pair of coordinates to be above and on the left of the second pair
                top_left = min(self._coords[0], self._coords[2]), min(self._coords[1], self._coords[3])
                bot_right = max(self._coords[0], self._coords[2]), max(self._coords[1], self._coords[3])
                box = top_left + bot_right
                
                print(f'Capturing box: {box}')
                
                init_functions = {
                    'Palette': self.bot.init_palette,
                    'Canvas': self.bot.init_canvas,
                    'Custom Colors': self.bot.init_custom_colors
                }

                if self._tool_name == 'Palette':
                    p = init_functions['Palette'](prows=self.rows, pcols=self.cols, pbox=box)
                    # JSON does not support saving tuples hence the key has been converted into a string instead
                    self._current_tool['color_coords'] = {str(k): v for k, v in p.colors_pos.items()}
                    self._current_tool['rows'] = self.rows
                    self._current_tool['cols'] = self.cols
                else:
                    init_functions[self._tool_name](box)

                self._current_tool['status'] = True
                self._current_tool['box'] = box
                self._statuses[self._tool_name].configure(text='INITIALIZED', background='green')
                
                self._preview_panel.update()
                self._current_tool['preview'] = f'assets/{self._tool_name}_preview.png'
                ImageGrab.grab(box).save(self._current_tool['preview'], format='png')

                self._listener.stop()
                self.parent.deiconify()
                self._root.deiconify()

    def _validate_dimensions(self, value):
        return re.fullmatch('\d*', value) is not None

    def _on_invalid_dimensions(self):
        self._root.bell()

    def _on_update_dimensions(self, event):
        if event.widget.get() == '':
            event.widget.delete(0, END)
            event.widget.insert(0, '1')

    def close(self):
        self._root.destroy()
        self.on_complete()