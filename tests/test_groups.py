import unittest
from unittest.mock import AsyncMock
from ue_partyup.controller import Speaker
from ue_partyup.groups import GroupManager, receivers, validate_group, broadcasting
from ue_partyup.session import ProtocolError


def receiver_frame(addresses):
    payload = bytes([len(addresses)]) + b''.join(a.to_bytes(6,'big') + b'\0\6\0\0' for a in addresses)
    length = len(payload)+3
    return bytes([0x13,0xa0|(length>>8),length&255,0,11,0])+payload+b'\0\0'


class FakeSession:
    def __init__(self, speaker, addresses=()):
        self.on = False
        self.mode = 3
        self.audio = 0
        self.notifications = [receiver_frame(addresses)]
        self.commands = []
        self.closed = False
    async def __aenter__(self): return self
    async def __aexit__(self,*args): self.closed=True
    async def feature(self,feature): return 11
    async def request(self,index,function,payload=b'',**kwargs):
        self.commands.append((index,function,payload))
        if function==1: return bytes([self.mode if self.on else 0,self.audio])
        if function==0:
            self.on=bool(payload[0])
            self.mode,self.audio=payload
        return b''
    async def listen(self,seconds): return []


class FakeClient:
    def __init__(self, address, writes, failures=()):
        self.address=int(address.replace(':',''),16)
        self.writes=writes
        self.failures=failures
    async def __aenter__(self):
        if self.address in self.failures: raise RuntimeError('unreachable')
        return self
    async def __aexit__(self,*args): pass
    async def write_gatt_char(self, uuid, value, response): self.writes.append((self.address,value))


class GroupTests(unittest.IsolatedAsyncioTestCase):
    async def test_driver_cancellation_is_reported_and_later_guest_cleanup_continues(self):
        import asyncio
        session=FakeSession(Speaker(1),(2,3));session.on=True;writes=[]
        class CancelingClient(FakeClient):
            async def __aenter__(self):
                if self.address==2: raise asyncio.CancelledError()
                return self
        manager=GroupManager(lambda speaker:session,
            lambda address,**kwargs:CancelingClient(address,writes))
        result=await manager.run('stop',Speaker(1),[Speaker(2),Speaker(3)])
        self.assertFalse(result.host_on)
        self.assertEqual(result.members[0].state,'unconfirmed')
        self.assertEqual(result.members[1].state,'leave accepted')
        self.assertEqual(writes,[(3,bytes(8))]);self.assertTrue(session.closed)


    def test_scanning_only_does_not_count_as_audio_broadcast(self):
        self.assertFalse(broadcasting(b'\0\0'))
        self.assertFalse(broadcasting(b'\1\0'))
        self.assertTrue(broadcasting(b'\2\0'))
        self.assertTrue(broadcasting(b'\3\0'))
        for payload in (b'', b'\3', b'\4\0', b'\xff\0'):
            with self.assertRaises(RuntimeError): broadcasting(payload)

    def make(self,addresses=(),failures=()):
        session=FakeSession(Speaker(1),addresses)
        writes=[]
        manager=GroupManager(lambda speaker:session, lambda address,**kwargs:FakeClient(address,writes,failures))
        return manager,session,writes

    async def test_ten_members_all_join_and_receive_any_order(self):
        guests=[Speaker(i) for i in range(2,11)]
        manager,session,writes=self.make(list(reversed(range(2,11))))
        result=await manager.run('start',Speaker(1),guests)
        self.assertEqual(len(writes),9)
        self.assertEqual(len(result.reported),9)
        self.assertTrue(all(m.state=='reported by main speaker' for m in result.members))
        self.assertTrue(session.closed)

    async def test_eleven_rejected_before_connect(self):
        factory=AsyncMock()
        manager=GroupManager(factory)
        with self.assertRaises(ValueError):
            await manager.run('start',Speaker(1),[Speaker(i) for i in range(2,12)])
        factory.assert_not_called()

    async def test_start_does_not_rejoin_reported_active_guest(self):
        manager, session, writes = self.make((2,))
        session.on = True
        result = await manager.run('start', Speaker(1), [Speaker(2)])
        self.assertEqual(writes, [])
        self.assertEqual(result.members[0].state, 'reported by main speaker')
        self.assertIn('no join command', result.members[0].detail)
        self.assertFalse(any(op == 0 for _, op, _ in session.commands))

    async def test_scanning_only_host_is_enabled_before_joining(self):
        manager, session, writes = self.make()
        original = session.request
        async def scanning_until_enabled(index, function, payload=b'', **kwargs):
            if function == 1 and not session.on:
                return b'\1\0'
            return await original(index, function, payload, **kwargs)
        session.request = scanning_until_enabled
        result = await manager.run('start', Speaker(1), [Speaker(2)])
        self.assertIn((11, 0, b'\3\0'), session.commands)
        self.assertTrue(result.host_on)
        self.assertEqual(len(writes), 1)

    async def test_add_only_joins_new_guests(self):
        manager, session, writes = self.make((2,))
        session.on = True
        await manager.run('add', Speaker(1), [Speaker(2), Speaker(3)])
        self.assertEqual([address for address, value in writes], [3])

    async def test_ble_join_prepares_broadcast_only_and_preserves_audio(self):
        manager, session, writes = self.make()
        session.on = True
        session.audio = 0x50
        original_factory = manager.client_factory
        def checked_factory(*args, **kwargs):
            self.assertEqual((session.mode, session.audio), (2, 0x50))
            return original_factory(*args, **kwargs)
        manager.client_factory = checked_factory
        result = await manager.run('start', Speaker(1), [Speaker(2)])
        self.assertIn((11, 0, b'\2\x50'), session.commands)
        self.assertTrue(result.host_on)
        self.assertEqual(session.mode, 2)
        self.assertEqual(len(writes), 1)

    async def test_broadcast_only_host_needs_no_redundant_mode_write(self):
        manager, session, writes = self.make()
        session.on = True; session.mode = 2
        await manager.run('add', Speaker(1), [Speaker(2)])
        self.assertFalse(any(op == 0 for _,op,_ in session.commands))
        self.assertEqual(len(writes), 1)

    async def test_status_does_not_change_scanning_mode(self):
        manager, session, writes = self.make()
        session.on = True; session.mode = 3
        await manager.run('status', Speaker(1))
        self.assertEqual(session.mode, 3)
        self.assertFalse(any(op == 0 for _,op,_ in session.commands))

    async def test_unconfirmed_broadcast_only_mode_prevents_guest_join(self):
        manager, session, writes = self.make()
        session.on = True
        original_request = session.request
        async def request(index, operation, payload=b'', **kwargs):
            result = await original_request(index, operation, payload, **kwargs)
            if operation == 0 and payload[:1] == b'\2':
                session.mode = 3
            return result
        session.request = request
        with self.assertRaisesRegex(ProtocolError, 'Broadcaster-only mode was not confirmed'):
            await manager.run('add', Speaker(1), [Speaker(2)])
        self.assertFalse(writes)

    async def test_duplicate_rejected_before_connect(self):
        factory=AsyncMock()
        with self.assertRaises(ValueError):
            await GroupManager(factory).run('start',Speaker(1),[Speaker(2),Speaker(2)])
        factory.assert_not_called()

    async def test_failures_at_first_middle_last_preserve_successful_guests(self):
        for failure in (2,6,10):
            with self.subTest(failure=failure):
                manager,session,writes=self.make(failures=(failure,))
                result=await manager.run('start',Speaker(1),[Speaker(i) for i in range(2,11)])
                self.assertTrue(session.on)
                self.assertEqual(len(writes),8)
                self.assertEqual(sum(m.state=='unconfirmed' for m in result.members),1)
                self.assertNotIn((11,0,b'\0\0'),session.commands)

    async def test_stop_continues_guest_failures_and_verifies_off(self):
        manager,session,writes=self.make(failures=(3,))
        session.on=True
        result=await manager.run('stop',Speaker(1),[Speaker(2),Speaker(3),Speaker(4)])
        self.assertFalse(result.host_on)
        self.assertEqual(writes,[(2,bytes(8)),(4,bytes(8))])
        self.assertEqual(result.members[1].state,'unconfirmed')
        self.assertEqual(session.commands[:3],[(11,1,b''),(11,0,b'\0\0'),(11,1,b'')])

    async def test_remove_one_preserves_host_and_other_receivers(self):
        manager,session,writes=self.make((3,4))
        session.on=True
        result=await manager.run('remove',Speaker(1),[Speaker(2)])
        self.assertTrue(result.host_on)
        self.assertEqual(writes,[(2,bytes(8))])
        self.assertFalse(any(op==0 for _,op,_ in session.commands))

    async def test_status_needs_no_guest_and_never_mutates(self):
        manager,session,writes=self.make()
        await manager.run('status',Speaker(1))
        self.assertEqual(session.commands,[(11,1,b'')])
        self.assertFalse(writes)

    async def test_unknown_action_rejected(self):
        with self.assertRaises(ValueError): await self.make()[0].run('erase',Speaker(1))

    async def test_unknown_active_membership_cannot_bypass_ten_total(self):
        manager,session,writes=self.make()
        session.on=True; session.notifications=[]
        with self.assertRaisesRegex(RuntimeError,'membership is unknown'):
            await manager.run('add',Speaker(1),[Speaker(2)])
        self.assertFalse(writes)

    async def test_existing_receivers_count_toward_limit(self):
        manager,session,writes=self.make(range(2,11))
        session.on=True
        with self.assertRaisesRegex(ValueError,'exceed nine'):
            await manager.run('add',Speaker(1),[Speaker(11)])
        self.assertFalse(writes)

    def test_receiver_notifications_replace_prior_snapshot_and_validate_length(self):
        self.assertEqual(receivers([receiver_frame((2,3)),receiver_frame((4,))],11),{4:6})
        self.assertEqual(receivers([receiver_frame((2,))[:-1]],11),{})

    def test_experimental_models_require_opt_in(self):
        with self.assertRaises(ValueError): validate_group(Speaker(1),[Speaker(2,'BOOM',True)])
        validate_group(Speaker(1),[Speaker(2,'BOOM',True)],experimental=True)

    def test_invalid_addresses_rejected(self):
        for address in (0,-1,1<<48,True,'1'):
            with self.assertRaises(ValueError): Speaker(address)


if __name__=='__main__': unittest.main()
