import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from ue_partyup.runtime import data_directory, user_directory, redact, diagnostic_summary, InstanceGuard, asset_check
from ue_partyup.installer import import_settings


class RuntimeTests(unittest.TestCase):
    def test_data_is_outside_application_and_shared_between_source_and_bundle(self):
        with patch.dict(os.environ,{'LOCALAPPDATA':str(Path('test-local').absolute())}):
            source=data_directory()
            with patch.object(sys,'frozen',True,create=True): self.assertEqual(data_directory(),source)
            self.assertEqual(source,user_directory()/'data')

    def test_summary_contains_no_speaker_or_setting_identifiers(self):
        summary=diagnostic_summary()
        self.assertFalse(summary['telemetry']);self.assertTrue(summary['private_preview'])
        self.assertNotIn('address',json.dumps(summary));self.assertNotIn('selection',summary)
        self.assertIn('Pillow',summary['dependencies'])

    def test_address_redaction(self):
        self.assertNotIn('AA:BB:CC:DD:EE:FF',redact('error AA:BB:CC:DD:EE:FF'))
        self.assertNotIn('aabbccddeeff',redact('error aabbccddeeff'))

    @unittest.skipUnless(sys.platform=='win32','Windows mutex')
    def test_second_instance_is_rejected_and_handles_are_released(self):
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'LOCALAPPDATA':directory}):
            one,two,three=InstanceGuard(),InstanceGuard(),InstanceGuard()
            try:
                self.assertTrue(one.acquire());self.assertFalse(two.acquire())
                one.close();two.close()
                self.assertTrue(three.acquire())
            finally: one.close();two.close();three.close()

    def test_bundled_asset_check(self):
        self.assertEqual(asset_check()['application'],'PartyUp PC')

    def test_settings_import_preserves_existing_files_and_only_copies_allowlist(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'old';target=Path(directory)/'new';source.mkdir();target.mkdir()
            (source/'eq-memories.json').write_text('{"Metal":{"mode":5,"bands":[113,76,-25,29,98]}}')
            (source/'devices.json').write_text('{}');(target/'devices.json').write_text('{"keep":"existing"}')
            (source/'private.key').write_text('not copied')
            self.assertEqual(import_settings(source,target),['eq-memories.json'])
            self.assertFalse((target/'private.key').exists())
            self.assertEqual(json.loads((target/'devices.json').read_text()),{'keep':'existing'})
            self.assertEqual(import_settings(source,target),[])

    def test_invalid_import_is_not_written(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'old';target=Path(directory)/'new';source.mkdir()
            (source/'eq-memories.json').write_text('not JSON')
            with self.assertRaises(ValueError):import_settings(source,target)
            self.assertFalse((target/'eq-memories.json').exists())
