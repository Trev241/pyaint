import re
import utils

from PIL import (
    Image, 
    ImageTk,
    ImageGrab
)
from pynput.mouse import Listener
from pynput import keyboard
from tkinter import (
    Button, 
    Toplevel, 
    messagebox, 
    font, 
    END,
    Canvas,
    Scrollbar,
    Label as tkLabel  # Import tkinter.Label for color control
)
from tkinter.ttk import (
    LabelFrame, 
    Frame, 
    Label, 
    Button, 
    Entry
)

class SetupWindow:
    def __init__(self, parent, bot, tools, on_complete, title='Child Window', w=700, h=800, x=5, y=5):
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
            # Use the 'name' field for display if it exists, otherwise use the key
            display_name = v.get('name', k) if isinstance(v, dict) else k
            Label(frame, text=display_name, font=SetupWindow.TITLE_FONT).grid(column=0, row=idt, sticky='w', padx=5, pady=5)
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
            
            if k == 'New Layer' or k == 'Color Button' or k == 'Color Button Okay':
                # Create modifier checkboxes (CTRL, ALT, SHIFT)
                from tkinter import Checkbutton, IntVar
                self._mod_vars = getattr(self, '_mod_vars', {})
                mv = {}
                mods = v.get('modifiers', {}) if isinstance(v, dict) else {}
                for ci, name in enumerate(('ctrl', 'alt', 'shift')):
                    iv = IntVar()
                    iv.set(1 if mods.get(name, False) else 0)
                    # FIXED: Capture k as default argument tk to avoid lambda closure bug
                    cb = Checkbutton(settings_frame, text=name.upper(), variable=iv,
                                     command=lambda tk=k, n=name, iv=iv: self._on_modifier_toggle(tk, n, iv))
                    cb.grid(column=2 + ci, row=0, padx=2, sticky='w')
                    mv[name] = iv
                self._mod_vars[k] = mv
            elif k == 'color_preview_spot':
                # Color preview spot doesn't need any extra buttons (no modifiers, no preview)
                pass
            else:
                Button(settings_frame, text='Preview', command=lambda n=k : self._set_preview(n)).grid(column=2, columnspan=1, row=0, sticky='ew', padx=2, pady=5)
                
                # Add Manual Color Selection button for Palette
                if k == 'Palette':
                    Button(settings_frame, text='Edit Colors', command=lambda n=k, t=v : self._start_manual_color_selection(n, t)).grid(column=3, columnspan=1, row=0, sticky='ew', padx=2, pady=5)

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

            elif k == 'Color Button':
                settings_frame.rowconfigure(1, weight=1, uniform='row')

                Label(settings_frame, text='Delay (s)').grid(column=0, row=1, padx=5, pady=5)
                self._edelay = Entry(settings_frame, width=8)
                self._edelay.grid(column=1, row=1, padx=5, pady=5)

                delay_value = v.get('delay', 0.1)
                self._edelay.insert(0, str(delay_value))
                delay_vcmd = (self._root.register(self._validate_delay), '%P')
                delay_ivcmd = (self._root.register(self._on_invalid_delay),)
                self._edelay.config(
                    validate='all',
                    validatecommand=delay_vcmd,
                    invalidcommand=delay_ivcmd
                )
                self._edelay.bind('<FocusOut>', self._on_update_delay)
                self._edelay.bind('<Return>', self._on_update_delay)

            elif k == 'Color Button Okay':
                settings_frame.rowconfigure(1, weight=1, uniform='row')

                from tkinter import Checkbutton, IntVar
                self._enable_vars = getattr(self, '_enable_vars', {})
                ev = IntVar()
                ev.set(1 if v.get('enabled', False) else 0)
                cb = Checkbutton(settings_frame, text='Enable', variable=ev,
                             command=lambda n=k, ev=ev: self._on_enable_toggle(n, ev))
                cb.grid(column=0, row=1, columnspan=4, padx=5, pady=5, sticky='w')
                self._enable_vars[k] = ev

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
        
        # FIXED: Added 'color_preview_spot' to the tuple checking for single-click tools
        # Using the correct configuration key name
        self._required_clicks = 1 if self._tool_name in ('New Layer', 'Color Button', 'Color Button Okay', 'color_preview_spot') else 2
        
        prompt = 'Click the location of the button.' if self._required_clicks == 1 else 'Click on the UPPER LEFT and LOWER RIGHT corners of the tool.'
        if messagebox.askokcancel(self.title, prompt) == True:
            self._listener = Listener(on_click=self._on_click)
            self._listener.start()
            self._root.iconify()
            self.parent.iconify()
    
    def _start_manual_color_selection(self, name, tool):
        """Start manual color selection for palette grid"""
        self._current_tool = tool
        self._tool_name = name
        
        if self._tool_name != 'Palette':
            messagebox.showerror(self.title, 'Manual color selection is only available for Palette!')
            return
        
        # Check if palette has been captured
        if not tool.get('box'):
            messagebox.showerror(self.title, 'Please initialize the palette first (click Initialize)!')
            return
        
        self.rows = tool['rows']
        self.cols = tool['cols']
        box = tool['box']
        
        # Ensure palette_box coordinates are in correct order (left, top, right, bottom)
        if len(box) == 4:
            left = min(box[0], box[2])
            top = min(box[1], box[3])
            right = max(box[0], box[2])
            bottom = max(box[1], box[3])
            self.palette_box = (left, top, right, bottom)
        else:
            self.palette_box = box
        
        # Open color selection window
        self._open_color_selection_window()
    
    def _open_color_selection_window(self):
        """Open window for manually selecting valid palette colors"""
        # Create a new Toplevel window for color selection
        self._color_sel_window = Toplevel(self._root)
        self._color_sel_window.title('Select Valid Palette Colors')
        self._color_sel_window.geometry('900x700+100+100')
        
        # Center the window
        self._color_sel_window.update_idletasks()
        sw = self._color_sel_window.winfo_screenwidth()
        sh = self._color_sel_window.winfo_screenheight()
        w, h = 900, 700
        x = (sw - w) // 2
        y = (sh - h) // 2
        self._color_sel_window.geometry(f'{w}x{h}+{x}+{y}')
        
        # Configure grid layout
        self._color_sel_window.columnconfigure(0, weight=1)
        self._color_sel_window.rowconfigure(0, weight=0)  # Instructions and mode
        self._color_sel_window.rowconfigure(1, weight=1)  # Grid
        
        # Mode selection
        self._pick_centers_mode = False  # False = Toggle mode, True = Pick centers mode
        self._manual_centers = {}  # Store manually picked centers {index: (x, y)}
        
        # Load existing manual centers if available
        if self._current_tool.get('manual_centers'):
            self._manual_centers = {int(k): tuple(v) for k, v in self._current_tool['manual_centers'].items()}
        
        # Create grid buttons
        self._grid_buttons = {}
        
        # Load existing valid_positions if available, otherwise assume all are valid
        if self._current_tool.get('valid_positions'):
            # Filter to only include positions within current grid bounds
            max_position = self.rows * self.cols - 1
            self._valid_positions = {pos for pos in self._current_tool['valid_positions'] if pos <= max_position}
        else:
            self._valid_positions = set(range(self.rows * self.cols))
        
        # Instructions
        instructions = Label(
            self._color_sel_window,
            text='Click on grid cells to toggle them. Green = Valid, Red = Invalid. Use "Pick Centers" mode to set exact center points.',
            wraplength=870,
            justify='left'
        )
        instructions.grid(column=0, row=0, padx=10, pady=10, sticky='ew')
        
        # Mode buttons
        mode_frame = Frame(self._color_sel_window)
        mode_frame.grid(column=0, row=0, padx=10, pady=5, sticky='e')
        
        self._mode_btn_toggle = Button(mode_frame, text='Toggle Valid/Invalid', command=self._set_toggle_mode)
        self._mode_btn_toggle.pack(side='left', padx=5)
        
        self._mode_btn_pick = Button(mode_frame, text='Pick Centers', command=self._set_pick_centers_mode)
        self._mode_btn_pick.pack(side='left', padx=5)
        
        # Scrollable frame for grid
        canvas = Canvas(self._color_sel_window)
        scrollbar = Scrollbar(self._color_sel_window, orient='vertical', command=canvas.yview)
        scrollable_frame = Frame(canvas)
        
        scrollable_frame.bind(
            '<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all'))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(column=0, row=1, sticky='nsew', padx=10, pady=10)
        scrollbar.grid(column=1, row=1, sticky='ns', pady=10)
        
        # Create grid cells
        self._grid_buttons = {}
        # Note: self._valid_positions is already loaded above from config
        
        # Load palette preview image
        try:
            palette_img = Image.open(self._current_tool['preview'])
            self._palette_img_tk = ImageTk.PhotoImage(palette_img)
            
            # Display palette image as reference
            img_label = Label(scrollable_frame, image=self._palette_img_tk)
            img_label.grid(column=0, row=0, columnspan=self.cols, padx=5, pady=5)
            
            current_row = 1
        except:
            current_row = 0
            self._palette_img_tk = None
        
        # Create clickable grid cells
        for i in range(self.rows * self.cols):
            row = i // self.cols
            col = i % self.cols
            
            # Use tkLabel (tkinter.Label) for better color control (can change background)
            lbl = tkLabel(
                scrollable_frame,
                text=f'{i+1}',
                width=8,
                relief='raised',
                borderwidth=2,
                cursor='hand2'
            )
            lbl.bind('<Button-1>', lambda e, idx=i: self._toggle_grid_cell(idx))
            # Set initial color based on valid/invalid state
            if i in self._valid_positions:
                lbl.config(bg='lightgreen')
            else:
                lbl.config(bg='mistyrose')
            lbl.grid(column=col, row=current_row + row, padx=2, pady=2)
            self._grid_buttons[i] = lbl
        
        # Done button
        done_frame = Frame(self._color_sel_window)
        done_frame.grid(column=0, row=2, padx=10, pady=10, sticky='ew')
        
        Button(
            done_frame,
            text='Done',
            command=self._on_color_selection_done
        ).pack(side='left', padx=5)
        
        Button(
            done_frame,
            text='Auto-Estimate Centers',
            command=self._auto_estimate_centers
        ).pack(side='left', padx=5)
        
        Button(
            done_frame,
            text='Precision Estimate',
            command=self._start_precision_estimate
        ).pack(side='left', padx=5)
        
        Button(
            done_frame,
            text='Show Custom Centers',
            command=self._show_custom_centers_overlay
        ).pack(side='left', padx=5)
        
        Button(
            done_frame,
            text='Select All',
            command=self._select_all_colors
        ).pack(side='left', padx=5)
        
        Button(
            done_frame,
            text='Deselect All',
            command=self._deselect_all_colors
        ).pack(side='left', padx=5)
        
        Button(
            done_frame,
            text='Cancel',
            command=lambda: self._color_sel_window.destroy()
        ).pack(side='left', padx=5)
        
        # Bind ESC key to cancel picking on the parent window (works even when color window is minimized)
        self.parent.bind('<Escape>', lambda e: self._on_escape_press(e))
    
    def _toggle_grid_cell(self, index):
        """Toggle a grid cell between valid and invalid"""
        if index in self._valid_positions:
            self._valid_positions.remove(index)
            self._grid_buttons[index].config(bg='mistyrose')
        else:
            self._valid_positions.add(index)
            self._grid_buttons[index].config(bg='lightgreen')
    
    def _select_all_colors(self):
        """Select all grid cells as valid"""
        self._valid_positions = set(range(self.rows * self.cols))
        for i, btn in self._grid_buttons.items():
            btn.config(bg='lightgreen')
    
    def _deselect_all_colors(self):
        """Deselect all grid cells"""
        self._valid_positions = set()
        for i, btn in self._grid_buttons.items():
            btn.config(bg='mistyrose')
    
    def _set_toggle_mode(self):
        """Set mode to toggle valid/invalid cells"""
        self._pick_centers_mode = False
        self._manual_centers = {}  # Clear manual centers when switching modes
        # Update instructions
        for widget in self._color_sel_window.winfo_children():
            try:
                if isinstance(widget, Label) and 'text' in str(widget.cget('text')):
                    widget.config(text='Click on grid cells to toggle them. Green = Valid, Red = Invalid. Click "Done" when finished.')
            except:
                pass
        # Update grid to show valid/invalid toggle AND rebind click handler
        for i, lbl in self._grid_buttons.items():
            if i in self._valid_positions:
                lbl.config(bg='lightgreen', cursor='hand2', text=f'{i+1}')
            else:
                lbl.config(bg='mistyrose', cursor='hand2', text=f'{i+1}')
            # Rebind click handler to toggle mode function
            lbl.unbind('<Button-1>')
            lbl.bind('<Button-1>', lambda e, idx=i: self._toggle_grid_cell(idx))
    
    def _set_pick_centers_mode(self):
        """Set mode to pick exact center points for each color"""
        if not self._valid_positions:
            messagebox.showwarning(self.title, 'Please mark at least one color as valid first!')
            return
        
        self._pick_centers_mode = True
        self._manual_centers = {}  # Reset manual centers
        # Clear existing manual centers when entering pick mode
        for i in list(self._manual_centers.keys()):
            del self._manual_centers[i]
        
        # Update instructions
        for widget in self._color_sel_window.winfo_children():
            try:
                if isinstance(widget, Label) and 'text' in str(widget.cget('text')):
                    widget.config(text='Click on a color cell, then click the center point on your palette. System will automatically move to the next color. Press ESC to stop at any time. Yellow = Has center, White = No center yet.')
            except:
                pass
        
        # Update grid to show center picking status
        for i, lbl in self._grid_buttons.items():
            if i in self._manual_centers:
                lbl.config(bg='yellow', text='✓')
            else:
                lbl.config(bg='white', text=f'{i+1}')
            lbl.unbind('<Button-1>')
            lbl.bind('<Button-1>', lambda e, idx=i: self._pick_center(idx))
    
    def _pick_center(self, index):
        """Pick a center point for a specific color cell"""
        if index not in self._valid_positions:
            messagebox.showwarning(self.title, 'Cannot pick center for invalid cell!')
            return
        
        # Wait for mouse click to get center coordinates
        self._coords = []
        self._clicks = 0
        self._required_clicks = 1
        self._current_picking_index = index
        
        # Start listening for mouse click (no confirmation dialog for continuous picking)
        print(f'Picking center for color {index + 1}... Press ESC to stop.')
        self._listener = Listener(on_click=self._on_center_pick_click)
        self._listener.start()
        
        # Start global keyboard listener for ESC key
        self._key_listener = keyboard.Listener(on_press=self._on_key_press)
        self._key_listener.start()
        
        self._color_sel_window.iconify()
    
    def _on_key_press(self, key):
        """Handle keyboard press events"""
        try:
            # Check if ESC key is pressed
            if key == keyboard.Key.esc:
                if self._pick_centers_mode and hasattr(self, '_listener'):
                    # Stop the mouse listener and keyboard listener
                    try:
                        self._listener.stop()
                    except:
                        pass
                    try:
                        self._key_listener.stop()
                    except:
                        pass
                    self._color_sel_window.deiconify()
                    print('Center picking cancelled by ESC key')
        except AttributeError:
            pass  # Ignore special keys that don't have char attribute
    
    def _auto_estimate_centers(self):
        """Automatically estimate centers for all valid colors"""
        if not self._valid_positions:
            messagebox.showwarning(self.title, 'Please mark at least one color as valid first!')
            return
        
        # Calculate cell dimensions
        palette_w = self.palette_box[2] - self.palette_box[0]
        palette_h = self.palette_box[3] - self.palette_box[1]
        cell_w = palette_w // self.cols
        cell_h = palette_h // self.rows
        
        # Estimate centers for all valid positions
        for i in self._valid_positions:
            row = i // self.cols
            col = i % self.cols
            
            # Calculate center relative to palette box
            center_x = col * cell_w + cell_w // 2
            center_y = row * cell_h + cell_h // 2
            
            self._manual_centers[i] = (center_x, center_y)
            
            # Update the grid cell to show it has a center (show both number and checkmark)
            if i in self._grid_buttons:
                self._grid_buttons[i].config(bg='yellow', text=f'{i+1} ✓')
        
        # Show visual overlay of estimated centers on screen
        self._show_centers_overlay()
        
        # Update instructions to show estimated centers
        for widget in self._color_sel_window.winfo_children():
            try:
                if isinstance(widget, Label) and 'text' in str(widget.cget('text')):
                    widget.config(text='Centers auto-estimated (yellow = estimated). Click "Done" to accept or manually adjust by switching to Pick Centers mode.')
            except:
                pass
        
        print(f'Auto-estimated centers for {len(self._manual_centers)} colors')
    
    def _start_precision_estimate(self):
        """Start precision estimate mode using reference point selection"""
        if not self._valid_positions:
            messagebox.showwarning(self.title, 'Please mark at least one color as valid first!')
            return
        
        # Clear existing manual centers
        self._manual_centers = {}
        
        # Determine number of rows and columns with valid positions
        rows_with_valid = {i // self.cols for i in self._valid_positions}
        cols_with_valid = {i % self.cols for i in self._valid_positions}
        num_valid_rows = len(rows_with_valid)
        num_valid_cols = len(cols_with_valid)
        
        # Determine which mode to use based on row AND column count
        if num_valid_cols == 1 and num_valid_rows >= 2:
            # Single column, multiple rows - use single_column mode
            self._precision_mode = 'single_column'
        elif num_valid_rows == 1 and num_valid_cols >= 2:
            # Single row, multiple columns - use 1_row mode
            self._precision_mode = '1_row'
        elif num_valid_rows >= 2 and num_valid_cols >= 2:
            # Multiple rows and columns - use multi_row mode
            self._precision_mode = 'multi_row'
        else:
            messagebox.showwarning(self.title, 'No valid rows found!')
            return
        
        # Get instructions for this mode
        instructions = {
            'single_column': [
                ('Click on CENTER of FIRST color box in the FIRST row.', 'first_row_first_col'),
                ('Click on CENTER of FIRST color box in the SECOND row.', 'second_row_first_col'),
                ('Click on CENTER of FIRST color box in the LAST row.', 'last_row_first_col')
            ],
            '1_row': [
                ('Click on CENTER of FIRST color box (leftmost) in the row.', 'first_col'),
                ('Click on CENTER of SECOND color box in the row.', 'second_col'),
                ('Click on CENTER of LAST color box (rightmost) in the row.', 'last_col')
            ],
            'multi_row': []
        }
        
        # Dynamically generate multi_row instructions based on valid row count
        if self._precision_mode == 'multi_row':
            # First row points
            instructions['multi_row'].append(('Click on CENTER of FIRST color box (leftmost) in the FIRST row.', 'first_row_first_col'))
            instructions['multi_row'].append(('Click on CENTER of SECOND color box in the FIRST row.', 'first_row_second_col'))
            instructions['multi_row'].append(('Click on CENTER of LAST color box (rightmost) in the FIRST row.', 'first_row_last_col'))
            
            # Row points - only add second_row_first_col if there are more than 2 rows
            if num_valid_rows > 2:
                instructions['multi_row'].append(('Click on CENTER of FIRST color box in the SECOND row.', 'second_row_first_col'))
            
            # Last row points
            instructions['multi_row'].append(('Click on CENTER of FIRST color box (leftmost) in the LAST row.', 'last_row_first_col'))
            instructions['multi_row'].append(('Click on CENTER of LAST color box (rightmost) in the LAST row.', 'last_row_last_col'))
        
        # Start the precision estimation process
        self._precision_points = []
        self._precision_step = 0
        
        # Store instructions as instance variable for access in click handler
        self._precision_instructions = instructions[self._precision_mode]
        
        # Show all instructions in one dialog
        self._show_precision_dialog(self._precision_instructions)
    
    def _show_precision_dialog(self, instructions_list):
        """Show precision estimation instructions - all at once"""
        # Build instruction text
        instruction_text = "Click on the following points in order:\n\n"
        for i, (step_name, point_type) in enumerate(instructions_list):
            instruction_text += f"{i+1}. {step_name}\n"
        
        instruction_text += "\nClick OK to begin, then click the points on your palette in the order shown above."
        
        result = messagebox.askokcancel('Precision Estimate Instructions', instruction_text)
        
        if result:
            # User confirmed - minimize window and start listening
            self._color_sel_window.iconify()
            
            # Set up for first point
            self._precision_step = 0
            point_type = instructions_list[0][1]
            self._current_point_type = point_type
            
            # Start listening for click
            self._coords = []
            self._clicks = 0
            self._required_clicks = 1
            self._listener = Listener(on_click=self._on_precision_pick_click)
            self._listener.start()
        else:
            # User cancelled
            self._cancel_precision_estimate()
    
    def _show_precision_instruction(self):
        """Show instruction for next point to pick"""
        instructions = {
            'single_column': [
                ('Click on CENTER of FIRST color box in the FIRST row.', 'first_row_first_col'),
                ('Click on CENTER of FIRST color box in the SECOND row.', 'second_row_first_col'),
                ('Click on CENTER of FIRST color box in the LAST row.', 'last_row_first_col')
            ],
            '1_row': [
                ('Click on CENTER of FIRST color box (leftmost) in the row.', 'first_col'),
                ('Click on CENTER of SECOND color box in the row.', 'second_col'),
                ('Click on CENTER of LAST color box (rightmost) in the row.', 'last_col')
            ],
            'multi_row': [
                ('Click on CENTER of FIRST color box (leftmost) in the FIRST row.', 'first_row_first_col'),
                ('Click on CENTER of SECOND color box in the FIRST row.', 'first_row_second_col'),
                ('Click on CENTER of LAST color box (rightmost) in the FIRST row.', 'first_row_last_col'),
                ('Click on CENTER of FIRST color box in the SECOND row.', 'second_row_first_col'),
                ('Click on CENTER of FIRST color box (leftmost) in the LAST row.', 'last_row_first_col'),
                ('Click on CENTER of LAST color box (rightmost) in the LAST row.', 'last_row_last_col')
            ]
        }
        
        if self._precision_step < len(instructions[self._precision_mode]):
            instruction, point_type = instructions[self._precision_mode][self._precision_step]
            self._current_point_type = point_type
            
            # Show the messagebox with proper parent and window management
            self._color_sel_window.deiconify()
            self._color_sel_window.lift()
            self._root.after(50, lambda: self._show_precision_dialog(instruction))
        else:
            # All points collected, calculate centers
            self._calculate_precision_centers()
    
    def _on_precision_pick_click(self, x, y, _, pressed):
        """Handle click for precision estimate point selection"""
        if pressed:
            self._color_sel_window.bell()
            print(x, y)
            self._clicks += 1
            self._coords += x, y
            
            if self._clicks == self._required_clicks:
                # Store the picked point (relative to palette box)
                center_x = self._coords[0] - self.palette_box[0]
                center_y = self._coords[1] - self.palette_box[1]
                self._precision_points.append({
                    'type': self._current_point_type,
                    'coords': (center_x, center_y)
                })
                
                # DEBUG: Log detailed information
                print(f'[DEBUG] Screen click: ({x}, {y})')
                print(f'[DEBUG] Palette box: {self.palette_box}')
                print(f'[DEBUG] Relative center: ({center_x}, {center_y})')
                print(f'[DEBUG] Point type: {self._current_point_type}')
                
                # Move to next step
                self._precision_step += 1
                
                # Check if we have all required points
                # Get the instruction list to determine required point count
                if self._precision_mode == 'single_column':
                    required_points = 3
                elif self._precision_mode == '1_row':
                    required_points = 3
                else:  # multi_row
                    # Get the dynamically generated instruction count
                    required_points = len(self._precision_instructions)
                
                if self._precision_step >= required_points:
                    # All points collected, calculate centers
                    self._listener.stop()
                    self._calculate_precision_centers()
                else:
                    # Continue to next point - no dialog, just wait for next click
                    self._clicks = 0
                    self._coords = []
                    # Set point type for next step
                    if self._precision_mode == 'single_column':
                        point_types = ['first_row_first_col', 'second_row_first_col', 'last_row_first_col']
                    elif self._precision_mode == '1_row':
                        point_types = ['first_col', 'second_col', 'last_col']
                    else:
                        # Build point types from dynamically generated instructions
                        point_types = [pt for _, pt in self._precision_instructions]
                    self._current_point_type = point_types[self._precision_step]
                    print(f'Waiting for next click: {self._current_point_type}')
    
    def _calculate_precision_centers(self):
        """Calculate all centers based on precision estimate reference points"""
        try:
            # Get palette dimensions for clamping coordinates to valid range
            palette_w = self.palette_box[2] - self.palette_box[0]
            palette_h = self.palette_box[3] - self.palette_box[1]
            
            points_dict = {p['type']: p['coords'] for p in self._precision_points}
            
            if self._precision_mode == 'single_column':
                # Extract reference points
                first_row_first_col = points_dict['first_row_first_col']
                second_row_first_col = points_dict['second_row_first_col']
                last_row_first_col = points_dict['last_row_first_col']
                
                # Find first and last row indices with valid positions
                rows_with_valid = sorted(list({i // self.cols for i in self._valid_positions}))
                first_valid_row = rows_with_valid[0]
                last_valid_row = rows_with_valid[-1]
                
                # Calculate row spacing from first row to last row
                total_row_distance = last_row_first_col[1] - first_row_first_col[1]
                num_row_gaps = last_valid_row - first_valid_row
                row_spacing = total_row_distance / num_row_gaps if num_row_gaps > 0 else 0
                
                # Validate row spacing using second row if available
                if len(rows_with_valid) >= 2:
                    second_row_distance = second_row_first_col[1] - first_row_first_col[1]
                    expected_second_row_distance = row_spacing if first_valid_row + 1 == rows_with_valid[1] else row_spacing * (rows_with_valid[1] - first_valid_row)
                    # Use average if close, otherwise use direct measurement
                    if abs(second_row_distance - expected_second_row_distance) < 10:
                        avg_row_spacing = (row_spacing + second_row_distance) / (1 + (rows_with_valid[1] - first_valid_row))
                    else:
                        avg_row_spacing = row_spacing
                else:
                    avg_row_spacing = row_spacing
                
                # X position is the same for all in single column
                x_pos = first_row_first_col[0]
                
                # Calculate centers for all valid positions
                for i in self._valid_positions:
                    row_idx = i // self.cols
                    center_x = x_pos
                    center_y = first_row_first_col[1] + (row_idx - first_valid_row) * avg_row_spacing
                    # Clamp coordinates to valid range to prevent index out of bounds
                    center_x = max(0, min(center_x, palette_w - 1))
                    center_y = max(0, min(center_y, palette_h - 1))
                    self._manual_centers[i] = (center_x, center_y)
                
            elif self._precision_mode == '1_row':
                # Calculate horizontal spacing
                first_col = points_dict['first_col']
                second_col = points_dict['second_col']
                last_col = points_dict['last_col']
                
                # Get sorted valid column indices
                cols_with_valid = sorted(list({i % self.cols for i in self._valid_positions}))
                
                # Calculate spacing between columns
                col_spacing = second_col[0] - first_col[0]
                col_spacing2 = (last_col[0] - first_col[0]) / (len(cols_with_valid) - 1)
                
                # Use average of the two measurements for better accuracy
                avg_col_spacing = (col_spacing + col_spacing2) / 2
                
                # Y position is the same for all in single row
                y_pos = first_col[1]
                
                # Calculate centers for all valid positions
                for i in self._valid_positions:
                    col = i % self.cols
                    
                    # Find position of this column in valid columns
                    col_pos = cols_with_valid.index(col)
                    
                    center_x = first_col[0] + col_pos * avg_col_spacing
                    center_y = y_pos
                    # Clamp coordinates to valid range to prevent index out of bounds
                    center_x = max(0, min(center_x, palette_w - 1))
                    center_y = max(0, min(center_y, palette_h - 1))
                    
                    self._manual_centers[i] = (center_x, center_y)
                
            elif self._precision_mode == 'multi_row':
                # Extract reference points
                first_row_first_col = points_dict['first_row_first_col']
                first_row_second_col = points_dict['first_row_second_col']
                first_row_last_col = points_dict['first_row_last_col']
                last_row_first_col = points_dict['last_row_first_col']
                last_row_last_col = points_dict['last_row_last_col']
                
                # second_row_first_col may not be collected if there are only 2 rows
                second_row_first_col = points_dict.get('second_row_first_col', last_row_first_col)
                
                # Get sorted valid column indices
                cols_with_valid = sorted(list({i % self.cols for i in self._valid_positions}))
                first_valid_col = cols_with_valid[0]
                last_valid_col = cols_with_valid[-1]
                
                # Calculate horizontal spacing from first row
                col_spacing1 = first_row_second_col[0] - first_row_first_col[0]
                col_spacing2 = (first_row_last_col[0] - first_row_first_col[0]) / (len(cols_with_valid) - 1)
                avg_col_spacing = (col_spacing1 + col_spacing2) / 2
                
                # Find first and last row indices with valid positions
                rows_with_valid = sorted(list({i // self.cols for i in self._valid_positions}))
                first_valid_row = rows_with_valid[0]
                last_valid_row = rows_with_valid[-1]
                
                # Calculate row spacing from first row to last row
                total_row_distance = last_row_first_col[1] - first_row_first_col[1]
                num_row_gaps = last_valid_row - first_valid_row
                row_spacing = total_row_distance / num_row_gaps if num_row_gaps > 0 else 0
                
                # Validate row spacing using second row if available
                if len(rows_with_valid) >= 2:
                    second_row_distance = second_row_first_col[1] - first_row_first_col[1]
                    expected_second_row_distance = row_spacing if first_valid_row + 1 == rows_with_valid[1] else row_spacing * (rows_with_valid[1] - first_valid_row)
                    # Use average if close, otherwise use the direct measurement
                    if abs(second_row_distance - expected_second_row_distance) < 10:
                        avg_row_spacing = (row_spacing + second_row_distance) / (1 + (rows_with_valid[1] - first_valid_row))
                    else:
                        avg_row_spacing = row_spacing
                else:
                    avg_row_spacing = row_spacing
                
                # Calculate centers for all valid positions
                for i in self._valid_positions:
                    row_idx = i // self.cols
                    col = i % self.cols
                    
                    # Find position of this column in valid columns
                    col_pos = cols_with_valid.index(col)
                    
                    # Calculate Y position based on row index
                    center_y = first_row_first_col[1] + (row_idx - first_valid_row) * avg_row_spacing
                    
                    # Calculate X position based on column position in valid columns
                    center_x = first_row_first_col[0] + col_pos * avg_col_spacing
                    
                    # DEBUG: Log first center calculation
                    if i == min(self._valid_positions):
                        print(f'[DEBUG] First valid position: {i}')
                        print(f'[DEBUG] Row: {row_idx}, Col: {col}, Col pos: {col_pos}')
                        print(f'[DEBUG] first_row_first_col: {first_row_first_col}')
                        print(f'[DEBUG] avg_col_spacing: {avg_col_spacing}, avg_row_spacing: {avg_row_spacing}')
                        print(f'[DEBUG] Calculated center for pos {i}: ({center_x}, {center_y})')
                    
                    self._manual_centers[i] = (center_x, center_y)
            
            # Update grid to show estimated centers
            for i, lbl in self._grid_buttons.items():
                if i in self._manual_centers:
                    lbl.config(bg='yellow', text=f'{i+1} ✓')
                else:
                    lbl.config(bg='mistyrose', text=f'{i+1}')
            
            # Show overlay of estimated centers
            self._show_centers_overlay()
            
            # Show success message
            messagebox.showinfo(
                'Precision Estimate Complete',
                f'Precision estimate completed for {len(self._manual_centers)} colors!\n\n'
                f'Reference points collected: {len(self._precision_points)}\n'
                f'Mode: {self._precision_mode}\n\n'
                f'Yellow cells show estimated centers.\n'
                f'Click "Done" to accept or manually adjust centers.'
            )
            
            # Update instructions
            for widget in self._color_sel_window.winfo_children():
                try:
                    if isinstance(widget, Label) and 'text' in str(widget.cget('text')):
                        widget.config(text='Precision estimate complete (yellow = estimated). Click "Done" to accept or manually adjust by switching to Pick Centers mode.')
                except:
                    pass
            
            self._color_sel_window.deiconify()
            
        except Exception as e:
            messagebox.showerror('Precision Estimate Error', f'Error calculating centers: {str(e)}')
            self._cancel_precision_estimate()
    
    def _cancel_precision_estimate(self):
        """Cancel precision estimate mode"""
        self._precision_points = []
        self._precision_step = 0
        self._manual_centers = {}
        # Check if window still exists before deiconifying
        if hasattr(self, '_color_sel_window') and self._color_sel_window.winfo_exists():
            self._color_sel_window.deiconify()
        print('Precision estimate cancelled')
    
    def _show_centers_overlay(self):
        """Show overlay circles on screen at estimated center positions"""
        from tkinter import Toplevel, Canvas
        import time
        
        # Create overlay window positioned exactly over palette
        palette_x = self.palette_box[0]
        palette_y = self.palette_box[1]
        palette_w = self.palette_box[2] - self.palette_box[0]
        palette_h = self.palette_box[3] - self.palette_box[1]
        
        # Create overlay window
        overlay = Toplevel()
        overlay.overrideredirect(True)  # Remove window decorations
        overlay.attributes('-topmost', True)  # Keep on top
        overlay.attributes('-alpha', 0.9)  # Slightly transparent
        overlay.config(bg='white')  # White background to make red circles visible
        overlay.geometry(f'{palette_w}x{palette_h}+{palette_x}+{palette_y}')
        
        # Create canvas
        canvas = Canvas(overlay, bg='white', highlightthickness=0)
        canvas.pack(fill='both', expand=True)
        
        # Draw black dots at each estimated center position
        for i in sorted(self._manual_centers.keys()):
            center_x, center_y = self._manual_centers[i]
            
            # DEBUG: Log drawing coordinates
            if i == min(self._manual_centers.keys()):
                print(f'[DEBUG] Drawing first dot at canvas pos: ({center_x}, {center_y})')
                print(f'[DEBUG] Overlay window position: ({palette_x}, {palette_y})')
                print(f'[DEBUG] Expected screen position: ({palette_x + center_x}, {palette_y + center_y})')
            
            # Draw black dot (filled circle)
            canvas.create_oval(
                center_x - 6, center_y - 6,
                center_x + 6, center_y + 6,
                fill='black', outline='black'
            )
            
            # Add label showing color number
            canvas.create_text(
                center_x, center_y - 15,
                text=str(i + 1),
                fill='red',
                font=('Arial', 12, 'bold')
            )
        
        # Update window
        overlay.update()
        
        # Show for 5 seconds then close
        self._root.after(5000, lambda: overlay.destroy())
        print('Showing estimated centers overlay for 5 seconds...')
        
        # Show info dialog after overlay closes
        self._root.after(5100, lambda: messagebox.showinfo(
            self.title, 
            f'Auto-estimated centers for {len(self._manual_centers)} valid colors!\n\n'
            f'Red circles showed estimated positions on your palette.\n'
            f'Yellow cells in the grid show estimated centers.\n\n'
            f'You can still manually adjust by clicking "Pick Centers" to pick specific centers.'
        ))
    
    def _show_custom_centers_overlay(self):
        """Show overlay circles on screen at manually picked center positions"""
        from tkinter import Toplevel, Canvas
        import time
        
        if not self._manual_centers:
            messagebox.showwarning(self.title, 'No custom centers to show! Please pick centers first using "Pick Centers" mode.')
            return
        
        # Create overlay window positioned exactly over palette
        palette_x = self.palette_box[0]
        palette_y = self.palette_box[1]
        palette_w = self.palette_box[2] - self.palette_box[0]
        palette_h = self.palette_box[3] - self.palette_box[1]
        
        overlay = Toplevel()
        overlay.overrideredirect(True)  # Remove window decorations
        overlay.attributes('-topmost', True)  # Keep on top
        overlay.attributes('-alpha', 0.9)  # Slightly transparent
        overlay.config(bg='white')  # White background to make blue circles visible
        overlay.geometry(f'{palette_w}x{palette_h}+{palette_x}+{palette_y}')
        
        # Create canvas
        canvas = Canvas(overlay, bg='white', highlightthickness=0)
        canvas.pack(fill='both', expand=True)
        
        # Draw black dots at each custom center position
        for i in sorted(self._manual_centers.keys()):
            center_x, center_y = self._manual_centers[i]
            
            # Draw black dot (filled circle)
            canvas.create_oval(
                center_x - 6, center_y - 6,
                center_x + 6, center_y + 6,
                fill='black', outline='black'
            )
            
            # Add label showing color number
            canvas.create_text(
                center_x, center_y - 15,
                text=str(i + 1),
                fill='blue',
                font=('Arial', 12, 'bold')
            )
        
        # Update window
        overlay.update()
        
        # Show for 5 seconds then close
        self._root.after(5000, lambda: overlay.destroy())
        print('Showing custom centers overlay for 5 seconds...')
        
        # Show info dialog after overlay closes
        self._root.after(5100, lambda: messagebox.showinfo(
            self.title, 
            f'Displaying {len(self._manual_centers)} custom centers!\n\n'
            f'Blue circles showed your manually picked positions on your palette.\n'
            f'Yellow cells in the grid show custom centers.\n\n'
            f'You can adjust centers by clicking "Pick Centers" to pick specific centers.'
        ))
    
    def _on_escape_press(self, event):
        """Handle ESC key press to cancel picking"""
        if self._pick_centers_mode and hasattr(self, '_listener'):
            # Stop the listener and cancel picking
            try:
                self._listener.stop()
            except:
                pass  # Ignore errors when stopping
            self._color_sel_window.deiconify()
            print('Center picking cancelled by ESC key')
    
    def _on_center_pick_click(self, x, y, _, pressed):
        """Handle click for picking center point"""
        if pressed:
            self._root.bell()
            print(x, y)
            self._clicks += 1
            self._coords += x, y
            
            if self._clicks == self._required_clicks:
                # Store the picked center coordinates (relative to palette box)
                center_x = self._coords[0] - self.palette_box[0]
                center_y = self._coords[1] - self.palette_box[1]
                self._manual_centers[self._current_picking_index] = (center_x, center_y)
                
                # Update the grid cell to show it has a center
                if self._current_picking_index in self._grid_buttons:
                    self._grid_buttons[self._current_picking_index].config(bg='yellow', text='✓')
                
                print(f'Picked center for color {self._current_picking_index + 1}: ({center_x}, {center_y})')
                
                # Find next valid color that doesn't have a center yet
                next_index = None
                for i in sorted(self._valid_positions):
                    if i > self._current_picking_index and i not in self._manual_centers:
                        next_index = i
                        break
                
                if next_index is not None:
                    # Continue to next color automatically
                    self._current_picking_index = next_index
                    self._clicks = 0
                    self._coords = []
                    # Don't show messagebox, just continue picking
                    print(f'Continuing to color {next_index + 1}...')
                else:
                    # All valid colors have centers
                    self._listener.stop()
                    # Also stop the keyboard listener
                    try:
                        self._key_listener.stop()
                    except:
                        pass
                    self._color_sel_window.deiconify()
                    messagebox.showinfo(self.title, 'All valid colors have been assigned centers!\n\nClick "Done" to save or adjust centers.')
    
    def _on_color_selection_done(self):
        """Handle completion of manual color selection"""
        if not self._valid_positions:
            messagebox.showwarning(
                self.title,
                'You must select at least one valid color!'
            )
            return
        
        # Store valid positions in tool config
        self._current_tool['valid_positions'] = list(self._valid_positions)
        
        # Reinitialize palette with valid positions and manual centers
        try:
            pbox_adj = (self.palette_box[0], self.palette_box[1], 
                        self.palette_box[2] - self.palette_box[0], 
                        self.palette_box[3] - self.palette_box[1])
            
            # Pass manual_centers if in pick centers mode and centers were picked
            manual_centers = self._manual_centers if self._pick_centers_mode and self._manual_centers else None
            
            p = self.bot.init_palette(
                pbox=pbox_adj,
                prows=self.rows,
                pcols=self.cols,
                valid_positions=self._valid_positions,
                manual_centers=manual_centers
            )
            
            # Update tool data
            self._current_tool['color_coords'] = {str(k): v for k, v in p.colors_pos.items()}
            self._current_tool['manual_centers'] = {str(k): v for k, v in self._manual_centers.items()} if self._manual_centers else {}
            self._current_tool['status'] = True
            self._statuses[self._tool_name].configure(text='INITIALIZED', background='green')
            
            messagebox.showinfo(
                self.title,
                f'Palette updated with {len(self._valid_positions)} valid colors out of {self.rows * self.cols} total positions.'
            )
            
        except Exception as e:
            messagebox.showerror(self.title, f'Error updating palette: {str(e)}')
        
        # Close the selection window
        self._color_sel_window.destroy()
            

    def _on_click(self, x, y, _, pressed):
        if pressed:
            self._root.bell()
            print(x, y)
            self._clicks += 1
            self._coords += x, y

            if self._clicks == self._required_clicks:
                init_functions = {
                    'Palette': self.bot.init_palette,
                    'Canvas': self.bot.init_canvas,
                    'Custom Colors': self.bot.init_custom_colors,
                    'color_preview_spot': lambda box: None  # Single-click tool, no init needed
                }

                if self._required_clicks == 2:
                    # Determining corner coordinates based on received input. ImageGrab.grab() always expects
                    # the first pair of coordinates to be above and on the left of the second pair
                    top_left = (min(self._coords[0], self._coords[2]), min(self._coords[1], self._coords[3]))
                    bot_right = (max(self._coords[0], self._coords[2]), max(self._coords[1], self._coords[3]))
                    box = (top_left[0], top_left[1], bot_right[0], bot_right[1])
                    print(f'Capturing box: {box}')

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

                else:
                    # Single-click tools like New Layer
                    # Save the clicked point as coords
                    coords = (int(self._coords[0]), int(self._coords[1]))
                    print(f'Captured point: {coords}')
                    # Store as simple coords and mark status
                    self._current_tool['coords'] = list(coords)
                    self._current_tool['status'] = True
                    self._statuses[self._tool_name].configure(text='INITIALIZED', background='green')

                self._listener.stop()
                self.parent.deiconify()
                self._root.deiconify()

    def _validate_dimensions(self, value):
        return re.fullmatch(r'\d*', value) is not None

    def _on_invalid_dimensions(self):
        self._root.bell()

    def _on_update_dimensions(self, event):
        if event.widget.get() == '':
            event.widget.delete(0, END)
            event.widget.insert(0, '1')

    def _validate_delay(self, value):
        """Validate delay input: must be a number between 0.01 and 5.0"""
        if value == '':
            return True  # Allow empty during editing
        try:
            num = float(value)
            return 0.01 <= num <= 5.0
        except ValueError:
            return False

    def _on_invalid_delay(self):
        """Handle invalid delay input"""
        self._root.bell()

    def _on_update_delay(self, event):
        """Update delay value and validate on focus out or return"""
        try:
            value = event.widget.get()
            if value == '':
                # Default to 0.1 if empty
                event.widget.delete(0, END)
                event.widget.insert(0, '0.1')
                clamped = 0.1
            else:
                num = float(value)
                # Clamp to valid range
                clamped = max(0.01, min(5.0, num))
                if clamped != num:
                    event.widget.delete(0, END)
                    event.widget.insert(0, str(clamped))
            # Update tools dict with delay value
            self.tools['Color Button']['delay'] = clamped
        except ValueError:
            # If invalid, reset to default
            event.widget.delete(0, END)
            event.widget.insert(0, '0.1')
            self.tools['Color Button']['delay'] = 0.1

    def _on_enable_toggle(self, tool_name, intvar):
        # Update stored tools dict enabled state for given tool
        try:
            if tool_name in self.tools:
                self.tools[tool_name]['enabled'] = bool(intvar.get())
        except Exception:
            pass

    def _on_modifier_toggle(self, tool_name, modifier_name, intvar):
        # Update the stored tools dict modifiers for the given tool
        try:
            if tool_name in self.tools:
                if 'modifiers' not in self.tools[tool_name] or not isinstance(self.tools[tool_name]['modifiers'], dict):
                    self.tools[tool_name]['modifiers'] = {}
                self.tools[tool_name]['modifiers'][modifier_name] = bool(intvar.get())
        except Exception:
            pass

    def close(self):
        self._root.destroy()
        self.on_complete()
