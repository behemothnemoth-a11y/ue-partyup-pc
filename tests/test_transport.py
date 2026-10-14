"""Transport failure tests use fake Winsock only; never contact hardware."""
import ctypes as c
from ctypes import wintypes as w
import unittest
from unittest.mock import patch
from ue_partyup.ue_protocol import UE, FDSet, Timeval, INVALID_SOCKET, SO_RCVTIMEO, SO_SNDTIMEO


class FakeFunction:
    def __init__(self, implementation):
        self.implementation = implementation
        self.calls = []

    def __call__(self, *args):
        self.calls.append(args)
        return self.implementation(*args)


class FakeWinsock:
    def __init__(self):
        self.startup_error = 0
        self.socket_result = 42
        self.connect_result = -1
        self.last_error = 10035
        self.socket_error = 0
        self.select_result = 1
        self.select_writable = True
        self.option_error = 0
        self.ioctl_error = 0
        self.send_counts = []
        self.sent_chunks = []
        self.receive_chunks = []
        self.timeouts = []
        self.connect_waits = []
        self.modes = []
        functions = {
            'WSAStartup': lambda *_: self.startup_error,
            'WSACleanup': lambda: 0,
            'WSAGetLastError': lambda: self.last_error,
            'socket': lambda *_: self.socket_result,
            'connect': lambda *_: self.connect_result,
            'closesocket': lambda *_: 0,
            'send': self.send_data,
            'recv': self.receive_data,
            'ioctlsocket': self.set_mode,
            'setsockopt': self.set_option,
            'getsockopt': self.get_option,
            'select': self.wait_connect,
        }
        for name, implementation in functions.items():
            setattr(self, name, FakeFunction(implementation))

    def set_mode(self, sock, code, value):
        self.modes.append(c.cast(value, c.POINTER(w.ULONG)).contents.value)
        return self.ioctl_error

    def set_option(self, sock, level, option, value, size):
        self.timeouts.append((option, c.cast(value, c.POINTER(w.DWORD)).contents.value))
        return self.option_error

    def get_option(self, sock, level, option, value, size):
        c.cast(value, c.POINTER(c.c_int)).contents.value = self.socket_error
        return 0

    def wait_connect(self, count, read, writable, failed, timeout):
        delay = c.cast(timeout, c.POINTER(Timeval)).contents
        self.connect_waits.append(delay.seconds + delay.microseconds / 1000000)
        c.cast(writable, c.POINTER(FDSet)).contents.count = int(self.select_writable)
        c.cast(failed, c.POINTER(FDSet)).contents.count = int(not self.select_writable)
        return self.select_result

    def send_data(self, sock, data, size, flags):
        count = self.send_counts.pop(0) if self.send_counts else size
        if count > 0:
            self.sent_chunks.append(c.string_at(data, min(count, size)))
        return count

    def receive_data(self, sock, data, size, flags):
        result = self.receive_chunks.pop(0) if self.receive_chunks else -1
        if isinstance(result, bytes):
            c.memmove(data, result, len(result))
            return len(result)
        return result


class TransportTests(unittest.TestCase):
    def open(self, fake, **options):
        with patch('ue_partyup.ue_protocol.c.WinDLL', return_value=fake):
            return UE(1, **options)

    def assert_closed_once(self, fake):
        self.assertEqual(len(fake.closesocket.calls), 1)
        self.assertEqual(len(fake.WSACleanup.calls), 1)

    def test_pending_connect_uses_deadline_and_returns_to_blocking(self):
        fake = FakeWinsock()
        with patch('ue_partyup.ue_protocol.time.monotonic', side_effect=[100, 100.25]):
            transport = self.open(fake)
        self.assertEqual(fake.modes, [1, 0])
        self.assertEqual(fake.connect_waits, [14.75])
        self.assertEqual(fake.timeouts[:2], [(SO_RCVTIMEO, 1000), (SO_SNDTIMEO, 1000)])
        self.assertEqual(len(fake.getsockopt.calls), 1)
        transport.close()
        transport.close()
        self.assert_closed_once(fake)

    def test_immediate_connect_does_not_wait(self):
        fake = FakeWinsock()
        fake.connect_result = 0
        transport = self.open(fake)
        self.assertEqual(len(fake.select.calls), 0)
        transport.close()

    def test_connect_timeout_cleans_up(self):
        fake = FakeWinsock()
        fake.select_result = 0
        with self.assertRaisesRegex(RuntimeError, 'timed out'):
            self.open(fake)
        self.assert_closed_once(fake)

    def test_failed_connect_result_is_not_mistaken_for_success(self):
        fake = FakeWinsock()
        fake.select_writable = False
        fake.socket_error = 10061
        with self.assertRaisesRegex(RuntimeError, '10061'):
            self.open(fake)
        self.assert_closed_once(fake)

    def test_immediate_connect_error_cleans_up(self):
        fake = FakeWinsock()
        fake.last_error = 10022
        with self.assertRaisesRegex(RuntimeError, '10022'):
            self.open(fake)
        self.assertEqual(len(fake.select.calls), 0)
        self.assert_closed_once(fake)

    def test_invalid_socket_is_never_closed_or_connected(self):
        fake = FakeWinsock()
        fake.socket_result = INVALID_SOCKET
        with self.assertRaisesRegex(RuntimeError, 'socket error'):
            self.open(fake)
        self.assertEqual(len(fake.connect.calls), 0)
        self.assertEqual(len(fake.closesocket.calls), 0)
        self.assertEqual(len(fake.WSACleanup.calls), 1)

    def test_startup_failure_does_not_unbalance_winsock(self):
        fake = FakeWinsock()
        fake.startup_error = 10091
        with self.assertRaisesRegex(RuntimeError, 'startup'):
            self.open(fake)
        self.assertEqual(len(fake.socket.calls), 0)
        self.assertEqual(len(fake.WSACleanup.calls), 0)

    def test_timeout_configuration_failure_closes_before_connect(self):
        fake = FakeWinsock()
        fake.option_error = -1
        with self.assertRaisesRegex(RuntimeError, 'timeout configuration'):
            self.open(fake)
        self.assertEqual(len(fake.connect.calls), 0)
        self.assert_closed_once(fake)

    def test_send_all_handles_partial_writes_without_replaying_prefix(self):
        fake = FakeWinsock()
        transport = self.open(fake)
        fake.send_counts = [2, 1, 2]
        self.assertEqual(transport.send_all(b'hello'), 5)
        self.assertEqual(fake.sent_chunks, [b'he', b'l', b'lo'])
        transport.close()

    def test_partial_send_failure_closes_and_reports_unknown_outcome(self):
        fake = FakeWinsock()
        transport = self.open(fake)
        fake.send_counts = [2, -1]
        fake.last_error = 10060
        with self.assertRaisesRegex(RuntimeError, 'outcome is unknown'):
            transport.send_all(b'hello')
        self.assertEqual(fake.sent_chunks, [b'he'])
        transport.close()
        self.assert_closed_once(fake)
        with self.assertRaisesRegex(RuntimeError, 'closed'):
            transport.send_all(b'new command')

    def test_partial_send_deadline_closes_without_sending_more(self):
        fake = FakeWinsock()
        transport = self.open(fake)
        fake.send_counts = [2, 3]
        with patch('ue_partyup.ue_protocol.time.monotonic', side_effect=[0, 0, 2]):
            with self.assertRaisesRegex(RuntimeError, 'timed out'):
                transport.send_all(b'hello', seconds=1)
        self.assertEqual(fake.sent_chunks, [b'he'])
        self.assert_closed_once(fake)

    def test_receive_timeout_preserves_connection_and_bounds_wait(self):
        fake = FakeWinsock()
        transport = self.open(fake)
        fake.last_error = 10060
        self.assertIsNone(transport.recv_chunk(0.025))
        self.assertEqual(fake.timeouts[-1], (SO_RCVTIMEO, 25))
        self.assertEqual(transport.sock, 42)
        transport.close()

    def test_receive_eof_is_explicit_and_closes(self):
        fake = FakeWinsock()
        transport = self.open(fake)
        fake.receive_chunks = [0]
        with self.assertRaisesRegex(RuntimeError, 'EOF'):
            transport.recv_chunk()
        transport.close()
        self.assert_closed_once(fake)

    def test_receive_failure_is_explicit_and_closes(self):
        fake = FakeWinsock()
        transport = self.open(fake)
        fake.last_error = 10054
        with self.assertRaisesRegex(RuntimeError, '10054'):
            transport.recv_chunk()
        self.assert_closed_once(fake)

    def test_legacy_read_preserves_fragmented_and_multiple_frames(self):
        fake = FakeWinsock()
        transport = self.open(fake)
        with patch.object(transport, 'recv_chunk', side_effect=[b'\x02\x04', b'\x13\x02\x04\x14']), \
             patch('ue_partyup.ue_protocol.time.monotonic', side_effect=[0, 0, 0.5, 1.5]):
            self.assertEqual(transport.read(1), [b'\x02\x04\x13', b'\x02\x04\x14'])
        self.assertEqual(transport.buffer, bytearray())
        transport.close()

    def test_legacy_command_uses_send_all(self):
        fake = FakeWinsock()
        transport = self.open(fake)
        with patch.object(transport, 'read', return_value=['reply']) as read:
            self.assertEqual(transport.command(0x0413, b'\x03\x00'), ['reply'])
        self.assertEqual(fake.sent_chunks, [b'\x04\x04\x13\x03\x00'])
        read.assert_called_once_with(2)
        transport.close()

    def test_invalid_address_fails_before_api_call(self):
        for address in (0, -1, 1 << 48, True, 'address'):
            with self.subTest(address=address), patch('ue_partyup.ue_protocol.c.WinDLL') as dll:
                with self.assertRaises(ValueError):
                    UE(address)
                dll.assert_not_called()


if __name__ == '__main__':
    unittest.main()
