"""Music-classroom grouping view: one teacher and nine independently selectable seats."""
import tkinter as tk
from .house_view import HousePartyApp, label
from .house_layout import HouseLayout
from .house_widgets import PocketButton, DISPLAY
from .theme import HERO, INK, MUTED, ACCENT, SURFACE, BORDER

# Normalized seat centers inspected against the generated music-room asset.
SEATS=((0,.502,.286),(1,.304,.499),(1,.505,.499),(1,.709,.499),
       (2,.288,.667),(2,.505,.667),(2,.720,.667),
       (3,.271,.855),(3,.505,.855),(3,.737,.855))


class ClassroomLayout(HouseLayout):
    def __init__(self,path):
        super().__init__(path)
        self.rooms=['Teacher','Front row','Middle row','Back row']
        self.teacher=None

    def ensure(self,addresses):
        addresses=list(dict.fromkeys(addresses))
        if len(addresses)>10:raise ValueError('One teacher and nine student speakers fit in the classroom.')
        if not addresses:
            self.teacher=None;return
        self.teacher=addresses[0];self.positions[self.teacher]=0
        taken={0}
        for address in addresses[1:]:
            slot=self.positions.get(address)
            if slot not in range(1,10) or slot in taken:
                slot=next(i for i in range(1,10) if i not in taken)
                self.positions[address]=slot
            taken.add(slot)

    def move(self,address,slot,active):
        self.ensure(active)
        if address==self.teacher or slot==0:
            if address==self.teacher and slot==0:return
            raise ValueError('The main speaker keeps the teacher chair. Move guests between student chairs.')
        super().move(address,slot,active)


class ClassroomApp(HousePartyApp):
    slots=SEATS
    layout_type=ClassroomLayout
    layout_filename='classroom-layout.json'
    background_name='classroom-background-v1.png'

    def __init__(self,root,data_path=None):
        from .app import DATA
        super().__init__(root,DATA if data_path is None else data_path)
        replacements={'House':'Classroom','YOUR HOUSE':'MUSIC CLASS','Rooms':'Seating',
            'Music in every room':'Class is in session',
            'SPEAKER DRAWER':'WAITING ROOM',
            'Drag a speaker into a room to join · select a speaker for controls':
                'Drag a speaker to a student chair to join · select a speaker for controls',
            'Room placement is your selection. Listen to confirm playback.':
                'Seats show selection. Check group for speaker reports; listen to confirm playback.'}
        def visit(widget):
            if isinstance(widget,PocketButton) and widget.label in replacements:
                widget.configure(text=replacements[widget.label])
            elif isinstance(widget,tk.Label):
                text=widget.cget('text')
                if text in replacements:widget.configure(text=replacements[text])
            for child in widget.winfo_children():visit(child)
        visit(root)
        self.sync_house()

    def sync_house(self):
        super().sync_house()
        if not self.house_ready:return
        try:
            selected=self.selected_device();active=self.active_house()
            if active and selected.address==active[0].address:
                self.house_room.set('TEACHER');self.house_identity.set(f'{selected.name[:24]} · Main speaker')
            else:
                number=next((i for i,s in enumerate(active[1:],1) if s.address==selected.address),None)
                if number is not None:
                    self.house_room.set(f'STUDENT {number}')
                    self.house_identity.set(f'{selected.name[:24]} · Guest speaker')
        except ValueError:pass

    def draw_scene(self):
        self.scene_job=None
        if not self.house_ready:return
        canvas=self.scene;canvas.delete('all')
        width,height=canvas.winfo_width(),canvas.winfo_height()
        if width<20 or height<20:return
        scale=min(width/self.art.house.width,height/self.art.house.height)
        w,h=max(1,int(self.art.house.width*scale)),max(1,int(self.art.house.height*scale))
        x,y=(width-w)/2,(height-h)/2;self.scene_rect=(x,y,w,h)
        self.background_photo=self.art.photo('house',w,h)
        canvas.create_image(x,y,image=self.background_photo,anchor='nw')
        self.room_hits=[];self.speaker_hits=[]
        active=self.active_house()[:10]
        self.layout.ensure([s.address for s in active])
        try:selected=self.selected_device().address
        except ValueError:selected=None
        sprite_width=max(34,min(80,int(w*.068)))
        self.scene_speaker_photo=self.art.photo('speaker',int(sprite_width*1.10))
        self.scene_guest_photo=self.art.photo('guest',sprite_width)
        for number,speaker in enumerate(active):
            slot=self.layout.positions[speaker.address]
            _,rx,ry=SEATS[slot];sx,sy=x+rx*w,y+ry*h
            photo=self.scene_speaker_photo if number==0 else self.scene_guest_photo
            box=(sx-photo.width()/2-5,sy-photo.height()/2-5,sx+photo.width()/2+5,sy+photo.height()/2+5)
            canvas.create_image(sx,sy,image=photo)
            if selected==speaker.address:
                for cx,cy,dx,dy in ((box[0],box[1],1,1),(box[2],box[1],-1,1),
                                   (box[0],box[3],1,-1),(box[2],box[3],-1,-1)):
                    canvas.create_line(cx+dx*10,cy,cx,cy,cx,cy+dy*8,fill=ACCENT,width=3)
            tag='TEACHER / MAIN' if number==0 else f'STUDENT {number}'
            text=canvas.create_text(sx,box[1]-7,text=tag,fill=HERO,font=(DISPLAY,8),anchor='s')
            badge=canvas.bbox(text)
            background=canvas.create_rectangle(badge[0]-4,badge[1]-2,badge[2]+4,badge[3]+2,fill=INK,outline=HERO)
            canvas.tag_lower(background,text)
            state=self.group_states.get(speaker.address,'')
            evidence='Reported' if state=='reported by main speaker' else 'Join accepted' if state=='join accepted' else 'Selected'
            canvas.create_text(sx,box[3]+3,text=evidence,fill=ACCENT if evidence!='Selected' else INK,
                               font=('Segoe UI',8,'bold'),anchor='n')
            self.speaker_hits.append((box,speaker))
        if not active:
            canvas.create_text(width/2,22,text='FIND SPEAKERS TO FILL YOUR MUSIC CLASS',fill=INK,font=(DISPLAY,10))

    def slot_at(self,x,y):
        if not hasattr(self,'scene_rect'):return None
        left,top,w,h=self.scene_rect
        if not (left<=x<=left+w and top<=y<=top+h):return None
        return min(range(10),key=lambda i:(x-left-SEATS[i][1]*w)**2+(y-top-SEATS[i][2]*h)**2)

    def free_slot_at(self,x,y):
        slot=self.slot_at(x,y)
        if slot is None or slot==0:return None
        taken={self.layout.positions[s.address] for s in self.active_house()}
        if slot in taken:return None
        return slot

    def house_release(self,event):
        try:
            super().house_release(event)
            if self.status.get()=='That room has no empty speaker slots. Choose another room.':
                self.status.set('Choose an empty student chair. The teacher chair belongs to the main speaker.')
        except (ValueError,KeyError) as error:self.status.set(str(error));self.sync_house()

    def edit_rooms(self):
        dialog=tk.Toplevel(self.root);dialog.title('Music class seating');dialog.configure(bg=SURFACE)
        label(dialog,'MUSIC CLASS',size=18,pixel=True,padx=18,pady=16)
        label(dialog,'The main speaker is the teacher. Choose a different main in Settings to change the teacher.\n\n'
                     'Nine guests have their own student chairs. Drag a waiting speaker to an empty chair to join.\n'
                     'Move a selected guest between chairs to rearrange locally. Drag a guest back to the waiting room to remove it.\n\n'
                     'Selected seats are not a connection check. Use Check group for fresh speaker reports.',
              wraplength=500,padx=18,pady=(0,18))

