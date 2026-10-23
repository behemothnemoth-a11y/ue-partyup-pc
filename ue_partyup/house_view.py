"""Approved House Party presentation over the existing, tested controller."""
import tkinter as tk
from tkinter import ttk
from tkinter.font import Font
from .app import PartyUpApp, DATA, format_value
from .house_layout import HouseLayout, SLOTS
from .house_widgets import Artwork, PocketButton, PixelSlider, load_pixel_font, DISPLAY
from .theme import BG, HERO, SURFACE, PANEL, INK, MUTED, BORDER, ACCENT
from .house_settings import install_control_header, update_control_navigation, build_sound_studio


def label(parent,text='',variable=None,size=10,pixel=False,color=INK,anchor='w',wraplength=0,**pack):
    widget=tk.Label(parent,text=text,textvariable=variable,bg=parent.cget('background'),fg=color,
                    font=(DISPLAY if pixel else 'Segoe UI',size),anchor=anchor,wraplength=wraplength)
    widget.pack(**pack)
    return widget


class HousePartyApp(PartyUpApp):
    slots = SLOTS
    layout_type = HouseLayout
    layout_filename = 'house-layout.json'
    background_name = 'house-party-background.png'
    def __init__(self,root,data_path=DATA):
        self.house_ready=False
        load_pixel_font()
        super().__init__(root,data_path)
        self.legacy_shell=root.winfo_children()[0]
        self.legacy_shell.pack_forget()
        self.layout=self.layout_type(data_path/self.layout_filename)
        self.art=Artwork(root,background_name=self.background_name)
        self.room_hits=[];self.speaker_hits=[];self.drawer_hits=[];self.house_drag=None
        self.house_images=[];self.pending_house_remove=set()
        self.group_states={};self.scene_job=None
        root.geometry('1440x960');root.minsize(1120,800)
        self.house_shell=tk.Frame(root,bg=BG,padx=12,pady=10)
        self.house_shell.pack(fill='both',expand=True)
        self.build_house_shell()
        install_control_header(self)
        self.house_ready=True
        self.sync_house()

    def open_about(self):
        from .runtime import diagnostic_summary, user_directory
        from tkinter import filedialog
        import json
        from . import __version__
        dialog=tk.Toplevel(self.root);dialog.title('About PartyUp PC');dialog.configure(bg=SURFACE)
        label(dialog,'PARTYUP PC',pixel=True,size=20,padx=20,pady=(18,4))
        label(dialog,f'Private Windows preview {__version__}',color=ACCENT,padx=20)
        label(dialog,'One main speaker + up to nine guests. The tested hardware is your EVERBOOM pair.\n'
                     'Larger groups, older models and preview controls still need hardware acceptance.\n'
                     'Independent application; not affiliated with Ultimate Ears or Logitech.\n'
                     'No accounts, telemetry or automatic updates. Your settings stay on this PC.',
              wraplength=520,padx=20,pady=14)
        label(dialog,'Close the phone app if a control connection fails. Read EQ after an unconfirmed change.\n'
                     'Closing this controller leaves speaker audio playing.',wraplength=520,padx=20,pady=5)
        def export():
            path=filedialog.asksaveasfilename(parent=dialog,title='Save local diagnostic summary',
                      defaultextension='.json',initialfile='PartyUp-support.json',filetypes=[('JSON','*.json')])
            if path:
                try:
                    from pathlib import Path
                    Path(path).write_text(json.dumps(diagnostic_summary(self),indent=2),encoding='utf-8')
                    self.status.set('Diagnostic summary saved locally. No speaker names or addresses included.')
                except OSError as error:self.status.set(f'Could not save diagnostic summary: {error}')
        PocketButton(dialog,'Save support summary',export,width=260).pack(padx=20,pady=12)
        label(dialog,'Local logs: '+str(user_directory()/'logs'),size=9,color=MUTED,wraplength=520,padx=20,pady=(0,15))

    def button(self,parent,label,command,feature=None,variant=None):
        kind = 'start' if variant=='Primary.TButton' else 'stop' if variant=='Danger.TButton' else 'normal'
        width = Font(self.root,family=DISPLAY,size=9).measure(label.upper())+28
        return self.register(PocketButton(parent,label,command,kind,max(76,width),42,9),feature)

    def scale(self,parent,**options):
        return PixelSlider(parent,options['variable'],from_=options.get('from_',0),
                           to=options.get('to',31),orient=options.get('orient','horizontal'),
                           length=options.get('length',180))

    def setting(self,method,*args,**kwargs):
        if method == 'set_eq':
            from .settings import EQInfo
            self.tune_action('apply', destination=EQInfo(args[0],tuple(args[1])))
            return
        super().setting(method,*args,**kwargs)

    def build_sound(self,tab):
        build_sound_studio(self,tab)

    def pocket(self,parent,text,command,kind='normal',feature=None,width=160,height=44,font=10):
        button=PocketButton(parent,text,command,kind,width,height,font)
        self.register(button,feature)
        return button

    def build_house_shell(self):
        shell=self.house_shell
        header=tk.Frame(shell,bg=HERO,padx=10,pady=8);header.pack(fill='x')
        label(header,'⌂ PARTYUP',size=25,pixel=True,side='left')
        label(header,'Music in every room',size=11,side='left',padx=18)
        label(header,'PRIVATE PREVIEW',size=10,pixel=True,color=ACCENT,side='right',padx=10)
        navigation=tk.Frame(shell,bg=BG,pady=7);navigation.pack(fill='x')
        self.pocket(navigation,'House',self.return_house,'start',width=135,height=40).pack(side='left',padx=(0,6))
        self.pocket(navigation,'Sound',lambda:self.open_advanced('Sound'),'tab',width=135,height=40).pack(side='left',padx=(0,6))
        self.pocket(navigation,'Settings',lambda:self.open_advanced('Speaker'),'tab',width=135,height=40).pack(side='left')
        self.pocket(navigation,'Help',self.open_about,width=85,height=40).pack(side='right',padx=(8,0))
        self.pocket(navigation,'Find speakers',self.refresh,width=160,height=40).pack(side='right')
        # Pinned actions and feedback are packed first, so the scene yields at small sizes.
        footer=tk.Frame(shell,bg=BG);footer.pack(side='bottom',fill='x',pady=(7,0))
        label(footer,variable=self.status,size=10,fill='x')
        label(footer,'Room placement is your selection. Listen to confirm playback.',size=9,color=MUTED,fill='x')
        actions=tk.Frame(shell,bg=BG);actions.pack(side='bottom',fill='x',pady=(8,0))
        actions.grid_columnconfigure((0,1,2),weight=1,uniform='actions')
        self.house_start=self.pocket(actions,'▶ START PARTY',lambda:self.group_action('start'),'start',height=58,font=13)
        self.house_check=self.pocket(actions,'CHECK GROUP',lambda:self.group_action('status'),height=58,font=12)
        self.house_stop=self.pocket(actions,'■ STOP PARTY',lambda:self.group_action('stop'),'stop',height=58,font=13)
        for i,widget in enumerate((self.house_start,self.house_check,self.house_stop)):
            widget.grid(row=0,column=i,sticky='ew',padx=(0,8 if i<2 else 0))
        body=tk.Frame(shell,bg=BG);body.pack(fill='both',expand=True)
        body.grid_columnconfigure(0,weight=1);body.grid_columnconfigure(1,weight=0,minsize=330)
        body.grid_rowconfigure(0,weight=1)
        self.house_left=tk.Frame(body,bg=SURFACE,highlightthickness=1,highlightbackground=BORDER)
        self.house_left.grid(row=0,column=0,sticky='nsew',padx=(0,9))
        heading=tk.Frame(self.house_left,bg=SURFACE,padx=12,pady=7);heading.pack(fill='x')
        label(heading,'YOUR HOUSE',size=17,pixel=True,side='left')
        self.house_count=tk.StringVar(value='0 / 10 selected')
        label(heading,variable=self.house_count,size=10,color=MUTED,side='left',padx=14)
        self.pocket(heading,'Rooms',self.edit_rooms,width=85,height=33,font=8).pack(side='right')
        tray=tk.Frame(self.house_left,bg=PANEL,padx=9,pady=6);tray.pack(side='bottom',fill='x')
        tray_header=tk.Frame(tray,bg=PANEL);tray_header.pack(fill='x')
        label(tray_header,'SPEAKER DRAWER',size=12,pixel=True,side='left')
        label(tray_header,'Drag in to add · drag back to remove',size=9,color=MUTED,side='right')
        self.drawer=tk.Canvas(tray,bg=HERO,height=77,bd=0,highlightthickness=1,highlightbackground=BORDER,takefocus=True)
        self.drawer.pack(fill='x',pady=(5,0))
        drawer_scroll=ttk.Scrollbar(tray,orient='horizontal',command=self.drawer.xview)
        drawer_scroll.pack(fill='x');self.drawer.configure(xscrollcommand=drawer_scroll.set)
        self.drawer.bind('<Configure>',lambda _:self.draw_drawer())
        self.drawer.bind('<ButtonPress-1>',self.drawer_press)
        self.drawer.bind('<ButtonRelease-1>',self.house_release)
        self.drawer.bind('<Return>',lambda _:self.add_drawer_first())
        self.drawer.bind('<Right>',lambda _:self.drawer.xview_scroll(1,'units'))
        self.drawer.bind('<Left>',lambda _:self.drawer.xview_scroll(-1,'units'))
        label(self.house_left,'Drag a speaker into a room to join · select a speaker for controls',size=10,
              color=INK,side='bottom',pady=5)
        self.scene=tk.Canvas(self.house_left,bg=HERO,bd=0,highlightthickness=0,takefocus=True)
        self.scene.pack(fill='both',expand=True)
        self.scene.bind('<Configure>',self.schedule_scene)
        self.scene.bind('<ButtonPress-1>',self.scene_press)
        self.scene.bind('<ButtonRelease-1>',self.house_release)
        self.scene.bind('<Delete>',lambda _:self.remove_selected_house())
        self.scene.bind('<Right>',lambda _:self.cycle_house(1))
        self.scene.bind('<Left>',lambda _:self.cycle_house(-1))
        self.build_sidebar(body)

    def build_sidebar(self,body):
        outer=tk.Frame(body,bg=SURFACE,highlightthickness=1,highlightbackground=BORDER)
        outer.grid(row=0,column=1,sticky='nsew')
        self.sidebar_canvas=tk.Canvas(outer,bg=SURFACE,width=344,bd=0,highlightthickness=0)
        sidebar_scroll=ttk.Scrollbar(outer,orient='vertical',command=self.sidebar_canvas.yview)
        sidebar_scroll.pack(side='right',fill='y')
        self.sidebar_canvas.configure(yscrollcommand=sidebar_scroll.set)
        self.sidebar_canvas.pack(side='left',fill='both',expand=True)
        sidebar=tk.Frame(self.sidebar_canvas,bg=SURFACE,padx=12,pady=10)
        self.sidebar_window=self.sidebar_canvas.create_window((0,0),window=sidebar,anchor='nw')
        sidebar.bind('<Configure>',lambda _:self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox('all')))
        self.sidebar_canvas.bind('<Configure>',lambda event:self.sidebar_canvas.itemconfigure(self.sidebar_window,width=event.width))
        sidebar.bind('<MouseWheel>',lambda event:self.sidebar_canvas.yview_scroll(-1 if event.delta>0 else 1,'units'))
        self.sidebar=sidebar
        self.house_room=tk.StringVar(value='CHOOSE A SPEAKER')
        self.house_identity=tk.StringVar(value='Find paired speakers to begin')
        label(sidebar,variable=self.house_room,size=17,pixel=True,fill='x')
        label(sidebar,variable=self.house_identity,size=10,color=MUTED,fill='x',pady=(0,5))
        choose=tk.Frame(sidebar,bg=SURFACE);choose.pack(fill='x',pady=(0,7))
        self.house_combo=self.register(ttk.Combobox(choose,state='readonly',width=23),state='readonly')
        self.house_combo.pack(side='left',fill='x',expand=True)
        self.house_combo.bind('<<ComboboxSelected>>',self.house_combo_changed)
        self.pocket(choose,'Read',self.read_controls,feature='read_controls',width=65,height=34,font=8).pack(side='right',padx=(5,0))
        portrait=tk.Frame(sidebar,bg=HERO,highlightthickness=1,highlightbackground=BORDER,pady=12)
        portrait.pack(fill='x')
        self.portrait_image=self.art.photo('speaker',220)
        self.portrait_label=tk.Label(portrait,image=self.portrait_image,bg=HERO)
        self.portrait_label.pack()
        label(sidebar,'Guest controls and Remember group are disabled while PartyUp is on or unchecked. Stop PartyUp, then Check group to unlock.',size=9,color=ACCENT,wraplength=300,fill='x',pady=(8,0))
        self.house_battery=tk.StringVar(value='Battery unknown')
        label(portrait,variable=self.house_battery,size=11,color=ACCENT,anchor='center',fill='x')
        row=tk.Frame(sidebar,bg=SURFACE);row.pack(fill='x',pady=(11,0))
        label(row,'Volume',size=11,side='left')
        label(row,variable=self.volume_text,size=20,pixel=True,side='right')
        self.house_volume=self.register(PixelSlider(sidebar,self.volume,command=self.on_volume_release),'volume')
        self.house_volume.pack(fill='x',pady=(1,10))
        tk.Frame(sidebar,bg=BORDER,height=1).pack(fill='x',pady=(0,10))
        eqrow=tk.Frame(sidebar,bg=SURFACE);eqrow.pack(fill='x')
        label(eqrow,'EQ preset',size=10,side='left')
        self.house_eq=self.register(ttk.Combobox(eqrow,state='readonly',width=17),'eq',state='readonly')
        self.house_eq.pack(side='right')
        self.house_eq.bind('<<ComboboxSelected>>',self.house_eq_selected)
        bands=tk.Frame(sidebar,bg=SURFACE);bands.pack(fill='x',pady=(8,5))
        self.house_bands=[]
        for i,name in enumerate(('Low','Low-mid','Mid','High-mid','High')):
            box=tk.Frame(bands,bg=SURFACE);box.pack(side='left',expand=True,fill='x')
            slider=self.register(PixelSlider(box,self.eq_bands[i],from_=127,to=-128,orient='vertical',
                                            length=105,command=self.on_eq_band_release),'eq_band')
            slider.pack();self.house_bands.append(slider)
            label(box,name,size=8,anchor='center',fill='x')
        label(sidebar,'Bands use speaker levels, not dB.',size=8,color=MUTED,fill='x')
        shortcuts=tk.Frame(sidebar,bg=SURFACE);shortcuts.pack(fill='x',pady=(12,4))
        self.pocket(shortcuts,'Identify',self.identify,feature='identify',width=135,height=42).pack(side='left',fill='x',expand=True,padx=(0,5))
        self.pocket(shortcuts,'More controls',lambda:self.open_advanced('Speaker'),width=145,height=42,font=9).pack(side='left',fill='x',expand=True)
        self.pocket(sidebar,'Sync group volume',self.sync_group_volume,height=42,width=290).pack(fill='x',pady=(3,5))
        label(sidebar,'No controls loaded' ,variable=self.sound_hint,size=9,color=MUTED,wraplength=300,fill='x')

    def active_house(self):
        try:
            return [self.host(),*self.selected_guests()]
        except ValueError:
            return []

    def sync_house(self):
        if not self.house_ready:
            return
        active=self.active_house()
        self.layout.ensure([s.address for s in active[:10]])
        self.house_count.set(f'{len(active)} / 10 selected')
        if len(active)>10:self.status.set('Choose at most ten speakers before starting the group.')
        self.house_combo.configure(values=[s.name for s in self.speakers])
        current=self.device_combo.current()
        if current>=0:self.house_combo.current(current)
        try:
            speaker=self.selected_device()
            slot=self.layout.positions.get(speaker.address)
            self.house_room.set(self.layout.rooms[self.slots[slot][0]].upper() if slot is not None and speaker in active else speaker.name.upper()[:24])
            role='Main speaker' if active and speaker.address==active[0].address else 'Guest' if speaker in active else 'Not selected'
            self.house_identity.set(f'{speaker.name[:24]} · {role}')
            self.portrait_image=self.art.photo('speaker' if role=='Main speaker' else 'guest',220)
            self.portrait_label.configure(image=self.portrait_image)
        except ValueError:
            self.house_room.set('CHOOSE A SPEAKER');self.house_identity.set('Find paired speakers to begin')
        self.house_battery.set(format_value(self.selected_snapshot.get('battery')))
        self.house_eq.configure(values=[name for name,_ in self.eq_choices])
        if self.eq_combo.current()>=0:self.house_eq.current(self.eq_combo.current())
        else:self.house_eq.set('Read controls')
        self.house_volume.configure(to=self.selected_snapshot.get('max_volume') or 31)
        self.draw_scene();self.draw_drawer()

    def schedule_scene(self,_=None):
        if self.scene_job is not None:self.root.after_cancel(self.scene_job)
        self.scene_job=self.root.after(60,self.draw_scene)

    def draw_scene(self):
        self.scene_job=None
        if not self.house_ready:return
        canvas=self.scene;canvas.delete('all')
        width,height=canvas.winfo_width(),canvas.winfo_height()
        if width<20 or height<20:return
        # Aspect fit preserves every illustrated room and the approved pixel detail.
        scale=min(width/self.art.house.width,height/self.art.house.height)
        w,h=max(1,int(self.art.house.width*scale)),max(1,int(self.art.house.height*scale))
        x,y=(width-w)/2,(height-h)/2
        self.scene_rect=(x,y,w,h)
        self.background_photo=self.art.photo('house',w,h)
        canvas.create_image(x,y,image=self.background_photo,anchor='nw')
        self.room_hits=[];self.speaker_hits=[]
        for room,(rx,ry) in enumerate(((.18,.25),(.61,.25),(.18,.56),(.61,.56))):
            tx,ty=x+rx*w,y+ry*h
            text=canvas.create_text(tx+7,ty+4,text=self.layout.rooms[room],anchor='nw',fill=INK,font=('Segoe UI',10,'bold'))
            box=canvas.bbox(text)
            bg=canvas.create_rectangle(box[0]-6,box[1]-3,box[2]+6,box[3]+3,fill=HERO,outline=INK,width=1)
            canvas.tag_lower(bg,text)
            self.room_hits.append((room,tx,ty))
        active=self.active_house()[:10];occupied=set()
        try:selected=self.selected_device().address
        except ValueError:selected=None
        sprite_width=max(34,min(78,int(w*(.065 if len(active)>4 else .092))))
        self.scene_speaker_photo=self.art.photo('speaker',sprite_width)
        self.scene_guest_photo=self.art.photo('guest',sprite_width)
        sh=self.scene_speaker_photo.height()
        for number,speaker in enumerate(active):
            slot=self.layout.positions[speaker.address];occupied.add(slot)
            room,rx,ry=self.slots[slot];sx,sy=x+rx*w,y+ry*h
            box=(sx-sprite_width/2-5,sy-sh/2-5,sx+sprite_width/2+5,sy+sh/2+5)
            canvas.create_image(sx,sy,image=self.scene_speaker_photo if number==0 else self.scene_guest_photo)
            if selected==speaker.address:
                for cx,cy,dx,dy in ((box[0],box[1],1,1),(box[2],box[1],-1,1),
                                   (box[0],box[3],1,-1),(box[2],box[3],-1,-1)):
                    canvas.create_line(cx+dx*11,cy,cx,cy,cx,cy+dy*9,fill=ACCENT,width=3)
            tag='MAIN' if number==0 else f'GUEST {number}'
            text=canvas.create_text(sx,box[1]-8,text=tag,fill=HERO,font=(DISPLAY,8),anchor='s')
            badge=canvas.bbox(text)
            background=canvas.create_rectangle(badge[0]-4,badge[1]-2,badge[2]+4,badge[3]+2,fill=INK,outline=HERO)
            canvas.tag_lower(background,text)
            self.speaker_hits.append((box,speaker))
        for slot,(room,rx,ry) in enumerate(self.slots[:4]):
            if slot not in occupied:
                sx,sy=x+rx*w,y+ry*h
                canvas.create_rectangle(sx-27,sy-17,sx+27,sy+17,outline=INK,width=2,dash=(5,3))
        if not active:
            canvas.create_text(width/2,22,text='FIND SPEAKERS TO BUILD YOUR PARTY',fill=INK,font=(DISPLAY,11))

    def draw_drawer(self):
        if not self.house_ready:return
        self.drawer.delete('all');self.drawer_hits=[]
        selected={s.address for s in self.active_house()}
        available=[s for s in self.speakers if s.address not in selected]
        self.drawer_photo=self.art.photo('guest',58)
        for index,speaker in enumerate(available):
            x=8+index*220
            self.drawer.create_rectangle(x,7,x+210,69,fill=PANEL,outline=BORDER,width=2)
            self.drawer.create_image(x+38,38,image=self.drawer_photo)
            self.drawer.create_text(x+76,23,text=speaker.name[:17],anchor='w',fill=INK,font=('Segoe UI',10,'bold'))
            self.drawer.create_text(x+76,46,text='Paired · not selected',anchor='w',fill=MUTED,font=('Segoe UI',8))
            self.drawer.create_text(x+194,37,text='+',fill=ACCENT,font=(DISPLAY,18))
            self.drawer_hits.append(((x,7,x+210,69),speaker))
        if not available:
            self.drawer.create_text(15,34,text='All paired speakers are selected.' if selected else 'Find speakers paired in Windows to begin.',
                                    anchor='w',fill=MUTED,font=('Segoe UI',10))
        self.drawer.configure(scrollregion=(0,0,max(self.drawer.winfo_width(),len(available)*220+16),77))

    @staticmethod
    def inside(box,x,y):return box[0]<=x<=box[2] and box[1]<=y<=box[3]

    def scene_press(self,event):
        if self.busy:return
        self.scene.focus_set()
        for box,speaker in reversed(self.speaker_hits):
            if self.inside(box,event.x,event.y):
                self.select_house_speaker(speaker)
                self.house_drag=(speaker,event.x_root,event.y_root,'house')
                return

    def drawer_press(self,event):
        if self.busy:return
        self.drawer.focus_set()
        for box,speaker in self.drawer_hits:
            if self.inside(box,self.drawer.canvasx(event.x),event.y):
                self.house_drag=(speaker,event.x_root,event.y_root,'drawer')
                return

    def slot_at(self,x,y):
        left,top,width,height=self.scene_rect
        if not self.inside((left,top,left+width,top+height),x,y):return None
        return min(range(10),key=lambda i:(x-left-self.slots[i][1]*width)**2+(y-top-self.slots[i][2]*height)**2)

    def free_slot_at(self,x,y):
        left,top,width,height=self.scene_rect
        nearest=self.slot_at(x,y)
        if nearest is None:return None
        room=self.slots[nearest][0]
        taken={self.layout.positions[s.address] for s in self.active_house()}
        free=[i for i in range(10) if i not in taken and self.slots[i][0]==room]
        return min(free,key=lambda i:(x-left-self.slots[i][1]*width)**2+(y-top-self.slots[i][2]*height)**2) if free else None

    def house_release(self,event):
        dragged,self.house_drag=self.house_drag,None
        if not dragged or self.busy:return
        speaker,sx,sy,origin=dragged
        moved=abs(event.x_root-sx)+abs(event.y_root-sy)>12
        if not moved:
            if origin=='drawer':self.add_to_house(speaker)
            return
        x,y=event.x_root-self.scene.winfo_rootx(),event.y_root-self.scene.winfo_rooty()
        slot=self.slot_at(x,y) if hasattr(self,'scene_rect') else None
        if slot is not None:
            if origin=='drawer':
                slot=self.free_slot_at(x,y)
                if slot is None:
                    self.status.set('That room has no empty speaker slots. Choose another room.');return
                self.add_to_house(speaker,slot)
            else:
                self.layout.move(speaker.address,slot,[s.address for s in self.active_house()])
                self.save_rooms();self.sync_house()
        elif origin=='house' and self.inside((0,0,self.drawer.winfo_width(),self.drawer.winfo_height()),
                    event.x_root-self.drawer.winfo_rootx(),event.y_root-self.drawer.winfo_rooty()):
            self.remove_from_house(speaker)

    def add_drawer_first(self):
        try:chosen=self.selected_device()
        except ValueError:chosen=None
        if chosen is not None and any(s.address==chosen.address for _,s in self.drawer_hits):
            self.add_to_house(chosen)
        elif self.drawer_hits:self.add_to_house(self.drawer_hits[0][1])

    def add_to_house(self,speaker,slot=None):
        if self.busy:return
        try:
            if len(self.active_house())>=10:raise ValueError('Ten speakers are selected. Remove a guest before adding another.')
            index=next(i for i,s in enumerate(self.guest_choices) if s.address==speaker.address)
            self.guest_list.selection_set(index);self.guests_changed()
            self.layout.ensure([s.address for s in self.active_house()])
            if slot is not None:self.layout.move(speaker.address,slot,[s.address for s in self.active_house()])
            self.save_rooms();self.select_house_speaker(speaker);self.sync_house()
            self.group_action('add',guests_override=[speaker])
        except (ValueError,StopIteration) as exc:self.status.set(str(exc) or 'Choose a main speaker first.')

    def remove_from_house(self,speaker):
        if self.busy:return
        if speaker.address==self.host().address:
            self.status.set('The main speaker stays in the house. Choose a different main in Settings.');return
        self.pending_house_remove.add(speaker.address)
        self.group_action('remove',guests_override=[speaker])

    def remove_selected_house(self):
        try:self.remove_from_house(self.selected_device())
        except ValueError:pass

    def cycle_house(self,direction):
        if self.busy:return
        active=self.active_house()
        if not active:return
        try:index=next(i for i,s in enumerate(active) if s.address==self.selected_device().address)
        except (ValueError,StopIteration):index=0
        self.select_house_speaker(active[(index+direction)%len(active)])

    def select_house_speaker(self,speaker):
        if self.busy:return
        index=next((i for i,s in enumerate(self.speakers) if s.address==speaker.address),None)
        if index is not None:
            self.device_combo.current(index)
            # Selection uses cached readings only; Read is always an explicit action.
            self.render_snapshot(speaker,self.snapshots.get(speaker.address,{}))

    def house_combo_changed(self,_=None):
        index=self.house_combo.current()
        if 0<=index<len(self.speakers):self.select_house_speaker(self.speakers[index])

    def device_changed(self,event=None):
        if self.house_ready and self.house_shell.winfo_manager():
            try:speaker=self.selected_device()
            except ValueError:return
            self.render_snapshot(speaker,self.snapshots.get(speaker.address,{}))
            return
        super().device_changed(event)

    def on_tab_changed(self,event=None):
        if self.house_ready and self.house_shell.winfo_manager():return
        update_control_navigation(self)
        super().on_tab_changed(event)

    def house_eq_selected(self,_=None):
        if self.busy or self.house_eq.instate(['disabled']):return
        self.eq_combo.current(self.house_eq.current());self.apply_eq()

    def save_rooms(self):
        try:self.layout.save()
        except OSError as exc:self.status.set(f'Room layout could not be saved: {exc}')

    def edit_rooms(self):
        if self.busy:return
        dialog=tk.Toplevel(self.root);dialog.title('Room names · local layout');dialog.configure(bg=SURFACE)
        entries=[]
        for name in self.layout.rooms:
            entry=ttk.Entry(dialog,width=28);entry.insert(0,name);entry.pack(padx=18,pady=6);entries.append(entry)
        def save():
            values=[entry.get().strip() for entry in entries]
            if any(not x or len(x)>24 for x in values):
                self.status.set('Room names must have 1–24 characters.');return
            self.layout.rooms=values;self.save_rooms();self.sync_house();dialog.destroy()
        ttk.Button(dialog,text='Save room names',command=save).pack(pady=12)

    def open_advanced(self,page):
        self.house_shell.pack_forget();self.legacy_shell.pack(fill='both',expand=True)
        self.notebook.select(self.tab_viewports[page])
        update_control_navigation(self)

    def return_house(self):
        if not self.house_ready:return
        self.legacy_shell.pack_forget();self.house_shell.pack(fill='both',expand=True);self.sync_house()

    def render_snapshot(self,speaker,snapshot):
        super().render_snapshot(speaker,snapshot)
        self.sync_house()

    def guests_changed(self,event=None):
        super().guests_changed(event)
        self.sync_house()

    def show_discovery(self,speakers,radios):
        super().show_discovery(speakers,radios)
        self.sync_house()

    def clear_group_results(self):
        super().clear_group_results()
        if hasattr(self,'group_states'):self.group_states.clear()
        self.sync_house()

    def show_group(self,result):
        super().show_group(result)
        for member in result.members:
            self.group_states[member.speaker.address]=member.state
            if member.speaker.address in self.pending_house_remove:
                if member.state=='leave accepted':
                    for i,speaker in enumerate(self.guest_choices):
                        if speaker.address==member.speaker.address:self.guest_list.selection_clear(i)
                self.pending_house_remove.discard(member.speaker.address)
        self.guests_changed();self.sync_house()

    def update_enabled(self):
        super().update_enabled()
        if self.house_ready:
            self.draw_scene();self.draw_drawer()

    def close(self):
        if not self.busy and self.scene_job is not None:
            self.root.after_cancel(self.scene_job);self.scene_job=None
        super().close()

