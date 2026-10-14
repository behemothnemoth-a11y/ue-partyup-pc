"""Selection and native UI checks; no speaker connections or control writes."""
import json
from pathlib import Path
import tkinter as tk
import unittest
from unittest.mock import patch
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
        self.assertEqual(len(self.app.notebook.tabs()), 4)
        self.assertTrue(self.app.volume_scale.instate(['disabled']))
        self.assertEqual(self.app.device_combo.get(), '')

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

    def test_busy_close_is_guarded(self):
        self.app.busy = True
        with patch('ue_partyup.app.messagebox.showinfo') as message, patch.object(self.root, 'destroy') as destroy:
            self.app.close()
        message.assert_called_once()
        destroy.assert_not_called()


if __name__ == '__main__':
    unittest.main()
