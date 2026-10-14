import unittest
from ue_partyup.controller import Speaker
from ue_partyup.session import Session, NoReply, UnsupportedFeature, ProtocolError


def frame(index,function,sequence,payload=b''):
    return bytes([0x13,0xa0,len(payload)+3,0,index,function*16+sequence])+payload+b'\0\0'


class Transport:
    def __init__(self,address): self.calls=[]; self.closes=0
    def request(self,index,function,sequence,payload,seconds):
        self.calls.append((index,function,sequence,payload))
        return [frame(11,0,0,b'\0'), frame(index,function,sequence,b'\1\0\1' if index==0 else b'\3\0')]
    def close(self): self.closes+=1
    def read_modern(self,seconds): return [frame(11,0,0,b'\0')]


class SessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_dynamic_lookup_cached_and_notification_retained(self):
        transport=Transport(1)
        async with Session(Speaker(1),lambda a:transport) as session:
            self.assertEqual(await session.feature(1),1)
            self.assertEqual(len(transport.calls),1)
            self.assertEqual(await session.request(11,1,read=True),b'\3\0')
            self.assertEqual(len(session.notifications),2)
        self.assertEqual(transport.closes,1)
        session.close()
        self.assertEqual(transport.closes,1)

    async def test_missing_reply_only_retries_reads(self):
        transport=Transport(1)
        session=Session(Speaker(1),lambda a:transport)
        await session.connect()
        transport.request=lambda *args: []
        with self.assertRaises(NoReply): await session.request(11,0,b'\3\0')
        with self.assertRaises(NoReply): await session.request(11,1,read=True)
        session.close()

    async def test_unsupported_feature_does_not_become_index_zero(self):
        transport=Transport(1)
        session=Session(Speaker(1),lambda a:transport)
        await session.connect()
        transport.request=lambda index,function,seq,*args: [frame(index,function,seq,b'\0\0\0')]
        with self.assertRaises(UnsupportedFeature): await session.feature(0x204)
        session.close()

    async def test_stale_reply_is_not_current(self):
        transport=Transport(1)
        session=Session(Speaker(1),lambda a:transport)
        await session.connect()
        transport.request=lambda index,function,seq,*args:[frame(index,function,(seq%15)+1,b'\3\0')]
        with self.assertRaises(NoReply): await session.request(11,1,read=True)
        session.close()

    async def test_correlated_error_does_not_look_like_success(self):
        transport=Transport(1)
        session=Session(Speaker(1),lambda a:transport)
        await session.connect()
        def rejected(index,function,seq,*args):
            data=bytearray(frame(index,function,seq,b'\3')); data[3]=255
            return [bytes(data)]
        transport.request=rejected
        with self.assertRaisesRegex(ProtocolError,'rejected'): await session.request(11,0,b'\3\0')
        session.close()


if __name__=='__main__': unittest.main()
