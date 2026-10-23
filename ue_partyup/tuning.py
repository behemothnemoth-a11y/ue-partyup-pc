"""Confirmed EQ tuning state and bounded, single-write transactions."""
import asyncio
from dataclasses import dataclass
from .settings import EQInfo


def eq_value(value):
    if value is None:
        return None
    return EQInfo(value['mode'], tuple(value['bands'])) if isinstance(value, dict) else EQInfo(value.mode, tuple(value.bands))


@dataclass
class TuneResult:
    before: EQInfo | None = None
    after: EQInfo | None = None
    problem: str = ''
    conflict: bool = False


class TuningState:
    def __init__(self):
        self.target = None
        self.start = self.current = None
        self.history = []
        self.blocked = set()
        self.pending = False

    def select(self, address):
        if address != self.target:
            self.target = address
            self.start = self.current = None
            self.history.clear()

    def observe(self, address, value, fresh=False):
        self.select(address)
        value = eq_value(value)
        if value is None:
            return
        if fresh:
            self.blocked.discard(address)
        if address in self.blocked or self.pending:
            return
        if self.current is not None and self.current != value:
            self.history.clear()
            self.start = value
        if self.start is None:
            self.start = value
        self.current = value

    @property
    def ready(self):
        return self.current is not None and not self.pending and self.target not in self.blocked

    def finish(self, result, action):
        self.pending = False
        if result.problem:
            self.blocked.add(self.target)
            self.current = None
            self.history.clear()
            return
        if result.conflict:
            self.history.clear()
            self.start = self.current = result.after
            return
        if result.after != result.before:
            if action == 'undo':
                self.history.pop()
            elif action == 'reset':
                self.history.clear()
            else:
                self.history.append(result.before)
                self.history = self.history[-20:]
        self.current = result.after


async def transact(settings, expected, action, *, delta=0, preserve=True, destination=None):
    """Fresh read, advertise check, one mutation, exact readback. Never retry writes."""
    before = None
    try:
        before = eq_value(await settings.eq())
        if before != expected:
            return TuneResult(before, before, conflict=True)
        modes = await settings.eq_modes()
        if action == 'nudge':
            bands = list(before.bands)
            if delta not in (-1, 1):
                raise ValueError('Use one step per click.')
            bands[0] += delta
            if not -128 <= bands[0] <= 127:
                raise ValueError('Bass is at its protocol limit.')
            target = EQInfo(before.mode if preserve else 4, tuple(bands))
        else:
            target = destination
        if target is None or target.mode not in modes:
            raise ValueError('This speaker does not advertise the requested preset.')
        if target == before:
            return TuneResult(before, before)
        await settings.set_eq(target.mode, target.bands)
        after = eq_value(await settings.eq())
        if after != target:
            return TuneResult(before, None, 'Speaker readback differs from the requested setting.')
        return TuneResult(before, after)
    except (Exception, asyncio.CancelledError) as error:
        return TuneResult(before, None, str(error) or 'Bluetooth operation canceled.')
