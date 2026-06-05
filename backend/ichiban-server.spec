# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

# Ensure app modules are found
BASE_DIR = Path(__file__).parent

a = Analysis(
    ['run.py'],
    pathex=[str(BASE_DIR)],
    binaries=[],
    datas=[],
    hiddenimports=[
        'app',
        'app.api',
        'app.api.admin',
        'app.api.auth',
        'app.api.draw',
        'app.api.events',
        'app.api.payments',
        'app.api.pools',
        'app.api.setup',
        'app.api.upload',
        'app.api.warehouse',
        'app.database',
        'app.config',
        'app.dependencies',
        'app.models',
        'app.models.admin',
        'app.models.payment',
        'app.models.pool',
        'app.models.prize_grade',
        'app.models.ticket',
        'app.models.warehouse',
        'app.schemas',
        'app.schemas.admin',
        'app.schemas.payment',
        'app.schemas.pool',
        'app.schemas.setup',
        'app.schemas.ticket',
        'app.schemas.warehouse',
        'app.services',
        'app.services.auth',
        'app.services.events',
        'app.services.shuffle',
        'aiosqlite',
        'qrcode',
        'pyotp',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'PIL.ImageQt',
        'PIL.ImageShow',
        'PIL.TiffImagePlugin',
        'test',
        'unittest',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ichiban-server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    contents_directory='.',
)

# COLLECT creates a one-folder build
dist_dir = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ichiban-server',
)
