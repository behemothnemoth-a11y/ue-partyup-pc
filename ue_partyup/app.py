import asyncio
import json
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from .controller import control,discover
from . import __version__

DATA=Path(__file__).resolve().parents[1]/'data'

def main(smoke=False):
    root=tk.Tk()
    root.title(f'UE PartyUp PC {__version__} — private preview')
    root.geometry('680x460')
    root.minsize(600,440)
    panel=ttk.Frame(root,padding=24)
    panel.pack(fill='both',expand=True)
    ttk.Label(panel,text='PartyUp from your PC',font=('Segoe UI',22,'bold')).pack(anchor='w')
    ttk.Label(panel,text='Private preview · Tested with two EVERBOOMs',padding=(0,6,0,15)).pack(anchor='w')
    ttk.Label(panel,text='Pair both speakers in Windows and keep them on. Close the phone app.\nChoose the main speaker you want Windows to play audio through.',wraplength=620).pack(anchor='w')
    selectors=ttk.Frame(panel)
    selectors.pack(fill='x',pady=16)
    choices=[]
    for label in ('Main speaker','Second speaker'):
        box=ttk.Frame(selectors)
        box.pack(side='left',fill='x',expand=True,padx=(0,12))
        ttk.Label(box,text=label).pack(anchor='w')
        combo=ttk.Combobox(box,state='readonly',width=26)
        combo.pack(fill='x',pady=5)
        choices.append(combo)
    message=tk.StringVar(value='Find paired speakers to begin.')
    ttk.Label(panel,textvariable=message,wraplength=620).pack(anchor='w',pady=12)
    buttons=ttk.Frame(panel)
    buttons.pack(anchor='w',pady=12)
    events=queue.Queue()
    busy=False
    speakers=[]
    controls=[]
    def worker(task):
        nonlocal busy
        busy=True
        for widget in controls: widget.configure(state='disabled')
        for combo in choices: combo.configure(state='disabled')
        def execute():
            try: events.put(('done',task()))
            except Exception as exc: events.put(('error',str(exc)))
        threading.Thread(target=execute,daemon=True).start()
    def refresh():
        message.set('Reading paired EVERBOOMs…')
        worker(lambda:discover())
    def action(kind):
        if any(combo.current()<0 for combo in choices):
            message.set('Select both speakers first.')
            return
        host,guest=[speakers[combo.current()] for combo in choices]
        if host==guest:
            message.set('Choose two different speakers.')
            return
        DATA.mkdir(exist_ok=True)
        (DATA/'selection.json').write_text(json.dumps({'host':host.address,'guest':guest.address}))
        worker(lambda:asyncio.run(control(kind,host,guest,lambda m:events.put(('progress',m)))))
    for label,command in [('Find speakers',refresh),('Start PartyUp',lambda:action('start')),
                          ('Check status',lambda:action('status')),('Stop PartyUp',lambda:action('stop'))]:
        button=ttk.Button(buttons,text=label,command=command)
        button.pack(side='left',padx=(0,8))
        controls.append(button)
    ttk.Label(panel,text='Only EVERBOOM is enabled in this preview. Other UE models need separate testing.\nClosing this window leaves your speaker group playing.',wraplength=620).pack(anchor='w',pady=15)
    def poll():
        nonlocal busy,speakers
        try:
            while True:
                kind,result=events.get_nowait()
                if kind=='progress': message.set(result); continue
                busy=False
                for widget in controls: widget.configure(state='normal')
                for combo in choices: combo.configure(state='readonly')
                if isinstance(result,list):
                    speakers=result
                    for combo in choices: combo.configure(values=[s.label for s in speakers])
                    if len(speakers)>=2:
                        choices[0].current(0); choices[1].current(1)
                        try:
                            saved=json.loads((DATA/'selection.json').read_text())
                            for combo,key in zip(choices,('host','guest')):
                                combo.current(next(i for i,s in enumerate(speakers) if s.address==saved[key]))
                        except (OSError,ValueError,KeyError,StopIteration): pass
                    message.set(f'Found {len(speakers)} paired EVERBOOMs. Choose your main speaker.')
                else: message.set(result)
        except queue.Empty: pass
        root.after(100,poll)
    def close():
        if busy:
            messagebox.showinfo('Operation in progress','Please wait for the speaker operation to finish before closing.')
        else: root.destroy()
    root.protocol('WM_DELETE_WINDOW',close)
    poll()
    if smoke:
        root.withdraw()
        root.after(150,root.destroy)
    else:
        root.after(150,refresh)
    root.mainloop()
