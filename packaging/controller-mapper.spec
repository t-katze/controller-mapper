# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


ROOT = Path(SPECPATH).resolve().parent
SRC = ROOT / "src"
PROFILES = ROOT / "profiles"

datas = []
if PROFILES.exists():
    datas.extend((str(path), "profiles") for path in PROFILES.glob("*.yaml"))
    datas.extend((str(path), "profiles") for path in PROFILES.glob("*.yml"))

hiddenimports = set(collect_submodules("controller_mapper"))
hiddenimports.add("pygame")
try:
    hiddenimports.update(collect_submodules("pyvjoy"))
except Exception:
    hiddenimports.add("pyvjoy")

a = Analysis(
    [str(SRC / "controller_mapper" / "main.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=datas,
    hiddenimports=sorted(hiddenimports),
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
    [],
    exclude_binaries=True,
    name="controller-mapper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="controller-mapper",
)
