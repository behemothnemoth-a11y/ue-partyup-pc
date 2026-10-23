"""PartyUp's local, dependency-free control-deck visual theme.

Pixel-console presentation is configured here; there is no Bluetooth I/O or startup action.
"""
import ctypes
import sys
import tkinter as tk
from tkinter import ttk

BG = '#12101D'
SURFACE = '#211C32'
PANEL = '#302842'
HERO = '#171426'
INPUT = '#181423'
BORDER = '#58446E'
INK = '#FFF1D5'
MUTED = '#BEB0CE'
ACCENT = '#A8EDBD'
ACCENT_DARK = '#16241E'
DANGER = '#FF9B96'
DANGER_DARK = '#442A40'
AMBER = '#FFD080'


def apply_theme(root):
    """Apply one consistent palette without external packages or network access."""
    root.configure(bg=BG)
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('.', font=('Segoe UI', 10), background=SURFACE, foreground=INK)
    style.configure('TFrame', background=SURFACE)
    style.configure('Shell.TFrame', background=BG)
    style.configure('Hero.TFrame', background=HERO)
    style.configure('Toolbar.TFrame', background=PANEL)
    style.configure('Actions.TFrame', background=SURFACE)

    style.configure('TLabel', background=SURFACE, foreground=INK, font=('Segoe UI', 10))
    style.configure('HeroTitle.TLabel', background=HERO, foreground=INK, font=('Consolas', 24))
    style.configure('HeroSub.TLabel', background=HERO, foreground=MUTED, font=('Segoe UI', 10))
    style.configure('Kicker.TLabel', background=HERO, foreground=ACCENT, font=('Consolas', 9))
    style.configure('HeroBadge.TLabel', background=PANEL, foreground=ACCENT, font=('Consolas', 9),
                    padding=(13, 9))
    style.configure('Section.TLabel', background=SURFACE, foreground=INK, font=('Consolas', 12))
    style.configure('Muted.TLabel', background=SURFACE, foreground=MUTED, font=('Segoe UI', 9))
    style.configure('Micro.TLabel', background=SURFACE, foreground=ACCENT, font=('Consolas', 9))
    style.configure('ToolbarTitle.TLabel', background=PANEL, foreground=INK, font=('Consolas', 10))
    style.configure('ToolbarMuted.TLabel', background=PANEL, foreground=MUTED, font=('Segoe UI', 9))
    style.configure('Status.TLabel', background=PANEL, foreground=INK, font=('Segoe UI', 10), padding=(12, 10))
    style.configure('Footer.TLabel', background=BG, foreground=MUTED, font=('Segoe UI', 9))
    style.configure('Count.TLabel', background=PANEL, foreground=ACCENT, font=('Consolas', 10),
                    padding=(12, 8))
    style.configure('GroupState.TLabel', background=PANEL, foreground=MUTED,
                    font=('Consolas', 10), padding=(12, 8))
    style.configure('Volume.TLabel', background=SURFACE, foreground=ACCENT,
                    font=('Consolas', 30))
    style.configure('Value.TLabel', background=SURFACE, foreground=INK,
                    font=('Consolas', 11), padding=(9, 5))

    style.configure('TLabelframe', background=SURFACE, borderwidth=2,
                    relief='solid', bordercolor=BORDER)
    style.configure('TLabelframe.Label', background=SURFACE, foreground=INK,
                    font=('Consolas', 10))
    style.configure('TSeparator', background=BORDER)

    style.configure('TButton', background=PANEL, foreground=INK, bordercolor=BORDER,
                    darkcolor=PANEL, lightcolor=PANEL, borderwidth=2, relief='raised',
                    focuscolor=ACCENT, padding=(14, 9), font=('Consolas', 10))
    style.map('TButton',
              background=[('disabled', SURFACE), ('pressed', '#55406D'), ('active', '#443455')],
              foreground=[('disabled', '#887B98'), ('active', INK)],
              bordercolor=[('disabled', '#352B46'), ('active', '#A28ABB')])
    style.configure('Quiet.TButton', background=SURFACE, foreground=INK, bordercolor=BORDER,
                    padding=(14, 9), font=('Consolas', 10))
    style.map('Quiet.TButton',
              background=[('disabled', SURFACE), ('pressed', PANEL), ('active', PANEL)],
              foreground=[('disabled', '#887B98'), ('active', INK)])
    style.configure('Primary.TButton', background=ACCENT, foreground=ACCENT_DARK,
                    bordercolor=ACCENT, padding=(18, 10), font=('Consolas', 10))
    style.map('Primary.TButton',
              background=[('disabled', '#344C42'), ('pressed', '#75CB9B'), ('active', '#C1F7D0')],
              foreground=[('disabled', '#8EAB9A'), ('active', ACCENT_DARK)],
              bordercolor=[('disabled', '#344C42'), ('active', '#C1F7D0')])
    style.configure('Danger.TButton', background=DANGER_DARK, foreground='#FFC8CB',
                    bordercolor='#915761', padding=(17, 10), font=('Consolas', 10))
    style.map('Danger.TButton',
              background=[('disabled', SURFACE), ('pressed', '#8B4A63'), ('active', '#693A54')],
              foreground=[('disabled', '#887B98'), ('active', '#FFFFFF')])

    style.configure('TCheckbutton', background=SURFACE, foreground=INK, padding=(4, 6),
                    font=('Segoe UI', 10), indicatorcolor=INPUT)
    style.map('TCheckbutton',
              background=[('active', SURFACE), ('disabled', SURFACE)],
              foreground=[('disabled', '#9685A5'), ('active', INK)],
              indicatorcolor=[('selected', ACCENT), ('disabled', '#55466A')])
    style.configure('Toolbar.TCheckbutton', background=PANEL, foreground=MUTED, padding=(4, 7))
    style.map('Toolbar.TCheckbutton',
              background=[('active', PANEL), ('disabled', PANEL)],
              foreground=[('active', INK), ('disabled', '#9685A5')])

    style.configure('TEntry', background=INPUT, fieldbackground=INPUT, foreground=INK,
                    insertcolor=INK, bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER,
                    relief='flat', padding=(8, 7))
    style.map('TEntry', foreground=[('disabled', '#9685A5')],
              fieldbackground=[('disabled', SURFACE)])
    style.configure('TCombobox', background=PANEL, fieldbackground=INPUT, foreground=INK,
                    arrowcolor=ACCENT, insertcolor=INK, selectbackground='#58446E',
                    selectforeground=INK, bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER,
                    relief='flat', padding=(8, 7))
    style.map('TCombobox',
              fieldbackground=[('readonly', INPUT), ('disabled', SURFACE)],
              foreground=[('readonly', INK), ('disabled', '#9685A5')],
              arrowcolor=[('disabled', '#9685A5'), ('active', ACCENT)])
    root.option_add('*TCombobox*Listbox.background', INPUT)
    root.option_add('*TCombobox*Listbox.foreground', INK)
    root.option_add('*TCombobox*Listbox.selectBackground', '#58446E')
    root.option_add('*TCombobox*Listbox.selectForeground', '#FFFFFF')

    style.configure('TNotebook', background=SURFACE, borderwidth=0, bordercolor=SURFACE,
                    lightcolor=SURFACE, darkcolor=SURFACE, tabmargins=(0, 5, 0, 0))
    style.configure('TNotebook.Tab', background=BG, foreground=MUTED, borderwidth=0,
                    bordercolor=BG, focuscolor=BG, lightcolor=BG, darkcolor=BG,
                    relief='flat', padding=(20, 10),
                    font=('Consolas', 10))
    style.map('TNotebook.Tab', background=[('selected', PANEL), ('active', PANEL)],
              foreground=[('selected', ACCENT), ('active', INK)],
              padding=[('selected', (20, 10))])
    # Remove clam's raised tab outlines; selection is communicated by color.
    style.layout('TNotebook.Tab', [('Notebook.tab', {'sticky': 'nswe', 'children': [
        ('Notebook.padding', {'side': 'top', 'sticky': 'nswe', 'children': [
            ('Notebook.label', {'side': 'top', 'sticky': ''})]})]})])
    style.configure('Treeview', background=INPUT, fieldbackground=INPUT, foreground=INK,
                    borderwidth=0, relief='flat', font=('Segoe UI', 10), rowheight=40)
    style.configure('Treeview.Heading', background=PANEL, foreground=MUTED,
                    font=('Consolas', 9), borderwidth=0, relief='flat',
                    padding=(9, 10))
    style.map('Treeview', background=[('selected', '#58446E')],
              foreground=[('selected', '#FFFFFF')])
    style.map('Treeview.Heading', background=[('active', '#443455')])
    style.layout('Treeview', [('Treeview.treearea', {'sticky': 'nswe'})])
    style.configure('TScale', background=ACCENT, troughcolor=INPUT, sliderrelief='flat',
                    borderwidth=0, bordercolor=ACCENT, lightcolor=ACCENT, darkcolor=ACCENT)
    style.map('TScale', background=[('disabled', BORDER), ('active', '#D5F7BC')])
    style.configure('Vertical.TScrollbar', background=PANEL, troughcolor=INPUT,
                    bordercolor=INPUT, arrowcolor=MUTED, relief='flat')

    # Windows 11/10 supports this decoration hint; ignore unsupported versions.
    if sys.platform == 'win32':
        def dark_caption():
            try:
                handle = ctypes.c_void_p(root.winfo_id())
                value = ctypes.c_int(1)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(handle, 20, ctypes.byref(value),
                                                          ctypes.sizeof(value))
            except (AttributeError, OSError):
                pass
        root.after(30, dark_caption)
    return style



class ScrollableTab(ttk.Frame):
    """Keep setting panels accessible when the window is short or scaled up.

    The tab's viewport has a bounded preferred size; it never makes the whole
    window taller than the available screen. The scrollbar and mouse wheel can
    reach every card, including those below the fold.
    """

    def __init__(self, master):
        super().__init__(master, style='TFrame')
        self.canvas = tk.Canvas(self, bg=SURFACE, bd=0, highlightthickness=0,
                                height=220, yscrollincrement=20)
        self.scrollbar = ttk.Scrollbar(self, orient='vertical',
                                      command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        # A fixed footer keeps critical Group actions visible while cards scroll.
        self.footer = ttk.Frame(self, style='TFrame')
        self.footer.pack(side='bottom', fill='x')
        self.scrollbar.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)
        self.content = ttk.Frame(self.canvas, padding=(14, 13, 14, 12))
        self._window = self.canvas.create_window((0, 0), window=self.content,
                                                  anchor='nw')
        self.content.bind('<Configure>', self._recalculate)
        self.canvas.bind('<Configure>', self._recalculate)

    def _recalculate(self, event=None):
        self.canvas.itemconfigure(self._window, width=self.canvas.winfo_width())
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def _on_wheel(self, event):
        # Only scroll the current tab when the pointer is over its content.
        if self.winfo_ismapped() and event.delta:
            lines = max(1, abs(int(event.delta / 120)))
            self.canvas.yview_scroll((-1 if event.delta > 0 else 1) * lines,
                                     'units')
            return 'break'

    def enable_wheel(self):
        """Bind current descendants without swallowing list/tree scrolling."""
        def visit(widget):
            if isinstance(widget, (tk.Listbox, tk.Text, ttk.Treeview,
                                   ttk.Combobox, ttk.Scale)):
                return
            widget.bind('<MouseWheel>', self._on_wheel, add='+')
            for child in widget.winfo_children():
                visit(child)
        visit(self.content)
        self.canvas.bind('<MouseWheel>', self._on_wheel, add='+')
