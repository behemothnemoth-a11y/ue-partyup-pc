"""Selection and native UI checks; no speaker connections or control writes."""
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch, AsyncMock
from types import SimpleNamespace
from ue_partyup.app import PartyUpApp, load_selection, parse_mac, format_value
from ue_partyup.controller import Speaker
from ue_partyup.settings import BatteryInfo, EQInfo
from ue_partyup.groups import GroupResult, MemberResult


class SelectionTests(unittest.TestCase):
    def test_older_pair_selection_migrates_to_guest_list(self):
        with patch.object(Path, 'read_text', return_value=json.dumps({'host': 1, 'guest': 2})):
            self.assertEqual(load_selection(Path('unused-selection.json')), (1, [2]))

    def test_selection_rejects_duplicates_host_and_invalid_addresses(self):
        with patch.object(Path, 'read_text', return_value=json.dumps({'host': 1, 'guests': [1, 2, 2, -1, 0, True, 1 << 48, '3']})):
            self.assertEqual(load_selection(Path('unused-selection.json')), (1, [2]))

    def test_selection_never_restores_more_than_nine_guests(self):
        with patch.object(Path, 'read_text', return_value=json.dumps({'host': 1, 'guests': list(range(2, 14))})):
            self.assertEqual(load_selection(Path('unused-selection.json')), (1, list(range(2, 11))))

    def test_bad_selection_is_ignored(self):
        with patch.object(Path, 'read_text', return_value='not JSON'):
            self.assertEqual(load_selection(Path('unused-selection.json')), (None, []))

    def test_source_address_parsing(self):
        self.assertEqual(parse_mac('01:23:45:67:89:AB'), 0x0123456789AB)
        self.assertEqual(parse_mac('01-23-45-67-89-ab'), 0x0123456789AB)
        for value in ('', '00:00:00:00:00:00', 'not a radio', '123'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_mac(value)

    def test_battery_unknown_is_not_shown_as_zero(self):
        self.assertEqual(format_value(BatteryInfo(255, 255, 0)), 'Charge unknown · Not charging')
        self.assertEqual(format_value(BatteryInfo(75, 74, 2)), '74% · Fast charging')


class AppTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            self.skipTest(f'Native display unavailable: {error}')
        self.root.withdraw()
        self.file_patches = [patch.object(Path, 'read_text', side_effect=FileNotFoundError),
                             patch.object(Path, 'mkdir'), patch.object(Path, 'write_text')]
        for file_patch in self.file_patches:
            file_patch.start()
        self.discovery = patch('ue_partyup.app.discover')
        self.discover = self.discovery.start()
        self.app = PartyUpApp(self.root, Path('unused-test-data'))

    def tearDown(self):
        self.discovery.stop()
        self.root.destroy()
        for file_patch in reversed(self.file_patches):
            file_patch.stop()

    def test_construction_performs_no_discovery_or_speaker_io(self):
        self.discover.assert_not_called()
        self.assertFalse(self.app.busy)
        self.assertEqual(len(self.app.notebook.tabs()), 5)
        self.assertTrue(self.app.volume_scale.instate(['disabled']))
        self.assertEqual(self.app.device_combo.get(), '')

    def test_activity_history_keeps_recent_lines_without_unbounded_growth(self):
        from ue_partyup.app import MAX_LOG_LINES
        self.app.append_log('\n'.join(f'entry-{i}' for i in range(MAX_LOG_LINES+100)))
        text = self.app.log.get('1.0', 'end-1c')
        self.assertEqual(len(text.splitlines()), MAX_LOG_LINES)
        self.assertNotIn('entry-0\n', text)
        self.assertIn(f'entry-{MAX_LOG_LINES+99}', text)

    def test_hidden_activity_does_not_request_scroll_redraw(self):
        with patch.object(self.app.log, 'see') as scroll:
            self.app.append_log('Hidden activity still records results.')
        scroll.assert_not_called()
        self.assertIn('Hidden activity', self.app.log.get('1.0', 'end-1c'))

    def test_idle_queue_poll_backs_off_and_active_poll_is_responsive(self):
        from ue_partyup.app import IDLE_POLL_MS, BUSY_POLL_MS
        with patch.object(self.root, 'after') as schedule:
            self.app.poll()
            self.assertEqual(schedule.call_args.args[0], IDLE_POLL_MS)
            self.app.busy = True
            self.app.poll()
            self.assertEqual(schedule.call_args.args[0], BUSY_POLL_MS)
        self.discover.assert_not_called()

    def test_large_event_burst_yields_without_losing_pending_messages(self):
        from ue_partyup.app import MAX_EVENTS_PER_TICK
        for i in range(MAX_EVENTS_PER_TICK+1):
            self.app.events.put(('progress', str(i)))
        with patch.object(self.root, 'after') as schedule, patch.object(self.app, 'append_log'):
            self.app.poll()
        self.assertEqual(self.app.events.qsize(), 1)
        self.assertEqual(self.app.status.get(), str(MAX_EVENTS_PER_TICK-1))
        self.assertEqual(schedule.call_args.args[0], 10)

    def test_redesigned_tabs_scroll_and_group_actions_stay_visible(self):
        self.assertEqual(set(self.app.tab_viewports),
                         {'Group', 'Speaker', 'Sound', 'PartyUp settings', 'Guide'})
        footer = self.app.tab_viewports['Group'].footer
        labels = [child.cget('text')
                  for row in footer.winfo_children() for child in row.winfo_children()
                  if isinstance(child, ttk.Button)]
        self.assertEqual(labels, ['Start PartyUp', 'Add selected guests',
                                  'Check group', 'Stop PartyUp'])
        self.assertEqual(self.app.tab_viewports['Group'].canvas.cget('height'), '220')

    def test_status_badge_does_not_invent_active_audio(self):
        self.app.show_discovery([Speaker(1), Speaker(2)], [])
        self.assertEqual(self.app.device_count.get(), '2 PAIRED RECORDS')
        self.assertEqual(self.app.group_status.get(), 'STATUS NOT CHECKED')
        self.app.show_group(GroupResult('status', True, [
            MemberResult(Speaker(2), 'reported by main speaker')]))
        self.assertEqual(self.app.group_status.get(), 'BROADCAST ON')
        self.app.clear_group_results()
        self.assertEqual(self.app.group_status.get(), 'STATUS NOT CHECKED')

    def test_more_than_nine_guests_cannot_start_worker(self):
        speakers = [Speaker(index) for index in range(1, 12)]
        self.app.show_discovery(speakers, [])
        self.app.guest_list.selection_set(0, 'end')
        with patch.object(self.app, 'worker') as worker:
            self.app.group_action('start')
        worker.assert_not_called()
        self.assertIn('no more than nine', self.app.status.get())

    def test_changing_host_excludes_it_from_guest_list(self):
        self.app.show_discovery([Speaker(1), Speaker(2), Speaker(3)], [])
        self.app.host_combo.current(1)
        self.app.host_changed()
        self.assertEqual([speaker.address for speaker in self.app.guest_choices], [1, 3])
        self.assertNotIn(2, self.app.saved_guests)

    def test_changing_host_invalidates_old_member_actions(self):
        self.app.show_discovery([Speaker(1), Speaker(2), Speaker(3)], [])
        self.app.show_group(GroupResult('status', True, [MemberResult(Speaker(2), 'reported by main speaker')]))
        self.app.member_tree.selection_set('1')
        self.app.host_combo.current(1)
        self.app.host_changed()
        self.assertEqual(self.app.member_tree.get_children(), ())
        self.assertEqual(self.app.member_speakers, {})
        self.assertTrue(self.app.channel_button.instate(['disabled']))
        with patch.object(self.app, 'worker') as worker:
            self.app.group_action('remove', from_members=True)
            self.app.apply_channel()
        worker.assert_not_called()

    def test_refinding_speakers_invalidates_old_member_actions(self):
        self.app.show_discovery([Speaker(1), Speaker(2)], [])
        self.app.show_group(GroupResult('status', True, [MemberResult(Speaker(2), 'reported by main speaker')]))
        self.app.show_discovery([Speaker(2), Speaker(3)], [])
        self.assertEqual(self.app.member_tree.get_children(), ())
        self.assertEqual(self.app.member_speakers, {})

    def test_getter_failure_disables_volume_instead_of_using_zero(self):
        speaker = Speaker(1)
        self.app.show_discovery([speaker], [])
        self.app.render_snapshot(speaker, {'capabilities': {'volume': True}, 'volume': None, 'errors': {'volume': 'timeout'}})
        self.assertTrue(self.app.volume_scale.instate(['disabled']))
        self.assertIn('Not available', self.app.device_summary.get())

    def test_eq_snapshot_uses_advertised_wire_codes_and_current_bands(self):
        speaker = Speaker(1)
        self.app.show_discovery([speaker], [])
        self.app.render_snapshot(speaker, {'capabilities': {'eq': True}, 'eq': EQInfo(4, (-5, 0, 1, 2, 3)),
                                          'supported_eq_modes': (3, 4), 'errors': {}})
        self.assertEqual(self.app.eq_combo.get(), 'Custom')
        self.assertEqual(self.app.eq_choices, [('Standard', 3), ('Custom', 4)])
        self.assertEqual([value.get() for value in self.app.eq_bands], [-5, 0, 1, 2, 3])

    def test_eq_getter_failure_cannot_send_zero_bands(self):
        speaker = Speaker(1)
        self.app.show_discovery([speaker], [])
        self.app.render_snapshot(speaker, {'capabilities': {'eq': True}, 'eq': None,
                                          'supported_eq_modes': (3, 4), 'errors': {'eq': 'timeout'}})
        self.assertTrue(self.app.eq_combo.instate(['disabled']))

    def test_sleep_preset_never_sends_zero_minutes(self):
        speaker = Speaker(1)
        self.app.show_discovery([speaker], [])
        self.app.render_snapshot(speaker, {'capabilities': {'sleep_timer': True}, 'sleep_timer': 0, 'errors': {}})
        self.assertEqual(self.app.sleep_entry.get(), 'Never')
        with patch.object(self.app, 'setting') as setting:
            self.app.apply_sleep()
        setting.assert_called_once_with('set_sleep_timer', 0)

    def test_volume_uses_device_step_range(self):
        speaker = Speaker(1)
        self.app.show_discovery([speaker], [])
        self.app.render_snapshot(speaker, {'capabilities': {'volume': True}, 'volume': 9, 'max_volume': 31, 'errors': {}})
        self.assertFalse(self.app.volume_scale.instate(['disabled']))
        self.assertEqual(float(self.app.volume_scale.cget('to')), 31)
        self.assertEqual(self.app.volume_text.get(), '29%')

    def test_sound_tab_loads_controls_once_without_mutation(self):
        speaker = Speaker(1)
        self.app.show_discovery([speaker], [])
        self.assertNotIn(speaker.address, self.app.snapshots)
        with patch.object(self.app, 'read_sound_controls') as read:
            self.app.notebook.select(self.app.tab_viewports['Sound'])
            self.app.on_tab_changed()
            self.app.on_tab_changed()
        read.assert_called_once()
        self.assertIn(speaker.address, self.app.sound_requested)

    def test_volume_release_commits_once_only_when_changed(self):
        speaker = Speaker(1)
        self.app.show_discovery([speaker], [])
        self.app.render_snapshot(speaker, {
            'capabilities': {'volume': True}, 'volume': 9, 'max_volume': 31, 'errors': {}})
        with patch.object(self.app, 'setting') as setting:
            self.app.on_volume_release()
            setting.assert_not_called()
            self.app.volume.set(14.3)
            self.assertIn('pending', self.app.volume_text.get())
            self.app.on_volume_release()
        setting.assert_called_once_with('set_volume', 14)

    def test_slider_cannot_send_with_unknown_volume(self):
        speaker = Speaker(1)
        self.app.show_discovery([speaker], [])
        self.app.render_snapshot(speaker, {
            'capabilities': {'volume': True}, 'volume': None, 'errors': {}})
        self.app.volume.set(20)
        with patch.object(self.app, 'setting') as setting:
            self.app.on_volume_release()
            self.app.apply_volume()
        setting.assert_not_called()
        self.assertIn('Read controls', self.app.status.get())

    def test_eq_band_release_selects_advertised_custom_not_preset(self):
        speaker = Speaker(1)
        self.app.show_discovery([speaker], [])
        self.app.render_snapshot(speaker, {
            'capabilities': {'eq': True}, 'eq': EQInfo(3, (-5, 0, 1, 2, 3)),
            'supported_eq_modes': (3, 4), 'errors': {}})
        self.assertFalse(self.app.eq_band_scales[0].instate(['disabled']))
        self.app.eq_bands[0].set(-10)
        with patch.object(self.app, 'setting') as setting:
            self.app.on_eq_band_release()
        self.assertEqual(self.app.eq_combo.get(), 'Custom')
        setting.assert_called_once_with('set_eq', 4, (-10, 0, 1, 2, 3))

    def test_eq_custom_band_sliders_disabled_when_unadvertised(self):
        speaker = Speaker(1)
        self.app.show_discovery([speaker], [])
        self.app.render_snapshot(speaker, {
            'capabilities': {'eq': True}, 'eq': EQInfo(3, (0, 0, 0, 0, 0)),
            'supported_eq_modes': (3, 5), 'errors': {}})
        self.assertFalse(self.app.eq_combo.instate(['disabled']))
        self.assertTrue(all(s.instate(['disabled']) for s in self.app.eq_band_scales))
        with patch.object(self.app, 'setting') as setting:
            self.app.on_eq_band_release()
        setting.assert_not_called()
        self.assertIn('does not advertise Custom EQ', self.app.status.get())

    def test_volume_setting_queries_only_changed_value(self):
        speaker = Speaker(1)
        self.app.show_discovery([speaker], [])
        self.app.render_snapshot(speaker, {
            'capabilities': {'volume': True}, 'volume': 9, 'max_volume': 31, 'errors': {}})
        settings = SimpleNamespace(set_volume=AsyncMock(), volume=AsyncMock(return_value=14),
                                   snapshot=AsyncMock(side_effect=AssertionError('slow scan')))
        connection = AsyncMock()
        connection.__aenter__.return_value = settings
        with patch('ue_partyup.controls.settings_session', return_value=connection):
            with patch.object(self.app, 'worker') as worker:
                self.app.setting('set_volume', 14)
            kind, task = worker.call_args.args
            speaker_result, field, value, error = task()
        self.assertEqual(kind, 'adjusted')
        self.assertEqual((speaker_result, field, value, error), (speaker, 'volume', 14, None))
        settings.set_volume.assert_awaited_once_with(14)
        settings.volume.assert_awaited_once()
        settings.snapshot.assert_not_awaited()

    def test_sound_tab_fast_read_does_not_scan_or_mutate(self):
        speaker = Speaker(1)
        self.app.show_discovery([speaker], [])
        fake = SimpleNamespace(
            volume=AsyncMock(return_value=9),
            eq=AsyncMock(return_value=EQInfo(4, (-5, 0, 1, 2, 3))),
            eq_modes=AsyncMock(return_value=(3, 4)),
            snapshot=AsyncMock(side_effect=AssertionError('full scan')),
            set_volume=AsyncMock(), set_eq=AsyncMock())
        context = AsyncMock()
        context.__aenter__.return_value = fake
        with patch('ue_partyup.controls.settings_session', return_value=context):
            with patch.object(self.app, 'worker') as worker:
                self.app.read_sound_controls()
            kind, task = worker.call_args.args
            chosen, fields = task()
        self.assertEqual(kind, 'sound_snapshot')
        self.assertEqual(chosen, speaker)
        self.assertEqual(fields['volume'], 9)
        self.assertEqual(fields['capabilities'], {'volume': True, 'eq': True})
        fake.snapshot.assert_not_awaited()
        fake.set_volume.assert_not_awaited()
        fake.set_eq.assert_not_awaited()

    def test_sound_read_timeout_does_not_claim_unsupported(self):
        speaker = Speaker(1)
        self.app.show_discovery([speaker], [])
        fake = SimpleNamespace(
            volume=AsyncMock(side_effect=RuntimeError('timed out')),
            eq=AsyncMock(return_value=EQInfo(4, (0, 0, 0, 0, 0))),
            eq_modes=AsyncMock(return_value=(3, 4)))
        context = AsyncMock()
        context.__aenter__.return_value = fake
        with patch('ue_partyup.controls.settings_session', return_value=context):
            with patch.object(self.app, 'worker') as worker:
                self.app.read_sound_controls()
            _, task = worker.call_args.args
            _, snapshot = task()
        self.assertIsNone(snapshot['volume'])
        self.assertIsNone(snapshot['capabilities']['volume'])
        self.assertTrue(snapshot['capabilities']['eq'])
        self.assertIn('volume', snapshot['errors'])

    def test_confirmed_adjustment_updates_without_losing_other_fields(self):
        speaker = Speaker(1)
        self.app.show_discovery([speaker], [])
        self.app.render_snapshot(speaker, {
            'capabilities': {'volume': True, 'battery': True},
            'battery': BatteryInfo(75, 74, 2), 'volume': 9,
            'max_volume': 31, 'errors': {}})
        self.app.events.put(('adjusted', (speaker, 'volume', 14, None)))
        self.app.poll()
        current = self.app.snapshots[speaker.address]
        self.assertEqual(current['volume'], 14)
        self.assertEqual(current['battery'].percent, 74)
        self.assertFalse(self.app.volume_scale.instate(['disabled']))
        self.assertIn('verified', self.app.status.get())

    def test_eq_write_uses_targeted_readback_not_full_snapshot(self):
        speaker = Speaker(1)
        self.app.show_discovery([speaker], [])
        self.app.render_snapshot(speaker, {
            'capabilities': {'eq': True}, 'eq': EQInfo(3, (0, 0, 0, 0, 0)),
            'supported_eq_modes': (3, 4), 'errors': {}})
        eq = EQInfo(4, (4, 3, 2, 1, 0))
        fake = SimpleNamespace(set_eq=AsyncMock(), eq=AsyncMock(return_value=eq),
                               snapshot=AsyncMock(side_effect=AssertionError('full scan')))
        context = AsyncMock()
        context.__aenter__.return_value = fake
        with patch('ue_partyup.controls.settings_session', return_value=context):
            with patch.object(self.app, 'worker') as worker:
                self.app.setting('set_eq', 4, eq.bands)
            kind, task = worker.call_args.args
            _, field, value, error = task()
        self.assertEqual((kind, field, value, error), ('adjusted', 'eq', eq, None))
        fake.set_eq.assert_awaited_once_with(4, eq.bands)
        fake.eq.assert_awaited_once()
        fake.snapshot.assert_not_awaited()

    def test_playback_does_not_follow_command_with_unrelated_feature_scan(self):
        speaker = Speaker(1)
        self.app.show_discovery([speaker], [])
        self.app.render_snapshot(speaker, {'capabilities': {'playback': True}, 'errors': {}})
        fake = SimpleNamespace(playback=AsyncMock(),
                               snapshot=AsyncMock(side_effect=AssertionError('unrelated scan')))
        context = AsyncMock(); context.__aenter__.return_value = fake
        with patch('ue_partyup.controls.settings_session', return_value=context), patch.object(self.app, 'worker') as worker:
            self.app.setting('playback', 'next', 1)
            kind, task = worker.call_args.args
            message = task()
        self.assertEqual(kind, 'message')
        self.assertIn('command accepted', message)
        fake.playback.assert_awaited_once_with('next', 1)
        fake.snapshot.assert_not_awaited()

    def test_timer_change_reads_back_only_timer_and_preserves_other_fields(self):
        speaker = Speaker(1)
        self.app.show_discovery([speaker], [])
        self.app.render_snapshot(speaker, {'capabilities': {'sleep_timer': True},
                                         'sleep_timer': 15, 'errors': {}})
        fake = SimpleNamespace(set_sleep_timer=AsyncMock(), sleep_timer=AsyncMock(return_value=30),
                               snapshot=AsyncMock(side_effect=AssertionError('unrelated scan')))
        context = AsyncMock(); context.__aenter__.return_value = fake
        with patch('ue_partyup.controls.settings_session', return_value=context), patch.object(self.app, 'worker') as worker:
            self.app.setting('set_sleep_timer', 30)
            kind, task = worker.call_args.args
            _, field, confirmed, error = task()
        self.assertEqual((kind, field, confirmed, error), ('adjusted', 'sleep_timer', 30, None))
        fake.sleep_timer.assert_awaited_once()
        fake.snapshot.assert_not_awaited()

    def test_ack_without_readback_does_not_claim_volume_verified(self):
        speaker = Speaker(1)
        self.app.show_discovery([speaker], [])
        snapshot = {'capabilities': {'volume': True}, 'volume': 9, 'max_volume': 31, 'errors': {}}
        self.app.render_snapshot(speaker, snapshot)
        self.app.events.put(('adjusted', (speaker, 'volume', None, 'timeout')))
        self.app.poll()
        self.assertIsNone(self.app.snapshots[speaker.address]['volume'])
        self.assertTrue(self.app.volume_scale.instate(['disabled']))
        self.assertIn('unconfirmed', self.app.status.get())

    def test_busy_volume_release_does_not_send(self):
        speaker = Speaker(1)
        self.app.show_discovery([speaker], [])
        self.app.render_snapshot(speaker, {
            'capabilities': {'volume': True}, 'volume': 9, 'max_volume': 31, 'errors': {}})
        self.app.volume.set(12)
        self.app.busy = True
        with patch.object(self.app, 'setting') as setting:
            self.app.on_volume_release()
        setting.assert_not_called()

    def test_busy_close_is_guarded(self):
        self.app.busy = True
        with patch('ue_partyup.app.messagebox.showinfo') as message, patch.object(self.root, 'destroy') as destroy:
            self.app.close()
        message.assert_called_once()
        destroy.assert_not_called()

    def test_loading_local_eq_memory_never_sends_a_command(self):
        speaker = Speaker(1)
        self.app.show_discovery([speaker], [])
        self.app.render_snapshot(speaker, {'capabilities': {'eq': True},
            'eq': EQInfo(3, (0, 0, 0, 0, 0)), 'supported_eq_modes': (3, 4), 'errors': {}})
        self.app.memory_combo.set('Living room')
        with patch.object(self.app.eq_profiles, 'records', return_value={
                'Living room': {'mode': 4, 'bands': (1, 2, -3, 4, 5)}}), \
             patch.object(self.app, 'setting') as setting:
            self.app.load_eq_memory()
        self.assertEqual(tuple(value.get() for value in self.app.eq_bands), (1, 2, -3, 4, 5))
        self.assertEqual(self.app.eq_choices[self.app.eq_combo.current()][1], 4)
        setting.assert_not_called()

    def test_drag_join_uses_only_dragged_guest_and_busy_drag_does_nothing(self):
        guest = Speaker(2)
        self.app.dragged_speaker = ('add', guest, 0, 0)
        target = self.app.member_tree
        with patch.object(target, 'winfo_ismapped', return_value=True), \
             patch.object(target, 'winfo_rootx', return_value=100), \
             patch.object(target, 'winfo_rooty', return_value=100), \
             patch.object(target, 'winfo_width', return_value=200), \
             patch.object(target, 'winfo_height', return_value=200), \
             patch.object(self.app, 'group_action') as action:
            self.app.finish_speaker_drag(SimpleNamespace(x_root=150, y_root=150))
            action.assert_called_once_with('add', guests_override=[guest])
            action.reset_mock()
            self.app.busy = True
            self.app.dragged_speaker = ('add', guest, 0, 0)
            self.app.finish_speaker_drag(SimpleNamespace(x_root=150, y_root=150))
            action.assert_not_called()

    def test_click_without_drag_sends_no_join(self):
        self.app.dragged_speaker = ('add', Speaker(2), 100, 100)
        with patch.object(self.app, 'group_action') as action:
            self.app.finish_speaker_drag(SimpleNamespace(x_root=102, y_root=102))
        action.assert_not_called()

    def test_group_volume_sync_targets_host_not_selected_control_device(self):
        self.app.show_discovery([Speaker(1), Speaker(2)], [])
        self.app.device_combo.current(1)
        settings = SimpleNamespace(sync_volume=AsyncMock())
        context = AsyncMock(); context.__aenter__.return_value = settings
        with patch('ue_partyup.controls.settings_session', return_value=context) as session, \
             patch.object(self.app, 'worker') as worker:
            self.app.sync_group_volume()
            _, task = worker.call_args.args
            message = task()
        self.assertEqual(session.call_args.args[0].address, 1)
        settings.sync_volume.assert_awaited_once()
        self.assertIn('does not adjust audio/video', message)


if __name__ == '__main__':
    unittest.main()
