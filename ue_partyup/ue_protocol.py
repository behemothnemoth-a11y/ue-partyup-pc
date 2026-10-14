"""Native Windows RFCOMM transport for evidence-based UE protocol testing."""
import ctypes as c
from ctypes import wintypes as w
import time
import uuid
import json
from pathlib import Path
from .test_connection import Address, targets
from .diagnose import SPP


class UE:
    def __init__(self, address):
        self.ws = ws = c.WinDLL('Ws2_32.dll')
        ws.WSAStartup.argtypes = [w.WORD, c.c_void_p]
        ws.socket.argtypes = [c.c_int, c.c_int, c.c_int]
        ws.socket.restype = c.c_size_t
        ws.connect.argtypes = [c.c_size_t, c.c_void_p, c.c_int]
        ws.closesocket.argtypes = [c.c_size_t]
        ws.send.argtypes = ws.recv.argtypes = [c.c_size_t, c.c_void_p, c.c_int, c.c_int]
        ws.setsockopt.argtypes = [c.c_size_t, c.c_int, c.c_int, c.c_void_p, c.c_int]
        if ws.WSAStartup(0x0202, c.byref((c.c_ulonglong * 64)())):
            raise RuntimeError('Winsock startup failed')
        self.sock = ws.socket(32, 1, 3)
        self.buffer = bytearray()
        self.received_bytes = 0
        destination = Address()
        destination.family = 32
        destination.address = address
        destination.service[:] = uuid.UUID(SPP).bytes_le
        if ws.connect(self.sock, c.byref(destination), c.sizeof(destination)):
            error = ws.WSAGetLastError()
            self.close()
            raise RuntimeError(f'connect error {error}')
        timeout = w.DWORD(1000)
        ws.setsockopt(self.sock, 0xffff, 0x1006, c.byref(timeout), 4)
        ws.setsockopt(self.sock, 0xffff, 0x1005, c.byref(timeout), 4)

    def close(self):
        self.ws.closesocket(self.sock)
        self.ws.WSACleanup()

    def command(self, opcode, payload=b'', seconds=2):
        packet = bytes([len(payload) + 2]) + opcode.to_bytes(2, 'big') + payload
        sent = self.ws.send(self.sock, packet, len(packet), 0)
        if sent != len(packet):
            raise RuntimeError(f'send failed {self.ws.WSAGetLastError()}')
        return self.read(seconds)

    def read(self, seconds):
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
            self.received_bytes += count
            while self.buffer and len(self.buffer) >= self.buffer[0] + 1:
                size = self.buffer[0] + 1
                frame = bytes(self.buffer[:size])
                del self.buffer[:size]
                frames.append(frame)
        return frames


