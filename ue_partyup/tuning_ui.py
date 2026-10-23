"""Quick-tuning widgets and worker integration; no startup device activity."""
import asyncio
import tkinter as tk
from tkinter import ttk
from .tuning import TuningState, TuneResult, eq_value, transact
from .settings import EQInfo, EQ_PRESETS


class TuningUI:
    def build_tuning(self, parent):
        card = ttk.LabelFrame(parent, text='Quick tuning', padding=10)
        card.pack(fill='x', pady=(0, 10))
        self.tuning_text = tk.StringVar(value='Read EQ to begin. Controls affect only the selected speaker.')
        ttk.Label(card, textvariable=self.tuning_text, style='Micro.TLabel', wraplength=970).pack(anchor='w')
        row = ttk.Frame(card); row.pack(fill='x', pady=(6, 0))
        self.tune_minus = self.button(row, 'Bass -', lambda: self.tune_action('nudge', delta=-1))
        self.tune_minus.pack(side='left')
        self.tune_plus = self.button(row, 'Bass +', lambda: self.tune_action('nudge', delta=1))
        self.tune_plus.pack(side='left', padx=(5, 12))
        self.tune_undo = self.button(row, 'Undo', lambda: self.tune_action('undo'))
        self.tune_undo.pack(side='left', padx=(0, 5))
        self.tune_reset = self.button(row, 'Reset changes', lambda: self.tune_action('reset'))
        self.tune_reset.pack(side='left', padx=(0, 5))
        self.button(row, 'Read EQ', self.read_sound_controls).pack(side='left', padx=(0, 5))
        self.tune_save = self.button(row, 'Save as...', self.save_tuning_as)
        self.tune_save.pack(side='left')
        ttk.Label(card, text='Keeps the selected preset. Factory-preset band effect is unverified; steps are not dB.',
                  style='Muted.TLabel', wraplength=970).pack(anchor='w', pady=(4, 0))

    def update_tuning_controls(self):
        if not hasattr(self, 'tune_plus'):
            return
        caps = self.selected_snapshot.get('capabilities', {})
        supported = bool(caps.get('eq')) if isinstance(caps,dict) else 'eq' in caps
        ready = self.tuning.ready and not self.busy and supported
        for widget, allowed in ((self.tune_minus, ready and self.tuning.current.bands[0] > -128),
                                (self.tune_plus, ready and self.tuning.current.bands[0] < 127),
                                (self.tune_undo, ready and bool(self.tuning.history)),
                                (self.tune_reset, ready and self.tuning.current != self.tuning.start),
                                (self.tune_save, ready)):
            widget.configure(state='normal' if allowed else 'disabled')
        if self.tuning.target in self.tuning.blocked:
            for feature in ('eq','eq_band'):
                for widget in self.feature_widgets.get(feature,[]):
                    widget.configure(state='disabled')
            text = 'Change unconfirmed. Read EQ before another adjustment.'
        elif self.tuning.pending:
            text = 'Checking the selected speaker, then applying one change...'
        elif self.tuning.current is not None:
            eq = self.tuning.current
            delta = eq.bands[0] - self.tuning.start.bands[0]
            try: name = self.selected_device().name
            except ValueError: name = 'Selected speaker'
            try: role = 'Main' if self.selected_device().address == self.host().address else 'Guest / selected'
            except ValueError: role = 'Selected'
            text = f'Confirmed {role}: {name} only | {EQ_PRESETS.get(eq.mode, "Unknown preset")} | Bass {delta:+d} steps from starting sound'
        else:
            text = 'Read EQ to begin. Controls affect only the selected speaker.'
        self.tuning_text.set(text)

    def tune_action(self, action, delta=0, destination=None):
        if self.busy or not self.tuning.ready:
            return
        try:
            speaker = self.selected_device()
            expected = self.tuning.current
            if action == 'undo':
                if not self.tuning.history: return
                destination = self.tuning.history[-1]
            elif action == 'reset': destination = self.tuning.start
            if action == 'nudge' and not -128 <= expected.bands[0] + delta <= 127:
                self.status.set('Bass is at its protocol limit.'); return
            preserve = True
            experimental = self.experimental.get()
            group_host = self.host().address
            self.tuning.pending = True
            async def apply():
                from .controls import settings_session
                try:
                    async with settings_session(speaker, experimental=experimental, group_host=group_host) as settings:
                        result = await transact(settings, expected, action, delta=delta,
                                                preserve=preserve, destination=destination)
                except (Exception, asyncio.CancelledError) as error:
                    result = TuneResult(problem=str(error) or 'Connection canceled.')
                return speaker, action, result
            self.status.set('Reading current EQ before the adjustment...')
            self.worker('tuning', lambda: asyncio.run(apply()))
        except ValueError as error:
            self.tuning.pending = False
            self.status.set(str(error))

    def accept_tuning(self, result):
        speaker, action, outcome = result
        try: selected = self.selected_device().address == speaker.address
        except ValueError: selected = False
        if selected:
            self.tuning.finish(outcome, action)
        else:
            self.tuning.pending = False
            if outcome.problem: self.tuning.blocked.add(speaker.address)
        snapshot = dict(self.snapshots.get(speaker.address, {}))
        snapshot['eq'] = outcome.after
        errors = dict(snapshot.get('errors', {}))
        if outcome.problem:
            errors['eq'] = outcome.problem
            message = 'EQ change unconfirmed. Read EQ before another adjustment.'
        elif outcome.conflict:
            errors.pop('eq', None)
            message = 'Speaker EQ changed since the last reading. Refreshed starting sound; no write sent. Try again.'
        else:
            errors.pop('eq', None)
            message = 'EQ setting confirmed by speaker readback. Confirm the sound by listening.'
        snapshot['errors'] = errors
        self.snapshots[speaker.address] = snapshot
        if selected: self.render_snapshot(speaker, snapshot)
        self.status.set(message); self.append_log(message)

    def save_tuning_as(self):
        if self.busy or not self.tuning.ready: return
        dialog = tk.Toplevel(self.root); dialog.title('Save sound preset')
        ttk.Label(dialog, text='Preset name').pack(padx=18, pady=(15, 5))
        entry = ttk.Entry(dialog, width=28); entry.pack(padx=18); entry.focus_set()
        address, eq = self.tuning.target, self.tuning.current
        def save():
            if self.busy or self.tuning.target != address or not self.tuning.ready or self.tuning.current != eq:
                self.status.set('Tuning target changed. Close this dialog and save the current sound.'); return
            try:
                self.eq_profiles.save(entry.get(), eq.bands, mode=eq.mode)
                self.memory_combo.configure(values=list(self.eq_profiles.load()))
                self.memory_combo.set(entry.get().strip())
                self.status.set('Confirmed sound saved on this PC. Volume unchanged.')
                dialog.destroy()
            except (OSError, ValueError) as error: self.status.set(str(error))
        from .house_widgets import PocketButton
        PocketButton(dialog, 'Save preset', save, width=170).pack(padx=18, pady=15)
