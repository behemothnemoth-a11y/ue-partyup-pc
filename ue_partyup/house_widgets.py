"""House Party's static assets and keyboard-accessible pixel controls."""
import ctypes
from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from .theme import BG, SURFACE, PANEL, HERO, BORDER, INK, MUTED, ACCENT, DANGER

ASSETS = Path(__file__).with_name('assets')
DISPLAY = 'Silkscreen'


def load_pixel_font():
    """Register the bundled OFL font for this process, never system-wide."""
    if sys.platform == 'win32':
        ctypes.windll.gdi32.AddFontResourceExW(str(ASSETS / 'fonts' / 'Silkscreen-Regular.ttf'), 0x10, None)


def widget_background(widget):
    try:
        return widget.cget('background')
    except tk.TclError:
        return ttk.Style(widget).lookup(widget.cget('style') or widget.winfo_class(), 'background') or SURFACE


class Artwork:
    def __init__(self, master, background_name='house-party-background.png'):
        self.master = master
        self.house = Image.open(ASSETS / background_name).convert('RGB')
        self.speaker = Image.open(ASSETS / 'speaker-peach.png').convert('RGBA')
        box = self.speaker.getbbox()
        if box:
            self.speaker = self.speaker.crop(box)
        self.guest = Image.open(ASSETS / 'speaker-lavender.png').convert('RGBA')
        box = self.guest.getbbox()
        if box:
            self.guest = self.guest.crop(box)
        self.cache = {}

    def photo(self, kind, width, height=None):
        source = self.house if kind == 'house' else self.guest if kind == 'guest' else self.speaker
        width = max(1, int(width))
        height = max(1, int(height if height is not None else width * source.height / source.width))
        key = kind, width, height
        if key not in self.cache:
            # Keep only a few resize results; dragging the window must not grow memory.
            if len(self.cache) >= 20:
                self.cache.clear()
            sampling = Image.Resampling.LANCZOS if kind != 'house' and width < 120 else Image.Resampling.NEAREST
            self.cache[key] = ImageTk.PhotoImage(source.resize((width, height), sampling), master=self.master)
        return self.cache[key]


class PocketButton(tk.Canvas):
    """Stepped silhouette, real command, keyboard activation and disabled state."""
    def __init__(self, master, text, command, kind='normal', width=160, height=44, font_size=10):
        super().__init__(master, width=width, height=height, bg=widget_background(master),
                         bd=0, highlightthickness=0, takefocus=True, cursor='hand2')
        self.label, self.command, self.kind = text, command, kind
        self.font_size = font_size
        self.pressed = False
        self.bind('<Configure>', lambda _: self.draw())
        self.bind('<ButtonPress-1>', self.press)
        self.bind('<ButtonRelease-1>', self.release)
        self.bind('<KeyPress-space>', self.press)
        self.bind('<KeyRelease-space>', self.release)
        self.bind('<Return>', lambda _: self.invoke())
        self.bind('<FocusIn>', lambda _: self.draw())
        self.bind('<FocusOut>', lambda _: self.draw())
        self.draw()

    def configure(self, cnf=None, **kwargs):
        text = kwargs.pop('text', None)
        if text is not None:
            self.label = text
        result = super().configure(cnf, **kwargs)
        if hasattr(self, 'label') and (text is not None or 'state' in kwargs or 'width' in kwargs):
            if kwargs.get('state') == 'disabled':
                self.pressed = False
            self.draw()
        return result

    config = configure

    def instate(self, states):
        disabled = self.cget('state') == 'disabled'
        return all(disabled if state == 'disabled' else not disabled for state in states)

    def press(self, event=None):
        if self.cget('state') != 'disabled':
            self.focus_set()
            self.pressed = True
            self.draw()
        return 'break'

    def release(self, event=None):
        active = self.pressed
        self.pressed = False
        self.draw()
        inside = event is None or getattr(event, 'keysym', '') == 'space' or (
            0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height())
        if active and inside:
            self.invoke()
        return 'break'

    def invoke(self):
        if self.cget('state') != 'disabled':
            return self.command()

    def draw(self):
        self.delete('all')
        width = max(self.winfo_width(), int(self.cget('width')))
        height = max(self.winfo_height(), int(self.cget('height')))
        fill = {'start': ACCENT, 'stop': '#FF927F', 'normal': PANEL, 'tab': HERO}.get(self.kind, PANEL)
        disabled = self.cget('state') == 'disabled'
        if disabled:
            fill = '#292338'
        fg = MUTED if disabled else '#171426' if self.kind in ('start', 'stop') else INK
        offset = 3 if self.pressed else 0
        self.create_polygon(6, 4, width-6, 4, width-6, 8, width-2, 8, width-2, height-4,
                            width-6, height-4, width-6, height, 6, height, 6, height-4, 2, height-4, 2, 8, 6, 8,
                            fill='#0D0B15', outline='')
        self.create_polygon(6, offset, width-10, offset, width-10, 4+offset, width-6, 4+offset,
                            width-6, height-10+offset, width-10, height-10+offset, width-10, height-6+offset,
                            6, height-6+offset, 6, height-10+offset, 2, height-10+offset, 2, 4+offset, 6, 4+offset,
                            fill=fill, outline=INK if self.focus_get() == self and not disabled else BORDER, width=1)
        self.create_line(9, 3+offset, width-13, 3+offset, fill='#B7F2C6' if self.kind == 'start' else '#7A5B8B')
        self.create_text(width/2-2, height/2-4+offset, text=self.label, fill=fg,
                         font=(DISPLAY, self.font_size), width=width-16)


class PixelSlider(tk.Canvas):
    """Native canvas slider: visual trace only; commands fire on release."""
    def __init__(self, master, variable, from_=0, to=31, orient='horizontal', command=None, length=180):
        self.variable, self.minimum, self.maximum = variable, from_, to
        self.orient, self.command = orient, command
        self.dragging = False
        super().__init__(master, bg=widget_background(master), width=length if orient == 'horizontal' else 38,
                         height=34 if orient == 'horizontal' else length, bd=0, highlightthickness=0, takefocus=True)
        self.bind('<Configure>', lambda _: self.draw())
        self.bind('<ButtonPress-1>', self.press)
        self.bind('<B1-Motion>', self.move)
        self.bind('<ButtonRelease-1>', self.release)
        self.bind('<KeyPress>', self.key)
        self.bind('<KeyRelease>', self.key_release)
        self.trace = variable.trace_add('write', lambda *_: self.draw())
        self.bind('<Destroy>', self.dispose)

    def dispose(self, event):
        if event.widget == self:
            self.variable.trace_remove('write', self.trace)

    def configure(self, cnf=None, **kwargs):
        for name, target in (('from_', 'minimum'), ('to', 'maximum')):
            if name in kwargs:
                setattr(self, target, kwargs.pop(name))
        result = super().configure(cnf, **kwargs)
        if hasattr(self, 'trace'):
            self.draw()
        return result

    config = configure

    def instate(self, states):
        return all((self.cget('state') == 'disabled') == (state == 'disabled') for state in states)

    def press(self, event):
        if self.cget('state') == 'disabled':
            return
        self.focus_set(); self.dragging = True; self.move(event)

    def move(self, event):
        if not self.dragging or self.cget('state') == 'disabled':
            return
        fraction = ((event.x-8)/max(1, self.winfo_width()-16) if self.orient == 'horizontal'
                    else (event.y-8)/max(1, self.winfo_height()-16))
        self.variable.set(round(self.minimum + max(0, min(1, fraction)) * (self.maximum-self.minimum)))

    def release(self, event=None):
        active, self.dragging = self.dragging, False
        if active and self.cget('state') != 'disabled' and self.command:
            self.command()

    def key(self, event):
        if self.cget('state') == 'disabled' or event.keysym not in ('Left','Right','Up','Down'):
            return
        delta = 1 if event.keysym in ('Right','Up') else -1
        self.variable.set(max(min(self.minimum,self.maximum), min(max(self.minimum,self.maximum), self.variable.get()+delta)))
        self.dragging = True
        return 'break'

    def key_release(self, event):
        if event.keysym in ('Left','Right','Up','Down'):
            self.release()

    def draw(self):
        if not self.winfo_exists():
            return
        self.delete('all')
        disabled = self.cget('state') == 'disabled'
        color = BORDER if disabled else ACCENT
        fraction = max(0,min(1,(self.variable.get()-self.minimum)/(self.maximum-self.minimum or 1)))
        width, height = self.winfo_width(), self.winfo_height()
        if self.orient == 'horizontal':
            self.create_rectangle(7, 9, width-7, height-9, fill=HERO, outline=BORDER, width=2)
            for i in range(12):
                x = 9 + i*(width-18)/12
                self.create_rectangle(x,11,x+(width-18)/12-2,height-11,
                                      fill=color if (i+0.5)/12<=fraction else PANEL, outline='')
            x=8+fraction*(width-16)
            self.create_rectangle(x-5,5,x+5,height-5,fill=MUTED if disabled else INK,outline=HERO,width=2)
        else:
            x=width/2
            self.create_rectangle(x-5,7,x+5,height-7,fill=HERO,outline=BORDER)
            for i in range(10):
                y=8+i*(height-16)/10
                self.create_rectangle(x-4,y,x+4,y+(height-16)/10-2,fill=color if i/10>=fraction else PANEL,outline='')
            y=8+fraction*(height-16)
            self.create_rectangle(x-10,y-5,x+10,y+5,fill=MUTED if disabled else INK,outline=HERO,width=2)
