# -*- mode: python ; coding: utf-8 -*-
"""
OpenBL3CMM PyInstaller spec file.
Usage: pyinstaller OpenBL3CMM.spec
"""

import sys
from pathlib import Path

block_cipher = None

# All Python source files that need to be bundled
source_files = [
    'main.py',
    'models.py',
    'parser.py',
    'exporter.py',
    'commands.py',
    'blimp.py',
    'blmod.py',
    'object_explorer.py',
    'hotfix_highlighter.py',
    'generate_datapack.py',
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[(f, '.') for f in source_files if f != 'main.py'] + [('openbl3cmm.ico', '.')],
    hiddenimports=[
        'commands',
        'models',
        'parser',
        'exporter',
        'blimp',
        'blmod',
        'object_explorer',
        'hotfix_highlighter',
        'generate_datapack',
        'yaml',
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'PIL',
        'cv2',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='OpenBL3CMM',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window — GUI only
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='openbl3cmm.ico',
)
