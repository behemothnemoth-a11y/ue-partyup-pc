"""Deterministic timing tests; no radio, real waits, or speaker commands."""
import unittest
from unittest.mock import Mock, patch
from ue_partyup.everboom_protocol import Everboom


def reply(category, operation, sequence, payload=b'', device=0):
    return bytes([0x13, 0xa0, 3+len(payload), device, category,
                  operation*16+sequence])+payload+b'\0\0'


class ResponseLatencyTests(unittest.TestCase):
    def transport(self, chunks):
        clock = [100.0]
        pending = iter(chunks)
        transport = Everboom.__new__(Everboom)
        transport.buffer = bytearray()
        transport.send_all = Mock()
        def receive(remaining):
            data = next(pending, None)
            clock[0] += .001 if data is not None else remaining
            return data
        transport.recv_chunk = Mock(side_effect=receive)
        return transport, clock

    def test_matching_reply_returns_without_waiting_out_timeout(self):
        expected = reply(11, 1, 4, b'\3\0')
        transport, clock = self.transport([expected])
        with patch('ue_partyup.everboom_protocol.time.monotonic', side_effect=lambda:clock[0]):
            self.assertEqual(transport.request(11, 1, 4), [expected])
        self.assertLess(clock[0]-100, .01)
        self.assertEqual(transport.recv_chunk.call_count, 1)

    def test_notification_and_other_request_do_not_end_wait(self):
        notification = reply(11, 0, 0, b'\0')
        stale = reply(11, 1, 3, b'\3\0')
        expected = reply(11, 1, 4, b'\3\0')
        transport, clock = self.transport([notification+stale, expected[:4], expected[4:]])
        with patch('ue_partyup.everboom_protocol.time.monotonic', side_effect=lambda:clock[0]):
            frames = transport.request(11, 1, 4)
        self.assertEqual(frames, [notification, stale, expected])
        self.assertEqual(transport.recv_chunk.call_count, 3)

    def test_all_notifications_in_reply_batch_preserved(self):
        notification = reply(11, 0, 0, b'\0')
        expected = reply(11, 1, 4, b'\3\0')
        transport, clock = self.transport([expected+notification])
        with patch('ue_partyup.everboom_protocol.time.monotonic', side_effect=lambda:clock[0]):
            self.assertEqual(transport.request(11, 1, 4), [expected, notification])

    def test_correlated_error_returns_for_session_to_decode(self):
        error = reply(11, 1, 4, b'\3', device=255)
        transport, clock = self.transport([error])
        with patch('ue_partyup.everboom_protocol.time.monotonic', side_effect=lambda:clock[0]):
            self.assertEqual(transport.request(11, 1, 4), [error])
        self.assertEqual(transport.recv_chunk.call_count, 1)

    def test_missing_reply_retains_full_deadline(self):
        notification = reply(11, 0, 0, b'\0')
        transport, clock = self.transport([notification])
        with patch('ue_partyup.everboom_protocol.time.monotonic', side_effect=lambda:clock[0]):
            self.assertEqual(transport.request(11, 1, 4), [notification])
        self.assertAlmostEqual(clock[0]-100, 2)

    def test_explicit_event_listener_still_waits_its_window(self):
        notification = reply(11, 0, 0, b'\0')
        transport, clock = self.transport([notification])
        with patch('ue_partyup.everboom_protocol.time.monotonic', side_effect=lambda:clock[0]):
            self.assertEqual(transport.read_modern(2), [notification])
        self.assertAlmostEqual(clock[0]-100, 2)
