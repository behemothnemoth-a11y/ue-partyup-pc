import unittest
from types import SimpleNamespace

from ue_partyup.session import NoReply, ProtocolError, UnsupportedFeature
from ue_partyup.settings import (
    Settings, UnsupportedControl, NAME, BATTERY, VOLUME, EQ, OUTDOOR,
    REMOTE_POWER, AUTO_SLEEP, XUP, XUP_RECEIVER, AVRCP, APOLLO_BROADCASTER,
    decode_name, decode_battery, decode_eq, eq_payload, name_payload,
)


class FakeSession:
    def __init__(self):
        self.speaker = SimpleNamespace(address=0x112233445566)
        self.indices = {
            NAME: 7, BATTERY: 9, VOLUME: 17, EQ: 18, OUTDOOR: 19,
            REMOTE_POWER: 20, AUTO_SLEEP: 21, XUP: 22, AVRCP: 23,
            APOLLO_BROADCASTER: 24,
            XUP_RECEIVER: 25,
        }
        self.responses = {
            (7, 0): b'\x30\x08EVERBOOM', (7, 3): b'\x30',
            (9, 0): bytes([72, 75, 2]), (17, 0): b'\x1b',
            (18, 0): bytes([4, 128, 255, 0, 1, 127]),
            (18, 2): bytes([3, 3, 4, 5]), (19, 0): b'\0',
            (20, 0): b'\1', (21, 0): b'\x0f', (22, 9): b'\1',
            (25, 0): b'\1', (22, 1): b'\0\0',
        }
        self.calls = []
        self.lookups = []
        self.setter_response = b''

    async def feature(self, feature):
        self.lookups.append(feature)
        result = self.indices.get(feature, UnsupportedFeature('Not advertised'))
        if isinstance(result, Exception):
            raise result
        return result

    async def request(self, index, operation, payload=b'', read=False):
        self.calls.append((index, operation, payload, read))
        result = self.responses[(index, operation)] if read else self.setter_response
        if isinstance(result, Exception):
            raise result
        return result


class DecoderTests(unittest.TestCase):
    def test_current_name_reply_prefix_and_utf8(self):
        self.assertEqual(decode_name(b'\x30\x08EVERBOOM'), 'EVERBOOM')
        self.assertEqual(decode_name(b'\x30\x02\xc3\xa9'), 'é')
        self.assertEqual(decode_name(b'\x30\0'), '')
        for payload in (b'', b'\x30', b'\x30\x04abc', b'\x30\1\xff'):
            with self.subTest(payload=payload), self.assertRaises(ProtocolError):
                decode_name(payload)

    def test_name_limit_counts_encoded_bytes(self):
        self.assertEqual(name_payload('é', 2), b'\x02\xc3\xa9')
        for name, limit in [('éé', 3), ('', 48), ('  ', 48), ('a\0b', 48)]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                name_payload(name, limit)

    def test_battery_preserves_raw_and_display_soc(self):
        info = decode_battery(bytes([72, 75, 2]))
        self.assertEqual(info.battery, 72)
        self.assertEqual(info.percent, 75)
        self.assertEqual(info.charging_state, 'Fast charging')
        self.assertIsNone(decode_battery(bytes([255, 255, 255])).percent)
        self.assertIn('Unknown', decode_battery(bytes([255, 255, 255])).charging_state)
        with self.assertRaises(ProtocolError):
            decode_battery(b'\x50')

    def test_eq_signs_and_mode_not_enum_ordinal(self):
        payload = bytes([4, 128, 255, 0, 1, 127])
        info = decode_eq(payload)
        self.assertEqual(info.label, 'Custom')
        self.assertEqual(info.bands, (-128, -1, 0, 1, 127))
        self.assertEqual(eq_payload(4, info.bands), payload)
        for mode, bands in [(11, [0]*5), (4, [0]*4), (4, [-129]*5), (4, [128]*5), (4, [True]*5)]:
            with self.subTest(mode=mode,bands=bands), self.assertRaises(ValueError):
                eq_payload(mode, bands)
        with self.assertRaises(ProtocolError):
            decode_eq(bytes(5))


class SettingsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.session = FakeSession()
        self.settings = Settings(self.session)

    async def test_controls_use_discovered_indices(self):
        self.assertEqual(await self.settings.volume(), 27)
        await self.settings.set_volume(20)
        self.assertEqual(self.session.calls, [(17,0,b'',True),(17,1,b'\x14',False)])
        self.assertEqual(self.session.lookups, [VOLUME,VOLUME])

    async def test_invalid_scalar_settings_never_write(self):
        for operation in (
            lambda:self.settings.set_volume(256),
            lambda:self.settings.set_volume(32),
            lambda:self.settings.set_volume(True),
            lambda:self.settings.set_sleep_timer(-1),
            lambda:self.settings.set_sleep_timer(16),
            lambda:self.settings.set_remote_activation(1),
            lambda:self.settings.set_outdoor('enabled'),
            lambda:self.settings.set_sticky(0),
            lambda:self.settings.power_off('silent'),
        ):
            with self.assertRaises(ValueError): await operation()
        self.assertEqual(self.session.calls, [])

    async def test_rename_queries_device_limit_before_write(self):
        self.session.responses[(7,3)] = b'\2'
        await self.settings.rename('é')
        self.assertEqual(self.session.calls[-1], (7,1,b'\2\xc3\xa9',False))
        self.session.calls.clear()
        with self.assertRaises(ValueError): await self.settings.rename('éé')
        self.assertEqual(self.session.calls, [(7,3,b'',True)])

    async def test_outdoor_wire_boolean_is_inverted(self):
        self.assertTrue(await self.settings.outdoor())
        await self.settings.set_outdoor(True)
        await self.settings.set_outdoor(False)
        self.assertEqual(self.session.calls[-2:], [(19,1,b'\0',False),(19,1,b'\1',False)])

    async def test_eq_uses_advertised_preset_subset(self):
        await self.settings.set_eq(4, [-1,0,1,2,3])
        self.assertEqual(self.session.calls[-1], (18,1,bytes([4,255,0,1,2,3]),False))
        self.session.calls.clear()
        with self.assertRaises(UnsupportedControl): await self.settings.set_eq(8, [0]*5)
        self.assertEqual(self.session.calls, [(18,2,b'',True)])

    async def test_corrupt_preset_count_rejected(self):
        self.session.responses[(18,2)] = bytes([5,3,4])
        with self.assertRaises(ProtocolError): await self.settings.eq_modes()

    async def test_playback_app_command_and_network_order_mac(self):
        await self.settings.playback('next', 0xAABBCCDDEEFF)
        self.assertEqual(self.session.calls[-1],(23,0,bytes.fromhex('04aabbccddeeff'),False))
        with self.assertRaises(ValueError): await self.settings.playback('erase',1)
        with self.assertRaises(ValueError): await self.settings.playback('play',1<<48)

    async def test_identify_host_and_individual_guest(self):
        await self.settings.identify()
        await self.settings.identify(0xAABBCCDDEEFF,'alternate')
        self.assertEqual(self.session.calls, [
            (22,10,bytes.fromhex('0011223344556601'),False),
            (22,10,bytes.fromhex('01aabbccddeeff02'),False),
        ])

    async def test_persistent_group_and_volume_sync(self):
        self.assertTrue(await self.settings.sticky())
        await self.settings.set_sticky(False)
        await self.settings.sync_volume()
        self.assertEqual(self.session.calls[-2:], [(22,8,b'\0',False),(22,12,b'',False)])

    async def test_visibility_uses_receiver_feature_not_broadcaster(self):
        self.assertTrue(await self.settings.public())
        await self.settings.set_public(False)
        self.assertEqual(self.session.calls, [(25,0,b'',True),(25,1,b'\0',False)])

    async def test_sleep_presets_use_minutes_and_never_zero(self):
        self.assertEqual(await self.settings.sleep_timer(),15)
        for value in (0,15,30,60,180):
            await self.settings.set_sleep_timer(value)
        self.assertEqual(self.session.calls[-1], (21,1,b'\xb4',False))

    async def test_power_parameter_means_silent_not_standby(self):
        await self.settings.power_off()
        await self.settings.power_off(silent=True)
        self.assertEqual(self.session.calls, [(20,2,b'\0',False),(20,2,b'\1',False)])

    async def test_stereo_uses_apollo_not_partyup_feature(self):
        await self.settings.set_stereo_balance(-1)
        self.assertEqual(self.session.calls,[(24,4,b'\xff',False)])
        with self.assertRaises(UnsupportedControl): await self.settings.stereo_balance()

    async def test_unexpected_setter_payload_is_not_success(self):
        self.session.setter_response = b'\1'
        with self.assertRaises(ProtocolError): await self.settings.set_volume(20)

    async def test_snapshot_unknown_feature_is_not_absence(self):
        self.session.indices[EQ] = NoReply('Timed out')
        del self.session.indices[OUTDOOR]
        self.session.responses[(9,0)] = NoReply('Battery unavailable')
        info = await self.settings.snapshot()
        self.assertIsNone(info['capabilities']['eq'])
        self.assertFalse(info['capabilities']['outdoor'])
        self.assertTrue(info['capabilities']['battery'])
        self.assertIsNone(info['battery'])
        self.assertIsNone(info['eq'])
        self.assertEqual(info['errors']['eq'], 'Timed out')
        self.assertEqual(info['errors']['battery'], 'Battery unavailable')
        self.assertEqual(info['volume'],27)
        self.assertEqual(info['max_volume'],31)
        self.assertEqual(info['sleep_timer_unit'],'minutes (0 = Never)')
        self.assertFalse(info['capabilities']['standby'])
        self.assertEqual(self.session.lookups.count(XUP),2) # capability + sticky read

    async def test_bool_reply_is_not_fabricated_from_unknown_state(self):
        self.session.responses[(20,0)] = b'\x02'
        with self.assertRaises(ProtocolError): await self.settings.remote_activation()


if __name__ == '__main__': unittest.main()
