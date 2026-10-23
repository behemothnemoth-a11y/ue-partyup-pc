"""House Party presentation for the complete existing control pages; no device I/O."""
import tkinter as tk
from tkinter import ttk
from .house_widgets import DISPLAY, PocketButton
from .theme import HERO, SURFACE, PANEL, INK, MUTED, ACCENT, BORDER


def style_control_pages(root):
    style = ttk.Style(root)
    for name, size in (('Section.TLabel', 14), ('TLabelframe.Label', 10),
                       ('ToolbarTitle.TLabel', 10), ('Count.TLabel', 9),
                       ('GroupState.TLabel', 9), ('Value.TLabel', 11)):
        style.configure(name, font=(DISPLAY, size))
    style.configure('Volume.TLabel', font=(DISPLAY, 24), foreground=INK)
    style.configure('TNotebook.Tab', font=(DISPLAY, 9), padding=(16, 10))
    style.map('TNotebook.Tab', padding=[('selected', (16, 10))])
    style.configure('TLabelframe', borderwidth=2, bordercolor=BORDER, relief='solid')
    style.configure('Treeview.Heading', font=(DISPLAY, 8))


def install_control_header(app):
    """Retain every original page/widget under a matching House navigation shell."""
    shell = app.legacy_shell
    original_header = shell.winfo_children()[0]
    original_header.pack_forget()
    toolbar = shell.winfo_children()[1]
    header = tk.Frame(shell, bg=HERO, padx=12, pady=8)
    header.pack(before=toolbar, fill='x')
    tk.Label(header, text='⌂ PARTYUP', bg=HERO, fg=INK,
             font=(DISPLAY, 25)).pack(side='left')
    tk.Label(header, text='Music in every room', bg=HERO, fg=INK,
             font=('Segoe UI', 11)).pack(side='left', padx=18)
    tk.Label(header, text='PRIVATE PREVIEW', bg=HERO, fg=ACCENT,
             font=(DISPLAY, 10)).pack(side='right', padx=10)
    navigation = tk.Frame(shell, bg=shell.winfo_toplevel().cget('bg'), pady=7)
    navigation.pack(before=toolbar, fill='x')
    app.control_navigation = {}
    for name, page in (('House', None), ('Sound', 'Sound'), ('Settings', 'Speaker')):
        command = app.return_house if page is None else lambda page=page: app.open_advanced(page)
        button = PocketButton(navigation, name, command, 'tab', 135, 40)
        button.pack(side='left', padx=(0, 6))
        app.register(button)
        app.control_navigation[name] = button
    help_button=PocketButton(navigation,'Help',app.open_about,'normal',85,40)
    help_button.pack(side='right');app.register(help_button)
    banner = tk.Frame(shell, bg=PANEL, padx=16, pady=8,
                      highlightthickness=1, highlightbackground=BORDER)
    banner.pack(before=toolbar, fill='x', pady=(0, 7))
    app.control_page_title = tk.StringVar(value='SOUND STUDIO')
    app.control_page_hint = tk.StringVar()
    words = tk.Frame(banner, bg=PANEL)
    words.pack(side='left', fill='x', expand=True)
    tk.Label(words, textvariable=app.control_page_title, bg=PANEL, fg=INK,
             font=(DISPLAY, 19)).pack(anchor='w')
    tk.Label(words, textvariable=app.control_page_hint, bg=PANEL, fg=MUTED,
             font=('Segoe UI', 10)).pack(anchor='w', pady=(5, 0))
    app.control_portrait = app.art.photo('speaker', 125)
    tk.Label(banner, image=app.control_portrait, bg=PANEL).pack(side='right', padx=8)
    # Keep the target picker/read/experimental toggle and full notebook intact.
    # The old duplicate branding is hidden, not its functionality.
    style_control_pages(app.root)


def update_control_navigation(app):
    if not hasattr(app, 'control_navigation'):
        return
    current = app.notebook.select()
    name = next((name for name, view in app.tab_viewports.items() if str(view) == current), '')
    active = 'Sound' if name == 'Sound' else 'Settings'
    for key, button in app.control_navigation.items():
        button.kind = 'start' if key == active else 'tab'
        button.draw()
    titles = {'Sound': ('SOUND STUDIO', 'Volume, EQ and your saved sound memories.'),
              'Speaker': ('SPEAKER SETTINGS', 'Name, power, sleep and playback controls.'),
              'PartyUp settings': ('PARTY PREFERENCES', 'Group behavior, discovery and identification.'),
              'Group': ('PARTY CREW', 'Choose your main speaker and up to nine guests.'),
              'Guide': ('FIELD GUIDE', 'Control coverage and model-specific limits.')}
    title, hint = titles.get(name, ('HOUSE PARTY', 'Your complete speaker controls.'))
    app.control_page_title.set(title)
    app.control_page_hint.set(hint)


def build_sound_studio(app, tab):
    """Compose the same sound controls into two console panels, preserving callbacks."""
    ttk.Label(tab, textvariable=app.sound_hint, style='Micro.TLabel',
              wraplength=980).pack(anchor='w', pady=(0, 10))
    app.build_tuning(tab)
    panels = ttk.Frame(tab)
    panels.pack(fill='x')
    panels.columnconfigure(0, weight=1, minsize=265)
    panels.columnconfigure(1, weight=3, minsize=590)
    volume = ttk.LabelFrame(panels, text='Speaker volume', padding=14)
    volume.grid(row=0, column=0, sticky='nsew', padx=(0, 12))
    app.volume_text = tk.StringVar(value='Not read')
    ttk.Label(volume, textvariable=app.volume_text, style='Volume.TLabel').pack(anchor='w', pady=(5, 12))
    app.volume_scale = app.register(app.scale(volume, from_=0, to=31, variable=app.volume), 'volume')
    app.volume_scale.pack(fill='x', pady=(0, 5))
    app.volume_scale.bind('<ButtonRelease-1>', app.on_volume_release, add='+')
    app.volume_scale.bind('<KeyRelease>', app.on_volume_release, add='+')
    app.volume.trace_add('write', lambda *_: app.update_volume_label())
    ends = ttk.Frame(volume); ends.pack(fill='x')
    ttk.Label(ends, text='Quiet', style='Muted.TLabel').pack(side='left')
    ttk.Label(ends, text='Loud', style='Muted.TLabel').pack(side='right')
    app.button(volume, 'Set volume', app.apply_volume, 'volume').pack(fill='x', pady=(12, 10))
    ttk.Label(volume, text='Release to send one change.\nThe result is checked by readback.',
              style='Muted.TLabel', wraplength=250).pack(anchor='w')
    ttk.Separator(volume).pack(fill='x', pady=15)
    app.register(ttk.Checkbutton(volume, text='Outdoor mode', variable=app.outdoor), 'outdoor').pack(anchor='w')
    app.button(volume, 'Apply outdoor mode',
               lambda: app.setting('set_outdoor', app.outdoor.get()), 'outdoor').pack(fill='x', pady=(5, 0))

    eq = ttk.LabelFrame(panels, text='Shape your sound', padding=14)
    eq.grid(row=0, column=1, sticky='nsew')
    presets = ttk.Frame(eq); presets.pack(fill='x')
    ttk.Label(presets, text='Preset').pack(side='left', padx=(0, 8))
    app.eq_combo = app.register(ttk.Combobox(presets, state='readonly', width=22), 'eq', state='readonly')
    app.eq_combo.pack(side='left', fill='x', expand=True, padx=(0, 10))
    app.button(presets, 'Apply EQ', app.apply_eq, 'eq').pack(side='right')
    bands = ttk.Frame(eq); bands.pack(fill='x', pady=(12, 7))
    for index, (value, name) in enumerate(zip(app.eq_bands, ('Low', 'Low-mid', 'Mid', 'High-mid', 'High'))):
        box = ttk.Frame(bands); box.pack(side='left', fill='x', expand=True)
        ttk.Label(box, text=name, style='Muted.TLabel').pack()
        scale = app.register(app.scale(box, from_=127, to=-128, orient='vertical',
                                       length=130, variable=value), 'eq_band')
        scale.pack(pady=5)
        scale.bind('<ButtonRelease-1>', app.on_eq_band_release, add='+')
        scale.bind('<KeyRelease>', app.on_eq_band_release, add='+')
        app.eq_band_scales.append(scale)
        text = tk.StringVar(value='0')
        value.trace_add('write', lambda *_, value=value, text=text: text.set(str(round(value.get()))))
        ttk.Label(box, textvariable=text, style='Value.TLabel').pack()
    memories = ttk.Frame(eq); memories.pack(fill='x', pady=(7, 0))
    ttk.Label(memories, text='EQ memory').pack(side='left', padx=(0, 8))
    app.memory_combo = app.register(ttk.Combobox(memories, width=20, values=list(app.eq_profiles.load())))
    app.memory_combo.pack(side='left', fill='x', expand=True)
    actions = ttk.Frame(eq); actions.pack(fill='x', pady=(7, 0))
    app.button(actions, 'Save', app.save_eq_memory, 'eq').pack(side='left')
    app.button(actions, 'Load into sliders', app.load_eq_memory, 'eq').pack(side='left', padx=7)
    app.button(actions, 'Delete', app.delete_eq_memory).pack(side='left')
    ttk.Label(tab, text='Custom EQ applies on release; presets use Apply EQ. Memory loading only stages the sliders. '
              'Band values are speaker levels, not decibels.', style='Muted.TLabel',
              wraplength=980).pack(anchor='w', pady=(10, 0))
