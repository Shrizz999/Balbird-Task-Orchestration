# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Employee Task Updater app v11 (task_updater_app.py)

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None
ROOT = os.path.abspath('.')

# Collect all required asset files and library templates
datas = [
    ('user.ico', '.'),
    ('admin.ico', '.'),
]
datas += collect_data_files('customtkinter')
datas += collect_data_files('babel')

hiddenimports = [
    'config',
    'services',
    'services.n8n_client',
    'services.sheets_client',
    'services.supabase_client',
    'services.extension_store',
    'services.local_sync',
    'services.notifier',
    'winotify',
    'models',
    'models.data_models',
    'tkcalendar',
    'babel',
    'babel.numbers',
    'babel.dates',
    'pymongo',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'PIL._tkinter_finder',
    'requests',
    'urllib3',
    'postgrest',
    'gotrue',
    'httpx',
    'httpcore',
    'anyio',
    'sniffio',
    'h11',
]
hiddenimports += collect_submodules('customtkinter')
hiddenimports += collect_submodules('supabase')
hiddenimports += collect_submodules('postgrest')
hiddenimports += collect_submodules('gotrue')
hiddenimports += collect_submodules('httpx')

a = Analysis(
    ['task_updater_app.py'],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Stauff Task Updater v11',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='user.ico',
)
