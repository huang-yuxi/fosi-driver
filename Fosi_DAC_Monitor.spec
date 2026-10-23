# -*- mode: python ; coding: utf-8 -*-

import sys
import os

block_cipher = None

added_files = [
    ('templates', 'templates'),
    ('static', 'static'),
    ('fosi_dac.ico', '.'),
]

excluded_modules = [
    'PyQt5',
    'PySide6',
    'matplotlib',
    'scipy',
    'pandas',
    'IPython',
    'notebook',
    'sphinx',
    'tkinter',
    'torch',
    'tensorflow',
    'sympy',
    'tables',
    'pyarrow',
    'numba',
    'bokeh',
    'distributed',
    'dask',
]

a = Analysis(
    ['app_launcher.py'],
    pathex=['j:\\fosi'],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'pycaw',
        'comtypes',
        'pystray',
        'pystray._win32',
        'PIL',
        'PIL.Image',
        'PIL.IcoImagePlugin',
        'psutil',
        'jinja2',
        'werkzeug',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_modules,
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
    name='Fosi DAC Monitor',
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
    icon='fosi_dac.ico',
)
