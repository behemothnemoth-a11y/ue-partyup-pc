from pathlib import Path
from types import SimpleNamespace
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch
from ue_partyup.house_layout import HouseLayout
from ue_partyup.house_view import HousePartyApp
from ue_partyup.controller import Speaker
from ue_partyup.groups import GroupResult, MemberResult
from ue_partyup.settings import EQInfo
from ue_partyup.app import PartyUpApp
from ue_partyup.house_widgets import PocketButton, PixelSlider
from tkinter import ttk


class LayoutTests(unittest.TestCase):
    def test_ten_unique_slots_swap_and_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'rooms.json';layout=HouseLayout(path)
            layout.ensure(range(1,11))
            self.assertEqual(set(layout.positions.values()),set(range(10)))
            first,second=layout.positions[1],layout.positions[2]
            layout.move(1,second,list(range(1,11)))
            self.assertEqual((layout.positions[1],layout.positions[2]),(second,first))
            layout.rooms[0]='Lounge';layout.save()
            loaded=HouseLayout(path)
            self.assertEqual(loaded.rooms[0],'Lounge')
            self.assertEqual(loaded.positions,layout.positions)

    def test_capacity_and_malformed_storage_fail_safely(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'rooms.json';path.write_text('{broken')
            layout=HouseLayout(path)
            with self.assertRaises(ValueError):layout.ensure(range(1,12))
            path.write_text('{"positions":{"1":true,"2":99,"3":0,"4":0}}')
            layout=HouseLayout(path);layout.ensure([1,2,3,4])
            self.assertEqual(len(set(layout.positions[x] for x in (1,2,3,4))),4)


class HouseTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.root=tk.Tk();self.root.withdraw()
        self.app=HousePartyApp(self.root,Path(self.directory.name))

    def tearDown(self):
        self.app.close();self.directory.cleanup()

    def discover(self,count):
        self.app.show_discovery([Speaker(i,f'EVERBOOM {i}') for i in range(1,count+1)],[])

    def test_initialization_and_house_selection_do_not_contact_speakers(self):
        with patch('ue_partyup.app.discover') as discovery, patch.object(self.app,'worker') as worker:
            self.discover(2)
            self.app.select_house_speaker(self.app.speakers[1])
            self.app.return_house()
        discovery.assert_not_called();worker.assert_not_called()
        self.assertIn('Guest',self.app.house_identity.get())
        self.assertTrue(self.app.house_volume.instate(['disabled']))
        self.assertIn('Not available',self.app.house_battery.get())

    def test_ten_speakers_render_and_eleventh_cannot_join(self):
        self.discover(11)
        self.app.guest_list.selection_clear(0,'end')
        self.app.guest_list.selection_set(0,8);self.app.guests_changed()
        with patch.object(self.app.scene,'winfo_width',return_value=900),patch.object(self.app.scene,'winfo_height',return_value=510):
            self.app.draw_scene()
        self.assertEqual(len(self.app.speaker_hits),10)
        self.assertEqual(len(set(self.app.layout.positions[s.address] for s in self.app.active_house())),10)
        with patch.object(self.app,'group_action') as action:
            self.app.add_to_house(self.app.speakers[-1])
        action.assert_not_called()
        self.assertIn('Ten speakers',self.app.status.get())

    def test_arranging_selected_speaker_is_local_and_keeps_all_members(self):
        self.discover(3)
        active=[s.address for s in self.app.active_house()]
        with patch.object(self.app,'worker') as worker:
            self.app.layout.move(2,self.app.layout.positions[3],active)
            self.app.save_rooms();self.app.sync_house()
        worker.assert_not_called()
        self.assertEqual([s.address for s in self.app.active_house()],active)

    def test_failed_remove_stays_selected_and_accepted_remove_releases_slot(self):
        self.discover(2);guest=self.app.speakers[1]
        self.app.pending_house_remove.add(guest.address)
        self.app.show_group(GroupResult('remove',True,[MemberResult(guest,'unconfirmed')]))
        self.assertEqual(len(self.app.selected_guests()),1)
        self.app.pending_house_remove.add(guest.address)
        self.app.show_group(GroupResult('remove',True,[MemberResult(guest,'leave accepted')]))
        self.assertEqual(self.app.selected_guests(),[])
        self.assertEqual(len(self.app.drawer_hits),1)

    def test_sidebar_volume_gesture_sends_once_on_release_and_busy_blocks(self):
        self.discover(1)
        self.app.render_snapshot(self.app.speakers[0],{'capabilities':{'volume':True},'volume':10,'max_volume':31,'errors':{}})
        slider=self.app.house_volume
        with patch.object(slider,'winfo_width',return_value=200),patch.object(self.app,'setting') as setting:
            slider.press(SimpleNamespace(x=120,y=10))
            slider.move(SimpleNamespace(x=140,y=10))
            setting.assert_not_called();slider.release()
            setting.assert_called_once_with('set_volume',self.app.volume.get())
            setting.reset_mock();self.app.busy=True;self.app.update_enabled()
            slider.press(SimpleNamespace(x=80,y=10));slider.release()
            self.app.house_start.invoke();setting.assert_not_called()
        self.app.busy=False

    def test_overselection_in_advanced_controls_does_not_crash_or_start(self):
        self.discover(11);self.app.guest_list.selection_set(0,'end');self.app.guests_changed()
        with patch.object(self.app,'worker') as worker:self.app.group_action('start')
        worker.assert_not_called()

    def test_sidebar_eq_matches_advertised_values_and_stages_without_writes(self):
        self.discover(1)
        with patch.object(self.app,'setting') as setting:
            self.app.render_snapshot(self.app.speakers[0],{'capabilities':{'eq':True},
                'eq':EQInfo(3,(1,2,3,4,5)),'supported_eq_modes':(3,4),'errors':{}})
        setting.assert_not_called()
        self.assertEqual(tuple(self.app.house_eq.cget('values')),('Standard','Custom'))
        self.assertFalse(self.app.house_bands[0].instate(['disabled']))

    def test_hidden_sound_tab_cannot_start_reads_during_house_discovery(self):
        self.app.notebook.select(self.app.tab_viewports['Sound'])
        with patch.object(self.app,'read_sound_controls') as read:
            self.discover(2)
            self.app.on_tab_changed()
        read.assert_not_called()

    def test_new_drop_chooses_free_room_slot_without_displacing_main(self):
        self.discover(2)
        active=[s.address for s in self.app.active_house()]
        original=self.app.layout.positions[1]
        self.app.scene_rect=(0,0,900,510)
        slot=self.app.free_slot_at(900*.48,510*.46)
        self.assertEqual(self.app.layout.positions[1],original)
        self.assertNotIn(slot,{self.app.layout.positions[x] for x in active})
        self.assertEqual(__import__('ue_partyup.house_layout',fromlist=['SLOTS']).SLOTS[slot][0],0)

    def test_styled_pages_preserve_all_original_actions_and_capability_gates(self):
        baseline_root=tk.Tk();baseline_root.withdraw()
        baseline=PartyUpApp(baseline_root,Path(self.directory.name)/'baseline')
        try:
            previous={widget.cget('text') for widget,_ in baseline.controls if isinstance(widget,ttk.Button)}
            current={widget.label for widget,_ in self.app.controls if isinstance(widget,PocketButton)}
            self.assertTrue(previous <= current, previous-current)
            for feature,widgets in baseline.feature_widgets.items():
                self.assertGreaterEqual(len(self.app.feature_widgets[feature]),len(widgets),feature)
            self.assertEqual(len(self.app.eq_band_scales),5)
            self.assertIsInstance(self.app.volume_scale,PixelSlider)
            self.assertTrue(all(isinstance(scale,PixelSlider) for scale in self.app.eq_band_scales))
        finally:baseline.close()

    def test_styled_sound_sliders_share_state_and_keep_release_callbacks(self):
        self.discover(1)
        with patch.object(self.app,'setting') as setting:
            self.app.render_snapshot(self.app.speakers[0],{'capabilities':{'volume':True,'eq':True},
                'volume':10,'max_volume':31,'eq':EQInfo(3,(0,0,0,0,0)),
                'supported_eq_modes':(3,4),'errors':{}})
            self.app.volume.set(15)
            self.app.eq_bands[0].set(7)
            setting.assert_not_called()
            self.assertIs(self.app.volume_scale.variable,self.app.house_volume.variable)
            self.assertIn('on_volume_release',self.app.volume_scale.bind('<ButtonRelease-1>'))
            self.assertIn('on_eq_band_release',self.app.eq_band_scales[0].bind('<ButtonRelease-1>'))
            self.app.on_volume_release()
            setting.assert_called_once_with('set_volume',15)
            setting.reset_mock();self.app.busy=True;self.app.update_enabled()
            self.app.on_volume_release();self.app.on_eq_band_release()
            setting.assert_not_called()
        self.app.busy=False

    def test_control_page_navigation_keeps_every_page_reachable(self):
        self.discover(1);self.app.sound_requested.add(1)
        with patch.object(self.app,'worker') as worker:
            for page,title in (('Sound','SOUND STUDIO'),('Speaker','SPEAKER SETTINGS'),
                               ('PartyUp settings','PARTY PREFERENCES'),('Group','PARTY CREW'),('Guide','FIELD GUIDE')):
                self.app.open_advanced(page)
                self.assertEqual(self.app.control_page_title.get(),title)
                self.assertEqual(self.app.notebook.select(),str(self.app.tab_viewports[page]))
            self.app.return_house()
        worker.assert_not_called()

    def test_metal_memory_load_preserves_bass_boost_without_sending(self):
        self.discover(1)
        self.app.render_snapshot(self.app.speakers[0],{'capabilities':{'eq':True},
            'eq':EQInfo(3,(0,0,0,0,0)),'supported_eq_modes':(3,4,5),'errors':{}})
        self.app.eq_profiles.save('Metal',(113,76,-25,29,98),mode=5)
        self.app.memory_combo.set('Metal')
        with patch.object(self.app,'setting') as setting:
            self.app.load_eq_memory()
        setting.assert_not_called()
        self.assertEqual(self.app.eq_choices[self.app.eq_combo.current()][1],5)
        self.assertEqual(tuple(round(v.get()) for v in self.app.eq_bands),(113,76,-25,29,98))

    def test_quick_tune_rejects_repeated_clicks_and_tracks_verified_undo(self):
        from ue_partyup.tuning import TuneResult
        from unittest.mock import Mock
        self.discover(1)
        before=EQInfo(5,(113,76,-25,29,98));after=EQInfo(5,(114,76,-25,29,98))
        self.app.render_snapshot(self.app.speakers[0],{'capabilities':{'eq':True},
            'eq':before,'supported_eq_modes':(3,4,5),'errors':{}})
        def queued(*args):
            self.app.busy=True;self.app.update_enabled()
        with patch.object(self.app,'worker',side_effect=queued) as worker:
            self.app.tune_plus.invoke();self.app.tune_plus.invoke()
        self.assertEqual(worker.call_count,1)
        self.app.events.put(('tuning',(self.app.speakers[0],'nudge',TuneResult(before,after))))
        self.app.poll()
        self.assertFalse(self.app.busy)
        self.assertEqual(self.app.tuning.history,[before])
        self.assertIn('+1 steps',self.app.tuning_text.get())
        self.assertFalse(self.app.tune_undo.instate(['disabled']))

    def test_uncertain_tuning_disables_all_eq_until_explicit_read(self):
        from ue_partyup.tuning import TuneResult
        self.discover(1);speaker=self.app.speakers[0]
        eq=EQInfo(5,(113,76,-25,29,98))
        snapshot={'capabilities':{'eq':True},'eq':eq,'supported_eq_modes':(3,4,5),'errors':{}}
        self.app.render_snapshot(speaker,snapshot)
        self.app.events.put(('tuning',(speaker,'nudge',TuneResult(eq,problem='timeout'))))
        self.app.poll()
        self.assertTrue(self.app.tune_plus.instate(['disabled']))
        self.assertTrue(self.app.eq_combo.instate(['disabled']))
        self.app.render_snapshot(speaker,snapshot)
        self.assertTrue(self.app.tune_plus.instate(['disabled']))
        self.app.events.put(('sound_snapshot',(speaker,snapshot)))
        self.app.poll()
        self.assertFalse(self.app.tune_plus.instate(['disabled']))

    def test_late_tuning_reply_does_not_transfer_undo_to_another_target(self):
        from ue_partyup.tuning import TuneResult
        self.discover(2)
        original=EQInfo(5,(113,76,-25,29,98));changed=EQInfo(5,(114,76,-25,29,98))
        snapshot={'capabilities':{'eq':True},'eq':original,'supported_eq_modes':(3,4,5),'errors':{}}
        self.app.render_snapshot(self.app.speakers[0],snapshot)
        self.app.tuning.pending=True
        self.app.device_combo.current(1)
        self.app.render_snapshot(self.app.speakers[1],snapshot)
        self.app.accept_tuning((self.app.speakers[0],'nudge',TuneResult(original,changed)))
        self.assertFalse(self.app.tuning.pending)
        self.assertEqual(self.app.tuning.target,self.app.speakers[1].address)
        self.assertEqual(self.app.tuning.history,[])
        self.assertEqual(self.app.snapshots[self.app.speakers[0].address]['eq'],changed)

    def test_factory_preset_memory_does_not_require_custom_support(self):
        self.discover(1)
        eq=EQInfo(5,(113,76,-25,29,98))
        self.app.render_snapshot(self.app.speakers[0],{'capabilities':{'eq':True},
            'eq':eq,'supported_eq_modes':(3,5),'errors':{}})
        self.app.memory_combo.set('Factory only');self.app.save_eq_memory()
        self.assertEqual(self.app.eq_profiles.records()['Factory only']['mode'],5)
        self.app.eq_combo.current(0)
        with patch.object(self.app,'setting') as setting:self.app.load_eq_memory()
        setting.assert_not_called()
        self.assertEqual(self.app.eq_choices[self.app.eq_combo.current()][1],5)
