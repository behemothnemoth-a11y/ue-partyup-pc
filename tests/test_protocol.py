import unittest
from unittest.mock import patch,AsyncMock
from ue_partyup.everboom_protocol import packet,extract_frames,RequestIds
from ue_partyup.controller import matching,acknowledged,Speaker,control

class ProtocolTests(unittest.TestCase):
    def test_reply_device_id_is_not_length_high_byte(self):
        # A nonzero device-ID byte previously looked like a 256-byte length extension.
        frame=bytes.fromhex('13a0030101020000')
        buffer=bytearray(frame)
        self.assertEqual(extract_frames(buffer),[frame])
        self.assertEqual(buffer,bytearray())
    def test_fragmented_reply_and_following_frame(self):
        first=bytes.fromhex('13a005000b1203000000')
        second=bytes.fromhex('13a003000b030000')
        buffer=bytearray(first[:5])
        self.assertEqual(extract_frames(buffer),[])
        buffer.extend(first[5:]+second)
        self.assertEqual(extract_frames(buffer),[first,second])
    def test_high_length_bits_in_header_nibble(self):
        frame=bytes([0x13,0xa1,0x03])+bytes(259)+bytes(2)
        self.assertEqual(extract_frames(bytearray(frame)),[frame])
    def test_request_id_wrap_avoids_notification_id_zero(self):
        ids=RequestIds()
        self.assertEqual([ids.next() for _ in range(17)],list(range(1,16))+[1,2])
    def test_captured_packets(self):
        self.assertEqual(packet(0,0,1,b'\0\1').hex(),'13a00500000100016817')
        self.assertEqual(packet(11,0,15,b'\3\0').hex(),'13a005000b0f030087fc')
        self.assertEqual(packet(11,1,9).hex(),'13a003000b195ce0')
        self.assertEqual(packet(11,0,14,b'\0\0').hex(),'13a005000b0e0000338c')
    def test_ack_matches_request_and_not_notification(self):
        ack=bytes.fromhex('13a003000b0f0000')
        notification=bytes.fromhex('13a004000b70030000')
        self.assertTrue(acknowledged([ack,notification],11,0,15))
        self.assertFalse(acknowledged([ack],11,0,14))
        self.assertFalse(acknowledged([notification],11,0,15))
    def test_nonzero_ack_trailer_not_success(self):
        self.assertFalse(acknowledged([bytes.fromhex('13a003000b0f0100')],11,0,15))

class ValidationTests(unittest.IsolatedAsyncioTestCase):
    async def test_same_speaker_rejected_before_connect(self):
        with self.assertRaises(ValueError): await control('start',Speaker(1),Speaker(1))
    async def test_unknown_action_rejected_before_connect(self):
        with self.assertRaises(ValueError): await control('erase',Speaker(1),Speaker(2))

class CompatibilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_pair_entry_point_uses_group_manager(self):
        result=AsyncMock(return_value='accepted')
        with patch('ue_partyup.groups.GroupManager.run',result):
            self.assertEqual(await control('start',Speaker(1),Speaker(2)),'accepted')
        self.assertEqual(result.call_args.args[:3],('start',Speaker(1),[Speaker(2)]))

if __name__=='__main__': unittest.main()
