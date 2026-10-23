"""Native private-preview interface; speaker I/O runs outside the Tk thread."""
import asyncio
from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
from .controller import discover
from .groups import GroupManager
from . import __version__
from .theme import apply_theme, ScrollableTab, INPUT, INK, MUTED, ACCENT, BORDER
from .pixel_art import header_art, PixelGroupMap
from .profiles import EQProfiles
from .feature_guide import FEATURE_GUIDE, UE_GUIDE


from .runtime import data_directory
DATA = data_directory()
MAX_LOG_LINES = 500
MAX_EVENTS_PER_TICK = 32
IDLE_POLL_MS = 300
BUSY_POLL_MS = 60
SETTING_READBACK = {
    'set_volume': 'volume', 'set_eq': 'eq', 'set_outdoor': 'outdoor',
    'set_sleep_timer': 'sleep_timer', 'set_remote_activation': 'remote_activation',
    'set_sticky': 'sticky', 'set_public': 'public',
}
ACK_ONLY_ACTIONS = frozenset(('playback', 'identify', 'sync_volume',
                              'announce_battery', 'set_stereo_balance'))


def load_selection(path):
    """Accept the older host/guest file and the current host/guests file."""
    try:
        saved = json.loads(path.read_text(encoding='utf-8'))
        host = saved.get('host')
        guests = saved.get('guests', [saved['guest']] if 'guest' in saved else [])
        if not isinstance(host, int) or isinstance(host, bool) or not 0 < host < 1 << 48:
            return None, []
        if not isinstance(guests, list):
            return host, []
        valid = [value for value in guests if isinstance(value, int) and not isinstance(value, bool)
                 and 0 < value < 1 << 48 and value != host]
        return host, list(dict.fromkeys(valid))[:9]
    except (OSError, ValueError, TypeError, AttributeError):
        return None, []


def parse_mac(value):
    compact = value.replace(':', '').replace('-', '').replace(' ', '')
    if len(compact) != 12:
        raise ValueError('Choose a PC Bluetooth adapter or enter its six-byte address.')
    try:
        result = int(compact, 16)
    except ValueError:
        raise ValueError('Bluetooth addresses contain twelve hexadecimal digits.') from None
    if not result:
        raise ValueError('The Bluetooth address cannot be all zeros.')
    return result


def format_value(value):
    if value is None:
        return 'Not available'
    if hasattr(value, 'percent') and hasattr(value, 'charging_state'):
        level = f'{value.percent}%' if value.percent is not None else 'Charge unknown'
        return f'{level} · {value.charging_state}'
    if isinstance(value, dict):
        return ' · '.join(f'{key}: {item}' for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return ', '.join(map(str, value))
    return str(value)


from .tuning_ui import TuningUI
from .tuning import TuningState


class PartyUpApp(TuningUI):
    def __init__(self, root, data_path=DATA):
        self.root, self.data_path = root, data_path
        self.events = queue.Queue()
        self.busy = False
        self.tuning = TuningState()
        self.speakers = []
        self.guest_choices = []
        self.member_speakers = {}
        self.snapshots = {}
        self.radios = []
        self.selected_snapshot = {}
        self.eq_choices = []
        self.eq_profiles = EQProfiles(data_path / 'eq-memories.json')
        self.dragged_speaker = None
        self.eq_band_scales = []
        self.sound_requested = set()
        self.sound_hint = tk.StringVar(value='Open Sound to read controls for the selected speaker.')
        self.controls = []
        self.feature_widgets = {}
        self.status = tk.StringVar(value='Find paired speakers to begin.')
        self.group_count = tk.StringVar(value='0 guests selected · maximum 9')
        self.group_status = tk.StringVar(value='STATUS NOT CHECKED')
        self.device_count = tk.StringVar(value='AWAITING DISCOVERY')
        self.device_summary = tk.StringVar(value='Choose a speaker, then read its controls.')
        self.experimental = tk.BooleanVar(value=False)
        self.outdoor = tk.BooleanVar(value=False)
        self.remote_activation = tk.BooleanVar(value=False)
        self.sticky = tk.BooleanVar(value=False)
        self.public = tk.BooleanVar(value=False)
        self.silent_power = tk.BooleanVar(value=False)
        self.experimental_balance = tk.BooleanVar(value=False)
        self.experimental_wake = tk.BooleanVar(value=False)
        self.volume = tk.DoubleVar(value=0)
        self.balance = tk.DoubleVar(value=0)
        self.eq_bands = [tk.DoubleVar(value=0) for _ in range(5)]
        self.saved_host, self.saved_guests = load_selection(data_path / 'selection.json')
        root.title(f'UE PartyUp PC {__version__} — private preview')
        root.geometry('1180x900')
        root.minsize(960, 760)
        apply_theme(root)
        shell = ttk.Frame(root, style='Shell.TFrame', padding=(18, 14, 18, 10))
        shell.pack(fill='both', expand=True)

        # A compact brand header keeps the speaker workspace above the fold.
        hero = ttk.Frame(shell, style='Hero.TFrame', padding=(20, 12))
        hero.pack(fill='x')
        brand = ttk.Frame(hero, style='Hero.TFrame')
        brand.pack(side='left', fill='x', expand=True)
        title_row = ttk.Frame(brand, style='Hero.TFrame')
        title_row.pack(anchor='w')
        ttk.Label(title_row, text='PARTYUP', style='HeroTitle.TLabel').pack(side='left')
        ttk.Label(title_row, text='  /  PC', style='Kicker.TLabel').pack(side='left', padx=(4, 0))
        ttk.Label(brand, text='Tiny speakers. House-sized adventures.',
                  style='HeroSub.TLabel').pack(anchor='w')
        ttk.Label(brand, text='PIXEL PARTY  /  WINDOWS', style='Kicker.TLabel').pack(anchor='w', pady=(8, 0))
        overview = ttk.Frame(hero, style='Hero.TFrame')
        overview.pack(side='right', padx=(20, 0))
        ttk.Label(overview, textvariable=self.device_count,
                  style='HeroBadge.TLabel').pack(anchor='e')
        ttk.Label(overview, text='Private preview · Up to 10 speakers',
                  style='HeroSub.TLabel').pack(anchor='e', pady=(6, 0))
        art = header_art(hero)
        if art is not None:
            art.pack(side='right', padx=(12, 4))

        toolbar = ttk.Frame(shell, style='Toolbar.TFrame', padding=(15, 9))
        toolbar.pack(fill='x', pady=(11, 9))
        toolbar_top = ttk.Frame(toolbar, style='Toolbar.TFrame')
        toolbar_top.pack(fill='x', pady=(0, 7))
        ttk.Label(toolbar_top, text='YOUR SPEAKERS', style='ToolbarTitle.TLabel').pack(side='left')
        toggle = ttk.Checkbutton(toolbar_top, text='Experimental older speakers',
                                 variable=self.experimental, command=self.update_enabled,
                                 style='Toolbar.TCheckbutton')
        toggle.pack(side='right')
        self.controls.append((toggle, 'normal'))
        toolbar_controls = ttk.Frame(toolbar, style='Toolbar.TFrame')
        toolbar_controls.pack(fill='x')
        self.button(toolbar_controls, 'Find speakers', self.refresh,
                    variant='Quiet.TButton').pack(side='left', padx=(0, 12))
        ttk.Label(toolbar_controls, text='Control', style='ToolbarMuted.TLabel').pack(side='left', padx=(0, 9))
        self.device_combo = ttk.Combobox(toolbar_controls, state='readonly', width=34)
        self.device_combo.pack(side='left', fill='x', expand=True)
        self.controls.append((self.device_combo, 'readonly'))
        self.device_combo.bind('<<ComboboxSelected>>', self.device_changed)
        self.button(toolbar_controls, 'Read controls', self.read_controls).pack(side='left', padx=(12, 0))

        self.notebook = ttk.Notebook(shell)
        self.notebook.pack(fill='both', expand=True, pady=(1, 10))
        tabs = {}
        self.tab_viewports = {}
        for name in ('Group', 'Speaker', 'Sound', 'PartyUp settings', 'Guide'):
            viewport = ScrollableTab(self.notebook)
            self.notebook.add(viewport, text=name)
            self.tab_viewports[name] = viewport
            tabs[name] = viewport.content
        self.build_group(tabs['Group'])
        self.build_device(tabs['Speaker'])
        self.build_sound(tabs['Sound'])
        self.build_partyup(tabs['PartyUp settings'])
        self.build_guide(tabs['Guide'])
        self.notebook.bind('<<NotebookTabChanged>>', self.on_tab_changed)
        for viewport in self.tab_viewports.values():
            viewport.enable_wheel()

        status_strip = ttk.Frame(shell, style='Toolbar.TFrame', padding=(4, 0))
        status_strip.pack(fill='x', pady=(0, 8))
        ttk.Label(status_strip, text='STATUS  •', style='Count.TLabel').pack(side='left')
        self.status_widget = ttk.Label(status_strip, textvariable=self.status,
                                       style='Status.TLabel', wraplength=930)
        self.status_widget.pack(side='left', fill='x', expand=True)
        log_heading = ttk.Frame(shell, style='Shell.TFrame')
        log_heading.pack(fill='x', pady=(0, 6))
        self.activity_visible = False
        self.activity_button = self.button(log_heading, '▸  Show activity', self.toggle_activity,
                                           variant='Quiet.TButton')
        self.activity_button.pack(side='left')
        ttk.Label(log_heading, text='Local only · No telemetry',
                  style='Footer.TLabel').pack(side='right')
        self.log = ScrolledText(shell, height=3, state='disabled', wrap='word',
                                font=('Consolas', 9), bg=INPUT, fg=MUTED,
                                insertbackground=INK,
                                selectbackground='#286960', selectforeground='#FFFFFF',
                                relief='flat', bd=0, highlightthickness=1,
                                highlightbackground=BORDER, highlightcolor=ACCENT,
                                padx=12, pady=9)
        self.footer_note = ttk.Label(shell, style='Footer.TLabel',
                  text='Close the phone app before connecting. Your group keeps playing when you close this window.')
        self.footer_note.pack(
                      anchor='w', pady=(4, 0))
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.update_enabled()
        self.poll()

    def button(self, parent, label, command, feature=None, variant=None):
        button = ttk.Button(parent, text=label, command=command,
                            style=variant or 'TButton', cursor='hand2')
        self.controls.append((button, 'normal'))
        if feature:
            self.feature_widgets.setdefault(feature, []).append(button)
        return button

    def scale(self, parent, **options):
        return ttk.Scale(parent, **options)

    def register(self, widget, feature=None, state='normal'):
        self.controls.append((widget, state))
        if feature:
            self.feature_widgets.setdefault(feature, []).append(widget)
        return widget

    def build_guide(self, tab):
        ttk.Label(tab, text='FIELD GUIDE', style='Section.TLabel').pack(anchor='w')
        ttk.Label(tab, text='What each control does, where to find it, and what still needs testing.',
                  style='Muted.TLabel').pack(anchor='w', pady=(4, 12))
        guide_list = ttk.Frame(tab)
        guide_list.pack(fill='x')
        self.guide_tree = ttk.Treeview(guide_list, columns=('name', 'status'), show='headings', height=7)
        self.guide_tree.heading('name', text='Feature')
        self.guide_tree.heading('status', text='Current PC support')
        self.guide_tree.column('name', width=390)
        self.guide_tree.column('status', width=380)
        guide_scroll = ttk.Scrollbar(guide_list, orient='vertical', command=self.guide_tree.yview)
        self.guide_tree.configure(yscrollcommand=guide_scroll.set)
        guide_scroll.pack(side='right', fill='y')
        self.guide_tree.pack(side='left', fill='x', expand=True)
        for index, entry in enumerate(FEATURE_GUIDE):
            self.guide_tree.insert('', 'end', iid=str(index), values=(entry.name, entry.status))
        self.guide_detail = tk.StringVar()
        ttk.Label(tab, textvariable=self.guide_detail, wraplength=860,
                  justify='left', padding=(0, 12)).pack(fill='x')
        self.guide_tree.bind('<<TreeviewSelect>>', self.show_guide_entry)
        actions = ttk.Frame(tab)
        actions.pack(fill='x')
        self.guide_open = ttk.Button(actions, text='Go to control', command=self.open_guide_control)
        self.guide_open.pack(side='left')
        ttk.Button(actions, text='Official EVERBOOM guide', command=self.open_official_guide).pack(side='left', padx=8)
        self.guide_tree.selection_set('0')
        self.show_guide_entry()

    def show_guide_entry(self, _=None):
        selected = self.guide_tree.selection()
        if not selected:
            return
        entry = FEATURE_GUIDE[int(selected[0])]
        self.guide_detail.set(entry.detail)
        self.guide_open.configure(state='normal' if entry.page else 'disabled')

    def open_guide_control(self):
        selected = self.guide_tree.selection()
        if selected:
            page = FEATURE_GUIDE[int(selected[0])].page
            if page:
                self.notebook.select(self.tab_viewports[page])

    @staticmethod
    def open_official_guide():
        import webbrowser
        webbrowser.open(UE_GUIDE)

    def save_eq_memory(self):
        if self.busy:
            return
        if self.selected_snapshot.get('eq') is None or not self.eq_choices:
            self.status.set('Read supported EQ before saving a memory.')
            return
        try:
            name = self.memory_combo.get().strip()
            index = self.eq_combo.current()
            if not 0 <= index < len(self.eq_choices):
                raise ValueError('Choose an advertised EQ preset before saving.')
            self.eq_profiles.save(name, tuple(round(value.get()) for value in self.eq_bands),
                                  mode=self.eq_choices[index][1])
            self.memory_combo.configure(values=list(self.eq_profiles.load()))
            self.status.set(f'Saved “{name}” on this PC. No speaker command sent.')
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))

    def load_eq_memory(self):
        if self.busy:
            return
        if not self.eq_choices or self.selected_snapshot.get('eq') is None:
            self.status.set('Read supported EQ before loading a memory.')
            return
        record = self.eq_profiles.records().get(self.memory_combo.get().strip())
        if record is None:
            self.status.set('Choose a saved EQ memory first.')
            return
        target = next((index for index, (_, code) in enumerate(self.eq_choices) if code == record['mode']), None)
        if target is None:
            self.status.set('This speaker does not advertise the saved EQ preset. Nothing loaded.')
            return
        self.eq_combo.current(target)
        for variable, value in zip(self.eq_bands, record['bands']):
            variable.set(value)
        self.status.set('Memory loaded into sliders. Press Apply EQ to send it to the speaker.')

    def delete_eq_memory(self):
        if self.busy:
            return
        try:
            self.eq_profiles.delete(self.memory_combo.get().strip())
            self.memory_combo.set('')
            self.memory_combo.configure(values=list(self.eq_profiles.load()))
            self.status.set('Local EQ memory deleted. Speaker settings unchanged.')
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))

    def control_member(self):
        if self.busy:
            return
        selected = self.member_tree.selection()
        if len(selected) != 1 or selected[0] not in self.member_speakers:
            self.status.set('Select one group member to control.')
            return
        speaker = self.member_speakers[selected[0]]
        index = next((i for i, item in enumerate(self.speakers) if item.address == speaker.address), None)
        if index is None:
            return
        self.device_combo.current(index)
        self.notebook.select(self.tab_viewports['Sound'])
        self.device_changed()

    def sync_group_volume(self):
        if self.busy:
            return
        try:
            host, experimental = self.host(), self.experimental.get()
        except ValueError as exc:
            self.status.set(str(exc))
            return
        async def synchronize():
            from .controls import settings_session
            async with settings_session(host, experimental=experimental) as settings:
                await settings.sync_volume()
            return 'Group volume sync accepted. Confirm levels by listening; this does not adjust audio/video timing.'
        self.worker('message', lambda: asyncio.run(synchronize()))

    def begin_guest_drag(self, event):
        self.dragged_speaker = None
        if self.busy or not self.guest_choices:
            return
        index = self.guest_list.nearest(event.y)
        bounds = self.guest_list.bbox(index)
        if bounds and bounds[1] <= event.y <= bounds[1] + bounds[3]:
            self.dragged_speaker = ('add', self.guest_choices[index], event.x_root, event.y_root)

    def begin_member_drag(self, event):
        self.dragged_speaker = None
        if self.busy:
            return
        key = self.member_tree.identify_row(event.y)
        speaker = self.member_speakers.get(key)
        if speaker is not None and speaker.address != self.host().address:
            self.dragged_speaker = ('remove', speaker, event.x_root, event.y_root)

    def finish_speaker_drag(self, event):
        dragged, self.dragged_speaker = self.dragged_speaker, None
        if dragged is None or self.busy:
            return
        action, speaker, start_x, start_y = dragged
        if abs(event.x_root - start_x) + abs(event.y_root - start_y) < 12:
            return
        target = self.member_tree if action == 'add' else self.guest_list
        left, top = target.winfo_rootx(), target.winfo_rooty()
        if target.winfo_ismapped() and left <= event.x_root < left + target.winfo_width() and top <= event.y_root < top + target.winfo_height():
            self.group_action(action, guests_override=[speaker])

    def build_group(self, tab):
        ttk.Label(tab, text='PARTY SLOTS / YOUR SELECTION', style='Section.TLabel').pack(anchor='w')
        ttk.Label(tab, text='Play through your main speaker. Add the rooms you want to hear it in.',
                  style='Muted.TLabel', wraplength=990).pack(anchor='w', pady=(2, 10))
        self.pixel_group = PixelGroupMap(tab)
        self.pixel_group.pack(fill='x', pady=(0, 8))
        route = ttk.Frame(tab, style='Toolbar.TFrame', padding=(10, 6))
        route.pack(fill='x')
        ttk.Label(route, text='PC AUDIO   →   MAIN SPEAKER   →   YOUR GROUP',
                  style='ToolbarMuted.TLabel').pack(side='left')
        ttk.Label(route, textvariable=self.group_status, style='GroupState.TLabel').pack(side='right')
        audio_row = ttk.Frame(tab)
        audio_row.pack(fill='x', pady=(6, 0))
        self.audio_route_text = tk.StringVar(value='Windows output: not checked. Use your main speaker for PC audio.')
        ttk.Label(audio_row, textvariable=self.audio_route_text, style='Muted.TLabel', wraplength=720).pack(side='left', fill='x', expand=True)
        self.button(audio_row, 'Check PC output', self.check_audio_output, variant='Quiet.TButton').pack(side='right')
        top = ttk.Frame(tab)
        top.pack(fill='x', pady=10)
        ttk.Label(top, text='Main speaker').pack(side='left', padx=(0, 8))
        self.host_combo = self.register(ttk.Combobox(top, state='readonly', width=42), state='readonly')
        self.host_combo.pack(side='left')
        self.host_combo.bind('<<ComboboxSelected>>', self.host_changed)
        ttk.Label(top, textvariable=self.group_count, style='Count.TLabel').pack(side='left', padx=16)
        body = ttk.Frame(tab)
        body.pack(fill='both', expand=True)
        available = ttk.LabelFrame(body, text='Add speakers', padding=12)
        available.pack(side='left', fill='both', padx=(0, 12))
        self.guest_list = self.register(tk.Listbox(available, selectmode='multiple', exportselection=False,
                                                 height=9, width=28, font=('Segoe UI', 11)))
        self.guest_list.configure(bg=INPUT, fg=INK, selectbackground='#286A60',
                                  selectforeground='#FFFFFF', borderwidth=0,
                                  relief='flat', highlightthickness=1,
                                  highlightbackground=BORDER, highlightcolor=ACCENT,
                                  activestyle='none')
        self.guest_list.pack(fill='both', expand=True, padx=2, pady=3)
        self.guest_list.bind('<<ListboxSelect>>', self.guests_changed)
        self.guest_list.bind('<ButtonPress-1>', self.begin_guest_drag, add='+')
        self.guest_list.bind('<ButtonRelease-1>', self.finish_speaker_drag, add='+')
        ttk.Label(available, text='Select guests, then Start. Or drag one into Your group to join.',
                  style='Muted.TLabel', wraplength=240).pack(anchor='w', pady=(10, 0))
        members = ttk.LabelFrame(body, text='Your group', padding=12)
        members.pack(side='left', fill='both', expand=True)
        self.member_tree = self.register(ttk.Treeview(members, columns=('role', 'speaker', 'state', 'battery'),
                                                    show='headings', selectmode='extended', height=7))
        for key, label, width in [('role', 'Role', 55), ('speaker', 'Speaker', 210),
                                  ('state', 'Latest result', 215), ('battery', 'Battery', 100)]:
            self.member_tree.heading(key, text=label)
            self.member_tree.column(key, width=width, minwidth=45, stretch=key != 'role')
        self.member_tree.tag_configure('confirmed', foreground=ACCENT)
        self.member_tree.tag_configure('uncertain', foreground='#E8B76B')
        self.member_tree.pack(fill='both', expand=True)
        self.member_tree.bind('<<TreeviewSelect>>', self.member_selected)
        self.member_tree.bind('<ButtonPress-1>', self.begin_member_drag, add='+')
        self.member_tree.bind('<ButtonRelease-1>', self.finish_speaker_drag, add='+')
        self.member_detail = tk.StringVar(value='Select a member to see its detailed result.')
        ttk.Label(members, textvariable=self.member_detail, wraplength=650).pack(anchor='w', pady=8)
        self.button(members, 'Remove selected members', lambda: self.group_action('remove', from_members=True),
                    variant='Quiet.TButton').pack(anchor='w')
        quick = ttk.Frame(members)
        quick.pack(fill='x', pady=(8, 0))
        self.button(quick, 'Control selected speaker', self.control_member, variant='Quiet.TButton').pack(side='left')
        self.button(quick, 'Sync group volume', self.sync_group_volume, variant='Quiet.TButton').pack(side='left', padx=8)
        channel_row = ttk.Frame(members)
        channel_row.pack(fill='x', pady=(8, 0))
        ttk.Label(channel_row, text='Selected guest channel:').pack(side='left')
        self.channel_combo = self.register(ttk.Combobox(channel_row, state='readonly', width=9,
                                                      values=('Left', 'Right', 'Center')), state='readonly')
        self.channel_combo.current(2)
        self.channel_combo.pack(side='left', padx=6)
        self.channel_button = self.button(channel_row, 'Apply channel', self.apply_channel)
        self.channel_button.pack(side='left')
        # Critical controls stay visible even when the receiver list scrolls.
        actions = ttk.Frame(self.tab_viewports['Group'].footer, style='Toolbar.TFrame',
                            padding=(14, 8))
        actions.pack(fill='x')
        for label, action in [('Start PartyUp', 'start'), ('Add selected guests', 'add'),
                              ('Check group', 'status'), ('Stop PartyUp', 'stop')]:
            variant = {'start': 'Primary.TButton', 'stop': 'Danger.TButton',
                       'status': 'Quiet.TButton'}.get(action)
            self.button(actions, label, lambda action=action: self.group_action(action),
                        variant=variant).pack(side='left', padx=(0, 8))
        ttk.Label(tab, text='Receiver reports confirm a control connection. Listen to confirm playback.',
                  style='Muted.TLabel', wraplength=995).pack(anchor='w', pady=(10, 0))

    def build_device(self, tab):
        ttk.Label(tab, text='SPEAKER CONTROL', style='Section.TLabel').pack(anchor='w')
        ttk.Label(tab, textvariable=self.device_summary, style='Muted.TLabel',
                  wraplength=995).pack(anchor='w', pady=(4, 14))
        name = ttk.LabelFrame(tab, text='Speaker name', padding=10)
        name.pack(fill='x', pady=(0, 10))
        self.name_entry = self.register(ttk.Entry(name, width=40), 'name')
        self.name_entry.pack(side='left', padx=(0, 10))
        self.button(name, 'Rename', lambda: self.setting('rename', self.name_entry.get()), 'name').pack(side='left')
        battery = ttk.LabelFrame(tab, text='Battery and power', padding=10)
        battery.pack(fill='x', pady=(0, 10))
        self.battery_label = tk.StringVar(value='Read controls to see battery status.')
        ttk.Label(battery, textvariable=self.battery_label).pack(side='left', padx=(0, 16))
        self.button(battery, 'Announce battery', lambda: self.setting('announce_battery'), 'announce_battery').pack(side='left', padx=(0, 8))
        self.register(ttk.Checkbutton(battery, text='Silent', variable=self.silent_power), 'silent_power').pack(side='left', padx=(0, 8))
        self.button(battery, 'Power off', lambda: self.setting('power_off',
                    silent=self.silent_power.get() and not self.selected_snapshot.get('experimental', False)),
                    'power', variant='Danger.TButton').pack(side='left')
        wake = ttk.Frame(tab)
        wake.pack(fill='x', pady=(0, 10))
        self.register(ttk.Checkbutton(wake, text='Enable preview BLE wake', variable=self.experimental_wake,
                                     command=self.update_enabled)).pack(side='left')
        self.button(wake, 'Wake speaker', self.wake_selected, 'wake', variant='Quiet.TButton').pack(side='left', padx=8)
        ttk.Label(wake, text='Requires remote activation. Hardware test pending.', style='Muted.TLabel').pack(side='left')
        behavior = ttk.LabelFrame(tab, text='Speaker behavior', padding=10)
        behavior.pack(fill='x', pady=(0, 10))
        remote = self.register(ttk.Checkbutton(behavior, text='Remote activation', variable=self.remote_activation), 'remote_activation')
        remote.pack(side='left')
        self.button(behavior, 'Apply', lambda: self.setting('set_remote_activation', self.remote_activation.get()), 'remote_activation').pack(side='left', padx=8)
        ttk.Label(behavior, text='Sleep timer:').pack(side='left', padx=(16, 5))
        from .settings import SLEEP_PRESETS
        self.sleep_choices = [(label, value) for value, label in SLEEP_PRESETS.items()]
        self.sleep_entry = self.register(ttk.Combobox(behavior, state='readonly', width=13,
                                                     values=[label for label, _ in self.sleep_choices]),
                                          'sleep_timer', state='readonly')
        self.sleep_entry.pack(side='left')
        self.sleep_units = tk.StringVar(value='')
        ttk.Label(behavior, textvariable=self.sleep_units).pack(side='left', padx=5)
        self.button(behavior, 'Set timer', self.apply_sleep, 'sleep_timer').pack(side='left')
        playback = ttk.LabelFrame(tab, text='Playback controls', padding=10)
        playback.pack(fill='x', pady=(0, 10))
        source = ttk.Frame(playback)
        source.pack(fill='x', pady=(0, 8))
        ttk.Label(source, text='PC Bluetooth source:').pack(side='left')
        self.source_combo = self.register(ttk.Combobox(source, state='normal', width=35))
        self.source_combo.pack(side='left', padx=8)
        self.source_combo.bind('<<ComboboxSelected>>', lambda _: self.update_enabled())
        self.source_combo.bind('<KeyRelease>', lambda _: self.update_enabled())
        playback_buttons = ttk.Frame(playback)
        playback_buttons.pack(fill='x')
        for label, command in [('Previous', 'previous'), ('Play / pause', 'play_pause'), ('Next', 'next'),
                               ('Play', 'play'), ('Pause', 'pause'), ('Stop audio', 'stop')]:
            self.button(playback_buttons, label, lambda command=command: self.playback(command), 'playback').pack(side='left', padx=(0, 5))
        ttk.Label(tab, text='Controls enable only after this speaker reports the relevant feature. Unavailable values stay unknown. '
                  'Power off affects the selected speaker immediately.', wraplength=995).pack(anchor='w', pady=5)

    def build_sound(self, tab):
        ttk.Label(tab, text='SOUND & EQUALIZER', style='Section.TLabel').pack(anchor='w')
        ttk.Label(tab, text='Volume sends one change when you release the slider. Custom EQ bands apply on release.',
                  style='Muted.TLabel').pack(anchor='w', pady=(3, 5))
        ttk.Label(tab, textvariable=self.sound_hint, style='Micro.TLabel',
                  wraplength=955).pack(anchor='w', pady=(0, 13))
        volume = ttk.LabelFrame(tab, text='Speaker volume', padding=16)
        volume.pack(fill='x', pady=(0, 10))
        volume_heading = ttk.Frame(volume)
        volume_heading.pack(fill='x', pady=(0, 8))
        self.volume_text = tk.StringVar(value='Unknown')
        ttk.Label(volume_heading, textvariable=self.volume_text,
                  style='Volume.TLabel').pack(side='left')
        self.button(volume_heading, 'Set volume', self.apply_volume, 'volume').pack(side='right')
        self.volume_scale = self.register(self.scale(volume, from_=0, to=31, variable=self.volume), 'volume')
        self.volume_scale.pack(fill='x', pady=(2, 8))
        self.volume_scale.bind('<ButtonRelease-1>', self.on_volume_release, add='+')
        self.volume_scale.bind('<KeyRelease>', self.on_volume_release, add='+')
        self.volume.trace_add('write', lambda *_: self.update_volume_label())
        volume_ends = ttk.Frame(volume)
        volume_ends.pack(fill='x')
        ttk.Label(volume_ends, text='Quiet', style='Muted.TLabel').pack(side='left')
        ttk.Label(volume_ends, text='Loud', style='Muted.TLabel').pack(side='right')
        eq = ttk.LabelFrame(tab, text='Shape your sound', padding=16)
        eq.pack(fill='x', pady=(0, 10))
        top = ttk.Frame(eq)
        top.pack(fill='x')
        ttk.Label(top, text='Preset:').pack(side='left', padx=(0, 5))
        self.eq_combo = self.register(ttk.Combobox(top, state='readonly', width=30), 'eq', state='readonly')
        self.eq_combo.pack(side='left', padx=(0, 10))
        self.button(top, 'Apply EQ', self.apply_eq, 'eq').pack(side='left')
        memories = ttk.Frame(eq)
        memories.pack(fill='x', pady=(12, 0))
        ttk.Label(memories, text='EQ memory:').pack(side='left')
        self.memory_combo = self.register(ttk.Combobox(memories, width=20,
                                                       values=list(self.eq_profiles.load())))
        self.memory_combo.pack(side='left', padx=8)
        self.button(memories, 'Save', self.save_eq_memory, 'eq', variant='Quiet.TButton').pack(side='left')
        self.button(memories, 'Load into sliders', self.load_eq_memory, 'eq', variant='Quiet.TButton').pack(side='left', padx=6)
        self.button(memories, 'Delete', self.delete_eq_memory, variant='Quiet.TButton').pack(side='left')
        bands = ttk.Frame(eq)
        bands.pack(fill='x', pady=(18, 4))
        for number, value in enumerate(self.eq_bands, 1):
            box = ttk.Frame(bands)
            box.pack(side='left', fill='x', expand=True, padx=6)
            ttk.Label(box, text=f'Band {number}').pack()
            scale = self.register(self.scale(box, from_=127, to=-128,
                                            orient='vertical', length=150, variable=value), 'eq_band')
            scale.pack(pady=10)
            scale.bind('<ButtonRelease-1>', self.on_eq_band_release, add='+')
            scale.bind('<KeyRelease>', self.on_eq_band_release, add='+')
            self.eq_band_scales.append(scale)
            label = tk.StringVar(value='0')
            value.trace_add('write', lambda *_, value=value, label=label: label.set(str(round(value.get()))))
            ttk.Label(box, textvariable=label, style='Value.TLabel').pack()
        outdoor = ttk.LabelFrame(tab, text='Outdoor mode', padding=10)
        outdoor.pack(fill='x')
        self.register(ttk.Checkbutton(outdoor, text='Outdoor mode', variable=self.outdoor), 'outdoor').pack(side='left')
        self.button(outdoor, 'Apply outdoor mode', lambda: self.setting('set_outdoor', self.outdoor.get()), 'outdoor').pack(side='left', padx=10)
        ttk.Label(tab, text='Release the volume or Custom EQ sliders to send one change, then verify it by readback. '
                  'Presets use Apply EQ. Bluetooth commands may take a few seconds.',
                  style='Muted.TLabel', wraplength=995).pack(anchor='w', pady=10)
        ttk.Label(tab, text='Custom EQ bands use the speaker’s raw levels; these values are not decibels.', wraplength=995).pack(anchor='w')

    def build_partyup(self, tab):
        ttk.Label(tab, text='PARTYUP OPTIONS', style='Section.TLabel').pack(anchor='w')
        ttk.Label(tab, text='These options apply only to the selected control target. Unsupported features stay unavailable.',
                  style='Muted.TLabel', wraplength=995).pack(anchor='w', pady=(3, 14))
        general = ttk.LabelFrame(tab, text='Group preferences', padding=10)
        general.pack(fill='x', pady=(0, 10))
        self.register(ttk.Checkbutton(general, text='Remember PartyUp group', variable=self.sticky), 'sticky').pack(side='left')
        self.button(general, 'Apply group preference', lambda: self.setting('set_sticky', self.sticky.get()), 'sticky').pack(side='left', padx=10)
        self.button(general, 'Synchronize group volume', lambda: self.setting('sync_volume'), 'partyup').pack(side='left', padx=10)
        public = ttk.LabelFrame(tab, text='Speaker availability', padding=10)
        public.pack(fill='x', pady=(0, 10))
        self.register(ttk.Checkbutton(public, text='Allow nearby PartyUp discovery', variable=self.public), 'public').pack(side='left')
        self.button(public, 'Apply availability', lambda: self.setting('set_public', self.public.get()), 'public').pack(side='left', padx=10)
        identify = ttk.LabelFrame(tab, text='Identify speaker', padding=10)
        identify.pack(fill='x', pady=(0, 10))
        self.identify_combo = self.register(ttk.Combobox(identify, values=('Blink light', 'Solid light', 'Alternate light'),
                                                        state='readonly', width=16), 'identify', state='readonly')
        self.identify_combo.current(0)
        self.identify_combo.pack(side='left', padx=(0, 10))
        self.button(identify, 'Identify selected speaker', self.identify, 'identify').pack(side='left')
        ttk.Label(identify, text='Uses the speaker’s supported identification signal.', padding=(12, 0, 0, 0)).pack(side='left')
        stereo = ttk.LabelFrame(tab, text='Stereo / channel balance', padding=10)
        stereo.pack(fill='x', pady=(0, 10))
        option = self.register(ttk.Checkbutton(stereo, text='Enable experimental balance writes',
                                               variable=self.experimental_balance, command=self.update_enabled))
        option.pack(anchor='w', pady=(0, 8))
        balance = ttk.Frame(stereo)
        balance.pack(fill='x')
        ttk.Label(balance, text='Protocol value:').pack(side='left')
        self.register(self.scale(balance, from_=-128, to=127, variable=self.balance), 'stereo_balance').pack(side='left', fill='x', expand=True, padx=10)
        self.button(balance, 'Apply balance', lambda: self.setting('set_stereo_balance', round(self.balance.get())), 'stereo_balance').pack(side='left', padx=10)
        ttk.Label(tab, text='Balance direction and current-value readback have not been established. '
                  'Balance writes require a supported model and explicit experimental opt-in. '
                  'Mixed-model grouping and groups larger than two still require hardware acceptance.', wraplength=995).pack(anchor='w', pady=10)

    def append_log(self, text):
        follow_tail = self.activity_visible and self.log.yview()[1] >= .999
        self.log.configure(state='normal')
        self.log.insert('end', f'{datetime.now():%H:%M:%S}  {text}\n')
        excess = int(self.log.index('end-1c').split('.')[0]) - 1 - MAX_LOG_LINES
        if excess > 0:
            self.log.delete('1.0', f'{excess+1}.0')
        if follow_tail:
            self.log.see('end')
        self.log.configure(state='disabled')

    def toggle_activity(self):
        """Keep detailed diagnostics available without crowding the workspace."""
        self.activity_visible = not self.activity_visible
        if self.activity_visible:
            self.log.pack(fill='x', before=self.footer_note)
            self.log.see('end')
        else:
            self.log.pack_forget()
        self.activity_button.configure(text='▾  Hide activity' if self.activity_visible else '▸  Show activity')

    def worker(self, kind, task):
        if self.busy:
            return
        self.busy = True
        self.update_enabled()
        def execute():
            try:
                self.events.put((kind, task()))
            except (Exception, asyncio.CancelledError) as exc:
                self.events.put(('error', str(exc) or 'Bluetooth operation canceled.'))
        threading.Thread(target=execute, daemon=True).start()

    def progress(self, message):
        self.events.put(('progress', message))

    def refresh(self):
        self.status.set('Reading paired speaker records and PC Bluetooth adapters…')
        def inspect():
            from .test_connection import local_radios
            speakers = discover()
            try:
                radios = local_radios()
            except Exception:
                radios = []
            return speakers, radios
        self.worker('discovery', inspect)

    def host(self):
        index = self.host_combo.current()
        if not 0 <= index < len(self.speakers):
            raise ValueError('Choose a main speaker first.')
        return self.speakers[index]

    def selected_device(self):
        index = self.device_combo.current()
        if not 0 <= index < len(self.speakers):
            raise ValueError('Choose a speaker to control first.')
        return self.speakers[index]

    def selected_guests(self):
        return [self.guest_choices[index] for index in self.guest_list.curselection()]

    def remember(self):
        try:
            host = self.host()
        except ValueError:
            return
        self.saved_host = host.address
        self.saved_guests = [speaker.address for speaker in self.selected_guests()]
        try:
            self.data_path.mkdir(exist_ok=True, parents=True)
            (self.data_path / 'selection.json').write_text(json.dumps({'host': self.saved_host, 'guests': self.saved_guests}, indent=2), encoding='utf-8')
            path = self.data_path / 'devices.json'
            try:
                known = json.loads(path.read_text(encoding='utf-8'))
            except (OSError, ValueError):
                known = {}
            if not isinstance(known, dict):
                known = {}
            # Retain the original model name so renaming does not remove discovery.
            for speaker in self.speakers:
                known.setdefault(str(speaker.address), speaker.name)
            path.write_text(json.dumps(known, indent=2), encoding='utf-8')
        except OSError as exc:
            self.append_log(f'Could not save local selections: {exc}')

    def rebuild_guests(self, desired=None):
        desired = self.saved_guests if desired is None else desired
        try:
            host = self.host()
        except ValueError:
            host = None
        self.guest_choices = [speaker for speaker in self.speakers if host is None or speaker.address != host.address]
        self.guest_list.delete(0, 'end')
        for index, speaker in enumerate(self.guest_choices):
            self.guest_list.insert('end', speaker.label + (' · experimental' if speaker.experimental else ''))
            if speaker.address in desired:
                self.guest_list.selection_set(index)
        self.guests_changed()

    def host_changed(self, _=None):
        desired = [speaker.address for speaker in self.selected_guests()]
        self.clear_group_results()
        self.rebuild_guests(desired)
        self.remember()

    def clear_group_results(self):
        self.member_tree.delete(*self.member_tree.get_children())
        self.member_speakers = {}
        self.group_status.set('STATUS NOT CHECKED')
        self.audio_route_text.set('Windows output: not checked. Use your main speaker for PC audio.')
        self.member_detail.set('Check group to load results for the selected main speaker.')
        self.update_enabled()

    def guests_changed(self, _=None):
        count = len(self.guest_list.curselection())
        total = count + int(0 <= self.host_combo.current() < len(self.speakers))
        self.group_count.set(f'{count} guests selected · {total} total · maximum 10')
        self.pixel_group.show(total > count, min(count, 9))
        if count > 9:
            self.status.set('Choose at most nine guests before starting or changing the group.')
        self.remember()

    def device_changed(self, _=None):
        try:
            speaker = self.selected_device()
        except ValueError:
            return
        self.selected_snapshot = self.snapshots.get(speaker.address, {})
        self.render_snapshot(speaker, self.selected_snapshot)
        self.maybe_load_sound_controls()

    def on_tab_changed(self, _=None):
        self.maybe_load_sound_controls()

    def maybe_load_sound_controls(self):
        # A tab switch initiates only read-only queries; never mutate on opening.
        if self.busy or self.notebook.select() != str(self.tab_viewports['Sound']):
            return
        try:
            speaker = self.selected_device()
        except ValueError:
            self.sound_hint.set('Find and select a speaker first.')
            return
        if speaker.experimental:
            self.sound_hint.set('Experimental older speakers require manual Read controls.')
            return
        if speaker.address in self.snapshots and self.snapshots[speaker.address]:
            return
        if speaker.address in self.sound_requested:
            return  # Do not hammer an unreachable speaker on every tab switch.
        self.sound_requested.add(speaker.address)
        self.sound_hint.set('Reading volume and EQ only… No settings will change.')
        self.read_sound_controls()

    def member_selected(self, _=None):
        selected = self.member_tree.selection()
        if selected:
            self.member_detail.set(self.member_tree.item(selected[0], 'tags')[0] if self.member_tree.item(selected[0], 'tags') else '')
        self.update_enabled()

    def apply_channel(self):
        try:
            host = self.host()
            guests = [self.member_speakers[item] for item in self.member_tree.selection()
                      if item in self.member_speakers and self.member_speakers[item].address != host.address]
            if len(guests) != 1:
                raise ValueError('Select exactly one guest row to choose its channel.')
            guest = guests[0]
            channel = self.channel_combo.current() + 1
            if channel not in (1, 2, 3):
                raise ValueError('Choose Left, Right, or Center.')
            experimental = self.experimental.get()
            self.status.set(f'Applying channel to {guest.label}…')
            self.worker('message', lambda: asyncio.run(GroupManager().set_channel(host, guest, channel,
                                                                                experimental=experimental)))
        except ValueError as exc:
            self.status.set(str(exc))

    def group_action(self, action, from_members=False, guests_override=None):
        try:
            host = self.host()
            guests = self.selected_guests() if guests_override is None else list(guests_override)
            if from_members:
                guests = [self.member_speakers[item] for item in self.member_tree.selection()
                          if item in self.member_speakers and self.member_speakers[item].address != host.address]
                if not guests:
                    raise ValueError('Select one or more guest rows to remove.')
            if len(guests) > 9:
                raise ValueError('Select no more than nine guests.')
            experimental = self.experimental.get()
            self.remember()
            self.status.set(f'PartyUp {action} in progress…')
            self.worker('group', lambda: asyncio.run(GroupManager().run(action, host, guests, self.progress,
                                                                        experimental=experimental)))
        except ValueError as exc:
            self.status.set(str(exc))

    def wake_selected(self):
        if self.busy or not self.experimental_wake.get():
            return
        try:
            speaker = self.selected_device()
            if speaker.experimental:
                raise ValueError('Preview wake is currently limited to EVERBOOM.')
        except ValueError as exc:
            self.status.set(str(exc))
            return
        from .wake import wake_speaker
        self.status.set('Sending the source-backed BLE wake request…')
        self.worker('message', lambda: asyncio.run(wake_speaker(speaker)))

    def check_audio_output(self):
        if self.busy:
            return
        try:
            host = self.host()
            guests = [speaker.address for speaker in self.selected_guests()]
        except ValueError as exc:
            self.status.set(str(exc))
            return
        from .audio_route import inspect_audio_route
        self.status.set('Checking the default Windows audio output…')
        self.worker('audio_route', lambda: inspect_audio_route(host.address, guests))

    def read_controls(self):
        try:
            speaker, experimental = self.selected_device(), self.experimental.get()
            self.status.set(f'Reading controls from {speaker.label}…')
            group_host = self.host().address
            async def inspect():
                from .controls import settings_session
                async with settings_session(speaker, experimental=experimental, group_host=group_host) as settings:
                    return speaker, await settings.snapshot()
            self.worker('snapshot', lambda: asyncio.run(inspect()))
        except ValueError as exc:
            self.status.set(str(exc))

    def read_sound_controls(self):
        # Startup of Sound should not require the whole (slow) settings inventory.
        try:
            speaker = self.selected_device()
            if speaker.experimental:
                self.sound_hint.set('Use Read controls for experimental speaker capabilities.')
                return
            group_host = self.host().address
            async def inspect():
                from .controls import settings_session
                from .session import UnsupportedFeature
                async with settings_session(speaker, group_host=group_host) as settings:
                    readout = {'capabilities': {}, 'errors': {}, 'max_volume': 31}
                    getters = {'volume': settings.volume, 'eq': settings.eq,
                               'supported_eq_modes': settings.eq_modes}
                    missing = {}
                    for field, getter in getters.items():
                        try:
                            readout[field] = await getter()
                        except Exception as error:
                            readout[field] = None
                            missing[field] = error
                            readout['errors'][field] = str(error)
                    # A timeout means UNKNOWN, not unsupported. Only a concrete
                    # feature rejection makes the capability False.
                    readout['capabilities'] = {
                        'volume': (True if readout['volume'] is not None else
                                   False if isinstance(missing.get('volume'), UnsupportedFeature) else None),
                        'eq': (True if readout['eq'] is not None and readout['supported_eq_modes'] is not None
                               else False if any(isinstance(missing.get(key), UnsupportedFeature)
                                                 for key in ('eq', 'supported_eq_modes')) else None)}
                    return speaker, readout
            self.status.set(f'Reading volume and EQ from {speaker.label}…')
            self.worker('sound_snapshot', lambda: asyncio.run(inspect()))
        except ValueError as error:
            self.status.set(str(error))

    def setting(self, method, *args, **kwargs):
        try:
            speaker, experimental = self.selected_device(), self.experimental.get()
            if not self.selected_snapshot:
                raise ValueError('Read this speaker’s controls before changing a setting.')
            self.remember()
            self.status.set(f'Applying {method.replace("_", " ")} to {speaker.label}…')
            group_host = self.host().address
            async def apply():
                from .controls import settings_session
                async with settings_session(speaker, experimental=experimental, group_host=group_host) as settings:
                    await getattr(settings, method)(*args, **kwargs)
                    if method == 'power_off':
                        return speaker, {'powered_off': True, 'capabilities': {}, 'errors': {}}
                    if method in SETTING_READBACK:
                        # Verify only the changed setting, not every device feature.
                        field = SETTING_READBACK[method]
                        try:
                            confirmed = await getattr(settings, field)()
                        except Exception as error:
                            return speaker, field, None, str(error)
                        return speaker, field, confirmed, None
                    if method in ACK_ONLY_ACTIONS:
                        return f'{speaker.label}: {method.replace("_", " ")} command accepted. Effect not independently verified.'
                    return speaker, await settings.snapshot()
            event = ('adjusted' if method in SETTING_READBACK else
                     'message' if method in ACK_ONLY_ACTIONS else 'snapshot')
            self.worker(event, lambda: asyncio.run(apply()))
        except ValueError as exc:
            self.status.set(str(exc))

    def apply_sleep(self):
        index = self.sleep_entry.current()
        if not 0 <= index < len(self.sleep_choices):
            self.status.set('Choose a sleep timer preset.')
            return
        self.setting('set_sleep_timer', self.sleep_choices[index][1])

    def on_volume_release(self, _=None):
        # Tk's button/key release is one user gesture, not dozens of writes
        # generated while dragging a 0–31 scale.
        if not self.busy and not self.volume_scale.instate(['disabled']):
            self.apply_volume()

    def apply_volume(self):
        if self.busy:
            return
        if self.volume_scale.instate(['disabled']):
            self.status.set('Read controls from this speaker before changing volume.')
            return
        try:
            target = round(self.volume.get())
            if target == self.selected_snapshot.get('volume'):
                return  # Clicking the thumb or pressing a non-arrow key is harmless.
            self.setting('set_volume', target)
        except (ValueError, tk.TclError):
            self.status.set('Enter a whole-number volume level.')

    def update_volume_label(self):
        maximum = self.selected_snapshot.get('max_volume')
        current = self.selected_snapshot.get('volume')
        if current is None or not isinstance(maximum, (int, float)) or maximum <= 0:
            self.volume_text.set('Not read')
        else:
            target = round(self.volume.get())
            percent = round(target * 100 / maximum)
            self.volume_text.set(f'{percent}% · pending' if target != current else f'{percent}%')

    def on_eq_band_release(self, event=None):
        if self.busy or (event is not None and event.widget.instate(['disabled'])):
            return
        if not self.selected_snapshot.get('eq'):
            return
        # Custom is an actual advertised wire code, never a guessed enum index.
        custom = next((i for i, (_, code) in enumerate(self.eq_choices) if code == 4), None)
        if custom is None:
            self.status.set('This speaker does not advertise Custom EQ.')
            return
        self.eq_combo.current(custom)
        self.apply_eq()

    def apply_eq(self):
        if self.busy:
            return
        if self.eq_combo.instate(['disabled']):
            self.status.set('Read supported EQ controls before changing them.')
            return
        index = self.eq_combo.current()
        if not 0 <= index < len(self.eq_choices):
            self.status.set('Choose a supported EQ preset first.')
            return
        mode = self.eq_choices[index][1]
        bands = tuple(round(value.get()) for value in self.eq_bands)
        previous = self.selected_snapshot.get('eq')
        if previous is None:
            self.status.set('EQ readback is unavailable. No EQ command sent.')
            return
        prev_mode = previous.get('mode') if isinstance(previous, dict) else getattr(previous, 'mode', None)
        prev_bands = previous.get('bands') if isinstance(previous, dict) else getattr(previous, 'bands', ())
        if mode == prev_mode and bands == tuple(prev_bands):
            return
        self.setting('set_eq', mode, bands)

    def source_address(self):
        selected = self.source_combo.current()
        if 0 <= selected < len(self.radios):
            return self.radios[selected][0]
        return parse_mac(self.source_combo.get())

    def playback(self, command):
        try:
            self.setting('playback', command, self.source_address())
        except ValueError as exc:
            self.status.set(str(exc))

    def identify(self):
        index = self.identify_combo.current()
        if not 0 <= index < 3:
            self.status.set('Choose an identification signal.')
            return
        self.setting('identify', signal=('blink', 'solid', 'alternate')[index])

    def update_enabled(self):
        for widget, idle_state in self.controls:
            self.set_widget_state(widget, 'disabled' if self.busy else idle_state)
        if self.busy:
            return
        capabilities = self.selected_snapshot.get('capabilities', {})
        if not isinstance(capabilities, dict):
            capabilities = {item: True for item in capabilities}
        for feature, widgets in self.feature_widgets.items():
            available = bool(capabilities.get(feature))
            if feature == 'wake':
                try:
                    available = self.experimental_wake.get() and not self.selected_device().experimental
                except ValueError:
                    available = False
            if feature == 'silent_power':
                available = bool(capabilities.get('power')) and not self.selected_snapshot.get('experimental', False)
            if feature == 'stereo_balance':
                available = available and self.experimental_balance.get()
            if feature in ('name', 'volume', 'eq', 'outdoor', 'sleep_timer', 'remote_activation', 'sticky', 'public'):
                available = available and self.selected_snapshot.get(feature) is not None
            if feature == 'volume':
                maximum = self.selected_snapshot.get('max_volume')
                available = available and isinstance(maximum, (int, float)) and maximum > 0
            if feature == 'playback':
                try:
                    self.source_address()
                except ValueError:
                    available = False
            if feature == 'eq' and not self.eq_choices:
                available = False
            if feature == 'eq_band':
                available = bool(capabilities.get('eq')) and self.selected_snapshot.get('eq') is not None
                available = available and any(code == 4 for _, code in self.eq_choices)
            for widget in widgets:
                if not available:
                    self.set_widget_state(widget, 'disabled')
        try:
            host = self.host()
            guests = [self.member_speakers[item] for item in self.member_tree.selection()
                      if item in self.member_speakers and self.member_speakers[item].address != host.address]
            channel_allowed = len(guests) == 1
        except ValueError:
            channel_allowed = False
        self.channel_button.configure(state='normal' if channel_allowed else 'disabled')
        self.update_tuning_controls()

    @staticmethod
    def set_widget_state(widget, state):
        if isinstance(widget, ttk.Treeview):
            widget.state(['disabled'] if state == 'disabled' else ['!disabled'])
        else:
            widget.configure(state=state)

    def render_snapshot(self, speaker, snapshot):
        self.tuning.observe(speaker.address, snapshot.get('eq'))
        self.selected_snapshot = snapshot
        if snapshot:
            self.snapshots[speaker.address] = snapshot
        volume_ready = snapshot.get('volume') is not None
        eq_ready = (snapshot.get('eq') is not None and snapshot.get('supported_eq_modes') is not None)
        if not snapshot:
            self.sound_hint.set('Opening Sound reads available controls. The selected speaker must respond.')
        elif not volume_ready and not eq_ready:
            self.sound_hint.set('No volume or EQ readback. Check power, Bluetooth connection and try Read controls.')
        elif volume_ready and eq_ready:
            self.sound_hint.set('Volume and advertised EQ controls loaded. Release a slider to apply one change.')
        elif volume_ready:
            self.sound_hint.set('Volume loaded; EQ is unavailable. Use Read controls to try again.')
        else:
            self.sound_hint.set('EQ loaded; volume is unavailable. Use Read controls to try again.')
        if snapshot.get('powered_off'):
            self.device_summary.set(f'{speaker.label}: power command accepted. Read again after powering it on.')
            self.battery_label.set('Not available while powered off.')
            self.update_enabled()
            return
        volume, maximum = snapshot.get('volume'), snapshot.get('max_volume')
        volume_label = (f'{round(volume * 100 / maximum)}%' if isinstance(volume, (int, float))
                        and isinstance(maximum, (int, float)) and maximum > 0 else format_value(volume))
        self.device_summary.set(f'{speaker.label} · Battery: {format_value(snapshot.get("battery"))} · Volume: {volume_label}')
        self.battery_label.set(format_value(snapshot.get('battery')))
        self.name_entry.configure(state='normal')
        self.name_entry.delete(0, 'end')
        self.name_entry.insert(0, snapshot.get('name') or speaker.name)
        volume = snapshot.get('volume')
        if isinstance(volume, (int, float)):
            self.volume.set(volume)
        self.volume_scale.configure(to=snapshot.get('max_volume') or 31)
        self.update_volume_label()
        for key, variable in [('outdoor', self.outdoor), ('remote_activation', self.remote_activation),
                              ('sticky', self.sticky), ('public', self.public)]:
            if snapshot.get(key) is not None:
                variable.set(bool(snapshot[key]))
        if snapshot.get('sleep_timer') is not None:
            index = next((index for index, (_, value) in enumerate(self.sleep_choices)
                          if value == snapshot['sleep_timer']), None)
            if index is None:
                self.sleep_entry.set(f'Unknown ({snapshot["sleep_timer"]})')
            else:
                self.sleep_entry.current(index)
        else:
            self.sleep_entry.set('Not available')
        modes = snapshot.get('supported_eq_modes') or []
        try:
            from .settings import EQ_PRESETS
        except ImportError:
            EQ_PRESETS = {}
        if isinstance(modes, dict):
            self.eq_choices = [(str(label), code) for label, code in modes.items()]
        else:
            self.eq_choices = [(str(item.get('name', item.get('mode'))), item.get('mode', item.get('value')))
                               if isinstance(item, dict) else (str(item[0]), item[1])
                               if isinstance(item, (list, tuple)) and len(item) == 2 else (str(item), item)
                               for item in modes]
            self.eq_choices = [(EQ_PRESETS[code], code) for label, code in self.eq_choices if code in EQ_PRESETS]
        self.eq_combo.configure(values=[label for label, _ in self.eq_choices])
        eq = snapshot.get('eq')
        mode = eq.get('mode') if isinstance(eq, dict) else getattr(eq, 'mode', eq)
        match = next((index for index, (_, code) in enumerate(self.eq_choices) if code == mode), None)
        if match is not None:
            self.eq_combo.current(match)
        elif self.eq_choices:
            self.eq_combo.current(0)
        else:
            self.eq_combo.set('No supported presets reported')
        bands = eq.get('bands', ()) if isinstance(eq, dict) else getattr(eq, 'bands', ())
        for variable, value in zip(self.eq_bands, bands):
            variable.set(value)
        if isinstance(snapshot.get('stereo_balance'), (int, float)):
            self.balance.set(snapshot['stereo_balance'])
        self.update_enabled()

    def show_discovery(self, speakers, radios):
        # Refresh can choose a new main when the remembered device disappeared.
        self.clear_group_results()
        self.speakers, self.radios = speakers, radios
        self.snapshots.clear()  # A new discovery invalidates previously read capabilities.
        self.sound_requested.clear()
        self.device_count.set(f'{len(speakers)} PAIRED RECORDS')
        values = [speaker.label + (' · experimental' if speaker.experimental else '') for speaker in speakers]
        for combo in (self.host_combo, self.device_combo):
            combo.configure(values=values)
            combo.set('')
        if speakers:
            host_index = next((i for i, speaker in enumerate(speakers) if speaker.address == self.saved_host), 0)
            self.host_combo.current(host_index)
            self.device_combo.current(host_index)
            if self.saved_host is None:
                self.saved_guests = [speaker.address for i, speaker in enumerate(speakers) if i != host_index][:9]
        self.rebuild_guests()
        self.source_combo.configure(values=[f'{name} · {address:012X}' for address, name in radios])
        if radios:
            self.source_combo.current(0)
        self.device_changed()
        self.status.set(f'Found {len(speakers)} paired candidate speaker(s). Select a main speaker and up to nine guests.')
        self.append_log(self.status.get())

    def show_group(self, result):
        host = self.host()
        self.member_tree.delete(*self.member_tree.get_children())
        self.member_speakers = {}
        state = 'PartyUp enabled' if result.host_on else 'PartyUp off' if result.host_on is False else 'State unconfirmed'
        self.group_status.set('BROADCAST ON' if result.host_on else 'BROADCAST OFF'
                              if result.host_on is False else 'STATE UNKNOWN')
        host_detail = next((member.detail for member in result.members if member.speaker.address == host.address and member.detail),
                           'Windows audio should play through this speaker.')
        rows = [(host, 'Main', state, host_detail)]
        rows += [(member.speaker, 'Guest', member.state, member.detail) for member in result.members if member.speaker.address != host.address]
        for speaker, role, member_state, detail in rows:
            key = str(speaker.address)
            battery = format_value(self.snapshots.get(speaker.address, {}).get('battery'))
            confirmed = (member_state == 'PartyUp enabled' or member_state == 'reported by main speaker')
            tag = 'confirmed' if confirmed else 'uncertain'
            self.member_tree.insert('', 'end', iid=key, values=(role, speaker.label, member_state, battery),
                                    tags=(detail or member_state, tag))
            self.member_speakers[key] = speaker
        self.status.set(str(result).split('\n')[0])
        self.append_log(str(result))

    def poll(self):
        try:
            self._poll_events()
        except Exception:
            import logging
            logging.getLogger('partyup').exception('Worker result handling failed')
            self.status.set('A result could not be displayed. Check the local app log.')
            self.root.after(IDLE_POLL_MS,self.poll)

    def show_playback_notice(self, message):
        guest = str(message).startswith('Guest controls are paused')
        explanation = (
            'Guest controls are unavailable while PartyUp is on.\n\n'
            'Stop PartyUp first, then read the guest again.\n'
            'No guest control connection was opened.' if guest else
            'Stop PartyUp before changing Remember PartyUp group.\n\n'
            'Your previous setting has been restored.\n'
            'No preference change was sent.')
        messagebox.showwarning('Change blocked to protect playback', explanation, parent=self.root)

    def _poll_events(self):
        processed = 0
        try:
            while processed < MAX_EVENTS_PER_TICK:
                kind, result = self.events.get_nowait()
                processed += 1
                if kind == 'progress':
                    self.status.set(result)
                    self.append_log(result)
                    continue
                self.busy = False
                # Temporarily enable entries so values can be updated before capability gating.
                for widget, state in self.controls:
                    self.set_widget_state(widget, state)
                if kind == 'error':
                    # A guard refused before any mutation: restore the confirmed UI,
                    # rather than leaving an optimistic checkbox looking applied.
                    if str(result).startswith(('Guest controls are paused',
                                               'Stop PartyUp before changing Remember PartyUp group')):
                        try:
                            self.render_snapshot(self.selected_device(), self.selected_snapshot)
                        except ValueError:
                            pass
                        self.show_playback_notice(result)
                    self.status.set(result)
                    self.append_log(f'Operation failed: {result}')
                elif kind == 'discovery':
                    self.show_discovery(*result)
                elif kind == 'group':
                    self.show_group(result)
                elif kind == 'audio_route':
                    role = result['role']
                    message = {'main': 'matches your main speaker', 'guest': 'matches a selected guest; check your Windows output',
                               'other': 'does not match the selected speakers; check your Windows output'}[role]
                    self.audio_route_text.set(f'{result["name"]}: {message}. Per-app output overrides are not checked.')
                    self.status.set('Default Windows output checked. No audio settings changed.')
                elif kind == 'message':
                    self.status.set(str(result) if result else 'Channel command accepted; confirm playback by listening.')
                    self.append_log(self.status.get())
                elif kind == 'tuning':
                    self.accept_tuning(result)
                elif kind == 'sound_snapshot':
                    speaker, snapshot = result
                    if self.selected_device().address == speaker.address:
                        self.tuning.observe(speaker.address, snapshot.get('eq'), fresh=True)
                    self.snapshots[speaker.address] = snapshot
                    if self.selected_device().address == speaker.address:
                        self.render_snapshot(speaker, snapshot)
                    ready = [field for field in ('volume', 'eq') if snapshot.get(field) is not None]
                    label = ', '.join(ready) if ready else 'none'
                    message = f'{speaker.label}: sound controls read. Available: {label}.'
                    self.status.set(message)
                    self.append_log(message)
                    for field, error in snapshot.get('errors', {}).items():
                        self.append_log(f'{field}: {error}')
                elif kind == 'adjusted':
                    speaker, field, confirmed, problem = result
                    snapshot = dict(self.snapshots.get(speaker.address, self.selected_snapshot))
                    errors = dict(snapshot.get('errors', {}))
                    snapshot[field] = confirmed
                    if problem:
                        errors[field] = f'Write accepted but readback unavailable: {problem}'
                        message = f'{field.upper()} change accepted; current value unconfirmed. Read controls to retry.'
                    else:
                        errors.pop(field, None)
                        message = f'{speaker.label}: {field.upper()} change verified by speaker readback.'
                    snapshot['errors'] = errors
                    self.snapshots[speaker.address] = snapshot
                    if self.selected_device().address == speaker.address:
                        self.render_snapshot(speaker, snapshot)
                    self.status.set(message)
                    self.append_log(message)
                elif kind == 'snapshot':
                    speaker, snapshot = result
                    if self.selected_device().address == speaker.address:
                        self.tuning.observe(speaker.address, snapshot.get('eq'), fresh=True)
                    self.snapshots[speaker.address] = snapshot
                    name = snapshot.get('name')
                    if name:
                        self.speakers = [replace(item, name=name) if item.address == speaker.address else item for item in self.speakers]
                        values = [item.label + (' · experimental' if item.experimental else '') for item in self.speakers]
                        for combo in (self.host_combo, self.device_combo):
                            selected = combo.current()
                            combo.configure(values=values)
                            if selected >= 0:
                                combo.current(selected)
                        self.rebuild_guests()
                    self.render_snapshot(speaker, snapshot)
                    self.status.set(f'{speaker.label}: controls read. Enabled features reflect the speaker’s replies.')
                    self.append_log(self.status.get())
                    for field, error in snapshot.get('errors', {}).items():
                        self.append_log(f'{field}: {error}')
                self.update_enabled()
        except queue.Empty:
            pass
        # This polls only the worker queue, never the speakers. Idle windows
        # need fewer wakeups; bounded batches keep bursts from starving Tk.
        delay = 10 if processed == MAX_EVENTS_PER_TICK else BUSY_POLL_MS if self.busy else IDLE_POLL_MS
        self.root.after(delay, self.poll)

    def close(self):
        if self.busy:
            messagebox.showinfo('Operation in progress', 'Please wait for the speaker operation to finish before closing.', parent=self.root)
        else:
            self.root.destroy()


def main(smoke=False, logger=None):
    from .classroom_view import ClassroomApp
    root = tk.Tk()
    app = ClassroomApp(root)
    if logger is not None:
        def callback_error(kind,error,traceback):
            logger.error('Interface callback failed',exc_info=(kind,error,traceback))
            app.status.set('An interface action failed. Details are in the local app log.')
        root.report_callback_exception=callback_error
    if smoke:
        root.withdraw()
        root.after(150, root.destroy)
    else:
        root.after(150, app.refresh)
    root.mainloop()
