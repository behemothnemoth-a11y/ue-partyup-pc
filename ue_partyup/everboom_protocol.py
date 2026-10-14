"""EVERBOOM framing recovered from the user's official-app capture."""
import time
import json
from pathlib import Path
from .ue_protocol import UE
from .test_connection import targets


def crc16(data):
    value = 65535
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = (value >> 1) ^ 0x8408 if value & 1 else value >> 1
    return value


def packet(category, operation, sequence, payload=b''):
    if not 0 <= category <= 255 or not 0 <= operation <= 15 or not 1 <= sequence <= 15:
        raise ValueError('Invalid CPP request identifiers')
    body = bytes([0, category, (operation << 4) | sequence]) + payload
    if len(body)>4095:
        raise ValueError('CPP payload exceeds frame length limit')
    prefix = bytes([0x13,0xa0 | (len(body)>>8),len(body)&255]) + body
    return prefix + crc16(prefix).to_bytes(2, 'little')

def extract_frames(buffer):
    frames=[]
    while len(buffer)>=3:
        if buffer[0]!=0x13 or buffer[1]&0xf0!=0xa0:
            del buffer[0]
            continue
        size=((buffer[1]&15)<<8 | buffer[2])+5
        if size<8:
            del buffer[0]
            continue
        if len(buffer)<size:
            break
        frames.append(bytes(buffer[:size]))
        del buffer[:size]
    return frames

class RequestIds:
    def __init__(self): self.value=0
    def next(self):
        self.value=self.value%15+1
        return self.value

class Everboom(UE):
    def request(self, category, operation, sequence, payload=b'', seconds=2):
        data = packet(category, operation, sequence, payload)
        if self.ws.send(self.sock, data, len(data), 0) != len(data):
            raise RuntimeError('send failed')
        return self.read_modern(seconds)

    def read_modern(self, seconds):
        import ctypes as c
        frames = []
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            data = c.create_string_buffer(4096)
            count = self.ws.recv(self.sock, data, len(data), 0)
            if count == 0:
                break
            if count < 0:
                error = self.ws.WSAGetLastError()
                if error == 10060:
                    continue
                raise RuntimeError(f'receive error {error}')
            self.buffer.extend(data.raw[:count])
            frames.extend(extract_frames(self.buffer))
        return frames


