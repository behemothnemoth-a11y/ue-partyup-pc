import json
from pathlib import Path
import tempfile
import unittest
from ue_partyup.profiles import EQProfiles, validate_profile


class ProfileTests(unittest.TestCase):
    def test_preset_mode_survives_other_saves_and_deletes(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'memories.json'
            path.write_text(json.dumps({'Legacy':[0]*5}))
            profiles=EQProfiles(path)
            self.assertEqual(profiles.records()['Legacy']['mode'],4)
            profiles.save('Metal',(113,76,-25,29,98),mode=5)
            profiles.save('Other',(0,0,0,0,0))
            profiles.delete('Other')
            self.assertEqual(profiles.records()['Metal'],{'mode':5,'bands':(113,76,-25,29,98)})
            self.assertEqual(profiles.records()['Legacy']['mode'],4)

    def test_roundtrip_replace_delete_and_invalid_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'memories.json'
            path.write_text(json.dumps({'broken': [0], 'good': [0, 1, -1, 127, -128]}))
            profiles = EQProfiles(path)
            self.assertEqual(profiles.load(), {'good': (0, 1, -1, 127, -128)})
            profiles.save(' Warm room ', (1, 2, 3, 4, 5))
            self.assertEqual(profiles.load()['Warm room'], (1, 2, 3, 4, 5))
            profiles.save('Warm room', (-1, 0, 1, 0, -1))
            self.assertEqual(profiles.load()['Warm room'], (-1, 0, 1, 0, -1))
            profiles.delete('Warm room')
            self.assertNotIn('Warm room', profiles.load())
            self.assertFalse(path.with_suffix('.tmp').exists())

    def test_corrupt_memory_is_not_silently_overwritten_on_save(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'memories.json';path.write_text('{broken')
            profiles=EQProfiles(path)
            self.assertEqual(profiles.load(),{})
            with self.assertRaises(ValueError):profiles.save('New',(0,0,0,0,0))
            self.assertEqual(path.read_text(),'{broken')

    def test_capacity_allows_replacement_but_rejects_new_entry(self):
        with tempfile.TemporaryDirectory() as folder:
            profiles = EQProfiles(Path(folder) / 'memories.json')
            for index in range(20):
                profiles.save(str(index), (0, 0, 0, 0, 0))
            profiles.save('0', (1, 1, 1, 1, 1))
            with self.assertRaisesRegex(ValueError, '20 EQ memories'):
                profiles.save('another', (0, 0, 0, 0, 0))

    def test_rejects_unusable_values_before_writing(self):
        for name, bands in [('', [0]*5), ('x'*33, [0]*5), ('name', [0]*4),
                            ('name', [True]*5), ('name', [128]*5), ('name', [0.5]*5)]:
            with self.subTest(name=name, bands=bands), self.assertRaises(ValueError):
                validate_profile(name, bands)

    def test_corrupt_or_non_object_storage_is_empty(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'memories.json'
            profiles = EQProfiles(path)
            for value in ('[]', 'null', '{broken'):
                path.write_text(value)
                self.assertEqual(profiles.load(), {})
