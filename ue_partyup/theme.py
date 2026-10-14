"""PartyUp's local, dependency-free control-deck visual theme.

Only presentation is configured here; there is no Bluetooth I/O or startup action.
"""
import ctypes
import sys
import tkinter as tk
from tkinter import ttk

BG = '#0C121B'
SURFACE = '#15202E'
PANEL = '#1B2939'
HERO = '#111C2A'
INPUT = '#0F1926'
BORDER = '#314154'
INK = '#EDF6FA'
MUTED = '#A7B8C7'
ACCENT = '#47DFC2'
ACCENT_DARK = '#071C1D'
DANGER = '#F47D83'
DANGER_DARK = '#351D2A'
AMBER = '#E8B76B'


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
    style.configure('HeroTitle.TLabel', background=HERO, foreground=INK, font=('Segoe UI Semibold', 27))
    style.configure('HeroSub.TLabel', background=HERO, foreground=MUTED, font=('Segoe UI', 10))
    style.configure('Kicker.TLabel', background=HERO, foreground=ACCENT, font=('Segoe UI Semibold', 9))
    style.configure('HeroBadge.TLabel', background=PANEL, foreground=ACCENT, font=('Segoe UI Semibold', 9),
                    padding=(13, 9))
    style.configure('Section.TLabel', background=SURFACE, foreground=INK, font=('Segoe UI Semibold', 12))
    style.configure('Muted.TLabel', background=SURFACE, foreground=MUTED, font=('Segoe UI', 9))
    style.configure('Micro.TLabel', background=SURFACE, foreground=ACCENT, font=('Segoe UI Semibold', 9))
    style.configure('ToolbarTitle.TLabel', background=PANEL, foreground=INK, font=('Segoe UI Semibold', 10))
    style.configure('ToolbarMuted.TLabel', background=PANEL, foreground=MUTED, font=('Segoe UI', 9))
    style.configure('Status.TLabel', background=PANEL, foreground=INK, font=('Segoe UI', 10), padding=(12, 10))
    style.configure('Footer.TLabel', background=BG, foreground=MUTED, font=('Segoe UI', 9))
    style.configure('Count.TLabel', background=PANEL, foreground=ACCENT, font=('Segoe UI Semibold', 10),
                    padding=(12, 8))
    style.configure('GroupState.TLabel', background=PANEL, foreground=MUTED,
                    font=('Segoe UI Semibold', 10), padding=(12, 8))

    style.configure('TLabelframe', background=SURFACE, borderwidth=1,
                    relief='solid', bordercolor=BORDER)
    style.configure('TLabelframe.Label', background=SURFACE, foreground=INK,
                    font=('Segoe UI Semibold', 10))
    style.configure('TSeparator', background=BORDER)

    style.configure('TButton', background=PANEL, foreground=INK, bordercolor=BORDER,
                    darkcolor=PANEL, lightcolor=PANEL, borderwidth=1, relief='flat',
                    focuscolor=ACCENT, padding=(14, 9), font=('Segoe UI Semibold', 10))
    style.map('TButton',
              background=[('disabled', SURFACE), ('pressed', '#32485A'), ('active', '#2B4154')],
              foreground=[('disabled', '#65788A'), ('active', INK)],
              bordercolor=[('disabled', '#243243'), ('active', '#506779')])
    style.configure('Quiet.TButton', background=SURFACE, foreground=INK, bordercolor=BORDER,
                    padding=(14, 9), font=('Segoe UI Semibold', 10))
    style.map('Quiet.TButton',
              background=[('disabled', SURFACE), ('pressed', PANEL), ('active', PANEL)],
              foreground=[('disabled', '#65788A'), ('active', INK)])
    style.configure('Primary.TButton', background=ACCENT, foreground=ACCENT_DARK,
                    bordercolor=ACCENT, padding=(18, 10), font=('Segoe UI Semibold', 10))
    style.map('Primary.TButton',
              background=[('disabled', '#24463F'), ('pressed', '#28B69A'), ('active', '#73EAD4')],
              foreground=[('disabled', '#72948F'), ('active', ACCENT_DARK)],
              bordercolor=[('disabled', '#24463F'), ('active', '#73EAD4')])
    style.configure('Danger.TButton', background=DANGER_DARK, foreground='#FFC8CB',
                    bordercolor='#915761', padding=(17, 10), font=('Segoe UI Semibold', 10))
    style.map('Danger.TButton',
              background=[('disabled', SURFACE), ('pressed', '#803E50'), ('active', '#603343')],
              foreground=[('disabled', '#65788A'), ('active', '#FFFFFF')])

    style.configure('TCheckbutton', background=SURFACE, foreground=INK, padding=(4, 6),
                    font=('Segoe UI', 10), indicatorcolor=INPUT)
    style.map('TCheckbutton',
              background=[('active', SURFACE), ('disabled', SURFACE)],
              foreground=[('disabled', '#738495'), ('active', INK)],
              indicatorcolor=[('selected', ACCENT), ('disabled', '#405366')])
    style.configure('Toolbar.TCheckbutton', background=PANEL, foreground=MUTED, padding=(4, 7))
    style.map('Toolbar.TCheckbutton',
              background=[('active', PANEL), ('disabled', PANEL)],
              foreground=[('active', INK), ('disabled', '#738495')])

    style.configure('TEntry', background=INPUT, fieldbackground=INPUT, foreground=INK,
                    insertcolor=INK, bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER,
                    relief='flat', padding=(8, 7))
    style.map('TEntry', foreground=[('disabled', '#80909C')],
              fieldbackground=[('disabled', SURFACE)])
    style.configure('TCombobox', background=PANEL, fieldbackground=INPUT, foreground=INK,
                    arrowcolor=ACCENT, insertcolor=INK, selectbackground='#335F65',
                    selectforeground=INK, bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER,
                    relief='flat', padding=(8, 7))
    style.map('TCombobox',
              fieldbackground=[('readonly', INPUT), ('disabled', SURFACE)],
              foreground=[('readonly', INK), ('disabled', '#738495')],
              arrowcolor=[('disabled', '#63798D'), ('active', ACCENT)])
    root.option_add('*TCombobox*Listbox.background', INPUT)
    root.option_add('*TCombobox*Listbox.foreground', INK)
    root.option_add('*TCombobox*Listbox.selectBackground', '#27685F')
    root.option_add('*TCombobox*Listbox.selectForeground', '#FFFFFF')

    style.configure('TNotebook', background=SURFACE, borderwidth=0, bordercolor=SURFACE,
                    lightcolor=SURFACE, darkcolor=SURFACE, tabmargins=(0, 5, 0, 0))
    style.configure('TNotebook.Tab', background=BG, foreground=MUTED, borderwidth=0,
                    bordercolor=BG, focuscolor=BG, lightcolor=BG, darkcolor=BG,
                    relief='flat', padding=(22, 12),
                    font=('Segoe UI Semibold', 10))
    style.map('TNotebook.Tab', background=[('selected', PANEL), ('active', PANEL)],
              foreground=[('selected', ACCENT), ('active', INK)],
              padding=[('selected', (22, 12))])
    style.configure('Treeview', background=INPUT, fieldbackground=INPUT, foreground=INK,
                    borderwidth=0, relief='flat', font=('Segoe UI', 10), rowheight=34)
    style.configure('Treeview.Heading', background=PANEL, foreground=MUTED,
                    font=('Segoe UI Semibold', 9), borderwidth=0, relief='flat',
                    padding=(9, 10))
    style.map('Treeview', background=[('selected', '#275A59')],
              foreground=[('selected', '#FFFFFF')])
    style.map('Treeview.Heading', background=[('active', '#2E4153')])
    style.configure('TScale', background=SURFACE, troughcolor=INPUT, sliderrelief='flat',
                    borderwidth=0, lightcolor=ACCENT, darkcolor=ACCENT)
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
