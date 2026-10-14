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
    body = bytes([category, (operation << 4) | sequence]) + payload
    prefix = b'\x13\xa0' + (len(body) + 1).to_bytes(2, 'little') + body
    return prefix + crc16(prefix).to_bytes(2, 'little')


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
            while len(self.buffer) >= 4:
                if self.buffer[:2] != b'\x13\xa0':
                    del self.buffer[0]
                    continue
                size = int.from_bytes(self.buffer[2:4], 'little') + 5
                if len(self.buffer) < size:
                    break
                frames.append(bytes(self.buffer[:size]))
                del self.buffer[:size]
        return frames


