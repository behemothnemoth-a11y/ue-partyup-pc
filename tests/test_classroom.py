from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch
from ue_partyup.classroom_view import ClassroomLayout, ClassroomApp
from ue_partyup.controller import Speaker

class ClassroomTests(unittest.TestCase):
    def test_teacher_reserved_guest_swap_and_teacher_change(self):
        with tempfile.TemporaryDirectory() as folder:
            layout=ClassroomLayout(Path(folder)/'classroom.json')
            active=list(range(1,11));layout.ensure(active)
            self.assertEqual(layout.positions[1],0)
            self.assertEqual({layout.positions[x] for x in active},set(range(10)))
            with self.assertRaises(ValueError):layout.move(2,0,active)
            with self.assertRaises(ValueError):layout.move(1,3,active)
            a,b=layout.positions[2],layout.positions[3]
            layout.move(2,b,active)
            self.assertEqual((layout.positions[2],layout.positions[3]),(b,a))
            layout.ensure([2,1]+active[2:])
            self.assertEqual(layout.positions[2],0)
            self.assertEqual(len({layout.positions[x] for x in active}),10)
            layout.save();loaded=ClassroomLayout(layout.path)
            self.assertEqual(loaded.positions,layout.positions)
            with self.assertRaises(ValueError):layout.ensure(range(1,12))

    def test_ten_seats_render_without_bluetooth_and_teacher_cannot_be_join_target(self):
        with tempfile.TemporaryDirectory() as folder:
            root=tk.Tk();root.withdraw()
            app=ClassroomApp(root,Path(folder))
            try:
                with patch.object(app,'worker') as worker:
                    app.show_discovery([Speaker(i,f'EVERBOOM {i}') for i in range(1,11)],[])
                    app.guest_list.selection_set(0,8);app.guests_changed()
                    with patch.object(app.scene,'winfo_width',return_value=900),patch.object(app.scene,'winfo_height',return_value=510):
                        app.draw_scene()
                    self.assertEqual(len(app.speaker_hits),10)
                    left,top,w,h=app.scene_rect
                    self.assertIsNone(app.free_slot_at(left+.502*w,top+.286*h))
                    app.select_house_speaker(app.speakers[1])
                    self.assertIn('STUDENT',app.house_room.get())
                    worker.assert_not_called()
            finally:app.close()
