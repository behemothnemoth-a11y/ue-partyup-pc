import unittest
from ue_partyup.everboom_protocol import packet
from ue_partyup.controller import matching,acknowledged,Speaker,control

class ProtocolTests(unittest.TestCase):
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

if __name__=='__main__': unittest.main()
