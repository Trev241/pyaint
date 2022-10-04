import utils

from tkinter import Button, Label, Toplevel
from PIL import Image, ImageTk

class InstructionWindow:
    def __init__(self, parent, pages, on_complete=None, on_terminate=None, title='Child', w=700, h=550, x=50, y=50):
        self._root = Toplevel(parent)
        self._root.title('Setup Tutorial')
        self._root.geometry(f"{w}x{h}+{x}+{y}")
        self._root.protocol('WM_DELETE_WINDOW', self.close)

        self.title = title
        self._callback = on_complete
        self._on_terminate = on_terminate

        self._root.rowconfigure(0, weight=7, uniform='row')
        self._root.rowconfigure(1, weight=2, uniform='row')
        self._root.rowconfigure(2, weight=1, uniform='row')
        self._root.rowconfigure(3, weight=1, uniform='row')
        self._root.columnconfigure(0, weight=1, uniform='column')
        self._root.columnconfigure(1, weight=1, uniform='column')

        self.pages = pages

        self._img = None
        self._container = Label(self._root, borderwidth=3, relief='groove')
        self._help = Label(self._root, justify='left')
        self._back = Button(self._root, text='Back', command=lambda : self.set_page(self.current_page - 1))
        self._next = Button(self._root, text='Next', command=lambda : self.set_page(self.current_page + 1))
        self._skip = Button(self._root, text='Skip', command=self.complete)

        self._container.grid(column=0, row=0, columnspan=2, padx=5, pady=5, sticky='nsew')
        self._back.grid(column=0, row=2, padx=5, pady=5, sticky='ew')
        self._next.grid(column=1, row=2, padx=5, pady=5, sticky='ew')
        self._skip.grid(column=0, row=3, columnspan=2, padx=5, pady=5, sticky='ew')
        

        self._root.update()
        self._help['wraplength'] = self._root.winfo_width()
        self._help.grid(column=0, row=1, columnspan=2, padx=5, pady=5, sticky='nsew')
        
        self.set_page(0)

    def set_page(self, page=1):
        if page >= len(self.pages):
            self.complete()
            return

        self.current_page = min(len(self.pages) - 1, max(0, page))
        self._root.title(f'{self.title} ({self.current_page + 1} of {len(self.pages)})')

        info = self.pages[self.current_page]
        if info[0] is not None and isinstance(info[0], (str, Image.Image)):
            img = Image.open(info[0]) if type(info[0]) is str else info[0]
            size = utils.adjusted_img_size(img, (self._root.winfo_width(), self._root.winfo_height() * (7 / 11)))
            self._img = ImageTk.PhotoImage(img.resize(utils.adjusted_img_size(img, size)))

        self._help['text'] = info[1]
        self._container['image'] = self._img

    def close(self):
        self._root.destroy()
        if self._on_terminate is not None:
            self._on_terminate()

    def complete(self):
        self.close()
        if self._callback is not None:
            self._callback()