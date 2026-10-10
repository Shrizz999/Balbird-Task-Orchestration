# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Admin Dashboard app v4 (Stauff_Task_Orch/main.py)

import os

block_cipher = None
ROOT = os.path.abspath('.')

a = Analysis(
    ['Stauff_Task_Orch/main.py'],
    pathex=[ROOT, os.path.join(ROOT, 'Stauff_Task_Orch')],
    binaries=[],
    datas=[],
    hiddenimports=[
        'config',
        'services',
        'services.n8n_client',
        'services.sheets_client',
        'services.extension_store',
        'services.local_sync',
        'models',
        'models.data_models',
        'data',
        'data.repository',
        'data.models',
        'ui',
        'ui.main_window',
        'ui.dashboard',
        'ui.tasks',
        'ui.goals',
        'ui.updates',
        'ui.people',
        'ui.analytics',
        'ui.task_assignment',
        'ui.extension_requests',
        'ui.components',
        'tkcalendar',
        'babel',
        'babel.numbers',
        'pymongo',
        'pymongo.synchronous',
        'pymongo.synchronous.mongo_client',
        'dns',
        'dns.resolver',
        'matplotlib',
        'matplotlib.backends',
        'matplotlib.backends.backend_tkagg',
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
    name='Stauff Admin Dashboard v4',
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
    icon='admin.ico',
)
