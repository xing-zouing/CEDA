# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main_ui.py'],
    pathex=[],
    binaries=[('/home/yxk/.virtualenvs/CEDA/lib/python3.10/site-packages', 'site-packages')],
    datas=[('/home/yxk/CEDA/device_generation', 'device_generation'), ('/home/yxk/CEDA/analog_placement', 'analog_placement'), ('/home/yxk/CEDA/ota_case1', 'ota_case1'), ('/home/yxk/CEDA/rsmt_router', 'rsmt_router'), ('/home/yxk/CEDA/assets', 'assets')],
    hiddenimports=['PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'PyQt5.sip'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='parms',
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
)
