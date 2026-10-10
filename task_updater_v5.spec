# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Employee Task Updater app v4 (task_updater_app.py)

import os

block_cipher = None
ROOT = os.path.abspath('.')

a = Analysis(
    ['task_updater_app.py'],
    pathex=[ROOT],
    binaries=[],
    datas=[],
    hiddenimports=[
        'config',
        'services',
        'services.n8n_client',
        'services.sheets_client',
        'services.extension_store',
        'services.local_sync',
        'pymongo',
        'models',
        'models.data_models',
        'tkcalendar',
        'babel',
        'babel.numbers',
    ],
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
    name='Stauff Task Updater v5',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
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
