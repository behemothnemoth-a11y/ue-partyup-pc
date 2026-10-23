import unittest
from unittest.mock import patch, AsyncMock
from types import SimpleNamespace
from ue_partyup.controls import settings_session
from ue_partyup.controller import Speaker
from ue_partyup.settings import Settings
from ue_partyup.session import ProtocolError

class GuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_guest_connection_never_opens_when_host_active_unknown_or_unreachable(self):
        for response in (b'\2\0',b'\3\0',b'bad',RuntimeError('timeout')):
            host=AsyncMock();host.__aenter__.return_value=host
            host.feature.return_value=11
            if isinstance(response,Exception):host.request.side_effect=response
            else:host.request.return_value=response
            with patch('ue_partyup.controls.Session',return_value=host) as factory:
                with self.assertRaises((RuntimeError,ProtocolError)):
                    async with settings_session(Speaker(2),group_host=1):self.fail('Guest was opened')
                self.assertEqual(factory.call_count,1)
                self.assertEqual(factory.call_args.args[0].address,1)
                host.__aexit__.assert_awaited()

    async def test_guest_allowed_only_after_host_confirms_off(self):
        host=AsyncMock();host.__aenter__.return_value=host;host.request.return_value=b'\0\0'
        guest=SimpleNamespace(connect=AsyncMock(),close=lambda:None)
        with patch('ue_partyup.controls.Session',side_effect=[host,guest]) as factory:
            async with settings_session(Speaker(2),group_host=1) as settings:
                self.assertIs(settings.session,guest)
            self.assertEqual(factory.call_count,2)

    async def test_sticky_no_write_if_active_malformed_or_query_fails(self):
        for response in (b'\2\0',b'\3\0',b'bad',RuntimeError('timeout')):
            session=AsyncMock();settings=Settings(session)
            if isinstance(response,Exception):session.request.side_effect=response
            else:session.request.return_value=response
            with self.assertRaises((RuntimeError,ProtocolError)):
                await settings.set_sticky(True)
            self.assertEqual(session.request.await_count,1)
            self.assertTrue(session.request.call_args.kwargs['read'])
