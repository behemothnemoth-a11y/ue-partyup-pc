import unittest
from unittest.mock import patch,AsyncMock
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

class FakeTransport:
    def __init__(self,address):
        self.closed=False
        self.state=b'\0\0'
        self.writes=[]
    def request(self,category,operation,sequence,payload=b'',seconds=2):
        self.writes.append((category,operation,sequence,payload))
        if category==0:
            return [bytes.fromhex('13a0060000010100010000')]
        if operation==1:
            return [b'\x13\xa0\5\0\x0b'+bytes([16+sequence])+self.state+b'\0\0']
        self.state=payload
        return [b'\x13\xa0\3\0\x0b'+bytes([sequence])+b'\0\0']
    def close(self): self.closed=True

class WorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_status_closes_transport_without_writes(self):
        fake=FakeTransport(1)
        with patch('ue_partyup.controller.Everboom',return_value=fake):
            result=await control('status',Speaker(1),Speaker(2))
        self.assertIn('PartyUp off',result)
        self.assertTrue(fake.closed)
        self.assertEqual(len(fake.writes),2)
    async def test_guest_failure_restores_prior_host_state(self):
        fake=FakeTransport(1)
        client=AsyncMock()
        client.__aenter__.side_effect=RuntimeError('not reachable')
        with patch('ue_partyup.controller.Everboom',return_value=fake),patch('ue_partyup.controller.BleakClient',return_value=client):
            with self.assertRaisesRegex(RuntimeError,'Previous host state restored'):
                await control('start',Speaker(1),Speaker(2))
        self.assertEqual(fake.state,b'\0\0')
        self.assertTrue(fake.closed)
    async def test_stop_clears_guest_and_verifies_host_off(self):
        fake=FakeTransport(1)
        fake.state=b'\3\0'
        client=AsyncMock()
        client.__aenter__.return_value=client
        with patch('ue_partyup.controller.Everboom',return_value=fake),patch('ue_partyup.controller.BleakClient',return_value=client):
            result=await control('stop',Speaker(1),Speaker(2))
        client.write_gatt_char.assert_awaited_once()
        self.assertEqual(client.write_gatt_char.call_args.args[1],bytes(8))
        self.assertIn('broadcasting off',result)
        self.assertTrue(fake.closed)

if __name__=='__main__': unittest.main()
