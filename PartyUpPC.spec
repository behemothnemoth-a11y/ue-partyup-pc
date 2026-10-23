# Private Windows folder bundle. No local user data or research files are included.
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

a = Analysis(['desktop.py'],pathex=[SPECPATH],
    datas=collect_data_files('ue_partyup',includes=['assets/**/*'])+copy_metadata('bleak')+copy_metadata('Pillow'),
    hiddenimports=collect_submodules('winrt'),
    excludes=['pytest','unittest','pip','setuptools'],noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='PartyUpPC',debug=False,
        bootloader_ignore_signals=False,strip=False,upx=False,console=False,
        icon='ue_partyup/assets/speaker-peach.png')
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='PartyUpPC')
