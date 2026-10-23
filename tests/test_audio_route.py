import json
from types import SimpleNamespace
from unittest.mock import patch
import unittest
from ue_partyup.audio_route import inspect_audio_route


class AudioRouteTests(unittest.TestCase):
    def test_container_identity_distinguishes_main_guest_and_unrelated(self):
        endpoint = '{0.0.0.00000000}.{00000000-0000-0000-0000-000000000001}'
        for address, role in [('000000000001', 'main'), ('000000000002', 'guest'), ('000000000003', 'other')]:
            result = SimpleNamespace(returncode=0, stdout=json.dumps({'name': 'Speaker', 'addresses': [address]}))
            with patch('ue_partyup.audio_route.default_endpoint_id', return_value=endpoint), \
                 patch('ue_partyup.audio_route.subprocess.run', return_value=result):
                self.assertEqual(inspect_audio_route(1, [2]), {'name': 'Speaker', 'role': role})

    def test_invalid_endpoint_is_rejected_before_shell_process(self):
        with patch('ue_partyup.audio_route.default_endpoint_id', return_value="bad'; injected"), \
             patch('ue_partyup.audio_route.subprocess.run') as execute:
            with self.assertRaisesRegex(RuntimeError, 'Unrecognized'):
                inspect_audio_route(1, [2])
        execute.assert_not_called()
