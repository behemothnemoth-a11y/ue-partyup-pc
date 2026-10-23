import tempfile,time,tkinter as tk,unittest
from pathlib import Path
from unittest.mock import AsyncMock,Mock,patch
from ue_partyup.classroom_view import ClassroomApp
from ue_partyup.controller import Speaker

class GuardInterfaceTests(unittest.TestCase):
    def test_guest_read_error_clears_busy_and_allows_main_selection(self):
        with tempfile.TemporaryDirectory() as folder:
            root=tk.Tk();root.withdraw();app=ClassroomApp(root,Path(folder))
            try:
                app.show_discovery([Speaker(1,'EVERBOOM main'),Speaker(2,'EVERBOOM guest')],[])
                app.select_house_speaker(app.speakers[1])
                host=AsyncMock();host.__aenter__.return_value=host;host.request.return_value=b'\2\0'
                with patch('ue_partyup.controls.Session',return_value=host) as factory:
                    app.read_controls()
                    until=time.monotonic()+4
                    while app.busy and time.monotonic()<until:app._poll_events();time.sleep(.01)
                    self.assertFalse(app.busy)
                    self.assertIn('Guest controls are paused',app.status.get())
                    self.assertEqual(app.playback_notice.winfo_manager(),'pack')
                    self.assertIn('No guest control connection',app.playback_notice_text.get())
                    self.assertEqual(factory.call_count,1)
                    self.assertEqual(factory.call_args.args[0].address,1)
                app.select_house_speaker(app.speakers[0])
                self.assertEqual(app.selected_device().address,1)
            finally:
                for job in root.tk.splitlist(root.tk.call('after','info')):root.after_cancel(job)
                app.close()

    def test_persistence_error_clears_busy_and_preserves_cached_value(self):
        with tempfile.TemporaryDirectory() as folder:
            root=tk.Tk();root.withdraw();app=ClassroomApp(root,Path(folder))
            try:
                app.show_discovery([Speaker(1,'EVERBOOM main')],[])
                app.render_snapshot(app.speakers[0],{'sticky':False,'capabilities':{'sticky':True},'errors':{}})
                app.sticky.set(True)
                session=AsyncMock();session.close=Mock();session.request.return_value=b'\2\0'
                with patch('ue_partyup.controls.Session',return_value=session):
                    app.setting('set_sticky',True)
                    until=time.monotonic()+4
                    while app.busy and time.monotonic()<until:app._poll_events();time.sleep(.01)
                    self.assertFalse(app.busy)
                    self.assertIn('Stop PartyUp before changing',app.status.get())
                    self.assertFalse(app.selected_snapshot['sticky'])
                    self.assertFalse(app.sticky.get())
                    self.assertEqual(app.playback_notice.winfo_manager(),'pack')
                    self.assertIn('previous setting has been restored',app.playback_notice_text.get())
                    app.playback_notice_dismiss.invoke()
                    self.assertEqual(app.playback_notice.winfo_manager(),'')
                    self.assertEqual(session.request.await_count,1)
                    self.assertTrue(session.request.call_args.kwargs['read'])
            finally:
                for job in root.tk.splitlist(root.tk.call('after','info')):root.after_cancel(job)
                app.close()


