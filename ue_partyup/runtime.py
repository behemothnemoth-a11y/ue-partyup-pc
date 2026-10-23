"""Private desktop runtime: stable user data, redacted logs and one app per user."""
import ctypes
import hashlib
import importlib.metadata
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import re
import sys


def user_directory():
    return Path(os.environ.get('LOCALAPPDATA') or Path.home()/'AppData'/'Local')/'PartyUpPC'


def data_directory():
    return user_directory()/'data'


def redact(text):
    text=re.sub(r'(?i)\b(?:[0-9a-f]{2}[:-]){5}[0-9a-f]{2}\b','[speaker address]',str(text))
    return re.sub(r'(?i)\b[0-9a-f]{12}\b','[speaker address]',text)


class PrivateFormatter(logging.Formatter):
    def format(self, record):
        return redact(super().format(record))


def configure_logging():
    folder=user_directory()/'logs';folder.mkdir(parents=True,exist_ok=True)
    logger=logging.getLogger('partyup');logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler=RotatingFileHandler(folder/'app.log',maxBytes=200_000,backupCount=2,encoding='utf-8')
        handler.setFormatter(PrivateFormatter('%(asctime)s %(levelname)s %(message)s'))
        logger.addHandler(handler)
        logger.propagate=False
    return logger


class InstanceGuard:
    def __init__(self): self.handle=None
    def acquire(self):
        if sys.platform!='win32': return True
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.CreateMutexW.argtypes=[ctypes.c_void_p,ctypes.c_bool,ctypes.c_wchar_p]
        kernel.CreateMutexW.restype=ctypes.c_void_p
        key=hashlib.sha256(str(user_directory()).casefold().encode()).hexdigest()[:16]
        ctypes.set_last_error(0)
        self.handle=kernel.CreateMutexW(None,False,'Local\\PartyUpPC-'+key)
        error=ctypes.get_last_error()
        if not self.handle: raise ctypes.WinError(error)
        return error!=183
    def close(self):
        if self.handle:
            kernel=ctypes.WinDLL('kernel32',use_last_error=True)
            kernel.CloseHandle.argtypes=[ctypes.c_void_p]
            kernel.CloseHandle(self.handle);self.handle=None


def diagnostic_summary(app=None):
    from . import __version__
    versions={}
    for name in ('bleak','Pillow'):
        try: versions[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: versions[name]='unavailable'
    result={'application':'PartyUp PC','version':__version__,'private_preview':True,
            'python':sys.version.split()[0],'windows':sys.platform=='win32',
            'packaged':bool(getattr(sys,'frozen',False)),'dependencies':versions,
            'hardware_support':'Tested EVERBOOM pair; larger groups and older models unverified',
            'telemetry':False}
    if app is not None:
        result.update({'paired_candidates':len(app.speakers),'busy':app.busy,
                       'eq_result_unconfirmed':bool(app.tuning.blocked)})
    return result


def asset_check():
    from PIL import Image
    root=Path(__file__).with_name('assets')
    names=('classroom-background-v1.png','house-party-background.png','speaker-peach.png','speaker-lavender.png')
    for name in names:
        with Image.open(root/name) as image: image.verify()
    for name in ('Silkscreen-Regular.ttf','OFL-Silkscreen.txt'):
        if not (root/'fonts'/name).is_file(): raise FileNotFoundError(name)
    return diagnostic_summary()


def run():
    import argparse
    import multiprocessing
    multiprocessing.freeze_support()
    parser=argparse.ArgumentParser(description='PartyUp PC private Windows controller')
    parser.add_argument('--install',action='store_true',help='Install this private bundle for the current user')
    parser.add_argument('--import-settings',type=Path,help='Import missing local settings from a previous data directory')
    parser.add_argument('--smoke',action='store_true',help='Construct/close without Bluetooth activity')
    parser.add_argument('--self-check',action='store_true',help='Check bundled assets and dependencies without Bluetooth')
    parser.add_argument('--report',type=Path,help='Write a self-check report to this local file')
    args=parser.parse_args()
    if args.install:
        from .installer import install_bundle
        try:
            result=install_bundle(args.import_settings);code=0
        except Exception as error:
            result={'error':redact(error)};code=1
        if args.report: args.report.write_text(json.dumps(result,indent=2),encoding='utf-8')
        else:
            from tkinter import messagebox
            messagebox.showinfo('PartyUp private installer',result.get('message',result.get('error')))
        return code
    if args.self_check:
        try:
            result=asset_check();code=0
        except Exception as error:
            result={'error':redact(error)};code=1
        if args.report: args.report.write_text(json.dumps(result,indent=2),encoding='utf-8')
        if sys.stdout: print(json.dumps(result,indent=2))
        return code
    if args.smoke:
        from .app import main
        main(smoke=True);return 0
    guard=InstanceGuard()
    try:
        logger=configure_logging()
        from .installer import import_settings
        source=args.import_settings
        if source is None and not getattr(sys,'frozen',False):
            source=Path(__file__).resolve().parents[1]/'data'
        if source is not None: import_settings(source,data_directory())
        if not guard.acquire():
            from tkinter import messagebox
            messagebox.showinfo('PartyUp is already open','Use the existing PartyUp window. Only one controller can run at a time.')
            return 0
        from .app import main
        main(logger=logger)
        return 0
    except Exception:
        logging.getLogger('partyup').exception('Application startup failed')
        from tkinter import messagebox
        messagebox.showerror('PartyUp could not start','Startup failed. Check the local log at '+str(user_directory()/'logs'/'app.log'))
        return 1
    finally:
        guard.close()
