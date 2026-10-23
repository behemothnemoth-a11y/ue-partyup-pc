"""Static pixel artwork and a tiny group map; no animation or hardware I/O."""
from pathlib import Path
import tkinter as tk
from .theme import HERO, ACCENT, MUTED, INK, BORDER


def header_art(parent):
    path = Path(__file__).with_name('assets') / 'pixel-party-house.png'
    try:
        image = tk.PhotoImage(master=parent, file=str(path)).subsample(8)
    except (tk.TclError, OSError):
        return None
    label = tk.Label(parent, image=image, bg=HERO, bd=0)
    label.image = image
    return label


class PixelGroupMap(tk.Canvas):
    def __init__(self, parent):
        super().__init__(parent, height=68, bg=HERO, bd=0, highlightthickness=1,
                         highlightbackground=BORDER)
        self.selected = 0
        self.has_host = False
        self.bind('<Configure>', lambda _: self.draw())

    def show(self, has_host, selected):
        self.has_host, self.selected = has_host, selected
        self.draw()

    def draw(self):
        self.delete('all')
        width = max(self.winfo_width(), 600)
        slot = (width - 20) / 10
        for index in range(10):
            active = self.has_host if index == 0 else index <= self.selected
            x = 10 + slot * index + slot / 2
            color = ACCENT if active else BORDER
            if index:
                self.create_line(x - slot + 18, 25, x - 18, 25, fill=BORDER, width=2, dash=(4, 4))
            self.create_rectangle(x-13, 8, x+13, 42, fill=color, outline='')
            self.create_rectangle(x-17, 13, x+17, 37, fill=color, outline='')
            self.create_rectangle(x-9, 14, x+9, 36, fill=HERO, outline='')
            self.create_line(x-4, 23, x+4, 23, fill=color, width=2)
            self.create_line(x, 19, x, 27, fill=color, width=2)
            self.create_line(x-4, 32, x+4, 32, fill=color, width=2)
            self.create_text(x, 58, text='MAIN' if index == 0 else f'{index:02}',
                             fill=INK if active else MUTED, font=('Consolas', 9, 'bold'))
