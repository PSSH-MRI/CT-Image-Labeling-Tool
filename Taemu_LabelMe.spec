# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['Taemu_LabelMe.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('Taemu_Validation.py', '.'),
        ('icon.ico', '.')
    ],
    hiddenimports=['tkinterdnd2.TkinterDnD'],
    hookspath=['.'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['scipy', 'matplotlib'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Taemu_LabelMe',
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
    icon='icon.ico',
)
