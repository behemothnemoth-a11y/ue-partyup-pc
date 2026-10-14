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


DATA = Path(__file__).resolve().parents[1] / 'data'


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


class PartyUpApp:
    def __init__(self, root, data_path=DATA):
        self.root, self.data_path = root, data_path
        self.events = queue.Queue()
        self.busy = False
        self.speakers = []
        self.guest_choices = []
        self.member_speakers = {}
        self.snapshots = {}
        self.radios = []
        self.selected_snapshot = {}
        self.eq_choices = []
        self.controls = []
        self.feature_widgets = {}
        self.status = tk.StringVar(value='Find paired speakers to begin.')
        self.group_count = tk.StringVar(value='0 guests selected · maximum 9')
        self.device_summary = tk.StringVar(value='Choose a speaker, then read its controls.')
        self.experimental = tk.BooleanVar(value=False)
        self.outdoor = tk.BooleanVar(value=False)
        self.remote_activation = tk.BooleanVar(value=False)
        self.sticky = tk.BooleanVar(value=False)
        self.public = tk.BooleanVar(value=False)
        self.silent_power = tk.BooleanVar(value=False)
        self.experimental_balance = tk.BooleanVar(value=False)
        self.volume = tk.DoubleVar(value=0)
        self.balance = tk.DoubleVar(value=0)
        self.eq_bands = [tk.DoubleVar(value=0) for _ in range(5)]
        self.saved_host, self.saved_guests = load_selection(data_path / 'selection.json')
        root.title(f'UE PartyUp PC {__version__} — private preview')
        root.geometry('1110x860')
        root.minsize(850, 720)
        frame = ttk.Frame(root, padding=18)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='UE PartyUp PC', font=('Segoe UI', 23, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Up to 10 speakers · Private testing preview · Hardware verification still in progress',
                  padding=(0, 3, 0, 12)).pack(anchor='w')
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill='x')
        self.button(toolbar, 'Find speakers', self.refresh).pack(side='left', padx=(0, 12))
        toggle = ttk.Checkbutton(toolbar, text='Enable experimental older-speaker compatibility',
                                 variable=self.experimental, command=self.update_enabled)
        toggle.pack(side='left')
        self.controls.append((toggle, 'normal'))
        ttk.Label(toolbar, text='Speaker controls:').pack(side='left', padx=(18, 5))
        self.device_combo = ttk.Combobox(toolbar, state='readonly', width=28)
        self.device_combo.pack(side='left', fill='x', expand=True)
        self.controls.append((self.device_combo, 'readonly'))
        self.device_combo.bind('<<ComboboxSelected>>', self.device_changed)
        self.button(toolbar, 'Read controls', self.read_controls).pack(side='left', padx=(8, 0))
        self.notebook = ttk.Notebook(frame)
        self.notebook.pack(fill='both', expand=True, pady=12)
        tabs = {}
        for name in ('Group', 'Speaker', 'Sound', 'PartyUp settings'):
            tab = ttk.Frame(self.notebook, padding=14)
            self.notebook.add(tab, text=name)
            tabs[name] = tab
        self.build_group(tabs['Group'])
        self.build_device(tabs['Speaker'])
        self.build_sound(tabs['Sound'])
        self.build_partyup(tabs['PartyUp settings'])
        ttk.Label(frame, textvariable=self.status, wraplength=1040).pack(anchor='w', pady=(0, 7))
        self.log = ScrolledText(frame, height=6, state='disabled', font=('Segoe UI', 9), wrap='word')
        self.log.pack(fill='x')
        ttk.Label(frame, text='Close the phone app before connecting. Closing this window leaves the speaker group playing.',
                  padding=(0, 8, 0, 0)).pack(anchor='w')
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.update_enabled()
        self.poll()

    def button(self, parent, label, command, feature=None):
        button = ttk.Button(parent, text=label, command=command)
        self.controls.append((button, 'normal'))
        if feature:
            self.feature_widgets.setdefault(feature, []).append(button)
        return button

    def register(self, widget, feature=None, state='normal'):
        self.controls.append((widget, state))
        if feature:
            self.feature_widgets.setdefault(feature, []).append(widget)
        return widget

    def build_group(self, tab):
        ttk.Label(tab, text='Choose the main speaker that Windows plays audio through, then select up to nine guests.',
                  wraplength=990).pack(anchor='w')
        top = ttk.Frame(tab)
        top.pack(fill='x', pady=10)
        ttk.Label(top, text='Main speaker').pack(side='left', padx=(0, 8))
        self.host_combo = self.register(ttk.Combobox(top, state='readonly', width=42), state='readonly')
        self.host_combo.pack(side='left')
        self.host_combo.bind('<<ComboboxSelected>>', self.host_changed)
        ttk.Label(top, textvariable=self.group_count).pack(side='left', padx=16)
        body = ttk.Frame(tab)
        body.pack(fill='both', expand=True)
        available = ttk.LabelFrame(body, text='Available paired speakers', padding=8)
        available.pack(side='left', fill='both', padx=(0, 12))
        self.guest_list = self.register(tk.Listbox(available, selectmode='multiple', exportselection=False,
                                                 height=12, width=33, font=('Segoe UI', 10)))
        self.guest_list.pack(fill='both', expand=True)
        self.guest_list.bind('<<ListboxSelect>>', self.guests_changed)
        ttk.Label(available, text='Click a speaker to select or deselect it.\nSelections are remembered locally.',
                  wraplength=285).pack(anchor='w', pady=(7, 0))
        members = ttk.LabelFrame(body, text='Group and member results', padding=8)
        members.pack(side='left', fill='both', expand=True)
        self.member_tree = self.register(ttk.Treeview(members, columns=('role', 'speaker', 'state', 'battery'),
                                                    show='headings', selectmode='extended', height=10))
        for key, label, width in [('role', 'Role', 55), ('speaker', 'Speaker', 210),
                                  ('state', 'Last confirmed result', 240), ('battery', 'Battery', 100)]:
            self.member_tree.heading(key, text=label)
            self.member_tree.column(key, width=width, minwidth=45, stretch=key != 'role')
        self.member_tree.pack(fill='both', expand=True)
        self.member_tree.bind('<<TreeviewSelect>>', self.member_selected)
        self.member_detail = tk.StringVar(value='Select a member to see its detailed result.')
        ttk.Label(members, textvariable=self.member_detail, wraplength=650).pack(anchor='w', pady=8)
        self.button(members, 'Remove selected members', lambda: self.group_action('remove', from_members=True)).pack(anchor='w')
        channel_row = ttk.Frame(members)
        channel_row.pack(fill='x', pady=(8, 0))
        ttk.Label(channel_row, text='Selected guest channel:').pack(side='left')
        self.channel_combo = self.register(ttk.Combobox(channel_row, state='readonly', width=9,
                                                      values=('Left', 'Right', 'Center')), state='readonly')
        self.channel_combo.current(2)
        self.channel_combo.pack(side='left', padx=6)
        self.channel_button = self.button(channel_row, 'Apply channel', self.apply_channel)
        self.channel_button.pack(side='left')
        actions = ttk.Frame(tab)
        actions.pack(fill='x', pady=(12, 0))
        for label, action in [('Start PartyUp', 'start'), ('Add selected guests', 'add'),
                              ('Check group', 'status'), ('Stop PartyUp', 'stop')]:
            self.button(actions, label, lambda action=action: self.group_action(action)).pack(side='left', padx=(0, 8))
        ttk.Label(tab, text='A successful write is shown separately from a receiver report. Confirm playback by listening. '
                  'Older models are experimental until tested on the exact hardware.', wraplength=995).pack(anchor='w', pady=(10, 0))

    def build_device(self, tab):
        ttk.Label(tab, textvariable=self.device_summary, wraplength=995).pack(anchor='w', pady=(0, 12))
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
                    silent=self.silent_power.get() and not self.selected_snapshot.get('experimental', False)), 'power').pack(side='left')
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
        volume = ttk.LabelFrame(tab, text='Speaker volume', padding=10)
        volume.pack(fill='x', pady=(0, 10))
        self.volume_scale = self.register(ttk.Scale(volume, from_=0, to=31, variable=self.volume), 'volume')
        self.volume_scale.pack(side='left', fill='x', expand=True, padx=(0, 10))
        self.volume_text = tk.StringVar(value='Unknown')
        ttk.Label(volume, textvariable=self.volume_text, width=12).pack(side='left')
        self.volume.trace_add('write', lambda *_: self.update_volume_label())
        self.button(volume, 'Apply volume', self.apply_volume, 'volume').pack(side='left')
        eq = ttk.LabelFrame(tab, text='EQ preset and custom EQ', padding=10)
        eq.pack(fill='x', pady=(0, 10))
        top = ttk.Frame(eq)
        top.pack(fill='x')
        ttk.Label(top, text='Preset:').pack(side='left', padx=(0, 5))
        self.eq_combo = self.register(ttk.Combobox(top, state='readonly', width=30), 'eq', state='readonly')
        self.eq_combo.pack(side='left', padx=(0, 10))
        self.button(top, 'Apply EQ', self.apply_eq, 'eq').pack(side='left')
        bands = ttk.Frame(eq)
        bands.pack(fill='x', pady=12)
        for number, value in enumerate(self.eq_bands, 1):
            box = ttk.Frame(bands)
            box.pack(side='left', fill='x', expand=True, padx=6)
            ttk.Label(box, text=f'Band {number}').pack()
            scale = self.register(ttk.Scale(box, from_=127, to=-128, orient='vertical', variable=value), 'eq')
            scale.pack()
            label = tk.StringVar(value='0')
            value.trace_add('write', lambda *_, value=value, label=label: label.set(str(round(value.get()))))
            ttk.Label(box, textvariable=label).pack()
        outdoor = ttk.LabelFrame(tab, text='Outdoor mode', padding=10)
        outdoor.pack(fill='x')
        self.register(ttk.Checkbutton(outdoor, text='Outdoor mode', variable=self.outdoor), 'outdoor').pack(side='left')
        self.button(outdoor, 'Apply outdoor mode', lambda: self.setting('set_outdoor', self.outdoor.get()), 'outdoor').pack(side='left', padx=10)
        ttk.Label(tab, text='Moving a slider changes its pending value. Apply sends one setting, then reads the speaker back.',
                  wraplength=995).pack(anchor='w', pady=10)
        ttk.Label(tab, text='Custom EQ bands use the speaker’s raw levels; these values are not decibels.', wraplength=995).pack(anchor='w')

    def build_partyup(self, tab):
        ttk.Label(tab, text='These controls apply to the speaker selected in “Speaker controls” above.', wraplength=995).pack(anchor='w', pady=(0, 10))
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
        self.register(ttk.Scale(balance, from_=-128, to=127, variable=self.balance), 'stereo_balance').pack(side='left', fill='x', expand=True, padx=10)
        self.button(balance, 'Apply balance', lambda: self.setting('set_stereo_balance', round(self.balance.get())), 'stereo_balance').pack(side='left', padx=10)
        ttk.Label(tab, text='Balance direction and current-value readback have not been established. '
                  'Balance writes require a supported model and explicit experimental opt-in. '
                  'Mixed-model grouping and groups larger than two still require hardware acceptance.', wraplength=995).pack(anchor='w', pady=10)

    def append_log(self, text):
        self.log.configure(state='normal')
        self.log.insert('end', f'{datetime.now():%H:%M:%S}  {text}\n')
        self.log.see('end')
        self.log.configure(state='disabled')

    def worker(self, kind, task):
        if self.busy:
            return
        self.busy = True
        self.update_enabled()
        def execute():
            try:
                self.events.put((kind, task()))
            except Exception as exc:
                self.events.put(('error', str(exc)))
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
        self.member_detail.set('Check group to load results for the selected main speaker.')
        self.update_enabled()

    def guests_changed(self, _=None):
        count = len(self.guest_list.curselection())
        total = count + int(0 <= self.host_combo.current() < len(self.speakers))
        self.group_count.set(f'{count} guests selected · {total} total · maximum 10')
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

    def group_action(self, action, from_members=False):
        try:
            host = self.host()
            guests = self.selected_guests()
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

    def read_controls(self):
        try:
            speaker, experimental = self.selected_device(), self.experimental.get()
            self.status.set(f'Reading controls from {speaker.label}…')
            async def inspect():
                from .controls import settings_session
                async with settings_session(speaker, experimental=experimental) as settings:
                    return speaker, await settings.snapshot()
            self.worker('snapshot', lambda: asyncio.run(inspect()))
        except ValueError as exc:
            self.status.set(str(exc))

    def setting(self, method, *args, **kwargs):
        try:
            speaker, experimental = self.selected_device(), self.experimental.get()
            if not self.selected_snapshot:
                raise ValueError('Read this speaker’s controls before changing a setting.')
            self.remember()
            self.status.set(f'Applying {method.replace("_", " ")} to {speaker.label}…')
            async def apply():
                from .controls import settings_session
                async with settings_session(speaker, experimental=experimental) as settings:
                    await getattr(settings, method)(*args, **kwargs)
                    if method == 'power_off':
                        return speaker, {'powered_off': True, 'capabilities': {}, 'errors': {}}
                    return speaker, await settings.snapshot()
            self.worker('snapshot', lambda: asyncio.run(apply()))
        except ValueError as exc:
            self.status.set(str(exc))

    def apply_sleep(self):
        index = self.sleep_entry.current()
        if not 0 <= index < len(self.sleep_choices):
            self.status.set('Choose a sleep timer preset.')
            return
        self.setting('set_sleep_timer', self.sleep_choices[index][1])

    def apply_volume(self):
        try:
            self.setting('set_volume', round(self.volume.get()))
        except (ValueError, tk.TclError):
            self.status.set('Enter a whole-number volume level.')

    def update_volume_label(self):
        maximum = self.selected_snapshot.get('max_volume')
        if self.selected_snapshot.get('volume') is None or not isinstance(maximum, (int, float)) or maximum <= 0:
            self.volume_text.set('Unknown')
        else:
            self.volume_text.set(f'{round(self.volume.get() * 100 / maximum)}%')

    def apply_eq(self):
        index = self.eq_combo.current()
        if not 0 <= index < len(self.eq_choices):
            self.status.set('Choose a supported EQ preset first.')
            return
        self.setting('set_eq', self.eq_choices[index][1], tuple(round(value.get()) for value in self.eq_bands))

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

    @staticmethod
    def set_widget_state(widget, state):
        if isinstance(widget, ttk.Treeview):
            widget.state(['disabled'] if state == 'disabled' else ['!disabled'])
        else:
            widget.configure(state=state)

    def render_snapshot(self, speaker, snapshot):
        self.selected_snapshot = snapshot
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
        host_detail = next((member.detail for member in result.members if member.speaker.address == host.address and member.detail),
                           'Windows audio should play through this speaker.')
        rows = [(host, 'Main', state, host_detail)]
        rows += [(member.speaker, 'Guest', member.state, member.detail) for member in result.members if member.speaker.address != host.address]
        for speaker, role, member_state, detail in rows:
            key = str(speaker.address)
            battery = format_value(self.snapshots.get(speaker.address, {}).get('battery'))
            self.member_tree.insert('', 'end', iid=key, values=(role, speaker.label, member_state, battery), tags=(detail or member_state,))
            self.member_speakers[key] = speaker
        self.status.set(str(result).split('\n')[0])
        self.append_log(str(result))

    def poll(self):
        try:
            while True:
                kind, result = self.events.get_nowait()
                if kind == 'progress':
                    self.status.set(result)
                    self.append_log(result)
                    continue
                self.busy = False
                # Temporarily enable entries so values can be updated before capability gating.
                for widget, state in self.controls:
                    self.set_widget_state(widget, state)
                if kind == 'error':
                    self.status.set(result)
                    self.append_log(f'Operation failed: {result}')
                elif kind == 'discovery':
                    self.show_discovery(*result)
                elif kind == 'group':
                    self.show_group(result)
                elif kind == 'message':
                    self.status.set(str(result) if result else 'Channel command accepted; confirm playback by listening.')
                    self.append_log(self.status.get())
                elif kind == 'snapshot':
                    speaker, snapshot = result
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
        self.root.after(100, self.poll)

    def close(self):
        if self.busy:
            messagebox.showinfo('Operation in progress', 'Please wait for the speaker operation to finish before closing.', parent=self.root)
        else:
            self.root.destroy()


def main(smoke=False):
    root = tk.Tk()
    app = PartyUpApp(root)
    if smoke:
        root.withdraw()
        root.after(150, root.destroy)
    else:
        root.after(150, app.refresh)
    root.mainloop()
