"""Source-backed modern BLE remote wake, explicitly opt-in until hardware tested."""
import asyncio
from bleak import BleakClient

POWER_UUID = '5e9bf2a8-f93f-4481-a67e-3b2f4a07891a'
# The app's default AUID is six bytes of 02, followed by POWER_ON (FF).
# This is a public protocol constant, not a device credential.
WAKE_PAYLOAD = bytes([2] * 6 + [0xFF])


async def wake_speaker(speaker, client_factory=BleakClient):
    if speaker.experimental:
        raise ValueError('This wake flow is limited to modern EVERBOOM support; older models need their own verified flow.')
    address = ':'.join(f'{byte:02X}' for byte in speaker.address.to_bytes(6, 'big'))
    async def send():
        async with client_factory(address, timeout=12) as client:
            characteristic = client.services.get_characteristic(POWER_UUID)
            if characteristic is None or 'write' not in characteristic.properties:
                raise RuntimeError('The remote-power characteristic does not support an acknowledged write. No wake sent.')
            await asyncio.wait_for(client.write_gatt_char(characteristic, WAKE_PAYLOAD, response=True), 8)
    await asyncio.wait_for(send(), 25)
    return 'Wake write acknowledged. Power-on is not independently confirmed; use Read controls after the speaker wakes.'
