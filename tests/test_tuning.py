import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from ue_partyup.settings import EQInfo
from ue_partyup.tuning import TuningState, TuneResult, transact

METAL = EQInfo(5,(113,76,-25,29,98))
MORE = EQInfo(5,(114,76,-25,29,98))


class StateTests(unittest.TestCase):
    def setUp(self):
        self.state=TuningState();self.state.observe(1,METAL,fresh=True)

    def test_undo_and_reset_track_only_confirmed_changes(self):
        s=self.state;s.pending=True;s.finish(TuneResult(METAL,MORE),'nudge')
        self.assertEqual(s.history,[METAL]);self.assertEqual(s.start,METAL)
        s.finish(TuneResult(MORE,METAL),'undo')
        self.assertEqual(s.history,[]);self.assertEqual(s.current,METAL)
        s.finish(TuneResult(METAL,MORE),'nudge')
        s.finish(TuneResult(MORE,METAL),'reset')
        self.assertEqual(s.history,[])

    def test_uncertain_write_requires_fresh_read_even_after_target_switch(self):
        s=self.state;s.finish(TuneResult(METAL,problem='timeout'),'nudge')
        self.assertFalse(s.ready)
        s.observe(2,METAL);s.observe(1,METAL)
        self.assertFalse(s.ready)
        s.observe(1,MORE,fresh=True)
        self.assertTrue(s.ready);self.assertEqual(s.history,[])

    def test_target_change_and_external_change_clear_undo(self):
        s=self.state;s.finish(TuneResult(METAL,MORE),'nudge')
        s.observe(2,METAL)
        self.assertEqual(s.history,[]);self.assertEqual(s.start,METAL)
        s.finish(TuneResult(METAL,MORE),'nudge')
        s.observe(2,EQInfo(3,(0,0,0,0,0)),fresh=True)
        self.assertEqual(s.history,[]);self.assertEqual(s.start.mode,3)

    def test_conflict_uses_fresh_start_without_undo(self):
        s=self.state;s.finish(TuneResult(MORE,MORE,conflict=True),'nudge')
        self.assertEqual(s.current,MORE);self.assertEqual(s.start,MORE)
        self.assertEqual(s.history,[])


class TransactionTests(unittest.IsolatedAsyncioTestCase):
    def settings(self, after=MORE):
        return SimpleNamespace(eq=AsyncMock(side_effect=[METAL,after]),
            eq_modes=AsyncMock(return_value=(3,4,5)),set_eq=AsyncMock())

    async def test_fresh_read_and_single_write_preserve_mode_and_other_bands(self):
        c=self.settings();r=await transact(c,METAL,'nudge',delta=1)
        c.set_eq.assert_awaited_once_with(5,MORE.bands)
        self.assertEqual(r.after,MORE);self.assertEqual(c.eq.await_count,2)
        self.assertFalse(hasattr(c,'set_volume'))

    async def test_external_change_prevents_write(self):
        c=self.settings();c.eq.side_effect=[MORE]
        r=await transact(c,METAL,'nudge',delta=1)
        self.assertTrue(r.conflict);c.set_eq.assert_not_awaited()

    async def test_timeout_never_retries_write(self):
        c=self.settings();c.set_eq.side_effect=TimeoutError('late')
        r=await transact(c,METAL,'nudge',delta=1)
        self.assertEqual(r.problem,'late');c.set_eq.assert_awaited_once()
        self.assertIsNone(r.after)

    async def test_readback_failure_and_mismatch_stay_unconfirmed(self):
        for second in (TimeoutError('read failed'),METAL):
            c=self.settings();c.eq.side_effect=[METAL,second]
            r=await transact(c,METAL,'nudge',delta=1)
            self.assertTrue(r.problem);self.assertIsNone(r.after)

    async def test_cancelled_bluetooth_operation_returns_failure(self):
        c=self.settings();c.set_eq.side_effect=asyncio.CancelledError()
        r=await transact(c,METAL,'nudge',delta=1)
        self.assertTrue(r.problem)

    async def test_no_write_at_limit_or_for_unadvertised_mode(self):
        c=self.settings();limit=EQInfo(5,(127,0,0,0,0));c.eq.side_effect=[limit]
        r=await transact(c,limit,'nudge',delta=1)
        self.assertTrue(r.problem);c.set_eq.assert_not_awaited()
        c=self.settings();c.eq_modes.return_value=(3,4)
        r=await transact(c,METAL,'nudge',delta=1)
        self.assertTrue(r.problem);c.set_eq.assert_not_awaited()

    async def test_custom_opt_in_and_reset_use_exact_destination(self):
        custom=EQInfo(4,MORE.bands);c=self.settings(after=custom)
        r=await transact(c,METAL,'nudge',delta=1,preserve=False)
        self.assertEqual(r.after,custom)
        c=self.settings(after=METAL);c.eq.side_effect=[MORE,METAL]
        r=await transact(c,MORE,'reset',destination=METAL)
        c.set_eq.assert_awaited_once_with(5,METAL.bands)
        self.assertEqual(r.after,METAL)
