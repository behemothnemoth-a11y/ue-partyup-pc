"""Current-user private bundle installation, without admin rights or auto-launch."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from .runtime import data_directory, user_directory

SETTINGS=('selection.json','devices.json','eq-memories.json','house-layout.json','classroom-layout.json')


def import_settings(source, destination):
    source,destination=Path(source),Path(destination)
    imported=[]
    for name in SETTINGS:
        original,target=source/name,destination/name
        if target.exists() or not original.is_file(): continue
        if original.stat().st_size>1_000_000: raise ValueError('Settings file is unexpectedly large: '+name)
        content=original.read_text(encoding='utf-8')
        if not isinstance(json.loads(content),dict): raise ValueError('Settings must be a JSON object: '+name)
        destination.mkdir(parents=True,exist_ok=True)
        # Exclusive creation keeps an existing setting intact, including a concurrent import.
        try:
            with target.open('x',encoding='utf-8') as stream: stream.write(content)
        except FileExistsError: continue
        imported.append(name)
    return imported


def install_bundle(settings_source=None):
    if sys.platform!='win32' or not getattr(sys,'frozen',False):
        raise RuntimeError('Run the bundled Windows app with --install.')
    from . import __version__
    source=Path(sys.executable).resolve().parent
    destination=user_directory().parent/'Programs'/'PartyUpPC'/__version__
    executable=destination/'PartyUpPC.exe'
    if source!=destination:
        if destination.exists():
            raise FileExistsError('This version is already installed. Existing files were left intact.')
        shutil.copytree(source,destination)
    imported=import_settings(settings_source,data_directory()) if settings_source else []
    menu=Path(os.environ.get('APPDATA') or Path.home()/'AppData'/'Roaming')/'Microsoft'/'Windows'/'Start Menu'/'Programs'
    menu.mkdir(parents=True,exist_ok=True)
    def quoted(path): return "'"+str(path).replace("'","''")+"'"
    command=("$shell=New-Object -ComObject WScript.Shell; $shortcut=$shell.CreateShortcut("+
             quoted(menu/'PartyUp PC.lnk')+"); $shortcut.TargetPath="+quoted(executable)+
             "; $shortcut.WorkingDirectory="+quoted(destination)+"; $shortcut.Save()")
    subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],
                   creationflags=subprocess.CREATE_NO_WINDOW,check=True,timeout=20,capture_output=True)
    return {'message':'PartyUp is installed. Open PartyUp PC from the Start menu.',
            'version':__version__,'directory':str(destination),'settings_imported':imported,
            'auto_launched':False,'admin_required':False}

