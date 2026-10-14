import asyncio
from dataclasses import dataclass
from bleak import BleakClient
from .everboom_protocol import Everboom,RequestIds
from .test_connection import targets

GROUP_UUID='69c0f621-1354-4cf8-98a6-328b8faa1897'

@dataclass(frozen=True)
class Speaker:
    address: int
    @property
    def label(self):
        return f'EVERBOOM · {self.address & 65535:04X}'

def discover():
    return [Speaker(a) for a in sorted(targets())]

def matching(frames,category,operation,sequence):
    return [f for f in frames if len(f)>=8 and f[4]==category and f[5]==operation*16+sequence]

def acknowledged(frames,category,operation,sequence):
    return any(len(f)==8 and f[-2:]==b'\0\0' for f in matching(frames,category,operation,sequence))

async def control(action,host,guest,progress=lambda message:None):
    if host.address==guest.address:
        raise ValueError('Choose two different speakers.')
    if action not in ('start','stop','status'):
        raise ValueError('Unknown action.')
    progress('Connecting to the main speaker…')
    speaker=None
    for attempt in range(2):
        try:
            speaker=await asyncio.to_thread(Everboom,host.address)
            break
        except RuntimeError:
            if attempt:
                raise RuntimeError('Main speaker connection timed out. Keep it on, close the phone app, and check that the selected speaker is your audio source.') from None
            progress('Main speaker did not connect. Retrying once…')
            await asyncio.sleep(2)
    ids=RequestIds()
    async def request(cat,op,payload=b'',seconds=2):
        for attempt in range(2):
            seq=ids.next()
            frames=await asyncio.to_thread(speaker.request,cat,op,seq,payload,seconds)
            matches=matching(frames,cat,op,seq)
            if matches:
                return frames,seq
            if op!=1 and not (cat==0 and op==0):
                break  # Never retry a possibly accepted mutation blindly.
        return frames,seq
    try:
        frames,seq=await request(0,0,b'\0\1')
        if not matching(frames,0,0,seq):
            raise RuntimeError('The main speaker did not respond. Close the phone app and retry.')
        frames,seq=await request(11,1)
        states=matching(frames,11,1,seq)
        if not states or len(states[-1])<10:
            raise RuntimeError('The speaker did not return its PartyUp state.')
        prior=states[-1][6:8]
        if action=='status':
            return f'Main speaker: {"PartyUp off" if prior[0]==0 else "PartyUp enabled"}. State {prior[0]}; audio mode {prior[1]}. This does not verify guest playback.'
        progress('Starting the group…' if action=='start' else 'Stopping the group…')
        payload=b'\3\0' if action=='start' else b'\0\0'
        frames,seq=await request(11,0,payload)
        if not acknowledged(frames,11,0,seq):
            raise RuntimeError('No successful acknowledgement of the group command.')
        mac=':'.join(f'{b:02X}' for b in guest.address.to_bytes(6,'big'))
        progress('Connecting to the second speaker…')
        try:
            async with BleakClient(mac,timeout=15) as client:
                value=host.address.to_bytes(6,'big')+b'\1\2' if action=='start' else bytes(8)
                await client.write_gatt_char(GROUP_UUID,value,response=True)
        except Exception:
            # Restore prior host state if guest operation failed; report rollback failures honestly.
            restored=False
            try:
                rollback,seq=await request(11,0,prior)
                restored=acknowledged(rollback,11,0,seq)
            except Exception:
                pass
            raise RuntimeError('Second speaker connection/write failed. '+
                               ('Previous host state restored.' if restored else 'Host may be partially configured; check status.')) from None
        if action=='stop':
            frames,seq=await request(11,1)
            states=matching(frames,11,1,seq)
            if not states or states[-1][6]!=0:
                raise RuntimeError('Stop writes accepted, but host off-state was not verified.')
            return 'PartyUp stopped. Main speaker reports broadcasting off.'
        progress('Checking the second speaker…')
        frames=await asyncio.to_thread(speaker.read_modern,5)
        joined=any(len(f)>=19 and f[4:6]==b'\x0b\0' and f[6]>=1 and
                   f[7:13]==guest.address.to_bytes(6,'big') for f in frames)
        return ('Group started; main speaker reports your second speaker. Play audio through the selected main speaker.'
                if joined else 'Join writes accepted, but receiver confirmation was not observed. Check audio from both speakers.')
    finally:
        speaker.close()
