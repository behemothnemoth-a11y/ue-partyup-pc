import unittest
from dataclasses import dataclass

from ue_partyup.legacy import (
    LegacySession, LegacyProtocolError, LegacyUnsupportedError,
    LegacyExperimentRequired, encode_packet, decode_frame, model_from_device_id,
    LegacySettings,
)


@dataclass
class Speaker:
    address: int = 0x101112131415


class FakeTransport:
    def __init__(self, address):
        self.address = address
        self.writes = []
        self.acks = []
        self.closed = False
        self.responses = {
            1: [encode_packet(2, b"0100")],
            6: [encode_packet(7, b"MAXIMUS\0")],
            0x016D: [encode_packet(0x016E, b"Test speaker\0")],
            0x0414: [encode_packet(0x0415, b"\3\0")],
        }

    def command(self, opcode, payload=b"", seconds=2):
        self.writes.append((opcode, payload))
        return self.responses.get(opcode, [encode_packet(0, opcode.to_bytes(2, "big") + b"\0")])

    def acknowledge(self, opcode):
        self.acks.append(opcode)

    def close(self):
        self.closed = True


class FrameTests(unittest.TestCase):
    def test_source_backed_length_and_big_endian_opcode(self):
        self.assertEqual(encode_packet(0x0413, b"\3\0"), b"\4\4\x13\3\0")
        self.assertEqual(decode_frame(encode_packet(0x0415, b"\3\0")), (0x0415, b"\3\0"))

    def test_invalid_frame_never_becomes_a_successful_ack(self):
        for frame in (b"", b"\2\0", b"\5\0\0\4\x13", b"\2\0\0\0"):
            with self.subTest(frame=frame), self.assertRaises(LegacyProtocolError):
                decode_frame(frame)

    def test_oversize_payload_and_opcode_rejected(self):
        for opcode, payload in ((-1, b""), (65536, b""), (True, b""), (1, bytes(254))):
            with self.subTest(opcode=opcode), self.assertRaises(ValueError):
                encode_packet(opcode, payload)

    def test_original_models_are_not_assumed_to_be_cpp(self):
        self.assertEqual(model_from_device_id("UE Boom"), ("BOOM", "SMALL"))
        self.assertEqual(model_from_device_id("MEGABOOM"), ("MEGABOOM", "BIG"))
        self.assertEqual(model_from_device_id("MAXIMUS"), ("BOOM 2", "SMALL"))
        self.assertEqual(model_from_device_id("MENDOCIN"), ("BOOM 3", "SMALL"))
        self.assertEqual(model_from_device_id("MendocinoCR"), ("Unknown legacy device", "NO_GROUP"))
        self.assertEqual(model_from_device_id("EVERBOOM"), ("Unknown legacy device", "NO_GROUP"))


class LegacySessionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fake = FakeTransport(Speaker().address)
        self.session = LegacySession(Speaker(), transport_factory=lambda address: self.fake)
        await self.session.connect()

    async def asyncTearDown(self):
        self.session.close()

    async def test_probe_is_read_only_and_does_not_claim_hardware_compatibility(self):
        report = await self.session.probe()
        self.assertEqual(report.model, "BOOM 2")
        self.assertEqual(report.broadcast_state, (3, 0))
        self.assertTrue(report.broadcast_available)
        self.assertFalse(report.hardware_verified)
        self.assertEqual([op for op, _ in self.fake.writes], [1, 6, 0x016D, 0x0414])
        self.assertEqual(self.fake.acks, [2, 7, 0x016E, 0x0415])
        with self.assertRaises(LegacyExperimentRequired):
            await self.session.set_broadcast(3)
        self.assertEqual(len(self.fake.writes), 4)

    async def test_query_rejects_arbitrary_opcode_and_reply_pair_before_send(self):
        for opcode, expected in ((0x0413, 0), (1, 4), (0xFFFF, 0)):
            with self.subTest(opcode=opcode), self.assertRaises(ValueError):
                await self.session.query(opcode, expected)
        self.assertEqual(self.fake.writes, [])

    async def test_opt_in_still_requires_protocol_and_broadcast_probe(self):
        self.session.experimental = True
        with self.assertRaises(LegacyExperimentRequired):
            await self.session.set_volume(12)
        await self.session.query(1, 2)
        with self.assertRaises(LegacyExperimentRequired):
            await self.session.set_broadcast(3)
        self.assertEqual([op for op, _ in self.fake.writes], [1])

    async def test_unknown_device_identity_cannot_enable_mutations(self):
        self.session.experimental = True
        self.fake.responses[6] = [encode_packet(7, b"unrelated speaker\0")]
        report = await self.session.probe()
        self.assertEqual(report.profile, "NO_GROUP")
        self.assertTrue(report.broadcast_available)
        with self.assertRaisesRegex(LegacyExperimentRequired, "known legacy"):
            await self.session.set_broadcast(3)
        self.assertEqual(len(self.fake.writes), 4)

    async def test_source_backed_host_payloads_and_matching_ack(self):
        self.session.experimental = True
        await self.session.probe()
        guest = 0x010203040506
        await self.session.set_broadcast(3)
        await self.session.add_guest(guest)
        await self.session.remove_guest(guest)
        await self.session.sync_volume()
        self.assertEqual(self.fake.writes[4:], [
            (0x0413, b"\3\0"),
            (0x0417, bytes.fromhex("01020304050603")),
            (0x0419, bytes.fromhex("010203040506")),
            (0x041B, b""),
        ])

    async def test_other_command_ack_does_not_satisfy_request(self):
        self.session.experimental = True
        await self.session.probe()
        self.fake.responses[0x0413] = [encode_packet(0, b"\4\x19\0")]
        with self.assertRaisesRegex(LegacyProtocolError, "No matching reply"):
            await self.session.set_broadcast(3)
        self.assertEqual(sum(op == 0x0413 for op, _ in self.fake.writes), 1)

    async def test_query_ack_is_not_a_substitute_for_information(self):
        self.fake.responses[1] = [encode_packet(0, b"\0\1\0")]
        with self.assertRaises(LegacyProtocolError):
            await self.session.query(1, 2)
        self.assertFalse(self.session.protocol_verified)

    async def test_error_ack_rejected_and_mutation_not_retried(self):
        self.session.experimental = True
        await self.session.probe()
        self.fake.responses[0x0413] = [encode_packet(0, b"\4\x13\3")]
        with self.assertRaisesRegex(LegacyProtocolError, "status 3"):
            await self.session.set_broadcast(3)
        self.assertEqual(sum(op == 0x0413 for op, _ in self.fake.writes), 1)

    async def test_explicit_unrecognized_broadcast_is_a_negative_capability(self):
        self.fake.responses[0x0414] = [encode_packet(0, b"\4\x14\1")]
        report = await self.session.probe()
        self.assertFalse(report.broadcast_available)
        self.assertIsNone(report.broadcast_state)
        self.assertFalse(self.session.broadcast_verified)

    async def test_timeout_does_not_become_a_negative_capability(self):
        self.fake.responses[0x0414] = []
        with self.assertRaisesRegex(LegacyProtocolError, "result is unknown"):
            await self.session.probe()

    async def test_failed_reprobe_revokes_previous_write_capability(self):
        self.session.experimental = True
        await self.session.probe()
        self.fake.responses[0x0414] = [encode_packet(0, b"\4\x14\1")]
        with self.assertRaises(LegacyUnsupportedError):
            await self.session.query_broadcast()
        with self.assertRaises(LegacyExperimentRequired):
            await self.session.sync_volume()
        self.fake.responses[1] = []
        with self.assertRaises(LegacyProtocolError):
            await self.session.query(1, 2)
        self.assertFalse(self.session.protocol_verified)

    async def test_malformed_broadcast_configuration_not_marked_supported(self):
        self.fake.responses[0x0414] = [encode_packet(0x0415, b"\3")]
        with self.assertRaises(LegacyProtocolError):
            await self.session.query_broadcast()
        self.assertFalse(self.session.broadcast_verified)

    async def test_current_app_center_audio_options_are_accepted(self):
        self.session.experimental = True
        await self.session.probe()
        for option in (0x70, 0xB0):
            self.fake.responses[0x0414] = [encode_packet(0x0415, bytes((3, option)))]
            self.assertEqual(await self.session.query_broadcast(), (3, option))
            await self.session.set_broadcast(3, option)
            self.assertEqual(self.fake.writes[-1], (0x0413, bytes((3, option))))

    async def test_unrelated_notification_acknowledged_but_not_used_as_result(self):
        self.fake.responses[1].insert(0, encode_packet(0x0416, b"\0"))
        self.assertEqual(await self.session.query(1, 2), b"0100")
        self.assertEqual(self.fake.acks, [0x0416, 2])

    async def test_guest_self_and_invalid_ranges_rejected_before_send(self):
        self.session.experimental = True
        await self.session.probe()
        initial = len(self.fake.writes)
        for address in (self.session.speaker.address, 0, -1, 1 << 48, True):
            with self.subTest(address=address), self.assertRaises(ValueError):
                await self.session.add_guest(address)
        with self.assertRaises(ValueError):
            await self.session.add_guest(1, 0)
        self.assertEqual(len(self.fake.writes), initial)

    async def test_settings_validate_byte_lengths_and_volume_range(self):
        self.session.experimental = True
        await self.session.probe()
        for name in ("", "bad\0name", "é" * 25):
            with self.subTest(name=name), self.assertRaises(ValueError):
                await self.session.set_name(name)
        for volume, steps in ((32, 32), (16, 16), (-1, 32), (True, 32), (5, 100)):
            with self.subTest(volume=volume), self.assertRaises(ValueError):
                await self.session.set_volume(volume, steps)
        await self.session.set_name("é" * 24)
        await self.session.set_volume(15, 16)
        self.assertEqual(self.fake.writes[-2:], [(0x016F, ("é" * 24).encode() + b"\0"), (0x0190, b"\x0F")])

    async def test_context_cleanup_and_close_clear_probe_permissions(self):
        async with self.session:
            await self.session.probe()
        self.assertTrue(self.fake.closed)
        self.assertIsNone(self.session.transport)
        self.assertFalse(self.session.protocol_verified)
        self.assertFalse(self.session.broadcast_verified)
        self.session.close()  # Idempotent.


class LegacySettingsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fake = FakeTransport(Speaker().address)
        self.session = LegacySession(Speaker(), experimental=True, transport_factory=lambda address: self.fake)
        await self.session.connect()
        await self.session.probe()
        self.settings = LegacySettings(self.session)

    async def asyncTearDown(self):
        self.session.close()

    async def test_16_step_fallback_requires_explicit_unsupported_read(self):
        self.fake.responses[0x018E] = [encode_packet(0, b"\1\x8E\1")]
        self.fake.responses[0x0191] = [encode_packet(0x0192, b"\5")]
        self.assertEqual(await self.settings.volume(), 5)
        await self.settings.set_volume(15)
        self.assertEqual(self.fake.writes[-3:], [(0x018E, b""), (0x0191, b""), (0x0190, b"\x0F")])
        with self.assertRaises(ValueError):
            await self.settings.set_volume(16)

    async def test_volume_read_timeout_never_triggers_fallback_or_mutation(self):
        self.fake.responses[0x018E] = []
        with self.assertRaises(LegacyProtocolError):
            await self.settings.set_volume(10)
        self.assertEqual(self.fake.writes[4:], [(0x018E, b"")])

    async def test_snapshot_preserves_unknown_timeout_and_other_read_results(self):
        self.fake.responses[0x018E] = []
        self.fake.responses[0x0193] = [encode_packet(0x0194, b"\1")]
        self.fake.responses[0x042A] = [encode_packet(0, b"\4\x2A\1")]
        snapshot = await self.settings.snapshot()
        self.assertEqual(snapshot["name"], "Test speaker")
        self.assertTrue(snapshot["sticky"])
        self.assertIsNone(snapshot["volume"])
        self.assertIsNone(snapshot["capabilities"]["volume"])
        self.assertFalse(snapshot["capabilities"]["public"])
        self.assertIn("volume", snapshot["errors"])
        self.assertNotIn(0x0191, [op for op, _ in self.fake.writes])

    async def test_snapshot_reports_volume_range_used_by_setter(self):
        self.fake.responses[0x018E] = [encode_packet(0x018F, b"\x13")]
        self.fake.responses[0x0193] = [encode_packet(0x0194, b"\0")]
        self.fake.responses[0x042A] = [encode_packet(0x042B, b"\1")]
        snapshot = await self.settings.snapshot()
        self.assertEqual(snapshot["max_volume"], 31)
        self.assertEqual(snapshot["volume"], 19)
        self.assertTrue(snapshot["public"])
        self.assertEqual(snapshot["errors"], {})


if __name__ == "__main__":
    unittest.main()
