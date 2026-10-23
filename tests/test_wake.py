from types import SimpleNamespace
from unittest.mock import AsyncMock
import unittest
from ue_partyup.controller import Speaker
from ue_partyup.wake import wake_speaker, POWER_UUID, WAKE_PAYLOAD


class WakeTests(unittest.IsolatedAsyncioTestCase):
    async def test_verified_characteristic_receives_only_recovered_wake_payload(self):
        characteristic = SimpleNamespace(properties=['write'])
        client = SimpleNamespace(services=SimpleNamespace(get_characteristic=lambda uuid: characteristic if uuid == POWER_UUID else None),
                                 write_gatt_char=AsyncMock())
        context = AsyncMock(); context.__aenter__.return_value = client
        factory = lambda *args, **kwargs: context
        message = await wake_speaker(Speaker(1), factory)
        self.assertEqual(WAKE_PAYLOAD, b'\2\2\2\2\2\2\xff')
        client.write_gatt_char.assert_awaited_once_with(characteristic, WAKE_PAYLOAD, response=True)
        self.assertIn('not independently confirmed', message)
        context.__aexit__.assert_awaited_once()

    async def test_missing_or_unacknowledged_characteristic_never_writes(self):
        for characteristic in (None, SimpleNamespace(properties=['write-without-response'])):
            client = SimpleNamespace(services=SimpleNamespace(get_characteristic=lambda _: characteristic),
                                     write_gatt_char=AsyncMock())
            context = AsyncMock(); context.__aenter__.return_value = client
            with self.assertRaisesRegex(RuntimeError, 'No wake sent'):
                await wake_speaker(Speaker(1), lambda *args, **kwargs: context)
            client.write_gatt_char.assert_not_awaited()
            context.__aexit__.assert_awaited_once()

    async def test_legacy_rejected_before_connection(self):
        factory = AsyncMock()
        with self.assertRaises(ValueError):
            await wake_speaker(Speaker(1, 'BOOM', True), factory)
        factory.assert_not_called()
